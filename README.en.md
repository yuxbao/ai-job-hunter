# AI Job Hunter

[中文](./README.md) | [English](./README.en.md)

[![GitHub Stars](https://img.shields.io/github/stars/yuxbao/ai-job-hunter?style=social)](https://github.com/yuxbao/ai-job-hunter)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Powered%20by-LangGraph-1C3C3C)](https://github.com/langchain-ai/langgraph)
[![OpenAI Compatible](https://img.shields.io/badge/LLM-OpenAI%20Compatible-412991?logo=openai&logoColor=white)](https://openai.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen)](https://github.com/yuxbao/ai-job-hunter/pulls)

AI Job Hunter is an agentic workflow for collecting AI Engineer campus and internship roles from multiple recruiting websites.

It is built with LangGraph and combines:

- query planning
- multi-source search
- scraping
- quality gating
- LLM-based semantic filtering
- metadata enrichment
- acceptance evaluation
- structured reporting

## Workflow

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

## Why It Exists

Raw search results are noisy, and LLM calls are expensive.

So the pipeline is intentionally split into:

1. Low-cost stages
   search, scraping, rule-based cleanup, quality gating
2. High-cost stages
   LLM filtering, enrichment, and final acceptance evaluation

This keeps the expensive reasoning focused on the best candidates instead of the entire noisy pool.

## Quick Start

```bash
pip install -e .
cp .env.example .env
python main.py
```

To run real search mode:

```bash
MOCK_MODE=false python main.py
```

## Outputs

Runtime artifacts are written to `output/`:

- `jobs_latest.json`
- `jobs_latest.csv`
- `summary_latest.json`
- `llm_traces.jsonl`

These files are ignored by git by default.

## Tests

```bash
pytest tests/test_acceptance.py tests/test_searcher.py
```
