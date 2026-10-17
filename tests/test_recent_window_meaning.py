"""Recent sample units and name grammar preserve explicit request meaning."""

import pytest

from nbatools.commands._parse_helpers import canonicalize_sample_phrases
from nbatools.query_service import parse_query


@pytest.mark.parametrize("unit", ["games", "appearances", "contests", "outings"])
@pytest.mark.parametrize("number", ["9", "nine"])
def test_final_numbered_sample_is_a_window(unit, number):
    parsed = parse_query(
        f"Nikola Jokic averages scoring at least 29 points within his final {number} {unit} in 2023-24"
    )
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["player"] == "Nikola Jokić"
    assert parsed["route_kwargs"]["last_n"] == 9
    assert parsed["route_kwargs"]["last_n_scope"] == "window"
    assert parsed["route_kwargs"]["min_value"] == 29


@pytest.mark.parametrize("lead", ["", "Average "])
@pytest.mark.parametrize(
    "name", ["Nikola Jokic", "Nikola Jokic’s", "Jalen Brunson", "Jalen Brunson's"]
)
def test_summary_name_grammar_is_not_a_typo(lead, name):
    parsed = parse_query(f"{lead}{name} stats in 2023-24")
    assert parsed["route"] == "player_game_summary"
    assert not parsed["route_kwargs"].get("unsupported_filters")


@pytest.mark.parametrize(
    "query",
    [
        "Denver record in the last games scoring at least 114 in 2023-24",
        "Curry stats within his final appearances in 2023-24",
        "Nikola Jokic averages in his final 3 playoff appearances in 2023-24",
        "Nikola Jokic averages in his final three playoff appearances in 2023-24",
        "Nikola Jokic averages in his final 1 playoff appearance in 2023-24",
    ],
)
def test_unresolved_sample_does_not_broaden(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["entity_ambiguity"]


def test_partial_nickname_typo_remains_blocked():
    parsed = parse_query("Average Nikloa Jokic stats in 2023-24")
    assert "unresolved_player" in parsed["route_kwargs"]["unsupported_filters"]


def test_non_sample_appearance_and_final_minutes_meaning_is_preserved():
    assert canonicalize_sample_phrases("jokic final 3 minutes") == "jokic final 3 minutes"
    assert (
        parse_query("How many playoff appearances does Nikola Jokic have?")["route"]
        == "playoff_appearances"
    )
