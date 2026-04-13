from __future__ import annotations

from abc import ABC, abstractmethod

from src.tools.base import ToolResult


class BaseSource(ABC):
    """数据源基类"""

    name: str
    priority: int  # 越小优先级越高

    @abstractmethod
    async def search(self, query: str, page: int = 1) -> ToolResult:
        """搜索岗位列表"""
        ...

    @abstractmethod
    def build_query(self, keywords: list[str]) -> str:
        """构建搜索 query"""
        ...
