"""Offline planning, exact original reuse and native stage integration."""

import copy
import hashlib
import json

import pandas as pd
import pytest

from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.data_source import reset_data_source_cache
from tests.test_structured_participation import source  # noqa: F401
from tools.plan_participation_collection import (
    ENDPOINTS,
    MIRROR,
    PIN,
    REMOTE_BODY_BOUND_BYTES,
    _source_url,
    plan_collection,
)
from tools.stage_participation_collection import build_stage

pytestmark = pytest.mark.engine
SCOPES = [("2025-26", "Regular Season", 1), ("2025-26", "Regular Season", 2)]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _git_hash(kind, raw):
    return hashlib.sha1(f"{kind} {len(raw)}\0".encode() + raw).hexdigest()


def _write(path, document):
    path.write_text(json.dumps(document), encoding="utf-8")


@pytest.fixture
def retained_collection(source, tmp_path):  # noqa: F811 - reuse the existing source fixture
    root, traditional, summary, trad, summ = source
    _write(traditional, trad)
    _write(summary, summ)
    stage_structured_game(
        root,
        season="2025-26",
        season_type="Regular Season",
        game_id=22500002,
        traditional=traditional,
        summary=summary,
        summary_version=2,
        revision=PIN,
        retrieved_at="2026-10-31T12:00:00Z",
    )
    (root / "metadata").mkdir()
    (root / "metadata/player_names.csv").write_text(
        "player_id,player_name,season,first_seen\n11,A Player,2025-26,0\n21,B Player,2025-26,1\n"
    )
    (root / "raw/schedule").mkdir()
    capture = tmp_path / "held"
    (capture / "sources").mkdir(parents=True)
    held, indexed = {}, {}
    for year, games in ((2026, range(2, 7)), (2025, [6])):
        season = f"{year - 1}-{year % 100:02d}"
        suff = f"{season}_regular_season.csv"
        frames = {}
        for family in ("games", "team_game_stats", "player_game_stats"):
            data = pd.read_csv(root / f"raw/{family}/2025-26_regular_season.csv")
            data = data.loc[data.game_id.eq(22500002)]
            frames[family] = []
            for number in games:
                game = int(f"002{(year - 1) % 100:02d}{number:05d}")
                day = f"{year - 1}-10-{19 + number}"
                rows = data.assign(
                    game_id=game, game_date=day, season=season, season_type="Regular Season"
                )
                if family == "games":
                    rows = rows.assign(status="Final", team_a_id=1, team_b_id=2)
                    if year == 2026 and number == 6:
                        rows = rows.assign(home_team_id=None, away_team_id=None)
                if family == "team_game_stats":
                    rows["opponent_team_id"] = rows.team_id.map({1: 2, 2: 1})
                frames[family].append(rows)
                if family != "games" or (year == 2026 and number == 2):
                    continue
                original = copy.deepcopy(trad)
                original["boxScoreTraditional"]["gameId"] = f"{game:010d}"
                if year == 2026 and number == 4:
                    original["boxScoreTraditional"]["homeTeam"]["players"][0]["statistics"][
                        "minutes"
                    ] = "29:60"
                paired = {
                    "boxScoreSummary": dict(
                        gameId=f"{game:010d}",
                        gameEt=day,
                        gameStatus=3,
                        homeTeamId=1,
                        awayTeamId=2,
                        homeTeam=dict(teamId=1, teamTricode="AAA", score=10, inactives=[]),
                        awayTeam=dict(teamId=2, teamTricode="BBB", score=8, inactives=[]),
                    )
                }
                for endpoint, body in zip(ENDPOINTS, (original, paired), strict=True):
                    raw = json.dumps(body).encode()
                    key = f"{game:010d}.json"
                    blob = _git_hash("blob", raw)
                    indexed.setdefault((str(year), endpoint), {})[key] = dict(
                        path=key,
                        mode="100644",
                        type="blob",
                        sha=blob,
                        size=len(raw),
                    )
                    if year == 2026 and (
                        number in (3, 4) or number == 5 and endpoint == ENDPOINTS[0]
                    ):
                        name = f"{endpoint}_{key}"
                        (capture / "sources" / name).write_bytes(raw)
                        held[name] = dict(
                            url=_source_url(year, endpoint, f"{game:010d}"),
                            sha256=_sha(raw),
                            git_blob_sha=blob,
                            size_bytes=len(raw),
                            retrieved_at="2026-10-31T13:00:00Z",
                        )
        for family, frames_for_season in frames.items():
            pd.concat(frames_for_season).to_csv(root / f"raw/{family}/{suff}", index=False)
        pd.read_csv(root / f"raw/games/{suff}").to_csv(root / f"raw/schedule/{suff}", index=False)
    _write(capture / "sources.json", dict(repository=MIRROR, revision=PIN, files=held))
    trees, endpoint_receipts = {}, {}
    for (year, endpoint), items in indexed.items():
        tree_raw = b"".join(
            f"100644 {name}\0".encode() + bytes.fromhex(blob["sha"])
            for name, blob in sorted(items.items())
        )
        path = tmp_path / f"{year}-{endpoint}.json"
        tree_sha = _git_hash("tree", tree_raw)
        _write(path, dict(sha=tree_sha, truncated=False, tree=list(items.values())))
        trees[year, endpoint] = path
        record = endpoint_receipts.setdefault(
            endpoint, dict(endpoint_tree_sha="a" * 40, indexed_years=[], samples=[])
        )
        record["indexed_years"].append(year)
        record["samples"].append(
            dict(
                season=f"{int(year) - 1}-{year[-2:]}",
                status="untruncated_index_checked",
                season_tree_sha=tree_sha,
            )
        )
    receipt = tmp_path / "pinned-archive-index.json"
    _write(receipt, dict(repository=MIRROR, revision=PIN, endpoints=endpoint_receipts))
    entries = [
        dict(
            path=file.relative_to(root).as_posix(),
            size_bytes=file.stat().st_size,
            sha256=_sha(file.read_bytes()),
        )
        for file in root.rglob("*")
        if file.is_file()
    ]
    manifest = root / "metadata/generation_manifest.json"
    _write(manifest, dict(generation_id="base-fixture", files=entries))
    return root, _sha(manifest.read_bytes()), capture, trees, receipt, _sha(receipt.read_bytes())


