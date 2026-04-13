from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graph.nodes.searcher import run
from src.sources.base_source import BaseSource
from src.tools.base import ToolResult


class FakeSource(BaseSource):
    name = "fake"
    priority = 1

    def __init__(self, name: str, delay: float = 0.0, fail: bool = False):
        self.name = name
        self.delay = delay
        self.fail = fail
        self.calls: list[str] = []

    def build_query(self, keywords: list[str]) -> str:
        return f"{self.name}:{' '.join(keywords)}"

    async def search(self, query: str, page: int = 1) -> ToolResult:
        self.calls.append(query)
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError(f"{self.name} boom")
        return ToolResult(
            success=True,
            data=[{"query": query, "source": self.name}],
            source=self.name,
        )

@pytest.mark.anyio
async def test_searcher_runs_queries_in_parallel():
    sources = {
        "boss": FakeSource("boss", delay=0.2),
        "liepin": FakeSource("liepin", delay=0.2),
    }
    state = {
        "search_plan": {
            "queries": ["ai engineer", "llm engineer"],
            "target_sites": ["boss", "liepin"],
            "strategy": "test",
        },
        "failed_sources": [],
        "sources_used": [],
    }

    started = time.perf_counter()
    result = await run(state, sources, max_concurrency=4)
    elapsed = time.perf_counter() - started

    assert len(result["raw_results"]) == 4
    assert elapsed < 0.45


@pytest.mark.anyio
async def test_searcher_deduplicates_queries_before_searching():
    source = FakeSource("boss")
    state = {
        "search_plan": {
            "queries": ["ai engineer", "ai engineer", "llm engineer"],
            "target_sites": ["boss", "boss"],
            "strategy": "test",
        },
        "failed_sources": [],
        "sources_used": [],
    }

    result = await run(state, {"boss": source}, max_concurrency=2)

    assert len(result["raw_results"]) == 2
    assert source.calls == ["boss:ai engineer", "boss:llm engineer"]


@pytest.mark.anyio
async def test_searcher_marks_failed_sources_when_task_raises():
    ok_source = FakeSource("boss")
    bad_source = FakeSource("liepin", fail=True)
    state = {
        "search_plan": {
            "queries": ["ai engineer"],
            "target_sites": ["boss", "liepin"],
            "strategy": "test",
        },
        "failed_sources": [],
        "sources_used": [],
    }

    result = await run(
        state,
        {"boss": ok_source, "liepin": bad_source},
        max_concurrency=2,
    )

    assert len(result["raw_results"]) == 1
    assert result["sources_used"] == ["boss"]
    assert result["failed_sources"] == ["liepin"]


@pytest.mark.anyio
async def test_searcher_accumulates_previous_scraped_results():
    source = FakeSource("boss")
    state = {
        "search_plan": {
            "queries": ["llm engineer"],
            "target_sites": ["boss"],
            "strategy": "test",
        },
        "failed_sources": [],
        "sources_used": [],
        "scraped_pages": [
            {
                "title": "existing job",
                "company": "old company",
                "source": "boss",
                "job_url": "https://example.com/existing",
                "description": "already scraped",
            }
        ],
    }

    result = await run(state, {"boss": source}, max_concurrency=1)

    assert len(result["raw_results"]) == 2
    assert result["raw_results"][0]["description"] == "already scraped"
