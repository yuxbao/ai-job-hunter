from __future__ import annotations

from src.sources.base_source import BaseSource
from src.tools.base import ToolResult
from src.tools.data_adapter import DataAdapter


class SiteSearchSource(BaseSource):
    """Generic recruiting site source backed by the search engine."""

    def __init__(self, name: str, domain: str, search_tool, priority: int = 10) -> None:
        self.name = name
        self.domain = domain
        self.search_tool = search_tool
        self.priority = priority

    def build_query(self, keywords: list[str]) -> str:
        kw = " ".join(keywords)
        return f"site:{self.domain} {kw} 招聘"

    async def search(self, query: str, page: int = 1) -> ToolResult:
        result = await self.search_tool.execute(
            query=query,
            max_results=15,
            include_domains=[self.domain],
        )
        if result.success and not result.data:
            result = await self.search_tool.execute(
                query=query.replace(f"site:{self.domain}", "").strip(),
                max_results=15,
                include_domains=[self.domain],
            )
        if not result.success:
            return result

        adapted = [DataAdapter.adapt(r, "search_result") for r in result.data]
        return ToolResult(success=True, data=adapted, source=self.name)
