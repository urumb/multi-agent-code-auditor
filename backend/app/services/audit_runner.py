# Author: urumb
import logging
from typing import Any, Dict

from src.config import Config
from src.graph import graph

logger = logging.getLogger(__name__)


def run_audit_on_code(code: str) -> Dict[str, Any]:
    """Run the full LangGraph audit pipeline on a single code string.

    Builds the initial AuditorState, invokes the compiled graph, and
    returns the final state dict containing agent analysis results.

    Args:
        code: Raw source code content to audit.

    Returns:
        Full AuditorState dict after graph execution, including
        ``final_report``, ``security_analysis``, etc.

    Raises:
        RuntimeError: If graph invocation fails.
    """
    Config.validate()

    initial_state = {
        "original_code": code,
        "code_snippets": [],
        "security_analysis": [],
        "performance_analysis": [],
        "past_audits": [],
        "final_report": "",
    }

    logger.info("Invoking LangGraph audit pipeline (%d chars)", len(code))

    try:
        output = graph.invoke(initial_state)
        logger.info("Audit pipeline completed successfully")
        return output
    except Exception as exc:
        logger.error("Audit pipeline failed: %s", exc)
        raise RuntimeError(f"Audit pipeline failed: {exc}") from exc
