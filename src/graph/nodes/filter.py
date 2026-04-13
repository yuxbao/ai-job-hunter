from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

from config.settings import settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.models.job import JobPosting
from src.prompts.planner_prompt import FILTER_PROMPT
from src.tools.data_adapter import DataAdapter
from src.utils.logger import logger, print_llm_output, write_llm_output


async def run(state: dict, llm: BaseChatModel | None = None) -> dict:
    """筛选节点: 使用 LLM 进行语义筛选，LLM 不可用时纯规则筛选"""
    scraped_pages = state.get("gated_results", [])

    if not scraped_pages:
        logger.warning("[Filter] 没有待筛选数据")
        return {"candidate_jobs": [], "status": "filtering"}

    logger.info(f"[Filter] 开始语义筛选 {len(scraped_pages)} 条门控后数据")

    adapted = list(scraped_pages)

    # 去重 (基于 title + company)
    seen = set()
    unique = []
    for item in adapted:
        key = f"{item.get('title', '')}|{item.get('company', '')}"
        if key not in seen and item.get("title"):
            seen.add(key)
            unique.append(item)

    logger.info(f"[Filter] 去重后 {len(unique)} 条")

    # 基于规则的预筛选
    pre_filtered = _rule_based_filter(unique)
    logger.info(f"[Filter] 规则预筛选后 {len(pre_filtered)} 条")

    # LLM 语义筛选（分批处理）
    candidates = []

    output_dir = state.get("output_dir", settings.OUTPUT_DIR)

    if llm is None:
        # 无 LLM 时，规则筛选结果直接转为 JobPosting
        logger.info("[Filter] LLM 不可用，使用纯规则筛选")
        for item in pre_filtered:
            job = JobPosting(
                title=item.get("title", ""),
                company=item.get("company", ""),
                location=item.get("location", ""),
                salary=item.get("salary", ""),
                tech_tags=item.get("tech_tags", []),
                requirements=item.get("requirements", ""),
                source=item.get("source", ""),
                job_url=item.get("job_url", ""),
                confidence=0.8,
            )
            candidates.append(job)
    else:
        batch_size = state.get("batch_size", 10)
        total_batches = (len(pre_filtered) + batch_size - 1) // batch_size
        logger.info(f"[Filter] 使用并发数 {settings.FILTER_CONCURRENCY} 执行批量筛选")
        candidates = await _filter_batches(
            pre_filtered,
            llm=llm,
            batch_size=batch_size,
            total_batches=total_batches,
            output_dir=output_dir,
            max_concurrency=settings.FILTER_CONCURRENCY,
        )

    logger.info(f"[Filter] 筛选后 {len(candidates)} 条候选岗位")

    return {"candidate_jobs": candidates, "status": "filtering"}


async def _filter_batches(
    items: list[dict],
    llm: BaseChatModel,
    batch_size: int,
    total_batches: int,
    output_dir: str,
    max_concurrency: int,
) -> list[JobPosting]:
    semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def process_batch(batch_number: int, batch: list[dict]) -> tuple[int, list[JobPosting]]:
        logger.info(f"[Filter] 执行 LLM 批次 {batch_number}/{total_batches}")
        async with semaphore:
            candidates = await _llm_filter_batch(
                batch,
                llm,
                batch_number,
                total_batches,
                output_dir,
            )
        logger.info(f"[Filter] 完成 LLM 批次 {batch_number}/{total_batches}")
        return batch_number, candidates

    tasks = [
        asyncio.create_task(
            process_batch(batch_number, items[start : start + batch_size])
        )
        for batch_number, start in enumerate(range(0, len(items), batch_size), 1)
    ]
    batch_results = await asyncio.gather(*tasks)
    batch_results.sort(key=lambda item: item[0])

    candidates: list[JobPosting] = []
    for _, batch_candidates in batch_results:
        candidates.extend(batch_candidates)
    return candidates


def _rule_based_filter(items: list[dict]) -> list[dict]:
    """基于简单规则的预筛选"""
    ai_keywords = [
        "ai", "人工智能", "机器学习", "深度学习", "算法",
        "llm", "大模型", "nlp", "cv", "计算机视觉",
        "推荐", "搜索", "数据", "模型", "pytorch", "tensorflow",
        "神经网络", "transformer", "多模态", "语音",
        "agent", "rag", "aigc", "强化学习",
    ]
    exclude_keywords = [
        "前端", "测试", "运维", "销售", "行政", "hr", "人事",
        "3年以上", "5年", "社招", "高级",
    ]

    filtered = []
    for item in items:
        title = item.get("title", "").lower()
        desc = item.get("description", "").lower()
        text = f"{title} {desc}"
        job_url = item.get("job_url", "")
        parsed_url = urlparse(job_url)
        low_quality_liepin_page = (
            "liepin.com" in parsed_url.netloc.lower()
            and parsed_url.path.startswith("/zp")
            and "/job/" not in parsed_url.path
        )

        # 排除明显不符合的
        has_exclude = any(kw in text for kw in exclude_keywords)
        if has_exclude:
            continue

        # 排除明显的聚合页/索引页，避免把“招聘网”当成具体岗位
        low_quality_page = (
            "招聘网" in title
            or "汇聚众多行业名企" in desc
            or "公司名" in desc
            or low_quality_liepin_page
        )
        if low_quality_page:
            continue

        # 包含 AI 相关关键词
        has_ai = any(kw in text for kw in ai_keywords)
        if has_ai:
            filtered.append(item)
        elif title:  # title 不为空但没匹配到，也保留（可能 LLM 能判断）
            filtered.append(item)

    return filtered


async def _llm_filter_batch(
    batch: list[dict],
    llm: BaseChatModel,
    batch_number: int,
    total_batches: int,
    output_dir: str,
) -> list[JobPosting]:
    """使用 LLM 对一批岗位进行语义筛选"""
    # 简化输入，减少 token
    simplified = []
    for i, item in enumerate(batch):
        simplified.append({
            "index": i,
            "title": item.get("title", "")[:100],
            "company": item.get("company", "")[:50],
            "description": item.get("description", "")[:300],
        })

    prompt = FILTER_PROMPT.format(jobs_json=json.dumps(simplified, ensure_ascii=False))

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        if settings.WRITE_LLM_OUTPUT_FILES:
            write_llm_output(
                output_dir,
                "filter",
                str(response.content),
                meta={
                    "batch_number": batch_number,
                    "total_batches": total_batches,
                    "batch_size": len(batch),
                },
            )
        if settings.SHOW_LLM_OUTPUT:
            print_llm_output(
                f"Filter AI Reply {batch_number}/{total_batches}",
                str(response.content),
                max_chars=settings.LLM_OUTPUT_MAX_CHARS,
            )
        result = _parse_json_array(response.content)
    except Exception as e:
        logger.warning(f"[Filter] LLM 筛选异常: {e}")
        result = []

    # 根据 LLM 判断结果筛选
    candidates = []
    for item in result:
        idx = item.get("index", -1)
        if 0 <= idx < len(batch) and item.get("is_relevant", False):
            raw = batch[idx]
            job = JobPosting(
                title=raw.get("title", ""),
                company=raw.get("company", ""),
                location=raw.get("location", ""),
                salary=raw.get("salary", ""),
                source=raw.get("source", ""),
                job_url=raw.get("job_url", ""),
                description=raw.get("description", ""),
                confidence=item.get("confidence", 0.7),
            )
            candidates.append(job)

    return candidates


def _parse_json_array(text: str) -> list[dict]:
    """从 LLM 响应中解析 JSON 数组"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
