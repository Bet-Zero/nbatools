"""Self members are redundant union filters, never an inferred subject."""

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.mark.parametrize(
    "query,team,opponents",
    [
        ("Lakers record against Lakers and Celtics in 2023-24", "LAL", ["LAL", "BOS"]),
        ("Lakers record against Celtics and Lakers in 2023-24", "LAL", ["BOS", "LAL"]),
        ("Against Lakers and Celtics, what was Lakers record in 2023-24?", "LAL", ["LAL", "BOS"]),
        ("Nuggets record against Timberwolves and Nuggets in 2023-24", "DEN", ["MIN", "DEN"]),
        ("Against WAS and Celtics, what was WAS record in 2023-24?", "WAS", ["WAS", "BOS"]),
    ],
)
def test_explicit_subject_keeps_complete_union(query, team, opponents):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["team"] == team and kwargs["opponent"] == opponents
    assert not kwargs.get("unsupported_filters")
    meta = execute_natural_query(query).metadata
    assert meta["team"] == team and meta["team_context"]["team_abbr"] == team
    assert meta["opponents"] == opponents and meta["opponent"] == ", ".join(opponents)
    assert not meta.get("opponent_context")


@pytest.mark.parametrize("opponents", ["Lakers and Celtics", "Celtics and Lakers"])
def test_named_request_team_bound_remains_own_stat(opponents):
    kwargs = parse_query(
        f"Lakers games against {opponents} when Lakers score at least 110 in 2023-24"
    )["route_kwargs"]
    assert kwargs["team"] == "LAL" and kwargs["stat"] == "pts" and kwargs["min_value"] == 110
    assert not kwargs.get("conditions") and not kwargs.get("unsupported_filters")


def test_named_other_opponent_bound_retains_owner():
    kwargs = parse_query(
        "Lakers games against Lakers and Celtics when Celtics score at least 120 in 2023-24"
    )["route_kwargs"]
    assert kwargs["conditions"] == [
        dict(stat="opponent_pts", min_value=120, max_value=None, opponent_team="BOS")
    ]


def test_explicit_player_team_has_precedence_over_redundant_union_member():
    kwargs = parse_query(
        "Lakers LeBron James games against Lakers and Celtics when Lakers score at least 110 in 2023-24"
    )["route_kwargs"]
    assert kwargs["team"] == "LAL" and kwargs["stat"] == "team_pts"
    assert kwargs["conditions"] == [dict(stat="team_pts", min_value=110, max_value=None)]


@pytest.mark.parametrize(
    "query",
    [
        "record against Lakers and Celtics in 2023-24",
        "record against Celtics and Lakers in 2023-24",
    ],
)
def test_list_alone_does_not_choose_its_subject(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert "multiple_opponents" in result.metadata["unsupported_filters"]
    assert result.metadata["team"] is None and not result.metadata.get("team_context")
    assert set(result.metadata["opponents"]) == {"LAL", "BOS"}
    assert not result.result.to_dict()["sections"]


def test_scalar_self_and_third_owner_safeguards_remain():
    scalar = parse_query("Lakers record against Lakers in 2023-24")["route_kwargs"]
    assert "team_is_opponent" in scalar["unsupported_filters"]
    other = parse_query(
        "Against Lakers and Celtics, what was Lakers record when NYK score at least 110 in 2023-24?"
    )["route_kwargs"]
    assert other["team"] == "LAL" and other["opponent"] == ["LAL", "BOS"]
    assert "other_team_stat" in other["unsupported_filters"]
