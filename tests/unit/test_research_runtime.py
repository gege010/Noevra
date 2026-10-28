"""Queue cancellation, fair retrieval, and durable completion invariants."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.agents.researcher import researcher_node
from src.agents.state import default_state
from src.db.database import Base
from src.repositories.job_repository import JobRepository
from src.services.job_runtime import JobRuntime
from src.services.report_service import ReportService


@pytest.mark.asyncio
async def test_cancelled_queued_job_never_consumes_a_model_call():
    started, release = asyncio.Event(), asyncio.Event()
    async def research(job_id, **_):
        assert job_id == "first"
        started.set()
        await release.wait()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    with patch("src.services.job_runtime.async_session_maker", factory), patch("src.services.research_service.ResearchService.get_job", new=AsyncMock(return_value=SimpleNamespace(is_terminal=False))), patch("src.services.research_service.ResearchService.run_research", new=AsyncMock(side_effect=research)) as run, patch("src.services.job_runtime.JobRepository.update_error", new=AsyncMock()) as failed:
        runtime = JobRuntime()
        runtime.slots = asyncio.Semaphore(1)
        runtime.start("first")
        await asyncio.wait_for(started.wait(), 1)
        runtime.start("queued")
        await asyncio.sleep(0)
        queued = runtime.tasks["queued"]
        runtime.cancel("queued")
        await queued
        assert failed.await_args.args[0] == "queued"
        assert run.await_count == 1
        release.set()
        await runtime.close()


@pytest.mark.asyncio
async def test_source_budget_does_not_starve_counter_evidence():
    state = default_state("A scientific question", "test", sources_limit=5)
    state["plan"] = [{"search_query":lane, "lane":lane, "target_engine":"crossref"} for lane in ("primary", "independent", "counter")]
    async def search(query, **_):
        return [{"url":f"https://example.org/{query}/{i}", "title":f"{query} {i}", "source_type":"crossref", "snippet":"Evidence"} for i in range(6)]
    with patch("src.agents.researcher.crossref_search", new=AsyncMock(side_effect=search)):
        result = await researcher_node(state)
    assert len(result["sources"]) == 5
    assert {source["lane"] for source in result["sources"]} == {"primary", "independent", "counter"}
    assert len({source["source_id"] for source in result["sources"]}) == 5


@pytest.mark.asyncio
async def test_no_sources_fails_instead_of_fabricating_report():
    state = default_state("A scientific question", "test")
    state["plan"] = [{"search_query":"query", "target_engine":"crossref"}]
    with patch("src.agents.researcher.crossref_search", new=AsyncMock(return_value=[])):
        with pytest.raises(RuntimeError, match="No usable sources"):
            await researcher_node(state)


@pytest.mark.asyncio
async def test_cancelled_job_cannot_be_overwritten_with_success():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        repo = JobRepository(db)
        await repo.create("cancelled", "A scientific question")
        await repo.update_error("cancelled", "Cancelled")
        await repo.update_result("cancelled", "Late report", [])
        job = await repo.get("cancelled")
        assert job.status == "failed"
        assert not job.report_markdown
    await engine.dispose()


def test_unicode_pdf_preserves_academic_characters():
    from io import BytesIO
    from pypdf import PdfReader
    pdf = ReportService().markdown_to_pdf("# Étude — Research\n\n## Résumé\nEvidence for α and β with ≥ 5 trials.\n\nTemuan penelitian.")
    assert bytes(pdf).startswith(b"%PDF-")
    text = " ".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "α" in text and "β" in text and "Étude" in text
