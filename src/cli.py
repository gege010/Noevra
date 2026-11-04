"""One local entry point and a non-billing installation check."""
from __future__ import annotations

import argparse
import socket
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description="Noevra local research workspace")
    parser.add_argument("--check", action="store_true", help="Check configuration and writable storage; no provider requests.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Choose a port between 1 and 65535.")
    try:
        from src.config import get_settings
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=settings.data_dir):
            pass
        if args.check:
            from importlib.metadata import version
            for package in ("fastapi", "uvicorn", "langgraph", "aiosqlite", "fpdf2"):
                print(f"{package}: {version(package)}")
            from src.services.provider_service import provider_metadata
            configured = [info["name"] for info in provider_metadata().values() if info["configured_in_backend"]]
            print(f"Python: {sys.version.split()[0]}")
            print(f"Data directory: {settings.data_dir}")
            print("Storage: writable")
            print("Server credentials: " + (", ".join(configured) or "none; connect a provider in Settings"))
            print("Configuration check passed. No external services were contacted.")
            return 0
        with socket.socket() as listener:
            try:
                listener.bind(("127.0.0.1", args.port))
            except OSError:
                print(f"Port {args.port} is unavailable. Try: python run.py --port {args.port + 1 if args.port < 65535 else 8000}", file=sys.stderr)
                return 1
        print(f"\nOpen http://127.0.0.1:{args.port}\nConnect a provider in Settings > Connections. Press Ctrl+C to stop.\n", flush=True)
        import uvicorn
        uvicorn.run("src.main:app", host="127.0.0.1", port=args.port, workers=1, access_log=False, log_level=settings.log_level.lower())
        return 0
    except ImportError:
        print("A runtime dependency is missing. Run: python run.py --install", file=sys.stderr)
        return 1
    except (ValueError, OSError):
        # Pydantic errors may contain input values: never print raw settings errors.
        print("Configuration or storage is invalid. Check .env against .env.example and ensure the data folder is writable.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
