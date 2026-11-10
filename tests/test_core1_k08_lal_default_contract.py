"""Scope/refusal/corruption controls for the three existing staged positives."""

import copy

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.api_handlers import query_result_to_payload
from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands import _seasons
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_core1_k08_lal_default_real_data import (
    PLAYER_IDS,
    QUESTIONS,
    REST_COVERAGE,
    accepted_inputs,
    assert_private_rest,
    assert_public_rest,
    assert_record_body,
    exact_source_player_id,
    full_name_key,
)
from tests.test_core1_k08_served_default_contract import _controlled_answer
from tests.test_qualified_participation_pair import qualified_pair as _qualified_pair

qualified_pair = _qualified_pair


def test_retained_packages_bind_exact_originals_and_complete_accepted_populations():
    packages, docs, coverage = accepted_inputs()
    assert len(packages) == len(docs) == 2
    assert set(QUESTIONS) == {16, 18, 35}
    assert len(coverage["1629029"]["games"]) == len(coverage["1630559"]["games"]) == 82


def test_actual_three_parses_keep_served_default_and_reason_distinction(monkeypatch):
    # Real current name index and parser; only the deliberate served season is fixed.
    monkeypatch.setattr(_seasons, "latest_served_season", lambda kind: "2025-26")
    for ordinal, query in QUESTIONS.items():
        parsed = parse_query(query)
        assert parsed["route"] == "team_record"
        scope = parsed["route_kwargs"]
        assert scope["season"] == "2025-26" and scope["team"] == "LAL"
        assert full_name_key(scope["without_player"]) == full_name_key(
            "Austin Reaves" if ordinal == 35 else "Luka Doncic"
        )
        assert scope.get("without_player_reason") == ("reported_rest" if ordinal == 18 else None)
        assert not scope.get("with_player") and not scope.get("opponent")


@pytest.mark.parametrize(
    "damage", [None, "scope", "wrong_team", "missing_row", "wrong_stat", "missing_stat", "no_data"]
)
def test_complete_binary_record_requires_exact_scope_rows_and_metrics(damage):
    body, case = _controlled_answer()
    case.update(ordinal=16, query=QUESTIONS[16], kwargs=dict(without_player="Luka Doncic"))
    case["source_player_id"] = PLAYER_IDS[16]
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
    case["source_player_id"] = PLAYER_IDS[18]
    body.update(query=case["query"], result_status="no_result", result_reason="no_match")
    meta = body["result"]["metadata"]
    meta.update(
        without_player="Luka Dončić",
        opponent=None,
        without_player_reason="reported_rest",
        applied_filters=[
            dict(
                label="Reported absence reason",
                value="officially reported Rest",
                kind="reported_reason",
            )
        ],
    )
    expected = copy.deepcopy(REST_COVERAGE)
    body["notes"] = [reasons.coverage_note(expected)]
    body["result"]["sections"] = {}
    if damage == "unknown":
        expected.update(unknown=1, reported_other=17, complete=False)
        body["notes"] = [reasons.coverage_note(expected)]
    elif damage == "generic_dnp":
        expected.update(reported_rest=18, reported_other=0)
        body["notes"] = [reasons.coverage_note(expected)]
    elif damage == "no_data":
        body["result_reason"] = "no_data"
    elif damage == "nonempty":
        body["result"]["sections"] = dict(game_log=[{}])
    if damage:
        with pytest.raises(AssertionError):
            assert_record_body(body, case, natural=True)
    else:
        assert_record_body(body, case, natural=True)


@pytest.mark.parametrize("name", ["Luka Doncic", "Luka Dončić", "Luka", "Austin Reaves"])
def test_only_complete_accent_equivalent_subject_maps_to_exact_source_pid(name):
    players = pd.DataFrame([dict(player_id=1629029, player_name="Luka Dončić")])
    if name in {"Luka Doncic", "Luka Dončić"}:
        assert exact_source_player_id(players, name) == 1629029
    else:
        with pytest.raises(AssertionError):
            exact_source_player_id(players, name)


def test_ambiguous_full_name_source_identity_is_rejected():
    players = pd.DataFrame(
        [
            dict(player_id=1629029, player_name="Luka Dončić"),
            dict(player_id=999, player_name="Luka Doncic"),
        ]
    )
    with pytest.raises(AssertionError):
        exact_source_player_id(players, "Luka Doncic")


@pytest.mark.parametrize("missing", [False, True])
def test_native_api_rest_contract_preserves_private_proof_and_public_audit_note(
    qualified_pair, monkeypatch, missing
):
    # Existing controlled explicit participation fixture, actual engine/service/API.
    observations = (
        qualified_pair["ledger"]
        .loc[lambda f: f.player_id.eq(203076) & f.participation_state.eq("did_not_play")]
        .copy()
    )
    assert len(observations) == 2
    observations["reported_reason"] = "reported_other"
    if missing:
        observations = observations.iloc[:0].copy()
    monkeypatch.setattr(reasons, "load_observations", lambda *args: observations.copy())
    query = "Lakers record when Davis rests vs Celtics in 2023-24"
    kwargs = dict(
        team="LAL",
        season="2023-24",
        opponent="BOS",
        without_player="Anthony Davis",
        without_player_reason="reported_rest",
    )
    expected = dict(
        REST_COVERAGE, requested_games=4, qualified_nonparticipations=2, reported_other=2
    )
    results = [execute_natural_query(query), execute_structured_query("team_record", **kwargs)]
    client = TestClient(app)
    responses = [
        client.post("/query", json=dict(query=query)),
        client.post("/structured-query", json=dict(route="team_record", kwargs=kwargs)),
    ]
    for result in results:
        if missing:
            assert result.result_status == "no_result" and result.result_reason == "no_data"
            assert result.result.metadata["reported_reason_coverage"]["unknown"] == 2
            with pytest.raises(AssertionError):
                assert_private_rest(result, expected)
        else:
            assert_private_rest(result, expected)
    for body in [
        *[query_result_to_payload(result) for result in results],
        *[r.json() for r in responses],
    ]:
        assert "reported_reason_basis" not in body["result"]["metadata"]
        assert "reported_reason_coverage" not in body["result"]["metadata"]
        if missing:
            assert body["result_status"] == "no_result" and body["result_reason"] == "no_data"
            with pytest.raises(AssertionError):
                assert_public_rest(body, expected)
        else:
            assert_public_rest(body, expected)
    assert all(response.status_code == 200 for response in responses)
