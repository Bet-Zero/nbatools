"""C1: "beat" and "lose to" count wins and losses against that opponent.

"how many times did the Lakers beat the Celtics" answered "The Boston
Celtics have recorded 60 games" (every Celtics game); "lose to the Celtics"
did the same. Expected counts come from the fixture CSV.
"""

import pytest

from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query


@pytest.mark.fixture_data
def test_beat_and_lose_to_count_wins_and_losses_against_the_opponent():
    import pandas as pd

    games = pd.read_csv(
        "qa/fixtures/query_engine_sample/data/raw/team_game_stats/2025-26_regular_season.csv"
    )
    meetings = games[(games["team_abbr"] == "LAL") & (games["opponent_team_abbr"] == "BOS")]
    wins, losses = int((meetings["wl"] == "W").sum()), int((meetings["wl"] == "L").sum())

    beat = execute_natural_query("how many times did the Lakers beat the Celtics")
    lost = execute_natural_query("how many times did the Lakers lose to the Celtics")
    assert beat.result.to_dict()["sections"]["count"][0]["count"] == wins
    assert lost.result.to_dict()["sections"]["count"][0]["count"] == losses
    assert beat.metadata["count_phrase"].endswith(
        f"have won {wins} games against the Boston Celtics in the 2025-26 regular season."
    )
    assert f"have lost {losses} games against the Boston Celtics" in lost.metadata["count_phrase"]


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "road_only"),
    [
        ("how many times did the Lakers lose", False),
        ("how often do the Lakers lose", False),
        ("how many times did the Lakers lose on the road", True),
    ],
)
def test_did_they_lose_counts_losses(query, road_only):
    import pandas as pd

    games = pd.read_csv(
        "qa/fixtures/query_engine_sample/data/raw/team_game_stats/2025-26_regular_season.csv"
    )
    games = games[games["team_abbr"] == "LAL"]
    if road_only:
        games = games[games["is_home"] == 0]
    losses = int((games["wl"] == "L").sum())
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"][0]["count"] == losses
    assert f"have lost {losses} games" in result.metadata["count_phrase"]
