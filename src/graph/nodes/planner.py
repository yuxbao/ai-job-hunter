from __future__ import annotations

import json

from config.settings import settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.prompts.planner_prompt import PLANNER_PROMPT
from src.state.job_search_state import JobSearchState, SearchPlan
from src.utils.logger import logger, print_llm_output, write_llm_output


def _dedupe_keep_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


async def run(state: JobSearchState, llm: BaseChatModel | None = None) -> dict:
    """规划节点: 使用 LLM 生成搜索策略，LLM 不可用时使用默认策略"""
    logger.info("[Planner] 正在规划搜索策略...")

    default_plan: SearchPlan = {
        "queries": [
            "AI算法工程师 校招",
            "机器学习工程师 2026届",
            "大模型工程师 校园招聘",
            "LLM工程师 应届生",
            "算法工程师 校招 深度学习",
            "NLP工程师 校招",
            "计算机视觉 算法 校招",
        ],
        "target_sites": ["mock"],
        "strategy": "默认策略: 多关键词覆盖主流招聘网站",
    }

    # 根据可用数据源调整 target_sites
    if settings.MOCK_MODE:
        default_plan["target_sites"] = ["mock"]
    else:
        default_plan["target_sites"] = ["boss_zhipin", "liepin", "zhaopin"]

    if llm is None:
        logger.info("[Planner] LLM 不可用，使用默认策略")
        attempted = set(state.get("attempted_queries", []))
        queries = [q for q in default_plan["queries"] if q not in attempted]
        if not queries:
            queries = default_plan["queries"][:3]
        return {
            "search_plan": {**default_plan, "queries": queries},
            "iteration": state.get("iteration", 0) + 1,
            "status": "planning",
        }

    try:
        prompt = PLANNER_PROMPT.format(
            job_type=state.get("job_type", "AI Engineer"),
            target_count=state.get("target_count", 50),
            existing_count=len(state.get("final_jobs", [])),
            sources_used=", ".join(state.get("sources_used", [])),
            failed_sources=", ".join(state.get("failed_sources", [])),
            iteration=state.get("iteration", 0) + 1,
            max_iterations=state.get("max_iterations", 5),
        )

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        output_dir = state.get("output_dir", settings.OUTPUT_DIR)
        if settings.WRITE_LLM_OUTPUT_FILES:
            write_llm_output(
                output_dir,
                "planner",
                str(response.content),
                meta={"iteration": state.get("iteration", 0) + 1},
            )
        if settings.SHOW_LLM_OUTPUT:
            print_llm_output(
                "Planner AI Reply",
                str(response.content),
                max_chars=settings.LLM_OUTPUT_MAX_CHARS,
            )

        plan = _parse_json_response(response.content)
        search_plan: SearchPlan = {
            "queries": plan.get("queries", default_plan["queries"]),
            "target_sites": plan.get("target_sites", default_plan["target_sites"]),
            "strategy": plan.get("strategy", ""),
        }
    except Exception as e:
        logger.warning(f"[Planner] LLM 调用失败，使用默认策略: {e}")
        search_plan = default_plan

    attempted = set(state.get("attempted_queries", []))
    available_queries = [q for q in _dedupe_keep_order(search_plan["queries"]) if q not in attempted]
    if not available_queries:
        available_queries = [
            q for q in _dedupe_keep_order(default_plan["queries"])
            if q not in attempted
        ] or default_plan["queries"][:3]
    search_plan["queries"] = available_queries

    logger.info(
        f"[Planner] 生成 {len(search_plan['queries'])} 个搜索词, "
        f"目标网站: {search_plan['target_sites']}"
    )

    return {
        "search_plan": search_plan,
        "iteration": state.get("iteration", 0) + 1,
        "status": "planning",
    }


def _parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    # 尝试直接解析
    text = text.strip()
    if text.startswith("```"):
        # 去掉 markdown 代码块
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
