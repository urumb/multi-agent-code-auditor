import json

from benchmarks.run_benchmark import load_case, run, score, summarize, CASES_DIR
from src.agents.security import SecurityAgent
from src.config import Config
from src.findings import locate_line, merge_findings
from src.graph import finalize_node, retrieval_node, save_node
from src.static_analysis import hints_for_chunk, run_static_analysis

SQL_CODE = (
    "import sqlite3\n"
    "\n"
    "def get(conn, name):\n"
    "    query = \"SELECT * FROM users WHERE name = '%s'\" % name\n"
    "    return conn.execute(query).fetchall()\n"
)


# --- line anchoring ----------------------------------------------------------

def test_locate_line_ignores_indentation_and_spacing():
    lines = SQL_CODE.splitlines()
    assert locate_line("query = \"SELECT * FROM users WHERE name = '%s'\"  %  name", lines) == 4


def test_locate_line_returns_none_instead_of_guessing():
    assert locate_line("cursor.execute(totally_different)", SQL_CODE.splitlines()) is None
    assert locate_line("x = 1", SQL_CODE.splitlines()) is None  # too short to trust


# --- merging and de-duplication ---------------------------------------------

def _llm(issue, line_code, agent="security", severity="High", **extra):
    return {"severity": severity, "issue": issue, "explanation": "llm says", "suggested_fix": "fix it",
            "before_code": line_code, "after_code": "safe()", "cwe": "", "agent": agent, **extra}


def test_llm_and_tool_reporting_same_line_merge_into_one():
    static = run_static_analysis(SQL_CODE, "a.py")
    assert any(f["rule_id"] == "B608" and f["line"] == 4 for f in static)

    llm = [_llm("SQL injection", "query = \"SELECT * FROM users WHERE name = '%s'\" % name")]
    merged = merge_findings(llm, static, SQL_CODE)

    sql = [f for f in merged if f["line"] == 4 and f["agent"] == "security"]
    assert len(sql) == 1
    assert sql[0]["source"] == "bandit+llm"
    assert sql[0]["issue"] == "SQL injection"  # richer LLM text wins
    assert sql[0]["rule_id"] == "B608"  # tool metadata kept
    assert sql[0]["severity"] == "High"  # highest severity wins


def test_unlocatable_duplicates_merge_by_title_when_source_unknown():
    merged = merge_findings([_llm("Weak hashing", "nowhere"), _llm("weak  hashing", "nowhere either")], [], "")
    assert len(merged) == 1


def test_llm_finding_quoting_code_not_in_file_is_dropped():
    merged = merge_findings([_llm("Hardcoded secret", "API_KEY = 'abc123456'")], [], SQL_CODE)
    assert merged == []


def test_other_agents_cannot_refile_a_line_security_owns():
    line_code = "query = \"SELECT * FROM users WHERE name = '%s'\" % name"
    merged = merge_findings(
        [
            _llm("SQL injection", line_code, agent="security"),
            _llm("Unparameterized query is slow", line_code, agent="performance"),
            _llm("Unvalidated input", line_code, agent="quality"),
        ],
        [],
        SQL_CODE,
    )
    assert [f["agent"] for f in merged] == ["security"]


def test_tool_owned_line_blocks_llm_refiling_but_keeps_same_agent_merge():
    static = [{"agent": "quality", "line": 4, "source": "ruff", "rule_id": "F841", "severity": "Low",
               "issue": "unused", "before_code": ""}]
    line_code = "query = \"SELECT * FROM users WHERE name = '%s'\" % name"
    merged = merge_findings(
        [_llm("Bad name", line_code, agent="quality"), _llm("Slow", line_code, agent="performance")],
        static,
        SQL_CODE,
    )
    assert len(merged) == 1 and merged[0]["source"] == "llm+ruff"


