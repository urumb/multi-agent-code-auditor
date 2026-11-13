# Author: urumb
"""Running audits: background jobs (streamed over SSE) and the sync fallback.

Both paths audit each file through ``audit_file`` and describe the outcome
with ``file_result``, so a file's result has one shape everywhere.
"""
import asyncio
import concurrent.futures
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException

from backend.app.schemas.code_file import AuditResultResponse, CodeFile, FileAuditResult
from backend.app.services import db
from backend.app.services.audit_runner import run_audit_on_code
from backend.app.services.input_processor import process_github_repo
from backend.app.services.job_store import add_job_event, finalize_job, get_job
from src.config import Config

logger = logging.getLogger(__name__)

TOP_RISK_FILES = 5


# ---------------------------------------------------------------------------
# One file
# ---------------------------------------------------------------------------
def report_risk(final_report: str) -> Tuple[float, str]:
    """(risk_score, max_severity) from a report JSON string; safe defaults."""
    try:
        data = json.loads(final_report)
        return data.get("risk_score", 0.0), data.get("max_severity", "Low")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0.0, "Low"


def file_result(path: str, final_report: str = "", error: Optional[str] = None) -> Dict[str, Any]:
    """The result record for one audited file (also used for failures)."""
    risk_score, max_severity = report_risk(final_report) if final_report else (0.0, "Low")
    return {
        "file_path": path,
        "final_report": final_report,
        "risk_score": risk_score,
        "max_severity": max_severity,
        "error": error,
    }


