# Author: urumb
import logging
from typing import Any, Callable, Dict, Optional

from src.config import Config
from src.graph import graph

logger = logging.getLogger(__name__)

# Type alias for the optional log callback.
LogCallback = Optional[Callable[[str, str, str], None]]


def run_audit_on_code(
    code: str,
    log_callback: LogCallback = None,
) -> Dict[str, Any]:
    """Run the full LangGraph audit pipeline on a single code string.

    Builds the initial AuditorState, invokes the compiled graph, and
    returns the final state dict containing agent analysis results.

    Args:
        code: Raw source code content to audit.
        log_callback: Optional callback ``(agent, message, level)`` invoked
            at each major pipeline step to emit real-time progress events.

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
        "code_snippets": [],
        "security_analysis": [],
        "performance_analysis": [],
        "past_audits": [],
        "final_report": "",
    }

    _log("Manager Agent", "Decomposing code into analyzable snippets...")
    logger.info("Invoking LangGraph audit pipeline (%d chars)", len(code))

    try:
        _log("Security Agent", "Scanning for vulnerabilities...")
        _log("Performance Agent", "Analyzing complexity...")

        output = graph.invoke(initial_state)

        _log("Reviewer Agent", "Synthesizing final report...")
        _log("System", "Pipeline completed successfully", "success")
        logger.info("Audit pipeline completed successfully")
        return output
    except Exception as exc:
        _log("System", f"Pipeline failed: {exc}", "error")
        logger.error("Audit pipeline failed: %s", exc)
        raise RuntimeError(f"Audit pipeline failed: {exc}") from exc
