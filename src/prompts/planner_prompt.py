from __future__ import annotations

PLANNER_PROMPT = """你是一个专业的招聘信息搜索规划师。

## 任务
为 "{job_type}" 校招岗位制定搜索策略，目标是收集 {target_count} 条有效岗位信息。

## 当前状态
- 已收集: {existing_count} 条
- 已使用数据源: {sources_used}
- 失败的数据源: {failed_sources}
- 当前迭代: 第 {iteration} 轮（最多 {max_iterations} 轮）

## 要求
1. 生成 5-8 个不同的搜索关键词
2. 覆盖以下维度的不同组合:
   - 岗位名称: AI工程师, ML工程师, 大模型工程师, LLM工程师, 算法工程师, 机器学习工程师, NLP工程师, CV工程师
   - 岗位类型: 校招, 校园招聘, 2026届, 应届生, 实习
   - 技术方向: 大模型, NLP, 计算机视觉, 推荐系统, 深度学习, 强化学习, 多模态
3. 指定搜索的目标网站（至少2个，从以下选择）: boss_zhipin, liepin, zhaopin

## 输出格式（严格JSON，不要包含其他文字）
```json
{{
  "queries": ["关键词1", "关键词2", ...],
  "target_sites": ["boss_zhipin", "liepin"],
  "strategy": "策略描述"
}}
```"""


FILTER_PROMPT = """你是一个校招岗位筛选专家。请判断以下岗位是否符合 AI Engineer 校招/实习要求。

## 筛选标准
1. 面向应届生/校招/实习（非社招、非3年以上经验要求）
2. 与 AI/ML/LLM/算法/数据智能相关（非纯前端、纯后端、纯测试、纯运维）
3. 位于中国主要城市或支持远程

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


ENRICH_PROMPT = """你是一个 AI 技术栈分析专家。请从以下岗位描述中提取技术标签并补全信息。

## 岗位信息
{job_json}

## 需要提取的技术标签（从以下分类中选择合适的）
- 编程语言: Python, C++, Java, Go, Rust, Julia
- ML 框架: PyTorch, TensorFlow, JAX, scikit-learn, Keras
- LLM 相关: Transformer, GPT, BERT, LLaMA, RAG, Fine-tuning, RLHF, Prompt Engineering, LangChain, Agent
- MLOps: Docker, Kubernetes, MLflow, Ray, Airflow
- 数据处理: SQL, Spark, Pandas, NumPy
- 领域: NLP, CV, 推荐系统, 语音识别, 时序预测, 知识图谱, 图神经网络, 联邦学习
- 基础设施: CUDA, ONNX, TensorRT, DeepSpeed, Megatron, vLLM, Triton

## 输出格式（严格JSON）
```json
{{
  "tech_tags": ["标签1", "标签2", ...],
  "requirements": "从描述中提取的3-5条核心要求",
  "experience_level": "校招/实习/应届",
  "salary_cleaned": "清洗后的薪资范围（如 20k-35k）"
}}
```"""
