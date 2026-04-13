# AI Job Hunter

An agentic job-search workflow for collecting AI Engineer campus / internship roles from multiple recruiting websites.

Built with LangGraph, this project plans queries, retrieves search results, gates low-quality pages, filters with an LLM, enriches structured fields, evaluates acceptance criteria, and exports deliverables in JSON / CSV.

## What It Does

- Searches AI Engineer, LLM, NLP, CV, ML, and related campus roles.
- Uses multiple job sites such as Boss Zhipin, Liepin, and Zhaopin.
- Applies a quality gate before expensive LLM steps.
- Filters and enriches candidate jobs with structured metadata.
- Tracks acceptance status against a target count and source coverage.
- Writes human-readable reports plus machine-readable output files.

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

If acceptance is not met, the graph loops back to `Planner` with remembered query history so it avoids reusing the same search terms blindly.

## Why This Design

The project is optimized around a practical problem: search results are noisy, and LLM calls are expensive.

So the pipeline deliberately separates:

- Broad recall: search and scraping
- Cheap cleanup: rule-based gating and dedupe
- Expensive reasoning: LLM filtering and enrichment
- Final quality control: acceptance evaluation and reporting

This keeps the expensive parts focused on the best candidates instead of the full noisy result set.

## Key Features

- `Planner`: generates or falls back to search queries and tracks attempted queries
- `Searcher`: performs bounded-concurrency retrieval across data sources
- `QualityGate`: removes obvious aggregate pages and keeps higher-quality detail pages
- `Filter`: runs rule-based filtering plus bounded-concurrency LLM batch screening
- `Enricher`: enriches only a short list near the final target, not the full candidate pool
- `Evaluator`: checks target count, real source coverage, and required fields
- `Reporter`: exports results and writes acceptance summaries

## Tech Stack

- Python 3.11+
- LangGraph
- LangChain / langchain-openai
- httpx
- pydantic / pydantic-settings
- BeautifulSoup4
- pandas
- rich
- pytest / pytest-asyncio

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Fill in your keys in `.env`.

### 3. Run

Mock mode:

```bash
python main.py
```

Real search mode:

```bash
MOCK_MODE=false python main.py
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `LLM_API_KEY` | OpenAI-compatible API key | `""` |
| `LLM_MODEL` | LLM model name | `gpt-4o-mini` |
| `LLM_BASE_URL` | Optional custom LLM endpoint | `None` |
| `TAVILY_API_KEY` | Tavily search API key | `""` |
| `TARGET_JOB_COUNT` | Target number of jobs | `50` |
| `MAX_ITERATIONS` | Max graph iterations | `5` |
| `BATCH_SIZE` | Filter batch size | `10` |
| `SEARCH_CONCURRENCY` | Search concurrency | `4` |
| `FILTER_CONCURRENCY` | Filter LLM concurrency | `4` |
| `ENRICH_CANDIDATE_BUFFER` | Extra shortlist buffer above target | `10` |
| `ENRICH_CONCURRENCY` | Enrichment concurrency | `4` |
| `SHOW_LLM_OUTPUT` | Print LLM replies in console | `true` |
| `WRITE_LLM_OUTPUT_FILES` | Write LLM traces to file | `true` |
| `MOCK_MODE` | Use built-in mock dataset | `false` |

## Output

Generated files are written to `output/` during local runs:

- `jobs_latest.json`
- `jobs_latest.csv`
- `summary_latest.json`
- `llm_traces.jsonl`

These runtime artifacts are ignored by git and are not intended to be committed.

## Project Structure

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

## Testing

```bash
pytest tests/test_acceptance.py tests/test_searcher.py
```

## Notes

- This repository does not commit `.env`, generated outputs, or local trace files.
- Real-world search quality depends on external APIs and the freshness of public recruiting pages.
- Mock mode is useful for local development and tests when external keys are unavailable.
