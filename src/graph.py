# Author: urumb
import logging
import json

from langgraph.graph import StateGraph, START, END
from .state import AuditorState
from .agents.manager import ManagerAgent
from .agents.security import SecurityAgent
from .agents.performance import PerformanceAgent
from .agents.reviewer import ReviewerAgent
from .utils.memory import AuditMemory
from .config import Config
from .findings import build_findings, compute_risk_score
from .static_analysis import run_static_analysis

logger = logging.getLogger(__name__)

# Initialize Agents
manager = ManagerAgent()
security = SecurityAgent()
performance = PerformanceAgent()
reviewer = ReviewerAgent()
memory: AuditMemory | None = None

AGENT_LABELS = {
    "manager": "Manager Agent",
    "security": "Security Agent",
    "performance": "Performance Agent",
    "quality": "Quality Agent",
    "reviewer": "Reviewer Agent",
}

ENABLED_AGENTS = {"security", "performance", "quality", "reviewer"}


def _get_memory() -> AuditMemory:
    global memory
    if memory is None:
        memory = AuditMemory()
    return memory


def _planned_agents(state: AuditorState) -> set[str]:
    plan = state.get("execution_plan") or {}
    return set(plan.get("agents", [])) & ENABLED_AGENTS


def _emit(state: AuditorState, event_type: str, agent_name: str) -> None:
    callback = state.get("event_callback")
    if callback:
        callback(event_type, {"agent": agent_name})


def _emit_payload(state: AuditorState, event_type: str, payload: dict) -> None:
    callback = state.get("event_callback")
    if callback:
        callback(event_type, payload)


def _run_agent_node(state: AuditorState, agent_key: str, run_fn):
    agent_name = AGENT_LABELS[agent_key]
    _emit(state, "agent_started", agent_name)
    try:
        result = run_fn(state)
        _emit(state, "agent_completed", agent_name)
        return result
    except Exception:
        _emit(state, "agent_failed", agent_name)
        raise


def manager_node(state: AuditorState):
    agent_name = AGENT_LABELS["manager"]
    _emit(state, "agent_started", agent_name)
    try:
        result = manager.run(state)
        _emit(state, "agent_completed", agent_name)
        _emit_payload(state, "execution_plan", result.get("execution_plan", {}))
        return result
    except Exception:
        _emit(state, "agent_failed", agent_name)
        raise

def static_node(state: AuditorState):
    """Run bandit/ruff/semgrep once over the whole file before the LLM agents.

    Only findings for agents in the execution plan are kept, so a Quick
    (security-only) scan doesn't report quality/performance lint.
    """
    planned = _planned_agents(state)
    findings = [
        f for f in run_static_analysis(state.get("original_code", ""), state.get("file_path") or "input.py")
        if f.get("agent") in planned
    ]
    if findings:
        tools = sorted({f["source"] for f in findings})
        _emit_payload(state, "log", {
            "agent": "Static Analysis",
            "message": f"{len(findings)} issue(s) flagged by {', '.join(tools)}",
            "level": "info",
        })
    return {"static_findings": findings}


def retrieval_node(state: AuditorState):
    if not Config.MEMORY_ENABLED:
        return {"past_audits": []}
    if _planned_agents(state) == {"security"}:
        logger.debug("Memory: skipping context retrieval for fast path")
        return {"past_audits": []}

    logger.info("Memory: retrieving context")
    snippets = state.get("code_snippets", [])
    past_audits = []
    
    # Retrieve context for each snippet (limit to top 1 to avoid context overflow)
    # Only retrieve context once for the entire file to save time (just use the first snippet)
    audit_memory = _get_memory()
    if snippets:
        try:
            results = audit_memory.retrieve_similar(snippets[0], n_results=1)
            past_audits.extend(results)
        except Exception as e:
            logger.warning("Memory: error retrieving context: %s", e)
            pass
    
    # Deduplicate
    unique_audits = list(set(past_audits))
    return {"past_audits": unique_audits}

def security_node(state: AuditorState):
    return _run_agent_node(state, "security", security.run)

