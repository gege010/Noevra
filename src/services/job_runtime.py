"""Bounded, cancellable single-worker runtime; secrets are never persisted."""
from __future__ import annotations
import asyncio
from src.config import get_settings
from src.db.database import async_session_maker
from src.repositories.job_repository import JobRepository


class JobRuntime:
    def __init__(self):
        self.tasks: dict[str, asyncio.Task] = {}
        self.admission = asyncio.Lock()
        self.slots = asyncio.Semaphore(get_settings().max_concurrent_jobs)

    @property
    def full(self):
        return len(self.tasks) >= get_settings().max_queued_jobs

    def start(self, job_id: str, **params):
        task = asyncio.create_task(self._run(job_id, params), name=f"research-{job_id}")
        self.tasks[job_id] = task
        task.add_done_callback(lambda _: self.tasks.pop(job_id, None))

    def cancel(self, job_id: str):
        task = self.tasks.get(job_id)
        if task:
            task.cancel()

    async def _run(self, job_id: str, params: dict):
        from src.services.research_service import ResearchService, broadcast_event
        try:
            async with self.slots:
                async with async_session_maker() as db:
                    service = ResearchService(db)
                    job = await service.get_job(job_id)
                    if not job or job.is_terminal:
                        return
                    await service.run_research(job_id, **params)
        except asyncio.CancelledError:
            async with async_session_maker() as db:
                await JobRepository(db).update_error(job_id, "Research interrupted or cancelled. Start a new investigation to retry.")
            await broadcast_event(job_id, {"type": "error", "error": "Research cancelled or interrupted."})
        except Exception:
            async with async_session_maker() as db:
                await JobRepository(db).update_error(job_id, "Research could not start. Check your connection and try again.")
            await broadcast_event(job_id, {"type": "error", "error": "Research could not start. Check your connection and try again."})

    async def close(self):
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


runtime = JobRuntime()
