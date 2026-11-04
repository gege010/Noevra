"""Exercise HTTP → owned task → persistence → SSE → exports with a fake graph."""

import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.main import app


def test_research_result_is_persisted_and_exportable(tmp_path, monkeypatch):
    import src.api.deps as deps
    import src.db.database as database
    import src.main as main
    import src.services.job_runtime as jobs

    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "async_session_maker", sessions)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(deps, "async_session_maker", sessions)
    monkeypatch.setattr(jobs, "async_session_maker", sessions)
    report = "# Local integration report\n\n## Findings\nA bounded finding [1].\n\n## Limitations\nHuman review is required."
    source = {
        "source_id": "S-01",
        "title": "A recorded study",
        "url": "https://example.org/paper",
        "authors": ["Test Author"],
        "published_date": "2026",
        "source_type": "journal",
        "snippet": "A bounded finding.",
    }

    class FakeGraph:
        async def astream(self, state, config):
            assert state["model"] == "test-model"
            assert state["api_key"] == "private-test-token"
            for node, result in (
                ("planner", {"plan": [], "status": "researching"}),
                ("researcher", {"sources": [source], "status": "verifying"}),
                ("verifier", {"evidence_matrix": [], "status": "writing"}),
                ("writer", {"draft": report, "status": "reviewing"}),
                ("reviewer", {"status": "done"}),
            ):
                yield {node: result}

    with patch("src.agents.supervisor.get_supervisor_graph", return_value=FakeGraph()):
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/research",
                json={
                    "query": "A local flow check",
                    "provider": "groq",
                    "model": "test-model",
                    "api_key": "private-test-token",
                },
            )
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            for _ in range(50):
                status = client.get(f"/api/v1/research/{job_id}").json()
                if status["status"] in ("done", "failed"):
                    break
                time.sleep(0.02)
            assert status["status"] == "done", status
            saved = client.get(f"/api/v1/research/{job_id}/report")
            assert saved.status_code == 200 and saved.json()["report_markdown"] == report
            assert "private-test-token" not in saved.text
            assert any(job["job_id"] == job_id for job in client.get("/api/v1/research").json())
            stream = client.get(f"/api/v1/research/{job_id}/stream")
            assert "event: done" in stream.text
            assert "private-test-token" not in stream.text
            markdown = client.get(f"/api/v1/research/{job_id}/report/download")
            assert markdown.status_code == 200 and markdown.text == report
            bibliography = client.get(f"/api/v1/research/{job_id}/report/bibtex")
            assert bibliography.status_code == 200 and "A recorded study" in bibliography.text
            pdf = client.get(f"/api/v1/research/{job_id}/report/pdf")
            assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
