# Author: urumb
import concurrent.futures
import json
import logging
import os
import asyncio
import threading
import time
from typing import List

from pydantic import BaseModel

from fastapi import FastAPI, File, Form, UploadFile, BackgroundTasks, HTTPException
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
from backend.app.services.job_store import (
    create_job,
    get_job,
    add_job_event,
    finalize_job,
)
from backend.app.services import db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Hard timeout for auditing a single file, covering every agent LLM call for
# that file's snippets (up to ManagerAgent.MAX_SNIPPETS chunks x 3 analysis
# agents, plus one reviewer call — all serialized through a single local
# Ollama instance). 240s gives realistic local-LLM inference room on modest
# hardware while still guaranteeing a bounded, non-infinite wait.
PER_FILE_TIMEOUT_SECONDS = 240

# Safety limits on repository/upload size so a single audit request cannot
# exhaust memory, disk, or run for an unbounded amount of time.
# Each file costs roughly a minute on a CPU-only machine, so the default cap is
# modest; raise it via env (MAX_FILES_PER_AUDIT) if you have a GPU.
MAX_FILES_PER_AUDIT = int(os.getenv("MAX_FILES_PER_AUDIT", "25"))

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Multi-Agent Code Auditor",
    description="Phase 5 — Background SSE streaming and speed optimization.",
    version="0.5.0",
)

from src.config import Config

