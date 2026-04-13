from __future__ import annotations

import asyncio
import json

from config.settings import settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.models.job import JobPosting
from src.prompts.planner_prompt import ENRICH_PROMPT
from src.utils.logger import logger, print_llm_output, write_llm_output


def _job_key(job: JobPosting) -> tuple[str, str, str]:
    return (job.job_url, job.title, job.company)


def _needs_enrichment(job: JobPosting) -> bool:
    return not job.tech_tags or not job.requirements or not job.salary


def _shortlist_candidates(
    candidates: list[JobPosting],
    target_count: int,
    buffer_count: int,
) -> list[JobPosting]:
    if len(candidates) <= target_count + buffer_count:
        return candidates

    ranked = sorted(candidates, key=lambda job: job.confidence, reverse=True)
    limit = target_count + buffer_count
    selected: list[JobPosting] = []
    selected_keys: set[tuple[str, str, str]] = set()

    # 先保证每个来源至少有一条，避免短名单被单一来源挤满。
    for job in ranked:
        if job.source in {item.source for item in selected}:
            continue
        key = _job_key(job)
        selected.append(job)
        selected_keys.add(key)
        if len(selected) >= limit:
            return selected

    for job in ranked:
        key = _job_key(job)
        if key in selected_keys:
            continue
        selected.append(job)
        selected_keys.add(key)
        if len(selected) >= limit:
            break

    return selected


async def _enrich_candidates(
    shortlisted: list[JobPosting],
    llm: BaseChatModel | None,
    output_dir: str,
    max_concurrency: int,
) -> list[JobPosting]:
    total = len(shortlisted)
    semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def process_one(index: int, job: JobPosting) -> JobPosting:
        title = job.title[:36] if job.title else "Untitled"
        logger.info(f"[Enricher] 处理 {index}/{total}: {title}")

        if llm is None or not _needs_enrichment(job):
            logger.info(f"[Enricher] 完成 {index}/{total}: {title} (无需补全)")
            return job

        try:
            async with semaphore:
                enriched_job = await _enrich_single(job, llm, output_dir, index, total)
        except Exception as exc:
            logger.debug(f"[Enricher] 补全失败 {index}/{total}: {exc}")
            logger.info(f"[Enricher] 完成 {index}/{total}: {title} (补全失败，保留原始数据)")
            return job

        logger.info(f"[Enricher] 完成 {index}/{total}: {title}")
        return enriched_job

    tasks = [
        asyncio.create_task(process_one(index, job))
        for index, job in enumerate(shortlisted, 1)
    ]
    return await asyncio.gather(*tasks)


async def run(state: dict, llm: BaseChatModel | None = None) -> dict:
    """补全节点: 使用 LLM 补全缺失字段并识别技术栈"""
    candidates: list[JobPosting] = state.get("candidate_jobs", [])

    if not candidates:
        logger.warning("[Enricher] 没有待补全的岗位")
        return {"candidate_jobs": [], "status": "enriching"}

    target_count = state.get("target_count", 50)
    output_dir = state.get("output_dir", settings.OUTPUT_DIR)
    shortlisted = _shortlist_candidates(
        candidates,
        target_count=target_count,
        buffer_count=settings.ENRICH_CANDIDATE_BUFFER,
    )

    if len(shortlisted) < len(candidates):
        logger.info(
            f"[Enricher] 候选 {len(candidates)} 条，仅补全前 {len(shortlisted)} 条高置信短名单"
        )
    else:
        logger.info(f"[Enricher] 开始补全 {len(shortlisted)} 条岗位信息")

    logger.info(
        f"[Enricher] 使用并发数 {settings.ENRICH_CONCURRENCY} 进行补全"
    )
    enriched = await _enrich_candidates(
        shortlisted,
        llm=llm,
        output_dir=output_dir,
        max_concurrency=settings.ENRICH_CONCURRENCY,
    )

    # 计算技术标签统计
    tech_stats: dict[str, int] = {}
    for job in enriched:
        for tag in job.tech_tags:
            tech_stats[tag] = tech_stats.get(tag, 0) + 1

    logger.info(f"[Enricher] 补全完成, 技术标签共 {len(tech_stats)} 种")

    return {
        "candidate_jobs": enriched,
        "tech_tag_stats": tech_stats,
        "status": "enriching",
    }


async def _enrich_single(
    job: JobPosting,
    llm: BaseChatModel,
    output_dir: str,
    index: int,
    total: int,
) -> JobPosting:
    """使用 LLM 补全单个岗位"""
    job_data = {
        "title": job.title,
        "company": job.company,
        "description": job.description,
    }

    prompt = ENRICH_PROMPT.format(job_json=json.dumps(job_data, ensure_ascii=False))

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    if settings.WRITE_LLM_OUTPUT_FILES:
        write_llm_output(
            output_dir,
            "enricher",
            str(response.content),
            meta={
                "index": index,
                "total": total,
                "title": job.title,
                "company": job.company,
            },
        )
    if settings.SHOW_LLM_OUTPUT:
        print_llm_output(
            f"Enricher AI Reply - {job.title[:24]}",
            str(response.content),
            max_chars=settings.LLM_OUTPUT_MAX_CHARS,
        )

    try:
        result = _parse_json_response(response.content)
        return JobPosting(
            title=job.title,
            company=job.company,
            description=job.description,
            location=job.location or result.get("location", ""),
            salary=job.salary or result.get("salary_cleaned", ""),
            tech_tags=result.get("tech_tags", []) or job.tech_tags,
            requirements=result.get("requirements", "") or job.requirements,
            source=job.source,
            job_url=job.job_url,
            experience_level=result.get("experience_level", "") or job.experience_level,
            confidence=job.confidence,
        )
    except (json.JSONDecodeError, KeyError):
        return job


def _parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