def performance_node(state: AuditorState):
    return _run_agent_node(state, "performance", performance.run)

from .agents.quality import QualityAgent
quality = QualityAgent()
def quality_node(state: AuditorState):
    return _run_agent_node(state, "quality", quality.run)

def reviewer_node(state: AuditorState):
    return _run_agent_node(state, "reviewer", reviewer.run)

def finalize_node(state: AuditorState):
    """
    Produces a structured report when the execution plan intentionally skips
    Reviewer (e.g. the fast path for small snippets). Uses the same findings
    schema as the full Reviewer path so the frontend never has to special-case
    "fast path" results.
    """
    if state.get("final_report"):
        return {}

    all_findings = build_findings(state)
    risk_info = compute_risk_score(all_findings)

    if all_findings:
        summary = f"{len(all_findings)} finding(s) detected by the Security Agent and static analysis."
    else:
        summary = "No issues were detected by the Security Agent or static analysis."

    return {
        "final_report": json.dumps({
            "Executive Summary": "Quick security scan - only the Security Agent ran. Run a Full scan for performance and quality analysis too.",
            "Findings Summary": summary,
            "risk_score": risk_info["risk_score"],
            "risk_breakdown": risk_info["risk_breakdown"],
            "max_severity": risk_info["max_severity"],
            "findings": all_findings,
            "top_risk_files": [],
        })
    }

def save_node(state: AuditorState):
    if not Config.MEMORY_ENABLED:
        return {}
    if "reviewer" not in _planned_agents(state):
        logger.debug("Memory: skipping save for fast path")
        return {}

    logger.info("Memory: saving audit results")
    snippets = state.get("code_snippets", [])
    final_report = state.get("final_report", "")
    security_analysis = state.get("security_analysis", [])
    
    # Save the first snippet as representative (or all?)
    # For now, let's save the first snippet with the summary to avoid duplication
    if snippets:
        # Extract vulnerabilities summary
        vulns = [s.get('analysis') for s in security_analysis if 'analysis' in s]
        summary_finding = f"Report Logic Summary:\n{final_report[:200]}...\nVulnerabilities: {len(vulns)} found."
        
        _get_memory().save_audit(snippets[0], summary_finding, tags=["audit", "v1"])
        
    return {}

def route_after_manager(state: AuditorState):
    planned = _planned_agents(state)
    if planned == {"security"}:
        return "security"
    return "retrieve"

def route_to_planned_agents(state: AuditorState):
    planned = _planned_agents(state)
    routes = []
    if "security" in planned:
        routes.append("security")
    if "performance" in planned:
        routes.append("performance")
    if "quality" in planned:
        routes.append("quality")
    return routes or ["finalize"]

def route_after_analysis(state: AuditorState):
    if "reviewer" in _planned_agents(state):
        return "reviewer"
    return "finalize"

# Build Graph
builder = StateGraph(AuditorState)

builder.add_node("manager", manager_node)
builder.add_node("static", static_node)
builder.add_node("retrieve", retrieval_node)
builder.add_node("security", security_node)
builder.add_node("performance", performance_node)
builder.add_node("quality", quality_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("finalize", finalize_node)
builder.add_node("save", save_node)

# Flow
builder.add_edge(START, "manager")
builder.add_edge("manager", "static")
builder.add_conditional_edges("static", route_after_manager, {
    "retrieve": "retrieve",
    "security": "security",
})
builder.add_conditional_edges("retrieve", route_to_planned_agents, {
    "security": "security",
    "performance": "performance",
    "quality": "quality",
    "finalize": "finalize",
})
builder.add_conditional_edges("security", route_after_analysis, {
    "reviewer": "reviewer",
    "finalize": "finalize",
})
builder.add_conditional_edges("performance", route_after_analysis, {
    "reviewer": "reviewer",
    "finalize": "finalize",
})
builder.add_conditional_edges("quality", route_after_analysis, {
    "reviewer": "reviewer",
    "finalize": "finalize",
})
builder.add_edge("reviewer", "save")
builder.add_edge("finalize", END)
builder.add_edge("save", END)

graph = builder.compile()
