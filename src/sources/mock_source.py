from __future__ import annotations

import random

from src.sources.base_source import BaseSource
from src.tools.base import ToolResult

MOCK_JOBS = [
    {
        "title": "后端开发工程师（2026届校招）",
        "company": "字节跳动",
        "location": "北京",
        "salary": "25k-40k",
        "tech_tags": ["Java", "Go", "微服务", "MySQL"],
        "requirements": "熟悉 Java 或 Go，理解分布式系统和数据库基础",
        "source": "mock",
        "job_url": "https://mock.bytedance.com/jobs/1",
        "description": "参与核心业务后台服务开发，负责接口设计、性能优化和系统稳定性建设。",
    },
    {
        "title": "后端开发实习生",
        "company": "美团",
        "location": "上海",
        "salary": "250/天",
        "tech_tags": ["Java", "Spring Boot", "Redis", "SQL"],
        "requirements": "有 Java 后端项目经验，熟悉常见 Web 开发框架",
        "source": "mock",
        "job_url": "https://mock.meituan.com/jobs/2",
        "description": "协助业务服务开发与维护，参与接口联调和线上问题排查。",
    },
    {
        "title": "前端开发工程师（校招）",
        "company": "阿里巴巴",
        "location": "杭州",
        "salary": "24k-38k",
        "tech_tags": ["TypeScript", "React", "工程化", "性能优化"],
        "requirements": "熟悉前端基础，具备 React 或 Vue 项目经验",
        "source": "mock",
        "job_url": "https://mock.alibaba.com/jobs/3",
        "description": "负责业务前端页面和中后台系统开发，提升交互体验和工程效率。",
    },
    {
        "title": "前端开发实习生",
        "company": "小红书",
        "location": "上海",
        "salary": "280/天",
        "tech_tags": ["React", "TypeScript", "CSS", "Node.js"],
        "requirements": "熟悉 React 和现代前端工程化工具链",
        "source": "mock",
        "job_url": "https://mock.xiaohongshu.com/jobs/4",
        "description": "参与增长产品前端开发，负责页面实现和组件抽象。",
    },
    {
        "title": "产品经理（2026届校招）",
        "company": "腾讯",
        "location": "深圳",
        "salary": "20k-32k",
        "tech_tags": ["需求分析", "原型设计", "数据分析", "跨团队协作"],
        "requirements": "逻辑清晰，有产品实习或校园项目经验优先",
        "source": "mock",
        "job_url": "https://mock.tencent.com/jobs/5",
        "description": "负责用户需求分析、产品方案设计和上线推进，协同研发与设计团队落地功能。",
    },
    {
        "title": "产品经理实习生",
        "company": "B站",
        "location": "上海",
        "salary": "230/天",
        "tech_tags": ["竞品分析", "PRD", "数据分析", "用户研究"],
        "requirements": "有良好的表达能力和数据敏感度，熟悉互联网产品流程",
        "source": "mock",
        "job_url": "https://mock.bilibili.com/jobs/6",
        "description": "参与社区产品需求梳理、数据复盘和版本迭代。",
    },
    {
        "title": "数据分析师（校招）",
        "company": "拼多多",
        "location": "上海",
        "salary": "22k-35k",
        "tech_tags": ["SQL", "Python", "Tableau", "A/B测试"],
        "requirements": "熟练使用 SQL，具备数据分析和可视化能力",
        "source": "mock",
        "job_url": "https://mock.pdd.com/jobs/7",
        "description": "支持业务数据洞察、实验分析和用户增长策略评估。",
    },
    {
        "title": "数据分析实习生",
        "company": "滴滴",
        "location": "北京",
        "salary": "250/天",
        "tech_tags": ["SQL", "Excel", "Python", "业务分析"],
        "requirements": "具备数据处理能力，能独立完成基础分析任务",
        "source": "mock",
        "job_url": "https://mock.didiglobal.com/jobs/8",
        "description": "负责日常运营数据报表、专题分析和策略效果跟踪。",
    },
    {
        "title": "测试开发工程师（校招）",
        "company": "华为",
        "location": "深圳",
        "salary": "20k-32k",
        "tech_tags": ["Python", "自动化测试", "接口测试", "CI/CD"],
        "requirements": "熟悉测试流程和至少一种自动化测试语言",
        "source": "mock",
        "job_url": "https://mock.huawei.com/jobs/9",
        "description": "参与自动化测试平台建设和质量保障体系优化。",
    },
    {
        "title": "测试开发实习生",
        "company": "京东",
        "location": "北京",
        "salary": "220/天",
        "tech_tags": ["Python", "Selenium", "接口测试", "质量保障"],
        "requirements": "有测试工具使用经验，具备基础编码能力",
        "source": "mock",
        "job_url": "https://mock.jd.com/jobs/10",
        "description": "协助电商业务开展功能测试、回归测试和自动化脚本维护。",
    },
    {
        "title": "运营专员（校招）",
        "company": "快手",
        "location": "北京",
        "salary": "15k-24k",
        "tech_tags": ["内容运营", "数据复盘", "活动策划", "用户增长"],
        "requirements": "有内容平台或校园活动经验，沟通推动能力强",
        "source": "mock",
        "job_url": "https://mock.kuaishou.com/jobs/11",
        "description": "负责内容活动策划、达人合作及运营数据跟踪。",
    },
    {
        "title": "运营实习生",
        "company": "网易",
        "location": "杭州",
        "salary": "200/天",
        "tech_tags": ["用户运营", "活动执行", "社群运营", "数据整理"],
        "requirements": "执行力强，能支持活动落地与复盘",
        "source": "mock",
        "job_url": "https://mock.163.com/jobs/12",
        "description": "协助完成产品活动策划、内容运营和社群增长工作。",
    },
    {
        "title": "UI/UX 设计师（校招）",
        "company": "OPPO",
        "location": "深圳",
        "salary": "18k-30k",
        "tech_tags": ["Figma", "交互设计", "视觉设计", "设计系统"],
        "requirements": "有完整设计作品集，理解用户体验设计方法",
        "source": "mock",
        "job_url": "https://mock.oppo.com/jobs/13",
        "description": "负责移动端产品界面与交互设计，参与设计系统维护。",
    },
    {
        "title": "设计实习生",
        "company": "百度",
        "location": "北京",
        "salary": "220/天",
        "tech_tags": ["视觉设计", "Figma", "插画", "用户体验"],
        "requirements": "熟悉设计工具，有移动端或 Web 作品",
        "source": "mock",
        "job_url": "https://mock.baidu.com/jobs/14",
        "description": "支持产品界面设计、活动视觉输出与素材整理。",
    },
    {
        "title": "算法工程师（校招）",
        "company": "商汤科技",
        "location": "上海",
        "salary": "25k-42k",
        "tech_tags": ["Python", "PyTorch", "机器学习", "计算机视觉"],
        "requirements": "熟悉机器学习基础，具备算法项目经验",
        "source": "mock",
        "job_url": "https://mock.sensetime.com/jobs/15",
        "description": "负责图像理解和模型训练相关算法研发。",
    },
    {
        "title": "算法实习生",
        "company": "小米",
        "location": "北京",
        "salary": "300/天",
        "tech_tags": ["Python", "模型训练", "特征工程", "数据处理"],
        "requirements": "熟悉 Python 和常见机器学习算法",
        "source": "mock",
        "job_url": "https://mock.xiaomi.com/jobs/16",
        "description": "协助模型实验、数据清洗和算法评估工作。",
    },
    {
        "title": "人力资源专员（校招）",
        "company": "蚂蚁集团",
        "location": "杭州",
        "salary": "14k-22k",
        "tech_tags": ["招聘协调", "雇主品牌", "沟通协作", "流程管理"],
        "requirements": "沟通能力强，有校园活动组织经验优先",
        "source": "mock",
        "job_url": "https://mock.antgroup.com/jobs/17",
        "description": "支持招聘流程推进、候选人沟通和校园招聘项目执行。",
    },
    {
        "title": "HR 实习生",
        "company": "理想汽车",
        "location": "北京",
        "salary": "180/天",
        "tech_tags": ["招聘运营", "面试协调", "Excel", "流程支持"],
        "requirements": "细心负责，能支持招聘流程和基础数据整理",
        "source": "mock",
        "job_url": "https://mock.lixiang.com/jobs/18",
        "description": "负责招聘日程协调、简历处理和候选人沟通。",
    },
    {
        "title": "财务分析师（校招）",
        "company": "蔚来",
        "location": "上海",
        "salary": "16k-28k",
        "tech_tags": ["财务分析", "Excel", "预算管理", "数据建模"],
        "requirements": "财务或会计相关专业，数据敏感度高",
        "source": "mock",
        "job_url": "https://mock.nio.com/jobs/19",
        "description": "支持预算分析、经营数据整理和管理报表输出。",
    },
    {
        "title": "财务实习生",
        "company": "携程",
        "location": "上海",
        "salary": "200/天",
        "tech_tags": ["Excel", "对账", "报表", "数据整理"],
        "requirements": "基础财务知识扎实，能处理表格和数据校验",
        "source": "mock",
        "job_url": "https://mock.trip.com/jobs/20",
        "description": "协助财务对账、月度报表整理和费用审核支持。",
    },
    {
        "title": "运维开发工程师（校招）",
        "company": "腾讯云",
        "location": "广州",
        "salary": "22k-35k",
        "tech_tags": ["Linux", "Python", "自动化运维", "容器化"],
        "requirements": "熟悉 Linux 和脚本开发，了解云服务基础",
        "source": "mock",
        "job_url": "https://mock.qcloud.com/jobs/21",
        "description": "负责基础设施自动化建设、运维平台能力开发和故障排查。",
    },
    {
        "title": "运维实习生",
        "company": "哔哩哔哩",
        "location": "上海",
        "salary": "230/天",
        "tech_tags": ["Linux", "Shell", "监控", "故障排查"],
        "requirements": "具备 Linux 使用基础，愿意参与线上支持和值班轮值",
        "source": "mock",
        "job_url": "https://mock.bilibili.com/jobs/22",
        "description": "支持业务系统监控、巡检和日常运维流程。",
    },
]


class MockSource(BaseSource):
    """模拟数据源 - 面向通用校招/实习岗位的示例数据"""

    name = "mock"
    priority = 99

    def build_query(self, keywords: list[str]) -> str:
        return " ".join(keywords)

    async def search(self, query: str, page: int = 1) -> ToolResult:
        results = MOCK_JOBS.copy()
        if query:
            query_lower = query.lower()
            generic_terms = {"校招", "校园招聘", "应届生", "2026届", "实习", "实习生", "日常实习"}
            keywords = [keyword for keyword in query_lower.split() if keyword not in generic_terms]
            filtered = []
            for job in results:
                text = (
                    f"{job['title']} {job.get('description', '')} "
                    f"{job.get('requirements', '')} {' '.join(job.get('tech_tags', []))}"
                ).lower()
                if any(keyword in text for keyword in keywords):
                    filtered.append(job)
            if filtered:
                results = filtered

        start = (page - 1) * 20
        page_results = results[start : start + 20]

        if len(page_results) > 10:
            page_results = random.sample(page_results, min(len(page_results), 15))

        return ToolResult(success=True, data=page_results, source=self.name)
