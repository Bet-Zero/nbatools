"""The package version has one source of truth.

Before this, `0.7.0` was written out in four places — `pyproject.toml`,
`nbatools.__version__`, the CLI banner, and the API payload fallback — and
stayed at `0.7.0` through 883 commits because bumping it meant remembering all
four. These tests make that failure mode loud instead of silent.

They are deliberately static: they read files rather than the installed
distribution metadata, so they give the same answer whether or not the working
tree has been reinstalled since the last version bump.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_INIT = ROOT / "src/nbatools/__init__.py"
SRC = ROOT / "src/nbatools"

# A version literal: a double-quoted dotted release string such as "0.8.0".
VERSION_LITERAL = re.compile(r'"\d+\.\d+\.\d+[^"]*"')

# `__init__.py` holds the single permitted fallback literal.
ALLOWED_VERSION_LITERAL_FILES = {PACKAGE_INIT.resolve()}


def _pyproject_version() -> str:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def _fallback_version() -> str:
    match = re.search(
        r'^_FALLBACK_VERSION\s*=\s*"([^"]+)"',
        PACKAGE_INIT.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match, f"{PACKAGE_INIT} no longer defines _FALLBACK_VERSION"
    return match.group(1)


def test_fallback_version_matches_pyproject() -> None:
    """The one literal in `src/` must agree with the packaging metadata.

    A release bump touches `pyproject.toml` and `_FALLBACK_VERSION`. If only one
    moves, a source-tree run reports a different version from an installed one.
    """
    pyproject, fallback = _pyproject_version(), _fallback_version()
    assert fallback == pyproject, (
        f"pyproject.toml declares version {pyproject!r} but "
        f"nbatools._FALLBACK_VERSION is {fallback!r}; bump both together"
    )


def test_package_version_is_not_hardcoded_anywhere_else() -> None:
    """No module may keep its own copy of the version.

    `nbatools.__version__` is the single runtime source. The CLI banner and the
    API payload read it; a new literal elsewhere is a fourth copy waiting to go
    stale.
    """
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path.resolve() in ALLOWED_VERSION_LITERAL_FILES:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "version" not in line.lower():
                continue
            for literal in VERSION_LITERAL.findall(line):
                offenders.append(
                    f"{path.relative_to(ROOT)}:{number}: {literal} in {line.strip()!r}"
                )

    assert not offenders, (
        "these lines hardcode a version instead of reading nbatools.__version__:\n  "
        + "\n  ".join(offenders)
    )


def test_version_is_exported_and_well_formed() -> None:
    import nbatools

    assert "__version__" in nbatools.__all__
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", nbatools.__version__), (
        f"nbatools.__version__ is {nbatools.__version__!r}, not a release string"
    )


def test_cli_and_api_report_the_shared_version() -> None:
    """One value reaches every surface that publishes it."""
    import nbatools
    from nbatools import api_handlers, cli

    assert cli.APP_VERSION == nbatools.__version__
    assert api_handlers._VERSION == nbatools.__version__
