from __future__ import annotations

from typing import TypedDict, Literal

from src.models.job import JobPosting


class SearchPlan(TypedDict):
    queries: list[str]
    target_sites: list[str]
    strategy: str


class JobSearchState(TypedDict, total=False):
    # 输入
    target_count: int
    job_type: str

    # 规划阶段
    search_plan: SearchPlan | None
    iteration: int
    max_iterations: int

    # 搜索结果
    raw_results: list[dict]
    scraped_pages: list[dict]
    gated_results: list[dict]

    # 处理结果
    candidate_jobs: list[JobPosting]
    final_jobs: list[JobPosting]

    # 质量控制
    failed_sources: list[str]
    error_log: list[str]
    coverage_score: float
    acceptance_passed: bool
    acceptance_issues: list[str]
    acceptance_summary: dict

    # 元数据
    sources_used: list[str]
    tech_tag_stats: dict[str, int]
    attempted_queries: list[str]

    # 控制流
    status: Literal[
        "planning",
        "searching",
        "scraping",
        "filtering",
        "enriching",
        "evaluating",
        "reporting",
        "completed",
        "failed",
    ]

    # 输出
    output_path: str
