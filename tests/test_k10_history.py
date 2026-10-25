"""Explicit series questions answer series counts, alongside labeled game counts."""

import pandas as pd
import pytest

from nbatools.commands.structured_results import SummaryResult
from nbatools.query_service import _add_playoff_history_answer_metadata

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    "query", ["Lakers titles from 2000 to 2002", "Cavaliers titles from 2014-15 to 2017-18"]
)
def test_team_title_scope_is_the_postseason(query):
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(query)
    assert parsed["route"] == "playoff_history"
    assert parsed["season_type"] == "Playoffs"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers playoff series record in 2023-24",
        "How many playoff series have the Lakers won in 2023-24?",
    ],
)
def test_single_season_series_record_is_not_presented_as_a_game_record(query):
    # Two completed series (one won, one lost); five wins in eleven games.
    result = SummaryResult(
        summary=pd.DataFrame(
            [
                dict(
                    team_name="Los Angeles Lakers",
                    season_start="2023-24",
                    season_end="2023-24",
                    wins=5,
                    losses=6,
                    series_won=1,
                    series_lost=1,
                )
            ]
        ),
        series=pd.DataFrame(
            [
                dict(
                    playoff_round="First Round",
                    opponent_team_name="One",
                    result="Won",
                    wins=4,
                    losses=2,
                ),
                dict(
                    playoff_round="Second Round",
                    opponent_team_name="Two",
                    result="Lost",
                    wins=1,
                    losses=4,
                ),
            ]
        ),
    )
    meta = dict(route="playoff_history", query_text=query)
    _add_playoff_history_answer_metadata(meta, result)
    assert "1-1 in playoff series" in meta["answer_phrase"]
    assert "5-6 in games" in meta["answer_phrase"]
