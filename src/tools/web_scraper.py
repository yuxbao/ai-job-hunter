from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from src.tools.base import BaseTool, ToolResult


class WebScraperTool(BaseTool):
    """网页抓取工具: httpx -> Jina Reader fallback"""

    name = "web_scraper"
    description = "抓取网页内容并提取文本"

    async def execute(self, url: str) -> ToolResult:
        # 策略1: httpx 直接请求
        result = await self._scrape_httpx(url)
        if result.success and len(result.data) > 0:
            return result

        # 策略2: Jina Reader API
        result = await self._scrape_jina(url)
        if result.success:
            return result

        return ToolResult(success=False, error="All scraping methods failed")

    async def _scrape_httpx(self, url: str) -> ToolResult:
        """直接 HTTP 请求 + BeautifulSoup 解析"""
        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {resp.status_code}",
                    )

                soup = BeautifulSoup(resp.text, "html.parser")
                # 移除脚本和样式
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()

                text = soup.get_text(separator="\n", strip=True)
                # 截取前 5000 字符，避免过长
                text = text[:5000] if len(text) > 5000 else text

                return ToolResult(
                    success=True,
                    data=[{"url": url, "content": text}],
                    source="httpx",
                )
        except Exception as e:
            return ToolResult(success=False, error=f"httpx error: {e}")

    async def _scrape_jina(self, url: str) -> ToolResult:
        """Jina Reader API: https://r.jina.ai/{url}"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://r.jina.ai/{url}",
                    headers={"Accept": "text/plain"},
                )
                if resp.status_code == 200:
                    text = resp.text[:5000] if len(resp.text) > 5000 else resp.text
                    return ToolResult(
                        success=True,
                        data=[{"url": url, "content": text}],
                        source="jina",
                    )
                return ToolResult(
                    success=False,
                    error=f"Jina API error: {resp.status_code}",
                )
        except Exception as e:
            return ToolResult(success=False, error=f"Jina error: {e}")
