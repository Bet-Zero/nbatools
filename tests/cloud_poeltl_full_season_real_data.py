"""Required full-season participation acceptance from recovered native originals.

The original receipt stays unqualified capture metadata. The separately reviewed
finite interval ledger and all three original articles jointly qualify tenure.
Nothing is fetched or published; the existing generalized engine is unchanged.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands._dated_membership import validate_intervals
from nbatools.data_source import data_path, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_multi_team_absence_real_data import build_native_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "working/nba-tools-completion-program/source-evidence/poeltl-full-season-20261106"
ORACLE = json.loads((EVIDENCE / "independent-source-oracle.json").read_text())


def build_qualified_stage(destination, monkeypatch):
    """Install a hash-pinned, independently source-qualified finite ledger."""
    qualification = json.loads((EVIDENCE / "qualification.json").read_text())
    for name, digest in qualification["files"].items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == digest
    root, teams, players = build_native_stage(destination, monkeypatch)
    with ZipFile(EVIDENCE / "collection.zip") as zipped:
        assert set(zipped.namelist()) == {
            "receipt.json",
            "sources/tenure.html",
            "sources/trade.html",
            "sources/return.html",
        }
        assert len(zipped.namelist()) == 4 and zipped.testzip() is None
        receipt_bytes = zipped.read("receipt.json")
        assert receipt_bytes == (EVIDENCE / "capture-receipt.json").read_bytes()
        receipt = json.loads(receipt_bytes)
        assert receipt["classification"] == "original_capture_only_not_qualified"
        assert len(receipt["records"]) == 3
        source_root = root / "data/raw/player_team_membership_sources"
        source_root.mkdir(parents=True)
        for record in receipt["records"]:
            assert record["file"] in {"tenure.html", "trade.html", "return.html"}
            raw = zipped.read("sources/" + record["file"])
            assert len(raw) == record["size_bytes"] and record["http_status"] == 200
            assert hashlib.sha256(raw).hexdigest() == record["sha256"]
            (source_root / (record["sha256"] + ".source")).write_bytes(raw)
    ledger = pd.read_csv(EVIDENCE / "2022-23.csv")
    validate_intervals(ledger, "2022-23")
    assert qualification["unknown_calendar_dates"] == ["2023-02-09"]
    membership = root / "data/raw/player_team_membership"
    membership.mkdir(parents=True)
    shutil.copyfile(EVIDENCE / "2022-23.csv", membership / "2022-23.csv")
    # Portable support chain travels with the ledger; primary row hashes alone
    # do not replace this separate source qualification.
    shutil.copyfile(
        EVIDENCE / "qualification.json", root / "data/metadata/dated_membership_qualification.json"
    )
    return root, teams, players


def _keys(rows):
    return {(int(r["game_id"]), str(r["team_abbr"])) for r in rows}


def _assert_answer(answer, expected):
    assert answer.result_status == "ok", answer.metadata
    sections = answer.result.to_dict()["sections"]
    assert sections["count"] == [{"count": len(expected)}]
    assert _keys(sections.get("finder", [])) == expected
    return answer.result.to_dict()["metadata"]["membership_coverage"]


def test_full_season_qualified_population_and_consumers(tmp_path, monkeypatch):
    base_manifest = None
    if os.environ.get("DATA_SOURCE") == "r2":
        base_manifest = hashlib.sha256(
            data_path("data/metadata/generation_manifest.json").read_bytes()
        ).hexdigest()
        assert base_manifest == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
    root, teams, _ = build_qualified_stage(tmp_path, monkeypatch)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        eligible = {(int(r["game_id"]), r["team"]) for r in ORACLE["eligible_games"]}
        played = {
            (int(r["game_id"]), r["team"])
            for r in ORACLE["eligible_games"]
            if r["status"] == "played"
        }
        missed = eligible - played
        question = "How many games did Jakob Poeltl miss in 2022-23?"
        answer = execute_natural_query(question)
        coverage = _assert_answer(answer, missed)
        raw_points = {(int(r["game_id"]), r["team"]): r["pts"] for r in ORACLE["eligible_games"]}
        returned = answer.result.to_dict()["sections"]["finder"]
        assert all(r["pts"] == raw_points[(int(r["game_id"]), r["team_abbr"])] for r in returned)
        assert sum(r["pts"] for r in returned) == sum(raw_points[key] for key in missed)
        assert coverage["complete"] and coverage["unknown_membership_dates"] == []
        assert coverage["missed_games"] == len(missed)
        audit = coverage["games"]
        assert _keys([r for r in audit if r["membership_state"] == "member"]) == eligible
        assert _keys([r for r in audit if r["participation_state"] == "played"]) == played
        assert _keys([r for r in audit if r["participation_state"] == "did_not_play"]) == missed
        assert not any(r["participation_state"] == "unknown" for r in audit)
        excluded = {
            (int(r["GAME_ID"]), "SAS" if r["TEAM_ID"] == 1610612759 else "TOR")
            for r in ORACLE["excluded_club_games"]
        }
        assert _keys([r for r in audit if r["participation_state"] == "not_member"]) == excluded
        assert sum(r["eligible_games"] for r in coverage["by_team"]) == len(eligible)
        assert sum(r["candidate_games"] for r in coverage["by_team"]) == len(eligible | excluded)
        assert "NBA games" in answer.metadata["answer_phrase"]
        structured = execute_structured_query(
            "game_finder", season="2022-23", membership_player="Jakob Poeltl", limit=1000
        )
        assert structured.result_status == "ok"
        assert _keys(structured.result.to_dict()["sections"]["finder"]) == missed
        client = TestClient(app)
        response = client.post("/query", json={"query": question})
        assert response.status_code == 200 and response.json()["result_status"] == "ok"
        assert _keys(response.json()["result"]["sections"]["finder"]) == missed
        assert response.json()["result"]["sections"]["count"] == [{"count": len(missed)}]
        receipts = []
        for clause, kwargs, predicate in [
            ("at home", {"home_only": True}, lambda r: " vs. " in r["matchup"]),
            ("on the road", {"away_only": True}, lambda r: " @ " in r["matchup"]),
            ("with 105+ team points", {"stat": "pts", "min_value": 105}, lambda r: r["pts"] >= 105),
            (
                "with under 105 team points",
                {"stat": "pts", "max_value": 104.9999},
                lambda r: r["pts"] < 105,
            ),
            ("against the Lakers", {"opponent": "LAL"}, lambda r: r["matchup"].endswith("LAL")),
            ("for the Spurs", {"team": "SAS"}, lambda r: r["team"] == "SAS"),
            ("for the Raptors", {"team": "TOR"}, lambda r: r["team"] == "TOR"),
        ]:
            sample = [r for r in ORACLE["eligible_games"] if predicate(r)]
            expected = {
                (int(r["game_id"]), r["team"]) for r in sample if r["status"] == "explicit_dnp"
            }
            query = f"How many games did Jakob Poeltl miss in 2022-23 {clause}?"
            filtered = execute_natural_query(query)
            got = _assert_answer(filtered, expected)
            assert sum(r["eligible_games"] for r in got["by_team"]) == len(sample)
            direct = execute_structured_query(
                "game_finder",
                season="2022-23",
                membership_player="Jakob Poeltl",
                limit=1000,
                **kwargs,
            )
            assert _keys(direct.result.to_dict()["sections"].get("finder", [])) == expected
            payload = client.post("/query", json={"query": query}).json()
            assert payload["result_status"] == "ok", payload
            assert payload["result"]["sections"]["count"] == [{"count": len(expected)}]
            receipts.append(
                dict(
                    query=query,
                    count=len(expected),
                    eligible=len(sample),
                    game_ids=sorted(g for g, _ in expected),
                    answer=filtered.metadata["answer_phrase"],
                )
            )
        # February9 has no candidate-club game, but date-only membership must
        # still remain honestly unknown; no intraday chronology is fabricated.
        for day, expected_state in [
            ("2023-02-08", "member"),
            ("2023-02-09", "unknown"),
            ("2023-02-10", "member"),
        ]:
            member = execute_structured_query(
                "player_membership", player_id=1627751, date=day, season="2022-23"
            )
            assert (
                member.result.to_dict()["sections"]["summary"][0]["membership_state"]
                == expected_state
            )
        clubs = teams.loc[teams.team_abbr.isin(["SAS", "TOR"])]
        assert not clubs.game_date.eq("2023-02-09").any()
        output = (
            Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
            / "poeltl-full-season"
        )
        output.mkdir(parents=True, exist_ok=True)
        # Standard failing QA harness, isolated to the qualified staged data.
        subprocess.run(
            [
                sys.executable,
                str(REPO / "tools/raw_query_answer_qa.py"),
                "--corpus",
                str(EVIDENCE / "raw-query-corpus.yaml"),
                "--out",
                str(output / "rawqa"),
                "--run-id",
                "qualified-stage",
                "--fail-on-expectation-failure",
            ],
            cwd=REPO,
            check=True,
        )
        summary = json.loads((output / "rawqa/qualified-stage/summary.json").read_text())
        assert summary["case_count"] == 4 and summary["expectation_case_counts"] == {"pass": 4}
        (output / "acceptance.json").write_text(
            json.dumps(
                dict(
                    qualified_version="poeltl-tenure-qualified-v1-20261106",
                    base_manifest=base_manifest,
                    eligible=len(eligible),
                    played=len(played),
                    missed=len(missed),
                    unknown=0,
                    original_receipt_unchanged=True,
                    filtered_answers=receipts,
                    ordinary_answer=answer.metadata["answer_phrase"],
                    production_writes=0,
                ),
                indent=2,
            )
            + "\n"
        )
    finally:
        reset_data_source_cache()


@pytest.mark.parametrize("damage", ["missing_participation", "membership_gap", "source_hash"])
def test_qualified_membership_never_fills_unknown_or_unsafe_inputs(tmp_path, monkeypatch, damage):
    root, _, _ = build_qualified_stage(tmp_path, monkeypatch)
    if damage == "missing_participation":
        path = root / "data/raw/player_game_availability/2022-23_regular_season.csv"
        rows = pd.read_csv(path)
        gid = int(ORACLE["explicit_dnps"][0]["game_id"])
        rows.loc[~(rows.player_id.eq(1627751) & rows.game_id.eq(gid))].to_csv(path, index=False)
    elif damage == "membership_gap":
        path = root / "data/raw/player_team_membership/2022-23.csv"
        rows = pd.read_csv(path)
        rows.loc[rows.team_id.eq(1610612759), "end_date"] = "2023-01-31"
        rows.to_csv(path, index=False)
    else:
        digest = json.loads((EVIDENCE / "capture-receipt.json").read_text())["records"][0]["sha256"]
        (root / "data/raw/player_team_membership_sources" / (digest + ".source")).write_bytes(
            b"corrupted controlled safety probe"
        )
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        answer = execute_natural_query("How many games did Jakob Poeltl miss in 2022-23?")
        assert answer.result_status != "ok", answer.metadata
        assert "count" not in answer.result.to_dict()["sections"]
        if damage != "source_hash":
            assert answer.result_reason == "no_data"
            coverage = answer.result.to_dict()["metadata"]["membership_coverage"]
            assert not coverage["complete"] and coverage["missed_games"] is None
            if damage == "missing_participation":
                assert sum(t["eligible_games"] for t in coverage["by_team"]) == len(
                    ORACLE["eligible_games"]
                )
                assert sum(t["unknown"] for t in coverage["by_team"]) == 1
            else:
                assert coverage["unknown_membership_dates"]
    finally:
        reset_data_source_cache()
