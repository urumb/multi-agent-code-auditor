import threading
import uuid
import time
from typing import Any, Dict, List, Optional

from backend.app.services import db

# In-memory store for LIVE jobs only — SSE event history for jobs currently
# streaming or recently finished. This is intentionally ephemeral: an audit
# that was mid-flight during a backend restart can't be resumed anyway (the
# in-process LangGraph run is gone with it), so there's no point persisting
# raw event logs. Completed/failed jobs are snapshotted into SQLite
# (services/db.py) for durable History/metrics access.
#
# Structure:
# {
#   "job-uuid": {
#       "status": "pending" | "running" | "completed" | "failed",
#       "events": [{"type": "...", "data": {...}}],
#       "total_files": 0,
#       "created_at": float,
#       "last_updated": float
#   }
# }
jobs: Dict[str, Dict[str, Any]] = {}

# Jobs are created from request handlers and updated from background-task
# threads at the same time; this lock guards changes to the ``jobs`` dict and
# each job's event list so cleanup can't iterate while another thread inserts.
_lock = threading.RLock()

# Finished jobs' event logs are dropped after this long without updates.
JOB_TTL_SECONDS = 30 * 60
# Hard cap on jobs kept in memory; the oldest *finished* jobs are evicted
# first, so a burst of audits can't grow memory without bound.
MAX_LIVE_JOBS = 100
_FINISHED = ("completed", "failed")


def create_job(input_identifier: str = "Unknown Input", input_type: str = "unknown") -> str:
    """Create a new job and return its ID."""
    cleanup_old_jobs()
    now = time.time()
    job_id = str(uuid.uuid4())
    job = {
        "status": "pending",
        "events": [],
        "total_files": 0,
        "created_at": now,
        "last_updated": now,
        "input_identifier": input_identifier,
        "input_type": input_type,
        "total_findings": 0,
        "files_skipped": 0,
    }
    with _lock:
        jobs[job_id] = job
    # Persist immediately so the job shows up (as "pending"/"running") in
    # history/dashboard views even before it finishes, and so it isn't lost
    # if the backend restarts mid-run.
    db.upsert_job(
        job_id=job_id,
        input_identifier=input_identifier,
        input_type=input_type,
        status="pending",
        created_at=now,
    )
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve live job state by ID (in-memory only)."""
    return jobs.get(job_id)


def add_job_event(job_id: str, event_type: str, payload: dict):
    """Append a structured SSE event to the job's event list."""
    with _lock:
        job = jobs.get(job_id)
        if job:
            job["events"].append({"type": event_type, "data": payload})
            job["last_updated"] = time.time()


def finalize_job(
    job_id: str,
    status: str,
    results: Optional[List[Dict[str, Any]]] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Persist a completed/failed job's final snapshot to durable storage."""
    job = jobs.get(job_id)
    if not job:
        return

    total_findings = 0
    max_severity = "Low"
    severity_rank = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    for r in results or []:
        report = r.get("final_report")
        if not report:
            continue
        import json
        try:
            data = json.loads(report)
        except (json.JSONDecodeError, TypeError):
            continue
        total_findings += len(data.get("findings", []))
        sev = data.get("max_severity", "Low")
        if severity_rank.get(sev, 0) > severity_rank.get(max_severity, 0):
            max_severity = sev

    job["total_findings"] = total_findings

    db.upsert_job(
        job_id=job_id,
        input_identifier=job.get("input_identifier", "Unknown Input"),
        input_type=job.get("input_type", "unknown"),
        status=status,
        created_at=job["created_at"],
        completed_at=time.time(),
        duration=duration,
        total_files=job.get("total_files", len(results or [])),
        total_findings=total_findings,
        max_severity=max_severity,
        error=error,
        results=results,
        files_skipped=job.get("files_skipped", 0),
    )


def cleanup_old_jobs():
    """Drop in-memory event history for finished jobs that are stale or over the cap.

    Safe to do unconditionally now: completed/failed jobs are already
    durably persisted via finalize_job(), so dropping them from memory only
    discards the replayable SSE event log (which live viewers no longer
    need) — not the audit results themselves.
    """
    now = time.time()
    with _lock:
        expired = [
            k for k, v in jobs.items()
            if v["status"] in _FINISHED and (now - v["last_updated"]) > JOB_TTL_SECONDS
        ]
        for k in expired:
            del jobs[k]

        overflow = len(jobs) - MAX_LIVE_JOBS
        if overflow > 0:
            finished = sorted(
                (k for k, v in jobs.items() if v["status"] in _FINISHED),
                key=lambda k: jobs[k]["last_updated"],
            )
            for k in finished[:overflow]:
                del jobs[k]
