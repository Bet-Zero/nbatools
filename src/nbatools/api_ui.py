"""Shared UI shell helpers for the local API and Vercel fallback routes."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent / "ui" / "dist"
UI_INDEX = UI_DIR / "index.html"
UI_FALLBACK_ASSET = "/assets/index-fallback.js"
UI_FALLBACK_HTML = f"""<!doctype html>
<html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>nbatools</title>
    </head>
    <body>
        <div id=\"root\"></div>
        <script type=\"module\" src=\"{UI_FALLBACK_ASSET}\"></script>
    </body>
</html>
"""
UI_FALLBACK_SCRIPT = """
const root = document.getElementById("root");
if (root) {
    root.innerHTML = `
        <main
            style="
                font-family: ui-sans-serif, system-ui, sans-serif;
                max-width: 48rem;
                margin: 3rem auto;
                padding: 0 1rem;
                line-height: 1.5;
            "
        >
            <h1 style="margin-bottom: 0.5rem;">nbatools UI bundle not built</h1>
            <p style="margin: 0; color: #4b5563;">
                The API is available, but the frontend build output is missing from this checkout.
            </p>
            <p style="color: #4b5563;">
                Run <code>npm install</code> and <code>npm run build</code> in
                <code>frontend/</code> to enable the bundled UI.
            </p>
        </main>
    `;
}
""".strip()

_ASSET_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml; charset=utf-8",
    ".webp": "image/webp",
}


def load_ui_html(index_path: Path = UI_INDEX) -> str:
    """Return bundled UI HTML when present, else a minimal fallback shell."""
    if index_path.is_file():
        return index_path.read_text()
    return UI_FALLBACK_HTML


def resolve_ui_asset_path(asset_path: str, ui_dir: Path = UI_DIR) -> Path | None:
    """Resolve a UI asset path under the Vite dist directory, rejecting escapes."""
    cleaned = str(asset_path or "").strip().lstrip("/")
    if not cleaned:
        return None

    root = ui_dir.resolve()
    candidate = (root / cleaned).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def ui_asset_response(asset_path: str, ui_dir: Path = UI_DIR) -> tuple[int, bytes, str]:
    """Return a bundled UI asset response tuple for Vercel handlers."""
    candidate = resolve_ui_asset_path(asset_path, ui_dir)
    if candidate is None:
        return HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8"

    content_type = _ASSET_CONTENT_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
    return HTTPStatus.OK, candidate.read_bytes(), content_type
