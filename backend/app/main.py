# Author: urumb
import json
import logging
import asyncio
from typing import Generator, List

from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.app.schemas.code_file import (
    AuditRequest,
    AuditResultResponse,
    CodeFile,
    FileAuditResult,
)
from backend.app.services.audit_runner import run_audit_on_code
from backend.app.services.input_processor import (
    process_github_repo,
    process_pasted_code,
    process_uploaded_files,
)
from backend.app.services.job_store import create_job, get_job, add_job_event

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Multi-Agent Code Auditor",
    description="Phase 5 — Background SSE streaming and speed optimization.",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Background Job Execution
# ---------------------------------------------------------------------------
def _run_audit_job(job_id: str, code_files: List[CodeFile]) -> None:
    """Background task that runs the audit and pushed events to job_store.

    Args:
        job_id: UUID of the job.
        code_files: List of CodeFile objects to audit.
    """
    job = get_job(job_id)
    if not job:
        return

    job["status"] = "running"
    job["total_files"] = len(code_files)
    results: List[dict] = []

    try:
        add_job_event(job_id, "log", {
            "agent": "System",
            "message": f"Starting background audit — {len(code_files)} file(s) queued",
            "level": "info",
        })

        for i, file in enumerate(code_files, start=1):
            add_job_event(job_id, "file_start", {
                "path": file.path,
                "index": i,
                "total": len(code_files),
            })

            add_job_event(job_id, "log", {
                "agent": "System",
                "message": f"[{i}/{len(code_files)}] Processing: {file.path}",
                "level": "info",
            })

            # Log callback that routes directly to job store
            def log_callback(agent: str, message: str, level: str = "info") -> None:
                add_job_event(job_id, "log", {"agent": agent, "message": message, "level": level})

            try:
                output = run_audit_on_code(file.content, log_callback=log_callback)

                file_result = {
                    "file_path": file.path,
                    "final_report": output.get("final_report", ""),
                    "error": None,
                }
                results.append(file_result)

                add_job_event(job_id, "result", file_result)

            except Exception as exc:
                file_result = {
                    "file_path": file.path,
                    "final_report": "",
                    "error": str(exc),
                }
                results.append(file_result)

                add_job_event(job_id, "result", file_result)
                add_job_event(job_id, "log", {
                    "agent": "System",
                    "message": f"Failed: {file.path} — {exc}",
                    "level": "error",
                })

            add_job_event(job_id, "file_done", {
                "path": file.path,
                "index": i,
                "total": len(code_files),
            })

        add_job_event(job_id, "done", {"total_files": len(results)})
        job["status"] = "completed"

    except Exception as exc:
        logger.error("Background job %s failed: %s", job_id, exc)
        add_job_event(job_id, "error", {"message": str(exc)})
        job["status"] = "failed"


# ---------------------------------------------------------------------------
# SSE Helpers
# ---------------------------------------------------------------------------
async def _stream_job_events(job_id: str):
    """Async generator that yields SSE events from the job store.</br>
    Loops until the job is marked completed or failed.
    """
    job = get_job(job_id)
    if not job:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Job not found'}})}\n\n"
        return

    last_index = 0

    while True:
        # Yield any new events
        current_events = job["events"]
        while last_index < len(current_events):
            event = current_events[last_index]
            yield f"data: {json.dumps(event)}\n\n"
            last_index += 1

        # Check if complete
        if job["status"] in ("completed", "failed"):
            # Ensure all final events are yielded
            while last_index < len(job["events"]):
                event = job["events"][last_index]
                yield f"data: {json.dumps(event)}\n\n"
                last_index += 1
            break

        # Sleep briefly to avoid hot loop
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_code_files(request: AuditRequest) -> List[CodeFile]:
    """Convert an AuditRequest into a list of CodeFile objects."""
    if request.input_type == "github":
        return process_github_repo(request.github_url)
    elif request.input_type == "paste":
        return process_pasted_code(request.code)
    return []


def _run_audit_on_files(code_files: List[CodeFile]) -> AuditResultResponse:
    """Run the LangGraph audit pipeline synchronously (fallback)."""
    results: List[FileAuditResult] = []

    for file in code_files:
        logger.info("[AUDIT] Processing: %s", file.path)
        try:
            output = run_audit_on_code(file.content)
            results.append(FileAuditResult(
                file_path=file.path,
                final_report=output.get("final_report", ""),
            ))
        except Exception as exc:
            logger.error("[AUDIT] Failed for %s: %s", file.path, exc)
            results.append(FileAuditResult(
                file_path=file.path,
                error=str(exc),
            ))

    logger.info("[AUDIT] Completed — %d file(s) processed", len(results))

    return AuditResultResponse(
        total_files=len(results),
        results=results,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/audit/stream")
def audit_stream_start(request: AuditRequest, background_tasks: BackgroundTasks) -> dict:
    """Start a code audit in the background and return a job_id.

    Args:
        request: Validated AuditRequest body.
        background_tasks: FastAPI background tasks dependency.

    Returns:
        Dict containing ``job_id``.
    """
    logger.info("Received background audit request — input_type: %s", request.input_type)
    code_files = _resolve_code_files(request)
    logger.info("Extracted %d file(s), creating background job", len(code_files))

    job_id = create_job()
    background_tasks.add_task(_run_audit_job, job_id, code_files)

    return {"job_id": job_id}


@app.get("/audit/stream/{job_id}")
async def audit_stream_subscribe(job_id: str) -> StreamingResponse:
    """Subscribe to a background audit job via Server-Sent Events.

    Args:
        job_id: The UUID of the job from POST /audit/stream.

    Returns:
        StreamingResponse yielding structured JSON SSE events.
    """
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    return StreamingResponse(
        _stream_job_events(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/audit", response_model=AuditResultResponse)
def audit_code(request: AuditRequest) -> AuditResultResponse:
    """Run a full code audit (sync fallback)."""
    logger.info("Received sync audit request — input_type: %s", request.input_type)
    code_files = _resolve_code_files(request)
    return _run_audit_on_files(code_files)


@app.post("/audit/upload", response_model=AuditResultResponse)
async def audit_upload(files: List[UploadFile] = File(...)) -> AuditResultResponse:
    """Run a full code audit via file upload (sync)."""
    logger.info("Received upload audit request — %d file(s)", len(files))
    code_files = await process_uploaded_files(files)
    return _run_audit_on_files(code_files)


@app.get("/health")
def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}
