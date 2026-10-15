"""LangGraph supervisor graph — orchestrates the 5-agent research pipeline."""
from __future__ import annotations
import structlog
from langgraph.graph import StateGraph, END
from src.agents.state import AgentState
from src.agents.planner import planner_node
from src.agents.researcher import researcher_node
from src.agents.verifier import verifier_node
from src.agents.writer import writer_node
from src.agents.reviewer import reviewer_node

logger = structlog.get_logger()


def build_supervisor_graph():
    """Build and compile the 5-node LangGraph research supervisor."""
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("planner")

    # Workflow edges:
    # 1. Planner formulates multi-source vectors
    graph.add_edge("planner", "researcher")
    # 2. Researcher executes searches across ArXiv, CrossRef, PubMed, Web
    graph.add_edge("researcher", "verifier")
    # 3. Verifier audits credibility and creates Evidence Matrix
    graph.add_edge("verifier", "writer")
    # 4. Writer synthesizes publication-grade academic monograph
    graph.add_edge("writer", "reviewer")

    # 5. Reviewer decides whether to finalize or trigger targeted revision
    def review_router(state: AgentState) -> str:
        status = state.get("status", "done")
        if status == "done":
            return END
        return "researcher"

    graph.add_conditional_edges("reviewer", review_router, {"researcher": "researcher", END: END})

    return graph.compile()


_supervisor_graph = None


def get_supervisor_graph():
    global _supervisor_graph
    if _supervisor_graph is None:
        _supervisor_graph = build_supervisor_graph()
    return _supervisor_graph
