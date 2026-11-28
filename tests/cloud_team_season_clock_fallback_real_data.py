"""Capture two exact Final Box alternatives for the W8 archive clock failures."""

import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError

import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_read_csv, data_read_text

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
BASE = "availability-cleveland-2024-v3-20261124"
MANIFEST = "d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034"
CASES = (
    {
        "game_id": "0022500253",
        "date": "2025-11-18",
        "away": (1610612762, "UTA", 126),
        "home": (1610612747, "LAL", 140),
        "archive_clock": "29:60",
        "archive_traditional_sha256": "3c054786149b4f0068b1ad0754b866ba44d94bf54ead4741f7c468aee73777f2",
    },
    {
        "game_id": "0022501052",
        "date": "2026-03-25",
        "away": (1610612747, "LAL", 137),
        "home": (1610612754, "IND", 130),
        "archive_clock": "27:60",
        "archive_traditional_sha256": "bfe357c728c5ba499f1619015414b60f62a81143dcfec59880140a04ac071759",
    },
)


def test_capture_two_pinned_team_season_final_boxes():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    manifest = data_read_text("data/metadata/generation_manifest.json")
    assert hashlib.sha256(manifest.encode()).hexdigest() == MANIFEST
    assert json.loads(manifest)["generation_id"] == BASE
    suffix = "2025-26_regular_season.csv"
    catalog = data_read_csv(f"data/raw/games/{suffix}")
    teams = data_read_csv(f"data/raw/team_game_stats/{suffix}")
    prepared = []
    for case in CASES:
        game_id = int(case["game_id"])
        game = catalog.loc[catalog.game_id.eq(game_id)].squeeze()
        assert str(game.is_final).lower() in {"true", "1"}
        assert game.game_date == case["date"]
        assert (int(game.away_team_id), int(game.home_team_id)) == (
            case["away"][0],
            case["home"][0],
        )
        sides = teams.loc[teams.game_id.eq(game_id)]
        assert len(sides) == 2 and set(sides.game_date) == {case["date"]}
        names = []
        for side in ("away", "home"):
            row = sides.loc[sides[f"is_{side}"].eq(1)].squeeze()
            assert (int(row.team_id), row.team_abbr, int(row.pts)) == case[side]
            names.append(row.team_name)
        stamp = case["date"].replace("-", "")
        ref = f"{stamp}_{case['away'][1]}{case['home'][1]}"
        prepared.append((case, names, f"{report.SOURCE_ROOT}/{stamp}/{ref}.pdf"))

    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "w8-team-season-clock-reports"
    output.mkdir(parents=True, exist_ok=False)
    attempts, failures, byte_count = [], [], 0
    started = perf_counter()
    for case, names, url in prepared:
        cache = output / case["game_id"]
        cache.mkdir()
        attempt = dict(game_id=case["game_id"], source_url=url, source_reader_invocations=1)
        tick = perf_counter()
        try:
            text = report._fetch_report_text(url, archive=cache)
            headings, sections, _ = report._parse_sections(text, case["date"])
            assert all(
                report._name(name).endswith(report._name(heading))
                for name, heading in zip(names, headings, strict=True)
            )
            assert [report._score(section) for section in sections] == [
                case["away"][2],
                case["home"][2],
            ]
            stored = json.loads((cache / (Path(url).stem + ".json")).read_bytes())
            raw = (cache / stored["raw_file"]).read_bytes()
            assert raw.startswith(b"%PDF") and len(raw) <= 1_500_000
            assert stored["size_bytes"] == len(raw) and stored["source_url"] == url
            assert hashlib.sha256(raw).hexdigest() == stored["sha256"]
            byte_count += len(raw)
            assert byte_count <= 3_000_000
            attempt.update(capture_complete=True, source_receipt=stored)
        except Exception as exc:
            attempt.update(capture_complete=False, error_type=type(exc).__name__)
            if isinstance(exc, HTTPError):
                attempt["http_status"] = exc.code
            elif isinstance(exc, URLError):
                attempt["transport_reason"] = str(exc.reason)[:256]
            failures.append(attempt)
        finally:
            attempt["elapsed_seconds"] = round(perf_counter() - tick, 3)
            (cache / "capture.json").write_text(json.dumps(attempt, indent=2) + "\n")
            attempts.append(attempt)
    summary = dict(
        classification="two_bounded_final_box_captures",
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        archive_clock_failures=CASES,
        source_reader_invocations=len(attempts),
        attempts_per_file=1,
        pdf_bytes_retained=byte_count,
        wall_seconds=round(perf_counter() - started, 3),
        attempts=attempts,
        failures=failures,
        participation_qualified=False,
        production_writes=0,
    )
    (output / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert not failures, failures
