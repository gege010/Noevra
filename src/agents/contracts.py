"""Validate model output before it becomes research state or a quality verdict."""

from __future__ import annotations

from datetime import date
import json
import re
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


def json_object(content: str | list) -> dict:
    if isinstance(content, list):
        content = " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        )
    if not isinstance(content, str):
        raise ValueError("Expected textual structured output")
    text = content.strip()
    fence = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    parsed = json.loads(fence.group(1) if fence else text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


class ResearchVector(BaseModel):
    lane: Literal["primary", "independent", "counter"]
    title: str = Field(min_length=1, max_length=300)
    search_query: str = Field(min_length=3, max_length=1500)
    target_engine: Literal["crossref", "arxiv", "pubmed", "web"]
    rationale: str = Field(default="", max_length=2000)


class ResearchContract(BaseModel):
    question: str = Field(min_length=3, max_length=1500)
    as_of: date
    decision_context: str = Field(max_length=3000)
    scope: str = Field(max_length=3000)
    must_resolve: list[str] = Field(max_length=12)
    stop_when: str = Field(max_length=3000)


class ResearchPlan(BaseModel):
    vectors: list[ResearchVector] = Field(min_length=1, max_length=12)
    contract: ResearchContract | None = None


class VerificationOutput(BaseModel):
    evidence_ledger: list[dict] = Field(
        min_length=1,
        max_length=30,
        validation_alias=AliasChoices("evidence_ledger", "evidence_matrix"),
    )
    credibility_overview: dict = Field(default_factory=dict)
    cross_study_contradictions: list[dict | str] = Field(default_factory=list, max_length=30)


class ReviewOutput(BaseModel):
    overall_score: float = Field(ge=0, le=10, allow_inf_nan=False)
    verdict: Literal["ACCEPTED", "REVISE"]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    actionable_gaps: str = ""
    unverified_claims: list[str | dict] = Field(default_factory=list)
    contested_claims: list[str | dict] = Field(default_factory=list)
