"""Bounded on-demand source deltas; no publication, timer or acceptance waiver.

The cache stores originals and transport provenance, not statistical acceptance.
Seed it once from retained collection ZIPs. Each invocation uses a newly checked
schedule and immutable mirror inventory; unchanged blobs and successful direct
request identities are reused. Failed/interrupted transports need diagnosis,
never an implicit retry. The existing collector handles direct-source requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from nbatools.readiness import _missing_due_game_ids
from tools.cloud_nba_archive import fetch_capture
from tools.collect_rollover_readiness_laptop import build_owner_bundle, validate_request
from tools.collection_bundle import unpack

SEASON, KIND = "2026-27", "Regular Season"
MAX_REQUESTS, MAX_BYTES, MAX_SECONDS = 64, 32_000_000, 600
WINDOWS = {
    "q1": (1, 1),
    "q2": (2, 2),
    "q3": (3, 3),
    "q4": (4, 4),
    "h1": (1, 2),
    "h2": (3, 4),
    "ot": (5, 14),
}
PATH = re.compile(
    r"nba_stats/json/(?:scheduleleaguev2/2027\.json|"
    r"(?:playergamelogs|leaguegamefinder|leaguedashplayerstats|leaguedashteamstats|"
    r"leaguestandingsv3)/2027/[a-z_-]+\.json|"
    r"(?:boxscoretraditionalv3|boxscoresummaryv3|playbyplayv3)/2027/00226\d{5}\.json)"
)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(job):
    parameters = dict(job["parameters"])
    if job["endpoint"] in {"leaguedashplayerstats", "leaguedashteamstats"}:
        if parameters.get("ISTRound") is not None:
            raise ValueError("Unexpected tournament-round filter")
        parameters.pop("ISTRound", None)
    return _sha(_json([job["endpoint"], parameters]))


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _write(path, document):
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(_json(document) + b"\n")
    temporary.replace(path)


# The only already-qualified historical retry: retained602 timeout resolved by
# the authenticated517-response recovery. New failures need cloud diagnosis.
_RECOVERY_RESOLUTION = {
    "archive": "7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17",
    "request": "ee6eb91d35ff5f1c2c008df3cd460e516bf412c8a0f0161c366c87098823ad6d",
    "failed_archive": "03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3",
}


def _retain_direct_failure(records, job, attempt, origin, index):
    key = identity(job)
    record = records.setdefault(key, {"job": job, "failures": [], "resolution": None})
    failure = {"origin_sha256": origin, "attempt_index": index, "attempt": attempt}
    if failure not in record["failures"]:
        record["failures"].append(failure)


def _merge_direct_failures(target, incoming):
    for key, record in incoming.items():
        current = target.setdefault(key, {"job": record["job"], "failures": [], "resolution": None})
        for failure in record["failures"]:
            if failure not in current["failures"]:
                current["failures"].append(failure)
        if record.get("resolution") is not None:
            current["resolution"] = record["resolution"]


_RUN = r"runs/[0-9]{8}T[0-9]{12}Z"


def _run_members(payload):
    """Authenticate structural bounds before reading/extracting nested members."""
    import io
    import stat
    from pathlib import PurePosixPath

    if len(payload) > 20_000_000:
        raise ValueError("ZIP exceeds20MB bound")
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        items = z.infolist()
        names = [item.filename for item in items]
        total = sum(item.file_size for item in items)
        if len(items) > 2000 or len(set(names)) != len(names) or total > 100_000_000:
            raise ValueError("ZIP duplicate/expanded/entry bound differs")
        for item in items:
            name = item.filename
            if (
                item.is_dir()
                or stat.S_ISLNK(item.external_attr >> 16)
                or "\\" in name
                or ":" in name
                or any(ord(c) < 32 for c in name)
                or PurePosixPath(name).is_absolute()
                or PurePosixPath(name).as_posix() != name
                or any(part in {"", ".", ".."} for part in name.split("/"))
            ):
                raise ValueError("Unsafe returned ZIP member")
        return {item.filename: z.read(item) for item in items}, total, len(items)


def _preserve_zip(path, raw):
    if path.is_symlink():
        raise ValueError("Preserved ZIP must not be a symlink")
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Preserved immutable ZIP differs")
    else:
        with path.open("xb") as handle:
            handle.write(raw)


def _run_request_from_jobs(jobs):
    request = {
        "status": "collection_requirement_not_publication_approval",
        "season": SEASON,
        "season_type": KIND,
        "base_generation": "returned-run-scope-preflight",
        "base_manifest_sha256": "0" * 64,
        "jobs": jobs,
        "maximum_requests": len(jobs),
        "attempts_per_job": 1,
        "timeout_seconds": 30,
        "response_limit_bytes": 2_000_000,
        "minimum_interval_seconds": 1,
        "maximum_elapsed_seconds": 43_200,
    }
    return validate_request(request)


def _check_loose_batches(members, origin_sha256, verified_successes):
    groups = {name.split("/")[1] for name in members}
    jobs_seen, failures = set(), {}
    for request_sha in groups:
        prefix = "batches/" + request_sha + "/"
        report_raw = members.get(prefix + "acquisition.json")
        if report_raw is None:
            raise ValueError("Loose failed originals lack their acquisition binding")
        report = json.loads(report_raw)
        request = report["request"]
        if (
            validate_request(request) != request_sha
            or len(request["jobs"]) > 500
            or report.get("request_sha256") != request_sha
            or report.get("production_writes") != 0
            or report.get("canonical_period_accepted") is not False
            or len(report["attempts"]) > len(request["jobs"])
        ):
            raise ValueError("Loose failed acquisition binding differs")
        copy = members.get(prefix + "sources/capture-attempt.json")
        if copy is not None and copy != report_raw:
            raise ValueError("Loose acquisition copies differ")
        permitted = {
            prefix + "acquisition.json",
            prefix + "sources/capture-attempt.json",
            prefix + "collection-manifest.json",
        }
        for index, (attempt, job) in enumerate(
            zip(report["attempts"], request["jobs"], strict=False)
        ):
            if attempt["job"] != job:
                raise ValueError("Loose failed attempt order differs")
            if not attempt.get("transport_complete") or identity(job) not in verified_successes:
                # A loose completed original is still attempted, even when its
                # manifest cannot yet authenticate it. Do not recollect it.
                _retain_direct_failure(failures, job, attempt, origin_sha256, index)
            source = prefix + job["source_file"]
            permitted.add(source)
            if source in members and len(members[source]) > 2_000_000:
                raise ValueError("Loose failed body exceeds2MB bound")
        if any(name.startswith(prefix) and name not in permitted for name in members):
            raise ValueError("Unexpected loose failed source")
        jobs_seen.update(identity(job) for job in request["jobs"])
    if len(jobs_seen) > 500:
        raise ValueError("Loose returned run exceeds500 direct requests")
    return jobs_seen, failures


class SourceCache:
    """One writer; immutable bodies with atomic ledger updates and hash reentry."""

    def __init__(self, root):
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError("Cache must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects = self.root / "objects"
        self.objects.mkdir(exist_ok=True)
        self.path = self.root / "ledger.json"
        if self.objects.is_symlink() or self.path.is_symlink():
            raise ValueError("Cache paths must not be symlinks")
        self.data = (
            json.loads(self.path.read_bytes())
            if self.path.exists()
            else {
                "schema_version": 1,
                "direct": {},
                "mirror": {},
                "imports": {},
                "attempts": {},
                "classification": "retained_transport_not_statistical_acceptance",
                "production_writes": 0,
            }
        )
        if self.data.get("schema_version") != 1 or self.data.get("production_writes") != 0:
            raise ValueError("Invalid source ledger")
        for section in ("direct", "mirror"):
            for record in self.data[section].values():
                self.read(record)
        normalized = {}
        for key, record in self.data["direct"].items():
            canonical = identity(record["job"])
            literal = _sha(_json([record["job"]["endpoint"], record["job"]["parameters"]]))
            if key not in {canonical, literal}:
                raise ValueError("Direct source identity differs")
            if canonical in normalized:
                raise ValueError("Equivalent direct identities have conflicting retained originals")
            normalized[canonical] = record
        self.data["direct"] = normalized
        normalized_attempts = {}
        for key, record in self.data.get("direct_attempts", {}).items():
            canonical = identity(record["job"])
            literal = _sha(_json([record["job"]["endpoint"], record["job"]["parameters"]]))
            if key not in {canonical, literal}:
                raise ValueError("Failed direct identity differs")
            _merge_direct_failures(normalized_attempts, {canonical: record})
        self.data["direct_attempts"] = normalized_attempts
        for key, record in self.data["mirror"].items():
            if (
                key != record["path"] + ":" + record["blob"]
                or git_blob(self.read(record)) != record["blob"]
            ):
                raise ValueError("Archive blob identity differs")

        for record in self.data.get("runs", {}).values():
            self._check_run_original(record)

    def unresolved_direct_attempts(self):
        unresolved = {}
        for key, record in self.data.get("direct_attempts", {}).items():
            resolution = record.get("resolution")
            source = self.data["direct"].get(key)
            if not (
                resolution
                and source
                and resolution.get("archive_sha256") == _RECOVERY_RESOLUTION["archive"]
                and resolution.get("response_sha256") == source["sha256"]
            ):
                unresolved[key] = record
        return unresolved

    def require_unblocked(self, jobs):
        blocked = self.unresolved_direct_attempts()
        if any(identity(job) in blocked for job in jobs):
            raise ValueError("Failed/interrupted direct request requires explicit cloud diagnosis")

    def read(self, record):
        digest = record["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid source digest")
        path = self.objects / digest
        if path.is_symlink():
            raise ValueError("Source must not be a symlink")
        raw = path.read_bytes()
        if len(raw) != record["bytes"] or _sha(raw) != digest:
            raise ValueError("Retained original changed; no acquisition permitted")
        return raw

    def save(self):
        _write(self.path, self.data)

    def _body(self, raw):
        digest = _sha(raw)
        path = self.objects / digest
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(raw)
        record = {"sha256": digest, "bytes": len(raw)}
        self.read(record)
        return record

    def import_collection(self, archive, expected_sha256):
        """Authenticate the original container and every successful request first."""
        archive = Path(archive)
        if archive.stat().st_size > 20_000_000 or _sha(archive.read_bytes()) != expected_sha256:
            raise ValueError("Collection original differs")
        with zipfile.ZipFile(archive) as z:
            request = json.loads(z.read("collection-manifest.json"))["request"]
        legacy = "jobs" not in request
        if legacy:
            from tools.collect_rollover_q1_laptop import REQUEST

            if request != REQUEST:
                raise ValueError("Unknown legacy collection request")
            request_sha = _sha(_json(request))
            jobs = [
                {
                    "endpoint": endpoint,
                    "parameters": request["parameters"],
                    "source_file": f"sources/{endpoint}_0022600001_q1.json",
                }
                for endpoint in request["endpoints"]
            ]
        else:
            request_sha = validate_request(request)
            jobs = request["jobs"]
        incoming, failures = [], {}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "verified"
            unpack(archive, request, output)
            report_raw = (output / "acquisition.json").read_bytes()
            report = json.loads(report_raw)
            if (
                (output / "sources/capture-attempt.json").read_bytes() != report_raw
                or report["request"] != request
                or report.get("request_sha256", request_sha if legacy else None) != request_sha
                or report["production_writes"] != 0
                or len(report["attempts"]) > len(jobs)
            ):
                raise ValueError("Collection attempt bindings differ")
            for index, (attempt, job) in enumerate(zip(report["attempts"], jobs, strict=False)):
                if not legacy and attempt["job"] != job:
                    raise ValueError("Collection attempt order differs")
                if not attempt.get(
                    "transport_complete", legacy and attempt.get("response_complete")
                ):
                    _retain_direct_failure(failures, job, attempt, expected_sha256, index)
                    continue
                raw = (output / job["source_file"]).read_bytes()
                if (
                    attempt.get("endpoint") != job["endpoint"]
                    or attempt.get("parameters") != job["parameters"]
                    or attempt.get("url") != "https://stats.nba.com/stats/" + job["endpoint"]
                    or attempt.get("source_file") != job["source_file"]
                    or attempt.get("http_status") != 200
                    or attempt.get("attempts") != 1
                    or attempt.get("response_complete") is not True
                    or attempt.get("error_type")
                    or len(raw) > 2_000_000
                    or len(raw) != attempt["response_bytes"]
                    or _sha(raw) != attempt["response_sha256"]
                    or not isinstance(json.loads(raw), dict)
                ):
                    raise ValueError("Completed source lacks exact successful transport evidence")
                previous = self.data["direct"].get(identity(job))
                if previous and previous["sha256"] != _sha(raw):
                    raise ValueError(
                        "Same direct identity has conflicting originals; reconcile explicitly"
                    )
                incoming.append((job, raw, attempt["finished_at"]))
        _merge_direct_failures(self.data["direct_attempts"], failures)
        for job, raw, captured_at in incoming:
            self.data["direct"][identity(job)] = {
                **self._body(raw),
                "job": job,
                "captured_at": captured_at,
                "original_zip_sha256": expected_sha256,
            }
        if (
            expected_sha256 == _RECOVERY_RESOLUTION["archive"]
            and request_sha == _RECOVERY_RESOLUTION["request"]
        ):
            for job, raw, _ in incoming:
                record = self.data["direct_attempts"].get(identity(job))
                if record and any(
                    f["origin_sha256"] == _RECOVERY_RESOLUTION["failed_archive"]
                    for f in record["failures"]
                ):
                    record["resolution"] = {
                        "archive_sha256": expected_sha256,
                        "response_sha256": _sha(raw),
                        "basis": "previously authenticated reviewed recovery",
                    }
        result = {"successful_sources": len(incoming), "original_path": str(archive.resolve())}
        self.data["imports"][expected_sha256] = result
        self.save()
        return result

    def import_run(self, archive, expected_sha256, seed_sha256):
        """Consume one returned runtime ZIP; preserve bytes, never qualify statistics.

        Every nested collection is authenticated in an isolated scratch cache.
        Only after all bounds, bindings and originals pass does one ledger update
        admit their successful transports. Failed/partial evidence stays explicit.
        """
        for digest in (expected_sha256, seed_sha256):
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("Explicit outer ZIP and reviewed seed SHA256 required")
        archive = Path(archive)
        if archive.is_symlink() or archive.stat().st_size > 20_000_000:
            raise ValueError("Returned ZIP exceeds bounded regular-file protocol")
        payload = archive.read_bytes()
        if _sha(payload) != expected_sha256:
            raise ValueError("Returned ZIP differs from expected SHA256")
        previous = self.data.get("runs", {}).get(expected_sha256)
        if previous:
            if previous["seed_sha256"] != seed_sha256:
                raise ValueError("Returned ZIP belongs to another reviewed seed")
            self._check_run_original(previous)
            if previous.get("direct_attempt_tracking") == 2:
                return previous
        members, expanded, entries = _run_members(payload)
        receipts = [name for name in members if re.fullmatch(_RUN + r"/receipt\.json", name)]
        if len(receipts) != 1 or "state.json" not in members:
            raise ValueError("Returned ZIP needs exactly one run receipt and persistent state")
        receipt = json.loads(members[receipts[0]])
        state = json.loads(members["state.json"])
        failed = receipt.get("state") in {"failed_preserve_output_do_not_retry", "capture_stopped"}
        if (
            receipt.get("classification") != "unvalidated_acquisition_only"
            or receipt.get("seed_sha256") != seed_sha256
            or state.get("seed_sha256") != seed_sha256
            or receipt.get("production_writes") != 0
            or state.get("production_writes") != 0
            or receipt.get("statistical_acceptance") is not False
            or receipt.get("lag_hours") != 24
            or receipt.get("state")
            not in {
                "transport_complete",
                "no_missing_direct_requests",
                "failed_preserve_output_do_not_retry",
                "capture_stopped",
            }
        ):
            raise ValueError("Returned run/seed/acquisition-only bindings differ")
        if (
            receipt["state"] == "failed_preserve_output_do_not_retry"
            and state.get("blocked") is not True
        ):
            raise ValueError("Failed returned run must preserve its no-retry state")
        if (
            type(receipt.get("archive_requests")) is not int
            or not 0 <= receipt["archive_requests"] <= 32
            or type(receipt.get("archive_bytes")) is not int
            or not 0 <= receipt["archive_bytes"] <= 32_000_000
        ):
            raise ValueError("Returned archive transport bounds differ")
        blocked_files = set(state.get("blocked_files", []))
        planned = receipt.get("jobs", [])
        if len(planned) > 500:
            raise ValueError("Returned run exceeds500 direct requests")
        if planned:
            _run_request_from_jobs(planned)
        nested, loose, originals, evidence = [], {}, [], []
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            scratch = SourceCache(temporary / "cache")
            all_jobs, request_ids = [], set()
            for name, raw in members.items():
                evidence.append({"member": name, "sha256": _sha(raw), "bytes": len(raw)})
                match = re.fullmatch(r"batches/([a-f0-9]{64})/collection\.zip", name)
                if match:
                    inner, inner_size, inner_count = _run_members(raw)
                    expanded += inner_size
                    entries += inner_count
                    if expanded > 100_000_000 or entries > 2000:
                        raise ValueError("Nested return exceeds expanded/entry bounds")
                    manifest = json.loads(inner["collection-manifest.json"])
                    request = manifest["request"]
                    request_sha = validate_request(request)
                    if request_sha != match[1] or len(request["jobs"]) > 500:
                        raise ValueError("Nested request path/bounds differ")
                    report = json.loads(inner["acquisition.json"])
                    if report.get("canonical_period_accepted") is not False:
                        raise ValueError("Nested transport cannot claim statistical acceptance")
                    if receipt["state"] == "transport_complete" and (
                        report.get("transport_finished") is not True
                        or len(report["attempts"]) != len(request["jobs"])
                        or report.get("unattempted_jobs") != []
                        or not all(a.get("transport_complete") is True for a in report["attempts"])
                    ):
                        raise ValueError("Complete run contains an incomplete nested capture")
                    if request_sha in request_ids:
                        raise ValueError("Repeated nested request")
                    request_ids.add(request_sha)
                    all_jobs.extend(request["jobs"])
                    nested_path = temporary / (_sha(raw) + ".zip")
                    nested_path.write_bytes(raw)
                    result = scratch.import_collection(nested_path, _sha(raw))
                    nested.append(
                        {
                            "member": name,
                            "sha256": _sha(raw),
                            "request_sha256": request_sha,
                            "bytes": len(raw),
                            "successful_sources": result["successful_sources"],
                        }
                    )
                elif re.fullmatch(r"archive/[a-f0-9]{40}\.json", name):
                    if len(raw) > 8_000_000:
                        raise ValueError("Archive original exceeds8MB bound")
                    blob = name.removeprefix("archive/").removesuffix(".json")
                    matches = git_blob(raw) == blob
                    if not matches and (not failed or name not in blocked_files):
                        raise ValueError("Archive original differs from its Git blob")
                    originals.append(
                        {
                            "member": name,
                            "blob": blob,
                            "bytes": len(raw),
                            "sha256": _sha(raw),
                            "git_blob_matches": matches,
                            "classification": "unqualified_archive_original"
                            if matches
                            else "quarantined_partial_original",
                        }
                    )
                elif re.fullmatch(_RUN + r"/metadata/[0-9]{2}\.json", name):
                    if len(raw) > 2_000_000:
                        raise ValueError("Archive metadata exceeds2MB bound")
                    if not failed:
                        json.loads(raw)
                elif re.fullmatch(
                    r"batches/[a-f0-9]{64}/(?:acquisition|collection-manifest)\.json", name
                ) or re.fullmatch(r"batches/[a-f0-9]{64}/sources/[a-zA-Z0-9_-]+\.json", name):
                    if not failed:
                        raise ValueError("Loose batch originals require a failed run")
                    loose[name] = raw
                elif name not in {receipts[0], "state.json"}:
                    raise ValueError("Unexpected returned run member")
            if len(all_jobs) > 500 or len({identity(job) for job in all_jobs}) != len(all_jobs):
                raise ValueError("Nested run repeats requests or exceeds500 direct requests")
            if nested and all_jobs != planned:
                raise ValueError("Nested requests differ from run receipt plan")
            if not nested and planned and not failed:
                raise ValueError("Planned requests have no nested original capture")
            loose_jobs, loose_failures = _check_loose_batches(
                loose, expected_sha256, set(scratch.data["direct"]) | set(self.data["direct"])
            )
            _merge_direct_failures(scratch.data["direct_attempts"], loose_failures)
            if len(loose_jobs | {identity(job) for job in all_jobs}) > 500:
                raise ValueError("Returned run exceeds500 distinct direct requests")
            if receipt["state"] == "no_missing_direct_requests" and (nested or planned):
                raise ValueError("Empty delta cannot contain direct captures")
            for key, record in scratch.data["direct"].items():
                previous_source = self.data["direct"].get(key)
                if previous_source and previous_source["sha256"] != record["sha256"]:
                    raise ValueError(
                        "Returned source conflicts with an existing successful original"
                    )
            # All archive/nested/loose metadata has passed. Objects written below
            # remain unreferenced if an I/O failure prevents the final atomic ledger.
            import_root = self.root / "run-imports"
            if import_root.is_symlink():
                raise ValueError("Run import path must not be a symlink")
            import_root.mkdir(exist_ok=True)
            _preserve_zip(import_root / (expected_sha256 + ".zip"), payload)
            next_data = json.loads(json.dumps(self.data))
            _merge_direct_failures(next_data["direct_attempts"], scratch.data["direct_attempts"])
            for item in nested:
                path = import_root / (item["sha256"] + ".collection.zip")
                _preserve_zip(path, members[item["member"]])
                item["original_path"] = str(path.resolve())
                next_data["imports"][item["sha256"]] = {
                    "successful_sources": item["successful_sources"],
                    "original_path": str(path.resolve()),
                    "outer_zip_sha256": expected_sha256,
                }
            for key, record in scratch.data["direct"].items():
                self._body(scratch.read(record))
                next_data["direct"][key] = record
            for item in originals:
                self._body(members[item["member"]])
            result = {
                "classification": "authenticated_run_transport_not_statistical_acceptance",
                "outer_sha256": expected_sha256,
                "bytes": len(payload),
                "original_path": str((import_root / (expected_sha256 + ".zip")).resolve()),
                "seed_sha256": seed_sha256,
                "receipt": receipt,
                "nested_collections": nested,
                "archive_originals": originals,
                "evidence_files": evidence,
                "loose_failed_files": sorted(loose),
                "successful_sources": len(scratch.data["direct"]),
                "failed_or_interrupted": failed,
                "direct_attempt_tracking": 2,
                "blocked_direct_attempts": sorted(scratch.unresolved_direct_attempts()),
                "production_writes": 0,
            }
            next_data.setdefault("runs", {})[expected_sha256] = result
            previous_data = self.data
            self.data = next_data
            try:
                self.save()
            except BaseException:
                self.data = previous_data
                raise
        return result

    def _check_run_original(self, record):
        path = self.root / "run-imports" / (record["outer_sha256"] + ".zip")
        if (
            (self.root / "run-imports").is_symlink()
            or path.is_symlink()
            or path.stat().st_size != record["bytes"]
            or _sha(path.read_bytes()) != record["outer_sha256"]
        ):
            raise ValueError("Preserved returned run ZIP changed")
        for item in record["archive_originals"]:
            self.read(item)

    def import_mirror_manifest(self, manifest, sources):
        """Reuse a retained acquisition's exact files before planning archive deltas."""
        document = json.loads(Path(manifest).read_bytes())
        root = Path(sources).resolve()
        if (
            not re.fullmatch(r"[0-9a-f]{40}", document["revision"])
            or len(document["files"]) > 2000
            or sum(item["bytes"] for item in document["files"]) > 100_000_000
        ):
            raise ValueError("Retained source import exceeds bounded protocol")
        incoming = []
        for item in document["files"]:
            original = root / item["file"]
            path = original.resolve()
            if (
                not path.is_relative_to(root)
                or original.is_symlink()
                or not 0 < path.stat().st_size <= 8_000_000
            ):
                raise ValueError("Unsafe retained source path")
            raw = path.read_bytes()
            if (
                len(raw) != item["bytes"]
                or _sha(raw) != item["sha256"]
                or git_blob(raw) != item["sha"]
                or not PATH.fullmatch(item["path"])
            ):
                raise ValueError("Retained mirror source differs")
            incoming.append((item, raw))
        if len(incoming) > 2000 or sum(len(raw) for _, raw in incoming) > 100_000_000:
            raise ValueError("Retained source import exceeds bounded protocol")
        for item, raw in incoming:
            self.import_mirror(
                raw,
                path=item["path"],
                blob=item["sha"],
                revision=document["revision"],
                provenance=item,
            )
        return {"reused_originals": len(incoming), "production_writes": 0}

    def import_mirror(self, raw, *, path, blob, revision, provenance):
        if (
            not PATH.fullmatch(path)
            or not re.fullmatch(r"[0-9a-f]{40}", revision)
            or git_blob(raw) != blob
        ):
            raise ValueError("Pinned current-season archive identity differs")
        self.data["mirror"][path + ":" + blob] = {
            **self._body(raw),
            "path": path,
            "blob": blob,
            "revision": revision,
            "provenance": provenance,
        }
        self.save()


