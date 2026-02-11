# Author: urumb
from typing import TypedDict, List, Dict, Any, Optional

class AuditorState(TypedDict):
    """
    Shared state key-value store for the Multi-Agent Auditor.
    """
    original_code: str
    code_snippets: List[str]  # Decomposed functions/blocks
    
    # Analysis results from agents, mapped by snippet index or ID
    security_analysis: List[Dict[str, Any]] 
    performance_analysis: List[Dict[str, Any]]
    
    # Context retrieved from memory (ChromaDB)
    past_audits: List[str]
    
    # Final consolidated report
    final_report: str
