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