def due_population(schedule, games, checked_at):
    if checked_at.tzinfo is None:
        raise ValueError("Freshness check must have an explicit timezone")
    due = _missing_due_game_ids(schedule, games.iloc[:0], checked_at, SEASON, KIND)
    missing = _missing_due_game_ids(schedule, games, checked_at, SEASON, KIND)
    if due is None or missing is None:
        raise ValueError("Exact current due population is unknown; preserve readiness failure")
    return {
        "checked_at": checked_at.isoformat(),
        "lag_hours": 24,
        "due_game_ids": list(due),
        "missing_due_game_ids": list(missing),
        "final_acceptance_requires_new_freshness_check": True,
    }


def period_count(document, game_id):
    """Require both team arrays and root metadata; ambiguity never implies no OT."""
    box = document["boxScoreSummary"]
    if box["gameId"] != game_id:
        raise ValueError("Summary game identity differs")
    sides = [box[side]["periods"] for side in ("homeTeam", "awayTeam")]
    numbers = [[row["period"] for row in side] for side in sides]
    count = len(numbers[0])
    if (
        not 4 <= count <= 14
        or any(rows != list(range(1, count + 1)) for rows in numbers)
        or box["period"] != count
    ):
        raise ValueError("Summary period metadata ambiguous; qualified evidence required")
    return count


