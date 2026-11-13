# Author: urumb
import json
import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from src.graph import graph

logger = logging.getLogger(__name__)

# Type alias for the optional log callback.
LogCallback = Optional[Callable[[str, str, str], None]]
EventCallback = Optional[Callable[[str, Dict[str, Any]], None]]


_AI_AGENTS = (("security", "Security Agent"), ("performance", "Performance Agent"), ("quality", "Quality Agent"))
_UNREACHABLE_MARKERS = ("10061", "refused", "ConnectError", "Failed to connect", "Name or service not known")


def ai_failures(output: Dict[str, Any]) -> List[str]:
    """Human-readable warnings for AI agents whose LLM calls failed.

    Agents record a failed call per chunk instead of failing the audit, so
    without this an Ollama outage would silently turn a full audit into a
    tools-only one that looks complete.
    """
    warnings = []
    for key, label in _AI_AGENTS:
        results = output.get(f"{key}_analysis") or []
        errors = [str(r["error"]) for r in results if r.get("error")]
        if not errors:
            continue
        if any(marker in errors[0] for marker in _UNREACHABLE_MARKERS):
            reason = "Ollama isn't reachable; is it running?"
        else:
            reason = errors[0][:160]
        warnings.append(
            f"{label}: AI analysis failed for {len(errors)} of {len(results)} chunk(s) ({reason}). "
            "Only static-analysis findings are shown for it."
        )
    return warnings


def _annotate_report(final_report: str, plan: Dict[str, Any], warnings: List[str]) -> str:
    """Record in the report how much was actually analyzed and what failed,
    so the UI never implies a full AI audit that didn't happen."""
    if "chunks_total" not in plan and not warnings:
        return final_report
    try:
        report = json.loads(final_report)
    except (json.JSONDecodeError, TypeError):
        return final_report
    if not isinstance(report, dict):
        return final_report
    if "chunks_total" in plan:
        report["coverage"] = {
            "chunks_total": plan["chunks_total"],
            "chunks_analyzed": plan.get("chunks_analyzed", plan["chunks_total"]),
        }
    if warnings:
        report["warnings"] = warnings
    return json.dumps(report)


def run_audit_on_code(
    code: str,
    log_callback: LogCallback = None,
    event_callback: EventCallback = None,
    repository_file_count: int = 1,
    depth: str = "full",
    cancel_event: Optional[threading.Event] = None,
    file_path: str = "input.py",
) -> Dict[str, Any]:
    """Run the full LangGraph audit pipeline on a single code string.

    Builds the initial AuditorState, invokes the compiled graph, and
    returns the final state dict containing agent analysis results.

    Args:
        code: Raw source code content to audit.
        log_callback: Optional callback ``(agent, message, level)`` invoked
            at each major pipeline step to emit real-time progress events.
        event_callback: Optional callback ``(event_type, payload)`` invoked
            for structured SSE lifecycle events.
        repository_file_count: Number of files in the original input batch.
        cancel_event: Optional event; once set, remaining LLM calls are
            skipped and the pipeline raises AuditCancelled.
        file_path: Path of the audited file; its extension picks the
            static analyzers to run.

    Returns:
        Full AuditorState dict after graph execution, including
        ``final_report``, ``security_analysis``, etc.

    Raises:
        RuntimeError: If graph invocation fails.
    """
    def _log(agent: str, message: str, level: str = "info") -> None:
        """Emit a log event if a callback is registered."""
        if log_callback:
            log_callback(agent, message, level)

    initial_state = {
        "original_code": code,
        "file_path": file_path,
        "static_findings": [],
        "repository_file_count": repository_file_count,
        "depth": depth,
        "code_snippets": [],
        "execution_plan": {},
        "event_callback": event_callback,
        "cancel_event": cancel_event,
        "security_analysis": [],
        "performance_analysis": [],
        "quality_analysis": [],
        "past_audits": [],
        "final_report": "",
    }

    _log("Manager Agent", "Decomposing code into analyzable snippets...")
    logger.info("Invoking LangGraph audit pipeline (%d chars)", len(code))

    try:
        output = graph.invoke(initial_state)
        output.pop("event_callback", None)
        output.pop("cancel_event", None)

        plan = output.get("execution_plan") or {}
        warnings = ai_failures(output)
        output["final_report"] = _annotate_report(output.get("final_report", ""), plan, warnings)
        for warning in warnings:
            _log("System", warning, "warning")
        skipped = plan.get("chunks_total", 0) - plan.get("chunks_analyzed", 0)
        if skipped > 0:
            _log(
                "Manager Agent",
                f"File too large: analyzed the {plan['chunks_analyzed']} largest of "
                f"{plan['chunks_total']} code chunks ({skipped} skipped)",
                "warning",
            )

        planned_agents = plan.get("agents", [])
        if "reviewer" in planned_agents:
            _log("Reviewer Agent", "Synthesizing final report...")
        if warnings:
            _log("System", "Pipeline completed with warnings (see above)", "warning")
            logger.warning("Audit pipeline completed with warnings: %s", "; ".join(warnings))
        else:
            _log("System", "Pipeline completed successfully", "success")
            logger.info("Audit pipeline completed successfully")
        return output
    except Exception as exc:
        _log("System", f"Pipeline failed: {exc}", "error")
        logger.error("Audit pipeline failed: %s", exc)
        raise RuntimeError(f"Audit pipeline failed: {exc}") from exc
