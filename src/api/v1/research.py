"""Research job endpoints with real-time SSE streaming and multi-provider selection."""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, PlainTextResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.schemas.requests import ResearchRequest
from src.schemas.responses import ResearchResponse, ResearchStatus, ReportResponse
from src.services.research_service import ResearchService, register_listener, unregister_listener
from src.repositories.job_repository import JobRepository
from src.agents.llm_factory import get_available_providers

router = APIRouter(prefix="/research", tags=["research"])

REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/providers", summary="Get all available LLM providers and models")
async def list_providers() -> dict:
    """Return list of supported providers, models, context sizes, and configuration status."""
    return get_available_providers()


@router.post("", response_model=ResearchResponse, summary="Start research job")
async def start_research(
    request: ResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchResponse:
    from src.services.job_runtime import runtime
    job_id = str(uuid.uuid4())
    service = ResearchService(db)
    async with runtime.admission:
        if runtime.full:
            raise HTTPException(429, "The research queue is full. Wait for a running job to finish.")
        await service.create_job(
            job_id=job_id,
            query=request.query,
            provider=request.provider,
            model=request.model,
            depth=request.depth,
            sources_limit=request.sources_limit,
            include_academic=request.include_academic,
            include_web=request.include_web,
            output_format=request.output_format,
            language=request.language,
            research_settings=request.model_dump(exclude={"api_key", "base_url"}),
        )
        runtime.start(
            job_id,
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            auth_type=request.auth_type,
            base_url=request.base_url,
            depth=request.depth,
            domain_focus=request.domain_focus,
            citation_style=request.citation_style,
            language=request.language,
            max_iterations=request.max_iterations,
            include_academic=request.include_academic,
            include_web=request.include_web,
            sources_limit=request.sources_limit,
        )
    return ResearchResponse(
        job_id=job_id,
        status="queued",
        stream_url=f"/api/v1/research/{job_id}/stream",
        estimated_duration="~1-3 minutes",
    )


@router.get("/{job_id}/stream", summary="Real-time Server-Sent Events stream of agent execution")
async def stream_job_telemetry(job_id: str, db: AsyncSession = Depends(get_db)):
    """Stream live agent thoughts, vector formulation, citations, and status via SSE."""
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    async def event_generator() -> AsyncGenerator[dict, None]:
        q = register_listener(job_id)
        try:
            # Subscribe before refreshing the snapshot to close the completion race.
            job = await service.get_job(job_id)
            # If job already completed, yield completed state immediately
            if job.status == "done":
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "type": "done",
                        "job_id": job.id,
                        "status": "done",
                        "pct": 100,
                        "step": "Academic Research Monograph Ready",
                        "draft": job.report_markdown,
                        "sources": job.sources_json or [],
                        "evidence_matrix": job.evidence_json or [],
                        "step_logs": job.step_logs_json or [],
                    })
                }
                return

            if job.status == "failed":
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "error": job.error or "Unknown failure"})
                }
                return

            # Otherwise, stream live events from queue
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=10.0)
                    yield {
                        "event": event.get("type", "update"),
                        "data": json.dumps(event),
                    }
                    if event.get("type") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    latest = await service.get_job(job_id)
                    if latest and latest.status in ("done", "failed"):
                        yield {"event": "done" if latest.status == "done" else "error", "data": json.dumps({"type": "done" if latest.status == "done" else "error", "job_id": job_id, "error": latest.error})}
                        break
                    # Keep-alive heartbeat
                    yield {"event": "ping", "data": json.dumps({"type": "ping"})}
        finally:
            unregister_listener(job_id, q)

    return EventSourceResponse(event_generator())


