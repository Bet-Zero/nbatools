"""A scalar played question checks one original game, not appearance omission."""

import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query
from tests.test_qualified_played_pair import TATUM
from tests.test_qualified_played_pair import pair_sample as _pair_sample

pair_sample = _pair_sample
pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def query(name="Tatum", extra=""):
    return f"Did {name} play in the Lakers last game against Celtics {extra} in 2023-24?"


def assert_scalar(result, game_id, name, truth):
    assert result.result_status == "ok", result.metadata
    assert result.route == "game_finder" and result.metadata["intent"] == "finder"
    assert result.metadata["player"] == name
    assert result.metadata["player_context"]["player_name"] == name
    assert set(result.metadata["player_context"]) == {"player_id", "player_name"}
    assert result.metadata["stat"] is None
    assert result.metadata["min_value"] is None and result.metadata["max_value"] is None
    assert not result.metadata["threshold_conditions"]
    assert not result.metadata["with_player"] and not result.metadata["without_player"]
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith(f"{'Yes' if truth else 'No'}: {name} ")
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == game_id
    assert rows[0]["team_id"] == 1610612747 and rows[0]["opponent_team_id"] == 1610612738
    assert not any(k in rows[0] for k in ("player_id", "player_name", "player"))
    assert str(rows[0]["game_date"])[:10] in phrase
    filters = result.metadata["applied_filters"]
    assert {"kind": "player", "label": "Played check", "value": name + " played"} in filters
    assert not any(f["label"] in ("With player", "Without player") for f in filters)
    assert any(
        "team-game totals" in c and "not the checked player's statistics" in c
        for c in result.result.caveats
    )


@pytest.mark.parametrize("name,canonical", [("Tatum", "Jayson Tatum"), ("Reaves", "Austin Reaves")])
def test_explicit_dnp_no_keeps_original_team_evidence(pair_sample, name, canonical):
    latest = pair_sample["ids"][-1]
    result = execute_natural_query(query(name))
    assert_scalar(result, latest, canonical, False)
    original = pair_sample["candidates"].loc[lambda d: d.game_id.eq(latest)].iloc[0]
    row = result.result.to_dict()["sections"]["finder"][0]
    assert [row[k] for k in ("pts", "reb", "ast")] == [original[k] for k in ("pts", "reb", "ast")]
    assert ": 0 points" not in result.metadata["answer_phrase"]


def test_date_scope_precedes_played_check_and_stat_line_uses_same_game(pair_sample):
    first = pair_sample["candidates"].loc[lambda d: d.game_id.eq(pair_sample["ids"][0])].iloc[0]
    result = execute_natural_query(query(extra="on " + str(first.game_date)[:10]))
    assert_scalar(result, int(first.game_id), "Jayson Tatum", True)
    path = (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2023-24_regular_season.csv"
    )
    raw = pd.read_csv(path)
    actual = raw.loc[raw.game_id.eq(first.game_id) & raw.player_id.eq(TATUM)].iloc[0]
    for metric, word in [("pts", "points"), ("reb", "rebounds"), ("ast", "assists")]:
        assert f"{actual[metric]:g} {word}" in result.metadata["answer_phrase"]


@pytest.mark.parametrize("damage", ["missing", "unknown", "wrong_date", "wrong_side"])
def test_unqualified_selected_game_cannot_be_no_or_old_appearance(pair_sample, damage):
    ledger = pair_sample["ledger"]
    mask = ledger.game_id.eq(pair_sample["ids"][-1]) & ledger.player_id.eq(TATUM)
    if damage == "missing":
        ledger.drop(ledger.index[mask], inplace=True)
    elif damage == "unknown":
        ledger.loc[mask, "participation_state"] = "unknown"
    elif damage == "wrong_date":
        ledger.loc[mask, "game_date"] = "1900-01-01"
    else:
        ledger.loc[mask, "team_id"] = 1610612752
    result = execute_natural_query(query())
    assert_unavailable(result)
    assert result.metadata["player"] == "Jayson Tatum"


