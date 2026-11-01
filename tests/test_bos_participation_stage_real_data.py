"""Qualify Boston season participation from retained structured and scoped reports."""

import csv
import hashlib
import io
import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._player_identity import player_name_key
from nbatools.commands.pipeline.pull_player_game_availability import backfill, validate_publication
from nbatools.data_source import data_path, data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_lal_participation_stage_real_data import _assert_record, _original_fact
from tools.availability_overlay import binding, preserve_cells, verify_append
from tools.participation_coverage import build_report
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
REQUEST = PROGRAM / "collection-requests/bos-participation-remaining-2025-26.json"
SUPPLEMENT = PROGRAM / "collection-requests/bos-clock-report-fallback-2025-26.json"
SOURCES = PROGRAM / "source-evidence/k08-bos-remaining"
SUFFIX = "2025-26_regular_season.csv"
CSV = "raw/player_game_availability/" + SUFFIX
BOS = 1610612738
PEOPLE = {1628369: "Jayson Tatum", 1627759: "Jaylen Brown"}
BAD_GAMES = {"0022500250", "0022500580", "0022500660", "0022500721"}
OLD_GAME = "0022500702"
OLD_ORACLE = ROOT / "tests/fixtures/participation/boston-20260201.json"
OLD_CACHE = (
    PROGRAM / "source-evidence/tatum-20260201/acquired_data/raw/player_game_availability_sources"
)
NEW_CACHE = SOURCES / "clock-reports"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _baseline_states(teams, players, ledger):
    dates = {int(r.game_id): pd.Timestamp(r.game_date).date() for r in teams.itertuples()}
    opponents = {int(r.game_id): int(r.opponent_team_id) for r in teams.itertuples()}
    facts = defaultdict(lambda: defaultdict(set))
    for frame, appearance in [(players, True), (ledger, False)]:
        for row in frame.loc[frame.player_id.isin(PEOPLE)].itertuples():
            gid, pid, tid = int(row.game_id), int(row.player_id), int(row.team_id)
            if gid not in dates or appearance and not row.minutes > 0:
                continue
            assert pd.Timestamp(row.game_date).date() == dates[gid]
            assert tid in {BOS, opponents[gid]}
            facts[(gid, pid)][tid].add("played" if appearance else row.participation_state)
    result = {}
    for pid in PEOPLE:
        result[pid] = {}
        for gid in dates:
            sides = facts[(gid, pid)]
            assert len(sides) <= 1
            own = sides.get(BOS, set())
            assert not own or len(own) == 1 and own <= {"played", "did_not_play"}
            result[pid][gid] = (
                next(iter(own)) if own else "same_game_other_side" if sides else "unknown"
            )
    return result


