"""Compose accepted participation evidence once; no NBA collection or publication."""

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.data_source import data_generation_context, data_path
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_reported_rest_stage_real_data import _capture, _write_inventory
from tools.compose_participation_overlays import compose_overlays
from tools.participation_coverage import build_report

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
PACKAGES = [
    (
        EVIDENCE / "k08-lal-remaining/staged-acceptance-source.zip",
        "a18792e51f036cfbffc509c7990ee403fbbd70edc59bd1b0fa0d4cbff3a1eb03",
    ),
    (
        EVIDENCE / "k08-bos-remaining/staged-acceptance-source.zip",
        "4883c4291a74ab1139af9fd97c5242a2dcd6928cb0a994d68adebb41079df692",
    ),
    (
        EVIDENCE / "k08-direct-dependencies/staged-acceptance-source.zip",
        "3b09d74c9deb5915033b3b28518a5926056e7c37ede6a0f24281d41a337312db",
    ),
    (
        EVIDENCE / "k08-rest/staging-acceptance-source.zip",
        "f2c4461403706d111563cd9bd38293517b2cb8163caa9badd2026e421583532e",
    ),
]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _receipt_json_default(value):
    # Finder rows contain pandas Timestamp (a datetime/date subclass). Keep
    # their ISO dates while retaining native numerical fields and rejecting
    # unrecognized types instead of turning arbitrary values into strings.
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Unsupported receipt value: {type(value).__name__}")


def _documents():
    """Reuse immutable accepted state/arithmetic oracles, not a producer's claim."""
    docs, reports, answers = [], [], []
    for index, (path, digest) in enumerate(PACKAGES):
        assert _sha(path.read_bytes()) == digest
        with ZipFile(path) as archive:
            name = next(n for n in archive.namelist() if n.endswith("/validation.json"))
            validation = json.loads(archive.read(name))
            assert validation["base_generation"] == BASE
            assert validation["base_manifest_sha256"] == MANIFEST
            docs.append(validation)
            if index < 3:
                suffix = "/receipt.json" if index < 2 else "/acceptance.json"
                name = next(n for n in archive.namelist() if n.endswith(suffix))
                accepted = json.loads(archive.read(name))
                reports.extend(accepted["coverage"].values() if index < 2 else accepted["reports"])
                if index < 2:
                    answers.append(accepted["answers"][0])
    assert len(reports) == 8
    return docs, reports, answers


def _baseline(root, docs):
    with data_generation_context() as generation:
        assert generation == BASE
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(raw) == MANIFEST
        manifest = json.loads(raw)
        assert manifest["generation_id"] == BASE and len(manifest["files"]) == 775
        entries = {r["path"]: r for r in manifest["files"]}
        required = {}
        for doc in docs:
            for binding in [doc, *doc.get("season_stage_validations", [])]:
                assert binding["base_generation"] == BASE
                assert binding["base_manifest_sha256"] == MANIFEST
                for path, digest in binding.get("base_file_hashes", {}).items():
                    assert path not in required or required[path] == digest
                    required[path] = digest
        # Every touched existing source/table is explicitly checked, including
        # shared source paths not listed by the reason companion package.
        for doc in docs:
            for item in doc["overlay_files"]:
                if item["path"] in entries:
                    required[item["path"]] = entries[item["path"]]["sha256"]
        for path, digest in sorted(required.items()):
            item = entries[path]
            body = data_path("data/" + path).read_bytes()
            assert _sha(body) == digest == item["sha256"]
            assert len(body) == item["size_bytes"]
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        target = root / "metadata/generation_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return manifest, required


