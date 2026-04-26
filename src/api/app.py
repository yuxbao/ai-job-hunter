from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.api.job_manager import job_manager
from src.models.search_request import SearchRequest

app = FastAPI(title="Job Hunter API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search-jobs")
async def create_search_job(request: SearchRequest) -> dict[str, str]:
    record = job_manager.create_job(request)
    return {"job_id": record.job_id, "status": record.status}


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str) -> dict:
    record = job_manager.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.to_status_payload()


@app.get("/api/jobs/{job_id}/result")
async def get_job_result(job_id: str) -> dict:
    record = job_manager.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.to_result_payload()


@app.get("/api/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    if job_manager.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        async for event in job_manager.event_stream(job_id):
            yield job_manager.format_sse(event["event"], event["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


@app.get("/", response_model=None)
async def index():
    index_path = frontend_dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run the React app in frontend/."}
