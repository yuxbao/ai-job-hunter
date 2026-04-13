from __future__ import annotations

import httpx

from src.tools.base import BaseTool, ToolResult


class SearchEngineTool(BaseTool):
    """通过 Tavily Search API 搜索招聘信息"""

    name = "search_engine"
    description = "使用搜索引擎搜索招聘信息"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={"User-Agent": "ai-job-hunter/0.1"},
        )

    async def execute(
        self,
        query: str,
        max_results: int = 10,
        include_domains: list[str] | None = None,
    ) -> ToolResult:
        if not self.api_key:
            return ToolResult(success=False, error="TAVILY_API_KEY not configured")

        try:
            resp = await self._client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "advanced",
                    "include_domains": include_domains
                    or [
                        "zhipin.com",
                        "liepin.com",
                        "zhaopin.com",
                        "51job.com",
                        "linkedin.com",
                        "nowcoder.com",
                    ],
                },
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                return ToolResult(success=True, data=results, source="tavily")
            return ToolResult(
                success=False,
                error=f"Tavily API error: {resp.status_code} {resp.text[:200]}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Search error: {e}")

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            resp = await self._client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": "test",
                    "max_results": 1,
                },
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
