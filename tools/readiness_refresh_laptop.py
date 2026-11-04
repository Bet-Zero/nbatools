"""Standalone on-demand acquisition runtime, embedded with the existing collector.

Only the cloud builder supplies SEED. No repository, credentials, installation,
publication or timer is needed on the acquisition laptop. Keep the state folder.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SEED = None
if SEED is None:
    from tools.collect_rollover_readiness_laptop import collect, validate_request
MIRROR = "sportsdataverse/hoopR-nba-stats-raw"
MAX_GAMES, MAX_DIRECT = 40, 500
MAX_ARCHIVE_BYTES, MAX_RUN_SECONDS = 32_000_000, 43_200
PERIODS = {
    "q1": (1, 1),
    "q2": (2, 2),
    "q3": (3, 3),
    "q4": (4, 4),
    "h1": (1, 2),
    "h2": (3, 4),
    "ot": (5, 14),
}


def token(job):
    parameters = dict(job["parameters"])
    if job["endpoint"] in {"leaguedashplayerstats", "leaguedashteamstats"}:
        if parameters.get("ISTRound") is not None:
            raise ValueError("Unexpected tournament-round filter")
        parameters.pop("ISTRound", None)
    payload = json.dumps(
        [job["endpoint"], parameters], sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def blob_hash(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def json_write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def schedule_due(document, now):
    """Exact UTC24h boundary, matching canonical readiness's ET-date invariant."""
    if now.tzinfo is None:
        raise ValueError("Timezone required")
    schedule = document["leagueSchedule"]
    if schedule["seasonYear"] != "2026-27" or schedule["leagueId"] != "00":
        raise ValueError("Current-season schedule identity differs")
    seen, due = set(), []
    for day in schedule["gameDates"]:
        for game in day["games"]:
            gid = game["gameId"]
            if not re.fullmatch(r"00226\d{5}", gid):
                continue
            if gid in seen or game["gameStatus"] not in (1, 2, 3):
                raise ValueError("Schedule duplicate or unknown status")
            seen.add(gid)
            date = datetime.fromisoformat(game["gameDateEst"].replace("Z", "+00:00")).date()
            instant = datetime.fromisoformat(game["gameDateTimeUTC"].replace("Z", "+00:00"))
            if (
                instant.tzinfo is None
                or instant.astimezone(ZoneInfo("America/New_York")).date() != date
            ):
                raise ValueError("Schedule instant and basketball date disagree")
            if instant <= now - timedelta(hours=24):
                due.append(gid)
    if not seen:
        raise ValueError("Empty regular-season schedule")
    return sorted(due)


def summary_periods(document, gid):
    box = document["boxScoreSummary"]
    if box["gameId"] != gid:
        raise ValueError("Summary identity differs")
    sides = [[p["period"] for p in box[side]["periods"]] for side in ("homeTeam", "awayTeam")]
    count = len(sides[0])
    if (
        not 4 <= count <= 14
        or any(p != list(range(1, count + 1)) for p in sides)
        or box["period"] != count
    ):
        return None
    return count


def game_jobs(gid, count):
    labels = [*list(PERIODS)[:6], *(["ot"] if count and count > 4 else [])]
    jobs = []
    for label in labels:
        first, last = PERIODS[label]
        for endpoint in ("boxscoretraditionalv3", "boxscoreadvancedv3"):
            jobs.append(
                {
                    "endpoint": endpoint,
                    "parameters": {
                        "GameID": gid,
                        "StartPeriod": first,
                        "EndPeriod": last,
                        "RangeType": 1,
                        "StartRange": 0,
                        "EndRange": 28800,
                    },
                    "source_file": f"sources/{endpoint}_{gid}_{label}.json",
                }
            )
    return jobs


def local_summary_counts(root):
    counts = {}
    for path in (root / "batches").glob("*/acquisition.json"):
        report = json.loads(path.read_bytes())
        for attempt in report["attempts"]:
            job = attempt["job"]
            if job["endpoint"] == "boxscoresummaryv3" and attempt.get("transport_complete"):
                gid = job["parameters"]["GameID"]
                counts[gid] = summary_periods(
                    json.loads((path.parent / job["source_file"]).read_bytes()), gid
                )
    return counts


