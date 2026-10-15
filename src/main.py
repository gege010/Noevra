"""FastAPI application entry point with modern static web workbench."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.router import api_router
from src.config import get_settings
from src.db.database import init_db
from src.exceptions.handlers import register_exception_handlers

settings = get_settings()

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="ScholarAgent — Autonomous Multi-Agent Research Assistant",
    description="Hierarchical LangGraph multi-agent research workbench with cross-verification on ArXiv, PubMed, and CrossRef",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)

# Mount Static Files
static_dir = Path("src/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/", tags=["root"], include_in_schema=False)
async def serve_index():
    """Serve the ScholarAgent Web Workbench."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "ScholarAgent", "version": "2.0.0", "docs": "/docs"}


@app.get("/api/info", tags=["root"])
async def api_info() -> dict:
    return {
        "name": "ScholarAgent",
        "version": "2.0.0",
        "docs": "/docs",
        "agents": ["planner", "researcher", "verifier", "writer", "reviewer"],
        "databases": ["arxiv", "pubmed", "crossref", "tavily", "web"],
    }
