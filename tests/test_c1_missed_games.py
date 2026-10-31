"""C1: games a player missed.

"how many games has LeBron missed" counted the games he played (60). It is
his team's games he did not play; on the fixture every player played every
game, so the counts are 0 and the phrase says so.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.mark.parametrize(
    ("query", "team", "player"),
    [
        ("how many games has LeBron missed this season", "LAL", "LeBron James"),
        ("how many games did Tatum miss in 2024-25", "BOS", "Jayson Tatum"),
        ("games LeBron missed", "LAL", "LeBron James"),
        ("how many home games did LeBron miss", "LAL", "LeBron James"),
    ],
)
def test_missed_games_are_team_games_without_him(query, team, player):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "game_finder"
    assert (kwargs["team"], kwargs["without_player"]) == (team, player)
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"][0]["count"] == 0
    assert result.metadata["answer_phrase"].startswith(f"{player} did not miss a")


@pytest.mark.parametrize(
    "query",
    [
        "LeBron missed shots",
        "did LeBron miss the playoffs",
        "LeBron missed free throws",
        # Another player's games, missed stats, records and streaks.
        "Reaves points in games LeBron missed",
        "LeBron stats in games Davis missed",
        "how many free throws did LeBron miss in home games",
        "how many shots did LeBron miss per game",
        "games LeBron missed more than 10 shots",
        "how many games did the Lakers win when LeBron missed",
        "Lakers record in games LeBron missed",
        "how many consecutive games has LeBron missed",
    ],
)
def test_other_misses_are_not_missed_games(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert not any(str(n).startswith("missed_games:") for n in parsed.get("notes") or [])


@pytest.mark.parametrize(
    "query",
    [
        "how many games did LeBron miss in the 2024-25 season",
        "how many games did LeBron miss from 2023-24 to 2025-26",
        "how many games did LeBron miss over the last 3 seasons",
        "number of games LeBron James missed this season",
        "LeBron games missed",
    ],
)
def test_season_wordings_are_missed_games(query):
    parsed = parse_query(query)
    assert any(str(n).startswith("missed_games:") for n in parsed.get("notes") or [])


def test_two_named_seasons_refuse():
    result = execute_natural_query("how many games did LeBron miss in 2024-25 and 2025-26")
    assert result.result_status == "no_result"


@pytest.mark.parametrize(
    "query,start,end",
    [
        (
            "how many games did LeBron James miss from 2025-10-24 to 2025-10-27 in 2025-26",
            "2025-10-24",
            "2025-10-27",
        ),
        (
            "how many home games did LeBron miss between October 24 and October 27 in 2025-26",
            "2025-10-24",
            "2025-10-27",
        ),
        ("number of games LeBron James missed on October 26, 2025", "2025-10-26", "2025-10-26"),
    ],
)
def test_missed_count_preserves_validated_calendar_scope(query, start, end):
    parsed = parse_query(query)
    assert parsed["route"] == "game_finder"
    assert parsed["route_kwargs"]["without_player"] == "LeBron James"
    assert (parsed["route_kwargs"]["start_date"], parsed["route_kwargs"]["end_date"]) == (
        start,
        end,
    )


def test_calendar_mask_keeps_unrelated_stat_clause():
    from nbatools.commands._date_utils import strip_explicit_calendar_date_clauses

    text = strip_explicit_calendar_date_clauses(
        "between October 24 and October 27 and scored 30 points"
    )
    assert "and scored 30 points" in text


@pytest.mark.parametrize(
    "dates",
    [
        "on October 24 or October 27",
        "from October 24 - October 27",
    ],
)
def test_unread_date_list_cannot_become_partial_missed_count(dates):
    parsed = parse_query(f"how many games did LeBron miss {dates} in 2025-26")
    assert parsed["route_kwargs"]["unsupported_filters"] == ["missed_games_extra_clause"]
    result = execute_natural_query(f"how many games did LeBron miss {dates} in 2025-26")
    assert result.result_status == "no_result"
    assert "count" not in result.result.to_dict()["sections"]


def test_calendar_mask_does_not_own_and_without_between():
    from nbatools.commands._date_utils import strip_explicit_calendar_date_clauses

    assert "and" in strip_explicit_calendar_date_clauses("on October 24 and October 27")
    assert "and" not in strip_explicit_calendar_date_clauses("between October 24 and October 27")


@pytest.mark.parametrize(
    "dates",
    [
        "on 2025-10-24 and 2025-10-27",
        "on October 24 and October 27",
        "on 2025-10-24, 2025-10-27",
        "on October 27, October 24 and October 27",
        "on October 24 and October 27,",
    ],
)
def test_explicit_date_set_is_read_once_and_not_as_continuous_range(dates):
    query = f"how many games did LeBron miss {dates} in 2025-26"
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["game_dates"] == ["2025-10-24", "2025-10-27"]
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    assert result.result.to_dict()["sections"]["count"][0]["count"] == 0
    assert "on 2025-10-24, 2025-10-27" in result.metadata["answer_phrase"]
    assert "from 2025-10-24 to" not in result.metadata["answer_phrase"]
    badges = result.metadata["applied_filters"]
    assert {"label": "Dates", "value": "2025-10-24, 2025-10-27", "kind": "date"} in badges
    assert all(f["label"] != "Date range" for f in badges)


@pytest.mark.parametrize(
    "tail",
    [
        "before October",
        "after November",
        "in November",
        "from January to March",
        "since yesterday",
        "and scored 30 points",
        "vs winning teams",
        "if LeBron plays",
        "by season",
    ],
)
def test_date_set_never_overwrites_another_calendar_or_stat_clause(tail):
    query = f"how many games did LeBron miss on 2025-10-24 and 2025-10-27 {tail} in 2025-26"
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata
    assert "count" not in result.result.to_dict()["sections"]


@pytest.mark.parametrize("suffix", ["foo", "stfoo", "-foo"])
def test_partial_date_token_is_not_a_complete_date_set(suffix):
    query = f"how many games did LeBron miss on 2025-10-24 and 2025-10-27{suffix} in 2025-26"
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata
