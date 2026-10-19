"""Boolean checks retain the selected original game, including known false."""

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._latest_original_both import read_request
from nbatools.query_service import execute_natural_query
from tests.test_qualified_played_pair import TATUM
from tests.test_qualified_played_pair import pair_sample as _pair_sample

pair_sample = _pair_sample
pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def _query(names="Tatum and Reaves", scope="last game"):
    return f"Of the Lakers {scope} against Celtics in 2023-24, did BOTH {names} play?"


def _assert_answer(result, game_id, truth):
    assert result.result_status == "ok", result.metadata
    assert result.route == "game_finder"
    assert result.metadata["player"] is None
    assert not result.metadata["with_player"] and not result.metadata["without_player"]
    assert not result.metadata["unsupported_filters"]
    assert result.metadata["team"] == "LAL" and result.metadata["opponent"] == "BOS"
    assert result.metadata["season"] == "2023-24"
    request = next(
        json.loads(n.split(":", 1)[1])
        for n in result.metadata["notes"]
        if n.startswith("yes_no_last_game:")
    )
    assert request["event"] == "played_pair"
    assert set(request["players"]) == {"Jayson Tatum", "Austin Reaves"}
    assert result.metadata["answer_phrase"].startswith("Yes:" if truth else "No:")
    rows = result.result.to_dict()["sections"]["finder"]
    assert [int(row["game_id"]) for row in rows] == [game_id]
    assert rows[0]["team_id"] == 1610612747 and rows[0]["opponent_team_id"] == 1610612738
    assert str(rows[0]["game_date"])[:10] in result.metadata["answer_phrase"]
    filters = result.metadata["applied_filters"]
    assert not any(f["label"] in ("With player", "Without player") for f in filters)
    assert any(
        f["label"] == "Played check"
        and "Jayson Tatum" in f["value"]
        and "Austin Reaves" in f["value"]
        for f in filters
    )
    assert any(f["label"] == "Sample selection" and "original" in f["value"] for f in filters)


@pytest.mark.parametrize("truth", [False, True])
def test_original_row_survives_either_boolean_value(pair_sample, truth):
    latest = pair_sample["ids"][-1]
    if truth:
        ledger = pair_sample["ledger"]
        ledger.loc[ledger.game_id.eq(latest), "participation_state"] = "played"
    result = execute_natural_query(_query())
    _assert_answer(result, latest, truth)
    expected = pair_sample["candidates"].loc[lambda x: x.game_id.eq(latest)].iloc[0]
    row = result.result.to_dict()["sections"]["finder"][0]
    assert [row[k] for k in ("pts", "reb", "ast")] == [expected[k] for k in ("pts", "reb", "ast")]
    if not truth:
        assert "did not both play" in result.metadata["answer_phrase"]


@pytest.mark.parametrize(
    "query",
    [
        _query("Reaves and Tatum"),
        "Did both Tatum and Reaves play in the Lakers' last game against Celtics in 2023-24?",
        "Did Reaves and Tatum both play in the Lakers most recent meeting versus Boston in 2023-24?",
        "Of the LA Lakers latest original game vs BOS during the 2023-24 season, did Tatum and Reaves both play?",
        _query(scope="last one game"),
    ],
)
def test_whole_question_aliases_and_clause_order(pair_sample, query):
    _assert_answer(execute_natural_query(query), pair_sample["ids"][-1], False)


def test_older_unknown_is_not_a_participation_cohort(pair_sample):
    ledger = pair_sample["ledger"]
    mask = ledger.game_id.ne(pair_sample["ids"][-1]) & ledger.participation_state.eq("did_not_play")
    ledger.loc[mask, "participation_state"] = "unknown"
    _assert_answer(execute_natural_query(_query()), pair_sample["ids"][-1], False)