def audit_file(
    file: CodeFile,
    total_files: int,
    depth: str = "full",
    *,
    cancel_event: Optional[threading.Event] = None,
    log_callback: Optional[Callable[..., None]] = None,
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Run the pipeline on one file and return its ``file_result``. Raises on failure."""
    output = run_audit_on_code(
        file.content,
        log_callback=log_callback,
        event_callback=event_callback,
        repository_file_count=total_files,
        depth=depth,
        cancel_event=cancel_event,
        file_path=file.path,
    )
    return file_result(file.path, output.get("final_report", ""))


def top_risk_files(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    risky = [
        {"file_path": r["file_path"], "risk_score": r["risk_score"]}
        for r in results
        if (r.get("risk_score") or 0) > 0
    ]
    risky.sort(key=lambda x: x["risk_score"], reverse=True)
    return risky[:TOP_RISK_FILES]


def cap_file_count(code_files: List[CodeFile], job_id: Optional[str] = None) -> List[CodeFile]:
    """Cap the number of files audited in one run so a huge repository can't
    turn into an unbounded-length job. Keeps the smallest files (cheapest to
    analyze, and more of them fit), and records how many were skipped."""
    limit = Config.MAX_FILES_PER_AUDIT
    if len(code_files) <= limit:
        return code_files

    kept = sorted(code_files, key=lambda f: len(f.content))[:limit]
    skipped = len(code_files) - len(kept)
    message = (
        f"Repository contains {len(code_files)} auditable files — capping this run to the "
        f"{limit} smallest files ({skipped} skipped) to keep runtime bounded."
    )
    logger.warning(message)
    if job_id:
        job = get_job(job_id)
        if job:
            job["files_skipped"] = skipped
        add_job_event(job_id, "log", {"agent": "System", "message": message, "level": "warning"})
    return kept


# ---------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------
def _log(job_id: str, message: str, level: str = "info") -> None:
    add_job_event(job_id, "log", {"agent": "System", "message": message, "level": level})


def _audit_file_with_timeout(job_id: str, file: CodeFile, total: int, depth: str) -> Dict[str, Any]:
    """Audit one file inside a job, giving up after PER_FILE_TIMEOUT_SECONDS."""
    # Once set, this both cancels the file's remaining LLM calls (so it
    # releases the shared LLM slot instead of starving the next file) and
    # suppresses further events from it — a slow thread finishing after we
    # moved on can't append stale events (e.g. a late "Pipeline completed")
    # to this job's stream.
    abandoned = threading.Event()

    def log_callback(agent: str, message: str, level: str = "info") -> None:
        if not abandoned.is_set():
            add_job_event(job_id, "log", {"agent": agent, "message": message, "level": level})

    def event_callback(event_type: str, payload: dict) -> None:
        if not abandoned.is_set():
            add_job_event(job_id, event_type, payload)

    # Deliberately not a `with` block: ThreadPoolExecutor.__exit__ waits for
    # the task, which would make the timeout cosmetic. Python can't kill a
    # thread, so on timeout we abandon it (shutdown(wait=False)); the cancel
    # event makes it stop at its next LLM call.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        audit_file, file, total, depth,
        cancel_event=abandoned, log_callback=log_callback, event_callback=event_callback,
    )
    try:
        return future.result(timeout=Config.PER_FILE_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        abandoned.set()
        raise
    finally:
        executor.shutdown(wait=False)


def run_audit_job(job_id: str, code_files: List[CodeFile], depth: str = "full") -> None:
    """Background task: audit every file, streaming events into the job store."""
    job = get_job(job_id)
    if not job:
        return

    job["status"] = "running"
    job["total_files"] = len(code_files)
    db.set_status(job_id, "running")
    results: List[Dict[str, Any]] = []
    start_time = time.time()
    total = len(code_files)

    try:
        _log(job_id, f"Starting background audit — {total} file(s) queued")

        for i, file in enumerate(code_files, start=1):
            add_job_event(job_id, "file_start", {"path": file.path, "index": i, "total": total})
            _log(job_id, f"[{i}/{total}] Processing: {file.path}")

            try:
                result = _audit_file_with_timeout(job_id, file, total, depth)
                add_job_event(job_id, "risk_update", {"file_path": file.path, "risk_score": result["risk_score"]})
            except concurrent.futures.TimeoutError:
                result = file_result(file.path, error=f"Timed out after {Config.PER_FILE_TIMEOUT_SECONDS:g} seconds")
            except Exception as exc:
                result = file_result(file.path, error=str(exc))

            results.append(result)
            add_job_event(job_id, "result", result)
            if result["error"]:
                _log(job_id, f"Failed: {file.path} — {result['error']}", "error")
            add_job_event(job_id, "file_done", {"path": file.path, "index": i, "total": total})

        duration = round(time.time() - start_time, 2)
        add_job_event(job_id, "done", {
            "total_files": len(results),
            "files_skipped": job.get("files_skipped", 0),
            "duration": duration,
            "top_risk_files": top_risk_files(results),
        })
        job["status"] = "completed"
        finalize_job(job_id, "completed", results=results, duration=duration)

    except Exception as exc:
        logger.error("Background job %s failed: %s", job_id, exc)
        add_job_event(job_id, "error", {"message": str(exc)})
        job["status"] = "failed"
        finalize_job(job_id, "failed", results=results,
                     duration=round(time.time() - start_time, 2), error=str(exc))


def run_github_audit_job(job_id: str, github_url: str, depth: str = "full") -> None:
    """Background task: clone a GitHub repo, then audit it.

    Cloning happens here rather than in the request handler, so the endpoint
    returns a job_id immediately and the UI shows live "Cloning..." progress
    instead of the request appearing to hang for up to two minutes.
    """
    job = get_job(job_id)
    if not job:
        return

    _log(job_id, f"Cloning repository: {github_url}")
    start_time = time.time()
    try:
        code_files = cap_file_count(process_github_repo(github_url), job_id=job_id)
    except Exception as exc:
        message = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
        _log(job_id, f"Failed: {message}", "error")
        add_job_event(job_id, "error", {"message": message})
        job["status"] = "failed"
        db.set_status(job_id, "failed")
        finalize_job(job_id, "failed", results=[], duration=round(time.time() - start_time, 2), error=message)
        return

    _log(job_id, f"Cloned repository — {len(code_files)} auditable file(s) found", "success")
    run_audit_job(job_id, code_files, depth)


async def stream_job_events(job_id: str):
    """Yield a job's events as SSE until it completes or fails, with a
    heartbeat every ~2s so proxies and the browser keep the stream open."""
    job = get_job(job_id)
    if not job:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Job not found'}})}\n\n"
        return

    last_index = 0
    idle_ticks = 0
    while True:
        events = job["events"]
        sent = False
        while last_index < len(events):
            yield f"data: {json.dumps(events[last_index])}\n\n"
            last_index += 1
            sent = True
        idle_ticks = 0 if sent else idle_ticks + 1

        if job["status"] in ("completed", "failed"):
            while last_index < len(job["events"]):
                yield f"data: {json.dumps(job['events'][last_index])}\n\n"
                last_index += 1
            break

        if idle_ticks >= 4:  # 4 x 0.5s
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            idle_ticks = 0
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Synchronous fallback
# ---------------------------------------------------------------------------
def run_audit_on_files(code_files: List[CodeFile]) -> AuditResultResponse:
    """Audit files synchronously (no job, no streaming) and return all results."""

    def _one(file: CodeFile) -> Dict[str, Any]:
        logger.info("[AUDIT] Processing: %s", file.path)
        try:
            return audit_file(file, len(code_files))
        except Exception as exc:
            logger.error("[AUDIT] Failed for %s: %s", file.path, exc)
            return file_result(file.path, error=str(exc))

    # Up to 4 threads overlap pre/post-processing; LLM calls themselves are
    # still serialized by the LLM slot in src/llm.py.
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(len(code_files), 4))) as pool:
        results = list(pool.map(_one, code_files))

    # Include the cross-file ranking in each report, since the sync response
    # has no separate "done" event to carry it.
    ranking = top_risk_files(results)
    for r in results:
        if not r["error"] and r["final_report"]:
            try:
                report = json.loads(r["final_report"])
                report["top_risk_files"] = ranking
                r["final_report"] = json.dumps(report)
            except json.JSONDecodeError:
                pass

    logger.info("[AUDIT] Completed — %d file(s) processed", len(results))
    return AuditResultResponse(
        total_files=len(results),
        results=[FileAuditResult(**r) for r in results],
    )
