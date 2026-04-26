from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from pydantic import ValidationError
from src.models.search_request import SearchRequest
from src.runtime.search_runner import run_search
from src.utils.logger import logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通用校招/实习求职助手")
    parser.add_argument("--job-title", help="目标岗位名称（不传时进入交互式输入）")
    parser.add_argument("--requirements", default="", help="补充要求")
    parser.add_argument(
        "--search-type",
        default="all",
        choices=["campus", "intern", "all"],
        help="求职类型",
    )
    parser.add_argument("--cities", default="", help="城市，使用逗号分隔")
    parser.add_argument("--target-count", type=int, default=settings.TARGET_JOB_COUNT)
    parser.add_argument("--exclude-keywords", default="", help="排除关键词")
    return parser


def _split_cities(cities: str) -> list[str]:
    return [city.strip() for city in cities.replace("，", ",").replace("、", ",").split(",") if city.strip()]


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return default
    return value or default


def _request_from_args(args: argparse.Namespace) -> SearchRequest:
    job_title = args.job_title
    if not job_title:
        logger.info("未检测到 --job-title，进入交互式 CLI。只需要输入岗位名称即可开始。")
        job_title = _prompt("岗位名称（必填）")
        if not job_title:
            logger.error("必须先输入岗位名称，才能开始执行搜索。示例：python main.py --job-title \"后端开发实习生\"")
            raise SystemExit(2)

        args.requirements = _prompt("岗位要求（可选）", args.requirements)
        args.search_type = _prompt("求职类型 campus/intern/all", args.search_type)
        args.cities = _prompt("城市，逗号分隔（可选）", args.cities)
        target_count = _prompt("目标数量", str(args.target_count))
        args.exclude_keywords = _prompt("排除关键词（可选）", args.exclude_keywords)
        try:
            args.target_count = int(target_count)
        except ValueError:
            logger.error("目标数量必须是数字。")
            raise SystemExit(2) from None

    try:
        return SearchRequest(
            job_title=job_title,
            requirements=args.requirements,
            search_type=args.search_type,
            cities=_split_cities(args.cities),
            target_count=args.target_count,
            exclude_keywords=args.exclude_keywords,
        )
    except ValidationError as exc:
        logger.error(f"搜索参数无效：{exc}")
        raise SystemExit(2) from exc


async def main():
    args = _build_parser().parse_args()
    request = _request_from_args(args)

    logger.info("=" * 50)
    logger.info("Job Hunter - 通用校招/实习求职助手")
    logger.info(f"岗位: {request.job_title}")
    logger.info(f"目标: 收集 {request.target_count} 条岗位")
    logger.info(f"模式: {'Mock' if settings.MOCK_MODE else '真实搜索'}")
    logger.info("=" * 50)

    result = await run_search(request)

    logger.info(f"\n最终状态: {result.get('status')}")
    logger.info(f"目标写入: {request.target_count} 条")
    logger.info(f"实际写入: {len(result.get('final_jobs', []))} 条")
    logger.info(f"数据来源: {result.get('sources_used', [])}")
    logger.info(f"输出路径: {result.get('output_path', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
