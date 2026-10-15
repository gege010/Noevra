"""Pydantic response schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    title: str
    url: str | None = None
    doi: str | None = None
    pmid: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_date: Any = None
    journal: str | None = None
    snippet: str | None = None
    source_type: Literal["web", "arxiv", "pubmed", "journal", "encyclopedia", "pdf", "other"] = "web"
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)


class ArxivSource(SourceMetadata):
    arxiv_id: str | None = None
    abstract: str | None = None


class ResearchResponse(BaseModel):
    job_id: str
    status: Literal["queued", "planning", "researching", "verifying", "writing", "reviewing", "done", "failed"]
    stream_url: str
    estimated_duration: str


class ResearchStatus(BaseModel):
    job_id: str
    status: Literal["queued", "planning", "researching", "verifying", "writing", "reviewing", "done", "failed"]
    progress_pct: int = Field(ge=0, le=100)
    current_step: str
    provider: str | None = None
    model: str | None = None
    depth: str | None = None
    trace_url: str | None = None
    error: str | None = None
    step_logs: list[dict[str, Any]] = Field(default_factory=list)


class ReportResponse(BaseModel):
    job_id: str
    query: str | None = None
    provider: str | None = None
    model: str | None = None
    depth: str | None = None
    report_markdown: str
    pdf_base64: str | None = None
    sources: list[Any] = Field(default_factory=list)
    evidence_matrix: list[dict[str, Any]] = Field(default_factory=list)
    step_logs: list[dict[str, Any]] = Field(default_factory=list)
    trace_url: str | None = None
    generated_at: datetime
    tokens_used: int | None = None
    report_content: str | None = None  # alias for report_markdown (API compat)
    langgraph_version: str = "0.2.0"


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    groq: Literal["up", "down"]
    tavily: Literal["up", "down"]
    arxiv: Literal["up", "down"]
    db: Literal["up", "down"]
    active_jobs: int = 0
