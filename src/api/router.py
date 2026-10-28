"""FastAPI router aggregator."""
from __future__ import annotations
from fastapi import APIRouter
from src.api.v1 import research, health, auth, providers, session

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(research.router)
api_router.include_router(auth.router)
api_router.include_router(providers.router)
api_router.include_router(session.router)
