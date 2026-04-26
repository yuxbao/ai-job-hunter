# Job Hunter

[中文](./README.md) | [English](./README.en.md)

[![GitHub Stars](https://img.shields.io/github/stars/yuxbao/ai-job-hunter?style=social)](https://github.com/yuxbao/ai-job-hunter)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Powered%20by-LangGraph-1C3C3C)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/UI-React%20%2B%20TypeScript-20232A?logo=react&logoColor=61DAFB)](https://react.dev/)

一个通用的校招 / 日常实习求职助手。用户只需要输入岗位名称，就可以触发一整套 Agentic 链路：自动规划搜索词、跨站搜索、抓取岗位详情、质量门控、语义筛选、信息补全、结果验收，并最终在前端展示结构化岗位结果。

## 现在支持什么

- 通用岗位搜索，不再局限于 AI 岗位
- 输入最少只需要 `岗位名称`
- 可选输入：岗位要求、求职类型、城市、目标数量、排除关键词
- 多数据源检索：Boss 直聘、猎聘、智联招聘
- FastAPI 异步任务接口
- React + TypeScript 前端交互界面
- 任务进度轮询与阶段展示
- 输出 JSON / CSV / summary / LLM traces

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

如果当前结果未达到验收标准，工作流会回到 `Planner` 继续迭代，并记住已经尝试过的查询词。

## 产品结构

```text
ai-job-hunter/
├── main.py                  # CLI 入口
├── config/
├── src/
│   ├── api/                 # FastAPI 接口与任务管理
│   ├── graph/               # LangGraph 工作流节点
│   ├── models/
│   ├── runtime/             # 搜索执行入口
│   ├── sources/             # 招聘站点与 mock 数据源
│   ├── state/
│   ├── tools/
│   └── utils/
├── frontend/                # React + TypeScript 前端
├── docs/plans/
└── tests/
```

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

按需填写：

- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `TAVILY_API_KEY`

### 3. 启动后端 API

```bash
uvicorn src.api.app:app --reload
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5174`，并代理到 `http://127.0.0.1:8000` 的后端 API。

## API

### 创建搜索任务

```bash
curl -X POST http://127.0.0.1:8000/api/search-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "后端开发实习生",
    "requirements": "Java Spring Boot 微服务",
    "search_type": "intern",
    "cities": ["上海", "杭州"],
    "target_count": 30
  }'
```

### 查询任务进度

```bash
curl http://127.0.0.1:8000/api/jobs/<job_id>/status
```

### 查询最终结果

```bash
curl http://127.0.0.1:8000/api/jobs/<job_id>/result
```

## CLI 方式

如果你想直接从命令行运行，也可以：

```bash
python main.py
```

不带参数时会进入交互式输入；最少只需要填写岗位名称。也可以一次性传参：

```bash
python main.py --job-title "后端开发实习生" --requirements "Java Spring Boot" --cities "上海,杭州"
```

## 配置项

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_API_KEY` | OpenAI 兼容接口的 API Key | `""` |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |
| `LLM_BASE_URL` | 自定义 LLM endpoint | `None` |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | `""` |
| `TARGET_JOB_COUNT` | 默认目标岗位数 | `50` |
| `MAX_ITERATIONS` | 最大迭代轮数 | `5` |
| `SEARCH_CONCURRENCY` | 搜索并发数 | `4` |
| `FILTER_CONCURRENCY` | 筛选并发数 | `4` |
| `ENRICH_CONCURRENCY` | 信息补全并发数 | `4` |
| `SHOW_LLM_OUTPUT` | 是否在控制台显示 LLM 回复 | `true` |
| `WRITE_LLM_OUTPUT_FILES` | 是否写出 LLM trace 文件 | `true` |
| `MOCK_MODE` | 是否启用 mock 数据 | `false` |

## 输出文件

运行后会在 `output/` 下生成：

- `jobs_latest.json`
- `jobs_latest.csv`
- `summary_latest.json`
- `llm_traces.jsonl`

如果通过 API 发起任务，默认还会按 `output/jobs/<job_id>/` 进行隔离输出。

## 测试

```bash
pytest tests/test_acceptance.py tests/test_searcher.py
```
