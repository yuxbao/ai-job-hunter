# Job Hunter

[中文](./README.md) | [English](./README.en.md)

A general campus and internship job assistant built with LangGraph, FastAPI, and React.

Users can start with only a `job_title`, then trigger a full workflow:

- query planning
- multi-source search
- detail scraping
- quality gating
- semantic filtering
- metadata enrichment
- acceptance evaluation
- structured reporting

## Highlights

- Generic role search instead of AI-only positions
- Optional user preferences: requirements, search type, cities, target count, exclude keywords
- FastAPI async job APIs with live progress polling
- React + TypeScript frontend
- JSON / CSV / summary / LLM trace exports

## Run the backend

```bash
pip install -e .
uvicorn src.api.app:app --reload
```

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

## CLI example

```bash
python main.py --job-title "Backend Intern" --requirements "Java Spring Boot"
```

## API example

```bash
curl -X POST http://127.0.0.1:8000/api/search-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Backend Intern",
    "requirements": "Java Spring Boot",
    "search_type": "intern",
    "cities": ["Shanghai"],
    "target_count": 30
  }'
```
