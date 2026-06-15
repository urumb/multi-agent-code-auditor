# Author: urumb
from langgraph.graph import StateGraph, START, END
from .state import AuditorState
from .agents.manager import ManagerAgent
from .agents.security import SecurityAgent
from .agents.performance import PerformanceAgent
from .agents.reviewer import ReviewerAgent
from .utils.memory import AuditMemory

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
    "reviewer": "Reviewer Agent",
}

ENABLED_AGENTS = {"security", "performance", "reviewer"}


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

def retrieval_node(state: AuditorState):
    if _planned_agents(state) == {"security"}:
        print("--- Memory: Skipping Context Retrieval for Small Snippet ---")
        return {"past_audits": []}

    print("--- Memory: Retrieving Context ---")
    snippets = state.get("code_snippets", [])
    past_audits = []
    
    # Retrieve context for each snippet (limit to top 1 to avoid context overflow)
    audit_memory = _get_memory()
    for snippet in snippets[:5]: # Cap at 5 snippets for performance
        results = audit_memory.retrieve_similar(snippet, n_results=1)
        past_audits.extend(results)
    
    # Deduplicate
    unique_audits = list(set(past_audits))
    return {"past_audits": unique_audits}

def security_node(state: AuditorState):
    return _run_agent_node(state, "security", security.run)

def performance_node(state: AuditorState):
    return _run_agent_node(state, "performance", performance.run)

def reviewer_node(state: AuditorState):
    return _run_agent_node(state, "reviewer", reviewer.run)

def finalize_node(state: AuditorState):
    """
    Produces a minimal report when the execution plan intentionally skips Reviewer.
    """
    if state.get("final_report"):
        return {}

    security_data = state.get("security_analysis", [])
    sec_text = "\n".join(
        [
            f"Snippet {x['snippet_index']}: {x.get('analysis', 'Error: ' + str(x.get('error', 'Unknown')))}"
            for x in security_data
        ]
    )
    return {
        "final_report": (
            "# Fast Security Audit\n\n"
            "Execution plan selected the Security Agent only for this small snippet.\n\n"
            "## Security Analysis\n\n"
            f"{sec_text or 'No security findings were produced.'}"
        )
    }

def save_node(state: AuditorState):
    if "reviewer" not in _planned_agents(state):
        print("--- Memory: Skipping Save for Fast Path ---")
        return {}

    print("--- Memory: Saving Audit Results ---")
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
    return routes or ["finalize"]

def route_after_security(state: AuditorState):
    planned = _planned_agents(state)
    if "reviewer" in planned:
        return "reviewer"
    return "finalize"

def route_after_performance(state: AuditorState):
    if "reviewer" in _planned_agents(state):
        return "reviewer"
    return "finalize"

# Build Graph
builder = StateGraph(AuditorState)

builder.add_node("manager", manager_node)
builder.add_node("retrieve", retrieval_node)
builder.add_node("security", security_node)
builder.add_node("performance", performance_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("finalize", finalize_node)
builder.add_node("save", save_node)

# Flow
builder.add_edge(START, "manager")
builder.add_conditional_edges("manager", route_after_manager, {
    "retrieve": "retrieve",
    "security": "security",
})
builder.add_conditional_edges("retrieve", route_to_planned_agents, {
    "security": "security",
    "performance": "performance",
    "finalize": "finalize",
})
builder.add_conditional_edges("security", route_after_security, {
    "reviewer": "reviewer",
    "finalize": "finalize",
})
builder.add_conditional_edges("performance", route_after_performance, {
    "reviewer": "reviewer",
    "finalize": "finalize",
})
builder.add_edge("reviewer", "save")
builder.add_edge("finalize", END)
builder.add_edge("save", END)

graph = builder.compile()
