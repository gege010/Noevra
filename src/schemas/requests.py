"""Pydantic request schemas for autonomous research."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1500, description="Research topic, hypothesis, or inquiry")
    provider: str = Field(default="groq", description="LLM provider (groq, openai, anthropic, gemini, deepseek, openrouter, ollama, custom)")
    model: str = Field(default="llama-3.3-70b-versatile", description="Model identifier")
    api_key: str | None = Field(default=None, description="Optional client-provided API key override")
    base_url: str | None = Field(default=None, description="Optional custom base URL for local LLMs or custom gateway")
    depth: Literal["quick", "standard", "deep"] = Field(default="standard", description="Research depth level")
    domain_focus: Literal["general", "cs_ai", "biomedical", "economics", "physics", "policy"] = Field(default="general", description="Disciplinary domain")
    citation_style: Literal["ieee", "apa", "nature", "harvard"] = Field(default="ieee", description="Academic citation format")
    language: Literal["en", "id"] = Field(default="en", description="Monograph language (English or Indonesian)")
    max_iterations: int = Field(default=10, ge=1, le=25, description="Maximum agent execution cycles")
    sources_limit: int = Field(default=20, ge=5, le=100)
    include_academic: bool = Field(default=True)
    include_web: bool = Field(default=True)
    output_format: str = Field(default="both", pattern="^(markdown|pdf|both)$")

    @model_validator(mode="after")
    def validate_sources(self):
        self.query = self.query.strip()
        if len(self.query) < 3:
            raise ValueError("Research question must contain at least three non-whitespace characters")
        if not self.include_academic and not self.include_web:
            raise ValueError("Enable at least one source collection")
        if self.provider not in {"groq", "openai", "anthropic", "gemini", "deepseek", "openrouter", "ollama", "custom"}:
            raise ValueError("Unsupported LLM provider")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "Impact of transformer architecture on modern NLP",
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "depth": "standard",
                    "domain_focus": "cs_ai",
                    "citation_style": "ieee",
                    "language": "en",
                }
            ]
        }
    }
