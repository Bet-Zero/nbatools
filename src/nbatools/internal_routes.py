"""Environment policy for internal-only browser routes."""

from __future__ import annotations

import os
from collections.abc import Mapping


def visual_qa_route_available(env: Mapping[str, str] | None = None) -> bool:
    """Return whether ``/visual-qa`` may be served in this environment.

    The route is available only for local development and explicitly identified
    preview/development deployments.  Production and ambiguous deployed
    environments fail closed.
    """
    values = os.environ if env is None else env
    vercel_env = values.get("VERCEL_ENV", "").strip().lower()
    app_env = values.get("ENVIRONMENT", "").strip().lower()

    if vercel_env:
        return vercel_env in {"preview", "development"}
    if app_env:
        return app_env in {"local", "development", "dev", "preview"}
    if values.get("VERCEL"):
        return False
    return True
