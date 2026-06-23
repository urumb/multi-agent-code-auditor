# Author: urumb
import json
import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field


SEVERITIES = {"Critical", "High", "Medium", "Low"}
SEVERITY_WEIGHTS = {
    "Critical": 10,
    "High": 7,
    "Medium": 4,
    "Low": 1,
}
AGENT_MULTIPLIERS = {
    "security": 1.0,
    "performance": 0.6,
    "quality": 0.4,
}


class Finding(BaseModel):
    severity: str = "Low"
    issue: str = "Unstructured finding"
    explanation: str = ""
    suggested_fix: str = ""
    before_code: str = ""
    after_code: str = ""
    cwe: str = ""
    agent: str = Field(default="", exclude=False)


def _extract_json_object(text: str) -> Any:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(stripped[start : end + 1])

    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(stripped[start : end + 1])

    raise json.JSONDecodeError("No JSON object or array found", stripped, 0)


def _normalize_severity(value: Any) -> str:
    text = str(value or "Low").strip().lower()
    mapping = {
        "critical": "Critical",
        "high": "High",
        "medium": "Medium",
        "moderate": "Medium",
        "low": "Low",
        "warning": "Medium",
        "info": "Low",
        "informational": "Low",
    }
    return mapping.get(text, "Low")


def normalize_findings(raw: Any, agent: str, snippet: str = "") -> List[Dict[str, Any]]:
    """Normalize agent output to Finding dictionaries.

    Malformed JSON degrades to one Low finding that preserves the raw guidance,
    instead of failing the pipeline or dropping potentially useful output.
    """
    if raw is None:
        return []

    if isinstance(raw, str):
        if not raw.strip():
            return []
        try:
            payload = _extract_json_object(raw)
        except json.JSONDecodeError:
            return [
                Finding(
                    severity="Low",
                    issue=f"Unstructured {agent.title()} finding",
                    explanation=raw.strip(),
                    suggested_fix="Review the agent output and convert it into a concrete code change.",
                    before_code=snippet,
                    after_code="",
                    cwe="",
                    agent=agent,
                ).model_dump()
            ]
    else:
        payload = raw

    if isinstance(payload, dict):
        items = payload.get("findings", payload.get("issues", []))
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    findings: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue") or item.get("title") or item.get("description") or "Finding"
        explanation = item.get("explanation") or item.get("description") or ""
        suggested_fix = item.get("suggested_fix") or item.get("suggestedFix") or item.get("fix") or ""
        before_code = item.get("before_code") or item.get("beforeCode") or item.get("codeSnippet") or ""
        after_code = item.get("after_code") or item.get("afterCode") or item.get("fixed_code") or ""
        cwe = item.get("cwe") or item.get("CWE") or ""

        findings.append(
            Finding(
                severity=_normalize_severity(item.get("severity")),
                issue=str(issue),
                explanation=str(explanation),
                suggested_fix=str(suggested_fix),
                before_code=str(before_code),
                after_code=str(after_code),
                cwe=str(cwe),
                agent=agent,
            ).model_dump()
        )

    return findings


def collect_findings(*analysis_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for group in analysis_groups:
        for result in group or []:
            for finding in result.get("findings", []):
                copied = dict(finding)
                copied.setdefault("snippet_index", result.get("snippet_index"))
                findings.append(copied)
    return findings


def compute_risk_score(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    breakdown = {"security": 0.0, "performance": 0.0, "quality": 0.0}
    max_severity = "Low"
    max_weight = 0

    for finding in findings:
        severity = _normalize_severity(finding.get("severity"))
        agent = str(finding.get("agent") or "").lower()
        weight = SEVERITY_WEIGHTS.get(severity, 1)
        multiplier = AGENT_MULTIPLIERS.get(agent, 0.4)
        if agent in breakdown:
            breakdown[agent] += weight * multiplier
        if weight > max_weight:
            max_weight = weight
            max_severity = severity

    total = sum(breakdown.values())
    return {
        "risk_score": round(total, 2),
        "risk_breakdown": {key: round(value, 2) for key, value in breakdown.items()},
        "max_severity": max_severity if findings else "Low",
    }
