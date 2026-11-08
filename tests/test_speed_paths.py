from src.agents.manager import ManagerAgent
from src.agents.reviewer import ReviewerAgent


def test_small_input_is_one_chunk():
    code = "def a():\n    pass\n\ndef b():\n    pass\n" * 20  # < CHUNK_CHARS
    assert ManagerAgent().split_code(code) == [code]


def test_many_small_functions_are_packed_not_one_call_each():
    code = "\n\n".join(f"def f{i}():\n" + "    y = 1\n" * 20 + "    return y\n" for i in range(40))
    chunks = ManagerAgent().split_code(code)
    assert 1 < len(chunks) <= ManagerAgent.MAX_SNIPPETS
    assert all(len(c) <= ManagerAgent.CHUNK_CHARS for c in chunks)


def test_non_python_large_file_is_split_on_size():
    code = "\n".join(f"const x{i} = {i};" for i in range(2000))
    chunks = ManagerAgent().split_code(code)
    assert len(chunks) > 1
    assert all(len(c) <= ManagerAgent.CHUNK_CHARS for c in chunks)


def test_deterministic_summary_without_llm():
    findings = [
        {"severity": "High", "issue": "SQL injection", "agent": "security"},
        {"severity": "Low", "issue": "Naming", "agent": "quality"},
    ]
    risk = {"risk_score": 5.0, "risk_breakdown": {}, "max_severity": "High"}
    out = ReviewerAgent._build_summary(findings, risk, 1234)
    assert "SQL injection" in out["Executive Summary"]
    assert out["max_severity"] == "High" and len(out["findings"]) == 2
