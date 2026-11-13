# Author: urumb
import json
import logging
import threading
from typing import Any, Callable, Dict, Optional

from src.graph import graph

logger = logging.getLogger(__name__)

# Type alias for the optional log callback.
LogCallback = Optional[Callable[[str, str, str], None]]
EventCallback = Optional[Callable[[str, Dict[str, Any]], None]]


def _attach_coverage(final_report: str, plan: Dict[str, Any]) -> str:
    """Record how much of the file was actually analyzed in the report, so
    the UI can say when chunks were skipped instead of implying full coverage."""
    if "chunks_total" not in plan:
        return final_report
    try:
        report = json.loads(final_report)
    except (json.JSONDecodeError, TypeError):
        return final_report
    if not isinstance(report, dict):
        return final_report
    report["coverage"] = {
        "chunks_total": plan["chunks_total"],
        "chunks_analyzed": plan.get("chunks_analyzed", plan["chunks_total"]),
    }
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
        output["final_report"] = _attach_coverage(output.get("final_report", ""), plan)
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
        _log("System", "Pipeline completed successfully", "success")
        logger.info("Audit pipeline completed successfully")
        return output
    except Exception as exc:
        _log("System", f"Pipeline failed: {exc}", "error")
        logger.error("Audit pipeline failed: %s", exc)
        raise RuntimeError(f"Audit pipeline failed: {exc}") from exc
