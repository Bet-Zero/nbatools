"""C1: a team's point differential and "best" boards of a team's players.

"Lakers point differential" ranked team games by points; "who has the best
plus minus on the Lakers" and "who has the highest ppg on the Lakers" listed
team games or summarized the team. Expectations come from the fixture rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _team_margins(season: str = "2025-26") -> pd.DataFrame:
    games = pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv")
    opp = games[["game_id", "team_abbr", "pts"]].rename(
        columns={"team_abbr": "opp_abbr", "pts": "opp_pts"}
    )
    merged = games.merge(opp, on="game_id")
    merged = merged[merged["team_abbr"] != merged["opp_abbr"]].copy()
    merged["margin"] = merged["pts"] - merged["opp_pts"]
    return merged


@pytest.mark.parametrize(
    ("query", "team", "home"),
    [
        ("Lakers point differential", "LAL", None),
        ("what is the Lakers point differential", "LAL", None),
        ("Lakers scoring margin", "LAL", None),
        ("Lakers average margin", "LAL", None),
        ("Lakers point differential at home", "LAL", 1),
        ("Celtics point differential", "BOS", None),
    ],
)
def test_team_point_differential_is_the_average_margin(query, team, home):
    games = _team_margins()
    games = games[games["team_abbr"] == team]
    if home is not None:
        games = games[games["is_home"] == home]
    result = execute_natural_query(query)
    assert result.route == "game_summary"
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["plus_minus_avg"] == pytest.approx(games["margin"].mean(), abs=1e-3)
    wins, losses = int((games["wl"] == "W").sum()), int((games["wl"] == "L").sum())
    margin = games["margin"].mean()
    assert result.metadata["answer_phrase"].endswith(
        f"are {wins}-{losses} in {len(games)} games, outscoring opponents by "
        f"{margin:.1f} points per game."
    )


@pytest.mark.parametrize("query", ["Lakers net points", "Lakers point differential vs the Celtics"])
def test_other_differential_wording(query):
    games = _team_margins()
    games = games[games["team_abbr"] == "LAL"]
    if "Celtics" in query:
        games = games[games["opp_abbr"] == "BOS"]
    result = execute_natural_query(query)
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["plus_minus_avg"] == pytest.approx(games["margin"].mean(), abs=1e-3)
    margin = games["margin"].mean()
    words = "outscoring opponents by" if margin > 0 else "outscored by"
    assert f"{words} {abs(margin):.1f} points per game." in result.metadata["answer_phrase"]


def test_point_differential_over_the_last_10_games():
    games = _team_margins()
    games = games[games["team_abbr"] == "LAL"].sort_values(["game_date", "game_id"]).tail(10)
    result = execute_natural_query("Lakers point differential last 10 games")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["games"] == 10
    assert row["plus_minus_avg"] == pytest.approx(games["margin"].mean(), abs=1e-3)


def test_point_differential_over_a_span():
    games = pd.concat([_team_margins(s) for s in ("2024-25", "2025-26")])
    games = games[games["team_abbr"] == "BOS"]
    result = execute_natural_query("Celtics point differential since 2024")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["plus_minus_avg"] == pytest.approx(games["margin"].mean(), abs=1e-3)


@pytest.mark.parametrize(
    ("query", "route"),
    [
        # A threshold or a ranking keeps the game reading.
        ("Lakers games with a point differential over 20", "game_finder"),
        ("Lakers biggest point differential", "game_finder"),
        # The league board of teams.
        ("which team has the best point differential", "season_team_leaders"),
    ],
)
def test_point_differential_games_and_boards(query, route):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert parsed["route_kwargs"]["stat"] == "plus_minus"


def test_team_season_boards_keep_point_differential():
    parsed = parse_query("best point differential seasons ever")
    assert (parsed["route"], parsed["route_kwargs"]["stat"]) == (
        "season_team_leaders",
        "plus_minus_per_game",
    )
    assert parse_query("Lakers average margin of victory")["route_kwargs"].get("stat") is None


def _player_board(team: str, stat: str) -> pd.Series:
    rows = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    rows = rows[rows["team_abbr"] == team]
    return rows.groupby("player_name")[stat].mean().sort_values(ascending=False)


@pytest.mark.parametrize(
    ("query", "team", "stat", "column", "limit"),
    [
        ("who has the best plus minus on the Lakers", "LAL", "plus_minus", "plus_minus", 10),
        ("best plus minus on the Lakers", "LAL", "plus_minus", "plus_minus", 10),
        ("which Laker has the best plus minus", "LAL", "plus_minus", "plus_minus", 10),
        ("Lakers player with the best plus minus", "LAL", "plus_minus", "plus_minus", 10),
        (
            "who has the best plus minus on the Celtics this season",
            "BOS",
            "plus_minus",
            "plus_minus",
            10,
        ),
        ("who has the highest ppg on the Lakers", "LAL", "pts", "pts", 10),
        ("top 3 Lakers players in rebounds", "LAL", "reb", "reb", 3),
    ],
)
def test_best_on_a_team_is_a_board_of_its_players(query, team, stat, column, limit):
    expected = _player_board(team, column).head(limit)
    result = execute_natural_query(query)
    assert result.route == "season_leaders"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert [r["player_name"] for r in rows] == list(expected.index)
    assert [r[f"{stat}_per_game"] for r in rows] == pytest.approx(list(expected.values))


def test_highest_scoring_game_by_a_teams_player_is_one_game():
    rows = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    rows = rows[rows["team_abbr"] == "LAL"]
    result = execute_natural_query("which Lakers player had the highest scoring game")
    assert result.route == "player_game_finder"
    got = [r["pts"] for r in result.result.to_dict()["sections"]["finder"]]
    assert got == rows["pts"].nlargest(len(got)).tolist()


@pytest.mark.parametrize(
    "query",
    [
        "who had the best game on the Lakers",
        "who has the fewest turnovers on the Lakers",
        "who has the best turnover numbers on the Lakers",
        "Lakers best plus minus game",
        "Lakers top scoring games",
        "best scoring season by a Lakers player",
    ],
)
def test_other_best_wording_keeps_its_reading(query):
    assert parse_query(query)["route"] != "season_leaders"


@pytest.mark.parametrize(
    "query",
    [
        # Filters the board would drop keep their earlier reading (refusals
        # stay refusals).
        "who has the best plus minus on the Lakers in the clutch",
        "who has the highest ppg on the Lakers in the 4th quarter",
        "who has the best plus minus on the Lakers without LeBron",
        "who has the highest ppg on the Lakers on national tv",
        "who has the best plus minus on the Lakers in close games",
        "who has the best plus minus on the Lakers last 10 games",
    ],
)
def test_best_boards_never_drop_a_filter(query):
    assert parse_query(query)["route"] != "season_leaders"


@pytest.mark.parametrize(
    "query",
    [
        "best point differential in the league",
        "who has the best point differential",
        "point differential leaders",
        "scoring margin leaders",
    ],
)
def test_a_league_point_differential_board_ranks_teams(query):
    games = _team_margins()
    expected = games.groupby("team_abbr")["margin"].mean().sort_values(ascending=False)
    result = execute_natural_query(query)
    assert result.route == "season_team_leaders"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert [r["team_abbr"] for r in rows] == list(expected.index)[: len(rows)]


def test_scoring_margin_seasons_are_team_seasons():
    parsed = parse_query("best scoring margin seasons ever")
    assert (parsed["route"], parsed["route_kwargs"].get("per_season")) == (
        "season_team_leaders",
        True,
    )


def test_point_differential_groupings_are_not_one_summary():
    for query in ("Lakers point differential by season", "Lakers point differential rank"):
        assert parse_query(query)["route"] != "game_summary"
    assert parse_query("Lakers net points per game")["route_kwargs"]["stat"] == "plus_minus"


@pytest.mark.parametrize(
    ("query", "ascending"),
    [
        ("best point differential ever", None),
        ("best point differential of all time", None),
        ("best scoring margin ever", None),
        ("worst point differential ever", True),
    ],
)
def test_point_differential_ever_is_team_seasons(query, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_team_leaders"
    assert (kwargs["stat"], kwargs["per_season"], kwargs.get("ascending")) == (
        "plus_minus_per_game",
        True,
        ascending,
    )
    assert execute_natural_query(query).result_status == "ok"


@pytest.mark.parametrize(
    "query",
    [
        # The team-season board does not apply these filters: refuse rather
        # than drop them or rank players.
        "best point differential ever at home",
        "best point differential ever vs the Celtics",
        "best point differential ever in losses",
        "best point differential ever last 10 games",
        "best point differential seasons ever at home",
        "best point differential seasons ever against the Celtics",
    ],
)
def test_filtered_team_season_point_differential_refuses(query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("Lakers point differential from January to March", "2026-01-01", "2026-03-31"),
        ("Lakers point differential in the month of March", "2026-03-01", "2026-03-31"),
        ("Lakers point differential for the month of March", "2026-03-01", "2026-03-31"),
        ("Lakers point differential in March and April", "2026-03-01", "2026-04-30"),
    ],
)
def test_point_differential_over_a_month_window(query, start, end):
    games = _team_margins()
    games = games[
        (games["team_abbr"] == "LAL") & (games["game_date"] >= start) & (games["game_date"] <= end)
    ]
    row = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert row["games"] == len(games)
    assert row["plus_minus_avg"] == pytest.approx(games["margin"].mean(), abs=1e-3)


@pytest.mark.parametrize(
    "query",
    [
        # Windows the dates do not read refuse rather than answer the season.
        "Lakers point differential in March vs April",
        "Lakers point differential after Christmas",
        "Lakers point differential before the All-Star break",
    ],
)
def test_point_differential_over_an_unread_window_refuses(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_team_player_board_over_a_month_range():
    rows = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    rows = rows[
        (rows["team_abbr"] == "LAL")
        & (rows["game_date"] >= "2026-01-01")
        & (rows["game_date"] <= "2026-03-31")
    ]
    expected = rows.groupby("player_name")["plus_minus"].mean().sort_values(ascending=False)
    result = execute_natural_query(
        "who has the best plus minus on the Lakers from January to March"
    )
    board = result.result.to_dict()["sections"]["leaderboard"]
    assert [r["player_name"] for r in board] == list(expected.index)[: len(board)]
    assert [r["plus_minus_per_game"] for r in board] == pytest.approx(
        list(expected.values)[: len(board)]
    )


@pytest.mark.parametrize(
    "query",
    [
        # A window the dates did not read: the season answer would claim it.
        "Lakers point differential this month",
        "Lakers point differential until March",
        "Lakers point differential over the last two months",
        "Lakers point differential in the 2025 calendar year",
        "who has the best plus minus on the Lakers until March",
        "who has the most points on the Lakers until March",
        "which Laker has the most 30 point games this month",
        "which team has the best point differential until March",
    ],
)
def test_unread_windows_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers point differential last month",
        "who has the most assists on the Lakers last month",
        "who has the most rebounds on the Lakers in March",
    ],
)
def test_read_windows_still_answer(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("start_date") and kwargs.get("end_date")
    assert execute_natural_query(query).result_status == "ok"


def test_team_plus_minus_is_the_score_margin():
    from nbatools.commands.data_utils import score_margin_plus_minus

    # The source column is wrong in some real games (a wrong sign, a
    # fractional value); a game without both rows keeps the stored value.
    rows = pd.DataFrame(
        {
            "game_id": [1, 1, 2, 2, 3],
            "team_abbr": ["GSW", "LAC", "MIL", "BKN", "LAL"],
            "pts": [115, 113, 121, 109, 100],
            "plus_minus": [-3.0, 3.0, 12.4, -10.0, 7.0],
        }
    )
    fixed = score_margin_plus_minus(rows)
    assert fixed["plus_minus"].tolist() == [2.0, -2.0, 12.0, -12.0, 7.0]
    assert rows["plus_minus"].tolist() == [-3.0, 3.0, 12.4, -10.0, 7.0]


def test_corrupt_stored_margins_do_not_reach_any_answer(tmp_path, monkeypatch):
    import shutil

    shutil.copytree(RAW.parent.parent, tmp_path, dirs_exist_ok=True)
    path = tmp_path / "data" / "raw" / "team_game_stats" / "2025-26_regular_season.csv"
    games = pd.read_csv(path)
    games["plus_minus"] = games["plus_minus"].astype(float)
    lakers = games.index[games["team_abbr"] == "LAL"][:10]
    games.loc[lakers, "plus_minus"] = games.loc[lakers, "plus_minus"] + 30.4
    games.to_csv(path, index=False)
    from nbatools.data_source import reset_data_source_cache

    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    reset_data_source_cache()

    margin = _team_margins()
    margin = margin[margin["team_abbr"] == "LAL"]["margin"]
    summary = execute_natural_query("Lakers point differential").result.to_dict()
    assert summary["sections"]["summary"][0]["plus_minus_avg"] == pytest.approx(
        margin.mean(), abs=1e-3
    )
    board = execute_natural_query("which team has the best point differential").result.to_dict()
    lakers_row = next(r for r in board["sections"]["leaderboard"] if r["team_abbr"] == "LAL")
    assert lakers_row["plus_minus_per_game"] == pytest.approx(margin.mean(), abs=1e-3)
    top = execute_natural_query("Lakers best plus minus game").result.to_dict()
    best = next(iter(top["sections"].values()))[0]
    assert best["plus_minus"] == margin.max()
