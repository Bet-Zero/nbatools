"""C1: team populations by record and opponents played.

"which teams have a winning record" listed every team (no bar) and "how many
teams have a winning record" counted every team; "how many teams are over
.500" / "teams .500 or worse" did not route; "how many teams did the Lakers
play" counted games (60). Expected values come from the fixture's team rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _records(season: str = "2025-26", venue: str | None = None) -> pd.DataFrame:
    games = pd.read_csv(RAW / f"{season}_regular_season.csv")
    if venue == "home":
        games = games[games["is_home"] == 1]
    return games.groupby("team_abbr")["wl"].value_counts().unstack(fill_value=0)


def _teams(query: str) -> set:
    rows = execute_natural_query(query).result.to_dict()["sections"]["leaderboard"]
    return {row["team_abbr"] for row in rows}


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("which teams have a winning record", lambda r: r["W"] > r["L"]),
        ("which teams have a losing record", lambda r: r["W"] < r["L"]),
        ("teams .500 or better", lambda r: r["W"] >= r["L"]),
        ("teams .500 or worse", lambda r: r["W"] <= r["L"]),
    ],
)
def test_record_bar_lists_every_team_at_it(query, keep):
    records = _records()
    assert _teams(query) == set(records[keep(records)].index)


@pytest.mark.parametrize(
    ("query", "season", "keep"),
    [
        ("how many teams have a winning record", "2025-26", lambda r: r["W"] > r["L"]),
        ("how many teams are over .500", "2025-26", lambda r: r["W"] > r["L"]),
        ("how many teams finished under .500 last season", "2024-25", lambda r: r["W"] < r["L"]),
    ],
)
def test_record_bar_counts(query, season, keep):
    records = _records(season)
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"] == [{"count": int(keep(records).sum())}]
    assert "teams have a" in result.metadata["count_phrase"]


def test_record_bar_at_home():
    records = _records(venue="home")
    result = execute_natural_query("how many teams have a winning record at home")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int((records["W"] > records["L"]).sum())}
    ]
    assert "winning record at home" in result.metadata["count_phrase"]


def test_opponent_bars_stay_opponent_filters():
    kwargs = execute_natural_query("Lakers record vs .500 teams").metadata
    assert kwargs.get("route") != "team_record_leaderboard"


@pytest.mark.parametrize(
    ("query", "team", "seasons"),
    [
        ("how many teams did the Lakers play", "LAL", ["2025-26"]),
        ("how many teams have the Celtics faced since 2024", "BOS", ["2024-25", "2025-26"]),
    ],
)
def test_distinct_opponents(query, team, seasons):
    games = pd.concat([pd.read_csv(RAW / f"{s}_regular_season.csv") for s in seasons])
    expected = games[games["team_abbr"] == team]["opponent_team_abbr"].nunique()
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"] == [{"count": expected}]
    assert f"played {expected} teams" in result.metadata["count_phrase"]


def test_team_occurrence_count_reads_teams():
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    expected = games[games["pts"] >= 120]["team_abbr"].nunique()
    result = execute_natural_query("how many teams scored 120")
    assert result.metadata["count_phrase"].startswith(f"{expected} teams have had a game")


def test_population_500_or_better_is_one_bar():
    # "are .500 or better" was split as an OR ("... are .500" / "better").
    records = _records()
    for query, keep in (
        ("how many teams are .500 or better", records["W"] >= records["L"]),
        ("how many teams are .500 or worse", records["W"] <= records["L"]),
    ):
        result = execute_natural_query(query)
        assert result.result.to_dict()["sections"]["count"] == [{"count": int(keep.sum())}]


def test_winning_teams_population_is_over_500():
    records = _records()
    result = execute_natural_query("how many winning teams are there")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int((records["W"] > records["L"]).sum())}
    ]


def test_record_bar_names_its_date_window():
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    march = games[pd.to_datetime(games["game_date"]).dt.month == 3]
    records = march.groupby("team_abbr")["wl"].value_counts().unstack(fill_value=0)
    result = execute_natural_query("teams with a winning record in March")
    assert _teams("teams with a winning record in March") == set(
        records[records["W"] > records["L"]].index
    )
    assert "from 2026-03-01 to 2026-03-31" in result.metadata["answer_phrase"]


@pytest.mark.parametrize(
    "query",
    [
        # Conditions the record board cannot apply.
        "which teams have a winning record in the East",
        "teams with a winning record on back to backs",
        "teams with a winning record and 10 home losses",
        "teams with a winning record that made the playoffs",
        "teams with a winning record and a negative point differential",
        "teams with a winning record every season since 2023",
        "teams with a winning record by month",
        # "played for", or a qualifier distinct opponents would drop.
        "how many teams did LeBron play for",
        "how many teams has Kevin Durant played for",
        "how many teams did the Lakers play twice",
        "how many teams did the Lakers play more than 10 times",
        "how many teams did the Lakers play when LeBron scored 30",
    ],
)
def test_record_and_opponent_counts_with_other_conditions_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_opponent_count_names_venue_and_dates():
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    lakers = games[games["team_abbr"] == "LAL"]
    march = lakers[pd.to_datetime(lakers["game_date"]).dt.month == 3]
    result = execute_natural_query("how many teams did the Lakers play in March")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": march["opponent_team_abbr"].nunique()}
    ]
    assert "from 2026-03-01 to 2026-03-31" in result.metadata["count_phrase"]
    home = execute_natural_query("how many teams did the Lakers play at home")
    assert "teams at home" in home.metadata["count_phrase"]


def test_player_team_count_counts_his_opponents():
    rows = pd.read_csv(
        Path(
            "qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_regular_season.csv"
        )
    )
    games = rows[(rows["player_name"] == "LeBron James") & (rows["pts"] >= 30)]
    expected = games["opponent_team_abbr"].nunique()
    result = execute_natural_query("how many teams did LeBron score 30 against")
    assert result.result.to_dict()["sections"]["count"] == [{"count": expected}]
    assert f"against {expected} teams" in result.metadata["count_phrase"]
