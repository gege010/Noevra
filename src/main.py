"""FastAPI application entry point with modern static web workbench."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import secrets

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
    from src.db.database import async_session_maker
    from src.repositories.job_repository import JobRepository
    from src.services.job_runtime import runtime
    async with async_session_maker() as db:
        await JobRepository(db).recover_interrupted()
    yield
    await runtime.close()


app = FastAPI(
    title="Noevra — Autonomous Multi-Agent Research Assistant",
    description="Hierarchical LangGraph multi-agent research workbench with cross-verification on ArXiv, PubMed, and CrossRef",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=bool(settings.allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def workspace_boundary(request, call_next):
    public = request.url.path in {"/api/v1/session", "/api/v1/live"}
    if settings.workspace_password and request.url.path.startswith("/api/") and not public and not request.session.get("workspace"):
        return JSONResponse({"detail": "Unlock this workspace to continue."}, status_code=401)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        expected = str(request.base_url).rstrip("/")
        if origin and origin not in {expected, settings.public_url.rstrip("/"), *settings.allowed_origins}:
            return JSONResponse({"detail": "Cross-origin requests are not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# Registered last so the session is available to the workspace boundary.
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or secrets.token_urlsafe(48),
                   session_cookie="noevra_workspace", https_only=settings.is_production,
                   same_site="lax", max_age=86400)

register_exception_handlers(app)
app.include_router(api_router)

# Mount Static Files
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", tags=["root"], include_in_schema=False)
async def serve_index():
    """Serve the Noevra Web Workbench."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "Noevra", "version": "2.0.0", "docs": "/docs"}


@app.get("/api/info", tags=["root"])
async def api_info() -> dict:
    return {
        "name": "Noevra",
        "version": "2.0.0",
        "docs": "/docs",
        "agents": ["planner", "researcher", "verifier", "writer", "reviewer"],
        "databases": ["arxiv", "pubmed", "crossref", "tavily", "web"],
    }
