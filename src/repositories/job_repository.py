"""Job repository for database operations."""
from __future__ import annotations
from datetime import datetime
from typing import Sequence, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import ResearchJob


class JobRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(
        self,
        job_id: str,
        query: str,
        provider: str = "groq",
        model: str = "llama-3.3-70b-versatile",
        depth: str = "standard",
        sources_limit: int = 20,
        include_academic: bool = True,
        include_web: bool = True,
        output_format: str = "both",
        language: str = "en",
        research_settings: dict | None = None,
    ) -> ResearchJob:
        job = ResearchJob(
            id=job_id,
            query=query,
            provider=provider,
            model=model,
            depth=depth,
            status="queued",
            settings_json=research_settings,
        )
        self._db.add(job)
        await self._db.commit()
        await self._db.refresh(job)
        return job

    async def get(self, job_id: str) -> ResearchJob | None:
        result = await self._db.execute(select(ResearchJob).where(ResearchJob.id == job_id).execution_options(populate_existing=True))
        return result.scalar_one_or_none()

    async def update_status(self, job_id: str, status: str) -> None:
        await self._db.execute(update(ResearchJob).where(ResearchJob.id == job_id).values(status=status))
        await self._db.commit()

    async def update_result(
        self,
        job_id: str,
        report_markdown: str,
        sources_json: list[dict],
        evidence_json: list[dict] | None = None,
        step_logs_json: list[dict] | None = None,
        trace_url: str | None = None,
    ) -> None:
        values: dict[str, Any] = {
            "status": "done",
            "report_markdown": report_markdown,
            "sources_json": sources_json,
            "completed_at": datetime.utcnow(),
        }
        if evidence_json is not None:
            values["evidence_json"] = evidence_json
        if step_logs_json is not None:
            values["step_logs_json"] = step_logs_json
        if trace_url is not None:
            values["trace_url"] = trace_url

        await self._db.execute(
            update(ResearchJob).where(ResearchJob.id == job_id, ResearchJob.status != "failed").values(**values)
        )
        await self._db.commit()

    async def update_error(self, job_id: str, error_message: str) -> None:
        await self._db.execute(
            update(ResearchJob).where(ResearchJob.id == job_id).values(status="failed", error=error_message)
        )
        await self._db.commit()

    async def list_recent(self, limit: int = 25) -> Sequence[ResearchJob]:
        result = await self._db.execute(
            select(ResearchJob).order_by(ResearchJob.created_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def recover_interrupted(self):
        await self._db.execute(update(ResearchJob).where(ResearchJob.status.not_in(["done", "failed"])).values(
            status="failed", error="The server restarted before this research completed. Reconnect your provider and start a new investigation."))
        await self._db.commit()
