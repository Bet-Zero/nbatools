"""Capture four fixed official reports; preserve strict archive clock failures."""

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
REQUEST_SHA = "7558eda7a1659fe1c39b9c61608c343a7869219be44cbfece4c000895f197105"
QUALIFICATION_SHA = "779f582675bfd16aaf3ba94d07cf47f1cb6da5dcb42d7c78c45846b0403c4f70"
GAME_IDS = {22500250, 22500580, 22500660, 22500721}
BOS = 1610612738


def test_capture_four_official_bos_reports_without_clock_waiver():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    assert (
        hashlib.sha256(
            data_read_text("data/metadata/generation_manifest.json").encode()
        ).hexdigest()
        == MANIFEST
    )
    raw = (PROGRAM / "collection-requests/bos-clock-report-fallback-2025-26.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == REQUEST_SHA
    request = json.loads(raw)
    qualification = PROGRAM / "source-evidence/k08-bos-remaining/source-qualification.json"
    assert hashlib.sha256(qualification.read_bytes()).hexdigest() == QUALIFICATION_SHA
    assert request["base_generation"] == BASE and request["base_manifest_sha256"] == MANIFEST
    assert request["target_team_id"] == BOS
    assert request["limits"] == dict(
        source_files=4,
        reader_invocations=4,
        attempts_per_file=1,
        timeout_seconds=20,
        pdf_max_bytes=1_500_000,
        aggregate_max_bytes=6_000_000,
        metered_overage_usd=0,
    )
    cases = request["games"]
    assert len(cases) == 4 and {int(case["game_id"]) for case in cases} == GAME_IDS
    teams = data_read_csv("data/raw/team_game_stats/2025-26_regular_season.csv")
    prepared = []
    for case in cases:
        assert case["imported_team_ids"] == [BOS]
        assert case["required_target_player_ids"] == [1628369]
        sides = teams.loc[teams.game_id.eq(int(case["game_id"]))]
        assert len(sides) == 2 and set(sides.team_id) == {BOS, case["opponent_team_id"]}
        assert set(sides.game_date) == {case["game_date"]}
        home = sides.loc[sides.is_home.eq(1)].iloc[0]
        away = sides.loc[sides.is_away.eq(1)].iloc[0]
        assert (away.team_abbr, home.team_abbr) == (case["away_abbr"], case["home_abbr"])
        assert [int(away.pts), int(home.pts)] == [case["away_points"], case["home_points"]]
        stamp = case["game_date"].replace("-", "")
        url = f"{report.SOURCE_ROOT}/{stamp}/{stamp}_{away.team_abbr}{home.team_abbr}.pdf"
        assert url == case["source_url"]
        prepared.append((case, away.team_name, home.team_name, url))
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "bos-clock-reports"
    output.mkdir(parents=True, exist_ok=False)
    receipts, failures = [], []
    total = 0
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
            assert total <= 6_000_000
            receipt.update(capture_complete=True, source_receipt=stored)
        except Exception as exc:
            receipt.update(capture_complete=False, error_type=type(exc).__name__)
            failures.append(dict(game_id=case["game_id"], error_type=type(exc).__name__))
        finally:
            (cache / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
            receipts.append(receipt)
    summary = dict(
        classification="four_bounded_captures_not_source_or_stage_acceptance",
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        collection_request_sha256=REQUEST_SHA,
        preserved_blocked_source_qualification_sha256=QUALIFICATION_SHA,
        source_reader_invocations=4,
        attempts_per_file=1,
        pdf_bytes_retained=total,
        capture_receipts=receipts,
        failures=failures,
        stage_accepted=False,
        production_writes=0,
    )
    (output / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert not failures, failures
