"""Account catalogs and authentication boundaries without paid provider calls."""
import json
import time
from unittest.mock import patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from src.agents.oauth_model import OAuthChatModel
from src.api.v1.auth import validate_openai_identity, validate_redirect
from src.config import Settings
from src.main import app, settings
from src.services.provider_service import ProviderConnection, discover_models, normalize_models, validate_endpoint


def test_catalog_filters_non_research_and_hidden_models():
    assert normalize_models("groq", {"data": [{"id":"whisper-large-v3"}, {"id":"llama-text"}]}, "api_key")[0]["id"] == "llama-text"
    assert normalize_models("openai", {"models": [{"slug":"hidden", "visibility":"hide"}, {"slug":"plan-model", "visibility":"list"}]}, "oauth")[0]["id"] == "plan-model"
    assert normalize_models("gemini", {"models": [{"name":"models/embed", "supportedGenerationMethods":["embedContent"]}]}, "api_key") == []


@pytest.mark.asyncio
async def test_catalog_uses_account_key_and_paginates_anthropic():
    requests = []
    def handler(request):
        requests.append(request)
        assert request.headers["x-api-key"] == "test-private-key"
        if len(requests) == 1:
            return httpx.Response(200, json={"data":[{"id":"claude-first"}], "has_more":True, "last_id":"claude-first"})
        assert request.url.params["after_id"] == "claude-first"
        return httpx.Response(200, json={"data":[{"id":"claude-second"}], "has_more":False})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("src.services.provider_service.httpx.AsyncClient", return_value=client):
        result = await discover_models("anthropic", ProviderConnection(api_key="test-private-key"))
    assert [m["id"] for m in result["models"]] == ["claude-first", "claude-second"]
    assert "test-private-key" not in json.dumps(result)


@pytest.mark.asyncio
async def test_upstream_error_does_not_disclose_credential():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(401, text="secret-private-key")))
    with patch("src.services.provider_service.httpx.AsyncClient", return_value=client):
        with pytest.raises(HTTPException) as error:
            await discover_models("groq", ProviderConnection(api_key="secret-private-key"))
    assert error.value.status_code == 401
    assert "secret-private-key" not in error.value.detail


def test_production_configuration_and_endpoint_allowlist():
    with pytest.raises(ValueError):
        Settings(_env_file=None, APP_ENV="production")
    production = Settings(_env_file=None, APP_ENV="production", WORKSPACE_PASSWORD="a"*16, SESSION_SECRET="b"*32, APP_PUBLIC_URL="https://research.example")
    with patch("src.services.provider_service.get_settings", return_value=production):
        with pytest.raises(HTTPException):
            validate_endpoint("http://169.254.169.254/latest")
    with pytest.raises(HTTPException):
        validate_redirect("http://localhost:8000/", "openai")
    validate_redirect("http://127.0.0.1:8000/", "openai")


def test_workspace_requires_session_and_rejects_cross_origin():
    with patch.object(settings, "workspace_password", "private-workspace-password"):
        with patch("src.main.init_db"), patch("src.repositories.job_repository.JobRepository.recover_interrupted"):
            client = TestClient(app, raise_server_exceptions=True)
            assert client.get("/api/v1/research/providers").status_code == 401
            assert client.get("/api/v1/live").status_code == 200
            assert client.post("/api/v1/session", json={"password":"wrong"}).status_code == 401
            assert client.post("/api/v1/session", json={"password":"private-workspace-password"}).status_code == 200
            assert client.get("/api/v1/research/providers").status_code == 200
            assert client.post("/api/v1/session", headers={"Origin":"https://untrusted.example"}, json={"password":"private-workspace-password"}).status_code == 403
            client.delete("/api/v1/session")
            assert client.get("/api/v1/research/providers").status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", [None, "nonce", "audience", "scope", "signature"])
async def test_openai_identity_is_cryptographically_validated(fault):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid="test", alg="RS256", use="sig")
    claims = {"iss":"https://auth.openai.com", "aud":"issued-client", "sub":"account", "iat":int(time.time()), "exp":int(time.time())+300, "nonce":"expected"}
    if fault == "nonce": claims["nonce"] = "wrong"
    if fault == "audience": claims["aud"] = "wrong"
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if fault == "signature" else private
    tokens = {"id_token":jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid":"test"}), "scope":"chatgpt.tokens.use.direct" if fault != "scope" else "openid"}
    def handler(request):
        return httpx.Response(200, json={"issuer":"https://auth.openai.com", "jwks_uri":"https://auth.openai.com/keys"} if request.url.path.endswith("openid-configuration") else {"keys":[jwk]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        if fault:
            with pytest.raises((ValueError, jwt.PyJWTError)):
                await validate_openai_identity(tokens, "issued-client", "expected", client)
        else:
            await validate_openai_identity(tokens, "issued-client", "expected", client)


@pytest.mark.asyncio
@pytest.mark.parametrize("completion", ["response.completed", "response.incomplete", None])
async def test_responses_inference_requires_terminal_completion(completion):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["store"] is False and payload["stream"] is True
        assert request.url.path == "/v1/responses"
        events = [{"type":"response.output_text.delta", "delta":"Research content"}]
        if completion: events.append({"type":completion})
        return httpx.Response(200, text="".join("data: "+json.dumps(e)+"\n\n" for e in events))
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = OAuthChatModel(provider="openai", model="live-model", token="test-secret")
    assert "test-secret" not in repr(model)
    with patch("src.agents.oauth_model.httpx.AsyncClient", return_value=client):
        if completion == "response.completed":
            assert (await model.ainvoke([HumanMessage(content="question")])).content == "Research content"
        else:
            with pytest.raises(RuntimeError):
                await model.ainvoke([HumanMessage(content="question")])
