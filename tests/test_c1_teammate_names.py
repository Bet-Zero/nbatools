"""C1: a teammate named by one word, "LeBron games with Davis", and wording.

"Lakers record without Davis" and "LeBron stats with Austin" refused: the
one word is shared across the league. Among the team's players (or the
player's teammates) in the requested seasons it is one person, so it is now
read. "LeBron games with Davis" refused even with the full name, and "with
LeBron and Davis" kept LeBron only. "Lakers wins and losses split" refused,
"best 10 game window" listed games and "biggest blowout" listed 25.

Every fixture player plays every game, so the availability tests drop some
of Anthony Davis's and Austin Reaves's rows from a copy of the fixture.
Expected values come from that copy's rows; explicit synthetic observations
record the declared game-day participation independently of missing stat rows.
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
TEAMS = "data/raw/team_game_stats/2025-26_regular_season.csv"


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
    # This is controlled fixture evidence for the explicit schedule above,
    # never real NBA data or an inference from the saved sparse player file.
    observations = players[
        ["game_id", "game_date", "season", "season_type", "team_id", "player_id", "player_name"]
    ].copy()
    observations["participation_state"] = "played"
    observations.loc[drop, "participation_state"] = "did_not_play"
    observations["coverage_scope"] = "listed_player_rows_only"
    observations["source"] = "nba_official_finalbox:20251021_GSWLAL"
    observations["source_sha256"] = "a" * 64
    evidence = root / "data/raw/player_game_availability/2025-26_regular_season.csv"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    observations.to_csv(evidence, index=False)
    players[~drop].to_csv(root / PLAYERS, index=False)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield root, out
    reset_data_source_cache()


def _ok(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]


def _team_record(games: pd.DataFrame) -> tuple[int, int]:
    return int((games["wl"] == "W").sum()), int((games["wl"] == "L").sum())


@pytest.mark.parametrize(
    ("query", "name", "present"),
    [
        ("Lakers record without Davis", "Anthony Davis", False),
        ("Lakers record when Davis sits", "Anthony Davis", False),
        ("Lakers record with Austin", "Austin Reaves", True),
        ("Lakers record without Reaves", "Austin Reaves", False),
    ],
)
def test_team_record_with_a_one_word_teammate(sparse_root, query, name, present):
    _, out = sparse_root
    teams = pd.read_csv(FIXTURE / TEAMS)
    games = teams[(teams["team_abbr"] == "LAL")]
    games = games[games["game_id"].isin(out[name]) != present]
    row = _ok(query)["summary"][0]
    assert (row["wins"], row["losses"]) == _team_record(games)


@pytest.mark.parametrize(
    ("query", "name", "present"),
    [
        ("LeBron James stats without Davis", "Anthony Davis", False),
        ("LeBron stats when Davis sits", "Anthony Davis", False),
        ("LeBron James games with Davis", "Anthony Davis", True),
        ("LeBron James games with Anthony Davis", "Anthony Davis", True),
        ("LeBron stats with Austin", "Austin Reaves", True),
        ("LeBron stats when Reaves plays", "Austin Reaves", True),
        # Scope after the name is read on its own.
        ("LeBron James stats with Davis this season", "Anthony Davis", True),
        ("LeBron James stats without Davis this season", "Anthony Davis", False),
    ],
)
def test_player_games_with_or_without_a_teammate(sparse_root, query, name, present):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[players["player_name"] == "LeBron James"]
    lebron = lebron[lebron["game_id"].isin(out[name]) != present]
    row = _ok(query)["summary"][0]
    assert row["games"] == len(lebron)
    assert row["pts_avg"] == pytest.approx(lebron["pts"].mean(), abs=1e-3)


def test_player_game_list_with_a_teammate(sparse_root):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[
        (players["player_name"] == "LeBron James")
        & players["game_id"].isin(out["Anthony Davis"])
        & (players["pts"] >= 30)
    ]
    for query in (
        "LeBron James 30 point games without Davis",
        "LeBron James 30 point games when Davis sits",
    ):
        sections = _ok(query)
        rows = sections.get("finder") or sections["game_log"]
        assert {row["game_id"] for row in rows} == set(lebron["game_id"])
    rows = _ok("LeBron James 30 point games with Davis")["finder"]
    together = players[
        (players["player_name"] == "LeBron James")
        & ~players["game_id"].isin(out["Anthony Davis"])
        & (players["pts"] >= 30)
    ]
    assert {row["game_id"] for row in rows} == set(together["game_id"])


def test_team_record_with_scope_after_the_name(sparse_root):
    _, out = sparse_root
    teams = pd.read_csv(FIXTURE / TEAMS)
    games = teams[(teams["team_abbr"] == "LAL") & teams["game_id"].isin(out["Anthony Davis"])]
    row = _ok("Lakers record without Davis this season")["summary"][0]
    assert (row["wins"], row["losses"]) == _team_record(games)
    bos = games[games["opponent_team_abbr"] == "BOS"]
    row = _ok("Lakers record without Davis vs Celtics")["summary"][0]
    assert (row["wins"], row["losses"]) == _team_record(bos)


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        # The bound, then the teammate.
        ("LeBron James games with 30 points and Davis", lambda g: g["pts"] >= 30),
        ("LeBron James games with 30 points with Davis", lambda g: g["pts"] >= 30),
        ("LeBron James games with 10 assists and Davis", lambda g: g["ast"] >= 10),
        ("LeBron James stats with Davis vs Celtics", lambda g: g["opponent_team_abbr"] == "BOS"),
    ],
)
def test_teammate_after_a_bound_or_before_an_opponent(sparse_root, query, keep):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[
        (players["player_name"] == "LeBron James") & ~players["game_id"].isin(out["Anthony Davis"])
    ]
    lebron = lebron[keep(lebron)]
    sections = _ok(query)
    rows = sections.get("finder") or sections["game_log"]
    assert {row["game_id"] for row in rows} == set(lebron["game_id"])


@pytest.mark.parametrize(
    "query",
    [
        # Never his teammate: not read as "with".
        "LeBron James games with Stephen Curry",
        "LeBron James games with 30 points and Curry",
        # A second name who is not a teammate.
        "LeBron stats with Davis and Curry",
        "Lakers record with LeBron and Tatum",
        # Medical/status and unspecified missingness are not participation.
        "Lakers record with Davis and Reaves injured",
        "Lakers record with Davis and Reaves missing",
        "LeBron James stats with Davis and Reaves injured",
    ],
)
def test_unread_availability_still_refuses(sparse_root, query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize("suffix", ["both out", "out", "not playing"])
@pytest.mark.parametrize("subject", ["Lakers record", "LeBron James stats"])
def test_pair_absence_suffixes_apply_both_explicit_observations(sparse_root, suffix, subject):
    root, out = sparse_root
    player = subject.startswith("LeBron")
    games = pd.read_csv(root / PLAYERS) if player else pd.read_csv(FIXTURE / TEAMS)
    own = games.player_name.eq("LeBron James") if player else games.team_abbr.eq("LAL")
    selected = games.loc[own & games.game_id.isin(out["Anthony Davis"] & out["Austin Reaves"])]
    assert not selected.empty
    result = execute_natural_query(f"{subject} with Davis and Reaves {suffix}")
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    assert {row["game_id"] for row in sections["game_log"]} == set(selected.game_id)
    summary = sections["summary"][0]
    assert summary["games"] == len(selected)
    if not player:
        assert (summary["wins"], summary["losses"]) == _team_record(selected)
    for stat in ("pts", "reb", "ast"):
        assert summary[stat + "_avg"] == pytest.approx(selected[stat].mean(), abs=0.001)
    assert result.metadata["without_player"] == "Anthony Davis and Austin Reaves"
    assert result.metadata["with_player"] is None


def test_an_opponent_sitting(sparse_root):
    # "without" an opposing player: the games he did not play.
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[
        (players["player_name"] == "LeBron James")
        & (players["opponent_team_abbr"] == "BOS")
        & players["game_id"].isin(out["Jayson Tatum"])
    ]
    assert len(lebron) > 0
    row = _ok("LeBron James stats vs Celtics without Jayson Tatum")["summary"][0]
    assert (row["games"], row["wins"]) == (len(lebron), int((lebron["wl"] == "W").sum()))


def test_a_name_on_another_team_is_not_read():
    # No Celtic is named Davis: the name stays unresolved and refuses.
    assert execute_natural_query("Celtics record without Davis").result_status == "no_result"


def _lakers() -> pd.DataFrame:
    teams = pd.read_csv(FIXTURE / TEAMS)
    return teams[teams["team_abbr"] == "LAL"]


@pytest.mark.parametrize(
    "query", ["Lakers wins and losses split", "Lakers split by wins and losses"]
)
def test_wins_and_losses_split(query):
    games = _lakers()
    rows = {r["bucket"]: r["games"] for r in _ok(query)["split_comparison"]}
    assert rows == {
        "wins": int((games["wl"] == "W").sum()),
        "losses": int((games["wl"] == "L").sum()),
    }


def test_game_window_is_a_stretch():
    window = _ok("Lakers best 10 game window")["leaderboard"]
    stretch = _ok("Lakers best 10 game stretch")["leaderboard"]
    assert window == stretch


@pytest.mark.parametrize(
    ("query", "count"), [("Lakers biggest blowout", 1), ("Lakers biggest 3 blowouts", 3)]
)
def test_biggest_blowouts_rank_blowout_wins(query, count):
    games = _lakers()
    wins = games[(games["wl"] == "W") & (games["plus_minus"] >= 15)]
    rows = _ok(query)["finder"]
    assert [row["plus_minus"] for row in rows] == wins["plus_minus"].nlargest(count).tolist()


@pytest.mark.parametrize(
    ("query", "both"),
    [
        ("Lakers record with LeBron and Davis", True),
        ("Lakers record with LeBron James and Anthony Davis this season", True),
        ("Lakers record without Davis and Reaves", False),
    ],
)
def test_team_record_with_two_teammates(sparse_root, query, both):
    root, out = sparse_root
    teams = pd.read_csv(FIXTURE / TEAMS)
    games = teams[teams["team_abbr"] == "LAL"]
    if both:
        games = games[~games["game_id"].isin(out["Anthony Davis"])]
    else:
        games = games[
            games["game_id"].isin(out["Anthony Davis"])
            & games["game_id"].isin(out["Austin Reaves"])
        ]
    assert len(games) > 0
    row = _ok(query)["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (len(games), *_team_record(games))


@pytest.mark.parametrize(
    ("query", "both"),
    [
        ("LeBron stats with Davis and Austin", True),
        ("LeBron James stats with Anthony Davis and Austin Reaves", True),
        ("LeBron stats without Davis and Reaves", False),
    ],
)
def test_player_games_with_two_teammates(sparse_root, query, both):
    root, out = sparse_root
    players = pd.read_csv(root / PLAYERS)
    lebron = players[players["player_name"] == "LeBron James"]
    davis = lebron["game_id"].isin(out["Anthony Davis"])
    reaves = lebron["game_id"].isin(out["Austin Reaves"])
    lebron = lebron[~davis & ~reaves] if both else lebron[davis & reaves]
    assert len(lebron) > 0
    row = _ok(query)["summary"][0]
    assert row["games"] == len(lebron)
    assert row["pts_avg"] == pytest.approx(lebron["pts"].mean(), abs=1e-3)
