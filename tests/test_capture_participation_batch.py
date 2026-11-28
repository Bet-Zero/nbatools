"""Exercise the exact planner-to-capture-to-stage handoff without network access."""

import hashlib
import json

import pytest
from requests import HTTPError, Response

from nbatools.data_source import reset_data_source_cache
from tests.test_plan_participation_collection import retained_collection  # noqa: F401
from tests.test_structured_participation import source  # noqa: F401
from tools.capture_participation_batch import capture_batch
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


def _no_fetch(*args):
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

    def fetch(path, destination, revision):
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

    def fetch(path, target, revision):
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
