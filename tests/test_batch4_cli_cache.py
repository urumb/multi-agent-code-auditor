import json
import os
import tempfile

import pytest

from backend.app.schemas.code_file import CodeFile
from backend.app.services import audit_jobs, audit_runner, db
from src.cli import main as cli_main
from src.config import Config
from src.sarif import rule_id, to_sarif

VULN = 'import os\n\n\ndef ping(host):\n    return os.system("ping -c 1 " + host)\n'


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="auditor_test_b4_")
    monkeypatch.setattr(Config, "AUDIT_DB_PATH", os.path.join(tmp, "audit.db"))
    db._initialized = False
    yield
    db._initialized = False


# --- SARIF -----------------------------------------------------------------------

def test_sarif_structure_levels_and_rules():
    sarif = to_sarif([{
        "file_path": "app\\db.py",
        "findings": [
            {"severity": "Critical", "issue": "SQL injection", "agent": "security", "line": 7,
             "source": "bandit+llm", "rule_id": "B608", "cwe": "CWE-89", "explanation": "x"},
            {"severity": "Low", "issue": "Bad name", "agent": "quality", "line": None, "source": "llm"},
        ],
    }])
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0"
    first, second = run["results"]
    assert first["ruleId"] == "bandit/B608" and first["level"] == "error"
    assert first["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "app/db.py"
    assert first["locations"][0]["physicalLocation"]["region"]["startLine"] == 7
    assert second["level"] == "note" and second["properties"]["lineVerified"] is False
    assert second["locations"][0]["physicalLocation"]["region"]["startLine"] == 1
    rules = {r["id"]: r for r in run["tool"]["driver"]["rules"]}
    assert rules["bandit/B608"]["properties"]["security-severity"] == "9.5"
    assert "external/cwe/cwe-89" in rules["bandit/B608"]["properties"]["tags"]
    assert "security-severity" not in rules["ai/quality/bad-name"]["properties"]


def test_rule_id_prefers_tool_name_even_when_llm_listed_first():
    assert rule_id({"rule_id": "E722", "source": "llm+ruff"}) == "ruff/E722"


# --- CLI --------------------------------------------------------------------------

def _project(tmp_path):
    (tmp_path / "app.py").write_text(VULN)
    (tmp_path / "skipme").mkdir()
    (tmp_path / "skipme" / "other.py").write_text(VULN)
    return tmp_path


def test_cli_fail_on_exit_codes(tmp_path):
    root = _project(tmp_path)
    assert cli_main(["scan", str(root), "--static-only", "-q", "-o", str(tmp_path / "r.txt")]) == 1
    assert cli_main(["scan", str(root), "--static-only", "-q", "--fail-on", "none",
                     "-o", str(tmp_path / "r.txt")]) == 0
    assert cli_main(["scan", str(tmp_path / "missing"), "--static-only", "-q"]) == 2


def test_cli_json_output_and_exclude(tmp_path):
    root = _project(tmp_path)
    out = tmp_path / "report.json"
    cli_main(["scan", str(root), "--static-only", "-q", "--fail-on", "none",
              "--format", "json", "-o", str(out), "--exclude", "skipme/*"])
    data = json.loads(out.read_text())
    assert [f["file_path"] for f in data["files"]] == ["app.py"]
    finding = data["files"][0]["findings"][0]
    assert finding["rule_id"] == "B605" and finding["line"] == 5


def test_cli_sarif_output(tmp_path):
    root = _project(tmp_path)
    out = tmp_path / "r.sarif"
    cli_main(["scan", str(root / "app.py"), "--static-only", "-q", "--fail-on", "none",
              "--format", "sarif", "-o", str(out)])
    sarif = json.loads(out.read_text())
    assert sarif["runs"][0]["results"][0]["ruleId"] == "bandit/B605"


# --- re-audit only changed files ---------------------------------------------------

class CountingGraph:
    def __init__(self, warnings=False):
        self.calls = 0
        self.warnings = warnings

    def invoke(self, state):
        self.calls += 1
        report = {"findings": [], "risk_score": 0.0, "max_severity": "Low"}
        out = {**state, "final_report": json.dumps(report), "execution_plan": {"agents": ["security"]}}
        if self.warnings:
            out["security_analysis"] = [{"snippet_index": 0, "error": "connection refused", "findings": []}]
        return out


def test_unchanged_file_reuses_previous_result(monkeypatch):
    graph = CountingGraph()
    monkeypatch.setattr(audit_runner, "graph", graph)
    file = CodeFile(path="a.py", content="x = 1\n" * 20)

    first = audit_jobs.audit_file(file, 1, "quick")
    second = audit_jobs.audit_file(file, 1, "quick")
    assert graph.calls == 1
    assert first["cached"] is False and second["cached"] is True
    assert second["final_report"] == first["final_report"]


def test_changes_to_content_depth_or_model_reaudit(monkeypatch):
    graph = CountingGraph()
    monkeypatch.setattr(audit_runner, "graph", graph)
    audit_jobs.audit_file(CodeFile(path="a.py", content="x = 1\n" * 20), 1, "quick")
    audit_jobs.audit_file(CodeFile(path="a.py", content="x = 2\n" * 20), 1, "quick")
    audit_jobs.audit_file(CodeFile(path="a.py", content="x = 2\n" * 20), 1, "full")
    monkeypatch.setattr(Config, "MODEL_NAME", "some-other-model")
    audit_jobs.audit_file(CodeFile(path="a.py", content="x = 2\n" * 20), 1, "full")
    assert graph.calls == 4


def test_failed_ai_results_are_never_cached(monkeypatch):
    graph = CountingGraph(warnings=True)
    monkeypatch.setattr(audit_runner, "graph", graph)
    file = CodeFile(path="a.py", content="y = 1\n" * 20)
    audit_jobs.audit_file(file, 1, "quick")
    audit_jobs.audit_file(file, 1, "quick")
    assert graph.calls == 2


def test_cache_can_be_bypassed(monkeypatch):
    graph = CountingGraph()
    monkeypatch.setattr(audit_runner, "graph", graph)
    file = CodeFile(path="a.py", content="z = 1\n" * 20)
    audit_jobs.audit_file(file, 1, "quick")
    audit_jobs.audit_file(file, 1, "quick", use_cache=False)
    monkeypatch.setattr(Config, "CACHE_ENABLED", False)
    audit_jobs.audit_file(file, 1, "quick")
    assert graph.calls == 3


# --- cancel ---------------------------------------------------------------------

def test_cancel_stops_job_and_keeps_finished_files(monkeypatch):
    import threading
    import time as _time

    from backend.app.services import job_store

    class SlowGraph:
        def invoke(self, state):
            _time.sleep(0.6)
            return {**state, "final_report": json.dumps({"findings": []}),
                    "execution_plan": {"agents": ["security"]}}

    monkeypatch.setattr(audit_runner, "graph", SlowGraph())
    files = [CodeFile(path=f"f{i}.py", content=f"v = {i}\n" * 20) for i in range(5)]
    job_id = job_store.create_job("t", "paste")
    worker = threading.Thread(target=audit_jobs.run_audit_job, args=(job_id, files, "quick", False))
    worker.start()

    job = job_store.get_job(job_id)
    deadline = _time.time() + 10
    while sum(e["type"] == "result" for e in job["events"]) < 1 and _time.time() < deadline:
        _time.sleep(0.05)
    assert job_store.request_cancel(job_id) == "cancelling"
    worker.join(timeout=10)

    assert job["status"] == "cancelled"
    cancelled = [e for e in job["events"] if e["type"] == "cancelled"]
    assert len(cancelled) == 1 and 1 <= cancelled[0]["data"]["files_done"] < 5
    assert not any(e["type"] == "done" for e in job["events"])
    detail = db.get_job_detail(job_id)
    assert detail["status"] == "cancelled" and len(detail["results"]) == cancelled[0]["data"]["files_done"]
    assert job_store.request_cancel(job_id) == "finished"
    assert job_store.request_cancel("nope") == "not_found"
