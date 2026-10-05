"""Occurrence leaders against a conference, division or quality bar.

"which team has the most 120 point games vs the West" counts each team's
120-point games against Western Conference teams. Expected values come from
the fixture.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _west() -> set[str]:
    rows = _csv(RAW / "standings_snapshots" / "2025-26_regular_season.csv")
    return {r["team_abbr"] for r in rows if r["conference"].lower().startswith("w")}


def test_team_120_point_games_vs_the_west():
    west = _west()
    rows = _csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    expected = {}
    for row in rows:
        if row["opponent_team_abbr"] in west and float(row["pts"]) >= 120:
            expected[row["team_abbr"]] = expected.get(row["team_abbr"], 0) + 1

    result = _run("which team has the most 120 point games vs the West")
    assert result.route == "team_occurrence_leaders"
    board = result.result.to_dict()["sections"]["leaderboard"]
    got = {row["team_abbr"]: row["games_pts_120+"] for row in board if row["games_pts_120+"]}
    assert got == expected


def test_players_scoring_40_vs_the_west_counts_distinct_players():
    west = _west()
    rows = _csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    expected = {
        r["player_name"]
        for r in rows
        if r["opponent_team_abbr"] in west and float(r["pts"] or 0) >= 40
    }
    result = _run("how many players scored 40 vs the West")
    assert result.route == "player_occurrence_leaders"
    assert result.result.to_dict()["sections"]["count"][0]["count"] == len(expected)


def test_team_occurrence_vs_a_division_applies_the_filter():
    result = _run("which team has the most 120 point games vs Pacific teams")
    assert result.route == "team_occurrence_leaders"
    assert not result.metadata.get("unsupported_filters")


def test_west_surname_does_not_make_a_conference_query_ambiguous(monkeypatch):
    """Real data has David and Delonte West: "vs the West" is not a player."""
    from nbatools.commands import natural_query
    from nbatools.commands.entity_resolution import ResolutionResult

    real = natural_query.detect_player_resolved

    def resolve(text):
        if __import__("re").search(r"\bwest\b", text):
            return ResolutionResult(
                candidates=["David West", "Delonte West"],
                confidence="ambiguous",
                source="last_name",
            )
        return real(text)

    monkeypatch.setattr(natural_query, "detect_player_resolved", resolve)
    result = _run("which team has the most 120 point games vs the West")
    assert result.route == "team_occurrence_leaders"
    # A player named West is still a player outside the "vs the West" phrase.
    assert natural_query.parse_query("West stats vs the East").get("entity_ambiguity")


def _players(opponents: set[str] | None, test) -> set[str]:
    rows = _csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    return {
        r["player_name"]
        for r in rows
        if (opponents is None or r["opponent_team_abbr"] in opponents) and test(r)
    }


def _count_tens(row) -> int:
    return sum(float(row[s] or 0) >= 10 for s in ("pts", "reb", "ast", "stl", "blk"))


@pytest.mark.parametrize(
    ("query", "opponents", "test"),
    [
        (
            "how many players scored 30 vs the Warriors",
            {"GSW"},
            lambda r: float(r["pts"] or 0) >= 30,
        ),
        ("how many players had a triple double this season", None, lambda r: _count_tens(r) >= 3),
        (
            "how many players had a triple double vs the Nuggets",
            {"DEN"},
            lambda r: _count_tens(r) >= 3,
        ),
        (
            "how many players had a double double vs the Celtics",
            {"BOS"},
            lambda r: _count_tens(r) >= 2,
        ),
    ],
)
def test_distinct_player_counts_apply_the_opponent_and_event(query, opponents, test):
    result = _run(query)
    assert result.route == "player_occurrence_leaders"
    assert result.result.to_dict()["sections"]["count"][0]["count"] == len(
        _players(opponents, test)
    )


def test_distinct_triple_double_count_vs_the_west():
    result = _run("how many players had a triple double vs the West")
    expected = _players(_west(), lambda r: _count_tens(r) >= 3)
    assert result.result.to_dict()["sections"]["count"][0]["count"] == len(expected)
