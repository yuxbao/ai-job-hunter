from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """标准化岗位数据模型"""

    title: str = Field(description="岗位名称")
    company: str = Field(description="公司名称")
    description: str = Field(default="", description="岗位描述原文")
    location: str = Field(default="", description="工作地点")
    salary: str = Field(default="", description="薪资范围")
    tech_tags: list[str] = Field(default_factory=list, description="技术栈标签")
    requirements: str = Field(default="", description="岗位要求摘要")
    source: str = Field(description="数据来源网站")
    job_url: str = Field(default="", description="岗位链接")
    experience_level: str = Field(default="", description="经验要求 (校招/实习/应届)")
    confidence: float = Field(default=1.0, description="数据可信度 0-1")

    def to_csv_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "tech_tags": ", ".join(self.tech_tags),
            "requirements": self.requirements,
            "source": self.source,
            "job_url": self.job_url,
        }
