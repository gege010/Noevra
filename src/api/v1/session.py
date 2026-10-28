"""Private, single-workspace deployment gate. Provider OAuth is separate."""
from __future__ import annotations
import hmac
import time
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from src.config import get_settings

router = APIRouter(prefix="/session", tags=["workspace access"])
_attempts: dict[str, deque] = defaultdict(deque)


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=1024, repr=False)


@router.get("")
async def session_status(request: Request):
    enabled = bool(get_settings().workspace_password)
    return {"required": enabled, "authenticated": not enabled or bool(request.session.get("workspace"))}


@router.post("")
async def login(body: Login, request: Request):
    settings = get_settings()
    if not settings.workspace_password:
        return {"authenticated": True}
    peer, now = request.client.host if request.client else "unknown", time.monotonic()
    if len(_attempts) > 10000:
        _attempts.clear()
    attempts = _attempts[peer]
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= 5:
        raise HTTPException(429, "Too many login attempts. Try again in one minute.")
    attempts.append(now)
    if not hmac.compare_digest(body.password.encode(), settings.workspace_password.encode()):
        raise HTTPException(401, "The workspace password is incorrect.")
    request.session.clear()
    request.session["workspace"] = True
    attempts.clear()
    return {"authenticated": True}


@router.delete("")
async def logout(request: Request):
    request.session.clear()
    return {"authenticated": False}
