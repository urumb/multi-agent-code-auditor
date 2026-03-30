import uuid
from typing import Any, Dict

# In-memory job store mapping step. Ideally this would be Redis/PostgreSQL in prod.
# Structure:
# {
#   "job-uuid": {
#       "status": "pending" | "running" | "completed" | "failed",
#       "events": [{"type": "...", "data": {...}}],
#       "total_files": 0
#   }
# }
jobs: Dict[str, Dict[str, Any]] = {}

def create_job() -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "events": [],
        "total_files": 0
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
