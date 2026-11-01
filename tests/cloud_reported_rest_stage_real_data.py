"""Replay retained reason sources over the accepted LAL participation overlay."""

import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_lal_participation_stage_real_data import _assert_record
from tools.availability_overlay import verify_append

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/k08-rest"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
SEASON = "2025-26"
SUFFIX = "2025-26_regular_season.csv"
LAL, LUKA = 1610612747, 1629029
AVAILABILITY = "raw/player_game_availability/" + SUFFIX
IMPORTS = AVAILABILITY.removesuffix(".csv") + ".imports.json"
REASONS = "raw/player_game_absence_reasons/" + SUFFIX
REASON_IMPORTS = REASONS.removesuffix(".csv") + ".imports.json"
SOURCE_PREFIX = "raw/player_game_absence_reason_sources/"
SEED = PROGRAM / "source-evidence/k08-lal-remaining/staged-acceptance-source.zip"
SEED_SHA = "a18792e51f036cfbffc509c7990ee403fbbd70edc59bd1b0fa0d4cbff3a1eb03"
PINS = {
    "representative-source.zip": "cd11f240eee112254af862af6e1bfb278a5ded351d2cd1e5b085561237b7d8e4",
    "remainder-source.zip": "695cdb15daf25473ad378b4c2ec433fc0f6923a96f21586ffb06db5a0a5a35a7",
    "full-source-qualification.json": "477e3284ecb87ba71718ad488749597d8628e6f0e2c7e1e6afd94da6ab7907b4",
    "reported-reason-fact-journal.json": "9cc9a05a41d837e45654d4fdae880738da03d6cb882b37fc9ae8f715c12a0356",
    "reported-rest-oracle.json": "31d85064bde4527840e28d3ca48f83e77871e0ae7f4fe548946bd1a82513085a",
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _safe(path):
    value = Path(path)
    assert not value.is_absolute() and ".." not in value.parts
    return value


def _write_inventory(root):
    """Only the local query sandbox gets this inventory; export precedes it."""
    path = root / "metadata/generation_manifest.json"
    doc = dict(
        generation_id="legacy",
        classification="test_only_development_staging",
        files=[
            dict(
                path=p.relative_to(root).as_posix(),
                size_bytes=p.stat().st_size,
                sha256=_sha(p.read_bytes()),
            )
            for p in sorted(root.rglob("*"))
            if p.is_file() and p != path
        ],
    )
    path.write_text(json.dumps(doc) + "\n")
    reset_data_source_cache()
    clear_frame_cache()


def _materialize_seed(root, manifest):
    assert _sha(SEED.read_bytes()) == SEED_SHA
    entries = {row["path"]: row for row in manifest["files"]}
    with ZipFile(SEED) as archive:
        seed = json.loads(archive.read("acquired_data/validation.json"))
        assert seed["base_generation"] == BASE and seed["base_manifest_sha256"] == MANIFEST
        for relative, digest in seed["base_file_hashes"].items():
            raw = data_path("data/" + relative).read_bytes()
            assert _sha(raw) == digest == entries[relative]["sha256"]
            assert len(raw) == entries[relative]["size_bytes"]
            target = root / _safe(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        baseline = {name: (root / name).read_bytes() for name in (AVAILABILITY, IMPORTS)}
        assert len(list(csv.DictReader(io.StringIO(baseline[AVAILABILITY].decode())))) == 804
        assert len(json.loads(baseline[IMPORTS])) == 23
        assert len(seed["overlay_files"]) == 94
        for item in seed["overlay_files"]:
            relative = item["path"]
            raw = archive.read("acquired_data/" + relative)
            assert _sha(raw) == item["sha256"] and len(raw) == item["size_bytes"]
            target = root / _safe(relative)
            if target.exists():
                assert relative in seed["append_only"]
                verify_append(relative, baseline[relative], raw, seed["append_only"][relative])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    assert len(pd.read_csv(root / AVAILABILITY)) == 1874
    assert len(json.loads((root / IMPORTS).read_bytes())) == 54
    return seed


def _report_cache(destination):
    """Unpack only originals and their named receipts; equal reuse is allowed."""
    for filename in ("representative-source.zip", "remainder-source.zip"):
        with ZipFile(EVIDENCE / filename) as archive:
            for name in archive.namelist():
                path = _safe(name)
                if not (name.endswith(".pdf") or re.fullmatch(r"\d{8}_[A-Z]{6}\.json", path.name)):
                    continue
                raw = archive.read(name)
                if path.parent.name == "reused-representative":
                    original = list(destination.glob("*/" + path.name))
                    assert len(original) == 1 and original[0].read_bytes() == raw
                    continue
                assert re.fullmatch(r"\d{10}", path.parent.name)
                target = destination / path.parent.name / path.name
                if target.exists():
                    assert target.read_bytes() == raw
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
    receipts = list(destination.glob("*/*_*.json"))
    assert len(receipts) == 14
    return {int(path.parent.name): path for path in receipts}


def _assert_empty(outcome):
    assert outcome.result_status == "no_result" and outcome.result_reason == "no_match", (
        outcome.metadata
    )


def _capture(outcome):
    result = getattr(outcome, "result", None)
    return dict(
        status=outcome.result_status,
        reason=outcome.result_reason,
        route=outcome.route,
        metadata=outcome.metadata,
        result=result.to_dict() if hasattr(result, "to_dict") else None,
    )


def test_reported_rest_sources_are_not_all_missed_games(tmp_path, monkeypatch):
    from nbatools.commands.pipeline.reported_absence_reasons import (
        stage_observation,
        validate_publication,
    )

    for name, digest in PINS.items():
        assert _sha((EVIDENCE / name).read_bytes()) == digest
    journal = json.loads((EVIDENCE / "reported-reason-fact-journal.json").read_bytes())
    oracle = json.loads((EVIDENCE / "reported-rest-oracle.json").read_bytes())
    expected = {int(row["game_id"]): row for row in journal["games"]}
    assert len(expected) == 18 and oracle["population"]["reported_rest_season_count_qualified"]
    assert oracle["reported_rest"]["game_ids"] == [] and not oracle["unknown_game_ids"]
    root = tmp_path / "stage/data"
    root.mkdir(parents=True)
    with data_generation_context() as generation:
        assert generation == BASE
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(raw) == MANIFEST
        manifest = json.loads(raw)
        assert manifest["generation_id"] == BASE and len(manifest["files"]) == 775
        assert REASONS not in {row["path"] for row in manifest["files"]}
        seed = _materialize_seed(root, manifest)
    before = {
        p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    availability = pd.read_csv(root / AVAILABILITY)
    missed = availability.loc[
        availability.player_id.eq(LUKA)
        & availability.team_id.eq(LAL)
        & availability.participation_state.eq("did_not_play")
    ]
    assert set(missed.game_id.astype(int)) == set(expected)
    reports = _report_cache(tmp_path / "cached-reports")
    for row in missed.sort_values("game_id").itertuples():
        gid = int(row.game_id)
        if gid in reports:
            receipt_path = reports[gid]
            receipt = json.loads(receipt_path.read_bytes())
            source, kind = receipt_path.parent / receipt["raw_file"], "nba_official_finalbox"
        elif str(row.source).startswith("nba_official_finalbox:"):
            ref = str(row.source).split(":", 1)[1]
            receipt_path = root / "raw/player_game_availability_sources" / (ref + ".json")
            receipt = json.loads(receipt_path.read_bytes())
            source, kind = receipt_path.parent / receipt["raw_file"], "nba_official_finalbox"
        else:
            directory = PROGRAM / "source-evidence/k08-lal-remaining"
            receipt_path = directory / "sources.json"
            source = directory / "sources" / f"boxscoretraditionalv3_{gid:010d}.json"
            kind = "nba_stats_structured_archive"
        stage_observation(
            root,
            season=SEASON,
            season_type="Regular Season",
            game_id=gid,
            team_id=LAL,
            player_id=LUKA,
            source_kind=kind,
            source_file=source,
            source_receipt=receipt_path,
        )
    validate_publication(root)
    reasons = pd.read_csv(root / REASONS)
    assert len(reasons) == 18 and set(reasons.game_id.astype(int)) == set(expected)
    assert set(reasons.reported_reason) == {"reported_other"}
    reason_lineage = json.loads((root / REASON_IMPORTS).read_bytes())
    assert set(reason_lineage) == {f"{gid}:{LAL}:{LUKA}" for gid in expected}
    for row in reasons.itertuples():
        fact = expected[int(row.game_id)]
        assert (row.game_date, row.team_id, row.player_id) == (fact["game_date"], LAL, LUKA)
        assert row.reported_reason == fact["reported_reason_state"]
        assert row.reason_text == fact["reported_reason_literal"].removeprefix("INACTIVE - ")
    for relative, original in before.items():
        assert (root / relative).read_bytes() == original
    new_paths = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} - set(
        before
    )
    assert REASONS in new_paths and REASON_IMPORTS in new_paths
    assert all(
        path.startswith(("raw/player_game_absence_reasons/", SOURCE_PREFIX)) for path in new_paths
    )
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "reported-rest-stage"
    output.mkdir(parents=True, exist_ok=False)
    paths = {item["path"] for item in seed["overlay_files"]} | new_paths
    files = []
    for relative in sorted(paths):
        raw = (root / relative).read_bytes()
        target = output / _safe(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files.append(dict(path=relative, sha256=_sha(raw), size_bytes=len(raw)))
    validation = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        seed_overlay_sha256=SEED_SHA,
        append_only=seed["append_only"],
        manifest_absent_creations={
            path: dict(
                base_presence="manifest_absent",
                added_observation_keys=sorted(reason_lineage),
                added_records=18,
            )
            for path in (REASONS, REASON_IMPORTS)
        },
        overlay_files=files,
        new_reason_rows=18,
        new_reason_paths=sorted(new_paths),
        prior_stage_files_unchanged=True,
        full_required_slice_accepted=False,
        publication_state="staged_only_no_writes",
        production_writes=0,
    )
    (output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    receipt = dict(
        stage_preparation_accepted=True,
        consumer_acceptance="pending",
        consumer_failure=None,
        query_checks=[],
        api_checks=[],
        population=oracle["population"],
        validation=validation,
        production_writes=0,
    )
    receipt_path = output / "acceptance.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        _write_inventory(root)
        monkeypatch.setenv("DATA_SOURCE", "local")
        monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
        monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
        reset_data_source_cache()
        queries = [
            "Lakers record when Luka rests in 2025-26",
            "LeBron James stats when Luka rests in 2025-26",
            "LeBron James 20 point games when Luka rests in 2025-26",
        ]
        for query in queries:
            result = execute_natural_query(query)
            _assert_empty(result)
            receipt["query_checks"].append(dict(query=query, actual=_capture(result)))
        for command, extra in [
            ("team_record", dict(team="LAL")),
            ("game_finder", dict(team="LAL", limit=82)),
            ("game_summary", dict(team="LAL")),
            ("player_game_summary", dict(player="LeBron James")),
            ("player_game_finder", dict(player="LeBron James", stat="pts", min_value=20)),
        ]:
            result = execute_structured_query(
                command,
                season=SEASON,
                without_player="Luka Doncic",
                without_player_reason="reported_rest",
                **extra,
            )
            _assert_empty(result)
            receipt["query_checks"].append(dict(command=command, actual=_capture(result)))
        for query, count in [
            ("How many games did Luka Doncic rest in 2025-26?", 0),
            ("How many home games did Luka Doncic rest in 2025-26?", 0),
            ("How many games did Luka Doncic miss in 2025-26?", 18),
        ]:
            result = execute_natural_query(query)
            assert result.result_status == "ok" and result.route == "game_finder", result.metadata
            assert result.result.to_dict()["sections"]["count"] == [{"count": count}]
            receipt["query_checks"].append(dict(query=query, actual=_capture(result)))
        team = pd.read_csv(root / "raw/team_game_stats" / SUFFIX)
        selected = team.loc[team.team_id.eq(LAL) & team.game_id.isin(expected)]
        binary = execute_natural_query("Lakers record without Luka Doncic in 2025-26")
        assert binary.result_status == "ok"
        _assert_record(binary.result.to_dict(), selected)
        receipt["query_checks"].append(
            dict(query="Lakers record without Luka Doncic in 2025-26", actual=_capture(binary))
        )
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        for query in [
            queries[0],
            "How many games did Luka Doncic rest in 2025-26?",
            "How many games did Luka Doncic miss in 2025-26?",
        ]:
            response = client.post("/query", json={"query": query})
            assert response.status_code == 200
            body = response.json()
            if query == queries[0]:
                assert body["result_status"] == "no_result" and body["result_reason"] == "no_match"
            else:
                assert body["result_status"] == "ok"
                assert body["result"]["sections"]["count"] == [
                    {"count": 18 if "miss" in query else 0}
                ]
            receipt["api_checks"].append(dict(query=query, status=response.status_code, body=body))
        # A valid sparse reason table must produce unknown coverage, never the
        # complete zero above. Only the local sandbox changes after export.
        complete_csv = (root / REASONS).read_bytes()
        complete_imports = (root / REASON_IMPORTS).read_bytes()
        missing_gid = int(reasons.iloc[0].game_id)
        persisted = pd.read_csv(io.BytesIO(complete_csv), dtype=str, keep_default_na=False)
        partial = persisted.loc[pd.to_numeric(persisted.game_id).ne(missing_gid)]
        try:
            partial.to_csv(root / REASONS, index=False)
            sparse_imports = dict(reason_lineage)
            del sparse_imports[f"{missing_gid}:{LAL}:{LUKA}"]
            (root / REASON_IMPORTS).write_text(json.dumps(sparse_imports) + "\n")
            _write_inventory(root)
            validate_publication(root)
            unknown = execute_natural_query("How many games did Luka Doncic rest in 2025-26?")
            assert unknown.result_status == "no_result" and unknown.result_reason != "no_match", (
                unknown.metadata
            )
            receipt["unknown_control"] = dict(
                removed_valid_observation_game_id=missing_gid,
                remaining_valid_reason_rows=17,
                actual=_capture(unknown),
            )
        finally:
            (root / REASONS).write_bytes(complete_csv)
            (root / REASON_IMPORTS).write_bytes(complete_imports)
            _write_inventory(root)
        receipt["consumer_acceptance"] = "passed"
    except Exception as exc:
        receipt.update(
            consumer_acceptance="failed",
            consumer_failure=dict(type=type(exc).__name__, message=str(exc)),
        )
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + "\n")
        reset_data_source_cache()
        clear_frame_cache()
