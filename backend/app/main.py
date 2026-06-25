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
    import time
    from backend.app.services.job_store import cleanup_old_jobs
    
    # Prune old jobs from memory whenever a new one starts
    cleanup_old_jobs()

    job = get_job(job_id)
    if not job:
        return

    job["status"] = "running"
    job["total_files"] = len(code_files)
    results: List[dict] = []
    start_time = time.time()

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

            def event_callback(event_type: str, payload: dict) -> None:
                add_job_event(job_id, event_type, payload)

            try:
                # Execute audit with a 30s timeout per file
                import concurrent.futures
                
                def _run():
                    return run_audit_on_code(
                        file.content,
                        log_callback=log_callback,
                        event_callback=event_callback,
                        repository_file_count=len(code_files),
                    )
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run)
                    # Extend timeout to 120 seconds to accommodate slower LLMs or larger files
                    output = future.result(timeout=120)

                final_report_str = output.get("final_report", "")
                risk_score = 0.0
                try:
                    report_data = json.loads(final_report_str)
                    risk_score = report_data.get("risk_score", 0.0)
                except Exception:
                    pass

                file_result = {
                    "file_path": file.path,
                    "final_report": final_report_str,
                    "risk_score": risk_score,
                    "error": None,
                }
                results.append(file_result)

                add_job_event(job_id, "risk_update", {"file_path": file.path, "risk_score": risk_score})
                add_job_event(job_id, "result", file_result)
                
            except concurrent.futures.TimeoutError:
                error_msg = f"Timed out after 30 seconds"
                file_result = {
                    "file_path": file.path,
                    "final_report": "",
                    "risk_score": 0.0,
                    "error": error_msg,
                }
                results.append(file_result)
                add_job_event(job_id, "result", file_result)
                add_job_event(job_id, "log", {
                    "agent": "System",
                    "message": f"Failed: {file.path} — {error_msg}",
                    "level": "error",
                })

            except Exception as exc:
                file_result = {
                    "file_path": file.path,
                    "final_report": "",
                    "risk_score": 0.0,
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


        # Compute top risk files
        file_risks = []
        for res in results:
            try:
                if res["risk_score"] > 0:
                    file_risks.append({"file_path": res["file_path"], "risk_score": res["risk_score"]})
            except Exception:
                pass

        file_risks.sort(key=lambda x: x["risk_score"], reverse=True)
        top_risk_files = file_risks[:5] # e.g. top 5

        # Accumulate total findings
        total_findings = 0
        for res in results:
            try:
                report_data = json.loads(res["final_report"])
                total_findings += len(report_data.get("findings", []))
            except Exception:
                pass

        job["total_findings"] = total_findings

        # inject top risk files into results so frontend can access them, or emit as a separate event
        # Here we just emit a final top_risk_files event or include in 'done'
        duration = round(time.time() - start_time, 2)
        add_job_event(job_id, "done", {"total_files": len(results), "duration": duration, "top_risk_files": top_risk_files})
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
    ticks_without_event = 0

    while True:
        # Yield any new events
        current_events = job["events"]
        had_events = False
        while last_index < len(current_events):
            event = current_events[last_index]
            yield f"data: {json.dumps(event)}\n\n"
            last_index += 1
            had_events = True

        if had_events:
            ticks_without_event = 0
        else:
            ticks_without_event += 1

        # Check if complete
        if job["status"] in ("completed", "failed"):
            # Ensure all final events are yielded
            while last_index < len(job["events"]):
                event = job["events"][last_index]
                yield f"data: {json.dumps(event)}\n\n"
                last_index += 1
            break

        # Yield a heartbeat every ~2 seconds (4 * 0.5s checks)
        if ticks_without_event >= 4:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            ticks_without_event = 0

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

    import concurrent.futures

    def _process_file(file):
        logger.info("[AUDIT] Processing: %s", file.path)
        try:
            output = run_audit_on_code(file.content, repository_file_count=len(code_files))
            final_report_str = output.get("final_report", "")
            risk_score = 0.0
            try:
                report_data = json.loads(final_report_str)
                risk_score = report_data.get("risk_score", 0.0)
            except Exception:
                pass
            return FileAuditResult(
                file_path=file.path,
                final_report=final_report_str,
                risk_score=risk_score,
            )
        except Exception as exc:
            logger.error("[AUDIT] Failed for %s: %s", file.path, exc)
            return FileAuditResult(
                file_path=file.path,
                error=str(exc),
            )

    # Use ThreadPoolExecutor to run tests concurrently where possible (mostly limited by LLM concurrency though)
    # But it allows concurrent preparation and formatting. We keep it to min of len or 4.
    max_workers = max(1, min(len(code_files), 4))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_process_file, code_files))

    # Calculate top risk files across the whole repo and inject into final_report so sync returns it
    file_risks = []
    for r in results:
        if r.risk_score > 0:
            file_risks.append({"file_path": r.file_path, "risk_score": r.risk_score})
    file_risks.sort(key=lambda x: x["risk_score"], reverse=True)
    top_risk_files = file_risks[:5]

    for r in results:
        if not r.error and r.final_report:
            try:
                report_data = json.loads(r.final_report)
                report_data["top_risk_files"] = top_risk_files
                r.final_report = json.dumps(report_data)
            except Exception:
                pass

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

    input_identifier = "Paste/Upload"
    if request.input_type == "github":
        input_identifier = request.github_url.split("github.com/")[-1] if request.github_url else "GitHub Repo"
    elif request.input_type == "paste":
        input_identifier = "Pasted Code"

    job_id = create_job(input_identifier)
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

