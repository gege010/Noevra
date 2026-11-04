"""Tests use disposable storage and never consume real provider credentials."""

import os
import tempfile

import httpx
import pytest

_workspace = tempfile.TemporaryDirectory(prefix="noevra-tests-", ignore_cleanup_errors=True)
os.environ.update(
    APP_ENV="testing",
    NOEVRA_ENV_FILE=os.path.join(_workspace.name, "no-user-env"),
    NOEVRA_DATA_DIR=_workspace.name,
    DATABASE_URL="",
    WORKSPACE_PASSWORD="",
    SESSION_SECRET="",
    LANGSMITH_TRACING="false",
)
for _name in (
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "LANGSMITH_API_KEY",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_CLOUD_PROJECT",
):
    os.environ.pop(_name, None)


@pytest.fixture(autouse=True)
def block_unmocked_provider_network(monkeypatch):
    async def blocked(*_args, **_kwargs):
        raise AssertionError(
            "Tests must mock provider HTTP traffic; live credentials are never used."
        )

    def blocked_sync(*_args, **_kwargs):
        raise AssertionError("Tests must mock provider HTTP traffic")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked_sync)
    # New SDKs may use httpx2 while the application uses httpx.
    try:
        import httpx2
    except ImportError:
        return
    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", blocked)
    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", blocked_sync)
