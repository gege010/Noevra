"""Start Noevra from a checkout using only Python's standard library.

The first run installs the tested runtime into .venv. Later runs reuse it.
The user's .env, existing venv, and research data are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def dependency_fingerprint() -> str:
    digest = hashlib.sha256()
    for name in ("requirements.txt", "constraints.txt"):
        digest.update((ROOT / name).read_bytes())
    digest.update(f"{sys.version_info.major}.{sys.version_info.minor}".encode())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Install and run your local Noevra workspace.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--install", action="store_true", help="Install/update runtime dependencies, then exit."
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Check the installation and storage without starting research.",
    )
    parser.add_argument("--port", type=int, default=8000, help="Local port (default: 8000).")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required. CI targets Python 3.11 and 3.12.")
    if not 1 <= args.port <= 65535:
        parser.error("Choose a port between 1 and 65535.")

    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    stamp = environment / ".noevra-dependencies"
    expected = dependency_fingerprint()
    ready = python.is_file() and stamp.is_file() and stamp.read_text().strip() == expected
    try:
        if args.check and not ready:
            print(
                "Installation is missing or out of date. Run: python run.py --install",
                file=sys.stderr,
            )
            return 1
        if args.install or not ready:
            stamp.unlink(missing_ok=True)
            if not python.is_file():
                print("Creating an isolated Python environment in .venv...", flush=True)
                venv.EnvBuilder(with_pip=True).create(environment)
            print(
                "Installing the tested runtime dependencies. First setup needs internet access...",
                flush=True,
            )
            subprocess.run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "-c",
                    "constraints.txt",
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([str(python), "-m", "pip", "check"], cwd=ROOT, check=True)
            stamp.write_text(expected + "\n")
        if args.install:
            print("Setup complete. Start with: python run.py")
            return 0
        command = (
            [str(python), "-m", "src", "--check"]
            if args.check
            else [str(python), "-m", "src", "--port", str(args.port)]
        )
        return subprocess.call(command, cwd=ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(
            f"Setup could not finish ({type(exc).__name__}). Check internet access and folder permissions, then retry python run.py --install.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
