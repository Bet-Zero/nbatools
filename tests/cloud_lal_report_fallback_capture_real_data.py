"""Capture one official scorer report through the existing bounded report reader."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_read_csv, data_read_text

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
GAME = 22500708
URL = "https://statsdmz.nba.com/pdfs/20260201/20260201_LALNYK.pdf"


def test_capture_one_official_0708_report_without_clock_waiver():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    assert (
        hashlib.sha256(
            data_read_text("data/metadata/generation_manifest.json").encode()
        ).hexdigest()
        == MANIFEST
    )
    teams = data_read_csv("data/raw/team_game_stats/2025-26_regular_season.csv")
    sides = teams.loc[teams.game_id.eq(GAME)].copy()
    assert len(sides) == 2 and set(sides.team_id) == {1610612747, 1610612752}
    assert set(sides.game_date) == {"2026-02-01"}
    assert sides.loc[sides.team_id.eq(1610612747), "is_away"].item() == 1
    expected = dict(zip(sides.team_abbr, sides.pts))
    assert expected == {"LAL": 100, "NYK": 112}
    assert URL == report.SOURCE_ROOT + "/20260201/20260201_LALNYK.pdf"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "lal-0708-official-report"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        classification="one_official_report_capture_not_participation_or_clock_acceptance",
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        game_id=GAME,
        game_date="2026-02-01",
        source_url=URL,
        source_reader_invocations=0,
        source_byte_limit=1_500_000,
        source_timeout_seconds=20,
        scope="one official0708FinalBox; existing reader/headers; no other endpoint",
        imported_team_scope=[1610612747],
        participation_qualification=False,
        clock_qualification=False,
        full_slice_accepted=False,
        production_writes=0,
    )
    try:
        receipt["source_reader_invocations"] = 1
        text = report._fetch_report_text(URL, archive=output)
        headings, sections, _ = report._parse_sections(text, "2026-02-01")
        assert report._name(headings[0]).endswith(report._name("Los Angeles Lakers"))
        assert report._name(headings[1]).endswith(report._name("New York Knicks"))
        assert [report._score(section) for section in sections] == [100, 112]
        stored = json.loads((output / "20260201_LALNYK.json").read_bytes())
        raw = (output / stored["raw_file"]).read_bytes()
        assert raw.startswith(b"%PDF") and len(raw) <= 1_500_000
        assert hashlib.sha256(raw).hexdigest() == stored["sha256"]
        receipt.update(capture_complete=True, source_receipt=stored)
    except Exception as exc:
        receipt.update(capture_complete=False, error_type=type(exc).__name__)
        raise
    finally:
        (output / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