@app.get("/metrics")
def get_metrics() -> list:
    """Returns dashboard metrics based on job store data."""
    from backend.app.services.job_store import jobs

    # Snapshot jobs.values() to avoid dict changing size during iteration
    jobs_snapshot = list(jobs.values())
    total_audits = len(jobs_snapshot)
    completed_audits = sum(1 for j in jobs_snapshot if j["status"] == "completed")
    failed_audits = sum(1 for j in jobs_snapshot if j["status"] == "failed")

    return [
        {
            "label": "Total Audits",
            "value": total_audits,
            "trend": 0,
            "trendDirection": "up",
            "icon": "folder-git-2"
        },
        {
            "label": "Completed",
            "value": completed_audits,
            "trend": 0,
            "trendDirection": "up",
            "icon": "gauge"
        },
        {
            "label": "Failed",
            "value": failed_audits,
            "trend": 0,
            "trendDirection": "down",
            "icon": "bug"
        }
    ]

@app.get("/trends")
def get_trends() -> list:
    """Returns empty trends for now as it needs a persistent db for meaningful data."""
    return []

class SettingsUpdate(BaseModel):
    model: str

@app.post("/settings")
def update_settings(settings: SettingsUpdate) -> dict:
    """Updates global backend settings (like model name)."""
    from src.config import Config
    Config.MODEL_NAME = settings.model
    return {"status": "ok", "model": Config.MODEL_NAME}

@app.get("/settings/ollama")
def check_ollama() -> dict:
    """Checks if Ollama is accessible."""
    import requests
    from src.config import Config
    try:
        response = requests.get(Config.OLLAMA_BASE_URL, timeout=5)
        if response.status_code == 200:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=503, detail="Ollama returned non-200 status")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama connection failed: {str(e)}")

@app.get("/recent-audits")
def get_recent_audits() -> list:
    """Returns recent audits from the job store."""
    from backend.app.services.job_store import jobs
    import datetime

    recent = []
    # sort jobs by created_at descending
    sorted_jobs = sorted(jobs.items(), key=lambda x: x[1]["created_at"], reverse=True)

    for jid, jdata in sorted_jobs[:5]:
        recent.append({
            "id": jid,
            "repository": jdata.get("input_identifier", "Audit Job"),
            "date": datetime.datetime.fromtimestamp(jdata["created_at"]).isoformat(),
            "status": jdata["status"],
            "findings": jdata.get("total_findings", 0)
        })

    return recent
