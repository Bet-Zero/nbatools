"""Scope/refusal/corruption controls for the three existing staged positives."""

import copy

import pytest

from nbatools.commands import _seasons
from nbatools.commands import entity_resolution as er
from nbatools.commands.natural_query import parse_query
from tests.cloud_core1_k08_lal_default_real_data import (
    NATURAL_PLAYERS,
    QUESTIONS,
    accepted_inputs,
    assert_record_body,
)
from tests.test_core1_k08_served_default_contract import _controlled_answer


def test_retained_packages_bind_exact_originals_and_complete_accepted_populations():
    packages, docs, coverage = accepted_inputs()
    assert len(packages) == len(docs) == 2
    assert set(QUESTIONS) == {16, 18, 35}
    assert len(coverage["1629029"]["games"]) == len(coverage["1630559"]["games"]) == 82


def test_actual_three_parses_keep_served_default_and_reason_distinction(monkeypatch, request):
    er.reset_player_index()
    request.addfinalizer(er.reset_player_index)
    monkeypatch.setattr(er, "data_source_cache_key", lambda: "lal-default-three-contract")
    monkeypatch.setattr(
        er, "_read_player_names", lambda data_dir=None: {"Luka Dončić", "Austin Reaves"}
    )
    monkeypatch.setattr(_seasons, "latest_served_season", lambda kind: "2025-26")
    for ordinal, query in QUESTIONS.items():
        parsed = parse_query(query)
        assert parsed["route"] == "team_record"
        scope = parsed["route_kwargs"]
        assert scope["season"] == "2025-26" and scope["team"] == "LAL"
        assert scope["without_player"] == NATURAL_PLAYERS[ordinal]
        assert scope.get("without_player_reason") == ("reported_rest" if ordinal == 18 else None)
        assert not scope.get("with_player") and not scope.get("opponent")


@pytest.mark.parametrize(
    "damage", [None, "scope", "wrong_team", "missing_row", "wrong_stat", "missing_stat", "no_data"]
)
def test_complete_binary_record_requires_exact_scope_rows_and_metrics(damage):
    body, case = _controlled_answer()
    case.update(ordinal=16, query=QUESTIONS[16], kwargs=dict(without_player="Luka Doncic"))
    case["expected"]["rows"][0]["wl"] = "W"
    body["result"]["sections"]["game_log"][0]["wl"] = "W"
    for row in (case["expected"]["rows"][0], body["result"]["sections"]["game_log"][0]):
        row.update(opponent_team_id=1610612738, opponent_team_abbr="BOS")
    body.update(query=case["query"])
    body["result"]["metadata"].update(without_player="Luka Dončić", opponent=None)
    if damage == "scope":
        body["result"]["metadata"]["with_player"] = "LeBron James"
    elif damage == "wrong_team":
        body["result"]["sections"]["game_log"][0]["team_id"] = 1610612738
    elif damage == "missing_row":
        body["result"]["sections"]["game_log"] = []
    elif damage == "wrong_stat":
        body["result"]["sections"]["game_log"][0]["fgm"] = 99
    elif damage == "missing_stat":
        body["result"]["sections"]["game_log"][0].pop("fg3a")
    elif damage == "no_data":
        body.update(result_status="no_result", result_reason="no_data")
    if damage:
        with pytest.raises((AssertionError, KeyError)):
            assert_record_body(body, case, natural=True)
    else:
        assert_record_body(body, case, natural=True)


@pytest.mark.parametrize("damage", [None, "unknown", "generic_dnp", "no_data", "nonempty"])
def test_reported_rest_zero_requires_complete_source_reason_denominator(damage):
    body, case = copy.deepcopy(_controlled_answer())
    case.update(ordinal=18, query=QUESTIONS[18], kwargs=dict(without_player="Luka Doncic"))
    body.update(query=case["query"], result_status="no_result", result_reason="no_match")
    meta = body["result"]["metadata"]
    meta.update(
        without_player="Luka Dončić",
        opponent=None,
        reported_reason_basis="officially reported Rest",
        reported_reason_coverage=dict(
            basis="officially reported Rest",
            complete=True,
            requested_games=82,
            qualified_nonparticipations=18,
            reported_rest=0,
            reported_other=18,
            unknown=0,
        ),
    )
    body["result"]["sections"] = {}
    if damage == "unknown":
        meta["reported_reason_coverage"].update(unknown=1, reported_other=17, complete=False)
    elif damage == "generic_dnp":
        meta["reported_reason_coverage"].update(reported_rest=18, reported_other=0)
    elif damage == "no_data":
        body["result_reason"] = "no_data"
    elif damage == "nonempty":
        body["result"]["sections"] = dict(game_log=[{}])
    if damage:
        with pytest.raises(AssertionError):
            assert_record_body(body, case, natural=True)
    else:
        assert_record_body(body, case, natural=True)
