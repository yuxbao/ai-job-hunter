from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from config.settings import settings
from src.models.search_request import SearchRequest
from src.runtime.search_runner import run_search

STAGE_ORDER = [
    "planner",
    "searcher",
    "scraper",
    "quality_gate",
    "filter",
    "enricher",
    "evaluator",
    "reporter",
]


@dataclass
class JobRecord:
    job_id: str
    request: dict[str, Any]
    status: str = "queued"
    stage: str = "queued"
    progress: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    message: str = ""
    iteration: int = 0
    counts: dict[str, int] = field(
        default_factory=lambda: {
            "raw_results": 0,
            "scraped_pages": 0,
            "gated_results": 0,
            "candidate_jobs": 0,
            "final_jobs": 0,
        }
    )
    errors: list[str] = field(default_factory=list)
    recent_events: list[dict[str, str]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    output_path: str = ""
    result: dict[str, Any] | None = None
    task: asyncio.Task | None = None

    def to_status_payload(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message": self.message,
            "iteration": self.iteration,
            "counts": self.counts,
            "errors": self.errors,
            "recent_events": self.recent_events,
            "summary": self.summary,
            "request": self.request,
            "output_path": self.output_path,
        }

    def to_result_payload(self) -> dict[str, Any]:
        payload = self.to_status_payload()
        payload["result"] = self.result
        return payload


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    def create_job(self, request: SearchRequest) -> JobRecord:
        job_id = uuid4().hex
        record = JobRecord(job_id=job_id, request=request.model_dump())
        record.message = "任务已创建，等待执行"
        self._jobs[job_id] = record
        self._subscribers[job_id] = set()
        record.task = asyncio.create_task(self._run_job(record, request))
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]] | None:
        record = self._jobs.get(job_id)
        if record is None:
            return None

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.setdefault(job_id, set()).add(queue)
        queue.put_nowait({"event": "status", "data": record.to_status_payload()})
        if record.result is not None:
            queue.put_nowait({"event": "result", "data": record.to_result_payload()})
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._subscribers.get(job_id)
        if not subscribers:
            return
        subscribers.discard(queue)

    async def event_stream(self, job_id: str):
        queue = self.subscribe(job_id)
        if queue is None:
            raise KeyError(job_id)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": {"job_id": job_id}}
                    continue

                yield event
                if event["event"] == "result":
                    break
        finally:
            self.unsubscribe(job_id, queue)

    @staticmethod
    def format_sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def _publish(self, job_id: str, event: str, data: dict[str, Any]) -> None:
        subscribers = self._subscribers.get(job_id, set())
        stale: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in subscribers:
            try:
                queue.put_nowait({"event": event, "data": data})
            except RuntimeError:
                stale.append(queue)

        for queue in stale:
            subscribers.discard(queue)

    async def _run_job(self, record: JobRecord, request: SearchRequest) -> None:
        output_dir = str(Path(settings.OUTPUT_DIR) / "jobs" / record.job_id)
        record.status = "running"
        record.stage = "planner"
        record.message = "开始执行搜索任务"
        record.updated_at = datetime.now().isoformat(timespec="seconds")
        await self._publish(record.job_id, "status", record.to_status_payload())

        async def on_progress(payload: dict[str, Any]) -> None:
            stage = payload.get("stage", record.stage)
            event = payload.get("event", "")
            stage_index = payload.get("stage_index", 0)
            total_stages = max(payload.get("total_stages", len(STAGE_ORDER)), 1)

            if event == "stage_started":
                progress = stage_index / total_stages
            elif event == "stage_progress":
                stage_progress = min(max(payload.get("stage_progress", 0.0), 0.0), 1.0)
                progress = (stage_index + stage_progress) / total_stages
            else:
                progress = (stage_index + 1) / total_stages

            record.stage = stage
            record.progress = min(max(progress, 0.0), 1.0)
            record.iteration = payload.get("iteration", record.iteration)
            payload_counts = payload.get("counts", {})
            if payload_counts:
                record.counts = {**record.counts, **payload_counts}
            record.updated_at = datetime.now().isoformat(timespec="seconds")
            record.message = {
                "stage_started": f"{stage} 阶段执行中",
                "stage_completed": f"{stage} 阶段完成",
                "stage_failed": f"{stage} 阶段失败",
                "stage_progress": payload.get("message", record.message),
            }.get(event, record.message)

            if payload.get("message"):
                record.recent_events = (
                    [{"stage": stage, "message": payload["message"], "time": record.updated_at}]
                    + record.recent_events
                )[:12]

            if payload.get("status") == "failed":
                record.status = "failed"
            if payload.get("summary"):
                record.summary = payload["summary"]
            if payload.get("output_path"):
                record.output_path = payload["output_path"]
            await self._publish(record.job_id, "status", record.to_status_payload())

        try:
            result = await run_search(
                request,
                progress_callback=on_progress,
                output_dir=output_dir,
            )
        except Exception as exc:
            record.status = "failed"
            record.message = "搜索任务执行失败"
            record.errors.append(str(exc))
            record.updated_at = datetime.now().isoformat(timespec="seconds")
            await self._publish(record.job_id, "status", record.to_status_payload())
            await self._publish(record.job_id, "result", record.to_result_payload())
            return

        record.status = result.get("status", "completed")
        record.stage = "reporter"
        record.progress = 1.0
        record.updated_at = datetime.now().isoformat(timespec="seconds")
        record.summary = result.get("acceptance_summary", record.summary)
        record.output_path = result.get("output_path", "")
        record.result = {
            "final_jobs": [job.model_dump() for job in result.get("final_jobs", [])],
            "acceptance_passed": result.get("acceptance_passed", False),
            "acceptance_issues": result.get("acceptance_issues", []),
            "acceptance_summary": result.get("acceptance_summary", {}),
            "search_warnings": result.get("search_warnings", []),
            "degraded_mode": result.get("degraded_mode", False),
            "sources_used": result.get("sources_used", []),
            "summary_path": result.get("summary_path", ""),
            "output_path": result.get("output_path", ""),
        }
        record.counts["final_jobs"] = len(record.result["final_jobs"])
        record.message = "搜索任务已完成" if record.status == "completed" else "搜索任务已结束"
        await self._publish(record.job_id, "status", record.to_status_payload())
        await self._publish(record.job_id, "result", record.to_result_payload())


job_manager = JobManager()
