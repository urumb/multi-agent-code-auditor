import uuid
import time
from typing import Any, Dict

# In-memory job store mapping step. Ideally this would be Redis/PostgreSQL in prod.
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

def create_job() -> str:
    """Create a new job and return its ID."""
    now = time.time()
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "events": [],
        "total_files": 0,
        "created_at": now,
        "last_updated": now
    }
    return job_id

def get_job(job_id: str) -> Dict[str, Any] | None:
    """Retrieve job state by ID."""
    return jobs.get(job_id)

def add_job_event(job_id: str, event_type: str, payload: dict):
    """Append a structured SSE event to the job's event list."""
    job = jobs.get(job_id)
    if job:
        job["events"].append({"type": event_type, "data": payload})
        job["last_updated"] = time.time()

def cleanup_old_jobs():
    """Remove jobs older than 30 minutes to save memory."""
    now = time.time()
    expired_keys = [
        k for k, v in jobs.items()
        if (now - v["last_updated"]) > 1800  # 30 mins
    ]
    for k in expired_keys:
        del jobs[k]

