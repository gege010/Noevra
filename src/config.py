import sys
from functools import lru_cache

# Ensure UTF-8 output on Windows consoles to prevent charmap encoding errors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Multi-provider LLM API keys
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")

    # Default LLM configuration
    default_provider: str = Field(default="groq", alias="DEFAULT_PROVIDER")
    llm_model: str = Field(default="openai/gpt-oss-120b", alias="LLM_MODEL")

    # Search & Retrieval
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # Observability
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(default="research-assistant", alias="LANGSMITH_PROJECT")

    # Application settings
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_concurrent_jobs: int = Field(default=3, ge=1, le=16, alias="MAX_CONCURRENT_JOBS")
    revision_max: int = Field(default=2, alias="REVISION_MAX")
    allowed_origins: list[str] = Field(default_factory=list, alias="ALLOWED_ORIGINS")
    custom_llm_allowed_origins: list[str] = Field(default_factory=list, alias="CUSTOM_LLM_ALLOWED_ORIGINS")
    public_url: str = Field(default="http://127.0.0.1:8000", alias="APP_PUBLIC_URL")
    workspace_password: str = Field(default="", alias="WORKSPACE_PASSWORD", repr=False)
    session_secret: str = Field(default="", alias="SESSION_SECRET", repr=False)
    google_oauth_client_id: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_SECRET", repr=False)
    google_project_id: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT")
    research_timeout_seconds: int = Field(default=900, ge=30, le=7200, alias="RESEARCH_TIMEOUT_SECONDS")
    max_queued_jobs: int = Field(default=12, ge=1, le=100, alias="MAX_QUEUED_JOBS")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/research_assistant.db",
        alias="DATABASE_URL",
    )

    @model_validator(mode="after")
    def configure_tracing(self):
        # Tracing is explicitly opt-in; research may contain private material.
        return self

    @model_validator(mode="after")
    def deployment_requirements(self):
        if self.app_env == "production":
            if len(self.workspace_password) < 16 or len(self.session_secret) < 32:
                raise ValueError("Production requires WORKSPACE_PASSWORD (16+ characters) and SESSION_SECRET (32+ characters)")
            if not self.public_url.startswith("https://"):
                raise ValueError("Production APP_PUBLIC_URL must use HTTPS")
        return self

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production mode."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

