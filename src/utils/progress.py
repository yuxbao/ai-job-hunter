from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


async def emit_progress(
    callback: ProgressCallback | None,
    payload: dict[str, Any],
) -> None:
    if callback is None:
        return

    result = callback(payload)
    if inspect.isawaitable(result):
        await result
