# Author: urumb
import json
import re
from typing import Any, Dict, List, Optional

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
    # 1-based line in the audited file. Set by static analyzers directly, or
    # for LLM findings by locating ``before_code`` in the source; None when
    # the quoted code can't be found (so the UI never shows a made-up line).
    line: Optional[int] = None
    # Who reported it: "llm", a tool name ("bandit", "ruff", "semgrep"), or
    # several joined with "+" when duplicates were merged.
    source: str = "llm"
    rule_id: str = ""


def _loads(text: str) -> Any:
    """json.loads that keeps BOTH values when a model repeats a key.

    Small local models sometimes emit {"findings": [a], "findings": [b]};
    plain json.loads silently keeps only the last one, dropping real findings.
    Repeated list values are concatenated instead.
    """

    def merge_pairs(pairs):
        merged: Dict[str, Any] = {}
        for key, value in pairs:
            if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key] = merged[key] + value
            else:
                merged[key] = value
        return merged

    return json.loads(text, object_pairs_hook=merge_pairs)


def _candidate_json_slice(text: str) -> Any:
    """Try to parse text as JSON, trimming to the outermost {..} or [..] if needed."""
    text = text.strip()
    if not text:
        return None
    try:
        return _loads(text)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return _loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _extract_json_object(text: str) -> Any:
    """Extract the model's structured JSON answer from free-form LLM output.

    Local models frequently prose-explain before emitting JSON, and often wrap
    illustrative code snippets in their own ``` fences ahead of the real
    answer. Preferring the LAST fenced block (and json-tagged fences over
    generic ones) avoids latching onto an early code example instead of the
    actual structured response.
    """
    stripped = text.strip()

    candidates: List[str] = []
    candidates.extend(reversed(re.findall(r"```json\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)))
    candidates.extend(reversed(re.findall(r"```[a-zA-Z0-9_+-]*\s*(.*?)```", stripped, re.DOTALL)))
    candidates.append(stripped)

    for candidate in candidates:
        result = _candidate_json_slice(candidate)
        if result is not None:
            return result

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


SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
_MIN_ANCHOR_CHARS = 8


def _squash(text: str) -> str:
    return " ".join(text.split())


def locate_line(before_code: str, code_lines: List[str]) -> Optional[int]:
    """Find the 1-based line in the file where ``before_code`` appears.

    LLMs quote code loosely (re-indented, trimmed, sometimes several lines),
    so each substantial quoted line is compared whitespace-insensitively
    against each source line. Returns None rather than guessing.
    """
    squashed_source = [_squash(line) for line in code_lines]
    for raw in (before_code or "").splitlines():
        candidate = _squash(raw)
        if len(candidate) < _MIN_ANCHOR_CHARS:
            continue
        for idx, source_line in enumerate(squashed_source):
            if candidate in source_line:
                return idx + 1
        for idx, source_line in enumerate(squashed_source):
            if len(source_line) >= _MIN_ANCHOR_CHARS and source_line in candidate:
                return idx + 1
    return None


def _merge_pair(kept: Dict[str, Any], dup: Dict[str, Any]) -> None:
    """Fold ``dup`` into ``kept``: highest severity, the richer LLM text,
    and every source/rule that reported it."""
    if SEVERITY_ORDER.index(_normalize_severity(dup.get("severity"))) < SEVERITY_ORDER.index(
        _normalize_severity(kept.get("severity"))
    ):
        kept["severity"] = _normalize_severity(dup.get("severity"))
    if dup.get("source") == "llm" and kept.get("source") != "llm":
        for key in ("issue", "explanation", "suggested_fix", "after_code"):
            if dup.get(key):
                kept[key] = dup[key]
    for key in ("cwe", "rule_id", "after_code", "suggested_fix"):
        if not kept.get(key) and dup.get(key):
            kept[key] = dup[key]
    sources = set(str(kept.get("source") or "llm").split("+")) | set(str(dup.get("source") or "llm").split("+"))
    kept["source"] = "+".join(sorted(sources))


def _is_duplicate(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    if a.get("agent") != b.get("agent"):
        return False
    if a.get("line") is not None and a.get("line") == b.get("line"):
        both_tools = a.get("source") != "llm" and b.get("source") != "llm"
        # Two different tool rules on one line are two different problems.
        return not (both_tools and a.get("rule_id") != b.get("rule_id"))
    if a.get("line") is None and b.get("line") is None:
        return _squash(str(a.get("issue", ""))).lower() == _squash(str(b.get("issue", ""))).lower()
    return False


def merge_findings(
    llm_findings: List[Dict[str, Any]],
    static_findings: Optional[List[Dict[str, Any]]] = None,
    original_code: str = "",
) -> List[Dict[str, Any]]:
    """Combine LLM and static-analysis findings into one de-duplicated list.

    - LLM findings get a verified line number when their quoted code is found.
    - The same problem reported twice (same agent and line, e.g. bandit and
      the Security Agent both flagging one SQL query) becomes one finding.
    - Output is sorted most severe first, then by line.
    """
    code_lines = original_code.splitlines()
    combined: List[Dict[str, Any]] = []
    for finding in static_findings or []:
        combined.append(dict(finding))
    for finding in llm_findings:
        copied = dict(finding)
        copied.setdefault("source", "llm")
        if copied.get("line") is None and code_lines:
            copied["line"] = locate_line(copied.get("before_code", ""), code_lines)
        combined.append(copied)

    merged: List[Dict[str, Any]] = []
    for finding in combined:
        for kept in merged:
            if _is_duplicate(kept, finding):
                _merge_pair(kept, finding)
                break
        else:
            merged.append(finding)

    def sort_key(f: Dict[str, Any]):
        sev = _normalize_severity(f.get("severity"))
        line = f.get("line")
        return (SEVERITY_ORDER.index(sev), line is None, line or 0)

    merged.sort(key=sort_key)
    return merged


def build_findings(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All findings for one audited file, from every agent and tool."""
    llm = collect_findings(
        state.get("security_analysis", []),
        state.get("performance_analysis", []),
        state.get("quality_analysis", []),
    )
    return merge_findings(llm, state.get("static_findings", []), state.get("original_code", ""))
