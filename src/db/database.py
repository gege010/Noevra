"""SQLAlchemy async database setup."""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    """Dependency for FastAPI route handlers."""
    async with async_session_maker() as session:
        yield session

async def init_db() -> None:
    """Create all tables and migrate columns if needed."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import inspect
        columns = await conn.run_sync(lambda sync: {col["name"] for col in inspect(sync).get_columns("research_jobs")})
        # Migrate columns if existing database has older schema
        for col, col_type in [
            ("provider", "VARCHAR(50) DEFAULT 'groq'"),
            ("model", "VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile'"),
            ("depth", "VARCHAR(20) DEFAULT 'standard'"),
            ("evidence_json", "JSON"),
            ("step_logs_json", "JSON"),
            ("settings_json", "JSON"),
        ]:
            if col not in columns:
                await conn.exec_driver_sql(f"ALTER TABLE research_jobs ADD COLUMN {col} {col_type};")

