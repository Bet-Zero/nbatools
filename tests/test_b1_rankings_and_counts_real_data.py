"""B1 rankings and counts against the real 1996-97+ game rows.

Companion to ``test_b1_rankings_and_counts.py`` (fixture). Expected values come
from the raw ``player_game_stats`` rows of the pinned generation with pandas,
never from the code under test.
"""

from __future__ import annotations

from collections import defaultdict
from csv import DictReader
from fractions import Fraction

import pandas as pd
import pytest

from nbatools.data_source import data_path, data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

SEASON = "2023-24"


def _games(season: str = SEASON, season_type: str = "regular_season") -> pd.DataFrame:
    frame = data_read_csv(
        f"raw/player_game_stats/{season}_{season_type}.csv", dtype={"game_id": str}
    )
    for column in ("pts", "reb", "ast", "tov", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _counts(frame: pd.DataFrame, mask: pd.Series) -> pd.Series:
    return frame.assign(hit=mask.fillna(False).astype(int)).groupby("player_id")["hit"].sum()


@pytest.mark.parametrize(
    ("query", "column", "mask"),
    [
        (
            f"most 30 point 10 rebound games in {SEASON}",
            "games_pts_30+_reb_10+",
            lambda g: (g["pts"] >= 30) & (g["reb"] >= 10),
        ),
        (
            f"most games with 10+ assists and 0 turnovers in {SEASON}",
            "games_ast_10+_tov_0",
            lambda g: (g["ast"] >= 10) & (g["tov"] == 0),
        ),
        (
            f"most 20 point 10 assist games in {SEASON}",
            "games_pts_20+_ast_10+",
            lambda g: (g["pts"] >= 20) & (g["ast"] >= 10),
        ),
    ],
)
def test_condition_count_leaders_match_raw_rows(query, column, mask):
    games = _games()
    counts = _counts(games, mask(games))
    expected_top = sorted(counts.values, reverse=True)[:10]

    rows = _run(query).result.to_dict()["sections"]["leaderboard"]
    assert [row[column] for row in rows] == expected_top
    names = games.drop_duplicates("player_id").set_index("player_id")["player_name"]
    by_name = {names[pid]: n for pid, n in counts.items()}
    for row in rows:
        assert by_name[row["player_name"]] == row[column], row


def test_league_count_of_ten_assist_zero_turnover_games():
    games = _games()
    expected = int(((games["ast"] >= 10) & (games["tov"] == 0)).sum())
    (row,) = _run(f"how many games with 10+ assists and 0 turnovers in {SEASON}").result.to_dict()[
        "sections"
    ]["count"]
    assert row["count"] == expected


def test_league_list_of_forty_point_games():
    games = _games()
    expected = games[games["pts"] >= 40]
    rows = _run(f"games with 40+ points in {SEASON}").result.to_dict()["sections"]["finder"]
    assert len(rows) == min(len(expected), 25)
    keys = set(zip(expected["game_id"].astype(int), expected["player_id"].astype(int)))
    assert {(int(r["game_id"]), int(r["player_id"])) for r in rows} <= keys


@pytest.mark.parametrize(
    ("query", "column", "made", "attempted", "minimum"),
    [
        (
            f"best three point percentage in {SEASON} minimum 300 attempts",
            "fg3_pct",
            "fg3m",
            "fg3a",
            300,
        ),
        (
            f"best free throw percentage in {SEASON} minimum 200 attempts",
            "ft_pct",
            "ftm",
            "fta",
            200,
        ),
    ],
)
def test_qualified_rate_leaders_match_raw_totals(query, column, made, attempted, minimum):
    games = _games()
    totals = games.groupby("player_id").agg(made=(made, "sum"), attempted=(attempted, "sum"))
    qualified = totals[totals["attempted"] >= minimum]
    expected = (qualified["made"] / qualified["attempted"]).sort_values(ascending=False)

    rows = _run(query).result.to_dict()["sections"]["leaderboard"]
    assert [row[column] for row in rows] == pytest.approx(list(expected.head(10)))
    assert all(row[f"{attempted}_total"] >= minimum for row in rows)


def test_games_played_leaders_match_raw_rows():
    games = _games()
    played = games.groupby("player_id")["game_id"].nunique().sort_values(ascending=False)
    rows = _run(f"most games played in {SEASON}").result.to_dict()["sections"]["leaderboard"]
    assert [row["games_played"] for row in rows] == list(played.head(10))


def test_broad_three_point_ranking_matches_all_raw_seasons():
    made: dict[int, int] = defaultdict(int)
    attempted: dict[int, int] = defaultdict(int)
    games: dict[int, set[str]] = defaultdict(set)

    for year in range(1996, 2026):
        season = f"{year}-{(year + 1) % 100:02d}"
        path = data_path(f"raw/player_game_stats/{season}_regular_season.csv")
        with path.open(newline="", encoding="utf-8") as stream:
            for row in DictReader(stream):
                player_id = int(row["player_id"])
                made[player_id] += int(float(row["fg3m"]))
                attempted[player_id] += int(float(row["fg3a"]))
                games[player_id].add(row["game_id"])

    games_played = {player_id: len(game_ids) for player_id, game_ids in games.items()}
    del games
    qualified = [player_id for player_id, attempts in attempted.items() if attempts >= 300]
    ranked = sorted(
        qualified,
        key=lambda player_id: (
            Fraction(made[player_id], attempted[player_id]),
            games_played[player_id],
        ),
        reverse=True,
    )[:5]
    expected = [
        (player_id, games_played[player_id], made[player_id], attempted[player_id])
        for player_id in ranked
    ]

    answer = _run(
        "Top 5 players by three point percentage from 1996-97 to 2025-26 minimum 300 attempts"
    )
    assert answer.route == "season_leaders"
    rows = answer.result.to_dict()["sections"]["leaderboard"]
    assert [
        (row["player_id"], row["games_played"], row["fg3m_total"], row["fg3a_total"])
        for row in rows
    ] == expected
    assert [row["fg3_pct"] for row in rows] == pytest.approx(
        [makes / attempts for _, _, makes, attempts in expected]
    )
    assert all(
        row["seasons"] == "1996-97 to 2025-26" and row["season_type"] == "Regular Season"
        for row in rows
    )
