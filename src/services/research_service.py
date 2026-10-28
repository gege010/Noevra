"""Research orchestration service with real-time event streaming."""
from __future__ import annotations
import asyncio
from typing import AsyncGenerator, Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.state import default_state
from src.agents.supervisor import get_supervisor_graph
from src.repositories.job_repository import JobRepository
from src.services.report_service import ReportService
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# In-memory pub/sub queues for live SSE streaming to web clients
_job_event_queues: dict[str, list[asyncio.Queue]] = {}


def register_listener(job_id: str) -> asyncio.Queue:
    """Register an SSE listener queue for a specific job."""
    q: asyncio.Queue = asyncio.Queue(maxsize=128)
    if job_id not in _job_event_queues:
        _job_event_queues[job_id] = []
    _job_event_queues[job_id].append(q)
    return q


def unregister_listener(job_id: str, q: asyncio.Queue) -> None:
    """Clean up a listener queue."""
    if job_id in _job_event_queues:
        if q in _job_event_queues[job_id]:
            _job_event_queues[job_id].remove(q)
        if not _job_event_queues[job_id]:
            del _job_event_queues[job_id]


async def broadcast_event(job_id: str, event: dict[str, Any]) -> None:
    """Broadcast an execution event to all connected web clients."""
    queues = _job_event_queues.get(job_id, [])
    for q in queues:
        try:
            if q.full():
                q.get_nowait()
            q.put_nowait(event)
        except Exception:
            pass


class ResearchService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = JobRepository(db)
        self._report_service = ReportService()

    async def create_job(self, **kwargs) -> None:
        await self._repo.create(**kwargs)

    async def get_job(self, job_id: str):
        return await self._repo.get(job_id)

    async def list_recent(self, limit: int = 25):
        return await self._repo.list_recent(limit=limit)

    async def cancel_job(self, job_id: str) -> None:
        from src.services.job_runtime import runtime
        runtime.cancel(job_id)
        await self._repo.update_status(job_id, "failed")
        await self._repo.update_error(job_id, "Cancelled by user")
        await broadcast_event(job_id, {"type": "error", "message": "Cancelled by user"})

    async def run_research(
        self,
        job_id: str,
        provider: str = "groq",
        model: str = "llama-3.3-70b-versatile",
        api_key: str | None = None,
        base_url: str | None = None,
        depth: str = "standard",
        domain_focus: str = "general",
        citation_style: str = "ieee",
        language: str = "en",
        max_iterations: int = 10,
        include_academic: bool = True,
        include_web: bool = True,
        sources_limit: int = 20,
        auth_type: str = "api_key",
    ) -> None:
        """Execute the multi-agent research pipeline with real-time telemetry."""
        job = await self._repo.get(job_id)
        if not job:
            logger.error("job_not_found", job_id=job_id)
            return

        logger.info("research_started", job_id=job_id, query=job.query, provider=provider, model=model)
        await broadcast_event(job_id, {
            "type": "start",
            "job_id": job_id,
            "query": job.query,
            "provider": provider,
            "model": model,
            "depth": depth,
        })

        try:
            await self._repo.update_status(job_id, "planning")
            await broadcast_event(job_id, {"type": "status", "status": "planning", "pct": 10, "step": "Formulating scientific search vectors"})

            state = default_state(
                query=job.query,
                job_id=job_id,
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                depth=depth,
                domain_focus=domain_focus,
                citation_style=citation_style,
                language=language,
                include_academic=include_academic,
                include_web=include_web,
                max_iterations=max_iterations,
                sources_limit=sources_limit,
                auth_type=auth_type,
            )

            graph = get_supervisor_graph()

            # Execute graph nodes with progress broadcasting
            async def run_graph():
                current_state = state
                async for output in graph.astream(current_state, config={"recursion_limit": max_iterations * 4 + 5}):
                    for node_name, node_output in output.items():
                        logger.info("node_executed", node=node_name, job_id=job_id)
                        progress_map = {
                            "planner": (25, "Research vectors created", "researching"),
                            "researcher": (50, "Academic & web evidence gathered", "verifying"),
                            "verifier": (70, "Empirical data & citations verified", "writing"),
                            "writer": (90, "Scholarly monograph synthesized", "reviewing"),
                            "reviewer": (95, "Peer review critique completed", "reviewing"),
                        }
                        pct, desc, next_status = progress_map.get(node_name, (50, f"Completed {node_name}", "working"))
                        await self._repo.update_status(job_id, ("researching" if node_output.get("status") == "researching" else next_status))
                        
                        # Extract latest step log from output
                        logs = node_output.get("step_logs", [])
                        latest_log = logs[-1] if logs else {}
                        
                        await broadcast_event(job_id, {
                            "type": "node_complete",
                            "node": node_name,
                            "pct": pct,
                            "step": desc,
                            "log": latest_log,
                            "sources_count": len(node_output.get("sources", [])),
                        })
                        current_state.update(node_output)
                return current_state

            from langsmith import tracing_context
            # Tab-supplied secrets must never be serialized into graph traces.
            with tracing_context(enabled=settings.langsmith_tracing and not bool(api_key)):
                final_state = await asyncio.wait_for(run_graph(), timeout=settings.research_timeout_seconds)

            draft = final_state.get("draft", "")
            raw_sources = final_state.get("sources", [])
            evidence_matrix = final_state.get("evidence_matrix", [])
            step_logs = final_state.get("step_logs", [])

            sources_json = []
            for s in raw_sources:
                if isinstance(s, dict):
                    sources_json.append(s)

            trace_url = final_state.get("trace_url")

            await self._repo.update_result(
                job_id=job_id,
                report_markdown=draft,
                sources_json=sources_json,
                evidence_json=evidence_matrix,
                step_logs_json=step_logs,
                trace_url=trace_url,
            )

            await broadcast_event(job_id, {
                "type": "done",
                "job_id": job_id,
                "status": "done",
                "pct": 100,
                "step": "Academic Research Monograph Ready",
                "draft": draft,
                "sources": sources_json,
                "evidence_matrix": evidence_matrix,
                "step_logs": step_logs,
            })

            logger.info("research_completed_successfully", job_id=job_id, words=len(draft.split()), sources=len(sources_json))
        except Exception as exc:
            logger.error("research_pipeline_failed", job_id=job_id, error_type=type(exc).__name__)
            message = "Research exceeded its time budget. Try a smaller scope." if isinstance(exc, asyncio.TimeoutError) else "Research could not complete. Check the provider connection, model permissions, and source availability before retrying."
            await self._repo.update_error(job_id, message)
            await broadcast_event(job_id, {
                "type": "error",
                "job_id": job_id,
                "status": "failed",
                "error": message,
            })
