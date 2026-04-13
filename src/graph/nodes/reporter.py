from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
from rich.console import Console
from rich.table import Table

from src.models.job import JobPosting
from src.utils.logger import logger


async def run(state: dict) -> dict:
    """输出节点: 生成 JSON/CSV 报告和技能画像"""
    jobs: list[JobPosting] = state.get("final_jobs", [])
    target_count = state.get("target_count", 50)
    candidate_count = len(state.get("candidate_jobs", []))
    tech_stats: dict[str, int] = state.get("tech_tag_stats", {})
    sources_used = state.get("sources_used", [])
    output_dir = state.get("output_dir", "output")
    acceptance_passed = state.get("acceptance_passed", False)
    acceptance_issues = state.get("acceptance_issues", [])
    acceptance_summary = state.get("acceptance_summary", {})

    logger.info(
        f"[Reporter] 生成报告: 候选池 {candidate_count} 条, "
        f"目标写入 {target_count} 条, 实际写入 {len(jobs)} 条"
    )

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 导出 JSON
    json_path = os.path.join(output_dir, f"jobs_{timestamp}.json")
    jobs_data = [j.model_dump() for j in jobs]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, ensure_ascii=False, indent=2)

    # 导出 CSV
    csv_path = os.path.join(output_dir, f"jobs_{timestamp}.csv")
    df = pd.DataFrame([j.to_csv_dict() for j in jobs])
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 同时保存一份 latest
    latest_json = os.path.join(output_dir, "jobs_latest.json")
    latest_csv = os.path.join(output_dir, "jobs_latest.csv")
    llm_trace_path = os.path.join(output_dir, "llm_traces.jsonl")
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, ensure_ascii=False, indent=2)
    df.to_csv(latest_csv, index=False, encoding="utf-8-sig")

    summary = {
        "status": "completed" if acceptance_passed else "failed",
        "acceptance_passed": acceptance_passed,
        "acceptance_issues": acceptance_issues,
        "acceptance_summary": acceptance_summary,
        "target_count": target_count,
        "candidate_count": candidate_count,
        "written_job_count": len(jobs),
        "sources_used": sources_used,
        "json_path": json_path,
        "csv_path": csv_path,
        "llm_trace_path": llm_trace_path if os.path.exists(llm_trace_path) else "",
    }
    summary_path = os.path.join(output_dir, f"summary_{timestamp}.json")
    latest_summary = os.path.join(output_dir, "summary_latest.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(latest_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 打印报告
    _print_report(
        jobs,
        target_count,
        candidate_count,
        tech_stats,
        sources_used,
        json_path,
        csv_path,
        llm_trace_path if os.path.exists(llm_trace_path) else "",
        acceptance_passed,
        acceptance_issues,
        acceptance_summary,
    )

    return {
        "status": "completed" if acceptance_passed else "failed",
        "output_path": json_path,
        "summary_path": summary_path,
    }


def _print_report(
    jobs: list[JobPosting],
    target_count: int,
    candidate_count: int,
    tech_stats: dict[str, int],
    sources_used: list[str],
    json_path: str,
    csv_path: str,
    llm_trace_path: str,
    acceptance_passed: bool,
    acceptance_issues: list[str],
    acceptance_summary: dict,
):
    """打印报告到控制台"""
    console = Console()

    # 标题
    console.print("\n[bold green]===== AI Engineer 校招岗位搜索报告 =====[/bold green]\n")

    # 汇总信息
    console.print(f"[bold]候选池:[/bold] {candidate_count} 条岗位")
    console.print(f"[bold]目标写入:[/bold] {target_count} 条岗位")
    console.print(f"[bold]实际写入:[/bold] {len(jobs)} 条岗位")
    console.print(f"[bold]数据源:[/bold] {', '.join(sources_used)}")
    console.print(f"[bold]输出:[/bold] {json_path}")
    console.print(f"[bold]输出:[/bold] {csv_path}")
    if llm_trace_path:
        console.print(f"[bold]LLM日志:[/bold] {llm_trace_path}")
    console.print(
        f"[bold]验收:[/bold] {'通过' if acceptance_passed else '未通过'}"
    )
    if acceptance_summary:
        console.print(
            f"[bold]真实网站:[/bold] "
            f"{', '.join(acceptance_summary.get('real_sources', [])) or '-'}"
        )
    if acceptance_issues:
        console.print(f"[bold red]问题:[/bold red] {'; '.join(acceptance_issues)}")

    # 岗位列表
    table = Table(title="岗位列表", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("岗位", style="cyan", max_width=30)
    table.add_column("公司", style="green", max_width=15)
    table.add_column("地点", max_width=8)
    table.add_column("薪资", style="yellow", max_width=12)
    table.add_column("技术栈", style="magenta", max_width=30)
    table.add_column("来源", style="dim", max_width=10)

    for i, job in enumerate(jobs, 1):
        tech_str = ", ".join(job.tech_tags[:5]) if job.tech_tags else "-"
        table.add_row(
            str(i),
            job.title[:28],
            job.company[:13],
            job.location[:6],
            job.salary[:10],
            tech_str[:28],
            job.source[:8],
        )

    console.print(table)

    # 技术栈统计
    if tech_stats:
        console.print("\n[bold]===== 技术栈热度 Top 20 =====[/bold]\n")
        sorted_tags = sorted(tech_stats.items(), key=lambda x: x[1], reverse=True)[:20]
        for tag, count in sorted_tags:
            bar = "█" * min(count, 30)
            console.print(f"  {tag:20s} {bar} {count}")

    # 技能画像
    console.print("\n[bold]===== AI Engineer 校招技能画像 =====[/bold]\n")
    profile = _generate_skill_profile(jobs, tech_stats)
    console.print(profile)

    title = "===== 搜索完成 =====" if acceptance_passed else "===== 搜索未达验收标准 ====="
    style = "bold green" if acceptance_passed else "bold red"
    console.print(f"\n[{style}]{title}[/{style}]\n")


def _generate_skill_profile(jobs: list[JobPosting], tech_stats: dict[str, int]) -> str:
    """生成技能画像摘要"""
    if not tech_stats:
        return "暂无数据"

    top_tags = sorted(tech_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    tags_str = ", ".join([f"{tag}({count})" for tag, count in top_tags])

    locations = {}
    for j in jobs:
        if j.location:
            locations[j.location] = locations.get(j.location, 0) + 1
    top_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]
    loc_str = ", ".join([f"{loc}({cnt})" for loc, cnt in top_locations])

    companies = {}
    for j in jobs:
        if j.company:
            companies[j.company] = companies.get(j.company, 0) + 1
    top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
    comp_str = ", ".join([f"{c}({cnt})" for c, cnt in top_companies])

    return (
        f"  核心技能: {tags_str}\n"
        f"  热门城市: {loc_str}\n"
        f"  热门公司: {comp_str}\n"
        f"  岗位总数: {len(jobs)}"
    )