def _plan(collection, output, **options):
    root, manifest, capture, trees, receipt, receipt_hash = collection
    return plan_collection(
        root,
        output,
        manifest_sha256=manifest,
        held_captures=[capture],
        archive_trees=trees,
        archive_index_receipt=receipt,
        archive_index_receipt_sha256=receipt_hash,
        **({"scopes": SCOPES, "max_games": 3} | options),
    )


def test_reuse_is_side_specific_and_emits_native_stage(retained_collection, tmp_path, monkeypatch):
    root = retained_collection[0]
    baseline = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    output = tmp_path / "plan"
    report = _plan(retained_collection, output)
    assert report["metrics"]["game_sides"] == 10
    assert report["metrics"]["unique_games"] == 5
    retained, held, clock, partial, neutral = report["games"]
    assert [side["state"] for side in retained["sides"]] == ["qualified_retained_side"] * 2
    assert held["batch_status"] == "ready_for_staging"
    assert {side["reason"] for side in clock["sides"]} == {"Invalid box-score duration: 29:60"}
    assert partial["batch_status"] == "deferred_by_budget"
    assert neutral["batch_status"] == "canonical_venue_unresolved"
    assert neutral["game_id"] == "0022500006" and neutral["home_team_id"] is None
    assert not neutral.get("originals")
    assert report["metrics"]["actual_remote_calls"] == 0
    assert report["metrics"]["planned_remote_calls"] == 0

    local = tmp_path / "local"
    generations = local / "data/generations"
    generations.mkdir(parents=True)
    (generations / "base-fixture").symlink_to(root, target_is_directory=True)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(local))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "base-fixture")
    reset_data_source_cache()
    batch = output / report["stage_batches"][0]["directory"]
    try:
        result = build_stage(
            batch / "request.json",
            batch / "capture",
            tmp_path / "stage-work",
            tmp_path / "stage-out",
            candidate_sha="c" * 40,
        )
    finally:
        reset_data_source_cache()
    assert [game["game_id"] for game in result["qualified_games"]] == ["0022500003"]
    assert report["stage_batches"][0]["held_originals"] == 2
    assert report["stage_batches"][0]["request_sha256"] == _sha(
        (batch / "request.json").read_bytes()
    )
    assert report["stage_batches"][0]["capture_manifest_sha256"] == _sha(
        (batch / "capture/sources.json").read_bytes()
    )
    assert {p: p.read_bytes() for p in baseline} == baseline