def direct_delta(cache, due_ids, *, period_counts=None):
    """Six required windows, OT only from qualified evidence; cache suppresses repeats."""
    jobs, unresolved = [], []
    period_counts = period_counts or {}
    for gid in sorted(set(due_ids)):
        if not re.fullmatch(r"00226\d{5}", gid):
            raise ValueError("Invalid current-season due game")
        count = period_counts.get(gid)
        if count is None:
            unresolved.append(gid)
        elif type(count) is not int or not 4 <= count <= 14:
            raise ValueError("Invalid qualified period count")
        windows = [*list(WINDOWS)[:6], *(["ot"] if count and count > 4 else [])]
        for label in windows:
            start, end = WINDOWS[label]
            for endpoint in ("boxscoretraditionalv3", "boxscoreadvancedv3"):
                job = {
                    "endpoint": endpoint,
                    "parameters": {
                        "GameID": gid,
                        "StartPeriod": start,
                        "EndPeriod": end,
                        "RangeType": 1,
                        "StartRange": 0,
                        "EndRange": 28800,
                    },
                    "source_file": f"sources/{endpoint}_{gid}_{label}.json",
                }
                if identity(job) not in cache.data["direct"]:
                    jobs.append(job)
    cache.require_unblocked(jobs)
    return {
        "jobs": jobs,
        "period_population_unresolved": unresolved,
        "statistical_acceptance": False,
        "production_writes": 0,
    }


