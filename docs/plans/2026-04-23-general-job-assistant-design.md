# General Campus And Internship Job Assistant Design

## Goal

Refactor the project from an AI-job-only workflow into a generic campus and day-to-day internship job assistant.

The new product should:

- accept a minimal user input of `job_title`
- optionally accept user preferences such as requirements, cities, search type, target count, and exclude keywords
- run the full planning, search, scrape, filter, enrich, evaluate, and report workflow for any job family
- expose the workflow through a FastAPI backend with async job execution and live progress polling
- provide a React + TypeScript frontend for search input, progress tracking, and result exploration

## Product Scope

### In scope

- Generalize prompts, filters, and reporting language away from AI-only roles
- Add a structured search request model driven by user input
- Preserve the existing multi-source search architecture
- Add backend APIs for creating jobs and polling status/results
- Add a frontend UI integrated into the repository
- Update docs and mock data so the repository positioning matches the product

### Out of scope for v1

- User accounts or saved search history
- Database persistence beyond in-memory or file-backed runtime artifacts
- WebSocket-only streaming
- Multi-page frontend routing
- Production deployment scripts

## User Input Model

The search request will use `job_title` as the only required field.

Optional fields:

- `requirements`: free-text skill or experience preferences
- `search_type`: `campus`, `intern`, or `all`
- `cities`: list of target cities
- `target_count`: desired number of jobs
- `exclude_keywords`: free-text exclusions such as industries or role families

The backend will build a `search_brief` string from these inputs so planning, filtering, and reporting can use one consistent summary.

## Backend Architecture

### Workflow generalization

The LangGraph state will be extended from a fixed `job_type` string to a richer request-driven model:

- `job_title`
- `requirements`
- `search_type`
- `cities`
- `exclude_keywords`
- `search_brief`

Node behavior will change as follows:

- `Planner`: generate query combinations from the user request instead of AI-specific templates
- `Searcher`: unchanged in structure, but receives broader query output
- `Scraper`: unchanged in structure
- `QualityGate`: stays generic and focuses on page quality
- `Filter`: evaluate relevance to the request, not to AI-specific keywords
- `Enricher`: extract common job metadata and optional skill tags from the job description
- `Evaluator`: keep acceptance logic around count, source diversity, and field completeness
- `Reporter`: produce generic summaries and export metadata tied to the search request

### Runtime and progress tracking

Add a lightweight async job manager in the backend:

- create a `job_id` for each request
- execute the workflow in a background task
- store live status, node progress, summary metrics, errors, and final results in memory

Each graph node will emit progress updates through a shared callback so the API can expose:

- current stage
- percent/progress label
- iteration
- counts such as raw results, gated results, candidate jobs, and final jobs
- terminal states: `queued`, `running`, `completed`, `failed`

## API Design

### `POST /api/search-jobs`

Creates a new async job search task.

Request body:

```json
{
  "job_title": "后端开发实习生",
  "requirements": "Java Spring Boot 微服务",
  "search_type": "intern",
  "cities": ["上海", "杭州"],
  "target_count": 30,
  "exclude_keywords": "外包 销售"
}
```

Response body:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### `GET /api/jobs/{job_id}/status`

Returns live progress, node status, summary counts, and errors.

### `GET /api/jobs/{job_id}/result`

Returns final summary and job list once complete. If unfinished, the endpoint returns the latest partial state plus a non-terminal status.

## Frontend Architecture

### Stack

- React
- TypeScript
- Vite

### Page structure

One single-page app with three vertically stacked sections:

1. Search panel
   - job title required
   - optional advanced inputs in a collapsible section
   - submit button with disabled/loading states

2. Progress panel
   - current stage headline
   - timeline for planner, searcher, scraper, quality gate, filter, enricher, evaluator, reporter
   - live counters and recent messages

3. Results panel
   - summary cards
   - searchable/sortable job list
   - selected job detail preview
   - export links when available

### Visual direction

Use an editorial operations-room aesthetic:

- warm ivory and ink base instead of generic white/purple SaaS styling
- strong serif display typography paired with a readable sans body
- layered cards, hairline borders, muted gradients, and subtle paper-like texture
- restrained but meaningful motion for stage updates and result reveals

## Data Flow

1. User fills the form and submits a request.
2. Frontend calls `POST /api/search-jobs`.
3. Frontend stores `job_id` and starts polling `GET /api/jobs/{job_id}/status`.
4. Backend runs the graph in the background and updates job state after every stage.
5. When status becomes terminal, frontend fetches `GET /api/jobs/{job_id}/result`.
6. Frontend renders summaries, jobs, and output paths.

## Mock Data Strategy

The mock source should no longer be AI-only. It should include a broader mix such as:

- backend development
- frontend development
- product
- data analysis
- operations
- testing

This allows the generalized planner and filter logic to be exercised without misleading repository positioning.

## Testing Strategy

Add or update tests for:

- generic planner fallback behavior
- request-aware filtering behavior
- API job lifecycle
- status polling contract
- result schema shape

Frontend verification will focus on:

- form validation
- polling state transitions
- result rendering for complete and failed jobs

## Risks And Mitigations

- Prompt over-generalization may reduce precision.
  Mitigation: pass a compact `search_brief` and keep rule-based prefiltering conservative.

- In-memory task storage means results disappear on process restart.
  Mitigation: acceptable for v1; keep output artifacts on disk and design the manager so file-backed persistence can be added later.

- Frontend progress can feel stale under polling.
  Mitigation: structure progress payloads cleanly so the transport can later move to SSE/WebSocket without rewriting the UI model.
