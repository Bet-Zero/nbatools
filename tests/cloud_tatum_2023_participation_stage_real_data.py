"""Qualify a new candidate before composition; no collection or publication.

Phase1 is independently source-reviewed and qualifies all278 canonical cells
before the composer may see its candidate ZIP. It is not a previously accepted
artifact. Both phase outputs remain pending final independent output acceptance.
Any phase failure persists diagnostics and retains already prepared artifacts.
"""

import csv
import hashlib
import io
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from nbatools.commands._player_identity import player_name_key
from nbatools.commands.pipeline.pull_player_game_availability import COLUMNS, validate_publication
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_composed_participation_stage_real_data import (
    MANIFEST,
    PACKAGES,
    _baseline,
    _receipt_json_default,
)
from tests.cloud_reported_rest_stage_real_data import _capture, _write_inventory
from tools.availability_overlay import _indexed, _table, verify_append
from tools.compose_participation_overlays import compose_overlays
from tools.participation_coverage import build_report
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/k08-tatum-2023"
REQUEST = PROGRAM / "collection-requests/bos-tatum-participation-remaining-2023-24.json"
ACCEPTED = PROGRAM / "source-evidence/k08-composition/staging-acceptance-source.zip"
ACCEPTED_SHA = "4ce53f28bd44230138f000927d3ffa43dbe618759e265ce65e095b505ecb92cf"
BASE = "availability-lebron-season-v1-20261031"
SEASON, BOS, TATUM = "2023-24", 1610612738, 1628369
CSV = "raw/player_game_availability/2023-24_regular_season.csv"
IMPORTS = CSV.replace(".csv", ".imports.json")
PINS = {
    "sources.json": "b262fa528acd053b94e3f573f6905fa69bd63cd4d9e92896b5a530c23b910065",
    "listed-fact-journal.json": "91dfa1ff88b1b6c3d2562d705b38b6fba3f3052ac1bbee0ca6dca8472a525dde",
    "source-qualification-review.json": "82d76d4f4277a5ccd0a7352c09c7ba8709615522324dba710228e37721bc3913",
    "independent-source-oracle.json": "d5d6120e6e5859dbd22f6028d949e760b8a3e923e43381b76b79e863b74b85ad",
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _dump(path, receipt):
    path.write_text(json.dumps(receipt, indent=2, default=_receipt_json_default) + "\n")


@contextmanager
def _phase(receipt, path, name):
    receipt["phases"][name] = dict(status="running")
    _dump(path, receipt)
    try:
        yield
    except Exception as exc:
        receipt["phases"][name] = dict(
            status="failed", error_type=type(exc).__name__, error=str(exc)
        )
        raise
    else:
        receipt["phases"][name] = dict(status="passed")
    finally:
        _dump(path, receipt)


def _key(row):
    return tuple(int(row[k]) for k in ("game_id", "team_id", "player_id"))


def _compare_population(frame, facts, packets, canonical):
    """Compare every new cell to independent original facts, then canonical play."""
    assert list(frame.columns) == list(COLUMNS)
    actual = {_key(r): r for r in frame.to_dict("records")}
    expected = {_key(r): r for r in facts}
    assert len(actual) == len(frame) and len(expected) == len(facts)
    assert actual.keys() == expected.keys()
    for key, original in expected.items():
        row = actual[key]
        for field in ("game_date", "season", "season_type", "team_abbr", "participation_state"):
            assert row[field] == original[field], (key, field)
        assert row["player_name"] == original["player_name_raw"].strip(), key
        comment = (
            (original["comment_literal"] or "").strip()
            if original["traditional_row_literal"] is not None
            else "INACTIVE - BoxScoreSummaryV2 explicit listed row"
        )
        assert row["source_comment"] == comment, key
        if original["source_seconds"] is None:
            assert row["source_minutes"] == "", key
        else:
            assert float(row["source_minutes"]) == pytest.approx(
                original["source_seconds"] / 60, abs=1e-10
            ), key
        assert (
            row["source"]
            == f"nba_stats_structured_archive:2e44b7c039f104bc6b41a1de494411e83a03714e:{key[0]:010d}"
        )
        assert row["source_sha256"] == packets[key[0]]
        assert row["identity_source_sha256"] == ""
        assert row["coverage_scope"] == "listed_player_rows_only"
    positive = {k: f for k, f in expected.items() if f["participation_state"] == "played"}
    known = {_key(r): r for r in canonical.to_dict("records")}
    assert len(known) == len(canonical) and known.keys() == positive.keys()
    for key, row in known.items():
        assert player_name_key(row["player_name"]) == player_name_key(
            positive[key]["player_name_raw"]
        )
        assert float(row["pts"]) == positive[key]["source_points"], key


def _packet_bindings(root, rows, provenance):
    packets = {}
    for gid, group in rows.groupby(pd.to_numeric(rows.game_id)):
        values = set(group.source_sha256)
        assert len(values) == 1
        digest = values.pop()
        raw = (root / f"raw/player_game_availability_sources/{digest}.structured.json").read_bytes()
        assert _sha(raw) == digest
        packet = json.loads(raw)
        assert (
            packet["game_id"],
            packet["season"],
            packet["season_type"],
            packet["summary_version"],
        ) == (int(gid), SEASON, "Regular Season", 2)
        assert packet["revision"] == "2e44b7c039f104bc6b41a1de494411e83a03714e"
        captures = []
        for endpoint in ("boxscoretraditionalv3", "boxscoresummaryv2"):
            original = provenance["files"][f"{endpoint}_{gid:010d}.json"]
            item = packet["sources"][endpoint]
            assert (item["sha256"], item["size_bytes"], item["url"], item["file"]) == (
                original["sha256"],
                original["size_bytes"],
                original["url"],
                original["sha256"] + ".json",
            )
            retained = (root / "raw/player_game_availability_sources" / item["file"]).read_bytes()
            assert _sha(retained) == original["sha256"] and len(retained) == original["size_bytes"]
            captures.append(datetime.fromisoformat(original["retrieved_at"]))
        assert datetime.fromisoformat(packet["retrieved_at"]) == max(captures)
        packets[int(gid)] = digest
    return packets


def _candidate_zip(output, archive_path):
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.write(path, "candidate/" + path.relative_to(output).as_posix())
    return _sha(archive_path.read_bytes())


def _accepted_documents():
    # Metadata bindings only; old qualification, arithmetic and21queries are reused.
    docs = []
    for path, digest in PACKAGES:
        assert _sha(path.read_bytes()) == digest
        with ZipFile(path) as archive:
            name = next(n for n in archive.namelist() if n.endswith("/validation.json"))
            docs.append(json.loads(archive.read(name)))
    assert _sha(ACCEPTED.read_bytes()) == ACCEPTED_SHA
    with ZipFile(ACCEPTED) as archive:
        name = next(n for n in archive.namelist() if n.endswith("/validation.json"))
        accepted = json.loads(archive.read(name))
        assert len(accepted["overlay_files"]) == 407
        prefix = name.removesuffix("validation.json")
        bodies = {
            item["path"]: archive.read(prefix + item["path"]) for item in accepted["overlay_files"]
        }
    for item in accepted["overlay_files"]:
        assert (
            _sha(bodies[item["path"]]) == item["sha256"]
            and len(bodies[item["path"]]) == item["size_bytes"]
        )
    return docs, bodies


def _assert_record(result, ids, record):
    assert result.result_status == "ok" and result.route == "team_record", result.metadata
    sections = result.result.to_dict()["sections"]
    assert {int(r["game_id"]) for r in sections["game_log"]} == ids
    row = sections["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (
        record["games"],
        record["wins"],
        record["losses"],
    )
    assert row["pts_avg"] == pytest.approx(record["points_average"], abs=0.001)


def test_new_tatum_population_is_qualified_before_joint_composition(tmp_path, monkeypatch):
    assert (
        _sha(REQUEST.read_bytes())
        == "b91224596ce7aa8585b320b0d0e46d96025f788524e93ca81c76a87c4dee6d74"
    )
    documents = {}
    for name, digest in PINS.items():
        raw = (EVIDENCE / name).read_bytes()
        assert _sha(raw) == digest
        documents[name] = json.loads(raw)
    facts = documents["listed-fact-journal.json"]["facts"]
    oracle = documents["independent-source-oracle.json"]
    assert len(facts) == 278 and len(oracle["projected_games"]) == 82
    assert documents["listed-fact-journal.json"]["source_manifest_sha256"] == PINS["sources.json"]
    assert (
        documents["source-qualification-review.json"]["source_manifest_sha256"]
        == PINS["sources.json"]
    )
    assert oracle["listed_fact_journal"]["sha256"] == PINS["listed-fact-journal.json"]
    gids = {int(g) for g in oracle["target_DNP_game_ids"]}
    home_ids = {int(g) for g in oracle["target_home_DNP_game_ids"]}
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "tatum-2023-stage"
    output.mkdir(parents=True)
    receipt = dict(
        classification="new_candidate_qualification_then_composition_not_publication",
        phases={},
        input_roles=dict(
            accepted407="previously_accepted", new26="prepared_pending_current_gate_qualification"
        ),
        candidate_stage_qualified=False,
        consumer_acceptance="pending",
        answers=[],
        api_checks=[],
        source_proofs=PINS,
        full_required_slice_accepted=False,
        production_writes=0,
        new_nba_source_calls=0,
    )
    receipt_path = output / "acceptance.json"
    _dump(receipt_path, receipt)
    try:
        with _phase(receipt, receipt_path, "canonical_candidate"):
            stage_work, stage_output = tmp_path / "new-stage", tmp_path / "new-overlay"
            new = build_stage(
                REQUEST,
                EVIDENCE,
                stage_work,
                stage_output,
                candidate_sha=os.environ["VALIDATION_SHA"],
            )
            assert len(new["overlay_files"]) == 26 and new["requested_game_count"] == 8
            # Preserve the prepared26paths even if an independent comparison fails.
            candidate_zip = output / "candidate-overlay.zip"
            candidate_sha = _candidate_zip(stage_output, candidate_zip)
            receipt["candidate_zip"] = dict(
                sha256=candidate_sha, files=26, independent_output_acceptance="pending"
            )
            stage_root = stage_work / "data"
            whole = pd.read_csv(stage_root / CSV, dtype=str, keep_default_na=False)
            rows = whole.loc[pd.to_numeric(whole.game_id).isin(gids)]
            assert len(whole) == 346 and len(rows) == 278
            canonical = pd.read_csv(
                stage_root / f"raw/player_game_stats/{SEASON}_regular_season.csv"
            )
            canonical = canonical.loc[canonical.game_id.isin(gids)]
            assert len(canonical) == 173
            packets = _packet_bindings(stage_root, rows, documents["sources.json"])
            _compare_population(rows, facts, packets, canonical)
            for relative, digest in new["base_file_hashes"].items():
                if relative not in new["append_only"]:
                    assert _sha((stage_root / relative).read_bytes()) == digest
            assert new["append_only"][CSV]["added_records"] == 278
            assert new["append_only"][IMPORTS]["added_records"] == 8
            receipt["candidate_stage_qualified"] = True
            receipt["input_roles"]["new26"] = (
                "qualified_during_current_gate_independent_output_acceptance_pending"
            )
            receipt["candidate_qualification"] = dict(
                all_new_rows_compared=278,
                canonical_positive_rows_compared=173,
                unchanged_base_cells=68,
                unchanged_base_imports=2,
                source_replay_validator="passed_inside_unchanged_build_stage",
            )
        with _phase(receipt, receipt_path, "joint_composition"):
            assert (
                receipt["candidate_stage_qualified"]
                and receipt["phases"]["canonical_candidate"]["status"] == "passed"
            )
            docs, accepted_bodies = _accepted_documents()
            root = tmp_path / "joint/data"
            root.mkdir(parents=True)
            manifest, required = _baseline(root, [*docs, new])
            baseline = {p: (root / p).read_bytes() for p in required}
            composed = output / "composed-overlay"
            validation = compose_overlays(
                [(ACCEPTED, ACCEPTED_SHA), (candidate_zip, candidate_sha)],
                root,
                composed,
                base_generation=BASE,
                base_manifest_sha256=MANIFEST,
                candidate_sha=os.environ["VALIDATION_SHA"],
            )
            assert len(validation["overlay_files"]) == 431
            for item in validation["overlay_files"]:
                relative = item["path"]
                body = (composed / relative).read_bytes()
                assert _sha(body) == item["sha256"] and len(body) == item["size_bytes"]
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
            validate_publication(root)
            for path, raw in accepted_bodies.items():
                if path == CSV:
                    _, old = _table(raw)
                    _, current = _table((root / path).read_bytes())
                    old, current = _indexed(old), _indexed(current)
                    assert all(current[k] == row for k, row in old.items()) and len(old) == 597
                elif path == IMPORTS:
                    old, current = json.loads(raw), json.loads((root / path).read_bytes())
                    assert all(current[k] == value for k, value in old.items()) and len(old) == 17
                else:
                    assert (root / path).read_bytes() == raw
            changed = {r["path"] for r in validation["overlay_files"]}
            for path, raw in baseline.items():
                if path not in changed:
                    assert (root / path).read_bytes() == raw
            for path, spec in validation["append_only"].items():
                verify_append(path, baseline[path], (root / path).read_bytes(), spec)
            assert len(pd.read_csv(root / CSV)) == 875
            assert len(json.loads((root / IMPORTS).read_bytes())) == 25
            receipt["validation"] = validation
            receipt["preservation"] = dict(
                prior407_paths_checked=407,
                prior405_other_paths_byte_identical=True,
                prior597_cells_and17_imports_preserved=True,
                added_rows=278,
                projected_all_season_rows=5376,
                new_2023_rows=875,
                new_2023_imports=25,
                final_source_root_validator="passed",
            )
        with _phase(receipt, receipt_path, "consumers"):
            _write_inventory(root)  # Local TEST sandbox only; never exported.
            monkeypatch.setenv("DATA_SOURCE", "local")
            monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
            monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
            manifest_sha = _sha((root / "metadata/generation_manifest.json").read_bytes())
            report = build_report(
                generation="legacy",
                manifest_sha256=manifest_sha,
                season=SEASON,
                team_id=BOS,
                player_id=TATUM,
            )
            assert {int(r["game_id"]): r["state"] for r in report["games"]} == {
                int(r["game_id"]): r["state"] for r in oracle["projected_games"]
            }
            assert report["counts"] == dict(
                played=74, did_not_play=8, same_game_other_side=0, unknown=0
            )
            assert (
                report["complete_requested_population"]
                and not report["missing_keys"]
                and report["missed_games"] == 8
            )
            receipt["coverage"] = report
            for question, expected in [
                ("How many games did Jayson Tatum miss in 2023-24?", gids),
                ("How many home games did Jayson Tatum miss in 2023-24?", home_ids),
                ("Which games did Jayson Tatum miss in 2023-24?", gids),
            ]:
                result = execute_natural_query(question)
                sections = result.result.to_dict()["sections"]
                assert result.result_status == "ok" and sections["count"] == [
                    dict(count=len(expected))
                ]
                assert {int(r["game_id"]) for r in sections["finder"]} == expected
                receipt["answers"].append(dict(query=question, actual=_capture(result)))
            question = "Celtics record without Jayson Tatum in 2023-24"
            result = execute_natural_query(question)
            _assert_record(result, gids, oracle["source_score_record"])
            receipt["answers"].append(dict(query=question, actual=_capture(result)))
            result = execute_structured_query(
                "team_record", team="BOS", season=SEASON, without_player="Jayson Tatum"
            )
            _assert_record(result, gids, oracle["source_score_record"])
            receipt["answers"].append(
                dict(command="structured_team_record", actual=_capture(result))
            )
            from fastapi.testclient import TestClient

            from nbatools.api import app

            client = TestClient(app)
            for question, count in [
                ("How many games did Jayson Tatum miss in 2023-24?", 8),
                ("How many home games did Jayson Tatum miss in 2023-24?", 5),
                ("Celtics record without Jayson Tatum in 2023-24", None),
            ]:
                response = client.post("/query", json={"query": question})
                body = response.json()
                receipt["api_checks"].append(
                    dict(query=question, status=response.status_code, body=body)
                )
                assert response.status_code == 200 and body["result_status"] == "ok"
                if count is not None:
                    assert body["result"]["sections"]["count"] == [dict(count=count)]
                else:
                    summary = body["result"]["sections"]["summary"][0]
                    assert (summary["games"], summary["wins"], summary["losses"]) == (8, 7, 1)
                    assert summary["pts_avg"] == pytest.approx(1030 / 8, abs=0.001)
            # A valid partial evidence table must yield unknown, never Rest/DNP0.
            complete_csv, complete_imports = (
                (root / CSV).read_bytes(),
                (root / IMPORTS).read_bytes(),
            )
            missing = min(gids)
            try:
                header, records = _table(complete_csv)
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\n")
                writer.writeheader()
                writer.writerows(r for r in records if int(r["game_id"]) != missing)
                (root / CSV).write_text(stream.getvalue())
                imports = json.loads(complete_imports)
                imports.pop(str(missing))
                (root / IMPORTS).write_text(json.dumps(imports, sort_keys=True) + "\n")
                _write_inventory(root)
                partial = build_report(
                    generation="legacy",
                    manifest_sha256=_sha((root / "metadata/generation_manifest.json").read_bytes()),
                    season=SEASON,
                    team_id=BOS,
                    player_id=TATUM,
                )
                assert (
                    partial["counts"]["unknown"] == 1
                    and partial["missed_games"] is None
                    and not partial["complete_requested_population"]
                )
                result = execute_natural_query("How many games did Jayson Tatum miss in 2023-24?")
                assert result.result_status == "no_result" and result.result_reason != "no_match"
                receipt["unknown_control"] = dict(
                    removed_complete_group=missing, report=partial, actual=_capture(result)
                )
            finally:
                (root / CSV).write_bytes(complete_csv)
                (root / IMPORTS).write_bytes(complete_imports)
                _write_inventory(root)
            receipt["consumer_acceptance"] = "passed"
    finally:
        _dump(receipt_path, receipt)
        reset_data_source_cache()
