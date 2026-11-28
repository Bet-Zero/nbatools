"""Exercise the exact planner-to-capture-to-stage handoff without network access."""

import hashlib
import io
import json

import pytest
from requests import HTTPError, Response
from requests.adapters import HTTPAdapter
from urllib3.response import HTTPResponse

from nbatools.data_source import reset_data_source_cache
from tests.test_plan_participation_collection import retained_collection  # noqa: F401
from tests.test_structured_participation import source  # noqa: F401
from tools import capture_participation_batch as capture
from tools.capture_participation_batch import capture_batch
from tools.cloud_nba_archive import fetch_capture
from tools.plan_participation_collection import (
    REMOTE_BODY_BOUND_BYTES,
    _source_url,
    plan_collection,
)
from tools.stage_participation_collection import build_stage

pytestmark = pytest.mark.engine
BATCH = "2025-26_regular_season-awaiting-originals"
MISSING = "boxscoresummaryv3_0022500005.json"
GAME = "0022500005"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _write(path, payload):
    raw = json.dumps(payload).encode()
    path.write_bytes(raw)
    return _sha(raw)


def _no_fetch(*args, **kwargs):
    pytest.fail(f"Unplanned request: {args[0]}")


@pytest.fixture
def draft(retained_collection, tmp_path):  # noqa: F811 - reuse the planner's native fixture
    root, manifest, held, trees, index, index_sha = retained_collection
    work = tmp_path / "original-plan"
    plan_collection(
        root,
        work,
        manifest_sha256=manifest,
        scopes=[("2025-26", "Regular Season", 1), ("2025-26", "Regular Season", 2)],
        held_captures=[held],
        archive_trees=trees,
        archive_index_receipt=index,
        archive_index_receipt_sha256=index_sha,
        max_games=2,
        max_remote_calls=1,
        max_remote_bytes=REMOTE_BODY_BOUND_BYTES,
    )
    return (
        work / "plan.json",
        {endpoint: path for (year, endpoint), path in trees.items() if year == "2026"},
        index,
        retained_collection,
    )


def _capture(draft, output, *, fetch=_no_fetch, plan_sha=None, **options):
    plan, trees, index, _ = draft
    return capture_batch(
        plan,
        plan_sha or _sha(plan.read_bytes()),
        BATCH,
        output,
        trees=trees,
        archive_receipt=index,
        fetch=fetch,
        **options,
    )


def _exact_summary():
    return json.dumps(
        {
            "boxScoreSummary": dict(
                gameId=GAME,
                gameEt="2025-10-24",
                gameStatus=3,
                homeTeamId=1,
                awayTeamId=2,
                homeTeam=dict(teamId=1, teamTricode="AAA", score=10, inactives=[]),
                awayTeam=dict(teamId=2, teamTricode="BBB", score=8, inactives=[]),
            )
        }
    ).encode()


def test_one_missing_original_enters_native_stage_without_recollecting_held(
    draft, tmp_path, monkeypatch
):
    root, manifest, held, trees, index, index_sha = draft[-1]
    captured = tmp_path / "captured"
    requests = []

    def fetch(path, destination, revision, *, direct_200):
        assert direct_200
        requests.append(path)
        assert path == f"nba_stats/json/boxscoresummaryv3/2026/{GAME}.json"
        raw = _exact_summary()
        destination.write_bytes(raw)
        return dict(
            url=_source_url(2026, "boxscoresummaryv3", GAME), bytes=len(raw), sha256=_sha(raw)
        )

    receipt = _capture(draft, captured, fetch=fetch)
    assert len(requests) == receipt["body_requests"] == 1
    assert receipt["complete"] and receipt["held_originals"] == 1
    assert receipt["measured_body_bytes"] == len(_exact_summary())
    assert not list((captured / "failed-originals").iterdir())
    assert (captured / "sources" / MISSING).read_bytes() == _exact_summary()
    # A new invocation can reuse a completed immutable body without a second request.
    prior = captured / "capture-attempts.json"
    with pytest.raises(ValueError, match="already attempted"):
        _capture(draft, tmp_path / "unneeded-repeat", prior_attempts=[prior])
    reused = _capture(draft, tmp_path / "reused", held_captures=[captured], prior_attempts=[prior])
    assert reused["body_requests"] == 0 and reused["held_originals"] == 2 and reused["complete"]

    replanned = tmp_path / "replanned"
    plan = plan_collection(
        root,
        replanned,
        manifest_sha256=manifest,
        scopes=[("2025-26", "Regular Season", 1)],
        held_captures=[held, captured],
        archive_trees=trees,
        archive_index_receipt=index,
        archive_index_receipt_sha256=index_sha,
        max_games=2,
    )
    assert plan["metrics"]["actual_remote_calls"] == plan["metrics"]["planned_remote_calls"] == 0
    stage = replanned / "2025-26_regular_season"
    established = tmp_path / "established"
    generations = established / "data/generations"
    generations.mkdir(parents=True)
    (generations / "base-fixture").symlink_to(root, target_is_directory=True)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(established))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "base-fixture")
    reset_data_source_cache()
    try:
        validation = build_stage(
            stage / "request.json",
            stage / "capture",
            tmp_path / "stage-work",
            tmp_path / "stage-out",
            candidate_sha="c" * 40,
        )
    finally:
        reset_data_source_cache()
    assert {game["game_id"] for game in validation["qualified_games"]} == {"0022500003", GAME}


