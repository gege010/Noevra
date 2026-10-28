"""Unified multi-provider LLM Factory.

Allows users to dynamically use any model provider (Groq, OpenAI, Anthropic Claude,
Google Gemini, DeepSeek, OpenRouter, Ollama, or custom OpenAI-compatible endpoints)
with per-request API key and model selection.
"""
from __future__ import annotations

import os
from typing import Any
import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

from src.services.provider_service import provider_metadata, validate_endpoint


def get_available_providers() -> dict[str, Any]:
    """Connection capabilities only; model availability comes from live discovery."""
    return provider_metadata()


def create_llm(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.1,
    streaming: bool = False,
    auth_type: str = "api_key",
) -> BaseChatModel:
    """Instantiate a chat model based on user selection or defaults."""
    provider = (provider or settings.default_provider or "groq").lower().strip()
    
    if auth_type == "oauth" and provider in ("openai", "gemini"):
        from src.agents.oauth_model import OAuthChatModel
        return OAuthChatModel(provider=provider, model=model or "", token=api_key or "", project=get_settings().google_project_id)

    if provider == "groq":
        from langchain_groq import ChatGroq
        key = api_key or settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("Groq API key not provided and not found in environment.")
        model_name = model or settings.llm_model or "llama-3.3-70b-versatile"
        return ChatGroq(
            api_key=key,
            model=model_name,
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        key = api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OpenAI API key not provided and not found in environment.")
        model_name = model or "gpt-4o"
        return ChatOpenAI(
            api_key=key,
            model=model_name,
            temperature=None,
            streaming=streaming,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        key = api_key or settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("Anthropic API key not provided and not found in environment.")
        model_name = model or "claude-3-7-sonnet-latest"
        return ChatAnthropic(
            api_key=key,
            model=model_name,
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = api_key or settings.gemini_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("Gemini API key not provided and not found in environment.")
        model_name = model or "gemini-2.0-flash"
        return ChatGoogleGenerativeAI(
            google_api_key=key,
            model=model_name,
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI
        key = api_key or settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not key:
            raise ValueError("DeepSeek API key not provided and not found in environment.")
        model_name = model or "deepseek-chat"
        return ChatOpenAI(
            api_key=key,
            model=model_name,
            base_url="https://api.deepseek.com/v1",
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        key = api_key or settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OpenRouter API key not provided and not found in environment.")
        model_name = model or "meta-llama/llama-3.3-70b-instruct"
        return ChatOpenAI(
            api_key=key,
            model=model_name,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "ollama":
        from langchain_openai import ChatOpenAI
        url = validate_endpoint(base_url or settings.ollama_base_url or "http://localhost:11434/v1")
        model_name = model or "llama3.3"
        return ChatOpenAI(
            api_key=api_key or "ollama",
            model=model_name,
            base_url=url,
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "custom":
        from langchain_openai import ChatOpenAI
        url = validate_endpoint(base_url or "http://localhost:1234/v1")
        model_name = model or "custom-model"
        return ChatOpenAI(
            api_key=api_key or "custom",
            model=model_name,
            base_url=url,
            temperature=temperature,
            streaming=streaming,
        )

    else:
        raise ValueError("Unsupported LLM provider")
