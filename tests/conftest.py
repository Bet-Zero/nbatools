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
    config.addinivalue_line(
        "markers",
        "fixture_data: run against the committed synthetic query fixture",
    )


@pytest.fixture(autouse=True)
def _skip_needs_data(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("needs_data")
    if marker is not None and not _has_local_data():
        pytest.skip("Local CSV data files not available")


# ---------------------------------------------------------------------------
# ``fixture_data`` marker – run against the committed synthetic fixture
# ---------------------------------------------------------------------------
#
# `needs_data` tests read the real pinned generation and assert real values, so
# they skip wherever it is absent — including CI, on every trigger.
#
# `fixture_data` is for tests whose assertion is *behavioural* rather than
# numeric: "a filter either changes the answer or is refused", "this split axis
# is not mistaken for an unapplied filter". Those hold against any internally
# consistent dataset, so they can run everywhere against
# `qa/fixtures/query_engine_sample`, written by
# `tools/generate_query_fixture.py`.
#
# The two markers are mutually exclusive on purpose. Pointing a test that
# asserts a real average at synthetic data would not make it pass; it would make
# it wrong. `tests/test_query_fixture_contract.py` enforces the separation.
# ---------------------------------------------------------------------------

_FIXTURE_ROOT = Path("qa/fixtures/query_engine_sample")
_FIXTURE_SENTINEL = _FIXTURE_ROOT / "data/raw/player_game_stats"


def _has_fixture_data() -> bool:
    """Return True when the committed query fixture is present."""
    return _FIXTURE_SENTINEL.is_dir() and any(_FIXTURE_SENTINEL.glob("*.csv"))


@pytest.fixture(autouse=True)
def _use_fixture_data(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    marker = request.node.get_closest_marker("fixture_data")
    if marker is None:
        yield
        return

    assert request.node.get_closest_marker("needs_data") is None, (
        f"{request.node.nodeid} carries both fixture_data and needs_data. A test "
        "reads either the real pinned generation or the synthetic fixture, never "
        "both: synthetic data cannot satisfy an assertion about a real value."
    )

    if not _has_fixture_data():
        pytest.skip("committed query fixture missing; run tools/generate_query_fixture.py")

    from nbatools.data_source import reset_data_source_cache

    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(_FIXTURE_ROOT.resolve()))
    reset_data_source_cache()
    try:
        yield
    finally:
        # monkeypatch restores the env var; the cached source keyed to the
        # fixture root must go with it or the next test reads the fixture.
        reset_data_source_cache()
