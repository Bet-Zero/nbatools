"""Run the existing app against one explicitly pinned local development snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbatools.development_data import development_snapshot, require_local_development


def create_app(root: Path, manifest_sha256: str):
    """Wrap the existing app for loopback use; public entrypoints never call this."""
    require_local_development()
    # Fail before starting a server if any receipt or manifested byte is invalid.
    with development_snapshot(root, manifest_sha256):
        pass
    from nbatools.api import app

    class LocalDevelopmentApp:
        async def __call__(self, scope, receive, send):
            if scope["type"] in {"http", "websocket"}:
                client = scope.get("client")
                if client and client[0] not in {"127.0.0.1", "::1", "testclient"}:
                    raise ValueError("Development queries are loopback-only")
            with development_snapshot(root, manifest_sha256):
                await app(scope, receive, send)

    return LocalDevelopmentApp()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--query")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.serve == bool(args.query):
        parser.error("Choose --query or --serve")
    if args.serve:
        import uvicorn

        uvicorn.run(
            create_app(args.snapshot, args.manifest_sha256), host="127.0.0.1", port=args.port
        )
    else:
        from nbatools.api_handlers import natural_query_payload

        with development_snapshot(args.snapshot, args.manifest_sha256):
            print(json.dumps(natural_query_payload(args.query), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