def assert_unavailable(result):
    assert result.result_status == "no_result"
    assert not result.metadata.get("answer_phrase")
    assert not result.result.to_dict()["sections"]
    assert not any(
        f["label"] == "Played check" for f in result.metadata.get("applied_filters") or []
    )


def test_known_name_without_game_day_membership_is_unknown_not_no(pair_sample):
    result = execute_natural_query(query("Stephen Curry"))
    assert_unavailable(result)
    assert result.metadata["player"] == "Stephen Curry"


@pytest.mark.parametrize(
    "q",
    [
        "For the Lakers latest meeting against Boston in 2023-24, did Jayson Tatum play?",
        "In the Lakers most recent matchup against Celtics in 2023-24, did Tatum play?",
        "Did Tatum play in the Lakers' last one game versus the Celtics in 2023-24?",
    ],
)
def test_complete_scalar_scope_wording_uses_shared_original_selector(pair_sample, q):
    assert_scalar(execute_natural_query(q), pair_sample["ids"][-1], "Jayson Tatum", False)


@pytest.mark.parametrize(
    "q",
    [
        query("Blorg"),
        query("Tatum and Reaves"),
        query(extra="while LeBron was healthy"),
        query().replace("play in", "play 30 minutes in"),
        query().replace("last game", "last two games"),
        query().replace("last game", "last qualifying game"),
        query().replace("last game", "last playoff game"),
        query().replace("play in", "play the first half in"),
        query().replace("play in", "play on the court in"),
        query().replace("play in", "play for"),
    ],
)
def test_unread_scope_never_receives_partial_boolean_or_player_stat_claim(pair_sample, q):
    result = execute_natural_query(q)
    assert_unavailable(result)
    assert not result.metadata.get("with_player") and not result.metadata.get("without_player")


@pytest.fixture
def explicit_lebron_dnp(tmp_path, monkeypatch):
    """Synthetic game-day DNP stipulation, not proof from deleting an appearance."""
    root = tmp_path / "fixture"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    teams = pd.read_csv(root / "data/raw/team_game_stats/2025-26_regular_season.csv")
    original = teams.loc[teams.team_abbr.eq("LAL")].sort_values(["game_date", "game_id"]).iloc[-1]
    players = pd.read_csv(path)
    players = players.loc[~(players.game_id.eq(original.game_id) & players.player_id.eq(2544))]
    players.to_csv(path, index=False)
    ledger = pd.DataFrame(
        [
            dict(
                game_id=int(original.game_id),
                game_date=original.game_date,
                team_id=1610612747,
                player_id=2544,
                player_name="LeBron James",
                participation_state="did_not_play",
            )
        ]
    )
    monkeypatch.setattr(observations, "load_observations", lambda *args: ledger.copy())
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    yield original
    reset_data_source_cache()


def test_selected_positive_report_conflict_cannot_be_a_scalar_answer(pair_sample):
    latest = pair_sample["ids"][-1]
    ledger = pair_sample["ledger"]
    day = ledger.loc[ledger.game_id.eq(latest), "game_date"].iloc[0]
    path = (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2023-24_regular_season.csv"
    )
    players = pd.read_csv(path)
    positive = players.loc[players.player_id.eq(TATUM)].iloc[[0]].copy()
    positive["game_id"], positive["game_date"] = latest, day
    pd.concat([players, positive], ignore_index=True).to_csv(path, index=False)
    assert_unavailable(execute_natural_query(query()))


def test_no_original_game_has_no_boolean(pair_sample, monkeypatch):
    from nbatools.commands import game_summary

    monkeypatch.setattr(
        game_summary, "select_team_summary_sample", lambda **kw: pair_sample["candidates"].iloc[:0]
    )
    assert_unavailable(execute_natural_query(query()))


