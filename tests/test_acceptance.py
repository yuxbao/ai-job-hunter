from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graph.nodes.evaluator import route_decision, run as evaluate
from src.graph.nodes.filter import _filter_batches
from src.graph.nodes.enricher import _enrich_candidates, _shortlist_candidates
from src.graph.nodes.filter import _rule_based_filter
from src.graph.nodes.quality_gate import run as gate_run
from src.graph.nodes.reporter import run as report
from src.models.job import JobPosting
from src.tools.data_adapter import DataAdapter


def make_job(index: int, source: str, confidence: float = 0.9) -> JobPosting:
    return JobPosting(
        title=f"AI Engineer {index}",
        company=f"Company {index}",
        location="Shanghai",
        salary="20k-30k",
        tech_tags=["LLM"],
        requirements="Python, LLM, Agent",
        source=source,
        job_url=f"https://example.com/{source}/{index}",
        confidence=confidence,
    )


@pytest.mark.anyio
async def test_evaluator_passes_acceptance_with_two_real_sources():
    jobs = [make_job(i, "boss_zhipin") for i in range(30)]
    jobs.extend(make_job(100 + i, "liepin") for i in range(25))
    state = {
        "candidate_jobs": jobs,
        "target_count": 50,
        "iteration": 1,
        "max_iterations": 5,
    }

    result = await evaluate(state)

    assert result["acceptance_passed"] is True
    assert len(result["final_jobs"]) == 50
    assert set(result["acceptance_summary"]["real_sources"]) == {
        "boss_zhipin",
        "liepin",
    }
    assert route_decision({**state, **result}) == "report"


@pytest.mark.anyio
async def test_evaluator_requests_more_search_before_max_iterations():
    jobs = [make_job(i, "boss_zhipin") for i in range(20)]
    state = {
        "candidate_jobs": jobs,
        "target_count": 50,
        "iteration": 2,
        "max_iterations": 5,
    }

    result = await evaluate(state)

    assert result["acceptance_passed"] is False
    assert "岗位数量不足" in result["acceptance_issues"][0]
    assert route_decision({**state, **result}) == "continue_search"


@pytest.mark.anyio
async def test_reporter_marks_failed_when_acceptance_not_met(tmp_path: Path):
    jobs = [make_job(i, "mock") for i in range(10)]
    state = {
        "final_jobs": jobs,
        "candidate_jobs": jobs,
        "target_count": 50,
        "tech_tag_stats": {"LLM": 10},
        "sources_used": ["mock"],
        "output_dir": str(tmp_path),
        "acceptance_passed": False,
        "acceptance_issues": ["岗位数量不足: 10/50", "真实招聘网站数量不足: 0/2"],
        "acceptance_summary": {
            "job_count": 10,
            "target_count": 50,
            "real_source_count": 0,
            "real_sources": [],
            "missing_core_fields": 0,
            "optional_field_coverage": {
                "location": 1.0,
                "salary": 1.0,
                "requirements": 1.0,
            },
        },
    }

    result = await report(state)

    assert result["status"] == "failed"
    summary = json.loads((tmp_path / "summary_latest.json").read_text())
    assert summary["acceptance_passed"] is False
    assert summary["status"] == "failed"
    assert summary["target_count"] == 50
    assert summary["candidate_count"] == 10
    assert summary["written_job_count"] == 10


def test_enricher_shortlists_near_target_count_with_buffer():
    jobs = [make_job(i, "boss_zhipin", confidence=1 - i * 0.01) for i in range(40)]
    jobs.extend(
        make_job(100 + i, "liepin", confidence=0.7 - i * 0.01)
        for i in range(35)
    )

    shortlisted = _shortlist_candidates(jobs, target_count=50, buffer_count=10)

    assert len(shortlisted) == 60
    assert {"boss_zhipin", "liepin"} <= {job.source for job in shortlisted}


def test_data_adapter_extracts_core_fields_from_search_result_like_pages():
    raw = {
        "title": "大模型算法工程师（博士专项）【2026届实习生】(J67072)_贝壳找房实习_牛客网",
        "url": "https://www.nowcoder.com/jobs/detail/387363",
        "content": "贝壳找房（北京）科技有限公司·校园招聘\n北京\n薪资面议\n岗位职责 负责大模型研发",
    }

    adapted = DataAdapter.adapt(raw, "liepin")

    assert adapted["company"] == "贝壳找房（北京）科技有限公司"
    assert adapted["location"] == "北京"
    assert adapted["salary"] == "薪资面议"
    assert adapted["source"] == "nowcoder"


