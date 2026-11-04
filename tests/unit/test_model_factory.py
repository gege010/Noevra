"""All shipped provider adapters can be constructed from a clean installation."""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.llm_factory import create_llm
from src.agents.oauth_model import OAuthChatModel


@pytest.mark.parametrize(
    "provider",
    ["groq", "openai", "anthropic", "gemini", "deepseek", "openrouter", "ollama", "custom"],
)
def test_provider_adapter_is_available_without_network(provider):
    model = create_llm(
        provider=provider,
        model="test-model",
        api_key="test-only-token",
        base_url="http://127.0.0.1:11434/v1" if provider in ("ollama", "custom") else None,
    )
    assert isinstance(model, BaseChatModel)


@pytest.mark.parametrize("provider", ["openai", "gemini"])
def test_oauth_uses_its_explicit_adapter_and_requires_a_token(provider):
    model = create_llm(
        provider=provider, model="test-model", api_key="test-only-token", auth_type="oauth"
    )
    assert isinstance(model, OAuthChatModel)
    with pytest.raises(ValueError, match="OAuth token"):
        create_llm(provider=provider, model="test-model", auth_type="oauth")


def test_unknown_provider_and_missing_key_do_not_fall_back():
    with pytest.raises(ValueError, match="Unsupported"):
        create_llm(provider="unknown", model="test-model", api_key="test-only-token")
    with pytest.raises(ValueError, match="key"):
        create_llm(provider="groq", model="test-model")
