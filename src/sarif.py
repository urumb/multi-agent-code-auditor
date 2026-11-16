# Author: urumb
"""Convert audit findings to SARIF 2.1.0.

SARIF is the standard format for static-analysis results. GitHub code
scanning (free for public repositories), VS Code's SARIF Viewer and many
CI tools read it, so findings show up next to the code they refer to.
"""
import re
from typing import Any, Dict, Iterable, List, Optional

TOOL_NAME = "multi-agent-code-auditor"
TOOL_URI = "https://github.com/urumb/multi-agent-code-auditor"
SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

# SARIF result level per severity.
_LEVEL = {"Critical": "error", "High": "error", "Medium": "warning", "Low": "note"}
# GitHub uses "security-severity" (0-10) to rank security alerts.
_SECURITY_SEVERITY = {"Critical": "9.5", "High": "8.0", "Medium": "5.5", "Low": "2.0"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "finding"


def rule_id(finding: Dict[str, Any]) -> str:
    """Stable rule id: the tool's own rule (e.g. bandit B608) when there is
    one, otherwise ``ai/<agent>/<issue-slug>`` for AI-only findings."""
    if finding.get("rule_id"):
        tool = str(finding.get("source") or "tool").split("+")[0]
        if tool == "llm":
            tool = next((s for s in str(finding.get("source")).split("+") if s != "llm"), "tool")
        return f"{tool}/{finding['rule_id']}"
    return f"ai/{finding.get('agent') or 'general'}/{_slug(str(finding.get('issue', '')))}"


def to_sarif(files: Iterable[Dict[str, Any]], tool_version: str = "0.6.0") -> Dict[str, Any]:
    """Build a SARIF log from ``[{"file_path": str, "findings": [...]}, ...]``.

    Findings use the schema from src/findings.py (severity, issue,
    explanation, suggested_fix, agent, line, source, rule_id, cwe).
    """
    rules: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []

    for file in files:
        path = str(file.get("file_path", "")).replace("\\", "/")
        for f in file.get("findings") or []:
            severity = f.get("severity") if f.get("severity") in _LEVEL else "Low"
            rid = rule_id(f)
            agent = str(f.get("agent") or "general")
            if rid not in rules:
                tags = [agent]
                if f.get("cwe"):
                    tags.append(str(f["cwe"]).lower().replace("cwe-", "external/cwe/cwe-"))
                rule: Dict[str, Any] = {
                    "id": rid,
                    "name": _slug(str(f.get("issue", rid))),
                    "shortDescription": {"text": str(f.get("issue") or rid)},
                    "properties": {"tags": tags},
                }
                if agent == "security":
                    rule["properties"]["security-severity"] = _SECURITY_SEVERITY[severity]
                rules[rid] = rule

            message = str(f.get("explanation") or f.get("issue") or rid)
            if f.get("suggested_fix"):
                message += f"\n\nSuggested fix: {f['suggested_fix']}"
            line: Optional[int] = f.get("line") if isinstance(f.get("line"), int) and f.get("line") > 0 else None
            location = {
                "physicalLocation": {
                    "artifactLocation": {"uri": path, "uriBaseId": "%SRCROOT%"},
                    # SARIF consumers require a region; findings without a
                    # verified line point at the top of the file.
                    "region": {"startLine": line or 1},
                }
            }
            results.append({
                "ruleId": rid,
                "level": _LEVEL[severity],
                "message": {"text": message},
                "locations": [location],
                "properties": {
                    "severity": severity,
                    "agent": agent,
                    "source": f.get("source") or "llm",
                    "lineVerified": line is not None,
                },
            })

    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": TOOL_NAME,
                "informationUri": TOOL_URI,
                "version": tool_version,
                "rules": list(rules.values()),
            }},
            "results": results,
        }],
    }
