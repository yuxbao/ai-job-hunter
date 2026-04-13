from __future__ import annotations

from urllib.parse import urlparse

from src.tools.data_adapter import DataAdapter
from src.utils.logger import logger


def _item_key(item: dict) -> tuple[str, str, str]:
    return (
        item.get("job_url", ""),
        item.get("title", ""),
        item.get("company", ""),
    )


def _is_detail_page(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if "zhipin.com" in host and "/job_detail/" in path:
        return True
    if "liepin.com" in host and ("/job/" in path or "/lptjob/" in path):
        return True
    if "zhaopin.com" in host and "jobdetail" in path:
        return True
    if "nowcoder.com" in host and ("/jobs/detail/" in path or "/feed/main/detail/" in path):
        return True
    return False


def _is_low_quality_page(item: dict) -> bool:
    title = item.get("title", "").lower()
    desc = item.get("description", "").lower()
    url = item.get("job_url", "")
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if "招聘网" in title or "汇聚众多行业名企" in desc or "公司名" in desc:
        return True
    if "liepin.com" in host and path.startswith("/zp") and "/job/" not in path:
        return True
    return False


def _quality_score(item: dict) -> tuple[int, int]:
    core_fields = ("title", "company", "source", "job_url")
    core_count = sum(bool(item.get(field)) for field in core_fields)
    score = core_count

    if _is_detail_page(item.get("job_url", "")):
        score += 3
    if item.get("location"):
        score += 1
    if item.get("salary"):
        score += 1
    if item.get("requirements") or item.get("description"):
        score += 1

    return score, core_count


def _merge(existing: list[dict], incoming: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    for item in existing + incoming:
        key = _item_key(item)
        if key in merged:
            merged[key].update(item)
        else:
            merged[key] = dict(item)
    return list(merged.values())


async def run(state: dict) -> dict:
    scraped_pages = state.get("scraped_pages", [])
    existing_gated = list(state.get("gated_results", []))
    target_count = state.get("target_count", 50)
    gate_limit = max(target_count * 3, target_count + 30)

    if not scraped_pages:
        logger.warning("[QualityGate] 没有待门控数据")
        return {"gated_results": existing_gated, "status": "filtering"}

    normalized = []
    for raw in scraped_pages:
        source = raw.get("source", "unknown")
        if raw.get("job_url") and raw.get("title"):
            normalized.append(DataAdapter.adapt(raw, "generic"))
        else:
            normalized.append(DataAdapter.adapt(raw, source))

    filtered = [
        item for item in normalized
        if item.get("job_url") and item.get("title") and not _is_low_quality_page(item)
    ]
    merged = _merge(existing_gated, filtered)
    merged.sort(key=_quality_score, reverse=True)
    gated_results = merged[:gate_limit]

    logger.info(
        f"[QualityGate] 原始 {len(scraped_pages)} 条, 保留 {len(filtered)} 条, "
        f"累计高质量候选 {len(gated_results)} 条"
    )

    return {"gated_results": gated_results, "status": "filtering"}
