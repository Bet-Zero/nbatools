"""Team records over a team's most recent games ("Knicks record last 10 games").

`team_record` used to parse the last-N window and then refuse, because it had
no execution path. It now selects the window with the same helper as the team
and player summaries: apply every other filter, then keep the N most recent
qualifying games (newest by date, then game id). Expected values come straight
from the fixture's team game CSVs, never from the engine.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

TEAM_STATS = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _team_games(
    team: str,
    season: str = "2025-26",
    season_type: str = "regular_season",
    *,
    home_only: bool = False,
    opponent: str | None = None,
) -> list[dict[str, str]]:
    with (TEAM_STATS / f"{season}_{season_type}.csv").open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["team_abbr"] == team]
    if home_only:
        rows = [row for row in rows if row["is_home"] in {"1", "True"}]
    if opponent:
        rows = [row for row in rows if row["opponent_team_abbr"] == opponent]
    return sorted(rows, key=lambda row: (row["game_date"], int(row["game_id"])), reverse=True)


def _record(rows: list[dict[str, str]]) -> dict:
    return {
        "games": len(rows),
        "wins": sum(row["wl"] == "W" for row in rows),
        "losses": sum(row["wl"] == "L" for row in rows),
        "game_ids": sorted(int(row["game_id"]) for row in rows),
        "pts_avg": round(sum(int(row["pts"]) for row in rows) / len(rows), 3),
    }


def _answer(query_result) -> dict:
    sections = query_result.result.to_dict()["sections"]
    (summary,) = sections["summary"]
    return {
        "games": summary["games"],
        "wins": summary["wins"],
        "losses": summary["losses"],
        "game_ids": sorted(int(row["game_id"]) for row in sections["game_log"]),
        "pts_avg": summary["pts_avg"],
    }


@pytest.mark.parametrize(
    ("query", "expected_rows"),
    [
        ("Knicks record last 10 games", lambda: _team_games("NYK")[:10]),
        ("Celtics record in their last 15 games", lambda: _team_games("BOS")[:15]),
        ("what is the warriors record over their last 7", lambda: _team_games("GSW")[:7]),
        (
            "Lakers home record last 10 games",
            lambda: _team_games("LAL", home_only=True)[:10],
        ),
        (
            "Knicks record last 4 games vs Celtics",
            lambda: _team_games("NYK", opponent="BOS")[:4],
        ),
        (
            "Knicks record last 10 games 2024-25",
            lambda: _team_games("NYK", season="2024-25")[:10],
        ),
        (
            "Lakers playoff record last 3 games",
            lambda: _team_games("LAL", season_type="playoffs")[:3],
        ),
        # More games requested than played this season: the whole season,
        # labelled as such.
        ("Knicks record last 500 games this season", lambda: _team_games("NYK")),
    ],
)
def test_team_record_counts_the_selected_recent_games(query, expected_rows):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)

    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.route == "team_record"
    assert _answer(result) == _record(expected_rows())


def test_window_larger_than_the_season_says_how_many_games_were_played():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Knicks record last 500 games this season")

    assert "last 500 games (played 60)" in result.result.to_dict()["caveats"]


def test_single_game_window_caveat_is_singular():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Knicks record last 1 game")
    assert result.result_status == "ok", result.result_reason
    assert _answer(result)["game_ids"] == _record(_team_games("NYK")[:1])["game_ids"]
    assert "last 1 game (played 1)" in result.result.to_dict()["caveats"]


def test_record_summary_and_structured_request_select_the_same_games():
    from nbatools.query_service import execute_natural_query, execute_structured_query

    expected = _record(_team_games("NYK")[:10])
    record = execute_natural_query("Knicks record last 10 games")
    summary = execute_natural_query("Knicks summary last 10 games")
    structured = execute_structured_query("team_record", team="NYK", season="2025-26", last_n=10)

    assert summary.route == "game_summary"
    assert _answer(record) == expected
    assert _answer(summary) == expected
    assert _answer(structured) == expected
