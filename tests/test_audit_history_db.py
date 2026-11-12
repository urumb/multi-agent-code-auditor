import json
import os
import tempfile
import unittest

from src.config import Config

from backend.app.services import db  # noqa: E402


class AuditHistoryDbTests(unittest.TestCase):
    def setUp(self):
        # Fresh, isolated DB file per test — never touches the real
        # audit_history.db and tests never see each other's rows.
        self._tmp_dir = tempfile.mkdtemp(prefix="auditor_test_db_")
        Config.AUDIT_DB_PATH = os.path.join(self._tmp_dir, "test_audit_history.db")
        db._initialized = False

    def test_upsert_and_list(self):
        db.upsert_job(
            job_id="job-1",
            input_identifier="Pasted Code",
            input_type="paste",
            status="pending",
            created_at=1000.0,
        )
        jobs = db.list_jobs(limit=10)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["status"], "pending")

    def test_status_transition_and_finalize_preserves_results(self):
        db.upsert_job(
            job_id="job-2",
            input_identifier="Pasted Code",
            input_type="paste",
            status="pending",
            created_at=1000.0,
        )
        db.set_status("job-2", "running")
        self.assertEqual(db.get_job_detail("job-2")["status"], "running")

        results = [
            {
                "file_path": "a.py",
                "final_report": json.dumps({"findings": [{"severity": "Critical"}]}),
                "risk_score": 10.0,
                "max_severity": "Critical",
                "error": None,
            }
        ]
        db.upsert_job(
            job_id="job-2",
            input_identifier="Pasted Code",
            input_type="paste",
            status="completed",
            created_at=1000.0,
            completed_at=1010.0,
            duration=10.0,
            total_files=1,
            total_findings=1,
            max_severity="Critical",
            results=results,
        )

        detail = db.get_job_detail("job-2")
        self.assertEqual(detail["status"], "completed")
        self.assertEqual(len(detail["results"]), 1)
        self.assertEqual(detail["results"][0]["file_path"], "a.py")

    def test_count_jobs(self):
        db.upsert_job(job_id="a", input_identifier="x", input_type="paste", status="completed", created_at=1.0)
        db.upsert_job(job_id="b", input_identifier="x", input_type="paste", status="failed", created_at=2.0)
        counts = db.count_jobs()
        self.assertEqual(counts["total"], 2)
        self.assertEqual(counts["completed"], 1)
        self.assertEqual(counts["failed"], 1)

    def test_get_missing_job_returns_none(self):
        self.assertIsNone(db.get_job_detail("does-not-exist"))

    def test_severity_trend_empty_without_history(self):
        self.assertEqual(db.severity_trend(), [])


if __name__ == "__main__":
    unittest.main()
