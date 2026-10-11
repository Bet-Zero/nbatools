"""C1: record bars against one team, and bars on the teams a beat board lists.

"which teams have a winning record against the Lakers" listed every opponent
(5-7 included); "which teams have the Lakers beaten that are over .500"
dropped the bar; "how many winning teams have the Lakers beaten" refused;
"Lakers record over teams over .500" gave the whole record (47-13). Expected
values come from the fixture's game rows and standings.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _games(season: str = "2025-26") -> pd.DataFrame:
    return pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv")


def _win_pct(season: str = "2025-26") -> dict[str, float]:
    table = pd.read_csv(RAW / "standings_snapshots" / f"{season}_regular_season.csv")
    return dict(zip(table["team_abbr"], table["win_pct"]))


def _against(opponent: str, seasons=("2025-26",)) -> pd.DataFrame:
    games = pd.concat([_games(season) for season in seasons])
    games = games[games["opponent_team_abbr"] == opponent]
    return games.groupby("team_abbr").agg(
        wins=("wl", lambda s: int((s == "W").sum())),
        losses=("wl", lambda s: int((s == "L").sum())),
    )


def _board(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["leaderboard"]


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("which teams have a winning record against the Lakers", lambda w, lost: w > lost),
        ("how many teams have a losing record against the Lakers", lambda w, lost: w < lost),
        ("which teams are over .500 against the Celtics", lambda w, lost: w > lost),
    ],
)
def test_head_to_head_record_bar(query, keep):
    opponent = "BOS" if "Celtics" in query else "LAL"
    record = _against(opponent)
    expected = {
        team: (row.wins, row.losses)
        for team, row in record.iterrows()
        if keep(row.wins, row.losses)
    }
    rows = _board(query)
    assert {r["team_abbr"]: (r["wins"], r["losses"]) for r in rows} == expected
    assert expected  # the fixture has teams on both sides of every bar


def test_head_to_head_bar_over_a_span():
    record = _against("LAL", ("2023-24", "2024-25", "2025-26"))
    expected = {t for t, row in record.iterrows() if row.wins > row.losses}
    rows = _board("teams with a winning record vs the Lakers since 2023")
    assert {r["team_abbr"] for r in rows} == expected


def test_head_to_head_answer_names_the_opponent():
    phrase = execute_natural_query("which teams have a winning record against the Lakers").metadata[
        "answer_phrase"
    ]
    assert "a winning record against the" in phrase


@pytest.mark.parametrize(
    ("query", "bar", "stat"),
    [
        ("which teams have the Lakers beaten that are over .500", lambda p: p > 0.5, "losses"),
        ("how many winning teams have the Lakers beaten", lambda p: p >= 0.5, "losses"),
        ("which teams over .500 have the Lakers beaten", lambda p: p > 0.5, "losses"),
        (
            "how many teams with a winning record have the Lakers beaten",
            lambda p: p > 0.5,
            "losses",
        ),
        ("which winning teams beat the Lakers", lambda p: p >= 0.5, "wins"),
        ("which teams .500 or better beat the Lakers this season", lambda p: p >= 0.5, "wins"),
        ("how many teams have beaten the Lakers that are over .500", lambda p: p > 0.5, "wins"),
    ],
)
def test_bar_on_the_listed_teams(query, bar, stat):
    win_pct = _win_pct()
    record = _against("LAL")
    expected = {
        team: int(row[stat])
        for team, row in record.iterrows()
        if row[stat] > 0 and bar(win_pct[team])
    }
    sections = execute_natural_query(query).result.to_dict()["sections"]
    rows = sections.get("leaderboard") or sections.get("count_detail") or []
    if not rows:
        rows = next(v for k, v in sections.items() if k != "count" and isinstance(v, list))
    assert {r["team_abbr"]: r[stat] for r in rows} == expected
    assert 0 < len(expected) < len(record)


def test_bar_on_listed_teams_over_seasons_is_per_season():
    seasons = ("2023-24", "2024-25", "2025-26")
    games = []
    for season in seasons:
        rows = _games(season)
        pct = _win_pct(season)
        rows = rows[(rows["opponent_team_abbr"] == "LAL") & (rows["wl"] == "L")]
        games.append(rows[rows["team_abbr"].map(lambda t, pct=pct: pct.get(t, 1) < 0.5)])
    expected = pd.concat(games)["team_abbr"].value_counts().to_dict()
    rows = _board("which losing teams have the Lakers beaten since 2023")
    assert {r["team_abbr"]: r["losses"] for r in rows} == expected


@pytest.mark.parametrize(
    "query",
    ["Lakers record over teams over .500", "Lakers record over winning teams"],
)
def test_record_over_quality_teams_is_against_them(query):
    quality = parse_query(query)["route_kwargs"].get("opponent_quality")
    assert quality is not None
    win_pct = _win_pct()
    floor = (lambda p: p > 0.5) if "over .500" in query else (lambda p: p >= 0.5)
    games = _games()
    games = games[
        (games["team_abbr"] == "LAL") & games["opponent_team_abbr"].map(lambda t: floor(win_pct[t]))
    ]
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    "query",
    [
        "which teams have the Lakers beaten",
        "which teams beat the Lakers twice",
        "how many teams have a winning record",
        "which teams have the best record against the Lakers",
    ],
)
def test_unbarred_boards_keep_their_reading(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert "team_quality" not in kwargs
    if "against" in query:
        assert kwargs.get("record_bar") is None


@pytest.mark.parametrize(
    ("query", "opponent", "keep"),
    [
        ("which teams are .500 or better against the Knicks", "NYK", lambda w, lost: w >= lost),
        ("teams .500 or better against the Knicks", "NYK", lambda w, lost: w >= lost),
        ("which teams finished .500 or worse against the Knicks", "NYK", lambda w, lost: w <= lost),
        (
            "which teams have a record of .500 or better against the Knicks",
            "NYK",
            lambda w, lost: w >= lost,
        ),
        ("teams with a .500 or better record against the Knicks", "NYK", lambda w, lost: w >= lost),
        ("which teams have a record over .500 against the Lakers", "LAL", lambda w, lost: w > lost),
        (
            "which teams have a record above .500 against the Lakers",
            "LAL",
            lambda w, lost: w > lost,
        ),
        (
            "which teams have a better than .500 record against the Lakers",
            "LAL",
            lambda w, lost: w > lost,
        ),
    ],
)
def test_head_to_head_bar_spellings(query, opponent, keep):
    record = _against(opponent)
    expected = {
        team: (row.wins, row.losses)
        for team, row in record.iterrows()
        if keep(row.wins, row.losses)
    }
    rows = _board(query)
    assert {r["team_abbr"]: (r["wins"], r["losses"]) for r in rows} == expected


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record over opponents over .500",
        "Lakers record against opponents over .500",
        "Lakers record over .500 teams",
    ],
)
def test_record_against_opponents_over_500(query):
    win_pct = _win_pct()
    games = _games()
    games = games[
        (games["team_abbr"] == "LAL") & games["opponent_team_abbr"].map(lambda t: win_pct[t] > 0.5)
    ]
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    ("query", "phrase"),
    [
        (
            "which teams have a winning record against the Lakers last season",
            "No team has a winning record against the",
        ),
        ("which teams under .500 did the Lakers lose to", "No team under .500 beat the"),
        ("which losing teams beat the Lakers", "No losing team beat the"),
    ],
)
def test_no_team_at_the_bar_is_answered(query, phrase):
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    assert result.result.to_dict()["sections"].get("leaderboard", []) == []
    assert result.metadata["answer_phrase"].startswith(phrase)


@pytest.mark.parametrize(
    "query",
    [
        # A shooting bar is not a team record: it stays refused (not dropped).
        "games Jokic shot .500 or better vs the Lakers",
        "LeBron fg pct .500 or better vs the Celtics",
        "which teams is Boston .500 or better against",
    ],
)
def test_shooting_500_bars_are_not_record_bars(query):
    assert execute_natural_query(query).result_status == "no_result"
