"""Core route/result/table section contracts for display safety."""

import pandas as pd
import pytest

from nbatools.commands.structured_results import (
    ComparisonResult,
    FinderResult,
    LeaderboardResult,
    SplitSummaryResult,
    StreakResult,
    SummaryResult,
)

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


@pytest.mark.parametrize("route", ["player_split_summary", "team_split_summary"])
def test_wave2_split_routes_emit_summary_and_split_comparison(route):
    result = SplitSummaryResult(
        summary=pd.DataFrame([{"split": "home_away", "games_total": 20}]),
        split_comparison=pd.DataFrame(
            [
                {"bucket": "home", "games": 10, "pts_avg": 29.4},
                {"bucket": "away", "games": 10, "pts_avg": 27.1},
            ]
        ),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["summary", "split_comparison"]
    assert sections["split_comparison"][0]["bucket"] == "home"


def test_wave2_player_on_off_uses_summary_presence_state_rows():
    result = SummaryResult(
        summary=pd.DataFrame(
            [
                {"presence_state": "on", "gp": 42, "net_rating": 14.1},
                {"presence_state": "off", "gp": 42, "net_rating": -7.8},
            ]
        ),
        metadata={"route": "player_on_off"},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["summary"]
    assert [row["presence_state"] for row in sections["summary"]] == ["on", "off"]


@pytest.mark.parametrize("route", ["player_streak_finder", "team_streak_finder"])
def test_wave2_streak_routes_emit_streak_section(route):
    result = StreakResult(
        streaks=pd.DataFrame([{"rank": 1, "condition": "pts>=20", "streak_length": 8}]),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["streak"]
    assert sections["streak"][0]["streak_length"] == 8


@pytest.mark.parametrize(
    "route",
    [
        "player_compare",
        "team_compare",
        "team_matchup_record",
        "playoff_matchup_history",
        "matchup_by_decade",
    ],
)
def test_wave2_comparison_routes_emit_summary_and_comparison(route):
    result = ComparisonResult(
        summary=pd.DataFrame([{"team_name": "Lakers"}, {"team_name": "Celtics"}]),
        comparison=pd.DataFrame([{"metric": "wins", "Lakers": 3, "Celtics": 1}]),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["summary", "comparison"]
    assert sections["comparison"][0]["metric"] == "wins"


@pytest.mark.parametrize("route", ["playoff_history", "record_by_decade"])
def test_wave2_history_summary_routes_emit_summary_and_by_season(route):
    result = SummaryResult(
        summary=pd.DataFrame([{"team_name": "Boston Celtics", "wins": 20, "losses": 12}]),
        by_season=pd.DataFrame([{"season": "2024-25", "wins": 8, "losses": 5}]),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["summary", "by_season"]
    assert sections["by_season"][0]["wins"] == 8


def test_wave2_lineup_summary_emits_summary_section():
    result = SummaryResult(
        summary=pd.DataFrame([{"lineup": "Jayson Tatum / Jaylen Brown", "net_rating": 11.0}]),
        metadata={"route": "lineup_summary"},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["summary"]
    assert sections["summary"][0]["lineup"] == "Jayson Tatum / Jaylen Brown"


@pytest.mark.parametrize(
    "route",
    [
        "playoff_appearances",
        "playoff_round_record",
        "record_by_decade_leaderboard",
        "lineup_leaderboard",
    ],
)
def test_wave2_leaderboard_routes_emit_leaderboard_section(route):
    result = LeaderboardResult(
        leaders=pd.DataFrame([{"rank": 1, "team_name": "Sample Team"}]),
        metadata={"route": route},
    )

    sections = result.to_dict()["sections"]

    assert list(sections) == ["leaderboard"]
    assert sections["leaderboard"][0]["rank"] == 1
