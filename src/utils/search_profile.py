from __future__ import annotations

import re

SEARCH_TYPE_LABELS = {
    "campus": "校招",
    "intern": "日常实习",
    "all": "校招/实习",
}


def split_search_terms(*chunks: str, limit: int = 12) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    for chunk in chunks:
        if not chunk:
            continue

        raw = chunk.strip()
        if raw and raw not in seen:
            terms.append(raw)
            seen.add(raw)

        for token in re.split(r"[\s,，、/;；|]+", raw):
            token = token.strip()
            if len(token) < 2:
                continue
            if token in seen:
                continue
            seen.add(token)
            terms.append(token)

        compact = re.sub(r"(校招|校园招聘|应届生|实习生|实习|岗位|方向)$", "", raw).strip()
        if len(compact) >= 2 and compact not in seen:
            seen.add(compact)
            terms.append(compact)

    return terms[:limit]


def build_search_brief(
    job_title: str,
    requirements: str = "",
    search_type: str = "all",
    cities: list[str] | None = None,
    exclude_keywords: str = "",
) -> str:
    cities = cities or []
    parts = [
        f"岗位名称：{job_title}",
        f"求职类型：{SEARCH_TYPE_LABELS.get(search_type, search_type)}",
    ]

    if requirements:
        parts.append(f"岗位要求：{requirements}")
    if cities:
        parts.append(f"目标城市：{', '.join(cities)}")
    if exclude_keywords:
        parts.append(f"排除关键词：{exclude_keywords}")

    return "；".join(parts)
