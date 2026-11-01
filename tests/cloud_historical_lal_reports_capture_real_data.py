"""Capture fifteen fixed historical LAL gamebooks; no participation acceptance."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_read_csv, data_read_text

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
REQUEST_SHA = "89e2291465cfbb8eedc4e0a7848d35bd959addb269f0bb4d0407ebf6f3376d01"
AUDIT_SHA = "0a6498eb700741d0f71e5bd8bd11db2fdf17073643801f7462410a1b4ef89d86"
GAME_IDS = {
    22300163,
    22300331,
    22300669,
    22301055,
    22301155,
    22300187,
    22300316,
    22300380,
    22300549,
    22300618,
    22300788,
    22300802,
    22300915,
    22301045,
    22301143,
}
LAL = 1610612747


def test_capture_fifteen_fixed_lal_historical_reports():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    assert (
        hashlib.sha256(
            data_read_text("data/metadata/generation_manifest.json").encode()
        ).hexdigest()
        == MANIFEST
    )
    raw = (PROGRAM / "collection-requests/lal-participation-remaining-2023-24.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == REQUEST_SHA
    request = json.loads(raw)
    qualification = PROGRAM / "source-evidence/k08-direct-dependencies/coverage-audit.json"
    assert hashlib.sha256(qualification.read_bytes()).hexdigest() == AUDIT_SHA
    assert request["base_generation"] == BASE and request["base_manifest_sha256"] == MANIFEST
    assert request["target_team_id"] == LAL
    assert request["limits"] == dict(
        source_files=15,
        reader_invocations=15,
        attempts_per_file=1,
        timeout_seconds=20,
        pdf_max_bytes=1_500_000,
        aggregate_max_bytes=10_000_000,
        metered_overage_usd=0,
    )
    cases = request["games"]
    assert len(cases) == 15 and {int(case["game_id"]) for case in cases} == GAME_IDS
    teams = data_read_csv("data/raw/team_game_stats/2023-24_regular_season.csv")
    prepared = []
    for case in cases:
        assert case["imported_team_ids"] == [LAL]
        assert case["required_target_player_ids"] in ([203076], [2544])
        sides = teams.loc[teams.game_id.eq(int(case["game_id"]))]
        assert len(sides) == 2 and set(sides.team_id) == {LAL, case["opponent_team_id"]}
        assert set(sides.game_date) == {case["game_date"]}
        home = sides.loc[sides.is_home.eq(1)].iloc[0]
        away = sides.loc[sides.is_away.eq(1)].iloc[0]
        assert (away.team_abbr, home.team_abbr) == (case["away_abbr"], case["home_abbr"])
        assert [int(away.pts), int(home.pts)] == [case["away_points"], case["home_points"]]
        stamp = case["game_date"].replace("-", "")
        url = f"{report.SOURCE_ROOT}/{stamp}/{stamp}_{away.team_abbr}{home.team_abbr}.pdf"
        assert url == case["source_url"]
        prepared.append((case, away.team_name, home.team_name, url))
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "hist-lal-reports"
    output.mkdir(parents=True, exist_ok=False)
    receipts, failures = [], []
    total = 0
    calls = 0
    for case, away_name, home_name, url in prepared:
        cache = output / case["game_id"]
        cache.mkdir()
        receipt = dict(
            classification="official_report_capture_not_player_clock_or_import_acceptance",
            game_id=case["game_id"],
            source_url=url,
            source_reader_invocations=1,
            participation_qualified=False,
            clock_qualified=False,
            full_slice_accepted=False,
            production_writes=0,
        )
        try:
            assert total < 10_000_000
            calls += 1
            text = report._fetch_report_text(url, archive=cache)
            headings, sections, _ = report._parse_sections(text, case["game_date"])
            assert report._name(headings[0]).endswith(report._name(away_name))
            assert report._name(headings[1]).endswith(report._name(home_name))
            assert [report._score(section) for section in sections] == [
                case["away_points"],
                case["home_points"],
            ]
            stored = json.loads((cache / (Path(url).stem + ".json")).read_bytes())
            pdf = (cache / stored["raw_file"]).read_bytes()
            assert pdf.startswith(b"%PDF") and len(pdf) <= 1_500_000
            assert hashlib.sha256(pdf).hexdigest() == stored["sha256"]
            total += len(pdf)
            assert total <= 10_000_000
            receipt.update(capture_complete=True, source_receipt=stored)
        except Exception as exc:
            receipt.update(capture_complete=False, error_type=type(exc).__name__)
            failures.append(dict(game_id=case["game_id"], error_type=type(exc).__name__))
        finally:
            (cache / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
            receipts.append(receipt)
    summary = dict(
        classification="fifteen_bounded_captures_not_source_or_stage_acceptance",
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        collection_request_sha256=REQUEST_SHA,
        accepted_input_audit_review_sha256=AUDIT_SHA,
        source_reader_invocations=calls,
        attempts_per_file=1,
        pdf_bytes_retained=total,
        capture_receipts=receipts,
        failures=failures,
        stage_accepted=False,
        production_writes=0,
    )
    (output / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert not failures, failures
