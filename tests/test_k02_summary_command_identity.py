"""Summary command grammar must not enter the full-name typo boundary."""

import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    "prefix", ["Give ", "Give me ", "Show ", "Show me ", "Tell me ", "Please give me ", "Average "]
)
@pytest.mark.parametrize("name", ["Devin Booker's", "Nikola Jokic", "Nikola Jokić's"])
def test_summary_command_preserves_resolved_full_name(prefix, name):
    parsed = parse_query(f"{prefix}{name} averages for the 2023-24 regular season")
    assert parsed["route"] == "player_game_summary"
    assert parsed["player"] in {"Devin Booker", "Nikola Jokic", "Nikola Jokić"}
    assert parsed["route_kwargs"]["season"] == "2023-24"
    assert not parsed["route_kwargs"].get("unsupported_filters")


@pytest.mark.parametrize(
    "prefix", ["Give ", "Give me ", "Show me ", "Tell me ", "Please give me ", "Average "]
)
def test_command_does_not_erase_misspelled_given_name(prefix):
    parsed = parse_query(f"{prefix}Nikloa Jokic averages in 2023-24")
    assert "unresolved_player" in parsed["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize(
    "query",
    [
        "Show me Devin Booker games with at least 30 points in 2023-24",
        "Show games where Nikola Jokic had 10 assists in 2023-24",
        "List Nikola Jokic games with at least 30 points in 2023-24",
    ],
)
def test_explicit_game_lists_retain_their_grain(query):
    parsed = parse_query(query)
    assert parsed["route"] == "player_game_finder"
    assert not parsed["route_kwargs"].get("unsupported_filters")
