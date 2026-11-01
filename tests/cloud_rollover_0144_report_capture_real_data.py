"""Explicit-only, one official report capture; starter positions remain unqualified."""

import hashlib
import io
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_read_text

ROOT = Path(__file__).resolve().parents[1]
REQUEST = (
    ROOT
    / "working/nba-tools-completion-program/collection-requests/rollover-0144-starter-report-2026-27.json"
)
REQUEST_SHA = "9f84e321385bf222e4e822d7235b784a81f7777b813580efd9515a7ef7ca8db3"
URL = "https://statsdmz.nba.com/pdfs/20261029/20261029_CLEATL.pdf"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
LIMIT = 1_500_000


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _prepare():
    raw = REQUEST.read_bytes()
    assert _sha(raw) == REQUEST_SHA
    request = json.loads(raw)
    assert (request["base_generation"], request["base_manifest_sha256"]) == (BASE, MANIFEST)
    assert request["limits"] == dict(
        source_files=1,
        reader_invocations=1,
        attempts_per_file=1,
        timeout_seconds=20,
        max_body_bytes=LIMIT,
        aggregate_max_bytes=LIMIT,
        redirects=0,
        retries=0,
        metered_overage_usd=0,
    )
    case = request["game"]
    assert case == dict(
        game_id="0022600144",
        game_date="2026-10-29",
        away_team_id=1610612739,
        away_abbr="CLE",
        away_name="Cleveland Cavaliers",
        away_points=111,
        home_team_id=1610612737,
        home_abbr="ATL",
        home_name="Atlanta Hawks",
        home_points=114,
        source_url=URL,
    )
    originals = {}
    for name, binding in request["retained_identity_sources"].items():
        body = (ROOT / binding["path"]).read_bytes()
        assert len(body) == binding["size_bytes"] and _sha(body) == binding["sha256"]
        originals[name] = body
    capture = json.loads(originals["capture"])
    assert capture["archive_revision"] == "7a1ab93e02f7a4d23443d3c6abb14bafe9c94f11"
    for name in ("summary", "pbp"):
        (item,) = [r for r in capture["files"] if r["file"] == name + ".json"]
        body = originals[name]
        assert item["sha256"] == _sha(body) and item["size"] == len(body)
        blob = b"blob " + str(len(body)).encode() + b"\0" + body
        assert hashlib.sha1(blob).hexdigest() == item["sha"]  # Git object identity.
    summary = json.loads(originals["summary"])["boxScoreSummary"]
    assert summary["gameId"] == case["game_id"] and summary["gameStatus"] == 3
    assert summary["gameCode"] == "20261029/CLEATL"
    assert summary["gameEt"][:10] == case["game_date"]
    for side in ("away", "home"):
        team = summary[side + "Team"]
        assert summary[side + "TeamId"] == team["teamId"] == case[side + "_team_id"]
        assert team["teamTricode"] == case[side + "_abbr"]
        assert team["score"] == case[side + "_points"]
    pbp = json.loads(originals["pbp"])["game"]
    assert pbp["gameId"] == case["game_id"]
    scored = [r for r in pbp["actions"] if r.get("scoreHome") and r.get("scoreAway")]
    assert [int(scored[-1]["scoreAway"]), int(scored[-1]["scoreHome"])] == [111, 114]
    with ZipFile(io.BytesIO(originals["schedule_zip"])) as archive:
        schedule_raw = archive.read(request["schedule_original"]["member"])
    binding = request["schedule_original"]
    assert len(schedule_raw) == binding["size_bytes"] and _sha(schedule_raw) == binding["sha256"]
    schedule = json.loads(schedule_raw)["leagueSchedule"]
    assert schedule["seasonYear"] == "2026-27"
    (game,) = [
        g for day in schedule["gameDates"] for g in day["games"] if g["gameId"] == case["game_id"]
    ]
    assert game["gameStatus"] == 3 and game["gameCode"] == summary["gameCode"]
    assert game["gameDateEst"][:10] == case["game_date"]
    for side in ("away", "home"):
        assert game[side + "Team"]["teamId"] == case[side + "_team_id"]
        assert game[side + "Team"]["score"] == case[side + "_points"]
    return request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_report():
    # Same established report-reader header/timeout; redirects explicitly disabled.
    request = urllib.request.Request(
        URL, headers={"User-Agent": "Mozilla/5.0 (NBATools official box-score ingest)"}
    )
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=20)


def _capture(case, output):
    assert case["source_url"] == URL and case["game_id"] == "0022600144"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        classification="official_report_envelope_capture_not_starter_position_qualification",
        game_id=case["game_id"],
        source_url=URL,
        collection_request_sha256=REQUEST_SHA,
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        started_at=datetime.now(UTC).isoformat(),
        source_reader_invocations=0,
        capture_complete=False,
        envelope_verified=False,
        starter_positions_qualified=False,
        participation_qualified=False,
        clock_qualified=False,
        full_slice_accepted=False,
        production_writes=0,
        readiness_accepted=False,
        stage_accepted=False,
        returned_body=None,
        failure=None,
    )

    def retain(raw):
        bounded = len(raw) <= LIMIT
        receipt["returned_body"] = dict(
            bytes_read=len(raw),
            sha256_of_bytes_read=_sha(raw),
            retained=bounded,
            read_limit_exceeded=not bounded,
        )
        if bounded:
            # Keep even invalid/non-PDF returned bodies before content/strict guards.
            suffix = ".pdf" if raw.startswith(b"%PDF") else ".body"
            path = output / (_sha(raw) + suffix)
            path.write_bytes(raw)
            receipt["returned_body"]["raw_file"] = path.name
            if suffix == ".pdf":
                report._archive_report(raw, URL, output)

    try:
        receipt["source_reader_invocations"] = 1
        try:
            with _open_report() as response:
                receipt["http_status"] = response.status
                receipt["content_type"] = response.headers.get("Content-Type", "")
                raw = response.read(LIMIT + 1)
                retain(raw)
                assert response.geturl() == URL
        except urllib.error.HTTPError as exc:
            # One failed attempt, no retry. Preserve any bounded HTTP error body too.
            receipt["http_status"] = exc.code
            try:
                retain(exc.read(LIMIT + 1))
            finally:
                exc.close()
            raise
        assert receipt["http_status"] == 200
        assert "application/pdf" in receipt["content_type"].lower()
        text = report._report_text(raw)
        headings, sections, _ = report._parse_sections(text, case["game_date"])
        for heading, side in zip(headings, ("away", "home"), strict=True):
            assert report._name(heading).endswith(report._name(case[side + "_name"]))
        assert [report._score(s) for s in sections] == [111, 114]
        receipt.update(capture_complete=True, envelope_verified=True)
    except Exception as exc:
        receipt["failure"] = dict(error_type=type(exc).__name__, message=str(exc))
        raise
    finally:
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        (output / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


@pytest.mark.needs_data
@pytest.mark.engine
def test_capture_only_0144_official_report_for_starter_role_research():
    request = _prepare()  # All retained source bindings checked BEFORE the one reader.
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    assert _sha(data_read_text("data/metadata/generation_manifest.json").encode()) == MANIFEST
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "rollover-0144-official-report"
    _capture(request["game"], output)
