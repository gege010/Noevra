import os
from pathlib import Path
from functools import lru_cache
from typing import Literal

# A checkout owns its data regardless of the caller's current directory.
# An installed wheel defaults to the user's home, never site-packages.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = Path(os.environ.get("NOEVRA_APP_ROOT", str(PACKAGE_ROOT if (PACKAGE_ROOT / "pyproject.toml").is_file() else Path.home() / ".noevra")))
ENV_FILE = os.environ.get("NOEVRA_ENV_FILE", str(APP_ROOT / ".env"))

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Multi-provider LLM API keys
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY", repr=False)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY", repr=False)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY", repr=False)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY", repr=False)
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY", repr=False)
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY", repr=False)
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")

    # Default LLM configuration
    default_provider: str = Field(default="groq", alias="DEFAULT_PROVIDER")
    llm_model: str = Field(default="openai/gpt-oss-120b", alias="LLM_MODEL")

    # Search & Retrieval
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY", repr=False)

    # Observability
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY", repr=False)
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(default="research-assistant", alias="LANGSMITH_PROJECT")

    data_dir: Path = Field(default=APP_ROOT / "data", alias="NOEVRA_DATA_DIR")

    # Application settings
    app_env: Literal["development", "testing", "production"] = Field(default="development", alias="APP_ENV")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", alias="LOG_LEVEL")
    max_concurrent_jobs: int = Field(default=3, ge=1, le=16, alias="MAX_CONCURRENT_JOBS")
    revision_max: int = Field(default=2, ge=0, le=5, alias="REVISION_MAX")
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
        default="",
        repr=False,
        alias="DATABASE_URL",
    )

    @model_validator(mode="after")
    def resolve_storage(self):
        self.data_dir = self.data_dir.expanduser()
        if not self.data_dir.is_absolute():
            self.data_dir = APP_ROOT / self.data_dir
        self.data_dir = self.data_dir.resolve()
        from sqlalchemy.engine import make_url, URL
        if not self.database_url:
            self.database_url = URL.create("sqlite+aiosqlite", database=str(self.data_dir / "research_assistant.db")).render_as_string(hide_password=False)
        else:
            url = make_url(self.database_url)
            if url.drivername == "sqlite+aiosqlite" and url.database and url.database != ":memory:":
                path = Path(url.database).expanduser()
                if not path.is_absolute():
                    path = APP_ROOT / path
                self.database_url = url.set(database=str(path.resolve())).render_as_string(hide_password=False)
        return self

    @model_validator(mode="before")
    @classmethod
    def ignore_example_credentials(cls, values):
        # Old .env examples must not be treated as usable account connections.
        for key, value in list(values.items()):
            if key.upper().endswith("API_KEY") and isinstance(value, str) and value.strip().lower().startswith(("your_", "your-", "sk-your", "gsk_your", "sk-ant-your", "tvly-your", "sk-or-your", "aizasy_your")):
                values[key] = ""
        return values

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

