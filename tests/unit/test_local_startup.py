"""First-run behavior must not rely on a developer's files, keys or CWD."""

from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from src.config import APP_ROOT, Settings
from src.main import app


def test_storage_is_absolute_and_independent_of_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None, NOEVRA_DATA_DIR="relative-test-data", DATABASE_URL="")
    assert settings.data_dir == (APP_ROOT / "relative-test-data").resolve()
    assert (
        Path(make_url(settings.database_url).database)
        == settings.data_dir / "research_assistant.db"
    )
    explicit = Settings(_env_file=None, DATABASE_URL="sqlite+aiosqlite:///./data/old.db")
    assert Path(make_url(explicit.database_url).database) == APP_ROOT / "data" / "old.db"


def test_old_example_keys_are_not_connections_or_logged_secrets():
    example = Settings(
        _env_file=None,
        GROQ_API_KEY="your_groq_api_key_here",
        LANGSMITH_API_KEY="your_langsmith_api_key_here",
    )
    assert example.groq_api_key == example.langsmith_api_key == ""
    configured = Settings(_env_file=None, OPENAI_API_KEY="private-test-secret")
    assert "private-test-secret" not in repr(configured)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV="prodution")


def test_fresh_workspace_starts_and_serves_without_provider_keys():
    with TestClient(app) as client:
        assert client.get("/api/v1/live").json() == {"status": "ok"}
        assert client.get("/api/v1/research").json() == []
        providers = client.get("/api/v1/research/providers").json()
        assert len(providers) == 8
        assert all(not info["configured_in_backend"] for info in providers.values())
        for asset in (
            "/",
            "/static/app.js",
            "/static/providers.js",
            "/static/app.css",
            "/static/fonts/Manrope.ttf",
        ):
            assert client.get(asset).status_code == 200


def test_installed_check_from_another_directory_has_no_provider_calls(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "src", "--check"],
        cwd=tmp_path,
        env={**__import__("os").environ, "PYTHONPATH": str(APP_ROOT)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "No external services were contacted" in result.stdout
    assert "Server credentials: none" in result.stdout


def test_launcher_rejects_invalid_port_before_installing():
    result = subprocess.run(
        [sys.executable, str(APP_ROOT / "run.py"), "--port", "0"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "between 1 and 65535" in result.stderr


def test_database_lock_blocks_another_process_and_releases(tmp_path):
    from src.db.locking import local_database_lock

    database = str(tmp_path / "history.db")
    command = [
        sys.executable,
        "-c",
        "from src.db.locking import local_database_lock; import sys;\nwith local_database_lock(sys.argv[1]): print('owned')",
        database,
    ]
    with local_database_lock(database):
        blocked = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert blocked.returncode != 0
        assert "already used by another Noevra process" in blocked.stderr
    released = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert released.returncode == 0
    assert "owned" in released.stdout


def test_rebinding_host_and_missing_connection_cannot_start_work():
    client = TestClient(app)
    assert (
        client.get("/api/v1/research/providers", headers={"Host": "untrusted.example"}).status_code
        == 400
    )
    assert client.post("/api/v1/research", json={"query": "A research question"}).status_code == 422
    assert (
        client.post(
            "/api/v1/research",
            json={"query": "A research question", "provider": "openai", "auth_type": "oauth"},
        ).status_code
        == 422
    )
