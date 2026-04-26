from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.utils.search_profile import build_search_brief, split_search_terms


class SearchRequest(BaseModel):
    job_title: str = Field(description="目标岗位名称")
    requirements: str = Field(default="", description="补充要求")
    search_type: Literal["campus", "intern", "all"] = Field(
        default="all",
        description="校招/实习/都要",
    )
    cities: list[str] = Field(default_factory=list, description="目标城市")
    target_count: int = Field(default=50, ge=1, le=100, description="目标岗位数量")
    exclude_keywords: str = Field(default="", description="排除关键词")

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("job_title is required")
        return cleaned

    @property
    def search_brief(self) -> str:
        return build_search_brief(
            job_title=self.job_title,
            requirements=self.requirements,
            search_type=self.search_type,
            cities=self.cities,
            exclude_keywords=self.exclude_keywords,
        )

    @property
    def target_terms(self) -> list[str]:
        return split_search_terms(self.job_title, self.requirements)

    @property
    def exclusion_terms(self) -> list[str]:
        return split_search_terms(self.exclude_keywords, limit=8)