app.add_middleware(
    CORSMiddleware,
    # Explicit allowlist, not a wildcard: this server has no authentication,
    # so an unrestricted CORS policy would let any website the user has
    # open silently trigger audits or read past results via fetch().
    allow_origins=Config.FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    db.init_db()
    # Pre-load the model so the first audit doesn't pay the cold-start cost.
    from src.llm import warm_up_model
    warm_up_model()


# ---------------------------------------------------------------------------
# Background Job Execution
# ---------------------------------------------------------------------------
def _run_audit_job(job_id: str, code_files: List[CodeFile], depth: str = "full") -> None:
    """Background task that runs the audit and pushed events to job_store.

    Args:
        job_id: UUID of the job.
        code_files: List of CodeFile objects to audit.
    """
    from backend.app.services.job_store import cleanup_old_jobs

    # Prune old jobs from memory whenever a new one starts
    cleanup_old_jobs()

    job = get_job(job_id)
    if not job:
        return

    job["status"] = "running"
    job["total_files"] = len(code_files)
    db.set_status(job_id, "running")
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

            # Once set, suppresses further events from this file's audit —
            # used when we give up waiting on a timed-out run, so a slow
            # background thread that finishes *after* we've already moved on
            # can't append stale/contradictory events (e.g. a late "Pipeline
            # completed successfully" arriving after we already reported a
            # timeout) into this job's stream.
            abandoned = threading.Event()

            def log_callback(agent: str, message: str, level: str = "info") -> None:
                if abandoned.is_set():
                    return
                add_job_event(job_id, "log", {"agent": agent, "message": message, "level": level})

            def event_callback(event_type: str, payload: dict) -> None:
                if abandoned.is_set():
                    return
                add_job_event(job_id, event_type, payload)

            try:
                def _run():
                    return run_audit_on_code(
                        file.content,
                        log_callback=log_callback,
                        event_callback=event_callback,
                        repository_file_count=len(code_files),
                        depth=depth,
                    )

                # Deliberately not a `with` block: ThreadPoolExecutor.__exit__
                # calls shutdown(wait=True), which would block here until the
                # submitted task finishes regardless of the timeout below —
                # making the timeout below purely cosmetic. Python has no way
                # to forcibly kill a running thread, so on timeout we instead
                # abandon it via shutdown(wait=False) and move on; the thread
                # finishes on its own, but callers of this job are not stuck
                # waiting for it.
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = executor.submit(_run)
                try:
                    output = future.result(timeout=PER_FILE_TIMEOUT_SECONDS)
                finally:
                    executor.shutdown(wait=False)

                final_report_str = output.get("final_report", "")
                risk_score = 0.0
                max_severity = "Low"
                try:
                    report_data = json.loads(final_report_str)
                    risk_score = report_data.get("risk_score", 0.0)
                    max_severity = report_data.get("max_severity", "Low")
                except Exception:
                    pass

                file_result = {
                    "file_path": file.path,
                    "final_report": final_report_str,
                    "risk_score": risk_score,
                    "max_severity": max_severity,
                    "error": None,
                }
                results.append(file_result)

                add_job_event(job_id, "risk_update", {"file_path": file.path, "risk_score": risk_score})
                add_job_event(job_id, "result", file_result)

            except concurrent.futures.TimeoutError:
                abandoned.set()
                error_msg = f"Timed out after {PER_FILE_TIMEOUT_SECONDS} seconds"
                file_result = {
                    "file_path": file.path,
                    "final_report": "",
                    "risk_score": 0.0,
                    "max_severity": "Low",
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
                    "max_severity": "Low",
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
        finalize_job(job_id, "completed", results=results, duration=duration)

    except Exception as exc:
        logger.error("Background job %s failed: %s", job_id, exc)
        add_job_event(job_id, "error", {"message": str(exc)})
        job["status"] = "failed"
        finalize_job(
            job_id,
            "failed",
            results=results,
            duration=round(time.time() - start_time, 2),
            error=str(exc),
        )


def _run_github_audit_job(job_id: str, github_url: str, depth: str = "full") -> None:
    """Background task that clones a GitHub repo, then hands off to
    _run_audit_job for the actual analysis.

    Cloning happens here — in the background — rather than inside the
    POST /audit/stream request handler, so the endpoint returns a job_id
    (and the frontend gets a live "Cloning..." event) immediately instead of
    the request appearing to hang for up to two minutes while git clone and
    the pre-clone size check run.
    """
    job = get_job(job_id)
    if not job:
        return

    add_job_event(job_id, "log", {
        "agent": "System",
        "message": f"Cloning repository: {github_url}",
        "level": "info",
    })

    start_time = time.time()
    try:
        code_files = _cap_file_count(process_github_repo(github_url), job_id=job_id)
    except HTTPException as exc:
        message = str(exc.detail)
        add_job_event(job_id, "log", {"agent": "System", "message": f"Failed: {message}", "level": "error"})
        add_job_event(job_id, "error", {"message": message})
        job["status"] = "failed"
        db.set_status(job_id, "failed")
        finalize_job(job_id, "failed", results=[], duration=round(time.time() - start_time, 2), error=message)
        return
    except Exception as exc:
        add_job_event(job_id, "log", {"agent": "System", "message": f"Failed: {exc}", "level": "error"})
        add_job_event(job_id, "error", {"message": str(exc)})
        job["status"] = "failed"
        db.set_status(job_id, "failed")
        finalize_job(job_id, "failed", results=[], duration=round(time.time() - start_time, 2), error=str(exc))
        return

    add_job_event(job_id, "log", {
        "agent": "System",
        "message": f"Cloned repository — {len(code_files)} auditable file(s) found",
        "level": "success",
    })
    _run_audit_job(job_id, code_files, depth)


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
        return process_pasted_code(request.code, request.language)
    return []


def _cap_file_count(code_files: List[CodeFile], job_id: str | None = None) -> List[CodeFile]:
    """Cap the number of files audited in one run so a huge repository can't
    turn into an unbounded-length background job. Keeps the smallest files
    first (cheapest/fastest to analyze, and more of them fit in the cap)."""
    if len(code_files) <= MAX_FILES_PER_AUDIT:
        return code_files

    sorted_files = sorted(code_files, key=lambda f: len(f.content))
    kept = sorted_files[:MAX_FILES_PER_AUDIT]
    skipped = len(code_files) - len(kept)
    message = (
        f"Repository contains {len(code_files)} auditable files — capping this run to the "
        f"{MAX_FILES_PER_AUDIT} smallest files ({skipped} skipped) to keep runtime bounded."
    )
    logger.warning(message)
    if job_id:
        add_job_event(job_id, "log", {"agent": "System", "message": message, "level": "warning"})
    return kept


def _run_audit_on_files(code_files: List[CodeFile]) -> AuditResultResponse:
    """Run the LangGraph audit pipeline synchronously (fallback)."""
    results: List[FileAuditResult] = []

    def _process_file(file):
        logger.info("[AUDIT] Processing: %s", file.path)
        try:
            output = run_audit_on_code(file.content, repository_file_count=len(code_files))
            final_report_str = output.get("final_report", "")
            risk_score = 0.0
            max_severity = "Low"
            try:
                report_data = json.loads(final_report_str)
                risk_score = report_data.get("risk_score", 0.0)
                max_severity = report_data.get("max_severity", "Low")
            except Exception:
                pass
            return FileAuditResult(
                file_path=file.path,
                final_report=final_report_str,
                risk_score=risk_score,
                max_severity=max_severity,
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

    if request.input_type == "github":
        if not request.github_url:
            raise HTTPException(status_code=400, detail="github_url is required")
        # Cloning can take up to ~2 minutes — do it inside the background
        # job (not here) so this endpoint returns immediately and the
        # frontend can show live "Cloning..." progress instead of the
        # request appearing to hang.
        input_identifier = request.github_url.split("github.com/")[-1]
        job_id = create_job(input_identifier, input_type="github")
        background_tasks.add_task(_run_github_audit_job, job_id, request.github_url, request.depth)
        return {"job_id": job_id}

    # Paste input is already in-memory and instant to resolve.
    code_files = process_pasted_code(request.code, request.language)
    logger.info("Extracted %d file(s), creating background job", len(code_files))

    job_id = create_job("Pasted Code", input_type="paste")
    code_files = _cap_file_count(code_files, job_id=job_id)
    background_tasks.add_task(_run_audit_job, job_id, code_files, request.depth)

    return {"job_id": job_id}


@app.post("/audit/stream/upload")
async def audit_stream_upload_start(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    depth: str = Form("full"),
) -> dict:
    """Start a file-upload audit in the background and return a job_id.

    Mirrors POST /audit/stream but for multipart file uploads, so uploaded
    files get the same live SSE progress, history persistence, and dashboard
    visibility as GitHub/paste audits instead of only a synchronous result.
    """
    logger.info("Received background upload audit request — %d file(s)", len(files))
    code_files = await process_uploaded_files(files)

    input_identifier = (
        code_files[0].path if len(code_files) == 1 else f"{len(code_files)} uploaded files"
    )
    job_id = create_job(input_identifier, input_type="upload")
    code_files = _cap_file_count(code_files, job_id=job_id)
    background_tasks.add_task(_run_audit_job, job_id, code_files, depth if depth in ("quick", "full") else "full")

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
    code_files = _cap_file_count(_resolve_code_files(request))
    return _run_audit_on_files(code_files)


@app.post("/audit/upload", response_model=AuditResultResponse)
async def audit_upload(files: List[UploadFile] = File(...)) -> AuditResultResponse:
    """Run a full code audit via file upload (sync)."""
    logger.info("Received upload audit request — %d file(s)", len(files))
    code_files = _cap_file_count(await process_uploaded_files(files))
    return _run_audit_on_files(code_files)


@app.get("/health")
def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}

@app.get("/metrics")
def get_metrics() -> list:
    """Returns dashboard metrics from the persistent audit history."""
    counts = db.count_jobs()

    return [
        {
            "label": "Total Audits",
            "value": counts["total"],
            "trend": 0,
            "trendDirection": "up",
            "icon": "folder-git-2"
        },
        {
            "label": "Completed",
            "value": counts["completed"],
            "trend": 0,
            "trendDirection": "up",
            "icon": "gauge"
        },
        {
            "label": "Failed",
            "value": counts["failed"],
            "trend": 0,
            "trendDirection": "down",
            "icon": "bug"
        }
    ]

@app.get("/trends")
def get_trends() -> list:
    """Returns real findings-by-severity trend data derived from completed
    audit history. Empty until at least one audit has completed — never
    fabricated."""
    return db.severity_trend(days=14)

class SettingsUpdate(BaseModel):
    model: str

def _model_installed(requested: str, installed: list[str]) -> bool:
    # Ollama lists "llama3.2:latest" for a model pulled as "llama3.2".
    return requested in installed or f"{requested}:latest" in installed


@app.get("/settings/models")
def list_models() -> dict:
    """Models actually installed in the local Ollama, plus the active one."""
    from src.config import Config
    from src.llm import installed_models
    try:
        models = installed_models()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not list Ollama models: {e}")
    return {"models": models, "current": Config.MODEL_NAME}


@app.post("/settings")
def update_settings(settings: SettingsUpdate) -> dict:
    """Switch the active model. Rejects models that aren't installed, so a
    typo or un-pulled model fails here instead of failing every audit."""
    from src.config import Config
    from src.llm import installed_models, warm_up_model
    try:
        installed = installed_models()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama is not reachable: {e}")
    if not _model_installed(settings.model, installed):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{settings.model}' is not installed. Run: ollama pull {settings.model}",
        )
    if Config.MODEL_NAME != settings.model:
        Config.MODEL_NAME = settings.model
        warm_up_model()
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

def _job_row_to_summary(row: dict) -> dict:
    import datetime

    return {
        "id": row["id"],
        "repository": row.get("input_identifier", "Audit Job"),
        "date": datetime.datetime.fromtimestamp(row["created_at"]).isoformat(),
        "status": row["status"],
        "findings": row.get("total_findings", 0),
        "max_severity": row.get("max_severity", "Low"),
        "duration": row.get("duration"),
        "input_type": row.get("input_type", "unknown"),
        "files_errored": row.get("files_errored", 0),
    }


@app.get("/recent-audits")
def get_recent_audits() -> list:
    """Returns the 5 most recent audits from persistent history."""
    return [_job_row_to_summary(row) for row in db.list_jobs(limit=5)]


@app.get("/audit/history")
def get_audit_history(limit: int = 20, offset: int = 0) -> list:
    """Returns paginated audit history for the History page."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return [_job_row_to_summary(row) for row in db.list_jobs(limit=limit, offset=offset)]


@app.get("/audit/history/{job_id}")
def get_audit_history_detail(job_id: str) -> dict:
    """Returns the full persisted results for one past audit, so a History
    entry can be reopened even after the live SSE job has expired from
    memory or the backend has restarted."""
    detail = db.get_job_detail(job_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Audit not found")
    return {
        "id": detail["id"],
        "repository": detail.get("input_identifier", "Audit Job"),
        "status": detail["status"],
        "input_type": detail.get("input_type", "unknown"),
        "created_at": detail["created_at"],
        "duration": detail.get("duration"),
        "error": detail.get("error"),
        "total_files": detail.get("total_files", 0),
        "results": detail.get("results", []),
    }
