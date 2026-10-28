"""Health check endpoints."""
from __future__ import annotations
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.api.deps import get_db
from src.schemas.responses import HealthResponse
from src.config import get_settings
from src.db.models import ResearchJob

router = APIRouter(tags=["health"])


@router.get("/live", summary="Process liveness without provider calls")
async def live():
    return {"status": "ok"}

async def _check_groq() -> bool:
    settings = get_settings()
    if not settings.groq_api_key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                timeout=5.0,
            )
            return resp.status_code == 200
    except Exception:
        return False

async def _check_tavily() -> bool:
    settings = get_settings()
    if not settings.tavily_api_key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.tavily.com/usage",
                headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
                timeout=5.0,
            )
            return resp.status_code == 200
    except Exception:
        return False

async def _check_arxiv() -> bool:
    """Check if ArXiv is reachable (public endpoint)."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "http://export.arxiv.org/api/query?search_query=all:test&max_results=1",
                timeout=5.0,
            )
            return resp.status_code == 200
    except Exception:
        return False

@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    import asyncio
    groq_up, tavily_up, arxiv_up = await asyncio.gather(_check_groq(), _check_tavily(), _check_arxiv())
    db_up = True
    try:
        result = await db.execute(
            select(func.count(ResearchJob.id)).where(
                ResearchJob.status.in_(["planning", "researching", "writing", "reviewing"])
            )
        )
        active_jobs = result.scalar() or 0
    except Exception:
        active_jobs = 0
        db_up = False
    if groq_up and tavily_up and db_up:
        overall = "healthy"
    elif db_up:
        overall = "degraded"
    else:
        overall = "unhealthy"
    return HealthResponse(
        status=overall,
        groq="up" if groq_up else "down",
        tavily="up" if tavily_up else "down",
        arxiv="up" if arxiv_up else "down",
        db="up" if db_up else "down",
        active_jobs=active_jobs,
    )

@router.get("/models", summary="Model discovery instructions")
async def list_models() -> dict:
    return {"models": [], "discovery_url": "/api/v1/providers/{provider}/models", "method": "POST", "note": "Use a provider connection to discover live model availability."}
