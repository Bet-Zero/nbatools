"""C2: player records, rookie win boards and a team's best decade.

"players with the best record" and "rookies with the most wins" ranked teams,
"players with the most wins by decade" ranked team decades, and "Lakers best
decade" listed this season's games.

Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.season_leaders import build_result
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "ascending", "season_type"),
    [
        ("players with the best record", False, "Regular Season"),
        ("players with the worst record", True, "Regular Season"),
        ("player with the best playoff record", False, "Playoffs"),
    ],
)
def test_player_records_rank_win_percentage(query, ascending, season_type):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["stat"], kwargs["ascending"], kwargs["season_type"]) == (
        "win_pct",
        ascending,
        season_type,
    )
    assert not kwargs["wins_only"] and not kwargs["losses_only"]


def test_best_single_season_record_by_a_player_ranks_each_season():
    kwargs = parse_query("best record by a player in a single season")["route_kwargs"]
    assert (kwargs["stat"], kwargs["start_season"], kwargs["per_season"]) == (
        "win_pct",
        "1996-97",
        True,
    )


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("rookies with the most wins", "games_played"),
        ("most wins by a rookie", "games_played"),
        ("rookies with the best record", "win_pct"),
    ],
)
def test_rookie_subjects_rank_players(query, stat):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["stat"], kwargs["rookies_only"]) == (stat, True)


def test_vs_dot_rookies_are_opponents():
    kwargs = parse_query("players with the most wins vs. rookies")["route_kwargs"]
    assert not kwargs.get("rookies_only")


@pytest.mark.parametrize("query", ["teams with the best record", "best record"])
def test_team_record_boards_stay(query):
    assert parse_query(query)["route"] == "team_record_leaderboard"


def test_player_wins_by_decade_refuse_rather_than_rank_teams():
    parsed = parse_query("players with the most wins by decade")
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["player_record_by_decade"]


@pytest.mark.parametrize(
    ("query", "season_type"),
    [
        ("Lakers best decade", "Regular Season"),
        ("Lakers worst decade", "Regular Season"),
        ("Celtics winningest decade", "Regular Season"),
        ("which decade did the Lakers win the most", "Regular Season"),
        ("Lakers best playoff decade", "Playoffs"),
    ],
)
def test_team_best_decade_is_the_decade_table(query, season_type):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "record_by_decade"
    assert (kwargs["season_type"], kwargs["start_season"]) == (season_type, "1996-97")
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    ("query", "ascending"),
    [("best decade", False), ("which team had the best decade", False), ("worst decade", True)],
)
def test_best_decade_ranks_team_decades_by_record(query, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "record_by_decade_leaderboard"
    assert (kwargs["stat"], bool(kwargs.get("ascending"))) == ("win_pct", ascending)


def test_player_best_decade_refuses():
    parsed = parse_query("LeBron best decade")
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["player_decade"]


def test_which_decade_without_a_record_stays_unclear():
    parsed = parse_query("which decade had the most points")
    assert parsed["route"] != "record_by_decade_leaderboard"


@pytest.mark.fixture_data
def test_player_record_board_counts_his_games():
    result = build_result(season="2025-26", stat="win_pct", limit=50)
    rows = result.leaders
    assert (rows["win_pct"] == rows["wins"] / (rows["wins"] + rows["losses"])).all()
    assert list(rows["win_pct"]) == sorted(rows["win_pct"], reverse=True)
    floor = -(-rows["games_played"].max() // 2)
    assert (rows["games_played"] >= floor).all()
    assert any("at least" in caveat for caveat in result.caveats)


@pytest.mark.fixture_data
def test_players_with_the_best_record_answers():
    result = execute_natural_query("players with the worst record")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert rows[0]["win_pct"] <= rows[-1]["win_pct"]
    assert {"wins", "losses"} <= set(rows[0])


@pytest.mark.parametrize(
    "query",
    [
        "best decade for points",
        "best decade by net rating",
        "Lakers best decade scoring",
        "Lakers best defensive decade",
        "best offensive decade",
    ],
)
def test_decade_superlative_with_a_stat_refuses(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["decade_stat"]


@pytest.mark.parametrize(
    "query",
    [
        "which decade did the Lakers lose the most",
        "Lakers best decade by wins",
    ],
)
def test_more_team_decade_wordings(query):
    parsed = parse_query(query)
    assert parsed["route"] == "record_by_decade"
    assert not parsed["route_kwargs"].get("unsupported_filters")


@pytest.mark.parametrize("query", ["which decade did LeBron win the most", "LeBron wins by decade"])
def test_player_decades_refuse(query):
    assert parse_query(query)["route_kwargs"]["unsupported_filters"] == ["player_decade"]


def test_role_rides_along():
    kwargs = parse_query("players with the best record coming off the bench")["route_kwargs"]
    assert kwargs["role"] == "bench"


@pytest.mark.parametrize(
    "query", ["most wins by a rookie coach", "rookie coach with the most wins"]
)
def test_rookie_coaches_are_not_rookie_players(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert not kwargs.get("rookies_only")


def test_which_decade_keeps_a_wins_filter_on_other_stats():
    parsed = parse_query("which decade did the Lakers score the most in wins")
    assert parsed["route"] != "record_by_decade" or parsed["route_kwargs"].get("wins_only")


@pytest.mark.fixture_data
def test_single_season_records_skip_short_seasons(monkeypatch):
    from nbatools.commands import season_leaders

    seen = {}
    real = season_leaders.best_single_seasons

    def spy(build, kwargs, **options):
        seen.update(options)
        return real(build, kwargs, **options)

    monkeypatch.setattr(season_leaders, "best_single_seasons", spy)
    build_result(start_season="2023-24", end_season="2025-26", stat="win_pct", per_season=True)
    assert seen["full_seasons_only"] is True


def test_one_postseason_counts_a_swept_series():
    import pandas as pd

    from nbatools.commands.season_leaders import _win_pct_floor

    df = pd.DataFrame({"games_played": [4, 12, 24]})
    assert _win_pct_floor(df, 1, season_type="Playoffs") == 4
    assert _win_pct_floor(df, 1, season_type="Playoffs", num_seasons=3) == 12
    assert _win_pct_floor(df, 1, season_type="Regular Season") == 12