@router.get("/{job_id}", response_model=ResearchStatus, summary="Get job status")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)) -> ResearchStatus:
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    status_map = {
        "queued": (5, "Waiting in queue"),
        "planning": (20, "Formulating scientific search vectors"),
        "researching": (50, "Retrieving academic papers & empirical data"),
        "verifying": (70, "Fact-checking & cross-verifying evidence"),
        "writing": (85, "Synthesizing publication-grade academic monograph"),
        "reviewing": (95, "Peer review referee critique"),
        "done": (100, "Research completed"),
        "failed": (100, f"Failed: {job.error or 'Unknown error'}"),
    }
    progress, step = status_map.get(job.status, (0, "Unknown"))
    return ResearchStatus(
        job_id=job.id,
        status=job.status,
        progress_pct=progress,
        current_step=step,
        provider=job.provider,
        model=job.model,
        depth=job.depth,
        trace_url=job.trace_url,
        error=job.error,
        step_logs=job.step_logs_json or [],
    )


@router.get("/{job_id}/report", response_model=ReportResponse, summary="Get full report")
async def get_report(job_id: str, db: AsyncSession = Depends(get_db)) -> ReportResponse:
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report not ready yet")

    return ReportResponse(
        job_id=job.id,
        query=job.query,
        provider=job.provider,
        model=job.model,
        depth=job.depth,
        report_markdown=job.report_markdown or "",
        sources=job.sources_json or [],
        evidence_matrix=job.evidence_json or [],
        step_logs=job.step_logs_json or [],
        trace_url=job.trace_url,
        generated_at=job.completed_at or datetime.utcnow(),
    )


@router.get("/{job_id}/report/bibtex", summary="Export citations as BibTeX")
async def export_bibtex(job_id: str, db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    """Generate BibTeX citation records for all gathered academic sources."""
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    sources = job.sources_json or []
    bibtex_entries = []
    for idx, s in enumerate(sources):
        key = f"ref_{idx + 1}"
        title = s.get("title", "Untitled")
        authors = " and ".join(s.get("authors", [])) or "Anonymous"
        year = s.get("published_date", "2024")[:4]
        doi = s.get("doi", "")
        journal = s.get("journal", "")
        url = s.get("url", "")
        
        entry = [
            f"@article{{{key},",
            f"  title = {{{{{title}}}}},",
            f"  author = {{{authors}}},",
            f"  year = {{{year}}},",
        ]
        if journal:
            entry.append(f"  journal = {{{journal}}},")
        if doi:
            entry.append(f"  doi = {{{doi}}},")
        if url:
            entry.append(f"  url = {{{url}}},")
        entry.append("}\n")
        bibtex_entries.append("\n".join(entry))

    return PlainTextResponse(
        content="\n".join(bibtex_entries) if bibtex_entries else "% No bibliographic records found.",
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f'attachment; filename="references_{job_id[:8]}.bib"'}
    )


@router.get("/{job_id}/report/download", summary="Download report as Markdown file")
async def download_markdown(job_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report not ready yet")

    markdown = job.report_markdown or ""
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in job.query)[:50]
    filename = f"{job_id[:8]}_{safe_title}.md"
    filepath = REPORTS_DIR / filename
    filepath.write_text(markdown, encoding="utf-8")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="text/markdown",
    )


@router.get("/{job_id}/report/pdf", summary="Download report as PDF file")
async def download_pdf(job_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report not ready yet")

    markdown = job.report_markdown or ""
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in job.query)[:50]
    filename = f"{job_id[:8]}_{safe_title}.pdf"
    filepath = REPORTS_DIR / filename

    try:
        from src.services.report_service import ReportService
        report_service = ReportService()
        pdf_bytes = await asyncio.to_thread(report_service.markdown_to_pdf, markdown)
        await asyncio.to_thread(filepath.write_bytes, pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF could not be generated. Download Markdown and try again.",
        )

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/pdf",
    )


@router.delete("/{job_id}", summary="Cancel job")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = ResearchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.is_terminal:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job already finished")
    await service.cancel_job(job_id)
    return {"message": "Job cancelled"}


@router.get("", summary="List all jobs")
async def list_jobs(
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    repo = JobRepository(db)
    jobs = await repo.list_recent(limit=limit)
    return [
        {
            "job_id": j.id,
            "query": j.query,
            "provider": j.provider,
            "model": j.model,
            "depth": j.depth,
            "status": j.status,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "sources_count": len(j.sources_json or []),
            "has_report": bool(j.report_markdown),
            "trace_url": j.trace_url,
            "error": j.error,
        }
        for j in jobs
    ]
