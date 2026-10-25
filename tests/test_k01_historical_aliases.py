"""Historical identity aliases preserve era scope and unrelated city names."""

import pandas as pd
import pytest

from nbatools.commands._franchise import team_value_mask
from nbatools.commands._matchup_utils import detect_unresolved_availability_player
from nbatools.commands.entity_resolution import resolve_team, resolve_team_in_query
from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.query


@pytest.mark.parametrize("name", ["Seattle", "Seattle SuperSonics", "SuperSonics", "Sonics"])
def test_seattle_alias_is_era_specific(name):
    resolved = resolve_team(name)
    assert resolved.is_confident and resolved.resolved == "SEA"
    rows = pd.DataFrame({"team_id": [1610612760, 1610612760], "team_abbr": ["SEA", "OKC"]})
    assert rows.loc[team_value_mask(rows, resolved.resolved), "team_abbr"].tolist() == ["SEA"]
    assert rows.loc[team_value_mask(rows, "OKC"), "team_abbr"].tolist() == ["SEA", "OKC"]


@pytest.mark.parametrize("name", ["Seattle Storm", "Seattle University"])
def test_seattle_city_alone_does_not_resolve_an_nba_team(name):
    assert not resolve_team(name).is_confident
    assert not resolve_team_in_query(f"{name} record in 2007-08").is_confident


def test_historical_subject_and_opponent_keep_both_identities():
    parsed = parse_query("Seattle SuperSonics record against Lakers in 2007-08")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["team"] == "SEA"
    assert parsed["route_kwargs"]["opponent"] == "LAL"
    assert parsed["route_kwargs"]["season"] == "2007-08"


@pytest.mark.parametrize(
    "query",
    [
        "What record did the Sonics finish with in 2007-08?",
        "Which record did the Grizzlies end with in 2023-24?",
    ],
)
def test_record_preposition_is_not_an_unresolved_teammate(query):
    parsed = parse_query(query)
    assert parsed["route"] == "team_record"
    assert not parsed.get("unsupported_filters")
    assert not parsed.get("unresolved_availability_player")


@pytest.mark.parametrize(
    "tail",
    ["mystery player", "in 2007-08 with mystery player", "in games where mystery player sits"],
)
def test_record_preposition_does_not_drop_a_person_or_unknown_tail(tail):
    query = "what record did the sonics finish with " + tail
    assert detect_unresolved_availability_player(query, mode="with") is not None
