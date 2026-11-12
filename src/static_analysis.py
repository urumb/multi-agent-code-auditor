# Author: urumb
"""Deterministic static-analysis pre-pass that runs before the LLM agents.

Real analyzers catch well-known bug patterns precisely and with exact line
numbers; the LLM agents are then told about them so they can spend their
small token budget on problems the tools can't see.

Tools (all free, all local, none of them execute the audited code):
- bandit  -> security findings (Python)
- ruff    -> quality / performance findings (Python)
- semgrep -> optional; used only if installed. Runs offline against the rule
             file in ``rules/semgrep.yml`` with metrics disabled.

Every tool is optional at runtime: a missing or failing tool is logged and
skipped, never fatal to the audit.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import Config

logger = logging.getLogger(__name__)

TOOL_TIMEOUT_SECONDS = 60

# bandit checks that only add noise:
#   B101       assert used (fine outside optimized builds)
#   B403/B404  importing pickle/subprocess (the dangerous *call* is reported)
#   B603/B607  subprocess with an argument list / partial path: this is the
#              SAFE pattern; shell=True (B602) and os.system (B605) still fire
_BANDIT_SKIP = "B101,B403,B404,B603,B607"

# ruff rules that point at real defects, not style:
#   F    pyflakes (undefined names, unused variables, redefinitions)
#   B    bugbear (mutable defaults, loop-variable capture, ...)
#   E722 bare except
#   PERF perflint (slow loop patterns)
_RUFF_SELECT = "F,B,E722,PERF"
_RUFF_HIGH = {"F821", "F823", "F811"}
_RUFF_MEDIUM = {"B006", "B008", "B023", "E722", "B904", "B012"}

_SEMGREP_SEVERITY = {"ERROR": "High", "WARNING": "Medium", "INFO": "Low"}
_BANDIT_SEVERITY = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}

DEFAULT_SEMGREP_RULES = Path(__file__).resolve().parent.parent / "rules" / "semgrep.yml"


def _line_text(code_lines: List[str], line: Optional[int]) -> str:
    if line and 1 <= line <= len(code_lines):
        return code_lines[line - 1].strip()
    return ""


def _finding(
    *,
    agent: str,
    source: str,
    rule_id: str,
    line: Optional[int],
    severity: str,
    issue: str,
    explanation: str,
    code_lines: List[str],
    cwe: str = "",
    docs_url: str = "",
) -> Dict[str, Any]:
    return {
        "severity": severity,
        "issue": issue,
        "explanation": explanation,
        "suggested_fix": f"See the rule documentation: {docs_url}" if docs_url else "",
        "before_code": _line_text(code_lines, line),
        "after_code": "",
        "cwe": cwe,
        "agent": agent,
        "line": line,
        "source": source,
        "rule_id": rule_id,
    }


def _run(cmd: List[str], cwd: str) -> Optional[str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TOOL_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Static analyzer failed to run (%s): %s", cmd[0], exc)
        return None
    return proc.stdout


def _bandit(path: str, cwd: str, code_lines: List[str]) -> List[Dict[str, Any]]:
    out = _run(
        [sys.executable, "-m", "bandit", "-q", "-f", "json", "-s", _BANDIT_SKIP, path],
        cwd,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        logger.warning("bandit returned non-JSON output")
        return []
    findings = []
    for r in data.get("results", []):
        cwe = r.get("issue_cwe") or {}
        cwe_id = f"CWE-{cwe['id']}" if cwe.get("id") else ""
        severity = _BANDIT_SEVERITY.get(str(r.get("issue_severity", "")).upper(), "Low")
        # Low-confidence results are often false positives; don't let them
        # claim the top weight. (Medium stays Medium: e.g. bandit's SQL
        # string-building check is Medium/low-confidence but usually real.)
        if str(r.get("issue_confidence", "")).upper() == "LOW" and severity == "High":
            severity = "Medium"
        findings.append(
            _finding(
                agent="security",
                source="bandit",
                rule_id=str(r.get("test_id", "")),
                line=r.get("line_number"),
                severity=severity,
                issue=str(r.get("test_name", "Security issue")).replace("_", " ").capitalize(),
                explanation=str(r.get("issue_text", "")),
                code_lines=code_lines,
                cwe=cwe_id,
                docs_url=str(r.get("more_info") or ""),
            )
        )
    return findings


def _ruff(path: str, cwd: str, code_lines: List[str]) -> List[Dict[str, Any]]:
    out = _run(
        [
            sys.executable, "-m", "ruff", "check", "--isolated", "--no-cache",
            "--select", _RUFF_SELECT, "--output-format", "json", "--exit-zero", path,
        ],
        cwd,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        logger.warning("ruff returned non-JSON output")
        return []
    findings = []
    for r in data:
        code = str(r.get("code") or "")
        if not code:  # syntax errors have no rule code; the LLM covers those
            continue
        severity = "High" if code in _RUFF_HIGH else "Medium" if code in _RUFF_MEDIUM else "Low"
        findings.append(
            _finding(
                agent="performance" if code.startswith("PERF") else "quality",
                source="ruff",
                rule_id=code,
                line=(r.get("location") or {}).get("row"),
                severity=severity,
                issue=str(r.get("message", code)).split(".")[0][:80],
                explanation=str(r.get("message", "")),
                code_lines=code_lines,
                docs_url=str(r.get("url") or ""),
            )
        )
    return findings


def _semgrep_rules() -> Optional[str]:
    rules = os.getenv("SEMGREP_RULES") or str(DEFAULT_SEMGREP_RULES)
    return rules if Path(rules).exists() else None


def _semgrep(path: str, cwd: str, code_lines: List[str]) -> List[Dict[str, Any]]:
    exe = shutil.which("semgrep")
    rules = _semgrep_rules()
    if not exe or not rules:
        return []
    out = _run(
        [
            exe, "scan", "--config", rules, "--json", "--quiet",
            "--metrics=off", "--disable-version-check", path,
        ],
        cwd,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        logger.warning("semgrep returned non-JSON output")
        return []
    findings = []
    for r in data.get("results", []):
        extra = r.get("extra") or {}
        meta = extra.get("metadata") or {}
        cwe = meta.get("cwe") or ""
        if isinstance(cwe, list):
            cwe = cwe[0] if cwe else ""
        cwe = str(cwe).split(":")[0]
        category = str(meta.get("category", "security")).lower()
        findings.append(
            _finding(
                agent=category if category in ("security", "performance", "quality") else "security",
                source="semgrep",
                rule_id=str(r.get("check_id", "")).split(".")[-1],
                line=(r.get("start") or {}).get("line"),
                severity=_SEMGREP_SEVERITY.get(str(extra.get("severity", "")).upper(), "Medium"),
                issue=str(meta.get("title") or r.get("check_id", "Semgrep finding")).split(".")[-1][:80],
                explanation=str(extra.get("message", "")),
                code_lines=code_lines,
                cwe=cwe,
            )
        )
    return findings


_PYTHON_TOOLS: List[Callable[[str, str, List[str]], List[Dict[str, Any]]]] = [_bandit, _ruff]


def run_static_analysis(code: str, file_path: str = "input.py") -> List[Dict[str, Any]]:
    """Run every applicable analyzer on ``code`` and return normalized findings.

    The code is written to a private temp directory under a fixed name (only
    the extension is taken from ``file_path``), analyzed, and deleted.
    """
    if not Config.STATIC_ANALYSIS_ENABLED or not code.strip():
        return []

    suffix = Path(file_path).suffix.lower() or ".txt"
    code_lines = code.splitlines()
    findings: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="auditor_static_") as tmp:
        target = os.path.join(tmp, f"target{suffix}")
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(code)
        tools = list(_PYTHON_TOOLS) if suffix == ".py" else []
        # semgrep costs ~5s of startup per file. The bundled rules only cover
        # JS/TS (Python is handled by bandit + ruff), so skip it for Python
        # unless the user supplied their own rule file.
        if suffix != ".py" or os.getenv("SEMGREP_RULES"):
            tools.append(_semgrep)
        for tool in tools:
            try:
                findings.extend(tool(target, tmp, code_lines))
            except Exception as exc:  # a broken tool must never fail the audit
                logger.warning("Static analyzer %s crashed: %s", tool.__name__, exc)
    return findings


def hints_for_chunk(static_findings: List[Dict[str, Any]], chunk: str, agent: str) -> str:
    """Lines in ``chunk`` that tools already flagged for ``agent``, as a short
    bullet list for the LLM prompt (so it looks for *other* problems)."""
    lines = []
    for f in static_findings:
        code = f.get("before_code", "")
        if f.get("agent") == agent and code and code in chunk:
            lines.append(f"- {f.get('issue')} ({f.get('rule_id')}): {code[:100]}")
    return "\n".join(lines[:8]) if lines else "None"
