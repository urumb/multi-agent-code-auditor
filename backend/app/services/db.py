"""SQLite-backed persistence for completed audit jobs.

The live job store (job_store.py) keeps in-progress audits and their SSE
event streams in memory only — that's fine, since a job that was mid-flight
during a backend restart cannot be resumed anyway (the LangGraph run itself
is gone). But *completed* audits need to survive restarts so History,
Dashboard metrics, and "open previous audit" actually work. This module is
the durable store for that: one row per finished (or failed) job.

SQLite (stdlib, no new dependency) is a deliberate, local-first choice
consistent with the rest of the stack — no external database service.
"""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from src.config import Config

_lock = threading.Lock()
_initialized = False


def _connect() -> sqlite3.Connection:
    # sqlite creates the file but not its folder (e.g. a fresh ./data/).
    parent = os.path.dirname(os.path.abspath(Config.AUDIT_DB_PATH))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(Config.AUDIT_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _db():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    """Create the audit_jobs table if it doesn't exist yet. Idempotent."""
    global _initialized
    if _initialized:
        return
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_jobs (
                id TEXT PRIMARY KEY,
                input_identifier TEXT NOT NULL,
                input_type TEXT NOT NULL DEFAULT 'unknown',
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                completed_at REAL,
                duration REAL,
                total_files INTEGER NOT NULL DEFAULT 0,
                total_findings INTEGER NOT NULL DEFAULT 0,
                max_severity TEXT NOT NULL DEFAULT 'Low',
                error TEXT,
                results_json TEXT
            )
            """
        )
        # Columns added after the first release; add them to older databases.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(audit_jobs)")}
        if "files_skipped" not in existing:
            conn.execute(
                "ALTER TABLE audit_jobs ADD COLUMN files_skipped INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_jobs_created_at ON audit_jobs(created_at DESC)"
        )
        # Jobs still pending/running at startup were killed by a restart and
        # can never finish; mark them failed so History doesn't show them
        # as "running" forever.
        conn.execute(
            "UPDATE audit_jobs SET status = 'failed', error = 'Interrupted by backend restart' "
            "WHERE status IN ('pending', 'running')"
        )
    _initialized = True


def upsert_job(
    job_id: str,
    input_identifier: str,
    input_type: str,
    status: str,
    created_at: float,
    completed_at: Optional[float] = None,
    duration: Optional[float] = None,
    total_files: int = 0,
    total_findings: int = 0,
    max_severity: str = "Low",
    error: Optional[str] = None,
    results: Optional[List[Dict[str, Any]]] = None,
    files_skipped: int = 0,
) -> None:
    """Insert or update a job's persisted snapshot."""
    init_db()
    results_json = json.dumps(results) if results is not None else None
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO audit_jobs (
                id, input_identifier, input_type, status, created_at, completed_at,
                duration, total_files, total_findings, max_severity, error, results_json,
                files_skipped
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                input_identifier=excluded.input_identifier,
                input_type=excluded.input_type,
                status=excluded.status,
                completed_at=excluded.completed_at,
                duration=excluded.duration,
                total_files=excluded.total_files,
                total_findings=excluded.total_findings,
                max_severity=excluded.max_severity,
                error=excluded.error,
                results_json=COALESCE(excluded.results_json, audit_jobs.results_json),
                files_skipped=excluded.files_skipped
            """,
            (
                job_id, input_identifier, input_type, status, created_at, completed_at,
                duration, total_files, total_findings, max_severity, error, results_json,
                files_skipped,
            ),
        )


def set_status(job_id: str, status: str) -> None:
    init_db()
    with _db() as conn:
        conn.execute("UPDATE audit_jobs SET status = ? WHERE id = ?", (status, job_id))


def list_jobs(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    init_db()
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id, input_identifier, input_type, status, created_at, completed_at,
                   duration, total_files, total_findings, max_severity, error, results_json
            FROM audit_jobs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            results_json = data.pop("results_json")
            # A job can "complete" (the background loop ran to the end)
            # while every individual file failed/timed out — surface that
            # so History/Dashboard don't show a misleading "0 findings,
            # Low severity" that reads as "nothing wrong" when nothing was
            # actually analyzed.
            files_errored = 0
            if results_json:
                try:
                    files_errored = sum(1 for r in json.loads(results_json) if r.get("error"))
                except (json.JSONDecodeError, TypeError):
                    pass
            data["files_errored"] = files_errored
            results.append(data)
        return results


def count_jobs() -> Dict[str, int]:
    init_db()
    with _db() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
            FROM audit_jobs
            """
        ).fetchone()
        return {
            "total": row["total"] or 0,
            "completed": row["completed"] or 0,
            "failed": row["failed"] or 0,
        }


def get_job_detail(job_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM audit_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["results"] = json.loads(data.pop("results_json") or "[]")
        return data


def severity_trend(days: int = 14) -> List[Dict[str, Any]]:
    """Real, derived-from-history trend data: findings by severity per day.

    Returns an empty list when there's no completed-audit history yet —
    never fabricated numbers.
    """
    init_db()
    import datetime

    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT created_at, results_json FROM audit_jobs
            WHERE status = 'completed' AND created_at >= ? AND results_json IS NOT NULL
            ORDER BY created_at ASC
            """,
            (cutoff,),
        ).fetchall()

    buckets: Dict[str, Dict[str, int]] = {}
    for row in rows:
        day = datetime.datetime.fromtimestamp(row["created_at"]).strftime("%Y-%m-%d")
        bucket = buckets.setdefault(day, {"critical": 0, "warning": 0, "info": 0})
        try:
            results = json.loads(row["results_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        for file_result in results:
            try:
                report = json.loads(file_result.get("final_report") or "{}")
            except json.JSONDecodeError:
                continue
            for finding in report.get("findings", []):
                severity = str(finding.get("severity", "Low")).lower()
                if severity == "critical":
                    bucket["critical"] += 1
                elif severity in ("high", "medium"):
                    bucket["warning"] += 1
                else:
                    bucket["info"] += 1

    return [
        {"date": day, "critical": counts["critical"], "warning": counts["warning"], "info": counts["info"]}
        for day, counts in sorted(buckets.items())
    ]
