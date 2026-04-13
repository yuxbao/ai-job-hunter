# AI Job Hunter

[中文](./README.md) | [English](./README.en.md)

[![GitHub Stars](https://img.shields.io/github/stars/yuxbao/ai-job-hunter?style=social)](https://github.com/yuxbao/ai-job-hunter)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Powered%20by-LangGraph-1C3C3C)](https://github.com/langchain-ai/langgraph)
[![OpenAI Compatible](https://img.shields.io/badge/LLM-OpenAI%20Compatible-412991?logo=openai&logoColor=white)](https://openai.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen)](https://github.com/yuxbao/ai-job-hunter/pulls)

一个面向 AI Engineer 校招 / 实习岗位的 Agentic 求职助手。项目基于 LangGraph 构建，能够自动规划搜索词、抓取招聘页面、过滤低质量结果、调用 LLM 做语义筛选与信息补全，并最终输出结构化岗位结果。

## 项目亮点

- 面向真实求职场景，而不是单纯的网页爬虫
- 多数据源检索：Boss 直聘、猎聘、智联招聘
- 质量门控前置：先淘汰聚合页、脏页，再进入 LLM 流程
- 受控并发：搜索、筛选、补全都支持并发上限
- 验收驱动：围绕“目标岗位数 + 来源覆盖 + 核心字段完整度”决策
- 本地输出清晰：JSON、CSV、summary、LLM traces 分开保存

## 工作流

```text
START
  → Planner
  → Searcher
  → Scraper
  → QualityGate
  → Filter
  → Enricher
  → Evaluator
  → Reporter
END
```

如果当前结果还没有满足验收标准，流程会回到 `Planner` 继续迭代，但会记住已经尝试过的 query，避免无意义重复检索。

## 设计思路

这个项目的核心不是“尽可能多地搜到页面”，而是“尽可能稳定地拿到 50 条可交付岗位”。

因此链路设计上做了两层拆分：

1. 低成本阶段
   搜索、抓取、规则清洗、质量门控
2. 高成本阶段
   LLM 筛选、字段补全、最终验收

这样可以把昂贵的 LLM 调用留给更高质量的候选，而不是把几百条脏结果全部送进去慢慢处理。

## 主要能力

- `Planner`
  根据目标数量、已有结果、失败来源生成搜索策略，并记录已尝试 query。
- `Searcher`
  多站点并发搜索，并合并多轮结果。
- `Scraper`
  对缺少详情的结果做网页抓取补充。
- `QualityGate`
  前置拦截聚合页、索引页、字段太差的页面。
- `Filter`
  规则过滤 + LLM 批量语义筛选。
- `Enricher`
  仅对接近最终目标的短名单做字段补全与技术栈抽取。
- `Evaluator`
  判断是否满足验收标准，决定继续搜索还是输出。
- `Reporter`
  生成 JSON / CSV / summary，并给出控制台报告。

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

然后按需填写：

- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `TAVILY_API_KEY`

### 3. 运行

Mock 模式：

```bash
python main.py
```

真实搜索模式：

```bash
MOCK_MODE=false python main.py
```

## 配置项

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_API_KEY` | OpenAI 兼容接口的 API Key | `""` |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |
| `LLM_BASE_URL` | 自定义 LLM endpoint | `None` |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | `""` |
| `TARGET_JOB_COUNT` | 目标岗位数 | `50` |
| `MAX_ITERATIONS` | 最大迭代轮数 | `5` |
| `BATCH_SIZE` | Filter 批大小 | `10` |
| `SEARCH_CONCURRENCY` | 搜索并发数 | `4` |
| `FILTER_CONCURRENCY` | Filter 并发数 | `4` |
| `ENRICH_CANDIDATE_BUFFER` | 补全短名单缓冲量 | `10` |
| `ENRICH_CONCURRENCY` | 补全并发数 | `4` |
| `SHOW_LLM_OUTPUT` | 是否在控制台显示 LLM 回复 | `true` |
| `WRITE_LLM_OUTPUT_FILES` | 是否写出 LLM trace 文件 | `true` |
| `MOCK_MODE` | 是否启用 mock 数据 | `false` |

## 输出文件

运行后会在 `output/` 下生成：

- `jobs_latest.json`
- `jobs_latest.csv`
- `summary_latest.json`
- `llm_traces.jsonl`

其中：

- `jobs_latest.*` 是最新岗位结果
- `summary_latest.json` 是本轮验收摘要
- `llm_traces.jsonl` 是 LLM 原始回复日志

这些文件默认不会提交到 git。

## 项目结构

```text
ai-job-hunter/
├── main.py
├── config/
│   └── settings.py
├── src/
│   ├── graph/
│   │   ├── builder.py
│   │   └── nodes/
│   │       ├── planner.py
│   │       ├── searcher.py
│   │       ├── scraper.py
│   │       ├── quality_gate.py
│   │       ├── filter.py
│   │       ├── enricher.py
│   │       ├── evaluator.py
│   │       └── reporter.py
│   ├── models/
│   ├── prompts/
│   ├── sources/
│   ├── state/
│   ├── tools/
│   └── utils/
└── tests/
```

## 测试

```bash
pytest tests/test_acceptance.py tests/test_searcher.py
```