def test_accepted_cohorts_work_together_without_discarded_coverage(tmp_path, monkeypatch):
    docs, oracles, records = _documents()
    root = tmp_path / "stage/data"
    root.mkdir(parents=True)
    manifest, required = _baseline(root, docs)
    before = {path: (root / path).read_bytes() for path in required}
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "composed-participation-stage"
    validation = compose_overlays(
        PACKAGES,
        root,
        output,
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        candidate_sha=os.environ["VALIDATION_SHA"],
    )
    assert len(validation["overlay_files"]) == 407
    changed = {item["path"] for item in validation["overlay_files"]}
    for item in validation["overlay_files"]:
        path = item["path"]
        body = (output / path).read_bytes()
        assert _sha(body) == item["sha256"] and len(body) == item["size_bytes"]
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    # One combined source-root validation. Original per-package qualification is
    # already accepted; this verifies preservation and cross-package consistency.
    validate_publication(root)
    for path, body in before.items():
        if path not in changed:
            assert (root / path).read_bytes() == body
    tables = {}
    for season, rows, imports in [
        ("2023-24", 597, 17),
        ("2024-25", 347, 10),
        ("2025-26", 4076, 121),
    ]:
        path = root / f"raw/player_game_availability/{season}_regular_season.csv"
        frame = pd.read_csv(path)
        assert len(frame) == rows
        assert len(json.loads(path.with_suffix(".imports.json").read_bytes())) == imports
        tables[season] = frame
    assert sum(map(len, tables.values())) == 5020
    receipt = dict(
        classification="accepted_overlay_composition_not_publication_or_full_slice_acceptance",
        validation=validation,
        source_root_validation="passed",
        stage_preparation_accepted=True,
        consumer_acceptance="pending",
        consumer_failure=None,
        coverage=[],
        answers=[],
        api_checks=[],
        composed_availability_rows=5020,
        unchanged_other_season_rows=78,
        projected_all_season_availability_rows=5098,
        full_required_slice_accepted=False,
        nba_source_requests=0,
        production_writes=0,
    )
    receipt_path = output / "acceptance.json"

    def persist():
        receipt_path.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False, default=_receipt_json_default) + "\n"
        )

    persist()
    try:
        # A local-only inventory enables consumers against this partial sandbox;
        # it is never exported as a production generation manifest.
        _write_inventory(root)
        monkeypatch.setenv("DATA_SOURCE", "local")
        monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
        monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
        for oracle in oracles:
            actual = build_report(
                generation="legacy",
                manifest_sha256=_sha((root / "metadata/generation_manifest.json").read_bytes()),
                season=oracle["season"],
                team_id=oracle["team_id"],
                player_id=oracle["player_id"],
            )
            expected = {int(r["game_id"]): r["state"] for r in oracle["games"]}
            observed = {int(r["game_id"]): r["state"] for r in actual["games"]}
            assert observed == expected and len(expected) == 82
            assert actual["complete_requested_population"] and not actual["missing_keys"]
            assert actual["counts"] == oracle["counts"]
            receipt["coverage"].append(actual)
            teams = pd.read_csv(root / f"raw/team_game_stats/{oracle['season']}_regular_season.csv")
            own = teams.loc[teams.team_id.eq(oracle["team_id"])]
            missed = {gid for gid, state in expected.items() if state == "did_not_play"}
            home = set(
                own.loc[
                    own.game_id.isin(missed)
                    & own.is_home.astype(str).str.lower().isin(["1", "1.0", "true"]),
                    "game_id",
                ].astype(int)
            )
            for home_only, ids in [(False, missed), (True, home)]:
                question = f"How many {'home ' if home_only else ''}games did {oracle['player_name']} miss in {oracle['season']}?"
                result = execute_natural_query(question)
                assert result.result_status == "ok" and result.route == "game_finder", (
                    result.metadata
                )
                sections = result.result.to_dict()["sections"]
                assert sections["count"] == [{"count": len(ids)}]
                rows = sections.get("finder", [])
                assert len(rows) == len(ids)
                assert {int(row["game_id"]) for row in rows} == ids
                receipt["answers"].append(
                    dict(query=question, game_ids=sorted(ids), actual=_capture(result))
                )
            persist()
        for oracle in records:
            result = execute_natural_query(oracle["query"])
            assert result.result_status == "ok" and result.route == "team_record", result.metadata
            payload = result.result.to_dict()
            assert {int(r["game_id"]) for r in payload["sections"]["game_log"]} == set(
                oracle["game_ids"]
            )
            summary = payload["sections"]["summary"][0]
            for field in ("games", "wins", "losses", "pts_avg"):
                assert summary[field] == oracle["summary"][field]
            receipt["answers"].append(dict(query=oracle["query"], actual=_capture(result)))
        # Cross-season historical record and the reason companion coexist with
        # both season-long 2025 cohorts, with no new source inference.
        result = execute_natural_query("Lakers record without Davis in 2023-24")
        assert result.result_status == "ok"
        summary = result.result.to_dict()["sections"]["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (6, 2, 4)
        assert summary["pts_avg"] == pytest.approx(701 / 6, abs=0.001)
        receipt["answers"].append(
            dict(query="Lakers record without Davis in 2023-24", actual=_capture(result))
        )
        result = execute_natural_query("How many games did Luka Doncic rest in 2025-26?")
        assert result.result_status == "ok" and result.result.to_dict()["sections"]["count"] == [
            {"count": 0}
        ]
        assert result.result.metadata["reported_reason_basis"] == "officially reported Rest"
        assert result.result.metadata["reported_reason_coverage"] == dict(
            basis="officially reported Rest",
            complete=True,
            requested_games=82,
            qualified_nonparticipations=18,
            reported_rest=0,
            reported_other=18,
            unknown=0,
        )
        receipt["answers"].append(
            dict(query="How many games did Luka Doncic rest in 2025-26?", actual=_capture(result))
        )
        # Structured consumer confirms the mixed historical scope retained.
        result = execute_structured_query(
            "team_record",
            team="LAL",
            season="2023-24",
            without_player="Anthony Davis",
            with_player="LeBron James",
        )
        assert result.result_status == "ok"
        summary = result.result.to_dict()["sections"]["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (5, 1, 4)
        receipt["answers"].append(
            dict(command="team_record:ADout/LeBronin2023", actual=_capture(result))
        )
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        for question, count in [
            ("How many games did Luka Doncic miss in 2025-26?", 18),
            ("How many games did Jayson Tatum miss in 2024-25?", 10),
            ("How many games did Luka Doncic rest in 2025-26?", 0),
        ]:
            response = client.post("/query", json={"query": question})
            body = response.json()
            receipt["api_checks"].append(
                dict(query=question, status=response.status_code, body=body)
            )
            assert response.status_code == 200 and body["result_status"] == "ok"
            assert body["result"]["sections"]["count"] == [{"count": count}]
        # Finite Core-1 integration on this SAME authenticated composed root.
        # Original ID12's shared pair interpretation needs a real nonempty
        # control as well as its qualified historical zero (not missing data).
        receipt["paired_missing"] = verify_paired_missing(root, oracles, client)
        from tests.test_participation_season_splits_real_data import (
            verify_qualified_participation_splits,
        )

        receipt["s4_integration"] = verify_qualified_participation_splits(root, monkeypatch)
        import subprocess
        import sys

        qa = output / "rawqa"
        cases = [
            "k08_pair_missing_nonempty",
            "k08_pair_missing_zero",
            "k08_pair_missing_zero_count",
            "k08_pair_missing_player_bound",
            "k08_s4_team_with",
            "k08_s4_team_without",
            "k08_s4_player_with",
            "k08_s4_player_without",
        ]
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/raw_query_answer_qa.py"),
                "--out",
                str(qa),
                "--run-id",
                "composed-core",
                "--fail-on-expectation-failure",
                *[arg for case in cases for arg in ("--case", case)],
            ],
            check=True,
        )
        receipt["integrated_rawqa"] = json.loads((qa / "composed-core/summary.json").read_text())
        assert len(receipt["coverage"]) == 8 and len(receipt["answers"]) == 21
        assert len(receipt["api_checks"]) == 3
        receipt["consumer_acceptance"] = "passed"
    except Exception as exc:
        receipt.update(
            consumer_acceptance="failed",
            consumer_failure=dict(type=type(exc).__name__, message=str(exc)),
        )
        raise
    finally:
        persist()


