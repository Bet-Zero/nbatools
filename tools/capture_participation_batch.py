"""Capture a checksum-pinned participation draft through the existing NBA archive reader.

Only a complete planner batch can be used. Preserve received originals and attempt
receipts, then pass the new capture directory back to the planner for native staging.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter

from requests import RequestException

from tools.cloud_nba_archive import fetch_capture
from tools.plan_participation_collection import (
    DATASET,
    ENDPOINTS,
    MAX_ORIGINAL_BYTES,
    MIRROR,
    PIN,
    REMOTE_BODY_BOUND_BYTES,
    REVIEWED_ARCHIVE_INDEX,
    _digest,
    _git_digest,
    _held_originals,
    _reviewed_archive_trees,
    _source_url,
    _write,
)
from tools.stage_participation_collection import _document, _unique


def _pinned_document(path, digest):
    if path.is_symlink():
        raise ValueError("Pinned batch input must not be a symlink")
    raw = path.read_bytes()
    if _digest(raw) != digest:
        raise ValueError(f"Pinned batch input checksum differs: {path.name}")
    return json.loads(raw, object_pairs_hook=_unique)


def _update(path, payload):
    pending = path.with_suffix(".tmp")
    _write(pending, payload)
    pending.replace(path)


def _draft(plan_path, plan_sha256, batch_name, trees, archive_receipt):
    plan = _pinned_document(plan_path, plan_sha256)
    batches = plan["stage_batches"]
    selected = [batch for batch in batches if batch["directory"] == batch_name]
    if (
        type(plan["schema_version"]) is not int
        or plan["schema_version"] != 1
        or plan["archive_repository"] != MIRROR
        or plan["archive_revision"] != PIN
        or len(selected) != 1
        or selected[0]["status"] != "acquisition_draft"
        or not re.fullmatch(
            r"(?:19|20)\d{2}-\d{2}_(?:regular_season|playoffs)-awaiting-originals", batch_name
        )
    ):
        raise ValueError("Choose an exact reviewed acquisition draft from the pinned plan")
    batch = selected[0]
    directory = plan_path.parent / batch_name
    if directory.resolve() != directory:
        raise ValueError("Indirect acquisition draft path")
    request = _pinned_document(directory / "request.json", batch["request_sha256"])
    season, kind = request["season"], request["season_type"]
    year = str(int(season[:4]) + 1)
    suffix = f"{season}_{kind.lower().replace(' ', '_')}-awaiting-originals"
    if (
        suffix != batch_name
        or season[-2:] != year[-2:]
        or kind not in {"Regular Season", "Playoffs"}
        or type(request["schema_version"]) is not int
        or request["schema_version"] != 1
        or request["dataset"] != DATASET
        or request["requirement_grain"] != "game"
        or (request["repository"], request["revision"]) != (MIRROR, PIN)
        or request["base_generation"] != plan["base_generation"]
        or request["base_manifest_sha256"] != plan["base_manifest_sha256"]
    ):
        raise ValueError("Acquisition draft scope differs from the pinned plan")
    if set(trees) != set(ENDPOINTS):
        raise ValueError("Supply both reviewed endpoint trees for the draft year")
    archive = _reviewed_archive_trees(
        {(year, endpoint): path for endpoint, path in trees.items()},
        archive_receipt,
        plan["archive_index_receipt_sha256"],
    )
    for endpoint, path in trees.items():
        if plan["archive_year_trees"][f"{year}/{endpoint}"] != {
            "archive_tree_sha": archive[year, endpoint][0],
            "document_sha256": _digest(path.read_bytes()),
        }:
            raise ValueError("Archive tree does not match the pinned plan evidence")

    jobs = {}
    game_ids = set()
    slated = {
        g["game_id"]: g
        for g in plan["games"]
        if (g.get("batch_status"), g["season"], g["season_type"])
        == ("awaiting_originals", season, kind)
    }
    prefix = ("002" if kind == "Regular Season" else "004") + season[2:4]
    for game in request["requirements"]:
        game_id, day = game["game_id"], game["game_date"]
        if (
            not re.fullmatch(prefix + r"[0-9]{5}", game_id)
            or game_id in game_ids
            or game_id not in slated
            or date.fromisoformat(day).isoformat() != day
            or int(day[:4]) not in {int(year) - 1, int(year)}
            or (
                slated[game_id]["game_date"],
                slated[game_id]["season"],
                slated[game_id]["season_type"],
            )
            != (day, season, kind)
        ):
            raise ValueError(
                "Acquisition draft contains a duplicate or noncanonical scheduled game"
            )
        game_ids.add(game_id)
        pair = game["proposed_sources"]
        if len(pair) != 2 or {item["endpoint"] for item in pair} != set(ENDPOINTS):
            raise ValueError("Acquire only complete reviewed whole-game archive pairs")
        for source in pair:
            endpoint = source["endpoint"]
            name = f"{endpoint}_{game_id}.json"
            tree_sha, leaves = archive[year, endpoint]
            if f"{game_id}.json" not in leaves:
                raise ValueError("Game is missing from the reviewed archive tree")
            expected = {
                "endpoint": endpoint,
                "game_id": game_id,
                "revision": PIN,
                "url": _source_url(year, endpoint, game_id),
                "source_tree_sha": tree_sha,
                "git_blob_sha": leaves[f"{game_id}.json"]["sha"],
            }
            planned = dict(slated[game_id]["originals"][name])
            status = planned.pop("status")
            fields = expected.keys() | ({"size_bytes"} if status == "retained_body" else set())
            if (
                source != request["source_files"][name]
                or source != planned
                or source.keys() != fields
                or any(source.get(key) != value for key, value in expected.items())
                or status not in {"indexed_body_missing", "retained_body"}
            ):
                raise ValueError(
                    "Archive original differs from the reviewed endpoint, game or Git blob"
                )
            jobs[name] = source
    retained = directory / "capture"
    seed = _pinned_document(retained / "sources.json", batch["capture_manifest_sha256"])["files"]
    missing = sorted(jobs.keys() - seed.keys())
    budget = plan["budget"]
    all_missing = sum(len(entry["missing_originals"]) for entry in batches)
    if (
        not missing
        or missing != batch["missing_originals"]
        or seed.keys() - jobs.keys()
        or set(jobs) != set(request["source_files"])
        or game_ids != slated.keys()
        or len(game_ids) != batch["games"]
        or len(seed) != batch["held_originals"]
        or sum(item["size_bytes"] for item in seed.values()) != batch["held_bytes"]
        or any(
            type(budget[key]) is not int for key in ("games", "remote_calls", "remote_body_bytes")
        )
        or sum(entry["games"] for entry in batches) > budget["games"]
        or all_missing > budget["remote_calls"]
        or all_missing * REMOTE_BODY_BOUND_BYTES > budget["remote_body_bytes"]
        or budget["per_call_body_bound_bytes"] != REMOTE_BODY_BOUND_BYTES
        or any(("size_bytes" in job) != (name in seed) for name, job in jobs.items())
    ):
        raise ValueError(
            "Pinned batch is incomplete or exceeds the reviewed game, call or byte budget"
        )
    return batch, jobs, year, retained, seed


def capture_batch(
    plan_path,
    plan_sha256,
    batch_name,
    output,
    *,
    trees,
    archive_receipt=REVIEWED_ARCHIVE_INDEX,
    held_captures=(),
    prior_attempts=(),
    fetch=fetch_capture,
):
    """Retain exact bytes and outcomes. Never infer source quality from transport."""
    started = perf_counter()
    plan_path, output = plan_path.resolve(), output.resolve()
    if output.exists() or plan_path.parent in (output, *output.parents):
        raise ValueError("Use a new capture directory outside the immutable plan")
    batch, jobs, year, seed_path, seed = _draft(
        plan_path, plan_sha256, batch_name, trees, archive_receipt
    )
    originals, held_manifests = _held_originals([seed_path, *held_captures])
    recorded = {}
    for name, job in jobs.items():
        held = originals.get((year, job["endpoint"], job["game_id"]))
        if held:
            record, path, _ = held
            if record["git_blob_sha"] != job["git_blob_sha"] or (
                name in seed and record["size_bytes"] != job["size_bytes"]
            ):
                raise ValueError(f"Held original differs from pinned draft: {name}")
            recorded[name] = (record, path)
        elif name in seed:
            raise ValueError(f"Pinned held source is unavailable: {name}")
    pending_urls = {job["url"] for name, job in jobs.items() if name not in recorded}
    for path in prior_attempts:
        if any(
            attempt["url"] in pending_urls
            and attempt["status"] in {"failed", "started", "received_exact"}
            for attempt in _document(path)["attempts"]
        ):
            raise ValueError(
                "A pending original was already attempted; check its retained evidence"
            )

    sources = output / "sources"
    sources.mkdir(parents=True)
    rejected = output / "failed-originals"
    rejected.mkdir()
    files, attempts = {}, []
    attempt_path = output / "capture-attempts.json"
    manifest_path = output / "sources.json"
    for name, (record, path) in recorded.items():
        raw = path.read_bytes()
        if _digest(raw) != record["sha256"]:
            raise ValueError(f"Held original changed during capture: {name}")
        (sources / name).write_bytes(raw)
        files[name] = record
    _update(manifest_path, dict(repository=MIRROR, revision=PIN, files=files))
    for name, job in jobs.items():
        if name in files:
            continue
        tick = perf_counter()
        attempt = dict(
            file=name, url=job["url"], status="started", start=datetime.now(UTC).isoformat()
        )
        attempts.append(attempt)
        _update(attempt_path, dict(attempts=attempts))
        target = rejected / name
        received_path = sources / name
        try:
            path = f"nba_stats/json/{job['endpoint']}/{year}/{job['game_id']}.json"
            witness = fetch(path, target, PIN, direct_200=True)
            raw = target.read_bytes()
            attempt.update(size_bytes=len(raw), sha256=_digest(raw))
            if (
                not 0 < len(raw) <= MAX_ORIGINAL_BYTES
                or _git_digest("blob", raw) != job["git_blob_sha"]
                or (witness["url"], witness["bytes"], witness["sha256"])
                != (job["url"], len(raw), attempt["sha256"])
            ):
                raise ValueError("Archive body differs from the pinned Git blob or reader receipt")
            receipt = dict(
                **job,
                size_bytes=len(raw),
                sha256=attempt["sha256"],
                retrieved_at=datetime.now(UTC).isoformat(),
            )
            updated_files = files | {name: receipt}
            target.rename(received_path)
            _update(manifest_path, dict(repository=MIRROR, revision=PIN, files=updated_files))
            files = updated_files
            attempt["status"] = "received_exact"
        except (RequestException, OSError, ValueError, KeyError) as exc:
            if received_path.is_file():
                try:
                    received_path.rename(target)
                except OSError as retention_error:
                    attempt["retention_error"] = str(retention_error)
                    target = received_path
            if target.is_file():
                attempt["retained_original"] = target.relative_to(output).as_posix()
            if target.is_file() and "size_bytes" not in attempt:
                attempt.update(
                    size_bytes=target.stat().st_size, sha256=_digest(target.read_bytes())
                )
            response = exc.response if isinstance(exc, RequestException) else None
            attempt.update(
                status="failed",
                http_status=response.status_code if response is not None else None,
                error_type=type(exc).__name__,
                error=str(exc),
            )
        attempt["duration_s"] = round(perf_counter() - tick, 3)
        _update(attempt_path, dict(attempts=attempts))
        if attempt["status"] == "failed":
            break
    if not attempts:
        _update(attempt_path, dict(attempts=[]))
    summary = dict(
        classification="retained_originals_only",
        source_plan_sha256=plan_sha256,
        request_sha256=batch["request_sha256"],
        sources_manifest_sha256=_digest(manifest_path.read_bytes()),
        held_capture_manifests=held_manifests,
        complete=set(jobs) == set(files),
        requested_originals=len(jobs),
        held_originals=len(recorded),
        body_requests=len(attempts),
        planned_body_byte_ceiling=len(batch["missing_originals"]) * REMOTE_BODY_BOUND_BYTES,
        measured_body_bytes=sum(attempt.get("size_bytes", 0) for attempt in attempts),
        unmeasured_body_attempts=[
            attempt["file"] for attempt in attempts if "size_bytes" not in attempt
        ],
        remaining_originals=sorted(jobs.keys() - files.keys()),
        duration_s=round(perf_counter() - started, 3),
        production_writes=0,
    )
    _update(output / "capture-summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument(
        "--archive-tree", action="append", nargs=2, metavar=("ENDPOINT", "FILE"), required=True
    )
    parser.add_argument("--archive-index-receipt", type=Path, default=REVIEWED_ARCHIVE_INDEX)
    parser.add_argument("--held-capture", type=Path, action="append", default=[])
    parser.add_argument("--prior-attempts", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trees = {endpoint: Path(path) for endpoint, path in args.archive_tree}
    if len(trees) != len(args.archive_tree):
        parser.error("Duplicate archive endpoint tree")
    summary = capture_batch(
        args.plan,
        args.plan_sha256,
        args.batch,
        args.output,
        trees=trees,
        archive_receipt=args.archive_index_receipt,
        held_captures=args.held_capture,
        prior_attempts=args.prior_attempts,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
