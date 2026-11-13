"""End-to-end API tests with the LangGraph pipeline replaced by a fake.

They exercise the real routes, background jobs, SSE stream, persistence and
caps, so a refactor of the backend layout can't silently change behavior.
"""
import io
import json
import os
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.services import audit_runner, db, job_store
from src.config import Config


def _report(code: str) -> str:
    severity = "High" if "danger" in code else "Low"
    return json.dumps({
        "Executive Summary": "fake",
        "Findings Summary": "fake",
        "risk_score": 7.0 if severity == "High" else 1.0,
        "risk_breakdown": {},
        "max_severity": severity,
        "findings": [{"severity": severity, "issue": "x", "agent": "security"}],
        "top_risk_files": [],
    })


class FakeGraph:
    delay = 0.0

    def invoke(self, state):
        if self.delay:
            time.sleep(self.delay)
        return {**state, "final_report": _report(state["original_code"]),
                "execution_plan": {"agents": ["security"]}}


@pytest.fixture
def client(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="auditor_api_")
    monkeypatch.setattr(Config, "AUDIT_DB_PATH", os.path.join(tmp, "audit.db"))
    db._initialized = False
    job_store.jobs.clear()
    fake = FakeGraph()
    monkeypatch.setattr(audit_runner, "graph", fake)
    monkeypatch.setattr("src.llm.warm_up_model", lambda: None)
    from backend.app.main import app

    with TestClient(app) as c:
        c.fake_graph = fake
        yield c
    job_store.jobs.clear()
    db._initialized = False


def _events(client, job_id):
    with client.stream("GET", f"/audit/stream/{job_id}") as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_paste_audit_streams_results_and_persists(client):
    resp = client.post("/audit/stream", json={
        "input_type": "paste", "code": "x = 'danger'\n" * 30, "language": "python", "depth": "quick",
    })
    job_id = resp.json()["job_id"]

    events = _events(client, job_id)
    types = [e["type"] for e in events]
    assert "file_start" in types and "result" in types and types[-1] == "done"
    result = next(e["data"] for e in events if e["type"] == "result")
    assert result["risk_score"] == 7.0 and result["max_severity"] == "High"
    assert events[-1]["data"]["files_skipped"] == 0

    detail = client.get(f"/audit/history/{job_id}").json()
    assert detail["status"] == "completed" and len(detail["results"]) == 1
    assert any(a["id"] == job_id for a in client.get("/recent-audits").json())
    assert client.get("/audit/history").json()[0]["findings"] == 1
    assert client.get("/metrics").json()[0]["value"] == 1


def test_upload_audit_caps_files_and_records_skipped(client, monkeypatch):
    monkeypatch.setattr(Config, "MAX_FILES_PER_AUDIT", 2)
    files = [
        ("files", (f"m{i}.py", io.BytesIO(("print('hello world')\n" * (i + 5)).encode()), "text/x-python"))
        for i in range(3)
    ]
    job_id = client.post("/audit/stream/upload", files=files, data={"depth": "quick"}).json()["job_id"]

    events = _events(client, job_id)
    assert sum(e["type"] == "result" for e in events) == 2
    assert events[-1]["data"]["files_skipped"] == 1
    assert client.get(f"/audit/history/{job_id}").json()["files_skipped"] == 1


def test_timed_out_file_is_reported_not_hung(client, monkeypatch):
    monkeypatch.setattr(Config, "PER_FILE_TIMEOUT_SECONDS", 0.3)
    client.fake_graph.delay = 1.0
    job_id = client.post("/audit/stream", json={
        "input_type": "paste", "code": "y = 1\n" * 50, "depth": "quick",
    }).json()["job_id"]

    result = next(e["data"] for e in _events(client, job_id) if e["type"] == "result")
    assert result["error"] == "Timed out after 0.3 seconds"


def test_sync_audit_adds_top_risk_files(client):
    resp = client.post("/audit", json={"input_type": "paste", "code": "z = 'danger'\n" * 30})
    body = resp.json()
    assert body["total_files"] == 1
    report = json.loads(body["results"][0]["final_report"])
    assert report["top_risk_files"][0]["risk_score"] == 7.0


def test_unknown_jobs_return_404(client):
    assert client.get("/audit/stream/nope").status_code == 404
    assert client.get("/audit/history/nope").status_code == 404


def test_invalid_requests_are_rejected(client):
    assert client.post("/audit/stream", json={"input_type": "paste"}).status_code == 422
    assert client.post("/audit/stream", json={"input_type": "github"}).status_code == 422


def test_settings_lists_and_validates_models(client, monkeypatch):
    monkeypatch.setattr("src.llm.installed_models", lambda: ["llama3.2:latest"])
    monkeypatch.setattr("src.llm.warm_up_model", lambda: None)
    assert client.get("/settings/models").json()["models"] == ["llama3.2:latest"]
    assert client.post("/settings", json={"model": "missing"}).status_code == 400
    assert client.post("/settings", json={"model": "llama3.2"}).json()["model"] == "llama3.2"
