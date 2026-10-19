"""A two-player played conjunction retains both sides and original coverage."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
LAL, BOS = 1610612747, 1610612738
TATUM, REAVES = 1628369, 1630559
PAIR = "Jayson Tatum and Austin Reaves"


@pytest.fixture
def pair_sample(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    suffix = "2023-24_regular_season.csv"
    team_path = root / "data/raw/team_game_stats" / suffix
    player_path = root / "data/raw/player_game_stats" / suffix
    teams, players = pd.read_csv(team_path), pd.read_csv(player_path)
    candidates = teams.loc[teams.team_id.eq(LAL) & teams.opponent_team_id.eq(BOS)]
    ids = sorted(candidates.game_id.unique())[:4]
    assert len(ids) == 4
    omitted_games = set(candidates.game_id) - set(ids)
    teams = teams.loc[~teams.game_id.isin(omitted_games)]
    players = players.loc[~players.game_id.isin(omitted_games)]
    candidates = teams.loc[teams.team_id.eq(LAL) & teams.game_id.isin(ids)].copy()
    # Independent synthetic stipulation: both, opponent only, own only, neither.
    states = [{TATUM, REAVES}, {TATUM}, {REAVES}, set()]
    evidence = []
    for game in candidates.itertuples():
        played = states[ids.index(game.game_id)]
        for pid, team, name in [(TATUM, BOS, "Jayson Tatum"), (REAVES, LAL, "Austin Reaves")]:
            evidence.append(
                dict(
                    game_id=int(game.game_id),
                    team_id=team,
                    player_id=pid,
                    player_name=name,
                    game_date=game.game_date,
                    participation_state="played" if pid in played else "did_not_play",
                )
            )
            if pid not in played:
                players = players.loc[
                    ~(players.game_id.eq(game.game_id) & players.player_id.eq(pid))
                ]
    teams.to_csv(team_path, index=False)
    players.to_csv(player_path, index=False)
    ledger = pd.DataFrame(evidence)
    monkeypatch.setattr(observations, "load_observations", lambda *args: ledger.copy())
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    yield dict(ids=ids, ledger=ledger, candidates=candidates)
    reset_data_source_cache()


def assert_pair(result, fixture):
    assert result.result_status == "ok", (result.result_reason, result.metadata)
    assert result.route == "team_record"
    assert result.metadata["with_player"] in [PAIR, "Austin Reaves and Jayson Tatum"]
    assert not result.metadata["without_player"] and result.metadata["player"] is None
    assert not result.metadata["unsupported_filters"]
    assert result.metadata["opponent_context"]["team_abbr"] == "BOS"
    assert {
        "label": "With player",
        "value": result.metadata["with_player"],
        "kind": "player",
    } in result.metadata["applied_filters"]
    sections = result.result.to_dict()["sections"]
    rows = sections["game_log"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == fixture["ids"][0]
    assert rows[0]["team_id"] == LAL and rows[0]["opponent_team_id"] == BOS
    expected = (
        fixture["candidates"].loc[fixture["candidates"].game_id.eq(fixture["ids"][0])].iloc[0]
    )
    summary = sections["summary"][0]
    assert summary["games"] == 1 and summary["wins"] == int(expected.wl == "W")
    for stat in ["pts", "reb", "ast"]:
        assert rows[0][stat] == expected[stat] == summary[stat + "_avg"]


@pytest.mark.parametrize(
    "clause",
    [
        "with Jayson Tatum playing while Austin Reaves plays",
        "when Jayson Tatum plays and Austin Reaves plays",
        "with Jayson Tatum playing, Austin Reaves plays",
        "with Jayson Tatum playing, and Austin Reaves playing",
        "with Jayson Tatum, Austin Reaves playing",
        "with Tatum, and Reaves playing",
        "with Tatum and Reaves both playing",
        "when Tatum and Reaves play",
        "with Tatum and Reaves",
        "with Reaves playing while Tatum plays",
    ],
)
def test_played_conjunction_selects_intersection_with_both_side_labels(pair_sample, clause):
    assert_pair(
        execute_natural_query(f"Lakers record against Celtics {clause} in 2023-24"), pair_sample
    )


@pytest.mark.parametrize("pair", [PAIR, "Austin Reaves and Jayson Tatum"])
def test_existing_structured_conjunction_is_same_sample(pair_sample, pair):
    assert_pair(
        execute_structured_query(
            "team_record", team="LAL", opponent="BOS", with_player=pair, season="2023-24"
        ),
        pair_sample,
    )


@pytest.mark.parametrize("scope", ["last 1 game"])
def test_unfinished_bare_pair_temporal_composition_never_opens_wrong_sample(pair_sample, scope):
    """The bare reading retains the previous new-pair boundary."""
    result = execute_natural_query(
        f"Lakers record against Celtics {scope} with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
    assert "multi_player_availability" in result.metadata["unsupported_filters"]
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "clause",
    [
        "with Tatum playing while Blorg plays",
        "with Blorg playing while Reaves plays",
        "with Tatum and Williams playing",
        "with Tatum playing while Reaves sits",
        "without Tatum while Reaves plays",
        "with Tatum playing while Reaves plays 35 minutes",
        "with Tatum playing while Reaves plays and scores 30 points",
        "with Tatum playing while Reaves plays and he scores at least 24",
        "with Tatum healthy while Reaves plays",
        "with Tatum and Reaves available",
        "with Tatum and Reaves on the court",
        "with Tatum playing while Reaves plays while LeBron plays",
        "with LeBron with Tatum and Reaves playing",
        "with Blorg with Tatum and Reaves playing",
        "with Tatum playing or Reaves plays",
        "with Tatum and Reaves playing if LeBron plays",
        "not with Tatum playing while Reaves plays",
        "with neither Tatum playing nor Reaves playing",
    ],
)
def test_unread_composition_cannot_become_qualified_pair_or_empty(pair_sample, clause):
    result = execute_natural_query(f"Lakers record against Celtics {clause} in 2023-24")
    assert result.result_status == "no_result", result.metadata
    assert result.result_reason != "no_match", result.metadata
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("damage", ["missing", "unknown", "wrong_date", "conflicting_team"])
def test_false_first_predicate_cannot_hide_second_unknown(pair_sample, damage):
    ledger = pair_sample["ledger"]
    # Game3: Tatum is explicitly DNP, so no positive row can fill missing
    # evidence; Reaves DNP first must not short-circuit the original sample.
    mask = ledger.game_id.eq(pair_sample["ids"][3]) & ledger.player_id.eq(TATUM)
    if damage == "missing":
        ledger.drop(ledger.index[mask], inplace=True)
    elif damage == "unknown":
        ledger.loc[mask, "participation_state"] = "unknown"
    elif damage == "wrong_date":
        ledger.loc[mask, "game_date"] = "1900-01-01"
    else:
        ledger.loc[mask, "team_id"] = LAL
    result = execute_natural_query(
        "Lakers record against Celtics with Reaves playing while Tatum plays in 2023-24"
    )
    assert result.result_status == "no_result"
    assert result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]
