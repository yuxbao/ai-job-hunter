from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    success: bool
    data: list[dict] = field(default_factory=list)
    error: str | None = None
    source: str | None = None


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...

    async def health_check(self) -> bool:
        return True

    async def aclose(self) -> None:
        """释放工具持有的异步资源。"""
        return None