def mirror_delta(cache, inventory, due_ids):
    revision = inventory["revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Full immutable mirror revision required")
    jobs = []
    for entry in inventory["entries"].values():
        for item in entry if isinstance(entry, list) else [entry]:
            path = item["path"]
            if not PATH.fullmatch(path):
                continue
            game = re.search(r"/(00226\d{5})\.json$", path)
            if game and game[1] not in due_ids:
                continue
            blob, size = item["sha"], item["size"]
            if not re.fullmatch(r"[0-9a-f]{40}", blob) or not 0 < size <= 8_000_000:
                raise ValueError("Invalid bounded archive inventory")
            if path + ":" + blob not in cache.data["mirror"]:
                jobs.append({"path": path, "blob": blob, "bytes": size, "revision": revision})
    return {
        "revision": revision,
        "jobs": sorted(jobs, key=lambda row: row["path"]),
        "classification": "transport_staging_only",
        "production_writes": 0,
    }


def stage_mirror(
    cache, plan, *, max_requests=MAX_REQUESTS, max_bytes=MAX_BYTES, max_seconds=MAX_SECONDS
):
    """No failed-request retry; reentry reuses every completed immutable blob."""
    if not (
        1 <= max_requests <= MAX_REQUESTS
        and 1 <= max_bytes <= MAX_BYTES
        and 31 <= max_seconds <= MAX_SECONDS
    ):
        raise ValueError("Archive run bounds exceed reviewed protocol")
    jobs = plan["jobs"]
    if (
        len(jobs) > max_requests
        or sum(j["bytes"] for j in jobs) > max_bytes
        or len({j["path"] for j in jobs}) != len(jobs)
    ):
        raise ValueError("Archive delta exceeds finite run bounds")
    for job in jobs:
        if (
            not PATH.fullmatch(job["path"])
            or not re.fullmatch(r"[0-9a-f]{40}", job["blob"])
            or job["revision"] != plan["revision"]
            or not re.fullmatch(r"[0-9a-f]{40}", job["revision"])
            or not 0 < job["bytes"] <= 8_000_000
        ):
            raise ValueError("Invalid pinned archive job")
    started, completed = time.monotonic(), 0
    for job in jobs:
        key = job["path"] + ":" + job["blob"]
        if key in cache.data["mirror"]:
            continue
        if key in cache.data["attempts"]:
            raise ValueError("Prior failed/interrupted archive request requires diagnosis")
        if time.monotonic() - started + 31 > max_seconds:
            return {"state": "elapsed_limit", "completed": completed, "production_writes": 0}
        attempt = {**job, "state": "started", "started_at": datetime.now(UTC).isoformat()}
        cache.data["attempts"][key] = attempt
        cache.save()
        destination = cache.root / (_sha(key.encode()) + ".original")
        try:
            source = fetch_capture(job["path"], destination, job["revision"])
            raw = destination.read_bytes()
            if len(raw) != job["bytes"]:
                raise ValueError("Archive body differs from pinned inventory size")
            cache.import_mirror(
                raw, path=job["path"], blob=job["blob"], revision=job["revision"], provenance=source
            )
            attempt["state"] = "completed"
            completed += 1
        except BaseException as exc:
            attempt.update(state="failed", error_type=type(exc).__name__)
            cache.save()
            raise
        cache.save()
    return {
        "state": "transport_staged_not_qualified",
        "completed": completed,
        "production_writes": 0,
    }