@pytest.mark.parametrize(
    "damage", ["missing", "unknown", "wrong_date", "wrong_side", "contradiction"]
)
def test_first_false_never_hides_unqualified_second(pair_sample, damage):
    ledger = pair_sample["ledger"]
    latest = pair_sample["ids"][-1]
    target = ledger.game_id.eq(latest) & ledger.player_id.eq(TATUM)
    if damage == "missing":
        ledger.drop(ledger.index[target], inplace=True)
    elif damage == "unknown":
        ledger.loc[target, "participation_state"] = "unknown"
    elif damage == "wrong_date":
        ledger.loc[target, "game_date"] = "1900-01-01"
    elif damage == "wrong_side":
        ledger.loc[target, "team_id"] = 1610612752
    else:
        # Synthetic positive minutes on the selected game conflict with its
        # explicit DNP report; this must not become either Boolean answer.
        path = (
            Path(os.environ["NBATOOLS_DATA_ROOT"])
            / "data/raw/player_game_stats/2023-24_regular_season.csv"
        )
        appearances = pd.read_csv(path)
        positive = appearances.loc[appearances.player_id.eq(TATUM)].iloc[[0]].copy()
        positive["game_id"] = latest
        positive["game_date"] = ledger.loc[target, "game_date"].iloc[0]
        positive["team_id"] = 1610612738
        pd.concat([appearances, positive], ignore_index=True).to_csv(path, index=False)
    result = execute_natural_query(_query("Reaves and Tatum"))
    assert result.result_status == "no_result"
    assert result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]
    assert not result.metadata.get("answer_phrase") and not result.metadata.get(
        "participation_check"
    )


def test_static_home_scope_precedes_latest_original_selection(pair_sample):
    candidates = pair_sample["candidates"]
    home = candidates.loc[candidates.is_home.eq(1)].sort_values(["game_date", "game_id"]).iloc[-1]
    result = execute_natural_query(_query(scope="last home game"))
    expected = int(home.game_id)
    _assert_answer(result, expected, bool(expected == pair_sample["ids"][0]))
    assert any(
        f["label"] == "Location" and f["value"] == "Home"
        for f in result.metadata["applied_filters"]
    )


def test_static_date_precedes_original_selection_and_qualification(pair_sample):
    first = pair_sample["candidates"].loc[lambda x: x.game_id.eq(pair_sample["ids"][0])].iloc[0]
    query = _query().replace("in 2023-24", f"on {str(first.game_date)[:10]} in 2023-24")
    _assert_answer(execute_natural_query(query), pair_sample["ids"][0], True)


def test_no_original_game_is_not_known_false(pair_sample, monkeypatch):
    from nbatools.commands import game_summary

    monkeypatch.setattr(
        game_summary, "select_team_summary_sample", lambda **kw: pair_sample["candidates"].iloc[:0]
    )
    result = execute_natural_query(_query())
    assert result.result_status == "no_result" and result.result_reason == "no_match"
    assert not result.metadata.get("answer_phrase") and not result.metadata.get(
        "participation_check"
    )
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "query",
    [
        _query("Blorg and Reaves"),
        _query("Tatum and Blorg"),
        _query("Williams and Reaves"),
        _query("Tatum and Tatum"),
        _query("Tatum and Reaves and LeBron"),
        _query().replace(" play?", " play and score 30 points?"),
        _query().replace(" play?", " play the whole game?"),
        _query().replace(" play?", " play or score 30 points?"),
        _query().replace(" play?", " play and (score 30 points or win)?"),
        _query().replace(" play?", " play if Lakers win?"),
        _query().replace(" play?", " play in the first half?"),
        _query().replace(" play?", " play while LeBron was healthy?"),
        _query().replace(" play?", " not play?"),
        _query().replace(" and ", " or "),
        _query().replace("BOTH", "either"),
        _query(scope="last two games"),
        _query(scope="last qualifying game"),
        _query().replace("2023-24", "2023-24 and 2025-26"),
        _query().replace("2023-24", "2023-25"),
        _query().replace("against Celtics", "against Celtics and Wizards"),
    ],
)
def test_other_positive_obligations_remain_honestly_unfinished(pair_sample, query):
    assert read_request(query) is None
    result = execute_natural_query(query)
    assert not str(result.metadata.get("answer_phrase") or "").startswith(("Yes:", "No:"))
    # No partial single-player result may masquerade as the full BOTH answer.
    assert result.result_status == "no_result", (query, result.metadata)
