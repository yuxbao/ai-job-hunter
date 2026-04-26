from __future__ import annotations

PLANNER_PROMPT = """你是一个专业的招聘信息搜索规划师。

## 任务
为以下求职需求制定搜索策略，目标是收集 {target_count} 条有效岗位信息。

## 用户需求
{search_brief}

## 当前状态
- 已收集: {existing_count} 条
- 已使用数据源: {sources_used}
- 失败的数据源: {failed_sources}
- 当前迭代: 第 {iteration} 轮（最多 {max_iterations} 轮）

## 要求
1. 生成 5-8 个不同的搜索关键词
2. 关键词要围绕用户的岗位名称、技能要求、求职类型、城市偏好来组合
3. 如果用户给了额外要求，请在部分查询词中带上这些要求
4. 不要把明显无关的岗位方向混进来
3. 指定搜索的目标网站（至少2个，从以下选择）: boss_zhipin, liepin, zhaopin, nowcoder, 51job

## 输出格式（严格JSON，不要包含其他文字）
```json
{{
  "queries": ["关键词1", "关键词2", ...],
  "target_sites": ["boss_zhipin", "liepin", "nowcoder"],
  "strategy": "策略描述"
}}
```"""


FILTER_PROMPT = """你是一个校招/实习岗位筛选专家。请判断以下岗位是否符合用户的求职需求。

## 用户需求
{search_brief}

## 筛选标准
1. 与用户目标岗位或相近岗位相关
2. 优先保留面向应届生/校招/实习的岗位，排除明显资深社招岗位
3. 如果用户指定了城市/要求/排除关键词，请纳入判断
4. 保留相关性强、信息较完整的岗位

## 待筛选岗位
{jobs_json}

## 输出格式（严格JSON数组）
```json
[
  {{"index": 0, "is_relevant": true, "confidence": 0.9, "reason": "简要原因",
    "confidence": 0.0到1.0的浮点数
  }},
  ...
]

只返回 is_relevant 为 true 且 confidence >= 0.6 的岗位。严格按JSON格式输出。"""


ENRICH_PROMPT = """你是一个通用岗位信息分析助手。请从以下岗位描述中提取技能标签并补全信息。

## 用户需求
{search_brief}

## 岗位信息
{job_json}

## 任务
1. 提取 3-8 个岗位相关的技能/工具/领域标签，使用简洁短词
2. 总结 3-5 条核心要求
3. 判断岗位类型更接近 校招 / 实习 / 应届 / 不限 / 社招
4. 尽量清洗薪资字段

## 输出格式（严格JSON）
```json
{{
  "tech_tags": ["标签1", "标签2", ...],
  "requirements": "从描述中提取的3-5条核心要求",
  "experience_level": "校招/实习/应届/不限/社招",
  "salary_cleaned": "清洗后的薪资范围（如 20k-35k）"
}}
```"""
