"""Season leaderboards rank the aggregation the question asks for.

Each additive count has two season figures: the total and the per-game
average. A leaderboard ranks one of them by default (`reb` ranks
`reb_per_game`, `pf` ranks `pf_total`), and a question that explicitly asks for
the other one - "total rebounds leaders", "personal fouls per game leaders",
"average minutes leaders" - used to be refused. It now ranks the sibling
column. Rates and percentages have no sibling: a season total of a percentage
is not a statistic, so total/per-game wording on them still refuses.

Every expected leaderboard here is computed from the fixture's game-log CSVs
with pandas - sum per player (or team) for a total, sum over distinct games for
a per-game figure - never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
UNSUPPORTED_AGGREGATION = "leaderboard_aggregation_unsupported"

#: The leaderboards' published qualifiers: a full regular season needs 20
#: games, a playoff board 4, and a date window or last-N sample 3.
REGULAR_SEASON_MIN_GAMES = 20
PLAYOFF_MIN_GAMES = 4
WINDOW_MIN_GAMES = 3


def _logs(kind: str, season: str = "2025-26", season_type: str = "Regular Season"):
    slug = season_type.lower().replace(" ", "_")
    frame = pd.read_csv(RAW / f"{kind}_game_stats" / f"{season}_{slug}.csv")
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    return frame


def _last_n(logs: pd.DataFrame, key: str, n: int) -> pd.DataFrame:
    ordered = logs.sort_values([key, "game_date", "game_id"], ascending=[True, False, False])
    return ordered.groupby(key, group_keys=False).head(n)


def _expected_board(
    logs: pd.DataFrame,
    column: str,
    *,
    key: str,
    name: str,
    min_games: int,
    limit: int = 10,
) -> list[tuple[int, float, int]]:
    """(id, figure, games) for the top *limit*, computed straight from the logs."""
    base = column.removesuffix("_total").removesuffix("_per_game")
    grouped = logs.groupby(key).agg(
        total=(base, "sum"), games=("game_id", "nunique"), name=(name, "first")
    )
    grouped = grouped[grouped["games"] >= min_games]
    if column.endswith("_total"):
        grouped["figure"] = grouped["total"]
    else:
        grouped["figure"] = grouped["total"] / grouped["games"]
    top = grouped.sort_values(["figure", "games", "name"], ascending=[False, False, True]).head(
        limit
    )
    return [(int(i), float(row.figure), int(row.games)) for i, row in top.iterrows()]


def _board(executed, column: str, key: str) -> list[tuple[int, float, int]]:
    leaders = executed.result.leaders
    return [
        (int(row[key]), float(row[column]), int(row["games_played"]))
        for _, row in leaders.iterrows()
    ]


def _assert_answers_with(executed, route: str, column: str) -> None:
    assert executed.route == route
    assert executed.result_status == "ok", executed.result_reason
    assert UNSUPPORTED_AGGREGATION not in (executed.metadata.get("unsupported_filters") or [])
    assert executed.metadata.get("stat") == column
    assert column in executed.result.leaders.columns


def _assert_same_board(actual, expected) -> None:
    assert [row[0] for row in actual] == [row[0] for row in expected]
    assert [row[2] for row in actual] == [row[2] for row in expected]
    assert [row[1] for row in actual] == pytest.approx([row[1] for row in expected])


# ---------------------------------------------------------------------------
# Player season totals of stats whose default board is per game
# ---------------------------------------------------------------------------

PLAYER_TOTALS = [
    ("total points leaders", "pts_total"),
    ("total rebounds leaders", "reb_total"),
    ("total assists leaders", "ast_total"),
    ("total threes leaders", "fg3m_total"),
    ("total steals leaders", "stl_total"),
    ("total blocks leaders", "blk_total"),
    ("total turnovers leaders", "tov_total"),
    ("players with the most total rebounds", "reb_total"),
    ("combined scoring leaders", "pts_total"),
    ("cumulative points leaders this season", "pts_total"),
]


@pytest.mark.parametrize("query, column", PLAYER_TOTALS, ids=[r[0] for r in PLAYER_TOTALS])
def test_player_season_total_is_the_summed_game_logs(query, column):
    executed = execute_natural_query(query)

    _assert_answers_with(executed, "season_leaders", column)
    expected = _expected_board(
        _logs("player"),
        column,
        key="player_id",
        name="player_name",
        min_games=REGULAR_SEASON_MIN_GAMES,
    )
    _assert_same_board(_board(executed, column, "player_id"), expected)


# ---------------------------------------------------------------------------
# Player per-game figures of stats whose default board is a season total
# ---------------------------------------------------------------------------

PLAYER_PER_GAME = [
    ("personal fouls per game leaders", "pf_per_game"),
    ("minutes per game leaders", "minutes_per_game"),
    ("average minutes leaders", "minutes_per_game"),
    ("minutes a game leaders", "minutes_per_game"),
    ("field goals attempted per game leaders", "fga_per_game"),
    ("free throws attempted per game leaders", "fta_per_game"),
    ("average three-point attempts leaders", "fg3a_per_game"),
]


@pytest.mark.parametrize("query, column", PLAYER_PER_GAME, ids=[r[0] for r in PLAYER_PER_GAME])
def test_player_per_game_figure_is_total_over_games(query, column):
    executed = execute_natural_query(query)

    _assert_answers_with(executed, "season_leaders", column)
    expected = _expected_board(
        _logs("player"),
        column,
        key="player_id",
        name="player_name",
        min_games=REGULAR_SEASON_MIN_GAMES,
    )
    _assert_same_board(_board(executed, column, "player_id"), expected)


# ---------------------------------------------------------------------------
# Team totals, seasons, playoffs and windows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, column",
    [
        ("team total rebounds leaders", "reb_total"),
        ("teams with the most total points", "pts_total"),
    ],
)
def test_team_season_total_is_the_summed_team_logs(query, column):
    executed = execute_natural_query(query)

    _assert_answers_with(executed, "season_team_leaders", column)
    expected = _expected_board(
        _logs("team"),
        column,
        key="team_id",
        name="team_name",
        min_games=REGULAR_SEASON_MIN_GAMES,
    )
    _assert_same_board(_board(executed, column, "team_id"), expected)


@pytest.mark.parametrize(
    "query, column, source",
    [
        ("best total turnover teams", "tov_total", "tov"),
        ("best total points allowed teams", "opponent_pts_total", "opponent_pts"),
    ],
)
def test_best_total_of_a_lower_is_better_stat_still_means_fewest(query, column, source):
    """Turnovers and points allowed stay lower-is-better when the total is ranked."""
    executed = execute_natural_query(query)

    _assert_answers_with(executed, "season_team_leaders", column)
    board = _board(executed, column, "team_id")
    logs = _logs("team")
    if source == "opponent_pts":
        # A team's points allowed are its opponent's points in the same game.
        opponent = logs[["game_id", "team_id", "pts"]].rename(
            columns={"team_id": "opponent_id", "pts": "opponent_pts"}
        )
        logs = logs.merge(opponent, on="game_id")
        logs = logs[logs["team_id"] != logs["opponent_id"]]
    totals = logs.groupby("team_id")[source].sum()
    assert [row[1] for row in board] == sorted(totals)[: len(board)]


def test_total_for_another_season_reads_that_season():
    executed = execute_natural_query("total rebounds leaders 2024-25")

    _assert_answers_with(executed, "season_leaders", "reb_total")
    expected = _expected_board(
        _logs("player", "2024-25"),
        "reb_total",
        key="player_id",
        name="player_name",
        min_games=REGULAR_SEASON_MIN_GAMES,
    )
    _assert_same_board(_board(executed, "reb_total", "player_id"), expected)


def test_playoff_total_reads_the_playoff_logs():
    executed = execute_natural_query("total rebounds leaders in the playoffs")

    _assert_answers_with(executed, "season_leaders", "reb_total")
    expected = _expected_board(
        _logs("player", season_type="Playoffs"),
        "reb_total",
        key="player_id",
        name="player_name",
        min_games=PLAYOFF_MIN_GAMES,
    )
    _assert_same_board(_board(executed, "reb_total", "player_id"), expected)


def test_total_inside_a_date_window_sums_only_that_window():
    executed = execute_natural_query("total points leaders from 2026-01-01 to 2026-01-31")

    _assert_answers_with(executed, "season_leaders", "pts_total")
    logs = _logs("player")
    window = logs[(logs["game_date"] >= "2026-01-01") & (logs["game_date"] <= "2026-01-31")]
    expected = _expected_board(
        window, "pts_total", key="player_id", name="player_name", min_games=WINDOW_MIN_GAMES
    )
    _assert_same_board(_board(executed, "pts_total", "player_id"), expected)
    # The window is a real restriction, not the season total relabelled.
    season_top = _expected_board(
        logs,
        "pts_total",
        key="player_id",
        name="player_name",
        min_games=REGULAR_SEASON_MIN_GAMES,
    )
    assert expected[0][1] < season_top[0][1]


def test_player_total_over_last_n_games_sums_each_players_last_n():
    executed = execute_natural_query("total rebounds leaders last 10 games")

    _assert_answers_with(executed, "season_leaders", "reb_total")
    sample = _last_n(_logs("player"), "player_id", 10)
    expected = _expected_board(
        sample, "reb_total", key="player_id", name="player_name", min_games=WINDOW_MIN_GAMES
    )
    _assert_same_board(_board(executed, "reb_total", "player_id"), expected)
    assert all(row[2] == 10 for row in expected)


def test_team_total_over_last_n_games_sums_each_teams_last_n():
    executed = execute_natural_query("team total rebounds leaders last 10 games")

    _assert_answers_with(executed, "season_team_leaders", "reb_total")
    sample = _last_n(_logs("team"), "team_id", 10)
    expected = _expected_board(
        sample, "reb_total", key="team_id", name="team_name", min_games=WINDOW_MIN_GAMES
    )
    _assert_same_board(_board(executed, "reb_total", "team_id"), expected)


# ---------------------------------------------------------------------------
# What does not change
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, column",
    [
        ("rebounds leaders", "reb_per_game"),
        ("points per game leaders", "pts_per_game"),
        ("personal fouls leaders", "pf_total"),
        ("total personal fouls leaders", "pf_total"),
    ],
)
def test_default_and_matching_aggregations_keep_their_board(query, column):
    executed = execute_natural_query(query)

    assert executed.route == "season_leaders"
    assert executed.result_status == "ok"
    assert column in executed.result.leaders.columns
    expected = _expected_board(
        _logs("player"),
        column,
        key="player_id",
        name="player_name",
        min_games=REGULAR_SEASON_MIN_GAMES,
    )
    _assert_same_board(_board(executed, column, "player_id"), expected)


RATE_REFUSALS = [
    ("total true shooting percentage leaders", "ts_pct", "total"),
    ("true shooting percentage per game leaders", "ts_pct", "per_game"),
    ("total three point percentage leaders", "fg3_pct", "total"),
    ("usage rate per game leaders", "usg_pct", "per_game"),
    ("total usage rate leaders", "usg_pct", "total"),
]


@pytest.mark.parametrize(
    "query, metric, requested", RATE_REFUSALS, ids=[r[0] for r in RATE_REFUSALS]
)
def test_rates_still_refuse_total_and_per_game_wording(query, metric, requested):
    executed = execute_natural_query(query)

    assert executed.result_status == "no_result"
    assert UNSUPPORTED_AGGREGATION in (executed.metadata.get("unsupported_filters") or [])
    assert executed.metadata.get("stat") is None
    assert executed.metadata.get("requested_stat") == metric
    assert executed.metadata.get("requested_aggregation") == requested
    assert executed.metadata.get("available_aggregation") == "rate"
    assert executed.to_dict()["sections"] == {}


def test_single_game_board_is_unchanged():
    executed = execute_natural_query("most rebounds in a game this season")

    assert executed.route == "top_player_games"
    assert executed.result_status == "ok"
    assert executed.metadata.get("stat") == "reb"
    top = executed.result.leaders.iloc[0]
    assert int(top["reb"]) == int(_logs("player")["reb"].max())