def retained_successes(root, seed):
    """Recheck all local originals; an interruption/failure stops future runs."""
    successes = set(seed["successes"])
    for path in sorted((root / "batches").glob("*/acquisition.json")):
        if path.is_symlink() or path.parent.is_symlink() or (path.parent / "sources").is_symlink():
            raise ValueError("Local report symlink")
        report = json.loads(path.read_bytes())
        request = report["request"]
        if (
            validate_request(request) != report["request_sha256"]
            or report["production_writes"] != 0
            or (path.parent / "sources/capture-attempt.json").read_bytes() != path.read_bytes()
            or len(report["attempts"]) > len(request["jobs"])
        ):
            raise ValueError("Local acquisition binding differs")
        for attempt, job in zip(report["attempts"], request["jobs"], strict=False):
            body = path.parent / job["source_file"]
            if (
                attempt["job"] != job
                or not attempt.get("transport_complete")
                or attempt.get("http_status") != 200
                or attempt.get("attempts") != 1
                or attempt.get("source_file") != job["source_file"]
                or attempt.get("endpoint") != job["endpoint"]
                or attempt.get("parameters") != job["parameters"]
                or attempt.get("url") != "https://stats.nba.com/stats/" + job["endpoint"]
                or attempt.get("response_complete") is not True
                or attempt.get("error_type")
                or body.is_symlink()
            ):
                raise ValueError(
                    "Prior failed/interrupted capture requires cloud diagnosis; do not retry"
                )
            raw = body.read_bytes()
            if (
                not 0 < len(raw) <= 2_000_000
                or len(raw) != attempt["response_bytes"]
                or hashlib.sha256(raw).hexdigest() != attempt["response_sha256"]
                or not isinstance(json.loads(raw), dict)
            ):
                raise ValueError("Local original changed")
            key = token(job)
            if key in successes:
                raise ValueError("Local capture repeated a successful request")
            successes.add(key)
    return successes


class ArchiveSession:
    """Public immutable GitHub metadata/raw reads, finite per invocation."""

    def __init__(self, root, state, started):
        self.root, self.state, self.started = root, state, started
        self.requests, self.bytes = 0, 0
        self.changed = []

    def get(self, url, destination, limit):
        import requests

        if self.requests >= 32 or time.monotonic() - self.started + 31 > 600:
            raise ValueError("Archive discovery request/time ceiling reached")
        if not (
            url.startswith(f"https://api.github.com/repos/{MIRROR}/")
            or url.startswith(f"https://raw.githubusercontent.com/{MIRROR}/")
        ):
            raise ValueError("Unapproved archive source")
        self.requests += 1
        raw = bytearray()
        try:
            with requests.get(url, timeout=30, stream=True, allow_redirects=False) as response:
                for chunk in response.iter_content(65536):
                    remaining = min(limit - len(raw), MAX_ARCHIVE_BYTES - self.bytes)
                    raw.extend(chunk[:remaining])
                    self.bytes += min(len(chunk), remaining)
                    if len(chunk) > remaining or time.monotonic() - self.started > 600:
                        raise ValueError("Archive response/elapsed ceiling reached")
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError("Archive requires HTTP200")
        finally:
            with destination.open("xb") as handle:
                handle.write(raw)
            self.changed.append(destination)
        return bytes(raw)

    def metadata(self, suffix):
        path = self.root / "metadata" / f"{self.requests:02d}.json"
        raw = self.get(f"https://api.github.com/repos/{MIRROR}/{suffix}", path, 2_000_000)
        return json.loads(raw)

    def tree(self, sha):
        if not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("Immutable Git tree required")
        document = self.metadata("git/trees/" + sha)
        if document.get("truncated") is not False:
            raise ValueError("Archive tree is incomplete")
        return {item["path"]: item for item in document["tree"]}

    def discover(self):
        head = self.metadata("commits?per_page=1")[0]
        revision = head["sha"]
        tree = self.tree(revision)
        tree = self.tree(tree["nba_stats"]["sha"])
        tree = self.tree(tree["json"]["sha"])
        schedule = self.tree(tree["scheduleleaguev2"]["sha"])["2027.json"]
        summaries = self.tree(tree["boxscoresummaryv3"]["sha"])
        summaries = self.tree(summaries["2027"]["sha"])
        return revision, schedule, summaries

    def body(self, revision, path, entry):
        blob = entry["sha"]
        if (
            not re.fullmatch(r"[a-f0-9]{40}", blob)
            or entry.get("type") != "blob"
            or not 0 < entry["size"] <= 8_000_000
        ):
            raise ValueError("Invalid bounded archive blob")
        destination = self.root.parent.parent / "archive" / (blob + ".json")
        if destination.is_symlink():
            raise ValueError("Archive original symlink")
        if destination.exists():
            raw = destination.read_bytes()
        else:
            key = path + ":" + blob
            if key in self.state["archive_attempts"]:
                raise ValueError("Prior failed archive request requires cloud diagnosis")
            self.state["archive_attempts"][key] = {"state": "started", "revision": revision}
            json_write(self.root.parent.parent / "state.json", self.state)
            raw = self.get(
                f"https://raw.githubusercontent.com/{MIRROR}/{revision}/{path}",
                destination,
                8_000_000,
            )
            self.state["archive_attempts"][key]["state"] = "complete"
        if len(raw) != entry["size"] or blob_hash(raw) != blob:
            raise ValueError("Archive original differs from immutable Git blob")
        json_write(self.root.parent.parent / "state.json", self.state)
        return json.loads(raw)


