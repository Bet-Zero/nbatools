"""C1: absence words after a name, a pair after a bound, three teams by month.

"LeBron stats with Davis out" returned every game, and "with Anthony Davis
out" the games Davis played: the trailing word was dropped. "LeBron games
with 30 points with Davis and Reaves" applied Reaves only. "Lakers vs
Celtics vs Knicks in March" and "... points" compared two of the teams.

Every fixture player plays every game, so the availability tests drop some
of Anthony Davis's and Austin Reaves's rows from a copy of the fixture.
Expected values come from that copy's rows.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

FIXTURE = Path("qa/fixtures/query_engine_sample")
PLAYERS = "data/raw/player_game_stats/2025-26_regular_season.csv"
TEAMS = "data/raw/team_game_stats/{}_regular_season.csv"


@pytest.fixture
def sparse_root(tmp_path, monkeypatch):
    """The fixture with Davis, Reaves and Tatum out of some of their games."""
    from nbatools.data_source import reset_data_source_cache

    root = tmp_path / "fx"
    shutil.copytree(FIXTURE, root)
    players = pd.read_csv(root / PLAYERS)
    lal = sorted(players.loc[players["team_abbr"] == "LAL", "game_id"].unique())
    bos = sorted(players.loc[players["team_abbr"] == "BOS", "game_id"].unique())
    out = {
        "Anthony Davis": set(lal[::4]),
        "Austin Reaves": set(lal[::6]),
        "Jayson Tatum": set(bos[::3]),
    }
    drop = pd.Series(False, index=players.index)
    for name, games in out.items():
        drop |= (players["player_name"] == name) & players["game_id"].isin(games)
    players[~drop].to_csv(root / PLAYERS, index=False)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield root, out
    reset_data_source_cache()


def _ok(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]


def _lakers() -> pd.DataFrame:
    teams = pd.read_csv(FIXTURE / TEAMS.format("2025-26"))
    return teams[teams["team_abbr"] == "LAL"]


def _keep(games: pd.DataFrame, out: dict, names: list[str], present: bool) -> pd.DataFrame:
    for name in names:
        games = games[games["game_id"].isin(out[name]) != present]
    return games


@pytest.mark.parametrize(
    ("query", "names", "present"),
    [
        ("Lakers record with Davis out", ["Anthony Davis"], False),
        ("Lakers record with Anthony Davis out", ["Anthony Davis"], False),
        ("Lakers record with Davis not playing", ["Anthony Davis"], False),
        ("Lakers record with Davis sitting this season", ["Anthony Davis"], False),
        ("Lakers record with Davis playing", ["Anthony Davis"], True),
        ("Lakers record with Davis and Reaves both out", ["Anthony Davis", "Austin Reaves"], False),
        ("Lakers record with Davis and Reaves DNP", ["Anthony Davis", "Austin Reaves"], False),
        ("Lakers record with Davis and Reaves out", ["Anthony Davis", "Austin Reaves"], False),
        ("Lakers record with Davis and Reaves missing", ["Anthony Davis", "Austin Reaves"], False),
        (
            "Lakers record with Davis and Reaves not playing",
            ["Anthony Davis", "Austin Reaves"],
            False,
        ),
        (
            "Lakers record without Davis and Reaves playing",
            ["Anthony Davis", "Austin Reaves"],
            False,
        ),
        (
            "Lakers record with Davis and Reaves both playing",
            ["Anthony Davis", "Austin Reaves"],
            True,
        ),
    ],
)
def test_team_record_with_absence_words(sparse_root, query, names, present):
    _, out = sparse_root
    games = _keep(_lakers(), out, names, present)
    assert len(games) > 0
    row = _ok(query)["summary"][0]
    assert (row["games"], row["wins"]) == (len(games), int((games["wl"] == "W").sum()))


@pytest.mark.parametrize(
    ("query", "names", "present"),
    [
        ("LeBron James stats with Davis out", ["Anthony Davis"], False),
        ("LeBron James stats with Anthony Davis out", ["Anthony Davis"], False),
        ("LeBron James stats with Davis out this season", ["Anthony Davis"], False),
        ("LeBron James stats with Davis and Reaves out", ["Anthony Davis", "Austin Reaves"], False),
        (
            "LeBron James stats with Davis and Reaves not playing",
            ["Anthony Davis", "Austin Reaves"],
            False,
        ),
    ],
)
def test_player_stats_with_absence_words(sparse_root, query, names, present):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = _keep(players[players["player_name"] == "LeBron James"], out, names, present)
    row = _ok(query)["summary"][0]
    assert row["games"] == len(lebron)
    assert row["pts_avg"] == pytest.approx(lebron["pts"].mean(), abs=1e-3)


@pytest.mark.parametrize(
    ("query", "bound", "present"),
    [
        ("LeBron James games with 30 points with Davis and Reaves", 30, True),
        ("LeBron James games with 25 points with Davis and Reaves", 25, True),
        ("LeBron James games with 20 points without Davis and Reaves", 20, False),
    ],
)
def test_a_teammate_pair_after_a_bound(sparse_root, query, bound, present):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[(players["player_name"] == "LeBron James") & (players["pts"] >= bound)]
    lebron = _keep(lebron, out, ["Anthony Davis", "Austin Reaves"], present)
    assert 0 < len(lebron) <= 25
    sections = _ok(query)
    rows = sections.get("finder") or sections["game_log"]
    assert {row["game_id"] for row in rows} == set(lebron["game_id"])


def test_team_record_with_a_bound_then_a_pair(sparse_root):
    _, out = sparse_root
    games = _lakers()
    games = _keep(games[games["pts"] >= 120], out, ["Anthony Davis", "Austin Reaves"], True)
    row = _ok("Lakers record with 120 points with Davis and Reaves")["summary"][0]
    assert (row["games"], row["wins"]) == (len(games), int((games["wl"] == "W").sum()))


@pytest.mark.parametrize(
    "query",
    [
        # Not a name before the absence word, or a second name who is not a teammate.
        "Lakers record with the starters out",
        "LeBron James games with 30 points with Davis and Curry",
        "LeBron James stats without Davis and Curry",
    ],
)
def test_unread_availability_still_refuses(sparse_root, query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "season", "month"),
    [
        ("Lakers vs Celtics vs Knicks in March", "2025-26", "2026-03"),
        ("Lakers vs Celtics vs Knicks in March 2024", "2023-24", "2024-03"),
        ("Lakers vs Celtics vs Knicks points", "2025-26", None),
        ("Lakers vs Celtics vs Knicks points per game", "2025-26", None),
    ],
)
def test_three_teams_by_month_or_points(query, season, month):
    teams = pd.read_csv(FIXTURE / TEAMS.format(season))
    if month:
        teams = teams[teams["game_date"].astype(str).str.startswith(month)]
    rows = _ok(query)["summary"]
    assert [row["team_name"] for row in rows] == ["LAL", "BOS", "NYK"]
    for row in rows:
        games = teams[teams["team_abbr"] == row["team_name"]]
        assert (row["games"], row["wins"]) == (len(games), int((games["wl"] == "W").sum()))
        assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers vs Celtics vs Knicks longest win streak",
        "Lakers vs Celtics vs Knicks head to head",
        "Lakers vs Celtics vs Knicks in wins",
    ],
)
def test_three_teams_with_an_unread_rest_refuse(query):
    # Another reader would compare two of the three.
    assert execute_natural_query(query).result_status == "no_result"


def test_three_team_stretch_is_still_the_stretch_board():
    assert _ok("Lakers vs Celtics vs Knicks best 5 game stretch")["leaderboard"]


@pytest.mark.parametrize(
    ("query", "opponents"),
    [
        ("Lakers record vs Celtics with Tatum out", ["BOS"]),
        ("Lakers record vs Celtics without Tatum", ["BOS"]),
        ("Lakers record vs Celtics when Tatum sits", ["BOS"]),
        ("Lakers record vs Celtics and Knicks without Tatum", ["BOS", "NYK"]),
    ],
)
def test_team_record_with_an_opposing_player_out(sparse_root, query, opponents):
    # He is on the opponent: the games he did not play, not "no games".
    _, out = sparse_root
    # Required positive obligation: Tatum belongs to Boston in this stipulated
    # fixture. Knicks games cannot count as his missed Boston games. The fixture
    # still lacks source-backed membership/coverage, so this test must not be
    # counted as accepted while the shared filter reports unavailable data.
    games = _lakers()
    games = games[
        games["opponent_team_abbr"].eq("BOS")
        & games["opponent_team_abbr"].isin(opponents)
        & games["game_id"].isin(out["Jayson Tatum"])
    ]
    assert len(games) > 0
    row = _ok(query)["summary"][0]
    assert (row["games"], row["wins"]) == (len(games), int((games["wl"] == "W").sum()))
    assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games with Davis out and 30 points",
        "LeBron James games with Davis out with 30 points",
        "LeBron James 30 point games with Davis out",
    ],
)
def test_absence_then_a_bound(sparse_root, query):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[
        (players["player_name"] == "LeBron James")
        & (players["pts"] >= 30)
        & players["game_id"].isin(out["Anthony Davis"])
    ]
    assert len(lebron) > 0
    sections = _ok(query)
    if "summary" in sections and "finder" not in sections:
        assert sections["summary"][0]["games"] == len(lebron)
    else:
        rows = sections.get("finder") or sections["game_log"]
        assert {row["game_id"] for row in rows} == set(lebron["game_id"])


@pytest.mark.parametrize(
    ("query", "bound"),
    [
        ("Lakers 120 point games vs Celtics with Tatum out", 120),
        ("Lakers 120 point games vs Celtics without Tatum", 120),
        ("Lakers points per game vs Celtics without Tatum", None),
    ],
)
def test_game_summary_with_an_opposing_player_out(sparse_root, query, bound):
    root, _ = sparse_root
    players = pd.read_csv(root / PLAYERS)
    played = set(players.loc[players["player_name"] == "Jayson Tatum", "game_id"])
    games = _lakers()
    games = games[(games["opponent_team_abbr"] == "BOS") & ~games["game_id"].isin(played)]
    if bound:
        games = games[games["pts"] >= bound]
    assert len(games) > 0
    row = _ok(query)["summary"][0]
    assert (row["games"], row["wins"]) == (len(games), int((games["wl"] == "W").sum()))
    assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)


@pytest.mark.parametrize(
    "status",
    [
        "injured",
        "hurt",
        "healthy",
        "available",
        "unavailable",
        "active",
        "inactive",
        "sidelined",
        "resting",
        "suspended",
        "in the lineup",
        "out of the lineup",
    ],
)
@pytest.mark.parametrize(
    "subject",
    [
        "Lakers record with Davis",
        "LeBron James stats with Davis and Reaves both",
        "Celtics record with Jayson Tatum",
    ],
)
def test_status_is_not_participation(sparse_root, subject, status):
    # The very same present/absent rows cannot establish status or its cause.
    result = execute_natural_query(f"{subject} {status}")
    assert result.result_status == "no_result"
    assert "availability_status" in result.metadata["unsupported_filters"]
    assert result.metadata["unsupported_availability"]["condition"]
    assert not result.to_dict()["sections"]


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games with 30 points with Davis and Reaves injured",
        "LeBron James stats when Davis is healthy",
        "Celtics record while Tatum is suspended",
        "Lakers record with injured Anthony Davis",
        "Celtics record whenever Tatum is active",
        "Celtics record during games where Tatum was active",
        "Jaylen Brown stats with Tatum fully fit",
        "Celtics record with Tatum doubtful",
        "Celtics record with Tatum questionable",
        "LeBron James stats with Davis available this season vs last season",
    ],
)
def test_status_survives_other_clauses(sparse_root, query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert "availability_status" in result.metadata["unsupported_filters"]


def test_participation_natural_structured_and_api(sparse_root):
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.query_service import execute_structured_query

    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    expected = players[(players["player_name"] == "LeBron James") & (players["pts"] >= 30)]
    expected = _keep(expected, out, ["Anthony Davis", "Austin Reaves"], True)
    query = "LeBron James games with 30 points with Davis and Reaves playing"
    natural = execute_natural_query(query)
    structured = execute_structured_query(
        "player_game_finder",
        player="LeBron James",
        season="2025-26",
        stat="pts",
        min_value=30,
        with_player="Anthony Davis and Austin Reaves",
    )
    for result in (natural, structured):
        assert result.result_status == "ok"
        rows = result.to_dict()["sections"]["finder"]
        assert {row["game_id"] for row in rows} == set(expected["game_id"])
    client = TestClient(app)
    response = client.post("/query", json={"query": query})
    assert response.status_code == 200
    rows = response.json()["result"]["sections"]["finder"]
    assert {row["game_id"] for row in rows} == set(expected["game_id"])
    response = client.post("/query", json={"query": "Lakers record with Davis injured"})
    assert response.status_code == 200
    payload = response.json()["result"]
    assert payload["result_status"] == "no_result"
    assert not payload["sections"]
    assert "availability_status" in payload["metadata"]["unsupported_filters"]
