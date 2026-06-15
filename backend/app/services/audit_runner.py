# Author: urumb
import logging
from typing import Any, Callable, Dict, Optional

from src.config import Config
from src.graph import graph

logger = logging.getLogger(__name__)

# Type alias for the optional log callback.
LogCallback = Optional[Callable[[str, str, str], None]]
EventCallback = Optional[Callable[[str, Dict[str, Any]], None]]


def run_audit_on_code(
    code: str,
    log_callback: LogCallback = None,
    event_callback: EventCallback = None,
    repository_file_count: int = 1,
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

    Returns:
        Full AuditorState dict after graph execution, including
        ``final_report``, ``security_analysis``, etc.

    Raises:
        RuntimeError: If graph invocation fails.
    """
    Config.validate()

    def _log(agent: str, message: str, level: str = "info") -> None:
        """Emit a log event if a callback is registered."""
        if log_callback:
            log_callback(agent, message, level)

    initial_state = {
        "original_code": code,
        "repository_file_count": repository_file_count,
        "code_snippets": [],
        "execution_plan": {},
        "event_callback": event_callback,
        "security_analysis": [],
        "performance_analysis": [],
        "past_audits": [],
        "final_report": "",
    }

    _log("Manager Agent", "Decomposing code into analyzable snippets...")
    logger.info("Invoking LangGraph audit pipeline (%d chars)", len(code))

    try:
        output = graph.invoke(initial_state)
        output.pop("event_callback", None)

        planned_agents = (output.get("execution_plan") or {}).get("agents", [])
        if "reviewer" in planned_agents:
            _log("Reviewer Agent", "Synthesizing final report...")
        _log("System", "Pipeline completed successfully", "success")
        logger.info("Audit pipeline completed successfully")
        return output
    except Exception as exc:
        _log("System", f"Pipeline failed: {exc}", "error")
        logger.error("Audit pipeline failed: %s", exc)
        raise RuntimeError(f"Audit pipeline failed: {exc}") from exc
