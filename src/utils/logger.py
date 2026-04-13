from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.syntax import Syntax

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger("ai-job-hunter")
console = Console()


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}\n... [truncated]"


def print_llm_output(title: str, content: str, max_chars: int = 2000) -> None:
    """将 LLM 输出以更易读的方式打印到控制台。"""
    if not content:
        return

    text = _truncate_text(content.strip(), max_chars)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        renderable = text
    else:
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
        renderable = Syntax(pretty, "json", theme="monokai", word_wrap=True)

    console.print(Panel(renderable, title=title, border_style="cyan"))


def write_llm_output(
    output_dir: str,
    stage: str,
    content: str,
    meta: dict | None = None,
) -> str:
    """将 LLM 输出追加写入 output 目录，便于离线查看。"""
    path = Path(output_dir) / "llm_traces.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stage": stage,
        "content": content,
        "meta": meta or {},
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(path)