@pytest.mark.parametrize("fault", ["http", "wrong_body"])
def test_failure_receipt_keeps_observable_bytes_and_prevents_repeat(draft, tmp_path, fault):
    captured = tmp_path / "failure"
    wrong = b'{"substituted":true}'

    def fetch(path, target, revision, *, direct_200):
        assert direct_200
        if fault == "http":
            response = Response()
            response.status_code = 403
            raise HTTPError("access denied", response=response)
        target.write_bytes(wrong)
        return dict(
            url=_source_url(2026, "boxscoresummaryv3", GAME), bytes=len(wrong), sha256=_sha(wrong)
        )

    summary = _capture(draft, captured, fetch=fetch)
    attempts = captured / "capture-attempts.json"
    (record,) = json.loads(attempts.read_bytes())["attempts"]
    assert not summary["complete"] and summary["remaining_originals"] == [MISSING]
    assert summary["body_requests"] == 1 and record["status"] == "failed"
    if fault == "http":
        assert record["http_status"] == 403
        assert summary["unmeasured_body_attempts"] == [MISSING]
    else:
        assert (captured / "failed-originals" / MISSING).read_bytes() == wrong
        assert record["sha256"] == _sha(wrong)
        assert summary["measured_body_bytes"] == len(wrong)
    assert not (captured / "sources" / MISSING).exists()
    with pytest.raises(ValueError, match="already attempted"):
        _capture(draft, tmp_path / "blocked-repeat", prior_attempts=[attempts])


def test_failed_manifest_commit_keeps_bytes_and_reports_original_pending(
    draft, tmp_path, monkeypatch
):
    output = tmp_path / "manifest-write-failure"
    exact = _exact_summary()
    persist = capture._update

    def update(path, payload):
        if path.name == "sources.json" and MISSING in payload["files"]:
            raise OSError("controlled sources manifest commit failure")
        return persist(path, payload)

    def fetch(path, destination, revision, *, direct_200):
        assert direct_200
        destination.write_bytes(exact)
        return dict(
            url=_source_url(2026, "boxscoresummaryv3", GAME), bytes=len(exact), sha256=_sha(exact)
        )

    monkeypatch.setattr(capture, "_update", update)
    summary = _capture(draft, output, fetch=fetch)
    (attempt,) = json.loads((output / "capture-attempts.json").read_bytes())["attempts"]
    manifest = json.loads((output / "sources.json").read_bytes())
    assert not summary["complete"] and summary["remaining_originals"] == [MISSING]
    assert MISSING not in manifest["files"] and not (output / "sources" / MISSING).exists()
    assert attempt["status"] == "failed" and attempt["error_type"] == "OSError"
    assert "manifest commit failure" in attempt["error"]
    assert (output / attempt["retained_original"]).read_bytes() == exact


@pytest.mark.parametrize("status", [200, 302, 206])
def test_adapter_reads_only_direct_200_bodies(draft, tmp_path, monkeypatch, status):
    decoded = _exact_summary() if status == 200 else b"x" * 8_100_000
    raw = HTTPResponse(
        body=io.BytesIO(decoded),
        preload_content=False,
        headers={"Content-Length": str(len(decoded))},
        status=status,
    )
    urls = []

    def send(adapter, request, **kwargs):
        urls.append(request.url)
        assert len(urls) == 1, "Reached an unplanned second host"
        response = Response()
        response.request = request
        response.url = request.url
        response.status_code = status
        response.headers["Location"] = "https://redirect-fixture.invalid/overscope"
        response.raw = raw
        return response

    monkeypatch.setattr(HTTPAdapter, "send", send)
    output = tmp_path / "nondirect"
    summary = _capture(draft, output, fetch=fetch_capture)
    (attempt,) = json.loads((output / "capture-attempts.json").read_bytes())["attempts"]
    assert urls == [_source_url(2026, "boxscoresummaryv3", GAME)] and summary["body_requests"] == 1
    if status == 200:
        assert summary["complete"] and summary["measured_body_bytes"] == len(decoded)
        assert (output / "sources" / MISSING).read_bytes() == decoded
    else:
        assert raw.tell() == 0 and summary["measured_body_bytes"] == 0
        assert not summary["complete"] and summary["remaining_originals"] == [MISSING]
        assert attempt["status"] == "failed" and attempt["http_status"] == status


@pytest.mark.parametrize("fault", ["plan_sha", "request", "cap", "scope", "blob"])
def test_rejects_bad_or_rebound_inconsistent_draft_before_fetch(draft, tmp_path, fault):
    plan = draft[0]
    body = json.loads(plan.read_bytes())
    request_path = plan.parent / BATCH / "request.json"
    request = json.loads(request_path.read_bytes())
    if fault == "plan_sha":
        with pytest.raises(ValueError, match="checksum"):
            _capture(draft, tmp_path / "bad", plan_sha="0" * 64)
        return
    if fault == "cap":
        body["budget"]["remote_body_bytes"] -= 1
    elif fault == "scope":
        request["requirements"][0]["game_date"] = "2025-10-25"
    elif fault == "blob":
        source = next(
            s
            for s in request["requirements"][0]["proposed_sources"]
            if s["endpoint"] == "boxscoresummaryv3"
        )
        request["source_files"][MISSING]["git_blob_sha"] = source["git_blob_sha"] = "f" * 40
    request_sha = _write(request_path, request)
    if fault != "request":
        next(item for item in body["stage_batches"] if item["directory"] == BATCH)[
            "request_sha256"
        ] = request_sha
        _write(plan, body)
    with pytest.raises(ValueError, match="checksum|budget|Git blob|noncanonical"):
        _capture(draft, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
