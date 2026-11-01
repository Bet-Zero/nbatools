"""One bounded official gamebook capture; no reported-rest or clinical acceptance."""

import hashlib
import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_generation_context, data_path

pytestmark = pytest.mark.engine
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
REQUEST = PROGRAM / "collection-requests/luka-reported-reasons-2025-26.json"
REQUEST_SHA = "6b10ba37eba43064d99e1830ce58ceb08ffb7b6f64fac26d1d825551b05e7124"
AUDIT_SHA = "d7732843931e7b4f0534a6c65aaf191f9e5f285fa5d66bbd3ccd1e4bf718c9dc"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
REPRESENTATIVE = "0022500136"
LAL, LUKA = 1610612747, 1629029
PDF_LIMIT = 1_500_000
GAME_IDS = {
    22500136,
    22500163,
    22500336,
    22500418,
    22500601,
    22500753,
    22500769,
    22500774,
    22500791,
    22501140,
    22501155,
    22501170,
    22501185,
    22501198,
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _prepare():
    raw = REQUEST.read_bytes()
    assert _sha(raw) == REQUEST_SHA
    request = json.loads(raw)
    assert (request["base_generation"], request["base_manifest_sha256"]) == (BASE, MANIFEST)
    audit_raw = (PROGRAM.parent.parent / request["reason_coverage_audit"]["path"]).read_bytes()
    assert _sha(audit_raw) == request["reason_coverage_audit"]["sha256"] == AUDIT_SHA
    audit = json.loads(audit_raw)
    assert len(request["games"]) == 14 and {int(r["game_id"]) for r in request["games"]} == GAME_IDS
    assert {(r["game_id"], r["team_id"], r["player_id"]) for r in request["games"]} == {
        (r["game_id"], r["team_id"], r["player_id"]) for r in audit["minimum_remaining_reason_keys"]
    }
    assert request["full_batch_structural_limits"] == dict(
        source_files=14,
        reader_invocations=14,
        attempts_per_file=1,
        timeout_seconds=20,
        pdf_max_bytes=PDF_LIMIT,
        aggregate_max_bytes=14 * PDF_LIMIT,
        metered_overage_usd=0,
    )
    assert request["representative_capture"] == dict(
        game_id=REPRESENTATIVE,
        source_files=1,
        reader_invocations=1,
        attempts_per_file=1,
        timeout_seconds=20,
        pdf_max_bytes=PDF_LIMIT,
        aggregate_max_bytes=PDF_LIMIT,
        metered_overage_usd=0,
    )
    assert request["remaining13_execution"]["implemented"] is False
    assert request["remaining13_execution"]["source_reader_invocations"] == 0
    assert {r["game_id"] for r in request["reuse_without_refetch"]} == {
        "0022500113",
        "0022500122",
        "0022500338",
        "0022501098",
    }
    with data_generation_context() as generation:
        assert generation == BASE
        manifest_raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(manifest_raw) == MANIFEST
        manifest = json.loads(manifest_raw)
        assert manifest["generation_id"] == BASE and len(manifest["files"]) == 775
        entries = {r["path"]: r for r in manifest["files"]}
        frames = {}
        for item in request["canonical_files"]:
            assert entries[item["path"]] == item
            raw = data_path("data/" + item["path"]).read_bytes()
            assert _sha(raw) == item["sha256"] and len(raw) == item["size_bytes"]
            frames[item["path"].split("/")[1]] = pd.read_csv(io.BytesIO(raw))
    teams, catalog = frames["team_game_stats"], frames["games"]
    prepared = {}
    for case in request["games"]:
        assert (case["team_id"], case["player_id"]) == (LAL, LUKA)
        assert case["reason_state_before"] == "unknown" and case["required_target_player_ids"] == [
            LUKA
        ]
        sides = teams.loc[teams.game_id.eq(int(case["game_id"]))]
        assert len(sides) == sides.team_id.nunique() == 2
        assert set(sides.team_id) == set(sides.opponent_team_id) == {LAL, case["opponent_team_id"]}
        assert sides.game_date.eq(case["game_date"]).all()
        assert sides.season.eq("2025-26").all() and sides.season_type.eq("Regular Season").all()
        home, away = sides.loc[sides.is_home.eq(1)], sides.loc[sides.is_away.eq(1)]
        assert len(home) == len(away) == 1
        home, away = home.iloc[0], away.iloc[0]
        assert [int(away.team_id), int(home.team_id)] == [
            case["away_team_id"],
            case["home_team_id"],
        ]
        assert [away.team_abbr, home.team_abbr] == [case["away_abbr"], case["home_abbr"]]
        assert [int(away.pts), int(home.pts)] == [case["away_points"], case["home_points"]]
        game = catalog.loc[catalog.game_id.eq(int(case["game_id"]))]
        assert len(game) == 1 and str(game.is_final.item()).lower() in {"1", "true"}
        assert game.game_date.item() == case["game_date"]
        assert game.season.item() == "2025-26" and game.season_type.item() == "Regular Season"
        for field, value in [("home_team_id", home.team_id), ("away_team_id", away.team_id)]:
            if pd.notna(game[field].item()):
                assert int(game[field].item()) == int(value)
        stamp = case["game_date"].replace("-", "")
        assert (
            case["source_url"]
            == f"{report.SOURCE_ROOT}/{stamp}/{stamp}_{away.team_abbr}{home.team_abbr}.pdf"
        )
        prepared[case["game_id"]] = dict(case, away_name=away.team_name, home_name=home.team_name)
    return prepared[REPRESENTATIVE]


def _capture_one(case, cache):
    cache.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        classification="representative_source_envelope_capture_not_reported_reason_acceptance",
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        collection_request_sha256=REQUEST_SHA,
        reason_coverage_audit_sha256=AUDIT_SHA,
        game_id=case["game_id"],
        game_date=case["game_date"],
        source_url=case["source_url"],
        source_reader_invocations=0,
        attempts_per_file=1,
        timeout_seconds=20,
        pdf_max_bytes=PDF_LIMIT,
        capture_complete=False,
        reported_reason_qualified=False,
        participation_qualified=False,
        clinical_status_qualified=False,
        full_slice_accepted=False,
        production_writes=0,
    )
    (cache / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        reader = report._fetch_report_text
        receipt["attempt_started_at"] = datetime.now(UTC).isoformat()
        receipt["source_reader_invocations"] = 1
        text = reader(case["source_url"], archive=cache)
        headings, sections, _ = report._parse_sections(text, case["game_date"])
        assert report._name(headings[0]).endswith(report._name(case["away_name"]))
        assert report._name(headings[1]).endswith(report._name(case["home_name"]))
        assert [report._score(section) for section in sections] == [
            case["away_points"],
            case["home_points"],
        ]
        stored = json.loads((cache / (Path(case["source_url"]).stem + ".json")).read_bytes())
        raw = (cache / stored["raw_file"]).read_bytes()
        assert stored["source_url"] == case["source_url"]
        assert raw.startswith(b"%PDF") and len(raw) == stored["size_bytes"] <= PDF_LIMIT
        assert _sha(raw) == stored["sha256"]
        receipt.update(capture_complete=True, source_receipt=stored)
    except Exception as exc:
        receipt.update(error_type=type(exc).__name__, error_message=str(exc))
        raise
    finally:
        # Count every archived PDF even when date/score/other qualification failed.
        archived = [
            dict(
                file=p.name,
                size_bytes=p.stat().st_size,
                sha256=_sha(p.read_bytes()) if p.stat().st_size <= PDF_LIMIT else None,
            )
            for p in sorted(cache.glob("*.pdf"))
        ]
        receipt["retained_pdf_files"] = archived
        receipt["retained_pdf_bytes"] = sum(r["size_bytes"] for r in archived)
        receipt["retention_limits_passed"] = (
            len(archived) <= 1
            and all(r["size_bytes"] <= PDF_LIMIT for r in archived)
            and receipt["retained_pdf_bytes"] <= PDF_LIMIT
        )
        receipt["capture_complete"] &= receipt["retention_limits_passed"]
        (cache / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert receipt["capture_complete"]
    return receipt


@pytest.mark.needs_data
def test_capture_one_luka_reason_representative_only():
    case = _prepare()
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "luka-reason-representative"
    cache = output / REPRESENTATIVE
    try:
        _capture_one(case, cache)
    finally:
        if (cache / "capture.json").exists():
            receipt = json.loads((cache / "capture.json").read_bytes())
            summary = dict(
                classification="one_representative_only_remaining13_not_implemented",
                source_reader_invocations=receipt["source_reader_invocations"],
                retained_pdf_bytes=receipt["retained_pdf_bytes"],
                capture_complete=receipt["capture_complete"],
                remaining_source_reader_invocations=0,
                request_sha256=REQUEST_SHA,
                audit_sha256=AUDIT_SHA,
                source_cases=[
                    dict(
                        game_id=f"{gid:010d}",
                        source_reader_invocations=receipt["source_reader_invocations"]
                        if gid == int(REPRESENTATIVE)
                        else 0,
                    )
                    for gid in sorted(GAME_IDS)
                ],
                reported_reason_qualified=False,
                production_writes=0,
            )
            (output / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def _synthetic_reader(monkeypatch, *, bad_date=False, timeout=False):
    def fetch(url, *, archive):
        assert json.loads((archive / "capture.json").read_bytes())["source_reader_invocations"] == 0
        if timeout:
            raise TimeoutError("synthetic read timeout")
        raw = b"%PDF synthetic unit bytes; not NBA evidence"
        digest = _sha(raw)
        (archive / f"{digest}.pdf").write_bytes(raw)
        (archive / (Path(url).stem + ".json")).write_text(
            json.dumps(
                dict(source_url=url, raw_file=f"{digest}.pdf", sha256=digest, size_bytes=len(raw))
            )
        )
        date = "Thursday, October 30, 2025" if bad_date else "Wednesday, October 29, 2025"
        return f"NATIONAL BASKETBALL ASSOCIATION\nFINAL BOX\n{date}\nVISITOR: Los Angeles Lakers (3-2)\n240:00 0 116\nHOME: Minnesota Timberwolves (2-3)\n240:00 0 115\nSCORE BY PERIOD\n"

    monkeypatch.setattr(report, "_fetch_report_text", fetch)
    return dict(
        game_id=REPRESENTATIVE,
        game_date="2025-10-29",
        source_url=report.SOURCE_ROOT + "/20251029/20251029_LALMIN.pdf",
        away_name="Los Angeles Lakers",
        home_name="Minnesota Timberwolves",
        away_points=116,
        home_points=115,
    )


def test_synthetic_date_failure_retains_and_counts_original_bytes(tmp_path, monkeypatch):
    case = _synthetic_reader(monkeypatch, bad_date=True)
    with pytest.raises(ValueError, match="date differs"):
        _capture_one(case, tmp_path / "cache")
    receipt = json.loads((tmp_path / "cache/capture.json").read_bytes())
    assert receipt["source_reader_invocations"] == 1 and not receipt["capture_complete"]
    assert receipt["retained_pdf_bytes"] == len(b"%PDF synthetic unit bytes; not NBA evidence")
    assert len(receipt["retained_pdf_files"]) == 1 and receipt["retention_limits_passed"]


def test_synthetic_reader_failure_records_one_attempt_and_zero_bytes(tmp_path, monkeypatch):
    case = _synthetic_reader(monkeypatch, timeout=True)
    with pytest.raises(TimeoutError):
        _capture_one(case, tmp_path / "cache")
    receipt = json.loads((tmp_path / "cache/capture.json").read_bytes())
    assert receipt["source_reader_invocations"] == 1 and receipt["retained_pdf_bytes"] == 0
    assert receipt["error_type"] == "TimeoutError" and not receipt["capture_complete"]


def test_synthetic_success_is_envelope_capture_without_reason_promotion(tmp_path, monkeypatch):
    case = _synthetic_reader(monkeypatch)
    receipt = _capture_one(case, tmp_path / "cache")
    assert receipt["capture_complete"] and receipt["source_reader_invocations"] == 1
    assert not receipt["reported_reason_qualified"] and not receipt["clinical_status_qualified"]
