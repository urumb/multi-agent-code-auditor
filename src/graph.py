# Author: urumb
from langgraph.graph import StateGraph, START, END
from .state import AuditorState
from .agents.manager import ManagerAgent
from .agents.security import SecurityAgent
from .agents.performance import PerformanceAgent
from .agents.reviewer import ReviewerAgent
from .utils.memory import AuditMemory

# Initialize Agents & Memory
manager = ManagerAgent()
security = SecurityAgent()
performance = PerformanceAgent()
reviewer = ReviewerAgent()
memory = AuditMemory()

def manager_node(state: AuditorState):
    return manager.run(state)

def retrieval_node(state: AuditorState):
    print("--- Memory: Retrieving Context ---")
    snippets = state.get("code_snippets", [])
    past_audits = []
    
    # Retrieve context for each snippet (limit to top 1 to avoid context overflow)
    for snippet in snippets[:5]: # Cap at 5 snippets for performance
        results = memory.retrieve_similar(snippet, n_results=1)
        past_audits.extend(results)
    
    # Deduplicate
    unique_audits = list(set(past_audits))
    return {"past_audits": unique_audits}

def security_node(state: AuditorState):
    return security.run(state)

def performance_node(state: AuditorState):
    return performance.run(state)

def reviewer_node(state: AuditorState):
    return reviewer.run(state)

def save_node(state: AuditorState):
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
        
        memory.save_audit(snippets[0], summary_finding, tags=["audit", "v1"])
        
    return {}

# Build Graph
builder = StateGraph(AuditorState)

builder.add_node("manager", manager_node)
builder.add_node("retrieve", retrieval_node)
builder.add_node("security", security_node)
builder.add_node("performance", performance_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("save", save_node)

# Flow
builder.add_edge(START, "manager")
builder.add_edge("manager", "retrieve")
builder.add_edge("retrieve", "security")
builder.add_edge("retrieve", "performance")
builder.add_edge("security", "reviewer")
builder.add_edge("performance", "reviewer")
builder.add_edge("reviewer", "save")
builder.add_edge("save", END)

graph = builder.compile()
