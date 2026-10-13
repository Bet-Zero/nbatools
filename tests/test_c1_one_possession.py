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


@pytest.mark.parametrize(
    ("query", "kept"),
    [
        ("Lakers record excluding one possession games", lambda m: m.abs() >= 4),
        ("Lakers record in non-one-possession games", lambda m: m.abs() >= 4),
        ("Lakers record outside of one possession games", lambda m: m.abs() >= 4),
        ("Lakers record excluding close games", lambda m: m.abs() >= 6),
        ("Lakers record in non-close games", lambda m: m.abs() >= 6),
        ("Lakers record excluding blowouts", lambda m: m.abs() <= 14),
        ("Lakers record in non-blowout games", lambda m: m.abs() <= 14),
    ],
)
def test_excluded_margins_keep_the_other_games(query, kept):
    # These read as the excluded games themselves.
    rows = _margins("2025-26")
    rows = rows[rows["team_abbr"] == "LAL"]
    rows = rows[kept(rows["margin"])]
    row = _execute(query).result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (
        len(rows),
        int((rows["margin"] > 0).sum()),
        int((rows["margin"] < 0).sum()),
    )


@pytest.mark.parametrize(
    "query",
    [
        # The team after "to" reads as the subject; the flag's refusal stays.
        "Lakers one possession losses to the Celtics",
        "Lakers one possession games to the Celtics",
        # A score during the game, not the final margin.
        "Lakers record in games within one possession in the final minute",
        "Lakers record in one possession games in the 4th quarter",
        "Lakers record in games within one possession in the 4th",
        "Lakers record in games within one possession down the stretch",
        "Lakers record in games within one possession entering the fourth",
        "Lakers record in games within one possession after three",
        "Lakers record in one possession games in the final period",
        # Two margins compared.
        "Lakers one possession games vs close games",
        "Lakers close games vs one possession games",
    ],
)
def test_unread_one_possession_wordings_keep_their_refusal(query):
    from nbatools.commands.natural_query import parse_query
    from nbatools.query_service import execute_natural_query

    assert parse_query(query)["one_possession"] is True
    assert execute_natural_query(query).result_status == "no_result"


def test_one_possession_games_against_a_team():
    close = _close("LAL")
    close = close[close["opp_abbr"] == "BOS"]
    rows = _execute("Lakers one possession games vs the Celtics").result.to_dict()["sections"]
    assert sorted(r["game_id"] for r in rows["finder"]) == sorted(close["game_id"])


def test_two_excluded_margins_keep_their_reading():
    # "excluding close games and blowouts" is not one excluded margin; it
    # keeps the reading it had (no game is both).
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Lakers record excluding close games and blowouts")
    assert result.result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "pick"),
    [
        (
            "Lakers one possession wins over the Celtics",
            lambda r: (r["opp_abbr"] == "BOS") & (r["margin"] > 0),
        ),
        (
            "Lakers one possession wins against the Celtics",
            lambda r: (r["opp_abbr"] == "BOS") & (r["margin"] > 0),
        ),
        (
            "Lakers one-possession losses vs the Celtics",
            lambda r: (r["opp_abbr"] == "BOS") & (r["margin"] < 0),
        ),
        ("Lakers one possession wins at home", lambda r: (r["is_home"] == 1) & (r["margin"] > 0)),
        (
            "Lakers one possession losses at home this season",
            lambda r: (r["is_home"] == 1) & (r["margin"] < 0),
        ),
    ],
)
def test_one_possession_outcomes_with_opponent_or_venue(query, pick):
    close = _close("LAL")
    expected = close[pick(close)]
    rows = _execute(query).result.to_dict()["sections"]["finder"]
    assert sorted(r["game_id"] for r in rows) == sorted(expected["game_id"])


def test_one_possession_record_over_a_season_span():
    row = _execute(
        "Lakers record in one possession games from 2023-24 to 2025-26"
    ).result.to_dict()["sections"]["summary"][0]
    close = pd.concat([_close("LAL", s) for s in ("2023-24", "2024-25", "2025-26")])
    assert (row["games"], row["wins"], row["losses"]) == (
        len(close),
        int((close["margin"] > 0).sum()),
        int((close["margin"] < 0).sum()),
    )
