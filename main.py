from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.graph.builder import build_graph
from src.state.job_search_state import JobSearchState
from src.utils.logger import logger


async def main():
    logger.info("=" * 50)
    logger.info("AI Job Hunter - 校招 AI Engineer 岗位自动搜索 Agent")
    logger.info(f"目标: 收集 {settings.TARGET_JOB_COUNT} 条岗位")
    logger.info(f"模式: {'Mock' if settings.MOCK_MODE else '真实搜索'}")
    logger.info("=" * 50)

    runtime = build_graph()

    initial_state: JobSearchState = {
        "target_count": settings.TARGET_JOB_COUNT,
        "job_type": "AI Engineer",
        "output_dir": settings.OUTPUT_DIR,
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
        "coverage_score": 0.0,
        "sources_used": [],
        "tech_tag_stats": {},
        "attempted_queries": [],
        "status": "planning",
    }

    try:
        result = await runtime.graph.ainvoke(initial_state)
    finally:
        await runtime.aclose()

    logger.info(f"\n最终状态: {result.get('status')}")
    logger.info(f"目标写入: {settings.TARGET_JOB_COUNT} 条")
    logger.info(f"实际写入: {len(result.get('final_jobs', []))} 条")
    logger.info(f"数据来源: {result.get('sources_used', [])}")
    logger.info(f"输出路径: {result.get('output_path', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
