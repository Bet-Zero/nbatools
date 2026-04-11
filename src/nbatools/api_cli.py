"""Standalone entry point for the nbatools API server.

Usage::

    nbatools-api                    # default: 127.0.0.1:8000
    nbatools-api --port 9000
    nbatools-api --reload           # development mode
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the nbatools API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload.")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required. Install with: pip install 'nbatools[api]'")
        raise SystemExit(1)

    uvicorn.run("nbatools.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
