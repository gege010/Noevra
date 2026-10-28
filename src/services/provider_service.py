"""Provider capabilities and live, account-specific model discovery."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit
import re

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from src.config import get_settings

Provider = Literal["groq", "openai", "anthropic", "gemini", "deepseek", "openrouter", "ollama", "custom"]


class ProviderConnection(BaseModel):
    api_key: str | None = Field(default=None, max_length=16384, repr=False)
    base_url: str | None = Field(default=None, max_length=2048)
    auth_type: Literal["api_key", "oauth"] = "api_key"


NAMES = {"groq": "Groq", "openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google Gemini",
         "deepseek": "DeepSeek", "openrouter": "OpenRouter", "ollama": "Ollama", "custom": "Custom endpoint"}
URLS = {"groq": "https://api.groq.com/openai/v1/models", "openai": "https://api.openai.com/v1/models",
        "anthropic": "https://api.anthropic.com/v1/models", "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
        "deepseek": "https://api.deepseek.com/models", "openrouter": "https://openrouter.ai/api/v1/models/user"}
AUTH_DOCS = {"openai": "https://developers.openai.com/siwc/token-sharing-open-source/sign-in",
             "anthropic": "https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use",
             "gemini": "https://ai.google.dev/gemini-api/docs/oauth",
             "openrouter": "https://openrouter.ai/docs/guides/overview/auth/oauth"}


def configured_key(provider: str) -> str:
    return getattr(get_settings(), f"{provider}_api_key", "")


def validate_endpoint(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise HTTPException(422, "Use an HTTP(S) endpoint without credentials, query parameters or fragments.")
    settings = get_settings()
    origin = f"{parts.scheme}://{parts.netloc}".lower()
    if settings.is_production and origin not in [s.lower().rstrip("/") for s in settings.custom_llm_allowed_origins]:
        raise HTTPException(422, "This endpoint origin must be explicitly allowed by the server administrator.")
    if parts.scheme == "http" and parts.hostname not in ("localhost", "127.0.0.1", "::1") and origin not in settings.custom_llm_allowed_origins:
        raise HTTPException(422, "Remote endpoints must use HTTPS unless the server administrator explicitly allows this origin.")
    return value.rstrip("/")


def provider_metadata() -> dict:
    settings = get_settings()
    result = {}
    for key, name in NAMES.items():
        oauth = key in ("openai", "openrouter", "gemini")
        configured = key != "gemini" or bool(settings.google_oauth_client_id and settings.google_oauth_client_secret and settings.google_project_id)
        note = {"openai": "ChatGPT plan access via official dynamic registration on a local 127.0.0.1 callback.",
                "gemini": "Google OAuth requires a registered web client and a billing/quota project on this server.",
                "anthropic": "Claude.ai subscription OAuth is not permitted in third-party apps. Use a Claude API key or a supported cloud provider.",
                "openrouter": "Connect your OpenRouter account with PKCE; usage is billed to your credits."}.get(key, "Use an API key or a local endpoint.")
        result[key] = {"name": name, "models": [], "default_model": "", "requires_key": key not in ("ollama", "custom"),
                       "configured_in_backend": bool(configured_key(key)), "auth_methods": ["api_key"] + (["oauth"] if oauth else []),
                       "oauth": {"supported": oauth, "configured": oauth and configured, "note": note, "docs": AUTH_DOCS.get(key)}}
    return result


def normalize_models(provider: str, payload: dict, auth_type: str) -> list[dict]:
    rows = payload.get("models", []) if provider == "gemini" or (provider == "openai" and auth_type == "oauth") else payload.get("data", [])
    output, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if provider == "gemini" and "generateContent" not in row.get("supportedGenerationMethods", []):
            continue
        if provider == "openai" and auth_type == "oauth" and row.get("visibility") != "list":
            continue
        identifier = row.get("slug") or row.get("id") or row.get("name", "").removeprefix("models/")
        if not identifier or identifier in seen:
            continue
        if provider in ("openai", "groq") and auth_type != "oauth" and re.search(r"embedding|whisper|tts|dall-e|sora|transcrib|image-|moderation|realtime|audio|babbage|davinci", identifier):
            continue
        architecture = row.get("architecture") or {}
        if architecture.get("output_modalities") and "text" not in architecture["output_modalities"]:
            continue
        seen.add(identifier)
        output.append({"id": identifier, "name": row.get("display_name") or row.get("displayName") or row.get("name") or identifier,
                       "context": row.get("context_length") or row.get("inputTokenLimit"), "created": row.get("created")})
    return output


async def discover_models(provider: str, connection: ProviderConnection) -> dict:
    key = connection.api_key or configured_key(provider)
    if connection.auth_type == "oauth" and provider not in ("openai", "gemini", "openrouter"):
        raise HTTPException(422, "OAuth model access is not supported for this provider.")
    if not key and provider not in ("ollama", "custom"):
        raise HTTPException(401, "Connect this provider with OAuth or an API key first.")
    headers, params = {}, {}
    if provider in ("ollama", "custom"):
        url = validate_endpoint(connection.base_url or (get_settings().ollama_base_url if provider == "ollama" else "http://localhost:1234/v1")) + "/models"
    else:
        url = URLS[provider]
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if provider == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        params["limit"] = 1000
    if provider == "gemini":
        if connection.auth_type == "oauth":
            headers["x-goog-user-project"] = get_settings().google_project_id
        else:
            headers = {"x-goog-api-key": key}
        params["pageSize"] = 1000
    models = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            for _ in range(10):
                response = await client.get(url, headers=headers, params=params)
                if response.status_code in (401, 403):
                    raise HTTPException(401, "The provider rejected this connection. Reconnect or check the key and permissions.")
                if response.status_code == 429:
                    raise HTTPException(429, "The provider is rate limiting model discovery. Try again shortly.")
                if response.status_code != 200:
                    raise HTTPException(502, "The provider could not list models. Check the connection and try again.")
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("invalid catalog")
                models.extend(normalize_models(provider, payload, connection.auth_type))
                if provider == "anthropic" and payload.get("has_more") and payload.get("last_id"):
                    params["after_id"] = payload["last_id"]
                elif provider == "gemini" and payload.get("nextPageToken"):
                    params["pageToken"] = payload["nextPageToken"]
                else:
                    break
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(502, "Model discovery could not reach the provider. No cached model list was substituted.") from None
    unique = list({m["id"]: m for m in models}.values())
    return {"provider": provider, "models": unique, "source": "live", "checked_at": datetime.now(timezone.utc).isoformat(),
            "note": "Listed by the provider for this connection. Runtime quotas and model capabilities may still limit a request."}