def readiness_dependencies(cutoff):
    """Explicit finite November4 source-basis probes; never retry their originals."""
    from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueDashTeamStats

    from tools.collect_rollover_readiness_laptop import DIAGNOSTIC_GAME_IDS

    diagnostics = []
    for gid, label in [
        (gid, label) for gid in sorted(DIAGNOSTIC_GAME_IDS) for label in list(WINDOWS)[:6]
    ]:
        first, last = WINDOWS[label]
        for endpoint in ("boxscoretraditionalv3", "boxscoreadvancedv3"):
            diagnostics.append(
                {
                    "endpoint": endpoint,
                    "parameters": {
                        "GameID": gid,
                        "StartPeriod": first,
                        "EndPeriod": last,
                        "RangeType": 2,
                        "StartRange": (first - 1) * 7200,
                        "EndRange": last * 7200,
                    },
                    "source_file": f"sources/{endpoint}_{gid}_{label}_range2.json",
                }
            )
    diagnostics.append(
        {
            "endpoint": "boxscoretraditionalv3",
            "parameters": {
                "GameID": "0022600172",
                **dict.fromkeys(
                    ["StartPeriod", "EndPeriod", "RangeType", "StartRange", "EndRange"], "0"
                ),
            },
            "source_file": "sources/boxscoretraditionalv3_0022600172_full.json",
        }
    )
    snapshots = []
    for cls in (LeagueDashPlayerStats, LeagueDashTeamStats):
        obj = cls(
            season=SEASON,
            season_type_all_star=KIND,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            date_from_nullable="",
            date_to_nullable=cutoff,
            get_request=False,
        )
        snapshots.append(
            {
                "endpoint": obj.endpoint,
                "parameters": obj.parameters,
                "source_file": f"sources/{obj.endpoint}_advanced_snapshot.json",
            }
        )
    return diagnostics, snapshots


