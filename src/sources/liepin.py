from __future__ import annotations

from src.sources.base_source import BaseSource
from src.tools.base import ToolResult
from src.tools.data_adapter import DataAdapter


class LiepinSource(BaseSource):
    """猎聘数据源 - 通过搜索引擎间接获取"""

    name = "liepin"
    priority = 2

    def __init__(self, search_tool):
        self.search_tool = search_tool

    def build_query(self, keywords: list[str]) -> str:
        kw = " ".join(keywords)
        return f"site:liepin.com {kw} 校招 2026届"

    async def search(self, query: str, page: int = 1) -> ToolResult:
        result = await self.search_tool.execute(
            query=query,
            max_results=15,
            include_domains=["liepin.com"],
        )
        if result.success and not result.data:
            result = await self.search_tool.execute(query=query, max_results=15)
        if not result.success:
            return result

        adapted = [DataAdapter.adapt(r, "liepin") for r in result.data]
        return ToolResult(success=True, data=adapted, source=self.name)
