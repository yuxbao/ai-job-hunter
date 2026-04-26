from __future__ import annotations

import json
import re

from config.settings import settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.prompts.planner_prompt import PLANNER_PROMPT
from src.state.job_search_state import JobSearchState, SearchPlan
from src.utils.search_profile import SEARCH_TYPE_LABELS, split_search_terms
from src.utils.logger import logger, print_llm_output, write_llm_output


def _dedupe_keep_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _build_default_queries(state: JobSearchState) -> list[str]:
    job_title = state.get("job_title", "岗位").strip()
    search_type = state.get("search_type", "all")
    requirements = state.get("requirements", "")
    cities = state.get("cities", [])
    type_terms = {
        "campus": ["校招", "校园招聘", "应届生", "2026届"],
        "intern": ["实习", "实习生", "日常实习"],
        "all": ["校招", "实习", "应届生"],
    }.get(search_type, ["校招", "实习"])
    extra_terms = split_search_terms(requirements, limit=4)

    queries = [f"{job_title} {term}" for term in type_terms[:3]]
    queries.extend(f"{job_title} {term}" for term in extra_terms[:2])

    for city in cities[:2]:
        queries.append(f"{job_title} {city} {type_terms[0]}")
        if extra_terms:
            queries.append(f"{job_title} {city} {extra_terms[0]} {type_terms[0]}")

    if extra_terms:
        queries.append(
            f"{job_title} {extra_terms[0]} {SEARCH_TYPE_LABELS.get(search_type, '')}".strip()
        )
    queries.append(job_title)

    cleaned = [
        re.sub(r"\s+", " ", query).strip()
        for query in queries
        if query.strip()
    ]
    return _dedupe_keep_order(cleaned)[:8]


async def run(state: JobSearchState, llm: BaseChatModel | None = None) -> dict:
    """规划节点: 使用 LLM 生成搜索策略，LLM 不可用时使用默认策略"""
    logger.info("[Planner] 正在规划搜索策略...")

    default_plan: SearchPlan = {
        "queries": _build_default_queries(state),
        "target_sites": ["mock"],
        "strategy": "默认策略: 基于岗位名称、求职类型、城市和补充要求生成组合查询",
    }

    # 根据可用数据源调整 target_sites
    if settings.MOCK_MODE:
        default_plan["target_sites"] = ["mock"]
    else:
        default_plan["target_sites"] = ["boss_zhipin", "liepin", "zhaopin", "nowcoder", "51job"]

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
            target_count=state.get("target_count", 50),
            search_brief=state.get("search_brief", state.get("job_title", "")),
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