def _stage(tmp_path, request, report_specs):
    """Compose the accepted grouped stager and existing offline report producer."""
    provenance = json.loads((SOURCES / "sources.json").read_bytes())
    valid = [r for r in request["requirements"] if r["game_id"] not in BAD_GAMES]
    covered = [r for r in request["requirements"] if r["game_id"] in BAD_GAMES]
    assert len(valid) == 70 and len(covered) == 4
    files = {
        name for name, row in request["source_files"].items() if row["game_id"] not in BAD_GAMES
    }
    assert len(files) == 124
    derived = tmp_path / "structured-input"
    (derived / "sources").mkdir(parents=True)
    subset = {
        key: request[key]
        for key in (
            "schema_version",
            "dataset",
            "season",
            "season_type",
            "base_generation",
            "base_manifest_sha256",
            "revision",
            "repository",
        )
    }
    subset.update(
        requirements=valid,
        source_files={name: request["source_files"][name] for name in sorted(files)},
        classification="derived_valid_structured_subset_staging_only",
        parent_request_sha256=_sha(REQUEST.read_bytes()),
    )
    (derived / "request.json").write_text(json.dumps(subset, indent=2) + "\n")
    (derived / "sources.json").write_text(
        json.dumps(
            dict(
                repository=provenance["repository"],
                revision=provenance["revision"],
                files={name: provenance["files"][name] for name in sorted(files)},
                parent_sources_sha256=_sha((SOURCES / "sources.json").read_bytes()),
            ),
            indent=2,
        )
        + "\n"
    )
    for name in sorted(files):
        source = SOURCES / "sources" / name
        assert not source.is_symlink()
        (derived / "sources" / name).write_bytes(source.read_bytes())
    ledger_path = CSV.removesuffix(".csv") + ".imports.json"
    baseline = {p: data_path("data/" + p).read_bytes() for p in (CSV, ledger_path)}
    new_games = {int(r["game_id"]) for r in request["requirements"]} | {int(OLD_GAME)}
    assert not new_games & set(pd.read_csv(io.BytesIO(baseline[CSV])).game_id.astype(int))
    assert len(json.loads(baseline[ledger_path])) == 23
    work = tmp_path / "stage"
    partial = build_stage(
        derived / "request.json",
        derived,
        work,
        tmp_path / "structured-overlay",
        candidate_sha=os.environ["VALIDATION_SHA"],
    )
    assert (partial["requested_game_count"], partial["requested_target_count"]) == (62, 70)
    root = work / "data"
    target_rows, report_bindings, report_counts = [], [], {}
    for spec in report_specs:
        gid, cache = int(spec["game_id"]), spec["cache"]
        receipt_path = cache / (Path(spec["source_url"]).stem + ".json")
        receipt_raw = receipt_path.read_bytes()
        receipt = json.loads(receipt_raw)
        raw = (cache / receipt["raw_file"]).read_bytes()
        assert receipt["source_url"] == spec["source_url"]
        assert _sha(raw) == spec["expected_pdf_sha256"]
        assert _sha(receipt_raw) == spec["expected_receipt_sha256"]
        assert len(raw) == receipt["size_bytes"] and _sha(raw) == receipt["sha256"]
        if spec["game_id"] == OLD_GAME:
            assert _sha(raw) == request["reuse_existing_evidence"]["pdf_sha256"]
        backfill(
            "2025-26",
            root=root,
            source="report",
            cached_reports=cache,
            game_ids=[gid],
            imported_team_ids=[BOS],
        )
        rows = pd.read_csv(root / CSV).loc[lambda frame: frame.game_id.eq(gid)]
        assert not rows.empty and rows.team_id.eq(BOS).all()
        assert rows.game_date.eq(spec["game_date"]).all()
        assert rows.source.eq("nba_official_finalbox:" + receipt_path.stem).all()
        oracle = {r["player_id"]: r for r in spec["oracle_rows"]}
        assert set(rows.player_id) == set(oracle)
        for row in rows.itertuples():
            truth = oracle[row.player_id]
            assert player_name_key(row.player_name) == player_name_key(truth["player_name"])
            assert row.participation_state == truth["state"]
            if truth["state"] == "played":
                assert row.source_minutes * 60 == pytest.approx(truth["source_seconds"])
        report_counts[spec["game_id"]] = len(rows)
        for target in spec["targets"]:
            found = rows.loc[rows.player_id.eq(target["player_id"])]
            assert len(found) == 1 and found.game_date.item() == target["game_date"]
            assert found.participation_state.item() in {"played", "did_not_play"}
            target_rows.append(
                {
                    **{
                        key: target[key] for key in ("game_id", "game_date", "team_id", "player_id")
                    },
                    "state": found.participation_state.item(),
                }
            )
        report_bindings.append(
            dict(
                game_id=spec["game_id"],
                imported_team_ids=[BOS],
                source_url=spec["source_url"],
                pdf_sha256=_sha(raw),
                receipt_sha256=_sha(receipt_raw),
                listed_rows=len(rows),
            )
        )
    after = pd.read_csv(root / CSV)
    games = sorted({row["game_id"] for row in request["requirements"]} | {OLD_GAME})
    assert len(games) == 67
    append = {
        CSV: binding(baseline[CSV], games, added_records=len(after) - 804),
        ledger_path: binding(baseline[ledger_path], games, added_records=67),
    }
    (root / CSV).write_bytes(
        preserve_cells(CSV, baseline[CSV], (root / CSV).read_bytes(), append[CSV])
    )
    verify_append(
        ledger_path, baseline[ledger_path], (root / ledger_path).read_bytes(), append[ledger_path]
    )
    validate_publication(root)
    # The previously diagnosed Milwaukee identity ambiguity is still excluded;
    # trying to widen the old report cannot change the validated BOS append.
    before = [(root / p).read_bytes() for p in (CSV, ledger_path)]
    with pytest.raises(ValueError, match="candidate IDs=2"):
        backfill(
            "2025-26",
            root=root,
            source="report",
            cached_reports=OLD_CACHE,
            game_ids=[int(OLD_GAME)],
        )
    assert [(root / p).read_bytes() for p in (CSV, ledger_path)] == before
    output = tmp_path / "bos-overlay"
    output.mkdir()
    overlay = []
    for directory in ("raw/player_game_availability", "raw/player_game_availability_sources"):
        for path in sorted((root / directory).iterdir()):
            relative, raw = path.relative_to(root).as_posix(), path.read_bytes()
            if partial["base_file_hashes"].get(relative) == _sha(raw):
                continue
            assert relative not in partial["base_file_hashes"] or relative in append
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            overlay.append(dict(path=relative, sha256=_sha(raw), size_bytes=len(raw)))
    quarantined = {
        name: provenance["files"][name]["sha256"]
        for name in request["source_files"]
        if name not in files
    }
    assert len(quarantined) == 8 and not set(quarantined.values()) & {r["sha256"] for r in overlay}
    assert {
        r["path"] for r in overlay if r["path"].startswith("raw/player_game_availability/")
    } == set(append)
    validation = {
        **partial,
        "strategy": "62_structured_games_plus_five_BOS_only_reports",
        "append_only": append,
        "qualified_targets": [*partial["qualified_targets"], *target_rows],
        "requested_target_count": 75,
        "requested_game_count": 67,
        "report_bindings": report_bindings,
        "overlay_files": overlay,
        "quarantined_originals_not_imported": quarantined,
        "input_hashes": {
            **partial["input_hashes"],
            "full_request": _sha(REQUEST.read_bytes()),
            "full_sources.json": _sha((SOURCES / "sources.json").read_bytes()),
            "source-qualification.json": _sha((SOURCES / "source-qualification.json").read_bytes()),
            "report_supplement": _sha(SUPPLEMENT.read_bytes()),
            "report-qualification.json": _sha((SOURCES / "report-qualification.json").read_bytes()),
        },
        "full_required_slice_accepted": False,
        "prior_LAL_stage_composed": False,
        "precise_clock_or_on_court_coverage_promoted": False,
    }
    (output / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    return work, output, validation, report_counts


def test_retained_boston_sources_close_both_populations_and_mixed_records(tmp_path, monkeypatch):
    request = json.loads(REQUEST.read_bytes())
    assert request["base_generation"] == "availability-lebron-season-v1-20261031"
    assert (
        request["base_manifest_sha256"]
        == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
    )
    requirements = request["requirements"]
    assert len(requirements) == 74 and len({r["game_id"] for r in requirements}) == 66
    old = request["reuse_existing_evidence"]
    old_target = {key: old[key] for key in ("game_id", "game_date", "team_id", "player_id")}
    all_targets = [*requirements, old_target]
    assert len({(r["game_id"], r["player_id"]) for r in all_targets}) == 75
    teams = (
        data_read_csv("data/raw/team_game_stats/" + SUFFIX)
        .loc[lambda frame: frame.team_id.eq(BOS)]
        .copy()
    )
    players = data_read_csv("data/raw/player_game_stats/" + SUFFIX)
    ledger = data_read_csv("data/" + CSV)
    baseline_csv = data_path("data/" + CSV).read_bytes()
    assert len(teams) == teams.game_id.nunique() == 82 and len(ledger) == 804
    states = _baseline_states(teams, players, ledger)
    assert Counter(states[1628369].values()) == {"played": 16, "did_not_play": 2, "unknown": 64}
    assert Counter(states[1627759].values()) == {"played": 71, "unknown": 11}
    assert {(int(r["game_id"]), r["player_id"]) for r in all_targets} == {
        (gid, pid) for pid in PEOPLE for gid, state in states[pid].items() if state == "unknown"
    }
    source_facts, eligible_rows = [], 0
    for gid in sorted({r["game_id"] for r in requirements}):
        docs, hashes = [], {}
        for endpoint, key in [
            ("boxscoretraditionalv3", "boxScoreTraditional"),
            ("boxscoresummaryv3", "boxScoreSummary"),
        ]:
            path = SOURCES / "sources" / f"{endpoint}_{gid}.json"
            raw = path.read_bytes()
            docs.append(json.loads(raw)[key])
            hashes[path.name] = _sha(raw)
        assert all(int(d["gameId"]) == int(gid) for d in docs)
        listed = [
            (int(d[side]["teamId"]), int(p["personId"]))
            for d, collection in zip(docs, ("players", "inactives"), strict=True)
            for side in ("homeTeam", "awayTeam")
            for p in d[side][collection]
        ]
        assert len(listed) == len(set(listed)) == len({pid for _, pid in listed})
        if gid not in BAD_GAMES:
            eligible_rows += len(listed)
        for r in requirements:
            if r["game_id"] != gid:
                continue
            fact = _original_fact(*docs, player_id=r["player_id"], team_id=BOS)
            assert (
                pd.Timestamp(teams.loc[teams.game_id.eq(int(gid)), "game_date"].item())
                .date()
                .isoformat()
                == r["game_date"]
            )
            states[r["player_id"]][int(gid)] = fact["state"]
            source_facts.append(
                {
                    **{key: r[key] for key in ("game_id", "game_date", "team_id", "player_id")},
                    **fact,
                    "source_hashes": hashes,
                    "evidence_role": "corroboration_only_quarantined_original"
                    if gid in BAD_GAMES
                    else "imported_structured_originals",
                }
            )
    assert eligible_rows == 2117 and len(source_facts) == 74
    old_oracle = json.loads(OLD_ORACLE.read_bytes())
    old_fact = next(
        row for row in old_oracle["rows"] if row["player_id"] == old_target["player_id"]
    )
    states[old_target["player_id"]][int(OLD_GAME)] = old_fact["state"]
    source_facts.append(
        {
            **old_target,
            "state": old_fact["state"],
            "evidence_role": "previously_qualified_BOS_only_report",
            "source_sha256": old_oracle["source"]["sha256"],
        }
    )
    supplement = json.loads(SUPPLEMENT.read_bytes())
    assert (
        supplement["base_generation"] == request["base_generation"]
        and supplement["base_manifest_sha256"] == request["base_manifest_sha256"]
    )
    report_specs = []
    assert supplement["target_team_id"] == BOS
    qualification_raw = (SOURCES / "source-qualification.json").read_bytes()
    assert _sha(qualification_raw) == supplement["source_qualification_sha256"]
    qualification = json.loads(qualification_raw)
    assert qualification["qualification_passed"] is False
    assert qualification["source_body_quality_accepted"] is False
    assert qualification["staging_accepted"] is False
    assert qualification["request_sha256"] == _sha(REQUEST.read_bytes())
    assert qualification["sources_manifest_sha256"] == _sha((SOURCES / "sources.json").read_bytes())
    pdf_proof_raw = (SOURCES / "report-qualification.json").read_bytes()
    assert _sha(pdf_proof_raw) == "387e619548ad9c25ea2af24c9cadc738c6f2a7c86fb7c36129da561a6f828ee7"
    pdf_proof = json.loads(pdf_proof_raw)
    assert pdf_proof["pdf_source_qualification_passed"] is True
    assert pdf_proof["staging_accepted"] is False and pdf_proof["full_slice_accepted"] is False
    assert pdf_proof["source_request_sha256"] == _sha(SUPPLEMENT.read_bytes())
    qualified_reports = {r["game_id"]: r for r in pdf_proof["reports"]}
    assert set(qualified_reports) == BAD_GAMES
    for entry in supplement["games"]:
        targets = [r for r in requirements if r["game_id"] == entry["game_id"]]
        assert targets and entry["imported_team_ids"] == [BOS]
        assert {r["player_id"] for r in targets} == set(entry["required_target_player_ids"])
        assert {r["game_date"] for r in targets} == {entry["game_date"]}
        proof = qualified_reports[entry["game_id"]]
        assert proof["source_url"] == entry["source_url"]
        assert proof["imported_team_ids"] == [BOS]
        report_specs.append(
            dict(
                **entry,
                cache=NEW_CACHE / entry["game_id"],
                targets=targets,
                expected_pdf_sha256=proof["pdf_sha256"],
                expected_receipt_sha256=proof["source_receipt_sha256"],
                oracle_rows=[
                    {**row, "state": row["participation_state"]}
                    for row in proof["qualified_boston_rows"]
                ],
            )
        )
    assert {r["game_id"] for r in report_specs} == BAD_GAMES
    report_specs.append(
        dict(
            game_id=OLD_GAME,
            game_date=old_target["game_date"],
            source_url=old_oracle["source"]["source_url"],
            cache=OLD_CACHE,
            targets=[old_target],
            expected_pdf_sha256=old_oracle["source"]["sha256"],
            expected_receipt_sha256=_sha((OLD_CACHE / "20260201_MILBOS.json").read_bytes()),
            oracle_rows=old_oracle["rows"],
        )
    )
    work, destination, validation, report_counts = _stage(tmp_path, request, report_specs)
    root = work / "data"
    assert report_counts == {gid: 17 for gid in BAD_GAMES | {OLD_GAME}}
    expected_added = eligible_rows + sum(report_counts.values())
    assert expected_added == 2202
    assert validation["append_only"][CSV]["added_records"] == expected_added
    assert len(pd.read_csv(root / CSV)) == 804 + expected_added
    assert {
        (int(r["game_id"]), r["player_id"], r["state"]) for r in validation["qualified_targets"]
    } == {(int(r["game_id"]), r["player_id"], r["state"]) for r in source_facts}
    old_cells = list(csv.DictReader(io.StringIO(baseline_csv.decode())))
    new_cells = {
        (r["game_id"], r["team_id"], r["player_id"]): r
        for r in csv.DictReader(io.StringIO((root / CSV).read_text()))
    }
    assert all(new_cells[(r["game_id"], r["team_id"], r["player_id"])] == r for r in old_cells)
    for kind in ("games", "team_game_stats", "player_game_stats"):
        path = "raw/" + kind + "/" + SUFFIX
        assert _sha((root / path).read_bytes()) == validation["base_file_hashes"][path]
    entries = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.relative_to(root).as_posix() != "metadata/generation_manifest.json"
        ):
            raw = path.read_bytes()
            entries.append(
                dict(path=path.relative_to(root).as_posix(), size_bytes=len(raw), sha256=_sha(raw))
            )
    manifest = json.dumps(
        dict(generation_id="legacy", classification="test_only_development_staging", files=entries)
    ).encode()
    (root / "metadata/generation_manifest.json").write_bytes(manifest)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(work))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        diagnostics = destination / "bos-participation-acceptance"
        diagnostics.mkdir()
        for name, frame in [
            ("team82.csv", teams),
            ("canonical-target-player-rows.csv", players.loc[players.player_id.isin(PEOPLE)]),
            ("prior-target-ledger.csv", ledger.loc[ledger.player_id.isin(PEOPLE)]),
        ]:
            frame.to_csv(diagnostics / name, index=False)
        (diagnostics / "source-target-facts.json").write_text(
            json.dumps(source_facts, indent=2) + "\n"
        )
        reports, answers = {}, []
        for pid, name in PEOPLE.items():
            coverage = build_report(
                generation="legacy",
                manifest_sha256=_sha(manifest),
                season="2025-26",
                team_id=BOS,
                player_id=pid,
            )
            assert coverage["requested_games"] == coverage["observed_team_games"] == 82
            assert coverage["complete_requested_population"] and not coverage["missing_keys"]
            assert coverage["counts"] == {
                state: Counter(states[pid].values())[state]
                for state in ("played", "did_not_play", "same_game_other_side", "unknown")
            }
            missed = {gid for gid, state in states[pid].items() if state == "did_not_play"}
            home = set(
                teams.loc[
                    teams.game_id.isin(missed)
                    & teams.is_home.astype(str).str.lower().isin(["1", "1.0", "true"]),
                    "game_id",
                ].astype(int)
            )
            assert coverage["missed_games"] == len(missed) == (66 if pid == 1628369 else 11)
            assert len(home) == (32 if pid == 1628369 else 3)
            reports[pid] = coverage
            for question, ids in [
                (f"how many games did {name} miss in 2025-26", missed),
                (f"how many home games did {name} miss in 2025-26", home),
            ]:
                result = execute_natural_query(question)
                assert result.result_status == "ok" and result.route == "game_finder", (
                    result.metadata
                )
                sections = result.result.to_dict()["sections"]
                assert sections["count"] == [{"count": len(ids)}]
                assert {int(r["game_id"]) for r in sections["finder"]} == ids
            other = next(actor for actor in PEOPLE if actor != pid)
            positive = set(
                players.loc[
                    players.team_id.eq(BOS) & players.player_id.eq(other) & players.minutes.gt(0),
                    "game_id",
                ].astype(int)
            )
            expected = teams.loc[teams.game_id.isin(missed & positive)]
            assert (len(expected), int(expected.wl.eq("W").sum()), int(expected.pts.sum())) == (
                (58, 36, 6659) if pid == 1628369 else (3, 2, 329)
            )
            question = f"Celtics record without {name} and with {PEOPLE[other]} in 2025-26"
            for result in [
                execute_natural_query(question),
                execute_structured_query(
                    "team_record",
                    team="BOS",
                    season="2025-26",
                    without_player=name,
                    with_player=PEOPLE[other],
                ),
            ]:
                assert result.result_status == "ok" and result.route == "team_record", (
                    result.metadata
                )
                summary = _assert_record(result.result.to_dict(), expected)
            response = client.post("/query", json={"query": question})
            assert response.status_code == 200 and response.json()["result_status"] == "ok"
            _assert_record(response.json()["result"], expected)
            answers.append(
                dict(
                    query=question,
                    game_ids=sorted(expected.game_id.astype(int)),
                    points=int(expected.pts.sum()),
                    summary=summary,
                    missed_ids=sorted(missed),
                    home_missed_ids=sorted(home),
                )
            )
        both_dnp = {
            gid
            for gid in states[1628369]
            if states[1628369][gid] == states[1627759][gid] == "did_not_play"
        }
        for floor in (None, 100):
            expected = teams.loc[teams.game_id.isin(both_dnp)]
            if floor is not None:
                expected = expected.loc[expected.pts.ge(floor)]
            assert (len(expected), int(expected.wl.eq("W").sum()), int(expected.pts.sum())) == (
                (8, 7, 898) if floor is None else (6, 6, 705)
            )
            question = "Celtics record without Jayson Tatum and Jaylen Brown"
            if floor:
                question += ", when the Celtics score at least 100 points"
            question += " in 2025-26"
            natural = execute_natural_query(question)
            structured = execute_structured_query(
                "team_record",
                team="BOS",
                season="2025-26",
                without_player="Jayson Tatum and Jaylen Brown",
                **(dict(stat="pts", min_value=floor) if floor else {}),
            )
            for result in (natural, structured):
                assert result.result_status == "ok", result.metadata
                summary = _assert_record(result.result.to_dict(), expected)
            if floor is None:
                response = client.post("/query", json={"query": question})
                assert response.status_code == 200 and response.json()["result_status"] == "ok"
                _assert_record(response.json()["result"], expected)
            answers.append(
                dict(
                    query=question,
                    game_ids=sorted(expected.game_id.astype(int)),
                    points=int(expected.pts.sum()),
                    summary=summary,
                )
            )
        receipt = dict(
            classification="BOS_isolated_qualified_staging_only_not_publication_or_LAL_composition",
            base_generation=request["base_generation"],
            base_manifest_sha256=request["base_manifest_sha256"],
            validation=validation,
            coverage=reports,
            answers=answers,
            full_required_slice_accepted=False,
            production_writes=0,
        )
        (diagnostics / "receipt.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n")
        if output := os.environ.get("NBATOOLS_ACQUISITION_OUTPUT"):
            export = Path(output)
            export.mkdir(parents=True, exist_ok=True)
            assert not any(export.iterdir())
            shutil.copytree(destination, export, dirs_exist_ok=True)
    finally:
        reset_data_source_cache()
