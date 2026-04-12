"""Shared fixtures and markers for the nbatools test suite."""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# ``needs_data`` marker – skip tests that require local CSV data files
# ---------------------------------------------------------------------------
#
# The ``data/raw/`` directory is gitignored and only exists when the user
# has pulled NBA game data locally.  Tests that run real queries against
# those CSVs should be marked with ``@pytest.mark.needs_data`` so they
# are automatically skipped in environments without data (CI, fresh
# clones, etc.).
#
# Usage:
#   - Single test:   @pytest.mark.needs_data
#   - Entire class:  @pytest.mark.needs_data   (on the class)
#   - Entire module: pytestmark = pytest.mark.needs_data
# ---------------------------------------------------------------------------

_DATA_SENTINEL = Path("data/raw/player_game_stats")


def _has_local_data() -> bool:
    """Return True when local CSV data files are present."""
    return _DATA_SENTINEL.is_dir() and any(_DATA_SENTINEL.glob("*.csv"))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "needs_data: skip when local CSV data files are not available",
    )


@pytest.fixture(autouse=True)
def _skip_needs_data(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("needs_data")
    if marker is not None and not _has_local_data():
        pytest.skip("Local CSV data files not available")
