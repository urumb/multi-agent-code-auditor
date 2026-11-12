import json
import os
import sqlite3
import tempfile
import threading
import time

import pytest

from src.config import Config
from backend.app.services import db, job_store
from backend.app.services.audit_runner import _attach_coverage
from src.agents.manager import ManagerAgent


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="auditor_test_batch1_")
    monkeypatch.setattr(Config, "AUDIT_DB_PATH", os.path.join(tmp, "audit.db"))
    db._initialized = False
    job_store.jobs.clear()
    yield
    job_store.jobs.clear()
    db._initialized = False


# --- job store --------------------------------------------------------------

def test_concurrent_job_creation_and_events_are_safe():
    errors = []

    def worker():
        try:
            for _ in range(20):
                job_id = job_store.create_job("x", "paste")
                for i in range(10):
                    job_store.add_job_event(job_id, "log", {"i": i})
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert all(len(j["events"]) == 10 for j in job_store.jobs.values())


def test_cap_evicts_oldest_finished_jobs_but_keeps_running(monkeypatch):
    monkeypatch.setattr(job_store, "MAX_LIVE_JOBS", 3)
    running = job_store.create_job("running", "paste")
    job_store.jobs[running]["status"] = "running"
    job_store.jobs[running]["last_updated"] = 0  # oldest of all

    finished = []
    for n in range(4):
        job_id = job_store.create_job(f"done-{n}", "paste")
        job_store.jobs[job_id]["status"] = "completed"
        job_store.jobs[job_id]["last_updated"] = time.time() - 10 + n  # recent, not expired
        finished.append(job_id)

    job_store.cleanup_old_jobs()

    assert len(job_store.jobs) == 3
    assert running in job_store.jobs
    assert finished[-1] in job_store.jobs and finished[0] not in job_store.jobs


def test_stale_running_job_is_not_dropped():
    job_id = job_store.create_job("x", "paste")
    job_store.jobs[job_id]["status"] = "running"
    job_store.jobs[job_id]["last_updated"] = 0
    job_store.cleanup_old_jobs()
    assert job_id in job_store.jobs


# --- skipped files persisted -------------------------------------------------

def test_files_skipped_is_persisted():
    job_id = job_store.create_job("repo", "github")
    job_store.jobs[job_id]["files_skipped"] = 7
    job_store.finalize_job(job_id, "completed", results=[], duration=1.0)
    assert db.get_job_detail(job_id)["files_skipped"] == 7


def test_old_database_gets_files_skipped_column():
    conn = sqlite3.connect(Config.AUDIT_DB_PATH)
    conn.execute(
        """CREATE TABLE audit_jobs (
            id TEXT PRIMARY KEY, input_identifier TEXT NOT NULL,
            input_type TEXT NOT NULL DEFAULT 'unknown', status TEXT NOT NULL,
            created_at REAL NOT NULL, completed_at REAL, duration REAL,
            total_files INTEGER NOT NULL DEFAULT 0,
            total_findings INTEGER NOT NULL DEFAULT 0,
            max_severity TEXT NOT NULL DEFAULT 'Low', error TEXT, results_json TEXT)"""
    )
    conn.execute(
        "INSERT INTO audit_jobs (id, input_identifier, status, created_at) "
        "VALUES ('old', 'x', 'completed', 1)"
    )
    conn.commit()
    conn.close()

    db.init_db()
    assert db.get_job_detail("old")["files_skipped"] == 0


# --- skipped chunks reported -------------------------------------------------

def test_split_reports_total_chunks_when_capped():
    code = "\n\n".join(
        f"def f{i}():\n" + "    value = 'x' * 100\n" * 30 + "    return value\n" for i in range(30)
    )
    chunks, total = ManagerAgent().split_code_with_stats(code)
    assert len(chunks) == ManagerAgent.MAX_SNIPPETS
    assert total > len(chunks)


def test_coverage_is_attached_to_report():
    report = json.dumps({"findings": []})
    out = json.loads(_attach_coverage(report, {"chunks_total": 9, "chunks_analyzed": 6}))
    assert out["coverage"] == {"chunks_total": 9, "chunks_analyzed": 6}


def test_coverage_leaves_unparseable_report_alone():
    assert _attach_coverage("not json", {"chunks_total": 2, "chunks_analyzed": 2}) == "not json"