def execute(root, seed):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("State directory symlink")
    root.mkdir(exist_ok=True)
    for folder in ("archive", "batches", "runs"):
        path = root / folder
        if path.is_symlink():
            raise ValueError("State subdirectory symlink")
        path.mkdir(exist_ok=True)
    state_path = root / "state.json"
    if state_path.is_symlink():
        raise ValueError("State symlink")
    seed_sha = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    state = (
        json.loads(state_path.read_bytes())
        if state_path.exists()
        else {"seed_sha256": seed_sha, "archive_attempts": {}, "production_writes": 0}
    )
    if state["seed_sha256"] != seed_sha or state["production_writes"] != 0:
        raise ValueError("Persistent state belongs to a different verified seed")
    now, started = datetime.now(UTC), time.monotonic()
    run = root / "runs" / now.strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir()
    (run / "metadata").mkdir()
    receipt = {
        "classification": "unvalidated_acquisition_only",
        "checked_at": now.isoformat(),
        "production_writes": 0,
        "statistical_acceptance": False,
        "lag_hours": 24,
        "seed_sha256": seed_sha,
        "reused_successes": None,
        "jobs": [],
        "period_population_unresolved": [],
        "state": "failed",
    }
    archive = ArchiveSession(run, state, started)
    outputs = []
    failed_paths = [root / name for name in state.get("blocked_files", [])]
    try:
        if state.get("blocked") or seed.get("blocked_attempts") or seed.get("transport_blocks"):
            raise ValueError("Prior failed invocation requires cloud diagnosis; do not retry")
        successes = retained_successes(root, seed)
        receipt["reused_successes"] = len(successes)
        local_counts = local_summary_counts(root)
        revision, schedule_entry, summary_entries = archive.discover()
        receipt["mirror_revision"] = revision
        schedule_path = root / "archive" / (seed["schedule"]["blob"] + ".json")
        if not schedule_path.exists():
            schedule_path.write_bytes(
                base64.b64decode(seed["schedule"]["body_base64"], validate=True)
            )
        schedule = archive.body(
            revision, "nba_stats/json/scheduleleaguev2/2027.json", schedule_entry
        )
        due = schedule_due(schedule, now)
        receipt["due_game_ids"] = due
        jobs = [
            job
            for job in seed.get("dependencies", [])
            if token(job) not in successes and job["parameters"].get("GameID") in due
        ]
        dates = [
            game["gameDateEst"][:10]
            for day in schedule["leagueSchedule"]["gameDates"]
            for game in day["games"]
            if game["gameId"] in due
        ]
        if dates:
            cutoff = datetime.fromisoformat(max(dates)).strftime("%m/%d/%Y")
            for template in seed.get("snapshot_templates", []):
                job = {
                    **template,
                    "parameters": {**template["parameters"], "DateTo": cutoff},
                    "source_file": "sources/"
                    + template["endpoint"]
                    + "_advanced_through_"
                    + max(dates).replace("-", "")
                    + ".json",
                }
                if token(job) not in successes:
                    jobs.append(job)
        selected = sorted(
            {job["parameters"]["GameID"] for job in jobs if "GameID" in job["parameters"]}
        )
        for gid in due:
            known = seed["summaries"].get(gid)
            entry = summary_entries.get(gid + ".json")
            if known and entry and known["blob"] == entry["sha"]:
                count = known["periods"]
            elif entry:
                # Only fetch changed/new Summary when a direct window is missing,
                # or a changed catalog can add a never-requested OT window.
                document = archive.body(
                    revision, f"nba_stats/json/boxscoresummaryv3/2027/{gid}.json", entry
                )
                count = summary_periods(document, gid)
            else:
                count = local_counts.get(gid)
            if count is None:
                receipt["period_population_unresolved"].append(gid)
            pending = [job for job in game_jobs(gid, count) if token(job) not in successes]
            # A missing archive Summary needs its first direct source request.
            summary_job = {
                "endpoint": "boxscoresummaryv3",
                "parameters": {"GameID": gid},
                "source_file": f"sources/boxscoresummaryv3_{gid}.json",
            }
            if not entry and token(summary_job) not in successes:
                pending.insert(0, summary_job)
            if pending:
                if len(set(selected) | {gid}) > MAX_GAMES or len(jobs) + len(pending) > MAX_DIRECT:
                    receipt["remaining_due_work"] = True
                    break
                jobs.extend(pending)
                if gid not in selected:
                    selected.append(gid)
        receipt.update(jobs=jobs, selected_game_ids=selected)
        if jobs:
            request = {
                "status": "collection_requirement_not_publication_approval",
                "season": "2026-27",
                "season_type": "Regular Season",
                "base_generation": seed["base_generation"],
                "base_manifest_sha256": seed["base_manifest_sha256"],
                "jobs": jobs,
                "maximum_requests": len(jobs),
                "attempts_per_job": 1,
                "timeout_seconds": 30,
                "response_limit_bytes": 2_000_000,
                "minimum_interval_seconds": 1,
                "maximum_elapsed_seconds": min(MAX_RUN_SECONDS - 600, len(jobs) * 32 + 31),
            }
            request_sha = validate_request(request)
            output = root / "batches" / request_sha
            outputs.append(output)
            report = collect(output, request)
            receipt["state"] = (
                "transport_complete" if report.get("transport_finished") else "capture_stopped"
            )
        else:
            receipt["state"] = "no_missing_direct_requests"
        # A first direct Summary can reveal OT missing from the mirror. Capture
        # that never-requested pair in this same bounded invocation.
        after = retained_successes(root, seed)
        discovered = local_summary_counts(root)
        receipt["period_population_unresolved"] = [
            gid for gid in receipt["period_population_unresolved"] if discovered.get(gid) is None
        ]
        additional = [
            job
            for gid in selected
            if discovered.get(gid, 4) and discovered.get(gid, 4) > 4
            for job in game_jobs(gid, discovered[gid])
            if token(job) not in after
        ]
        if additional:
            if len(jobs) + len(additional) > MAX_DIRECT:
                raise ValueError("Direct request ceiling reached; originals preserved")
            extra = {
                **request,
                "jobs": additional,
                "maximum_requests": len(additional),
                "maximum_elapsed_seconds": len(additional) * 32 + 31,
            }
            output = root / "batches" / validate_request(extra)
            outputs.append(output)
            report = collect(output, extra)
            receipt["jobs"].extend(additional)
            receipt["state"] = (
                "transport_complete" if report.get("transport_finished") else "capture_stopped"
            )
        receipt["verified_successes_after_run"] = len(retained_successes(root, seed))
    except BaseException as exc:
        receipt.update(error_type=type(exc).__name__, state="failed_preserve_output_do_not_retry")
        # A killed process may leave a checkpoint but no collection ZIP.
        for report_path in (root / "batches").glob("*/acquisition.json"):
            report = json.loads(report_path.read_bytes())
            if any(not row.get("transport_complete") for row in report["attempts"]):
                failed_paths.extend(
                    path
                    for path in report_path.parent.rglob("*.json")
                    if path.is_file() and not path.is_symlink()
                )
        state["blocked"] = True
        state["blocked_files"] = sorted(
            {path.relative_to(root).as_posix() for path in [*failed_paths, *archive.changed]}
        )
        json_write(state_path, state)
    finally:
        receipt.update(
            archive_requests=archive.requests,
            archive_bytes=archive.bytes,
            finished_at=datetime.now(UTC).isoformat(),
        )
        json_write(run / "receipt.json", receipt)
        paths = list(
            dict.fromkeys([*archive.changed, *failed_paths, run / "receipt.json", state_path])
        )
        paths.extend(
            output / "collection.zip" for output in outputs if (output / "collection.zip").exists()
        )
        # Export this invocation only. The persistent originals/cache stay in place.
        total = sum(path.stat().st_size for path in paths if path.exists())
        if total <= 100_000_000:
            temporary = root / "return.tmp"
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as z:
                for path in paths:
                    if path.exists():
                        z.write(path, path.relative_to(root).as_posix())
            if temporary.stat().st_size <= 20_000_000:
                temporary.replace(root / "current-run.zip")
            else:
                receipt["export_failure"] = "ZIP exceeds20MB; originals retained"
        else:
            receipt["export_failure"] = "Expanded export exceeds100MB; originals retained"
        json_write(run / "receipt.json", receipt)
    return receipt


def main():
    if SEED is None:
        raise ValueError("Use the cloud-prepared package with immutable verified seed")
    result = execute(Path(__file__).resolve().with_name("readiness-refresh"), SEED)
    print(
        "Return readiness-refresh/current-run.zip, including after failure. "
        "Keep this entire folder for reuse."
    )
    print(f"{result['state']}; production writes0; no dataset accepted or published.")
    return 0 if result["state"] in {"transport_complete", "no_missing_direct_requests"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
