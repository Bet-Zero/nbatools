"""Player clauses inside a team-record sample.

- "Lakers record when LeBron plays and scores 30" checked 30 points against
  the team's points and answered with the whole record.
- "when Luka sits" was not read as absence at all.
- "in games LeBron plays 35 minutes and Luka plays 35 minutes" dropped Luka.
- "and the Lakers play at home" after a minutes bound counted as a second
  player and refused.
- "below 3 turnovers" was read as a floor, and "... but loses" was ignored.

Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query)


def _record(query: str) -> tuple[int, int, int]:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"], summary["games"]


def _rows(query: str) -> list[dict]:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when LeBron James plays and scores at least 30 points", (10, 1, 11)),
        ("Lakers record when LeBron James plays and has 10 assists", (6, 0, 6)),
        (
            "Lakers record when LeBron James plays at least 35 minutes and the Lakers play at home",
            (2, 0, 2),
        ),
        ("Lakers record when LeBron James plays at least 35 minutes but loses", (0, 1, 1)),
        ("Lakers record when LeBron James scores 30 but they lose", (0, 1, 1)),
        ("Lakers record in games with not under 120 points", (18, 1, 19)),
    ],
)
def test_player_clause_is_applied(query, record):
    assert _record(query) == record


def test_plays_and_scores_matches_scores():
    assert _record("Lakers record when LeBron James plays and scores at least 30 points") == (
        _record("Lakers record when LeBron James scores at least 30 points")
    )


@pytest.mark.parametrize(
    "query",
    [
        # Luka played every fixture game, so his absence leaves no games.
        "Lakers record when Luka Doncic sits",
        "Lakers record when Luka Doncic rests",
    ],
)
def test_sits_is_absence(query):
    result = _execute(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record in games LeBron James plays at least 35 minutes and Luka Doncic plays "
        "at least 35 minutes",
        # A second player the resolver can't name still isn't dropped.
        "Lakers record when LeBron James plays 35 minutes and Davis sits",
        "Lakers record when LeBron James plays and scores 30 points and Davis sits",
        "Lakers record when LeBron James plays and scores 30 points while Davis rests",
        "Lakers record when LeBron James plays and scores 30 points while Davis is out",
        # The first player's own stat can't be checked on team rows.
        "Lakers record when LeBron James plays and scores 30 points and Davis plays",
        "Lakers record when LeBron James plays and has 10 assists and Anthony Davis plays",
        "Lakers record when LeBron James plays and scores 30 points and the starters play 30 "
        "minutes",
    ],
)
def test_second_player_clause_refuses(query):
    result = _execute(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


def test_supported_mixed_clauses_have_a_qualified_empty_fixture_population():
    import pandas as pd

    from nbatools.data_source import data_read_csv

    # Positive canonical appearances cover every candidate. That makes Luka's
    # absence false in all games; missing rows are never used as DNP evidence.
    teams = data_read_csv("data/raw/team_game_stats/2025-26_regular_season.csv")
    candidates = teams.loc[teams.team_id.eq(1610612747)]
    players = data_read_csv("data/raw/player_game_stats/2025-26_regular_season.csv")
    own = players.loc[players.team_id.eq(1610612747) & pd.to_numeric(players.minutes).gt(0)]
    games = set(candidates.game_id)
    assert games and len(games) == len(candidates)
    luka = own.loc[own.player_id.eq(1629029)]
    lebron = own.loc[own.player_id.eq(2544)]
    assert set(luka.game_id) == games
    assert set(lebron.game_id).intersection(games)
    assert not luka.duplicated(["game_id", "team_id", "player_id"]).any()
    for row in luka.itertuples():
        assert pd.Timestamp(row.game_date) == pd.Timestamp(
            candidates.loc[candidates.game_id.eq(row.game_id), "game_date"].item()
        )
    result = _execute("Lakers record when LeBron James plays and Luka Doncic sits")
    assert result.route == "team_record" and result.metadata["team"] == "LAL"
    assert result.metadata["player"] is None
    assert result.metadata["with_player"] == "LeBron James"
    assert result.metadata["without_player"] == "Luka Dončić"
    assert not result.metadata["unsupported_filters"]
    assert result.result_status == "no_result" and result.result_reason == "no_match"
    assert not result.result.to_dict()["sections"]


def test_below_is_a_ceiling():
    assert _rows("LeBron James games with below 3 turnovers") == _rows(
        "LeBron James games with at most 2 turnovers"
    )
    assert _rows("LeBron James games with 30 points and below 3 turnovers") == _rows(
        "LeBron James games with 30 points and at most 2 turnovers"
    )


def test_team_sitting_is_not_an_absence():
    # "they sit atop the standings" names no player; the record is unfiltered.
    assert _record("Lakers record when they sit atop the standings") == (47, 13, 60)


@pytest.mark.parametrize(
    ("query", "record"),
    [
        (
            "Lakers record when LeBron James plays and grabs 10 rebounds and the defense plays "
            "well",
            (11, 2, 13),
        ),
        ("Lakers record when LeBron James plays and scores 30 points and LA plays", (10, 1, 11)),
        (
            "Lakers record when LeBron James plays and scores 30 points and the Lakers play at home",
            (4, 1, 5),
        ),
        # A team stat beside presence still filters team rows.
        ("Lakers record with LeBron James in games with 120 points", (18, 1, 19)),
    ],
)
def test_team_subjects_are_not_second_players(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # Plural verbs, "as a team" and totals no player reaches are team stats.
        ("Lakers record when LeBron James plays and records 30 assists as a team", (3, 2, 5)),
        ("Lakers record when LeBron James plays and record 30 assists", (3, 2, 5)),
        ("Lakers record when LeBron James plays and score 120 points", (18, 1, 19)),
        ("Lakers record when LeBron James plays and scores 120 points", (18, 1, 19)),
        ("Lakers record when LeBron James plays and makes 15 threes", (18, 2, 20)),
        # A setting between "plays" and the player's own stat.
        ("Lakers record when LeBron James plays at home and scores 30 points", (4, 1, 5)),
    ],
)
def test_team_stat_clause_after_presence(query, record):
    assert _record(query) == record


def test_later_player_own_stat_beside_presence_refuses():
    result = _execute(
        "Lakers record when Luka Doncic plays and LeBron James plays and has 10 assists"
    )
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
