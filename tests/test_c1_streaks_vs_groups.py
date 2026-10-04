"""Streaks against a conference, division or quality bar of opponents.

"Lakers longest winning streak vs the West" is the longest run of wins over
the Lakers' consecutive games against Western Conference teams (each team
counted in the seasons it was in the West). Expected values come from the
fixture.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ("2023-24", "2024-25", "2025-26")


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _standings() -> list[dict[str, str]]:
    rows = []
    for season in SEASONS:
        rows += _csv(RAW / "standings_snapshots" / f"{season}_regular_season.csv")
    return rows


def _members(conference: str) -> set[tuple[str, str]]:
    return {
        (row["season"], row["team_abbr"])
        for row in _standings()
        if row["conference"].lower().startswith(conference)
    }


def _longest(flags: list[bool]) -> int:
    best = run = 0
    for flag in flags:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def _team_games(team: str, members: set[tuple[str, str]]) -> list[dict[str, str]]:
    rows = []
    for season in SEASONS:
        rows += _csv(RAW / "team_game_stats" / f"{season}_regular_season.csv")
    games = [
        r
        for r in rows
        if r["team_abbr"] == team and (r["season"], r["opponent_team_abbr"]) in members
    ]
    return sorted(games, key=lambda r: (r["game_date"], int(r["game_id"])))


@pytest.mark.parametrize(
    ("query", "conference"),
    [
        ("Lakers longest winning streak vs the West", "w"),
        ("Celtics longest winning streak against the East", "e"),
    ],
)
def test_team_win_streak_vs_conference(query, conference):
    team = "LAL" if "Lakers" in query else "BOS"
    games = _team_games(team, _members(conference))
    result = _run(query)
    assert result.route == "team_streak_finder"
    streak = result.result.to_dict()["sections"]["streak"][0]
    assert streak["streak_length"] == _longest([g["wl"] == "W" for g in games])
    assert "Conference teams" in " ".join(result.result.to_dict().get("caveats") or [])


def test_player_scoring_streak_vs_conference():
    east = _members("e")
    rows = []
    for season in SEASONS:
        rows += _csv(RAW / "player_game_stats" / f"{season}_regular_season.csv")
    games = sorted(
        (
            r
            for r in rows
            if r["player_name"] == "LeBron James" and (r["season"], r["opponent_team_abbr"]) in east
        ),
        key=lambda r: (r["game_date"], int(r["game_id"])),
    )
    result = _run("LeBron longest 25 point streak against the East")
    assert result.route == "player_streak_finder"
    streak = result.result.to_dict()["sections"]["streak"][0]
    assert streak["streak_length"] == _longest([float(g["pts"]) >= 25 for g in games])


@pytest.mark.parametrize(
    "query",
    ["Lakers winning streak against Pacific teams", "Lakers winning streak against winning teams"],
)
def test_team_streak_vs_division_and_quality_applies_the_filter(query):
    result = _run(query)
    assert result.route == "team_streak_finder"
    assert not result.metadata.get("unsupported_filters")
    kinds = {f["kind"] for f in result.metadata["applied_filters"]}
    assert kinds & {"opponent_division", "quality", "division"}, kinds


def test_league_win_streaks_vs_the_west_rank_every_team():
    west = _members("w")
    expected = {}
    for team in ("LAL", "BOS", "NYK", "MIA", "DEN", "GSW"):
        expected[team] = _longest([g["wl"] == "W" for g in _team_games(team, west)])
    result = _run("longest winning streak vs the West")
    assert result.route == "team_streak_finder"
    rows = result.result.to_dict()["sections"]["streak"]
    lengths = [row["streak_length"] for row in rows]
    assert lengths == sorted(expected.values(), reverse=True)[: len(lengths)]


@pytest.mark.parametrize(
    "query", ["longest 25 point streak vs the East", "longest winning streak vs Pacific teams"]
)
def test_league_streaks_vs_a_group_route(query):
    result = _run(query)
    assert result.route in {"team_streak_finder", "player_streak_finder"}
    assert not result.metadata.get("unsupported_filters")
