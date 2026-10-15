"""SQLAlchemy ORM models."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.db.database import Base


class ResearchJob(Base):
    """Tracks an autonomous research job through its lifecycle."""
    __tablename__ = "research_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=True, default="groq")
    model: Mapped[str] = mapped_column(String(100), nullable=True, default="llama-3.3-70b-versatile")
    depth: Mapped[str] = mapped_column(String(20), nullable=True, default="standard")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trace_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_markdown: Mapped[str | None] = mapped_column("report_markdown", Text, nullable=True)
    sources_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    step_logs_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column("error_message", Text, nullable=True)

    @property
    def is_terminal(self) -> bool:
        return self.status in ("done", "failed")
