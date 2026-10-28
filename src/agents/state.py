"""LangGraph agent state definitions for deep academic research."""
from __future__ import annotations
import operator
from typing import Annotated, Literal, TypedDict, Any


class AgentState(TypedDict):
    """Shared state across all agent nodes in the research pipeline."""

    # Core inputs & Model Configuration
    query: str
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    depth: Literal["quick", "standard", "deep"]
    domain_focus: Literal["general", "cs_ai", "biomedical", "economics", "physics", "policy"]
    citation_style: Literal["ieee", "apa", "nature", "harvard"]
    language: Literal["en", "id"]
    include_academic: bool
    include_web: bool
    max_iterations: int

    sources_limit: int
    unverified_claims: list[dict[str, Any]]
    contested_claims: list[dict[str, Any]]

    # Research Contract & Investigation state (from Research Machine philosophy)
    contract: dict[str, Any]  # bounded contract: question, as_of, scope, must_resolve, stop_when
    plan: list[dict[str, Any]]  # lane-based search vectors (primary, independent, counter-evidence)
    sources: list[dict[str, Any]]  # immutable raw sources with source_id (S-01, S-02), exact passages
    evidence_matrix: list[dict[str, Any]]  # evidence ledger: claim_id, claim, status, evidence passages, open_questions
    verification_report: dict[str, Any]  # fact-checking verdicts & credibility scoring
    draft: str  # publication-grade academic monograph
    review_score: float
    review_critique: dict[str, Any]
    revision_count: int
    gap_analysis: str | None
    current_iteration: int
    next_node: str | None

    # Real-time event log for UI streaming
    step_logs: list[dict[str, Any]]

    # Metadata
    status: Literal[
        "planning", "researching", "verifying", "writing", "reviewing", "done", "failed"
    ]
    trace_url: str | None
    error: str | None
    job_id: str | None


def default_state(
    query: str,
    job_id: str,
    provider: str = "groq",
    model: str = "llama-3.3-70b-versatile",
    api_key: str | None = None,
    base_url: str | None = None,
    depth: str = "standard",
    domain_focus: str = "general",
    citation_style: str = "ieee",
    language: str = "en",
    include_academic: bool = True,
    include_web: bool = True,
    max_iterations: int = 10,
    sources_limit: int = 20,
) -> AgentState:
    """Factory for initial agent state."""
    return AgentState(
        query=query,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        depth=depth,  # type: ignore[arg-type]
        domain_focus=domain_focus,  # type: ignore[arg-type]
        citation_style=citation_style,  # type: ignore[arg-type]
        language=language,  # type: ignore[arg-type]
        include_academic=include_academic,
        include_web=include_web,
        max_iterations=max_iterations,
        sources_limit=sources_limit,
        unverified_claims=[],
        contested_claims=[],
        contract={},
        plan=[],
        sources=[],
        evidence_matrix=[],
        verification_report={},
        draft="",
        review_score=0.0,
        review_critique={},
        revision_count=0,
        gap_analysis=None,
        current_iteration=0,
        next_node=None,
        step_logs=[],
        status="planning",
        trace_url=None,
        error=None,
        job_id=job_id,
    )