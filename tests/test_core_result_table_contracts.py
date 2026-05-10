"""Core route/result/table section contracts for Wave 1 display safety."""

import pandas as pd
import pytest

from nbatools.commands.structured_results import FinderResult, LeaderboardResult, SummaryResult

pytestmark = pytest.mark.output


def test_wave1_summary_routes_emit_current_section_keys():
    result = SummaryResult(
        summary=pd.DataFrame([{"team_name": "Boston Celtics", "wins": 4, "losses": 1}]),
        by_season=pd.DataFrame([{"season": "2025-26", "wins": 4, "losses": 1}]),
        game_log=pd.DataFrame([{"game_date": "2026-02-01", "team_name": "Boston Celtics"}]),
        top_performers=pd.DataFrame([{"player_name": "Jayson Tatum", "pts": 33}]),
        metadata={"route": "game_summary"},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["summary", "by_season", "game_log", "top_performers"]
    assert sections["summary"][0]["team_name"] == "Boston Celtics"
    assert sections["game_log"][0]["game_date"] == "2026-02-01"
    assert sections["top_performers"][0]["player_name"] == "Jayson Tatum"


def test_wave1_team_record_uses_summary_with_optional_game_log():
    record_only = SummaryResult(
        summary=pd.DataFrame([{"team_name": "New York Knicks", "wins": 3, "losses": 5}]),
        by_season=pd.DataFrame([{"season": "2025-26", "wins": 3, "losses": 5}]),
        metadata={"route": "team_record"},
    )
    with_game_log = SummaryResult(
        summary=pd.DataFrame([{"team_name": "New York Knicks", "wins": 3, "losses": 5}]),
        game_log=pd.DataFrame([{"game_date": "2026-02-01", "team_name": "New York Knicks"}]),
        metadata={"route": "team_record"},
    )

    assert list(record_only.to_dict()["sections"]) == ["summary", "by_season"]
    assert list(with_game_log.to_dict()["sections"]) == ["summary", "game_log"]


@pytest.mark.parametrize("route", ["player_game_finder", "game_finder"])
def test_wave1_finder_routes_emit_finder_section(route):
    result = FinderResult(
        games=pd.DataFrame([{"rank": 1, "game_date": "2026-02-01"}]),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["finder"]
    assert sections["finder"][0]["rank"] == 1


@pytest.mark.parametrize(
    "route",
    [
        "season_leaders",
        "season_team_leaders",
        "top_player_games",
        "top_team_games",
        "player_occurrence_leaders",
        "team_occurrence_leaders",
        "player_stretch_leaderboard",
    ],
)
def test_wave1_leaderboard_family_routes_emit_leaderboard_section(route):
    result = LeaderboardResult(
        leaders=pd.DataFrame([{"rank": 1, "player_name": "Sample Leader"}]),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["leaderboard"]
    assert sections["leaderboard"][0]["rank"] == 1
