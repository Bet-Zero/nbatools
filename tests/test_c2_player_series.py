"""C2: a player's playoff series record.

"LeBron playoff series record", "how many playoff series has LeBron won" and
"LeBron series wins" refused (player rows carry no series). They now count the
series his teams played in which he appeared, from the team playoff rows.
Expected values come from the fixture CSVs (2025-26 playoffs: LAL vs DEN).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _team_series(team: str) -> tuple[int, int]:
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_playoffs.csv")
    games = games[games["team_abbr"] == team]
    return int((games["wl"] == "W").sum()), int((games["wl"] == "L").sum())


@pytest.mark.parametrize(
    "query",
    [
        "LeBron playoff series record",
        "how many playoff series has LeBron won",
        "LeBron series wins",
        "how many series has LeBron won against the Nuggets",
    ],
)
def test_lebron_series_record(query):
    wins, losses = _team_series("LAL")
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["series_won"], summary["series_lost"]) == (1, 0)
    assert (summary["wins"], summary["losses"]) == (wins, losses)
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith("LeBron James won 1 of 1 playoff series")
    assert f"({wins}-{losses} in those games)" in phrase


def test_jokic_lost_series_and_round():
    wins, losses = _team_series("DEN")
    result = execute_natural_query("Jokic playoff series record")
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["series_won"], summary["series_lost"]) == (0, 1)
    phrase = execute_natural_query("LeBron first round series record").metadata["answer_phrase"]
    assert "won 1 of 1 first round series" in phrase
    assert (
        f"Nikola Jokić won 0 of 1 playoff series in 2025-26 ({wins}-{losses}"
        in (result.metadata["answer_phrase"])
    )


def test_series_record_spans_every_playoff_season():
    kwargs = parse_query("LeBron playoff series record")["route_kwargs"]
    assert kwargs["player"] == "LeBron James"
    assert kwargs["start_season"] == "1996-97" and kwargs["season"] is None


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("Lakers season series record vs Celtics", "team_record"),
        ("LeBron record when up 3-1 in a series", "player_game_summary"),
    ],
)
def test_other_series_readings_keep_their_routes(query, route):
    assert parse_query(query)["route"] == route


@pytest.mark.parametrize(
    ("query", "blocked"),
    [
        # A second player would be dropped from one player's series.
        ("LeBron and Curry playoff series record", "multi_player_series"),
        ("LeBron and Jokic series wins", "multi_player_series"),
        # A game condition has no series meaning; dropping it answers the
        # whole record (and "when LeBron scores" swapped the Lakers for him).
        ("LeBron playoff series record when scoring 30", "series_game_condition"),
        (
            "how many playoff series have the Lakers won when LeBron scores 30",
            "series_game_condition",
        ),
        ("Lakers playoff series record when scoring 120", "series_game_condition"),
    ],
)
def test_series_record_refuses_rather_than_drop_a_clause(query, blocked):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
    assert any(f"blocked: {blocked}" in note for note in result.metadata["notes"])
