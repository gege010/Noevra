"""Exchange OpenRouter PKCE codes without storing provider credentials."""
from __future__ import annotations

import httpx
import time
from urllib.parse import urlsplit
import jwt
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal
from src.config import get_settings

router = APIRouter(prefix="/auth", tags=["provider connections"])


class OAuthExchange(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    code_verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")
    redirect_uri: str = Field(max_length=2048)
    client_id: str = Field(default="", max_length=256)
    nonce: str = Field(default="", max_length=256)


def validate_redirect(uri: str, provider: str):
    parts = urlsplit(uri)
    local = parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise HTTPException(422, "Invalid OAuth callback URI.")
    if provider == "openai" and not (local and parts.hostname == "127.0.0.1"):
        raise HTTPException(422, "ChatGPT plan authorization requires a local 127.0.0.1 callback. Use an API key on a hosted deployment.")
    settings = get_settings()
    if not local and uri.rstrip("/") != settings.public_url.rstrip("/"):
        raise HTTPException(422, "The callback must match APP_PUBLIC_URL configured on this server.")


@router.get("/capabilities")
async def oauth_capabilities():
    settings = get_settings()
    return {"openai": {"client_id": "dynamic_agent_client", "local_only": True, "configured": True},
            "gemini": {"client_id": settings.google_oauth_client_id,
                       "configured": bool(settings.google_oauth_client_id and settings.google_oauth_client_secret and settings.google_project_id)},
            "openrouter": {"configured": True}}


async def validate_openai_identity(tokens: dict, client_id: str, nonce: str, client: httpx.AsyncClient):
    if not nonce:
        raise ValueError("missing nonce")
    discovery = await client.get("https://auth.openai.com/.well-known/openid-configuration")
    discovery.raise_for_status()
    metadata = discovery.json()
    jwks_url = metadata.get("jwks_uri", "")
    parsed = urlsplit(jwks_url)
    if parsed.scheme != "https" or parsed.hostname != "auth.openai.com" or parsed.username or parsed.password:
        raise ValueError("invalid issuer keys")
    response = await client.get(jwks_url)
    response.raise_for_status()
    header = jwt.get_unverified_header(tokens["id_token"])
    if header.get("alg") not in ("RS256", "ES256"):
        raise ValueError("invalid signing algorithm")
    matching = [key for key in response.json()["keys"] if key.get("kid") == header.get("kid")]
    if len(matching) != 1:
        raise ValueError("invalid signing key")
    claims = jwt.decode(tokens["id_token"], jwt.PyJWK.from_dict(matching[0]).key,
                        algorithms=[header["alg"]], audience=client_id, issuer=metadata["issuer"],
                        options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce"]})
    if metadata["issuer"].rstrip("/") != "https://auth.openai.com" or claims["nonce"] != nonce:
        raise ValueError("identity validation failed")
    if "chatgpt.tokens.use.direct" not in str(tokens.get("scope", "")).split():
        raise ValueError("ChatGPT plan access was not granted")


@router.post("/oauth/{provider}/exchange")
async def exchange_oauth(provider: Literal["openai", "gemini"], body: OAuthExchange):
    validate_redirect(body.redirect_uri, provider)
    settings = get_settings()
    if provider == "openai":
        if not body.client_id or body.client_id == "dynamic_agent_client":
            raise HTTPException(422, "The ChatGPT callback must provide the issued client ID.")
        endpoint = "https://auth.openai.com/api/accounts/oauth/token"
        fields = {"client_id": body.client_id, "resource": "https://api.openai.com/v1"}
    else:
        if not (settings.google_oauth_client_id and settings.google_oauth_client_secret and settings.google_project_id):
            raise HTTPException(409, "Google OAuth needs GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_CLOUD_PROJECT on this server.")
        endpoint = "https://oauth2.googleapis.com/token"
        fields = {"client_id": settings.google_oauth_client_id, "client_secret": settings.google_oauth_client_secret}
    fields.update(grant_type="authorization_code", code=body.code, code_verifier=body.code_verifier, redirect_uri=body.redirect_uri)
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(endpoint, data=fields)
            if response.status_code != 200:
                raise HTTPException(400, "The provider could not complete sign-in. Start a new authorization attempt.")
            tokens = response.json()
            if not isinstance(tokens.get("access_token"), str) or not tokens["access_token"]:
                raise ValueError("missing token")
            if provider == "openai":
                await validate_openai_identity(tokens, body.client_id, body.nonce, client)
        return JSONResponse({"key": tokens["access_token"], "expires_at": time.time() + min(int(tokens.get("expires_in", 3600)), 86400),
                             "auth_type": "oauth", "client_id": body.client_id}, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(502, "Provider sign-in could not be validated. Reconnect and grant model access.") from None


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