def test_overlapping_scopes_share_call_and_byte_budgets(retained_collection, tmp_path):
    report = _plan(
        retained_collection,
        tmp_path / "combined",
        max_remote_calls=2,
        max_remote_bytes=REMOTE_BODY_BOUND_BYTES * 2,
        scopes=[*SCOPES, ("2024-25", "Regular Season", 1)],
    )
    assert report["metrics"]["planned_remote_calls"] == 1
    assert report["metrics"]["batch_games"] == 2
    stages = {item["directory"]: item for item in report["stage_batches"]}
    pending = stages["2025-26_regular_season-awaiting-originals"]
    assert pending["missing_originals"] == ["boxscoresummaryv3_0022500005.json"]
    assert pending["held_originals"] == 1
    prior, *_ = report["games"]
    assert prior["game_id"] == "0022400006" and prior["batch_status"] == "deferred_by_budget"
    pending_bytes = report["metrics"]["planned_remote_body_byte_ceiling"]
    assert pending_bytes == REMOTE_BODY_BOUND_BYTES
    assert pending["status"] == "acquisition_draft"
    constrained = _plan(
        retained_collection,
        tmp_path / "constrained",
        max_remote_calls=2,
        max_remote_bytes=pending_bytes - 1,
    )
    assert constrained["metrics"]["planned_remote_calls"] == 0
    assert constrained["metrics"]["batch_games"] == 1


def test_failed_route_is_explicit_and_no_duplicate_request_is_planned(
    retained_collection, tmp_path
):
    attempts = tmp_path / "capture-attempts.json"
    _write(
        attempts,
        {
            "attempts": [
                dict(
                    status="failed",
                    http_status=403,
                    error="source denied",
                    url=_source_url(2026, ENDPOINTS[1], "0022500005"),
                )
            ]
        },
    )
    report = _plan(
        retained_collection,
        tmp_path / "failed",
        max_remote_calls=2,
        max_remote_bytes=REMOTE_BODY_BOUND_BYTES * 2,
        failed_attempts=[attempts],
    )
    assert report["metrics"]["planned_remote_calls"] == 0
    partial = report["games"][3]
    assert partial["unresolved_originals"] == ["boxscoresummaryv3_0022500005.json"]
    failed = partial["originals"][partial["unresolved_originals"][0]]
    assert failed["status"] == "known_capture_failure"
    assert failed["previous_failure"] == {"http_status": 403, "error": "source denied"}


@pytest.mark.parametrize("damaged", ["schedule", "capture", "tree", "archive_index"])
def test_tampered_inputs_fail_before_emitting_requests(retained_collection, tmp_path, damaged):
    root, _, capture, trees, receipt, _ = retained_collection
    path, reason = {
        "schedule": (root / "raw/schedule/2025-26_regular_season.csv", "pinned manifest"),
        "capture": (capture / "sources/boxscoresummaryv3_0022500003.json", "capture bytes"),
        "tree": (trees["2026", ENDPOINTS[1]], "tree identity differs"),
        "archive_index": (receipt, "independently pinned evidence"),
    }[damaged]
    if damaged == "tree":
        tree = json.loads(path.read_bytes())
        tree["tree"][0]["sha"] = "a" * 40
        _write(path, tree)
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    target = tmp_path / "damaged"
    with pytest.raises(ValueError, match=reason):
        _plan(retained_collection, target)
    assert not target.exists()


@pytest.mark.parametrize("swap", ["endpoint", "year"])
def test_unmodified_tree_cannot_supply_a_different_endpoint_or_year(
    retained_collection, tmp_path, swap
):
    trees = retained_collection[3]
    trees["2026", ENDPOINTS[0]] = (
        trees["2026", ENDPOINTS[1]] if swap == "endpoint" else trees["2025", ENDPOINTS[0]]
    )
    target = tmp_path / "wrong-slot"
    with pytest.raises(ValueError, match="reviewed endpoint/year ancestry"):
        _plan(retained_collection, target)
    assert not target.exists()


def test_unhashed_tree_sizes_cannot_reduce_bound_or_enter_request(retained_collection, tmp_path):
    trees = retained_collection[3]
    summary = trees["2026", ENDPOINTS[1]]
    report = json.loads(summary.read_bytes())
    for item in report["tree"]:
        item["size"] = 1
    _write(summary, report)
    low = _plan(retained_collection, tmp_path / "too-small", max_remote_calls=2, max_remote_bytes=4)
    assert low["metrics"]["planned_remote_calls"] == 0
    output = tmp_path / "approved-bound"
    sufficient = _plan(
        retained_collection, output, max_remote_calls=2, max_remote_bytes=REMOTE_BODY_BOUND_BYTES
    )
    assert sufficient["metrics"]["planned_remote_body_byte_ceiling"] == REMOTE_BODY_BOUND_BYTES
    pending = sufficient["stage_batches"][1]
    request = json.loads((output / pending["directory"] / "request.json").read_bytes())
    (missing,) = pending["missing_originals"]
    assert "size_bytes" not in request["source_files"][missing]
    assert len(request["source_files"][missing]["git_blob_sha"]) == 40
