# Author: urumb
import threading
from typing import TypedDict, List, Dict, Any, Optional, Callable

ExecutionPlan = Dict[str, Any]
EventCallback = Callable[[str, Dict[str, Any]], None]

class AuditorState(TypedDict):
    """
    Shared state key-value store for the Multi-Agent Auditor.
    """
    original_code: str
    file_path: Optional[str]  # used for the file extension (language) only
    repository_file_count: Optional[int]
    depth: Optional[str]  # "quick" (security only) or "full" (all agents)
    code_snippets: List[str]  # Decomposed functions/blocks
    execution_plan: ExecutionPlan
    event_callback: Optional[EventCallback]
    cancel_event: Optional[threading.Event]  # set when the audit is abandoned
    
    # Analysis results from agents, mapped by snippet index or ID
    security_analysis: List[Dict[str, Any]] 
    performance_analysis: List[Dict[str, Any]]
    quality_analysis: List[Dict[str, Any]]
    
    # Findings from bandit / ruff / semgrep (see static_analysis.py)
    static_findings: List[Dict[str, Any]]

    # Context retrieved from memory (ChromaDB)
    past_audits: List[str]
    
    # Final consolidated report
    final_report: str
