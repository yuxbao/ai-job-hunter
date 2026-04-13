from __future__ import annotations

import asyncio

from src.sources.base_source import BaseSource
from src.tools.base import ToolResult
from src.utils.logger import logger


async def _search_one(
    query: str,
    site_name: str,
    source: BaseSource,
    semaphore: asyncio.Semaphore,
) -> tuple[str, str, ToolResult | None, Exception | None]:
    try:
        async with semaphore:
            search_query = source.build_query(query.split())
            result = await source.search(search_query)
            return site_name, query, result, None
    except Exception as exc:
        return site_name, query, None, exc


def _result_key(item: dict) -> tuple[str, str, str]:
    url = item.get("job_url", item.get("url", ""))
    title = item.get("title", "")
    company = item.get("company", "")
    source = item.get("source", "")
    query = item.get("query", "")
    description = item.get("description", item.get("content", ""))

    if url:
        return ("url", url, source)
    if title or company:
        return ("job", f"{title}|{company}", source)
    if query:
        return ("query", query, source)
    return (
        "desc",
        description[:200],
        source,
    )


def _merge_results(existing: list[dict], new_items: list[dict]) -> list[dict]:
    merged: list[dict] = []
    index_by_key: dict[tuple[str, str, str], int] = {}

    for item in existing + new_items:
        key = _result_key(item)
        if key in index_by_key:
            merged[index_by_key[key]].update(item)
            continue

        index_by_key[key] = len(merged)
        merged.append(dict(item))

    return merged


async def run(
    state: dict,
    sources: dict[str, BaseSource],
    max_concurrency: int = 4,
) -> dict:
    """搜索节点: 根据计划执行搜索"""
    plan = state.get("search_plan")
    if not plan:
        logger.error("[Searcher] 没有搜索计划")
        return {"raw_results": [], "status": "searching"}

    logger.info(f"[Searcher] 开始执行搜索 (iteration={state.get('iteration', 1)})")

    existing_results = list(state.get("scraped_pages") or state.get("raw_results", []))
    all_results = list(existing_results)
    failed = list(state.get("failed_sources", []))
    sources_used = list(state.get("sources_used", []))
    attempted_queries = list(state.get("attempted_queries", []))
    unique_queries = list(dict.fromkeys(plan.get("queries", [])))
    target_sites = list(dict.fromkeys(plan.get("target_sites", [])))
    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    tasks: list[asyncio.Task[tuple[str, str, ToolResult | None, Exception | None]]] = []

    for query in unique_queries:
        for site_name in target_sites:
            if site_name in failed:
                continue

            source = sources.get(site_name)
            if not source:
                logger.warning(f"[Searcher] 未知数据源: {site_name}")
                continue

            tasks.append(asyncio.create_task(_search_one(query, site_name, source, semaphore)))

    results = await asyncio.gather(*tasks) if tasks else []

    for site_name, query, result, error in results:
        if error is not None:
            logger.error(f"[Searcher] {site_name} 异常: {error}")
            if site_name not in failed:
                failed.append(site_name)
            continue

        if result and result.success and result.data:
            all_results = _merge_results(all_results, result.data)
            if site_name not in sources_used:
                sources_used.append(site_name)
            logger.info(
                f"[Searcher] {site_name} 搜索 '{query}' "
                f"获取 {len(result.data)} 条结果"
            )
            continue

        logger.warning(
            f"[Searcher] {site_name} 搜索 '{query}' 失败: "
            f"{result.error if result else '未知错误'}"
        )

    logger.info(f"[Searcher] 搜索完成, 共获取 {len(all_results)} 条原始结果")

    return {
        "raw_results": all_results,
        "failed_sources": failed,
        "sources_used": sources_used,
        "attempted_queries": list(dict.fromkeys(attempted_queries + unique_queries)),
        "status": "searching",
    }
