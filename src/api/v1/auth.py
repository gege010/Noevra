"""Exchange OpenRouter PKCE codes without storing provider credentials."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["provider connections"])


class OpenRouterExchange(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    code_verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")


@router.post("/openrouter/exchange")
async def exchange_openrouter(body: OpenRouterExchange) -> JSONResponse:
    """The browser validates state; this fixed-origin exchange never logs keys."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/auth/keys",
                json={"code": body.code, "code_verifier": body.code_verifier,
                      "code_challenge_method": "S256"},
                headers={"Content-Type": "application/json"},
            )
        if response.status_code != 200:
            raise HTTPException(400, "OpenRouter authorization could not be completed. Connect again.")
        payload = response.json()
        key = payload.get("key") if isinstance(payload, dict) else None
        if not isinstance(key, str) or not key.startswith("sk-or-"):
            raise HTTPException(502, "OpenRouter returned an invalid connection response. Connect again.")
        return JSONResponse({"key": key}, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "OpenRouter could not be reached. Please try connecting again.") from None
