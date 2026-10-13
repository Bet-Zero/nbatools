"""One-possession games on real rows: a final margin of 3 or fewer.

Expected values come from the raw team and player rows, with each margin
taken from the two teams' points (the stored team plus_minus disagrees with
the score in 9 to 20 games a season in 2021-22 to 2023-24).
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _margins(season: str) -> pd.DataFrame:
    team = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
    opp = team[["game_id", "team_id", "pts"]].rename(
        columns={"team_id": "opp_id", "pts": "opp_pts"}
    )
    rows = team.merge(opp, on="game_id")
    rows = rows[rows["team_id"] != rows["opp_id"]].copy()
    rows["margin"] = rows["pts"] - rows["opp_pts"]
    return rows


def _close(team: str, season: str) -> pd.DataFrame:
    rows = _margins(season)
    return rows[(rows["team_abbr"] == team) & (rows["margin"].abs() <= 3)]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    ("team", "name", "season"),
    [
        ("LAL", "Lakers", "2021-22"),
        ("BOS", "Celtics", "2022-23"),
        ("LAL", "Lakers", "2023-24"),
        ("BOS", "Celtics", "2025-26"),
    ],
)
def test_team_record_in_one_possession_games(team, name, season):
    close = _close(team, season)
    row = _execute(f"{name} record in one possession games in {season}")["summary"][0]
    assert row["games"] == len(close)
    assert (row["wins"], row["losses"]) == (
        int((close["margin"] > 0).sum()),
        int((close["margin"] < 0).sum()),
    )


def test_stored_plus_minus_disagreements_do_not_change_the_sample():
    # 2022-23 holds games whose stored plus_minus is not the score's margin;
    # the list is every Celtics game decided by 3 or fewer.
    close = _close("BOS", "2022-23")
    rows = _execute("Celtics one-possession wins in 2022-23")["finder"]
    assert sorted(r["game_id"] for r in rows) == sorted(close[close["margin"] > 0]["game_id"])


def test_player_summary_in_one_possession_games():
    close = _close("LAL", "2023-24")
    players = data_read_csv("data/raw/player_game_stats/2023-24_regular_season.csv")
    lebron = players[
        (players["player_name"] == "LeBron James")
        & players["game_id"].isin(close["game_id"])
        & (players["team_abbr"] == "LAL")
    ]
    row = _execute("LeBron James stats in one possession games in 2023-24")["summary"][0]
    assert row["games"] == len(lebron)
    assert row["pts_avg"] == pytest.approx(lebron["pts"].mean(), abs=1e-3)


@pytest.mark.parametrize("season", ["2024-25", "2025-26"])
def test_served_schedule_context_one_possession_matches_the_score(season):
    context = data_read_csv(f"data/processed/schedule_context_features/{season}_regular_season.csv")
    rows = _margins(season)[["game_id", "team_id", "margin"]]
    merged = context.merge(rows, on=["game_id", "team_id"], validate="one_to_one")
    assert len(merged) == len(context)
    assert (merged["one_possession"] == merged["margin"].abs().le(3).astype(int)).all()
