"""The committed query fixture must stay a real baseline.

`assert_filter_applied_or_refused` returns early when the filtered query is
refused, without consulting the control. So a fixture too thin to answer the
*control* queries makes `tests/test_filter_execution_integrity.py` pass
vacuously: every query refuses for want of data, every assertion is satisfied,
and the badge-lying guard becomes decorative. That is strictly worse than the
honest skip it replaced.

These tests are that guard's guard. They assert the fixture can actually serve
as a comparison baseline, that it is internally consistent, and that it stays in
step with the generator that writes it.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from tests._filter_evidence import collect_evidence
from tests.test_filter_execution_integrity import FILTER_PAIRS

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "qa/fixtures/query_engine_sample"
FIXTURE_DATA = FIXTURE / "data"

CONTROL_QUERIES = sorted({control for _filtered, control, _badge in FILTER_PAIRS})


def _rows(relative: str) -> list[dict[str, str]]:
    with (FIXTURE_DATA / relative).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# ── The fixture is a usable baseline ──────────────────────────────────


@pytest.mark.fixture_data
@pytest.mark.parametrize("control_query", CONTROL_QUERIES)
def test_every_control_query_returns_a_populated_answer(control_query: str) -> None:
    """Each unfiltered control must answer, or its filter test proves nothing.

    If this fails, do not weaken it: extend the fixture until the control
    answers again. A refusing control means the filter-integrity assertion it
    backs has silently stopped comparing anything.
    """
    from nbatools.query_service import execute_natural_query

    evidence = collect_evidence(control_query, execute_natural_query)

    assert evidence.status == "ok", (
        f"control {control_query!r} returned status={evidence.status!r} "
        f"(reason={evidence.reason!r}) against the fixture. It cannot serve as a "
        f"comparison baseline, so every filter test using it would pass without "
        f"comparing anything."
    )
    assert evidence.populated, (
        f"control {control_query!r} returned an empty answer against the fixture "
        f"(sections={evidence.sections}); it cannot serve as a baseline."
    )


# ── The fixture matches its generator ─────────────────────────────────


def test_committed_fixture_matches_the_generator() -> None:
    """The fixture is generated, not hand-edited.

    Hand-editing a CSV here would desynchronise the datasets that are derived
    from each other — team totals from player lines, rest days from game dates —
    and produce a fixture that no real pipeline could have emitted.
    """
    result = subprocess.run(
        [sys.executable, "tools/generate_query_fixture.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "the committed fixture differs from tools/generate_query_fixture.py:\n"
        f"{result.stdout}{result.stderr}"
    )


# ── The fixture is internally consistent ──────────────────────────────


def test_team_totals_equal_the_sum_of_their_player_lines() -> None:
    """A team box score no real pipeline could produce is not a fixture.

    Every team total is summed from that team's player lines by the generator;
    this proves the emitted CSVs still agree.
    """
    summed: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in _rows("raw/player_game_stats/2023-24_regular_season.csv"):
        key = (row["game_id"], row["team_id"])
        for field in ("pts", "reb", "ast", "fgm", "fga", "fg3m", "tov"):
            summed[key][field] += int(row[field])

    checked = 0
    for row in _rows("raw/team_game_stats/2023-24_regular_season.csv"):
        key = (row["game_id"], row["team_id"])
        assert key in summed, f"team row {key} has no player rows"
        for field in ("pts", "reb", "ast", "fgm", "fga", "fg3m", "tov"):
            assert int(row[field]) == summed[key][field], (
                f"team {row['team_abbr']} game {row['game_id']}: {field} is "
                f"{row[field]} but its player lines sum to {summed[key][field]}"
            )
        checked += 1
    assert checked > 0


def test_every_game_has_exactly_two_teams_and_one_winner() -> None:
    sides: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _rows("raw/team_game_stats/2023-24_regular_season.csv"):
        sides[row["game_id"]].append(row)

    assert sides, "fixture has no team game rows"
    for game_id, rows in sides.items():
        assert len(rows) == 2, f"game {game_id} has {len(rows)} team rows, expected 2"
        assert {row["wl"] for row in rows} == {"W", "L"}, (
            f"game {game_id} does not have exactly one winner: "
            f"{[(r['team_abbr'], r['wl'], r['pts']) for r in rows]}"
        )
        home = [row for row in rows if row["is_home"] == "True"]
        assert len(home) == 1, f"game {game_id} does not have exactly one home team"


def test_every_player_game_row_has_a_trusted_starter_role() -> None:
    """Partial starter coverage makes a role-filtered leaderboard a wrong answer.

    `season_leaders` refuses rather than returning a partial board, so the
    fixture must cover every player-game or the role path is untestable.
    """
    roles = {
        (row["game_id"], row["team_id"], row["player_id"])
        for row in _rows("raw/player_game_starter_roles/2023-24_regular_season.csv")
        if row["role_source_trusted"] == "True"
    }
    missing = [
        (row["game_id"], row["team_abbr"], row["player_name"])
        for row in _rows("raw/player_game_stats/2023-24_regular_season.csv")
        if (row["game_id"], row["team_id"], row["player_id"]) not in roles
    ]
    assert not missing, f"{len(missing)} player-games lack a trusted role, e.g. {missing[:3]}"


def test_no_fixture_player_name_resolves_to_a_different_player() -> None:
    """A fixture name must not hand its rows to another player's question.

    `apply_base_filters` matches `player_name` exactly against whatever entity
    resolution produced, so a name that resolves elsewhere silently answers
    about someone else — the wrong-answer class this repository refuses to ship.

    Two real collisions were found while building this fixture and removed:
    `Karl-Anthony Towns` resolves to `Carmelo Anthony`, and `Nikola Jovic`
    resolves to `Nikola Jokić`. Resolving to *nothing* is fine — such a player
    is only ever reached through a leaderboard, never by name.

    This lives here rather than in the generator because the generator must stay
    importable without project dependencies: `--check` runs in the
    docs-governance job, which installs none.
    """
    from nbatools.commands.entity_resolution import resolve_player

    problems: list[str] = []
    for row in _rows("raw/rosters/2023-24.csv"):
        name = row["player_name"]
        resolved = resolve_player(name).resolved
        if resolved is not None and resolved != name:
            problems.append(f"{name!r} resolves to {resolved!r}")

    assert problems == [], (
        "fixture player names that resolve to a different player: "
        + "; ".join(problems)
        + ". Rename them in tools/generate_query_fixture.py and regenerate."
    )


def test_fixture_covers_the_engine_default_season() -> None:
    """An unanchored query defaults to the latest season; it must be present.

    Without it, "Lakers playoff history" and "Lakers vs Celtics record" refuse
    for want of data and stop being baselines.
    """
    from nbatools.commands._seasons import LATEST_PLAYOFF_SEASON, LATEST_REGULAR_SEASON

    available = {path.name.split("_")[0] for path in (FIXTURE_DATA / "raw/games").glob("*.csv")}
    assert LATEST_REGULAR_SEASON in available, (
        f"fixture covers {sorted(available)} but unanchored queries default to "
        f"{LATEST_REGULAR_SEASON}"
    )
    playoff_seasons = {
        path.name.split("_")[0] for path in (FIXTURE_DATA / "raw/games").glob("*_playoffs.csv")
    }
    assert LATEST_PLAYOFF_SEASON in playoff_seasons, (
        f"fixture has playoff data for {sorted(playoff_seasons)} but unanchored "
        f"playoff queries default to {LATEST_PLAYOFF_SEASON}"
    )


def test_position_groups_the_filter_resolves_all_have_members() -> None:
    """A position-filtered leaderboard cannot restrict an absent group."""
    from nbatools.commands.season_leaders import _resolve_position_filter

    positions = {row["position"] for row in _rows("raw/rosters/2023-24.csv")}
    for group in ("guards", "centers", "forwards"):
        codes = _resolve_position_filter(group)
        assert codes, f"{group!r} no longer resolves to position codes"
        assert positions & codes, (
            f"no fixture player has a {group!r} position code ({sorted(codes)}); "
            f"a {group}-filtered leaderboard could not restrict anything"
        )


# ── The two data markers stay separate ────────────────────────────────


def test_no_test_carries_both_data_markers() -> None:
    """A test reads the real generation or the fixture, never both.

    Synthetic data cannot satisfy an assertion about a real average. A module
    carrying both markers would run against the fixture and assert real values.
    """
    # Applied markers only, not prose. This module is excluded because it names
    # both markers in its own assertion, which would otherwise make it its own
    # first offender.
    fixture_marker = "mark." + "fixture_data"
    real_marker = "mark." + "needs_data"

    offenders: list[str] = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if fixture_marker in text and real_marker in text:
            offenders.append(path.name)
    assert offenders == [], (
        f"these modules reference both fixture_data and needs_data: {offenders}. "
        "Split them: behavioural assertions use the fixture, value assertions "
        "use the real pinned generation."
    )