def test_different_tool_rules_on_one_line_stay_separate():
    a = {"agent": "quality", "line": 3, "source": "ruff", "rule_id": "B006", "severity": "Medium", "issue": "a"}
    b = {"agent": "quality", "line": 3, "source": "ruff", "rule_id": "F841", "severity": "Low", "issue": "b"}
    assert len(merge_findings([], [a, b], "")) == 2


def test_findings_sorted_by_severity_then_line():
    static = [
        {"agent": "quality", "line": 9, "source": "ruff", "rule_id": "X", "severity": "Low", "issue": "l"},
        {"agent": "security", "line": 5, "source": "bandit", "rule_id": "Y", "severity": "High", "issue": "h"},
        {"agent": "security", "line": 2, "source": "bandit", "rule_id": "Z", "severity": "High", "issue": "h2"},
    ]
    assert [f["line"] for f in merge_findings([], static, "")] == [2, 5, 9]


# --- static analysis ---------------------------------------------------------

def test_static_analysis_can_be_disabled(monkeypatch):
    monkeypatch.setattr(Config, "STATIC_ANALYSIS_ENABLED", False)
    assert run_static_analysis(SQL_CODE, "a.py") == []


def test_python_tools_skip_non_python_files():
    # bandit/ruff only understand Python; semgrep (if installed) may still run.
    findings = run_static_analysis(SQL_CODE, "a.txt")
    assert not any(f["source"] in ("bandit", "ruff") for f in findings)


def test_hints_only_include_flagged_lines_in_this_chunk_and_category():
    static = run_static_analysis(SQL_CODE, "a.py")
    assert "B608" in hints_for_chunk(static, SQL_CODE, "security")
    assert hints_for_chunk(static, "def other():\n    pass\n", "security") == "None"
    assert hints_for_chunk(static, SQL_CODE, "performance") == "None"


def test_agent_prompt_carries_hints_and_finding_cap():
    messages = SecurityAgent().prompt.format_messages(code="x = 1", hints="- SQL (B608): q", max_findings=3)
    assert "at most 3 findings" in messages[0].content
    assert "B608" in messages[1].content


def test_quick_scan_report_includes_tool_findings():
    state = {
        "original_code": SQL_CODE,
        "security_analysis": [{"snippet_index": 0, "findings": []}],
        "static_findings": run_static_analysis(SQL_CODE, "a.py"),
    }
    report = json.loads(finalize_node(state)["final_report"])
    assert any(f["rule_id"] == "B608" for f in report["findings"])


# --- memory opt-in -------------------------------------------------------------

def test_memory_is_off_by_default_and_skipped(monkeypatch):
    monkeypatch.setattr(Config, "MEMORY_ENABLED", False)
    plan = {"execution_plan": {"agents": ["security", "performance", "quality", "reviewer"]},
            "code_snippets": ["x"]}
    assert retrieval_node(plan) == {"past_audits": []}
    assert save_node(plan) == {}


# --- benchmark -----------------------------------------------------------------

def test_benchmark_markers_are_stripped_and_recorded():
    code, expected = load_case(CASES_DIR / "py_injection.py")
    assert "EXPECT" not in code
    assert (7, "security") in expected


def test_benchmark_scoring_tolerance():
    found, correct, missed, fps = score(
        [(10, "security"), (20, "quality")],
        [{"line": 11, "agent": "security"}, {"line": 20, "agent": "security"}, {"line": None, "agent": "quality"}],
    )
    assert (found, correct) == (1, 1)
    assert missed == [(20, "quality")]
    assert len(fps) == 2


def test_static_benchmark_does_not_regress():
    """Guards the static pre-pass: if a tool upgrade or rule change makes it
    miss known issues or flag clean code, this fails. Python cases only, so
    the result doesn't depend on whether semgrep is installed."""
    totals = summarize([r for r in run(static_only=True) if r.name.endswith(".py")])
    assert totals["recall"] >= 0.80, totals
    assert totals["precision"] >= 0.90, totals
    clean = [r for r in run(static_only=True, only="clean") if r.name.endswith(".py")]
    assert all(not r.findings for r in clean), [r.findings for r in clean]