def build_reusable_bundle(
    cache,
    destination,
    *,
    schedule_raw,
    schedule_blob,
    summaries,
    base_generation,
    base_manifest_sha256,
    dependencies=(),
    snapshot_templates=(),
):
    """One reusable no-install launcher; only finite approved source templates.

    summaries maps each already qualified game to its pinned blob and period count;
    None explicitly preserves a metadata ambiguity. Seed successes retain original
    ZIP hashes; full original bytes stay in GitHub staging and the cloud cache.
    """
    import base64
    import zlib

    from tools.build_readiness_recovery import MAC_LAUNCHER, WINDOWS_LAUNCHER

    if (
        git_blob(schedule_raw) != schedule_blob
        or not re.fullmatch(r"[0-9a-f]{64}", base_manifest_sha256)
        or not base_generation
    ):
        raise ValueError("Reusable package source/base binding differs")
    for gid, item in summaries.items():
        if (
            not re.fullmatch(r"00226\d{5}", gid)
            or not re.fullmatch(r"[0-9a-f]{40}", item["blob"])
            or (
                item["periods"] is not None
                and (type(item["periods"]) is not int or not 4 <= item["periods"] <= 14)
            )
        ):
            raise ValueError("Invalid qualified Summary seed")
    seed = {
        "schema_version": 1,
        "season": SEASON,
        "base_generation": base_generation,
        "base_manifest_sha256": base_manifest_sha256,
        "successes": {
            key: {
                "job": value["job"],
                "sha256": value["sha256"],
                "original_zip_sha256": value["original_zip_sha256"],
            }
            for key, value in cache.data["direct"].items()
        },
        "schedule": {"blob": schedule_blob, "body_base64": base64.b64encode(schedule_raw).decode()},
        "summaries": summaries,
        "dependencies": list(dependencies),
        "snapshot_templates": list(snapshot_templates),
        "production_writes": 0,
    }
    blocked = cache.unresolved_direct_attempts()
    if blocked:
        seed["blocked_attempts"] = blocked
    extra = [*dependencies, *snapshot_templates]
    if extra:
        validate_request(
            {
                "status": "collection_requirement_not_publication_approval",
                "season": SEASON,
                "season_type": KIND,
                "base_generation": base_generation,
                "base_manifest_sha256": base_manifest_sha256,
                "jobs": extra,
                "maximum_requests": len(extra),
                "attempts_per_job": 1,
                "timeout_seconds": 30,
                "response_limit_bytes": 2_000_000,
                "minimum_interval_seconds": 1,
                "maximum_elapsed_seconds": 43_200,
            }
        )
    collector = Path(__file__).with_name("collect_rollover_readiness_laptop.py").read_text()
    collector = collector.rsplit('\nif __name__ == "__main__":', 1)[0]
    runtime = Path(__file__).with_name("readiness_refresh_laptop.py").read_text()
    runtime = runtime.replace("from __future__ import annotations\n", "", 1)
    encoded = base64.b64encode(zlib.compress(_json(seed))).decode()
    runtime = runtime.replace(
        "SEED = None", f"SEED = json.loads(zlib.decompress(base64.b64decode({encoded!r})))", 1
    )
    source = collector + "\n\n" + runtime
    compile(source, "run_capture.py", "exec")
    instructions = (
        "Open Run Capture.command (Mac) or Run Capture.bat (Windows). It uses the existing "
        "Python/nba_api and installs nothing. Keep this entire folder between invocations.\n"
        "Each launch discovers the latest immutable public archive schedule/Summary catalog, "
        "keeps the24-hour due rule, reuses every previous success, and captures a finite delta "
        "of at most40games/500direct requests. One attempt per new request;30s/2MB limits; "
        "no timer and no publication. Known source disagreements stay quarantined.\n"
        "Return readiness-refresh/current-run.zip, including after a failure. Preserve the "
        "folder for cloud diagnosis; failed/interrupted requests are never retried automatically.\n"
        "This is source acquisition only. No dataset or freshness acceptance is granted.\n"
    )
    with Path(destination).open("xb") as handle:
        with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("run_capture.py", source)
            command = zipfile.ZipInfo("Run Capture.command")
            command.create_system = 3
            command.external_attr = 0o100755 << 16
            mac = MAC_LAUNCHER.replace(
                "readiness-capture/collection.zip", "readiness-refresh/current-run.zip"
            )
            windows = WINDOWS_LAUNCHER.replace(
                "readiness-capture\\collection.zip", "readiness-refresh\\current-run.zip"
            )
            z.writestr(command, mac)
            z.writestr("Run Capture.bat", windows.replace("\n", "\r\n"))
            z.writestr("READ ME.txt", instructions)
    return {
        "seed_sha256": _sha(_json(seed)),
        "seed_successes": len(seed["successes"]),
        "owner_bundle_sha256": _sha(Path(destination).read_bytes()),
        "runtime_sha256": _sha(source.encode()),
        "production_writes": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed")
    seed.add_argument("archive", type=Path)
    seed.add_argument("--sha256", required=True)
    returned = sub.add_parser("import-run")
    returned.add_argument("archive", type=Path)
    returned.add_argument("--sha256", required=True)
    returned.add_argument("--seed-sha256", required=True)
    retained = sub.add_parser("seed-mirror")
    retained.add_argument("manifest", type=Path)
    retained.add_argument("--sources", required=True, type=Path)
    reusable = sub.add_parser("reusable-package")
    reusable.add_argument("--schedule-json", required=True, type=Path)
    reusable.add_argument("--summary-seed", required=True, type=Path)
    reusable.add_argument("--base-generation", required=True)
    reusable.add_argument("--base-manifest-sha256", required=True)
    reusable.add_argument("--output", required=True, type=Path)
    planning = sub.add_parser("plan")
    planning.add_argument("--schedule", required=True, type=Path)
    planning.add_argument("--games", required=True, type=Path)
    planning.add_argument("--inventory", required=True, type=Path)
    planning.add_argument("--period-counts", type=Path)
    planning.add_argument("--checked-at")
    planning.add_argument("--output", required=True, type=Path)
    staging = sub.add_parser("stage")
    staging.add_argument("plan", type=Path)
    package = sub.add_parser("package")
    package.add_argument("plan", type=Path)
    package.add_argument("--base-generation", required=True)
    package.add_argument("--base-manifest-sha256", required=True)
    package.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    cache = SourceCache(args.cache)
    if args.command == "seed":
        result = cache.import_collection(args.archive, args.sha256)
    elif args.command == "import-run":
        result = cache.import_run(args.archive, args.sha256, args.seed_sha256)
    elif args.command == "seed-mirror":
        result = cache.import_mirror_manifest(args.manifest, args.sources)
    elif args.command == "reusable-package":
        schedule_raw = args.schedule_json.read_bytes()
        result = build_reusable_bundle(
            cache,
            args.output,
            schedule_raw=schedule_raw,
            schedule_blob=git_blob(schedule_raw),
            summaries=json.loads(args.summary_seed.read_bytes()),
            base_generation=args.base_generation,
            base_manifest_sha256=args.base_manifest_sha256,
        )
    elif args.command == "plan":
        checked = datetime.fromisoformat(args.checked_at) if args.checked_at else datetime.now(UTC)
        population = due_population(pd.read_csv(args.schedule), pd.read_csv(args.games), checked)
        counts = json.loads(args.period_counts.read_bytes()) if args.period_counts else {}
        result = {
            "population": population,
            "mirror": mirror_delta(
                cache, json.loads(args.inventory.read_bytes()), population["due_game_ids"]
            ),
            "direct": direct_delta(cache, population["due_game_ids"], period_counts=counts),
        }
        _write(args.output, result)
    elif args.command == "stage":
        result = stage_mirror(cache, json.loads(args.plan.read_bytes())["mirror"])
    else:
        delta = json.loads(args.plan.read_bytes())["direct"]
        jobs = [job for job in delta["jobs"] if identity(job) not in cache.data["direct"]]
        if not jobs:
            raise ValueError("No incomplete direct requests; no package required")
        cache.require_unblocked(jobs)
        request = {
            "status": "collection_requirement_not_publication_approval",
            "season": SEASON,
            "season_type": KIND,
            "base_generation": args.base_generation,
            "base_manifest_sha256": args.base_manifest_sha256,
            "jobs": jobs,
            "maximum_requests": len(jobs),
            "attempts_per_job": 1,
            "timeout_seconds": 30,
            "response_limit_bytes": 2_000_000,
            "minimum_interval_seconds": 1,
            "maximum_elapsed_seconds": min(43_200, len(jobs) * 32 + 31),
        }
        result = build_owner_bundle(request, args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
