# Author: urumb
"""Audit history, dashboard metrics and trends (all from the SQLite store)."""
import datetime

from fastapi import APIRouter, HTTPException

from backend.app.services import db

router = APIRouter(tags=["history"])


def _job_row_to_summary(row: dict) -> dict:
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


@router.get("/recent-audits")
def get_recent_audits() -> list:
    """The 5 most recent audits."""
    return [_job_row_to_summary(row) for row in db.list_jobs(limit=5)]


@router.get("/audit/history")
def get_audit_history(limit: int = 20, offset: int = 0) -> list:
    """Paginated audit history for the History page."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return [_job_row_to_summary(row) for row in db.list_jobs(limit=limit, offset=offset)]


@router.get("/audit/history/{job_id}")
def get_audit_history_detail(job_id: str) -> dict:
    """Full persisted results for one past audit, so it can be reopened after
    its live SSE job has expired or the backend has restarted."""
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
        "files_skipped": detail.get("files_skipped") or 0,
        "results": detail.get("results", []),
    }


@router.get("/metrics")
def get_metrics() -> list:
    """Dashboard counters from the persistent audit history."""
    counts = db.count_jobs()
    return [
        {"label": "Total Audits", "value": counts["total"], "trend": 0, "trendDirection": "up", "icon": "folder-git-2"},
        {"label": "Completed", "value": counts["completed"], "trend": 0, "trendDirection": "up", "icon": "gauge"},
        {"label": "Failed", "value": counts["failed"], "trend": 0, "trendDirection": "down", "icon": "bug"},
    ]


@router.get("/trends")
def get_trends() -> list:
    """Findings by severity per day from completed audits. Empty until at
    least one audit has completed; never fabricated."""
    return db.severity_trend(days=14)
