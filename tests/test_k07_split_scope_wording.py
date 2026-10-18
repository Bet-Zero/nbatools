"""Statistical split clauses retain filters without becoming player names."""

import pytest

from nbatools.commands._matchup_utils import detect_unresolved_availability_player
from nbatools.commands.natural_query import parse_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize("team,stat,value", [("Bucks", "rebounds", 45), ("Celtics", "assists", 30)])
def test_stat_bound_before_named_seasons_keeps_both_buckets(team, stat, value):
    parsed = parse_query(
        f"{team} record with at least {value} {stat} in 2023-24 and 2025-26 by season"
    )
    assert parsed["route"] == "team_split_summary"
    kwargs = parsed["route_kwargs"]
    assert kwargs["split_seasons"] == ["2023-24", "2025-26"]
    assert kwargs["stat"] == {"rebounds": "reb", "assists": "ast"}[stat]
    assert kwargs["min_value"] == value
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize("command", ["Break", "Break down", "Please break down"])
def test_break_summary_command_preserves_player_and_sample(command):
    parsed = parse_query(
        f"{command} Stephen Curry's averages against the Trail Blazers into 2023-24 and 2025-26, using only appearances with 25 or more points"
    )
    assert parsed["route"] == "player_split_summary"
    kwargs = parsed["route_kwargs"]
    assert kwargs["player"] == "Stephen Curry"
    assert kwargs["opponent"] == "POR"
    assert kwargs["split_seasons"] == ["2023-24", "2025-26"]
    assert kwargs["stat"] == "pts" and kwargs["min_value"] == 25
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize("command", ["Break", "Break down"])
def test_split_command_retains_full_name_typo_boundary(command):
    parsed = parse_query(f"{command} Nikloa Jokic averages in 2023-24")
    assert "unresolved_player" in parsed["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize("tail", ["and Davis", "and 2 days rest", "by coach", "when Davis sits"])
def test_stat_bound_scope_does_not_swallow_unknown_or_player_clauses(tail):
    query = f"Lakers record with 45 rebounds in 2023-24 {tail}"
    assert detect_unresolved_availability_player(query.lower(), mode="with") is not None
