import json

from backend.app.services.audit_runner import run_audit_on_code
from src.config import Config

SQL = (
    "import sqlite3\n\n\n"
    "def get(conn, name):\n"
    "    query = \"SELECT * FROM users WHERE name = '%s'\" % name\n"
    "    return conn.execute(query).fetchall()\n"
) * 3  # long enough for a full (not "small snippet") plan


def test_tools_only_audit_runs_static_analysis_without_any_llm(monkeypatch):
    monkeypatch.setattr(Config, "AI_ENABLED", False)

    def no_llm(*_args, **_kwargs):
        raise AssertionError("the AI must not be called in tools-only mode")

    monkeypatch.setattr("src.agents.base.invoke_llm", no_llm)
    monkeypatch.setattr("src.agents.reviewer.invoke_llm", no_llm)
    events = []

    output = run_audit_on_code(SQL, event_callback=lambda t, p: events.append((t, p)),
                               depth="full", file_path="a.py")
    report = json.loads(output["final_report"])

    assert report["ai_enabled"] is False
    assert "Tools-only audit" in report["Executive Summary"]
    assert "warnings" not in report
    rules = {f["rule_id"] for f in report["findings"]}
    assert "B608" in rules  # security from bandit
    assert all(f["source"] != "llm" for f in report["findings"])
    plan = next(p for t, p in events if t == "execution_plan")
    assert plan["agents"] == [] and "Tools-only" in plan["reason"]
    assert not any(t == "agent_started" and p["agent"] != "Manager Agent" for t, p in events)


def test_quick_tools_only_keeps_only_security_categories(monkeypatch):
    monkeypatch.setattr(Config, "AI_ENABLED", False)
    output = run_audit_on_code(SQL, depth="quick", file_path="a.py")
    report = json.loads(output["final_report"])
    assert report["findings"] and {f["agent"] for f in report["findings"]} == {"security"}
