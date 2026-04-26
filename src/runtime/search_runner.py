from __future__ import annotations

from typing import Any, Awaitable, Callable

from config.settings import settings
from src.graph.builder import build_graph
from src.models.search_request import SearchRequest
from src.state.job_search_state import JobSearchState

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


def create_initial_state(
    request: SearchRequest,
    output_dir: str | None = None,
) -> JobSearchState:
    return {
        "target_count": request.target_count,
        "job_title": request.job_title,
        "requirements": request.requirements,
        "search_type": request.search_type,
        "cities": request.cities,
        "exclude_keywords": request.exclude_keywords,
        "search_brief": request.search_brief,
        "output_dir": output_dir or settings.OUTPUT_DIR,
        "search_plan": None,
        "iteration": 0,
        "max_iterations": settings.MAX_ITERATIONS,
        "raw_results": [],
        "scraped_pages": [],
        "gated_results": [],
        "candidate_jobs": [],
        "final_jobs": [],
        "failed_sources": [],
        "error_log": [],
        "search_warnings": [],
        "degraded_mode": False,
        "fallback_used": False,
        "coverage_score": 0.0,
        "sources_used": [],
        "tech_tag_stats": {},
        "attempted_queries": [],
        "status": "planning",
    }


async def run_search(
    request: SearchRequest,
    progress_callback: ProgressCallback | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    runtime = build_graph(progress_callback=progress_callback)
    initial_state = create_initial_state(request, output_dir=output_dir)

    try:
        return await runtime.graph.ainvoke(initial_state)
    finally:
        await runtime.aclose()
