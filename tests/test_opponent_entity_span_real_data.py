"""Raw-row acceptance for opponent clauses beside punctuation and grouping."""

from functools import wraps

import pytest

from nbatools.commands import team_split_summary
from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    "query,team,opponent,home",
    [
        (
            "Split Denver’s road record against Utah by season: 2023-24 and 2025-26.",
            "DEN",
            "UTA",
            False,
        ),
        (
            "Minnesota record at home against Denver, split into 2025-26 and 2023-24",
            "MIN",
            "DEN",
            True,
        ),
    ],
)
def test_opponent_entity_span_actual_rows(query, team, opponent, home, monkeypatch):
    expected = {}
    for season in ["2023-24", "2025-26"]:
        raw = data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv")
        assert not raw.duplicated(["game_id", "team_id"]).any()
        expected[season] = raw.loc[
            raw.team_abbr.eq(team) & raw.opponent_team_abbr.eq(opponent) & raw.is_home.eq(home)
        ]
        assert not expected[season].empty
    captured = {}
    original = team_split_summary._summarize_bucket

    @wraps(original)
    def capture(frame, bucket):
        captured[bucket] = frame.copy()
        return original(frame, bucket)

    monkeypatch.setattr(team_split_summary, "_summarize_bucket", capture)
    response = execute_natural_query(query)
    assert response.result_status == "ok"
    assert response.route == "team_split_summary"
    assert response.metadata["team"] == team
    assert response.metadata["opponent"] == opponent
    assert set(response.metadata["season_list"]) == set(expected)
    rows = response.result.to_dict()["sections"]["split_comparison"]
    assert {row["bucket"] for row in rows} == set(expected)
    for row in rows:
        season = row["bucket"]
        raw = expected[season]
        actual = captured[season]
        keys = ["game_id", "team_id"]
        assert len(actual) == len(raw)
        assert set(map(tuple, actual[keys].astype(int).to_numpy())) == set(
            map(tuple, raw[keys].astype(int).to_numpy())
        )
        assert row["games"] == len(raw)
        assert row["wins"] == raw.wl.eq("W").sum()
        assert row["losses"] == raw.wl.eq("L").sum()
        for stat in ["pts", "reb", "ast"]:
            assert row[stat + "_avg"] == pytest.approx(raw[stat].mean(), abs=0.001)
