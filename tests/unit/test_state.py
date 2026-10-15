"""Unit tests for agent state."""
import pytest
from src.agents.state import AgentState, default_state


def test_default_state_factory():
    state = default_state(
        query="Impact of LLMs on software engineering",
        job_id="test-job-123",
        depth="standard",
        language="en",
        include_academic=True,
        include_web=True,
        max_iterations=8,
    )
    assert state["query"] == "Impact of LLMs on software engineering"
    assert state["job_id"] == "test-job-123"
    assert state["status"] == "planning"
    assert state["plan"] == []
    assert state["sources"] == []
    assert state["draft"] == ""
    assert state["review_score"] == 0.0
    assert state["revision_count"] == 0
    assert state["gap_analysis"] is None
    assert state["max_iterations"] == 8
    assert state["current_iteration"] == 0
    assert state["next_node"] is None
    assert state["trace_url"] is None
    assert state["error"] is None


def test_agent_state_keys():
    state = default_state(query="Test", job_id="j1")
    required_keys = {
        "query", "depth", "language", "include_academic", "include_web",
        "max_iterations", "current_iteration", "next_node",
        "plan", "sources", "draft", "review_score", "revision_count",
        "gap_analysis", "status", "trace_url", "error", "job_id",
    }
    assert required_keys.issubset(set(state.keys()))
    # Verify new multi-provider & empirical verification keys
    assert "provider" in state
    assert "model" in state
    assert "evidence_matrix" in state
    assert "step_logs" in state
    assert "contract" in state