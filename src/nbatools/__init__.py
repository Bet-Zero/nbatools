__all__ = ["__version__", "execute_natural_query", "execute_structured_query", "QueryResult"]

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _installed_version

# Single source of truth for the package version.
#
# When nbatools is installed (including `pip install -e .`), the version comes
# from the distribution metadata, which is generated from `pyproject.toml`.
# `_FALLBACK_VERSION` covers running straight from a source tree with no
# install, and is the only version literal in `src/`. Everything else — the CLI
# banner, the FastAPI app version, the `/health` payload — reads `__version__`
# from here, so a release bump touches `pyproject.toml` and this line and
# nothing else. `tests/test_package_version.py` fails if the two disagree.
_FALLBACK_VERSION = "0.8.0"

try:
    __version__ = _installed_version("nbatools")
except PackageNotFoundError:  # pragma: no cover - source tree without an install
    __version__ = _FALLBACK_VERSION


def __getattr__(name: str):
    """Lazily expose query-service convenience imports."""
    if name in {"QueryResult", "execute_natural_query", "execute_structured_query"}:
        from nbatools import query_service

        value = getattr(query_service, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'nbatools' has no attribute {name!r}")
