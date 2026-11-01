"""Original mixed windows use unchanged published participation and raw game order."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.api_handlers import query_result_to_payload
from nbatools.data_source import data_path, data_read_csv, data_read_text
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
GENERATION = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
SUFFIX = "2025-26_regular_season.csv"
LAL, LEBRON, LUKA = 1610612747, 2544, 1629029
QA_CASES = [
    "k08_original_mixed_record",
    "k08_original_mixed_team_bound",
    "k08_original_mixed_qualified_empty",
]


def _assert_answer(payload, expected):
    if expected.empty:
        assert payload["result_status"] == "no_result" and payload["result_reason"] == "no_match"
        assert not payload["result"]["sections"]
        return
    assert payload["result_status"] == "ok"
    sections = payload["result"]["sections"]
    assert {int(row["game_id"]) for row in sections["game_log"]} == set(
        expected.game_id.astype(int)
    )
    row = sections["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (
        len(expected),
        int(expected.wl.eq("W").sum()),
        int(expected.wl.eq("L").sum()),
    )
    assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)


def test_original_mixed_windows_keep_raw_population_and_execute_registered_cases(
    tmp_path, monkeypatch
):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == GENERATION
    manifest_raw = data_read_text("data/metadata/generation_manifest.json")
    assert hashlib.sha256(manifest_raw.encode()).hexdigest() == MANIFEST
    manifest = json.loads(manifest_raw)
    paths = {
        f"raw/{kind}/{SUFFIX}"
        for kind in ("team_game_stats", "player_game_stats", "player_game_availability")
    }
    bindings = [row for row in manifest["files"] if row["path"] in paths]
    assert {row["path"] for row in bindings} == paths
    for row in bindings:
        raw = data_path("data/" + row["path"]).read_bytes()
        assert len(raw) == row["size_bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    teams = data_read_csv("data/raw/team_game_stats/" + SUFFIX)
    teams = teams.loc[teams.team_id.eq(LAL)].sort_values(["game_date", "game_id"])
    players = data_read_csv("data/raw/player_game_stats/" + SUFFIX)
    ledger = data_read_csv("data/raw/player_game_availability/" + SUFFIX)
    assert len(teams) == teams.game_id.nunique() == 82 and len(ledger) == 804
    own = players.loc[players.team_id.eq(LAL) & players.minutes.gt(0)]
    absent = ledger.loc[
        ledger.player_id.eq(LEBRON)
        & ledger.team_id.eq(LAL)
        & ledger.participation_state.eq("did_not_play")
    ]
    dnp = set(absent.game_id.astype(int))
    played = set(own.loc[own.player_id.eq(LEBRON), "game_id"].astype(int))
    luka = own.loc[own.player_id.eq(LUKA)]
    positive = set(luka.game_id.astype(int))
    assert len(dnp) == len(absent) == 22 and len(played) == 60 and len(positive) == 64
    assert not dnp & played and dnp | played == set(teams.game_id.astype(int))
    dates = {int(row.game_id): pd.Timestamp(row.game_date).date() for row in teams.itertuples()}
    for rows in (absent, own.loc[own.player_id.isin([LEBRON, LUKA])]):
        assert not rows.duplicated(["game_id", "player_id"]).any()
        for row in rows.itertuples():
            assert pd.Timestamp(row.game_date).date() == dates[int(row.game_id)]
    matches = dnp & positive
    original = teams.tail(20).loc[lambda frame: frame.game_id.isin(matches)]
    qualifying = teams.loc[teams.game_id.isin(matches)].tail(20)
    assert set(original.game_id.astype(int)) == {22500914, 22500922, 22500946}
    assert (len(original), int(original.wl.eq("W").sum()), int(original.pts.sum())) == (3, 3, 358)
    assert (len(qualifying), int(qualifying.wl.eq("W").sum()), int(qualifying.pts.sum())) == (
        15,
        11,
        1736,
    )
    empty = teams.tail(10).loc[lambda frame: frame.game_id.isin(matches)]
    assert empty.empty
    threshold = original.loc[original.pts.ge(120)]
    assert set(threshold.game_id.astype(int)) == {22500914, 22500946}
    assert int(threshold.pts.sum()) == 248

    output = (
        Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "original-mixed-window"
    )
    output.mkdir(parents=True, exist_ok=False)
    for name, frame in [
        ("team82.csv", teams),
        ("lebron-explicit-dnp.csv", absent),
        ("actor-positive-rows.csv", own.loc[own.player_id.isin([LEBRON, LUKA])]),
    ]:
        frame.to_csv(output / name, index=False)
    from fastapi.testclient import TestClient

    from nbatools.api import app

    client = TestClient(app)
    answers = []
    for n, floor, expected in [(20, None, original), (20, 120, threshold), (10, None, empty)]:
        question = f"Lakers record within their last {n} games without LeBron James and with Luka Doncic in 2025-26"
        if floor is not None:
            question += " where the Lakers scored at least 120 points"
        natural = execute_natural_query(question)
        structured = execute_structured_query(
            "team_record",
            team="LAL",
            season="2025-26",
            with_player="Luka Doncic",
            without_player="LeBron James",
            last_n=n,
            last_n_scope="original_window",
            **(dict(stat="pts", min_value=floor) if floor else {}),
        )
        for result in [natural, structured]:
            _assert_answer(query_result_to_payload(result), expected)
            assert (
                result.route == "team_record"
                and result.metadata["last_n_scope"] == "original_window"
            )
            assert (
                result.metadata["player"] is None
                and result.metadata["without_player"] == "LeBron James"
            )
            assert any(
                "before checking participation" in item["value"]
                for item in result.metadata["applied_filters"]
            )
        response = client.post("/query", json={"query": question})
        assert response.status_code == 200
        _assert_answer(response.json(), expected)
        answers.append(
            dict(
                query=question,
                original_window_game_ids=sorted(teams.tail(n).game_id.astype(int)),
                selected_game_ids=sorted(expected.game_id.astype(int)),
                games=len(expected),
                wins=int(expected.wl.eq("W").sum()),
                losses=int(expected.wl.eq("L").sum()),
                points=int(expected.pts.sum()),
            )
        )
    legacy = execute_natural_query(
        "Lakers record in their last 20 qualifying games without LeBron James and with Luka Doncic in 2025-26"
    )
    _assert_answer(query_result_to_payload(legacy), qualifying)
    assert legacy.metadata["last_n_scope"] == "qualifying"
    receipt = dict(
        classification="read_only_existing_published_population_original_window_acceptance",
        generation=GENERATION,
        manifest_sha256=MANIFEST,
        source_files=bindings,
        absence_population=82,
        luka_role="positive_appearances_only_no_complete_DNP_claim",
        answers=answers,
        registered_raw_qa_cases=QA_CASES,
        subset_sha256={
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in output.glob("*.csv")
        },
        production_writes=0,
    )
    from tools.raw_query_answer_qa import main as raw_qa

    with monkeypatch.context() as scope:
        scope.setattr(
            "sys.argv",
            [
                "raw-query-answer-qa",
                "--out",
                str(output / "raw-qa"),
                "--run-id",
                "original-mixed-window",
                *[item for case in QA_CASES for item in ("--case", case)],
                "--fail-on-expectation-failure",
            ],
        )
        assert raw_qa() == 0
    qa_directory = output / "raw-qa/original-mixed-window"
    summary = json.loads((qa_directory / "summary.json").read_bytes())
    rows = [json.loads(line) for line in (qa_directory / "report.jsonl").read_text().splitlines()]
    assert summary["case_count"] == 3 and summary["expectation_case_counts"] == {"pass": 3}
    assert len(rows) == 3 and {row["id"] for row in rows} == set(QA_CASES)
    receipt["raw_qa_executed"] = summary["case_count"]
    receipt["raw_qa_passed"] = summary["expectation_case_counts"]["pass"]
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