def verify_paired_missing(root, oracles, client):
    """Expected sets come from independently accepted explicit state vectors."""
    evidence = []
    for team, season, names, people in [
        ("BOS", "2025-26", "Jayson Tatum and Jaylen Brown", (1628369, 1627759)),
        ("LAL", "2023-24", "Anthony Davis and Austin Reaves", (203076, 1630559)),
    ]:
        reports = [
            next(r for r in oracles if r["season"] == season and r["player_id"] == pid)
            for pid in people
        ]
        assert all(
            r["complete_requested_population"] and r["counts"]["unknown"] == 0 for r in reports
        )
        state_maps = [
            {int(r["game_id"]): r["state"] for r in report["games"]} for report in reports
        ]
        assert set(state_maps[0]) == set(state_maps[1]) and len(state_maps[0]) == 82
        ids = {gid for gid in state_maps[0] if all(m[gid] == "did_not_play" for m in state_maps)}
        teams = pd.read_csv(root / f"raw/team_game_stats/{season}_regular_season.csv")
        expected = teams.loc[teams.team_abbr.eq(team) & teams.game_id.isin(ids)]
        assert len(expected) == len(ids)
        assert len(ids) == (8 if team == "BOS" else 0)
        queries = (
            [
                f"Celtics record with Tatum and Brown missing in {season}",
                f"Boston record with Jaylen Brown and Jayson Tatum both missing in {season}",
            ]
            if team == "BOS"
            else [
                f"Lakers record with Davis and Reaves missing in {season}",
                f"Los Angeles Lakers record with Austin Reaves and Anthony Davis were missing in {season}",
            ]
        )
        kwargs = dict(team=team, season=season, without_player=names)
        results = [execute_natural_query(q) for q in queries]
        results.append(execute_structured_query("team_record", **kwargs))
        responses = [
            client.post("/query", json={"query": queries[0]}),
            client.post("/structured-query", json={"route": "team_record", "kwargs": kwargs}),
        ]
        assert all(r.status_code == 200 for r in responses)
        payloads = [r.to_dict() for r in results] + [r.json()["result"] for r in responses]
        for result in results[:2]:
            assert result.metadata["team"] == team
            assert set(result.metadata["without_player"].split(" and ")) == set(
                names.split(" and ")
            )
            assert result.metadata["with_player"] is None
        for doc in payloads:
            if expected.empty:
                assert doc["result_status"] == "no_result" and doc["result_reason"] == "no_match", (
                    doc
                )
                assert not doc["sections"]
            else:
                assert doc["result_status"] == "ok", doc
                assert {int(r["game_id"]) for r in doc["sections"]["game_log"]} == ids
                summary = doc["sections"]["summary"][0]
                assert summary["games"] == len(ids)
                assert summary["wins"] == int(expected.wl.eq("W").sum())
                assert summary["losses"] == int(expected.wl.eq("L").sum())
                for stat in ["pts", "reb", "ast"]:
                    assert summary[stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)
        evidence.append(
            dict(
                team=team,
                season=season,
                players=list(people),
                queries=queries,
                game_ids=sorted(ids),
                games=len(ids),
                wins=int(expected.wl.eq("W").sum()),
                losses=int(expected.wl.eq("L").sum()),
                points_sum=int(expected.pts.sum()),
                natural=results[0].to_dict(),
                http=responses[0].json(),
                structured_http=responses[1].json(),
                coverage_classification="complete_qualified_observed_population_not_all_historical_tenure",
            )
        )
    # Original neighboring K08 player+bound consumer, now with the same
    # paired missing interpretation and independently qualified source rows.
    season = "2023-24"
    states = [
        {
            int(g["game_id"]): g["state"]
            for g in next(r for r in oracles if r["season"] == season and r["player_id"] == pid)[
                "games"
            ]
        }
        for pid in (2544, 203076)
    ]
    absent = {gid for gid in states[0] if all(m[gid] == "did_not_play" for m in states)}
    raw = pd.read_csv(root / f"raw/player_game_stats/{season}_regular_season.csv")
    expected = raw.loc[
        raw.player_id.eq(1630559)
        & raw.game_id.isin(absent)
        & raw.opponent_team_abbr.eq("BOS")
        & raw.pts.ge(20)
    ]
    assert expected.game_id.astype(int).tolist() == [22300684]
    assert expected[["pts", "reb", "ast"]].iloc[0].tolist() == [32, 2, 3]
    question = "Austin Reaves games with 20 points with LeBron James and Anthony Davis missing against Boston in 2023-24"
    kwargs = dict(
        player="Austin Reaves",
        team="LAL",
        season=season,
        opponent="BOS",
        without_player="LeBron James and Anthony Davis",
        stat="pts",
        min_value=20,
        limit=None,
    )
    results = [
        execute_natural_query(question),
        execute_structured_query("player_game_finder", **kwargs),
    ]
    responses = [
        client.post("/query", json={"query": question}),
        client.post("/structured-query", json={"route": "player_game_finder", "kwargs": kwargs}),
    ]
    assert all(r.status_code == 200 for r in responses)
    for doc in [r.to_dict() for r in results] + [r.json()["result"] for r in responses]:
        assert doc["result_status"] == "ok"
        rows = doc["sections"]["finder"]
        assert len(rows) == 1 and (int(rows[0]["game_id"]), rows[0]["player_id"]) == (
            22300684,
            1630559,
        )
        assert [rows[0][k] for k in ("pts", "reb", "ast")] == [32, 2, 3]
    zero_question = "How many Lakers games with Davis and Reaves missing in 2023-24?"
    zero = execute_natural_query(zero_question)
    http_zero = client.post("/query", json={"query": zero_question})
    assert zero.result_status == "ok" and zero.metadata["primary_count"] == 0
    assert http_zero.status_code == 200 and http_zero.json()["result_status"] == "ok"
    assert http_zero.json()["result"]["sections"]["count"] == [{"count": 0}]
    evidence.append(
        dict(
            query=question,
            game_ids=[22300684],
            player_id=1630559,
            pts=32,
            reb=2,
            ast=3,
            result=results[0].to_dict(),
            zero_query=zero_question,
            zero_count=zero.to_dict(),
        )
    )
    return evidence
