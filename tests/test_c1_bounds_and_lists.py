"""Upper bounds, season spans after a threshold, and lists on summaries.

"at most 5 points" is an upper bound (it was read as 5+), "how many players
had under 10 points and 10 rebounds" counts players (it counted games),
"5 assists between 2023 and 2025" is a season span (it was an assist range),
and summaries apply every condition in a list. Expected values are counted
from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _count(result) -> int:
    return result.result.to_dict()["sections"]["count"][0]["count"]


@pytest.mark.parametrize(
    ("query", "expected", "phrase"),
    [
        ("how many players have had at most 5 points this season", 24, "at most 5 points"),
        ("how many players had 5 points or fewer this season", 24, "at most 5 points"),
        ("how many players scored under 10 points this season", 29, "under 10 points"),
        (
            "how many players have had under 10 points and 10 rebounds this season",
            12,
            "under 10 points and 10+ rebounds",
        ),
    ],
)
def test_upper_bound_player_counts(query, expected, phrase):
    result = _run(query)
    assert result.route == "player_occurrence_leaders"
    assert _count(result) == expected
    assert f"{expected} players have had a game with {phrase}" in result.metadata["count_phrase"]


def test_years_after_a_threshold_are_seasons():
    result = _run("how many games has LeBron James had 5 assists between 2023 and 2025")
    assert _count(result) == 166
    assert result.metadata["count_phrase"].startswith(
        "LeBron James has had 166 games with 5+ assists from 2023-24 to 2025-26"
    )


@pytest.mark.parametrize(
    ("query", "games"),
    [
        ("LeBron James between 20 and 30 points and 5 assists since 2023", 97),
        ("LeBron James summary with 30 points and 10 rebounds since 2023", 7),
    ],
)
def test_summaries_apply_every_condition(query, games):
    result = _run(query)
    assert result.route == "player_game_summary"
    assert result.result.to_dict()["sections"]["summary"][0]["games"] == games


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # "N STAT or fewer" is a maximum; the occurrence reading also kept N as
        # a minimum, leaving only games with exactly N.
        ("how many games did LeBron James have 20 points or fewer", 18),
        ("how many games did Jokic have 2 turnovers or less", 29),
        # A verb-led number followed by "or fewer" is the same maximum.
        ("how many games did LeBron score 20 or fewer points", 18),
        # "or less than" joins two conditions with "or".
        ("how many games did Jokic have over 30 points or less than 2 turnovers", 24),
        ("how many games did LeBron have 30+ points or less than 5 assists", 14),
        ("how many games did LeBron have 30 points or less or 10 assists", 54),
    ],
)
def test_or_fewer_upper_bounds(query, expected):
    assert _count(_run(query)) == expected


def test_or_fewer_on_summaries_and_leaderboards():
    summary = _run("LeBron summary in games with 20 points or fewer")
    assert summary.result.to_dict()["sections"]["summary"][0]["games"] == 18

    leaders = _run("who has the most games with 20 points or fewer")
    top = leaders.result.to_dict()["sections"]["leaderboard"][0]
    assert top["games_pts_20_or_fewer"] == 60


@pytest.mark.parametrize(
    ("query", "games", "wins", "losses"),
    [
        ("Lakers record when scoring 110 or fewer points", 32, 21, 11),
        ("Lakers record when scoring at most 110", 32, 21, 11),
        # Points allowed, not the Lakers' own points.
        ("Lakers record when holding opponents to 100 points or fewer", 43, 41, 2),
        ("Lakers record when allowing at most 100 points", 43, 41, 2),
        ("Lakers record when opponents score at most 100 points", 43, 41, 2),
        ("Lakers record when they held opponents to 100 or fewer points", 43, 41, 2),
    ],
)
def test_team_record_upper_bounds(query, games, wins, losses):
    result = _run(query)
    assert result.route == "team_record"
    row = result.result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (games, wins, losses)


def test_allowed_count_uses_opponent_points():
    assert _count(_run("how many games did the Lakers allow 100 or fewer points")) == 43


@pytest.mark.parametrize(
    "query",
    [
        # Margins, percentages, rest and plus-minus bounds have no parse yet;
        # they refuse rather than return an unfiltered answer.
        "Celtics record in games decided by 5 or less",
        "Celtics record in games decided by 5 points or fewer",
        "Celtics record when they win by 10 or fewer",
        "LeBron record on 1 day of rest or less",
        "LeBron games shooting 40% or less",
        "LeBron games with a plus minus of 0 or less",
        "Lakers record when opponents shoot 40% or less",
        # One bound per player is not applied separately.
        "Lakers record when Luka scores 20 or less and LeBron scores 20 or less",
        # A route that never receives the bound.
        "which players had 5 or fewer points in most games",
    ],
)
def test_unapplied_upper_bounds_refuse(query):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


def test_made_threes_and_teams_that_scored():
    assert _count(_run("how many games did LeBron have 3 or fewer made threes")) == 42
    row = _run("Lakers record vs teams that scored 100 or fewer").result.to_dict()
    summary = row["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"]) == (43, 41, 2)
