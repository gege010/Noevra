"""A failed or outdated setup must not be mistaken for a ready workspace."""

import importlib.util
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock


def launcher(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("noevra_bootstrap", root / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "requirements.txt").write_text("# test manifest\n")
    (tmp_path / "constraints.txt").write_text("# test constraints\n")
    python = (
        tmp_path / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    python.parent.mkdir(parents=True)
    python.touch()
    return module


def test_failed_reinstall_invalidates_ready_stamp_and_preserves_env(tmp_path, monkeypatch):
    module = launcher(tmp_path, monkeypatch)
    env = tmp_path / ".env"
    env.write_text("TEST_SETTING=preserve-me\n")
    stamp = tmp_path / ".venv" / ".noevra-dependencies"
    stamp.write_text(module.dependency_fingerprint())
    monkeypatch.setattr(sys, "argv", ["run.py", "--install"])
    monkeypatch.setattr(
        module.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "pip"))
    )
    assert module.main() == 1
    assert not stamp.exists()
    assert env.read_text() == "TEST_SETTING=preserve-me\n"


def test_check_never_installs_an_outdated_environment(tmp_path, monkeypatch):
    module = launcher(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["run.py", "--check"])
    install = Mock()
    monkeypatch.setattr(module.subprocess, "run", install)
    assert module.main() == 1
    install.assert_not_called()
