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

SUPPORTED_PROVIDERS = {
    "groq": {
        "name": "Groq (High-Speed Inference)",
        "models": [
            {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B (High Reasoning)", "context": "128k"},
            {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B (Fast Research)", "context": "128k"},
            {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B (Lightweight)", "context": "128k"},
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "context": "128k"},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant", "context": "128k"},
        ],
        "default_model": "openai/gpt-oss-120b",
        "requires_key": True,
        "env_var": "GROQ_API_KEY",
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o (Omni Frontier)", "context": "128k"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Fast & Efficient)", "context": "128k"},
            {"id": "o3-mini", "name": "o3-mini (High-Reasoning)", "context": "200k"},
            {"id": "o1", "name": "o1 (Deep Reasoning)", "context": "200k"},
        ],
        "default_model": "gpt-4o",
        "requires_key": True,
        "env_var": "OPENAI_API_KEY",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "models": [
            {"id": "claude-3-7-sonnet-latest", "name": "Claude 3.7 Sonnet (Hybrid Reasoning)", "context": "200k"},
            {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet", "context": "200k"},
            {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku", "context": "200k"},
        ],
        "default_model": "claude-3-7-sonnet-latest",
        "requires_key": True,
        "env_var": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "name": "Google Gemini",
        "models": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Ultra-Fast)", "context": "1M"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro (Deep Research)", "context": "2M"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "context": "1M"},
        ],
        "default_model": "gemini-2.0-flash",
        "requires_key": True,
        "env_var": "GEMINI_API_KEY",
    },
    "deepseek": {
        "name": "DeepSeek API",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3", "context": "64k"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1", "context": "64k"},
        ],
        "default_model": "deepseek-chat",
        "requires_key": True,
        "env_var": "DEEPSEEK_API_KEY",
    },
    "openrouter": {
        "name": "OpenRouter (Universal Gateway)",
        "models": [
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "context": "128k"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "context": "200k"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "context": "1M"},
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "context": "64k"},
        ],
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "requires_key": True,
        "env_var": "OPENROUTER_API_KEY",
    },
    "ollama": {
        "name": "Ollama (Local & Free)",
        "models": [
            {"id": "llama3.3", "name": "Llama 3.3", "context": "128k"},
            {"id": "qwen2.5:14b", "name": "Qwen 2.5 14B", "context": "32k"},
            {"id": "deepseek-r1:14b", "name": "DeepSeek R1 14B", "context": "64k"},
            {"id": "mistral", "name": "Mistral 7B", "context": "32k"},
        ],
        "default_model": "llama3.3",
        "requires_key": False,
        "env_var": "OLLAMA_BASE_URL",
    },
    "custom": {
        "name": "Custom OpenAI-Compatible Endpoint",
        "models": [
            {"id": "custom-model", "name": "Custom Model (LM Studio / vLLM / Local)", "context": "Variable"}
        ],
        "default_model": "custom-model",
        "requires_key": False,
        "env_var": "CUSTOM_BASE_URL",
    },
}


def get_available_providers() -> dict[str, Any]:
    """Returns provider metadata and configured status for UI."""
    result = {}
    for key, val in SUPPORTED_PROVIDERS.items():
        configured = False
        if key == "groq" and bool(settings.groq_api_key):
            configured = True
        elif key == "openai" and bool(settings.openai_api_key):
            configured = True
        elif key == "anthropic" and bool(settings.anthropic_api_key):
            configured = True
        elif key == "gemini" and bool(settings.gemini_api_key or os.getenv("GOOGLE_API_KEY")):
            configured = True
        elif key == "deepseek" and bool(settings.deepseek_api_key):
            configured = True
        elif key == "openrouter" and bool(settings.openrouter_api_key):
            configured = True
        elif key in ("ollama", "custom"):
            configured = True  # Can be used locally without cloud key

        result[key] = {
            **val,
            "configured_in_backend": configured,
        }
    return result


def create_llm(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.1,
    streaming: bool = False,
) -> BaseChatModel:
    """Instantiate a chat model based on user selection or defaults."""
    provider = (provider or settings.default_provider or "groq").lower().strip()
    
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
            temperature=temperature,
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
        url = base_url or settings.ollama_base_url or "http://localhost:11434/v1"
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
        url = base_url or "http://localhost:1234/v1"
        model_name = model or "custom-model"
        return ChatOpenAI(
            api_key=api_key or "custom",
            model=model_name,
            base_url=url,
            temperature=temperature,
            streaming=streaming,
        )

    else:
        logger.warning("unknown_provider_fallback_to_groq", provider=provider)
        return create_llm(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key=settings.groq_api_key,
            temperature=temperature,
            streaming=streaming,
        )
