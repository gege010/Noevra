from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def exchange(response=None, error=None):
    transport = MagicMock()
    transport.post = AsyncMock(return_value=response, side_effect=error)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=transport)
    context.__aexit__ = AsyncMock(return_value=False)
    return context, transport


def test_pkce_exchange_returns_non_cached_key_and_fixed_upstream():
    response = MagicMock(status_code=200)
    response.json.return_value = {"key": "sk-or-test-only"}
    context, transport = exchange(response)
    with patch("src.api.v1.auth.httpx.AsyncClient", return_value=context):
        result = client.post("/api/v1/auth/openrouter/exchange", json={"code": "test-code", "code_verifier": "v" * 64})
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {"key": "sk-or-test-only"}
    args = transport.post.call_args
    assert args.args[0] == "https://openrouter.ai/api/v1/auth/keys"
    assert args.kwargs["json"]["code_challenge_method"] == "S256"


@pytest.mark.parametrize("verifier", ["short", "!" * 64, "a" * 129])
def test_rejects_invalid_verifiers_without_upstream_request(verifier):
    with patch("src.api.v1.auth.httpx.AsyncClient") as upstream:
        response = client.post("/api/v1/auth/openrouter/exchange", json={"code": "test", "code_verifier": verifier})
    assert response.status_code == 422
    upstream.assert_not_called()


@pytest.mark.parametrize("payload", [{}, {"key": "not-an-openrouter-key"}, [], None])
def test_invalid_upstream_response_is_recoverable(payload):
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    context, _ = exchange(response)
    with patch("src.api.v1.auth.httpx.AsyncClient", return_value=context):
        result = client.post("/api/v1/auth/openrouter/exchange", json={"code": "test", "code_verifier": "v" * 64})
    assert result.status_code == 502


def test_provider_errors_never_expose_upstream_secrets():
    response = MagicMock(status_code=403, text="secret-from-upstream")
    context, _ = exchange(response)
    with patch("src.api.v1.auth.httpx.AsyncClient", return_value=context):
        result = client.post("/api/v1/auth/openrouter/exchange", json={"code": "test", "code_verifier": "v" * 64})
    assert result.status_code == 400
    assert "secret-from-upstream" not in result.text


def test_network_failure_is_recoverable():
    context, _ = exchange(error=httpx.ConnectError("private-network-details"))
    with patch("src.api.v1.auth.httpx.AsyncClient", return_value=context):
        result = client.post("/api/v1/auth/openrouter/exchange", json={"code": "test", "code_verifier": "v" * 64})
    assert result.status_code == 502
    assert "private-network-details" not in result.text
