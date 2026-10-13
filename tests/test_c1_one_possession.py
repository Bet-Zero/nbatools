"""One-possession games read the final score.

"Lakers record in one possession games", "Lakers one possession wins" and
"LeBron stats in one possession games" read a schedule-context flag that the
served data carries for two seasons, on two routes; elsewhere they refused.
They now read a final margin of 3 or fewer from the score, like "close games"
(5 or fewer) and "decided by 3 or fewer".

Expected values are counted with pandas from the fixture's raw rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

_RAW = Path(__file__).resolve().parents[1] / "qa/fixtures/query_engine_sample/data/raw"


def _margins(season: str) -> pd.DataFrame:
    team = pd.read_csv(_RAW / f"team_game_stats/{season}_regular_season.csv")
    opp = team[["game_id", "team_abbr", "pts"]].rename(
        columns={"team_abbr": "opp_abbr", "pts": "opp_pts"}
    )
    rows = team.merge(opp, on="game_id")
    rows = rows[rows["team_abbr"] != rows["opp_abbr"]].copy()
    rows["margin"] = rows["pts"] - rows["opp_pts"]
    return rows


def _close(team: str, season: str = "2025-26") -> pd.DataFrame:
    rows = _margins(season)
    return rows[(rows["team_abbr"] == team) & (rows["margin"].abs() <= 3)]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _bound(query: str) -> tuple:
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(query)
    assert parsed["one_possession"] is False
    kwargs = parsed["route_kwargs"]
    found = {(c["stat"], c["min_value"], c["max_value"]) for c in kwargs.get("conditions") or []}
    if kwargs.get("stat"):
        found.add((kwargs["stat"], kwargs.get("min_value"), kwargs.get("max_value")))
    return found


@pytest.mark.parametrize(
    ("query", "bound"),
    [
        ("Lakers record in one possession games", ("margin", None, 3.0)),
        ("Lakers record in one-possession games", ("margin", None, 3.0)),
        ("Celtics one-possession record", ("margin", None, 3.0)),
        ("Lakers record in games within one possession", ("margin", None, 3.0)),
        ("Lakers record in games decided within one possession", ("margin", None, 3.0)),
        ("LeBron James stats in one possession games", ("margin", None, 3.0)),
        ("Lakers one possession wins", ("win_margin", None, 3.0)),
        ("Lakers one-possession losses", ("loss_margin", None, 3.0)),
    ],
)
def test_one_possession_is_a_margin_of_three_or_fewer(query, bound):
    assert bound in _bound(query)


@pytest.mark.parametrize(
    ("query", "team", "season"),
    [
        ("Lakers record in one possession games", "LAL", "2025-26"),
        ("Celtics one-possession record", "BOS", "2025-26"),
        ("Celtics record in one possession games in 2024-25", "BOS", "2024-25"),
        ("Lakers record in one-possession games in 2023-24", "LAL", "2023-24"),
    ],
)
def test_team_records(query, team, season):
    close = _close(team, season)
    row = _execute(query).result.to_dict()["sections"]["summary"][0]
    assert row["games"] == len(close)
    assert (row["wins"], row["losses"]) == (
        int((close["margin"] > 0).sum()),
        int((close["margin"] < 0).sum()),
    )
    assert row["pts_avg"] == pytest.approx(close["pts"].mean(), abs=1e-3)


def test_team_game_list_and_win_count():
    close = _close("LAL")
    finder = _execute("Lakers games in one possession games").result.to_dict()["sections"]
    assert sorted(r["game_id"] for r in finder["finder"]) == sorted(close["game_id"])
    wins = _execute("how many one possession games did the Lakers win")
    rows = wins.result.to_dict()["sections"]["finder"]
    assert sorted(r["game_id"] for r in rows) == sorted(close[close["margin"] > 0]["game_id"])
    losses = _execute("Lakers one-possession losses").result.to_dict()["sections"]["finder"]
    assert sorted(r["game_id"] for r in losses) == sorted(close[close["margin"] < 0]["game_id"])


def test_player_summary():
    close = _close("LAL")
    players = pd.read_csv(_RAW / "player_game_stats/2025-26_regular_season.csv")
    lebron = players[
        (players["player_name"] == "LeBron James") & players["game_id"].isin(close["game_id"])
    ]
    row = _execute("LeBron James stats in one possession games").result.to_dict()["sections"][
        "summary"
    ][0]
    assert row["games"] == len(lebron)
    assert row["pts_avg"] == pytest.approx(lebron["pts"].mean(), abs=1e-3)


def test_team_comparison_reads_each_teams_close_games():
    sections = _execute("Lakers vs Celtics in one possession games").result.to_dict()["sections"]
    games = {row["team_name"]: row["games"] for row in sections["summary"]}
    assert games == {"LAL": len(_close("LAL")), "BOS": len(_close("BOS"))}


def test_bare_within_one_possession_keeps_its_reading():
    # "within one possession in the final minute" is an in-game state, not a
    # final margin; it keeps the schedule-context reading (and its refusal).
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query("Lakers record when within one possession in the final minute")
    assert parsed["one_possession"] is True