def test_data_adapter_extracts_company_from_detail_title():
    raw = {
        "title": "【武汉 26校招-大模型与多模态算法工程师 (MJ001963)招聘】-东土科技招聘信息-猎聘",
        "url": "https://www.liepin.com/job/1980779469.shtml",
        "content": "武汉 20-30k",
    }

    adapted = DataAdapter.adapt(raw, "liepin")

    assert adapted["company"] == "东土科技"


def test_filter_excludes_low_quality_aggregate_pages():
    items = [
        {
            "title": "【LLM工具链实习生招聘网_2026年LLM工具链实习生招聘信息】-猎聘",
            "description": "汇聚众多行业名企 公司名",
            "job_url": "https://www.liepin.com/zpllmgjlsxsoyovh/",
        },
        {
            "title": "大模型算法工程师（博士专项）【2026届实习生】(J67072)_贝壳找房实习_牛客网",
            "description": "负责大模型研发，Agent，LLM，多模态",
            "job_url": "https://www.nowcoder.com/jobs/detail/387363",
        },
    ]

    filtered = _rule_based_filter(items)

    assert len(filtered) == 1
    assert "贝壳找房" in filtered[0]["title"]


@pytest.mark.anyio
async def test_quality_gate_keeps_detail_pages_and_dedupes():
    state = {
        "scraped_pages": [
            {
                "title": "【武汉 26校招-大模型与多模态算法工程师 (MJ001963)招聘】-东土科技招聘信息-猎聘",
                "company": "",
                "location": "武汉",
                "salary": "20-30k",
                "description": "大模型、多模态",
                "source": "liepin",
                "job_url": "https://www.liepin.com/job/1980779469.shtml",
            },
            {
                "title": "【LLM工具链实习生招聘网_2026年LLM工具链实习生招聘信息】-猎聘",
                "company": "广州市世际咨询服务有限公司",
                "location": "北京",
                "salary": "6-8k",
                "description": "汇聚众多行业名企 公司名",
                "source": "liepin",
                "job_url": "https://www.liepin.com/zpllmgjlsxsoyovh/",
            },
        ],
        "gated_results": [],
        "target_count": 50,
    }

    result = await gate_run(state)

    assert len(result["gated_results"]) == 1
    assert "东土科技" in result["gated_results"][0]["title"]


class FakeLLM:
    def __init__(self, delay: float = 0.0):
        self.delay = delay

    async def ainvoke(self, _messages):
        await asyncio.sleep(self.delay)
        return SimpleNamespace(
            content=json.dumps(
                {
                    "tech_tags": ["Python", "LLM"],
                    "requirements": "Python, LLM",
                    "experience_level": "校招",
                    "salary_cleaned": "20k-30k",
                },
                ensure_ascii=False,
            )
        )


import asyncio


@pytest.mark.anyio
async def test_enricher_processes_shortlist_with_controlled_concurrency(tmp_path: Path):
    jobs = [
        JobPosting(
            title=f"AI Engineer {i}",
            company=f"Company {i}",
            location="",
            salary="",
            tech_tags=[],
            requirements="",
            source="boss_zhipin",
            job_url=f"https://example.com/job/{i}",
            confidence=0.9,
        )
        for i in range(8)
    ]

    started = time.perf_counter()
    enriched = await _enrich_candidates(
        jobs,
        llm=FakeLLM(delay=0.1),
        output_dir=str(tmp_path),
        max_concurrency=4,
    )
    elapsed = time.perf_counter() - started

    assert len(enriched) == 8
    assert all(job.salary == "20k-30k" for job in enriched)
    assert elapsed < 0.5


class FakeFilterLLM:
    def __init__(self, delay: float = 0.0):
        self.delay = delay

    async def ainvoke(self, _messages):
        await asyncio.sleep(self.delay)
        return SimpleNamespace(
            content=json.dumps(
                [
                    {"index": 0, "is_relevant": True, "confidence": 0.9},
                    {"index": 1, "is_relevant": True, "confidence": 0.8},
                ],
                ensure_ascii=False,
            )
        )


@pytest.mark.anyio
async def test_filter_batches_run_with_controlled_concurrency(tmp_path: Path):
    items = [
        {
            "title": f"AI Engineer {i}",
            "company": f"Company {i}",
            "location": "Shanghai",
            "salary": "20k-30k",
            "source": "boss_zhipin",
            "job_url": f"https://example.com/{i}",
            "description": "LLM Agent",
        }
        for i in range(8)
    ]

    started = time.perf_counter()
    candidates = await _filter_batches(
        items,
        llm=FakeFilterLLM(delay=0.1),
        batch_size=2,
        total_batches=4,
        output_dir=str(tmp_path),
        max_concurrency=2,
    )
    elapsed = time.perf_counter() - started

    assert len(candidates) == 8
    assert elapsed < 0.35
