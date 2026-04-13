from __future__ import annotations

from src.models.job import JobPosting
from src.state.job_search_state import JobSearchState
from src.utils.logger import logger


REQUIRED_SOURCE_COUNT = 2
CORE_FIELDS = ("title", "company", "source", "job_url")


def _job_key(job: JobPosting) -> tuple[str, str, str]:
    return (job.job_url, job.title, job.company)


def _is_real_source(source: str) -> bool:
    return bool(source and source not in {"mock", "search", "unknown"})


def _select_final_jobs(unique_jobs: list[JobPosting], target: int) -> list[JobPosting]:
    if len(unique_jobs) <= target:
        return unique_jobs

    selected: list[JobPosting] = []
    selected_keys: set[tuple[str, str, str]] = set()
    real_sources: set[str] = set()

    for job in unique_jobs:
        if _is_real_source(job.source):
            real_sources.add(job.source)

    if len(real_sources) >= REQUIRED_SOURCE_COUNT:
        seeded_sources: set[str] = set()
        for job in unique_jobs:
            if not _is_real_source(job.source) or job.source in seeded_sources:
                continue
            selected.append(job)
            selected_keys.add(_job_key(job))
            seeded_sources.add(job.source)
            if len(seeded_sources) >= REQUIRED_SOURCE_COUNT:
                break

    for job in unique_jobs:
        key = _job_key(job)
        if key in selected_keys:
            continue
        selected.append(job)
        selected_keys.add(key)
        if len(selected) >= target:
            break

    return selected[:target]


def _evaluate_acceptance(final_jobs: list[JobPosting], target: int) -> tuple[bool, list[str], dict]:
    real_sources = sorted({job.source for job in final_jobs if _is_real_source(job.source)})
    missing_core_fields = sum(
        1
        for job in final_jobs
        if any(not getattr(job, field) for field in CORE_FIELDS)
    )
    optional_field_coverage = {
        field: (
            sum(1 for job in final_jobs if getattr(job, field))
            / len(final_jobs)
            if final_jobs
            else 0.0
        )
        for field in ("location", "salary", "requirements")
    }

    issues: list[str] = []
    if len(final_jobs) < target:
        issues.append(f"岗位数量不足: {len(final_jobs)}/{target}")
    if len(real_sources) < REQUIRED_SOURCE_COUNT:
        issues.append(
            f"真实招聘网站数量不足: {len(real_sources)}/{REQUIRED_SOURCE_COUNT}"
        )
    if missing_core_fields:
        issues.append(f"存在 {missing_core_fields} 条岗位缺少核心字段")

    summary = {
        "job_count": len(final_jobs),
        "target_count": target,
        "real_source_count": len(real_sources),
        "real_sources": real_sources,
        "missing_core_fields": missing_core_fields,
        "optional_field_coverage": optional_field_coverage,
    }
    return not issues, issues, summary


async def run(state: dict) -> dict:
    """评估节点: 评估当前结果质量，去重"""
    candidate_jobs: list[JobPosting] = state.get("candidate_jobs", [])
    target = state.get("target_count", 50)
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 5)

    logger.info(
        f"[Evaluator] 评估第 {iteration} 轮: "
        f"候选 {len(candidate_jobs)} 条, 目标 {target} 条"
    )

    # 去重
    seen = set()
    unique = []
    for job in candidate_jobs:
        key = f"{job.title}|{job.company}"
        if key not in seen:
            seen.add(key)
            unique.append(job)

    # 优先保留核心字段完整、置信度高的岗位
    unique.sort(
        key=lambda j: (
            sum(bool(getattr(j, field)) for field in CORE_FIELDS),
            j.confidence,
        ),
        reverse=True,
    )

    # 截取目标数量，并尽量保证最终结果包含至少 2 个真实来源
    final_jobs = _select_final_jobs(unique, target)
    coverage = min(len(final_jobs) / target, 1.0)
    acceptance_passed, acceptance_issues, acceptance_summary = _evaluate_acceptance(
        final_jobs,
        target,
    )

    logger.info(
        f"[Evaluator] 去重后 {len(unique)} 条, "
        f"覆盖率 {coverage:.0%}"
    )
    if acceptance_passed:
        logger.info("[Evaluator] 验收标准已满足")
    else:
        logger.info(f"[Evaluator] 验收未通过: {'; '.join(acceptance_issues)}")

    return {
        "final_jobs": final_jobs,
        "coverage_score": coverage,
        "acceptance_passed": acceptance_passed,
        "acceptance_issues": acceptance_issues,
        "acceptance_summary": acceptance_summary,
        "status": "evaluating",
    }


def route_decision(state: JobSearchState) -> str:
    """条件路由: 决定是继续搜索还是完成"""
    jobs = state.get("final_jobs", [])
    summary = state.get("acceptance_summary", {})
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 5)

    if state.get("acceptance_passed", False):
        logger.info(
            f"[Evaluator] 满足条件 ({len(jobs)}/{summary.get('target_count', 50)}, "
            f"来源: {summary.get('real_sources', [])}), 进入汇总阶段"
        )
        return "report"

    if iteration >= max_iter:
        logger.info(
            f"[Evaluator] 达到最大迭代次数 ({max_iter}), "
            f"当前 {len(jobs)} 条, 输出失败报告"
        )
        return "report"

    logger.info(
        f"[Evaluator] 验收未完成，继续搜索: "
        f"{state.get('acceptance_issues', [])}"
    )
    return "continue_search"
