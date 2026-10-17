"""An explicit opponent consumes its identity, preserving subsequent clauses."""

import pytest

from nbatools.commands._constants import normalize_text
from nbatools.commands._matchup_utils import detect_opponent
from nbatools.query_service import parse_query


@pytest.mark.parametrize(
    "suffix",
    [
        "by season: 2023-24 and 2025-26",
        ", scoring at least 30 points",
        "; at home",
        ": last 10 games",
    ],
)
@pytest.mark.parametrize("marker", ["against", "versus", "vs."])
def test_entity_span_preserves_clause_suffix(marker, suffix):
    query = f"Curry averages {marker} the Denver Nuggets {suffix}"
    opponent, remaining = detect_opponent(normalize_text(query))
    assert opponent == "DEN"
    assert remaining == normalize_text(f"Curry averages {suffix}")


@pytest.mark.parametrize(
    "query,team,opponent",
    [
        ("Split Denver’s road record against Utah by season: 2023-24 and 2025-26.", "DEN", "UTA"),
        ("Minnesota record at home against Denver, split into 2025-26 and 2023-24", "MIN", "DEN"),
    ],
)
def test_season_split_keeps_subject_and_opponent(query, team, opponent):
    parsed = parse_query(query)
    assert parsed["route"] == "team_split_summary"
    assert parsed["route_kwargs"]["team"] == team
    assert parsed["route_kwargs"]["opponent"] == opponent
    assert set(parsed["route_kwargs"]["split_seasons"]) == {"2023-24", "2025-26"}


def test_following_player_scoring_condition_survives():
    parsed = parse_query("Curry averages against Denver scoring at least 30 points in 2023-24")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["player"] == "Stephen Curry"
    assert parsed["route_kwargs"]["opponent"] == "DEN"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["min_value"] == 30
