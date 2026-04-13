from __future__ import annotations

import re
from urllib.parse import urlparse


class DataAdapter:
    """将不同来源的原始数据统一适配为内部标准格式"""

    @staticmethod
    def adapt(raw: dict, source: str) -> dict:
        adapter_map = {
            "boss_zhipin": DataAdapter._adapt_boss,
            "liepin": DataAdapter._adapt_liepin,
            "zhaopin": DataAdapter._adapt_zhaopin,
            "search_result": DataAdapter._adapt_search_result,
            "mock": DataAdapter._identity,
        }
        adapter = adapter_map.get(source, DataAdapter._adapt_generic)
        return adapter(raw)

    @staticmethod
    def _identity(raw: dict) -> dict:
        return raw

    @staticmethod
    def _adapt_boss(raw: dict) -> dict:
        source = DataAdapter._infer_source(raw.get("url", ""))
        title = raw.get("jobName", raw.get("title", ""))
        description = raw.get("jobDescription", raw.get("content", ""))
        return {
            "title": title,
            "company": raw.get("brandName", raw.get("company", ""))
            or DataAdapter._extract_company(title, description),
            "location": raw.get("cityName", raw.get("location", ""))
            or DataAdapter._extract_location(title, description),
            "salary": raw.get("salaryDesc", raw.get("salary", ""))
            or DataAdapter._extract_salary(title, description),
            "description": description,
            "source": source or "boss_zhipin",
            "job_url": raw.get("url", ""),
        }

    @staticmethod
    def _adapt_liepin(raw: dict) -> dict:
        title = raw.get("title", "")
        description = raw.get("jobDescription", raw.get("content", ""))
        source = DataAdapter._infer_source(raw.get("url", ""))
        return {
            "title": title,
            "company": raw.get("companyName", raw.get("company", ""))
            or DataAdapter._extract_company(title, description),
            "location": raw.get("city", raw.get("location", ""))
            or DataAdapter._extract_location(title, description),
            "salary": raw.get("salary", "")
            or DataAdapter._extract_salary(title, description),
            "description": description,
            "source": source or "liepin",
            "job_url": raw.get("url", ""),
        }

    @staticmethod
    def _adapt_zhaopin(raw: dict) -> dict:
        title = raw.get("jobName", raw.get("title", ""))
        description = raw.get("jobDescription", raw.get("content", ""))
        source = DataAdapter._infer_source(raw.get("url", ""))
        return {
            "title": title,
            "company": raw.get("companyName", raw.get("company", ""))
            or DataAdapter._extract_company(title, description),
            "location": raw.get("cityName", raw.get("location", ""))
            or DataAdapter._extract_location(title, description),
            "salary": raw.get("salary", "")
            or DataAdapter._extract_salary(title, description),
            "description": description,
            "source": source or "zhaopin",
            "job_url": raw.get("url", ""),
        }

    @staticmethod
    def _adapt_search_result(raw: dict) -> dict:
        """适配 Tavily 等搜索引擎返回的结果"""
        title = raw.get("title", "")
        description = raw.get("content", raw.get("snippet", ""))
        return {
            "title": title,
            "company": DataAdapter._extract_company(title, description),
            "location": DataAdapter._extract_location(title, description),
            "salary": DataAdapter._extract_salary(title, description),
            "description": description,
            "source": DataAdapter._infer_source(raw.get("url", "")) or "search",
            "job_url": raw.get("url", ""),
        }

    @staticmethod
    def _adapt_generic(raw: dict) -> dict:
        title = raw.get("title", "")
        description = raw.get("description", raw.get("content", ""))
        return {
            "title": title,
            "company": raw.get("company", "")
            or DataAdapter._extract_company(title, description),
            "location": raw.get("location", "")
            or DataAdapter._extract_location(title, description),
            "salary": raw.get("salary", "")
            or DataAdapter._extract_salary(title, description),
            "description": description,
            "source": raw.get("source")
            or DataAdapter._infer_source(raw.get("job_url", raw.get("url", "")))
            or "unknown",
            "job_url": raw.get("job_url", raw.get("url", "")),
        }

    @staticmethod
    def _infer_source(url: str) -> str:
        host = urlparse(url).netloc.lower()
        if "zhipin.com" in host:
            return "boss_zhipin"
        if "liepin.com" in host:
            return "liepin"
        if "zhaopin.com" in host:
            return "zhaopin"
        if "nowcoder.com" in host:
            return "nowcoder"
        if "51job.com" in host:
            return "51job"
        return ""

    @staticmethod
    def _extract_company(title: str, description: str) -> str:
        title = title or ""
        description = description or ""
        candidates: list[str] = []

        title_patterns = [
            r"_(?P<company>[^_]{2,30}?)(?:校招|实习)?_牛客网",
            r"^(?P<company>[^_【】\-\s]{2,20}?)(?:20\d{2}|26届|2026届)",
            r"(?P<company>[^·\n]{2,40}有限公司)·校园招聘",
            r"】-(?P<company>[^-]{2,30}?)招聘信息-猎聘",
            r"-\s*(?P<company>[^-_]{2,30})$",
        ]
        for pattern in title_patterns:
            match = re.search(pattern, title)
            if match:
                candidates.append(match.group("company").strip(" -_·"))

        content_patterns = [
            r"(?P<company>[^\n]{2,40}(?:有限公司|集团有限公司|股份有限公司|科技有限公司))·校园招聘",
            r"\n(?P<company>[^\n]{2,30}(?:有限公司|集团有限公司|股份有限公司|科技有限公司|集团|科技))\n",
            r"(?P<company>贝壳找房|米哈游|华为|美团|百度|腾讯|阿里巴巴|京东|快手|字节跳动)",
        ]
        for pattern in content_patterns:
            match = re.search(pattern, description)
            if match:
                candidates.append(match.group("company").strip(" -_·"))

        if not candidates:
            return ""
        best = max(candidates, key=len)
        return re.sub(r"^\s*招聘负责人\s*·\s*", "", best).strip(" -_·")

    @staticmethod
    def _extract_location(title: str, description: str) -> str:
        text = f"{title}\n{description}"
        city_pattern = (
            r"(?P<location>北京|上海|深圳|广州|杭州|成都|南京|苏州|武汉|西安|合肥|天津|厦门|长沙)"
        )
        for pattern in [city_pattern, rf"【\s*{city_pattern}\s*】"]:
            match = re.search(pattern, text)
            if match:
                return match.group("location").strip()
        return ""

    @staticmethod
    def _extract_salary(title: str, description: str) -> str:
        text = f"{title}\n{description}"
        match = re.search(r"(\d{1,2}-\d{1,2}k(?:·\d{1,2}薪)?)", text, re.I)
        if match:
            return match.group(1)
        if "薪资面议" in text:
            return "薪资面议"
        return ""