def test_old_appearance_team_is_not_membership_on_the_selected_game(pair_sample):
    # Hypothetical fixture: historical appearances were for LAL, while the
    # selected game's explicit DNP lists the player for BOS. A bare request
    # cannot certify the historical team's latest game as his own-team target.
    path = (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2023-24_regular_season.csv"
    )
    players = pd.read_csv(path)
    own = players.player_id.eq(TATUM)
    players.loc[own, ["team_id", "team_abbr", "team_name"]] = [
        1610612747,
        "LAL",
        "Los Angeles Lakers",
    ]
    players.to_csv(path, index=False)
    ledger = pair_sample["ledger"]
    ledger.loc[ledger.player_id.eq(TATUM) & ledger.participation_state.eq("played"), "team_id"] = (
        1610612747
    )
    result = execute_natural_query("Did Tatum play last game in 2023-24?")
    assert_unavailable(result)
    assert result.metadata["team"] is None and not result.metadata.get("team_context")
    assert result.metadata["player_context"]["player_id"] == TATUM


@pytest.mark.parametrize(
    "q",
    [
        "Did LeBron play in his team's last game?",
        "Has LeBron played in the Lakers last game?",
        "Did Curry play in his last game?",
    ],
)
def test_basic_qualified_positive_legacy_forms_keep_the_actual_same_game(q):
    # Committed synthetic fixture has a positive appearance on these teams'
    # latest game. This is a Yes proof, not an absence inference.
    result = execute_natural_query(q)
    assert result.result_status == "ok" and result.route == "game_finder"
    name = "Stephen Curry" if "Curry" in q else "LeBron James"
    assert result.metadata["answer_phrase"].startswith("Yes: " + name + " played")
    assert "points" in result.metadata["answer_phrase"]
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and str(rows[0]["game_date"])[:10] in result.metadata["answer_phrase"]
    assert not any(k in rows[0] for k in ("player_id", "player_name"))


@pytest.mark.parametrize(
    "predicate,check",
    [
        ("at least 30 minutes", lambda row: row.minutes >= 30),
        ("fewer than 30 minutes", lambda row: row.minutes < 30),
        (
            "at least 40 minutes or score at least 20 points",
            lambda row: row.minutes >= 40 or row.pts >= 20,
        ),
        (
            "at least 40 minutes or score at least 30 points",
            lambda row: row.minutes >= 40 or row.pts >= 30,
        ),
        ("at least 40 minutes or win", lambda row: row.minutes >= 40 or row.wl == "W"),
        ("at least 40 minutes or lose", lambda row: row.minutes >= 40 or row.wl == "L"),
        (
            "at least 30 minutes and score at least 20 points",
            lambda row: row.minutes >= 30 and row.pts >= 20,
        ),
        (
            "at least 30 minutes and score at least 30 points",
            lambda row: row.minutes >= 30 and row.pts >= 30,
        ),
        ("at least 30 minutes and win", lambda row: row.minutes >= 30 and row.wl == "W"),
        ("at least 30 minutes and lose", lambda row: row.minutes >= 30 and row.wl == "L"),
    ],
)
def test_existing_minutes_checks_keep_player_statistical_consumer(predicate, check):
    games = pd.read_csv(
        "qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_regular_season.csv"
    )
    original = games.loc[games.player_id.eq(2544)].sort_values(["game_date", "game_id"]).iloc[-1]
    result = execute_natural_query(f"Did LeBron play {predicate} last game?")
    assert result.result_status == "ok" and result.route == "player_game_finder"
    assert result.metadata["answer_phrase"].startswith("Yes:" if check(original) else "No:")
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == int(original.game_id)
    assert rows[0]["player_id"] == 2544
    assert rows[0]["minutes"] == original.minutes
    assert not any(f["label"] == "Played check" for f in result.metadata["applied_filters"])


@pytest.mark.parametrize(
    "predicate",
    [
        "and win",
        "and score at least 20 points",
        "at least 30 minutes while healthy",
        "at least 30 minutes and play the whole game",
        "at least 30 minutes while Reaves plays",
        "at least 30 minutes and do a backflip",
        "at least 30 minutes or win while healthy",
        "at least 30 minutes or play the whole game",
        "at least 30 minutes or Reaves plays",
        "at least 30 minutes or score at least 20 points and win",
    ],
)
def test_statistical_note_cannot_hide_unqualified_presence_or_unread_tail(predicate):
    result = execute_natural_query(f"Did LeBron play {predicate} last game?")
    assert_unavailable(result)
    assert not result.metadata.get("player_context")
