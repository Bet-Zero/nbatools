"""Plan one bounded, offline team-season whole-game participation batch.

Use a verified local generation restore and retained capture manifests. Optional
archive year trees must match the reviewed index for the exact pinned path.
Rerun after capture to turn acquisition drafts into measured stage requests.
Remote byte ceilings use the existing archive reader's bounded body reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import pandas as pd

from nbatools.commands.pipeline.structured_participation import ARCHIVE, stage_structured_game
from nbatools.commands.pipeline.team_appearance_coverage import qualify_retained_appearances
from tools.cloud_nba_archive import MIRROR, PIN
from tools.participation_coverage import _observed_team_games
from tools.stage_participation_collection import _document, _unique

ENDPOINTS = ("boxscoretraditionalv3", "boxscoresummaryv3")
MAX_ORIGINAL_BYTES = 2_000_000
# fetch_capture stops when its 8 MB payload cap is crossed by a 64 KiB chunk.
REMOTE_BODY_BOUND_BYTES = 8_000_000 + 65_536
DATASET = "raw/player_game_availability"
REVIEWED_ARCHIVE_INDEX = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence"
    / "k08-structured/research/archive-index.json"
)
REVIEWED_ARCHIVE_INDEX_SHA256 = "98ef7c62ce4018cb8d96ea0f60da9952cd5b8e37a79ca9b3b117146224d609d7"


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _git_digest(kind, raw):
    return hashlib.sha1(f"{kind} {len(raw)}\0".encode() + raw).hexdigest()


def _source_url(year, endpoint, game_id):
    return f"{ARCHIVE}/{PIN}/nba_stats/json/{endpoint}/{year}/{game_id}.json"


def _archive_tree(path, expected_tree_sha):
    tree = _document(path)
    entries = {item["path"]: item for item in tree["tree"]}
    if (
        tree["truncated"] is not False
        or len(entries) != len(tree["tree"])
        or any(
            item["type"] != "blob"
            or item["mode"] != "100644"
            or not re.fullmatch(r"[0-9]{10}\.json", name)
            or not re.fullmatch(r"[a-f0-9]{40}", item["sha"])
            for name, item in entries.items()
        )
    ):
        raise ValueError(f"Invalid or incomplete archive year tree: {path}")
    raw_tree = b"".join(
        f"100644 {name}\0".encode() + bytes.fromhex(item["sha"])
        for name, item in sorted(entries.items())
    )
    if _git_digest("tree", raw_tree) != tree["sha"]:
        raise ValueError(f"Archive year tree identity differs from entries: {path}")
    if tree["sha"] != expected_tree_sha:
        raise ValueError(f"Archive year tree differs from reviewed endpoint/year ancestry: {path}")
    return tree["sha"], entries


def _reviewed_archive_trees(tree_files, receipt_path, receipt_sha256):
    if not tree_files:
        return {}
    if receipt_path.is_symlink():
        raise ValueError("Retained archive index receipt must not be a symlink")
    raw = receipt_path.read_bytes()
    if _digest(raw) != receipt_sha256:
        raise ValueError("Archive index receipt differs from independently pinned evidence")
    receipt = json.loads(raw, object_pairs_hook=_unique)
    if (receipt["repository"], receipt["revision"]) != (MIRROR, PIN):
        raise ValueError("Archive index receipt differs from the reviewed mirror revision")
    trees = {}
    for (year, endpoint), path in tree_files.items():
        if not re.fullmatch(r"(?:19|20)[0-9]{2}", year) or endpoint not in ENDPOINTS:
            raise ValueError("Choose the reviewed boxscore archive endpoint and ending year")
        season = f"{int(year) - 1}-{year[-2:]}"
        endpoint_receipt = receipt["endpoints"].get(endpoint, {})
        matched = [item for item in endpoint_receipt.get("samples", []) if item["season"] == season]
        if (
            len(matched) != 1
            or matched[0]["status"] != "untruncated_index_checked"
            or year not in endpoint_receipt.get("indexed_years", [])
            or not re.fullmatch(r"[a-f0-9]{40}", endpoint_receipt.get("endpoint_tree_sha", ""))
            or not re.fullmatch(r"[a-f0-9]{40}", matched[0].get("season_tree_sha", ""))
        ):
            raise ValueError(f"Archive index has no reviewed ancestry for {endpoint}/{year}")
        trees[(year, endpoint)] = _archive_tree(path, matched[0]["season_tree_sha"])
    return trees


def _held_originals(directories):
    originals, manifests = {}, {}
    for directory in directories:
        manifest = directory / "sources.json"
        receipt = _document(manifest)
        if (receipt["repository"], receipt["revision"]) != (MIRROR, PIN):
            raise ValueError(
                f"Held capture differs from the reviewed archive revision: {directory}"
            )
        manifests[str(manifest)] = _digest(manifest.read_bytes())
        for name, item in receipt["files"].items():
            match = re.fullmatch(
                r"(boxscoretraditionalv3|boxscoresummaryv3)_([0-9]{10})\.json", name
            )
            capture = directory / "sources" / name
            if not match or capture.is_symlink() or capture.stat().st_size > MAX_ORIGINAL_BYTES:
                raise ValueError(f"Invalid retained archive file: {capture}")
            endpoint, game_id = match.groups()
            year = item["url"].split("/")[-2]
            raw = capture.read_bytes()
            retrieved = datetime.fromisoformat(item["retrieved_at"])
            if (
                not re.fullmatch(r"(?:19|20)[0-9]{2}", year)
                or item["url"] != _source_url(year, endpoint, game_id)
                or retrieved.utcoffset() is None
                or not 0 < len(raw) == item["size_bytes"]
                or _digest(raw) != item["sha256"]
                or _git_digest("blob", raw) != item["git_blob_sha"]
            ):
                raise ValueError(f"Held capture bytes or provenance differ from receipt: {capture}")
            key = (year, endpoint, game_id)
            if key in originals:
                prior, _, prior_retrieved = originals[key]
                if prior["sha256"] != item["sha256"]:
                    raise ValueError(f"Conflicting held captures for {item['url']}")
                if retrieved >= prior_retrieved:
                    continue
            originals[key] = (item, capture, retrieved)
    return originals, manifests


def _known_failures(paths):
    failures, receipts = {}, {}
    for path in paths:
        attempts = _document(path)["attempts"]
        receipts[str(path)] = _digest(path.read_bytes())
        for item in attempts:
            if item["status"] == "failed":
                failures[item["url"]] = {key: item[key] for key in ("error", "http_status")}
    return failures, receipts


def _preflight(root, season, kind, game, captures):
    """Use the native stage in empty scratch to surface exact original failures."""
    with TemporaryDirectory() as directory:
        scratch = Path(directory)
        suffix = f"{season}_{kind.lower().replace(' ', '_')}.csv"
        for family in ("games", "team_game_stats", "player_game_stats"):
            relative = Path("raw") / family / suffix
            target = scratch / relative
            target.parent.mkdir(parents=True)
            target.symlink_to(root / relative)
        try:
            rows = stage_structured_game(
                scratch,
                season=season,
                season_type=kind,
                game_id=int(game),
                traditional=captures[0][1],
                summary=captures[1][1],
                summary_version=3,
                revision=PIN,
                retrieved_at=max(capture[2] for capture in captures).isoformat(),
            )
        except (ValueError, KeyError, TypeError) as exc:
            return {}, str(exc)
    return {
        int(team_id): int(side.participation_state.eq("unknown").sum())
        for team_id, side in rows.groupby("team_id")
    }, None


def plan_collection(
    root,
    output,
    *,
    manifest_sha256,
    scopes,
    held_captures=(),
    archive_trees=None,
    archive_index_receipt=REVIEWED_ARCHIVE_INDEX,
    archive_index_receipt_sha256=REVIEWED_ARCHIVE_INDEX_SHA256,
    failed_attempts=(),
    max_games,
    max_remote_calls=0,
    max_remote_bytes=0,
):
    """Plan across explicit (season, season type, team ID) scopes, with one shared budget."""
    started = perf_counter()
    root, output = root.resolve(), output.resolve()
    if output.exists() or root == output or root in output.parents:
        raise ValueError("Use a new output directory outside the immutable restore")
    scopes = sorted(set(scopes))
    if not scopes or any(
        not re.fullmatch(r"(?:19|20)[0-9]{2}-[0-9]{2}", season)
        or int(season[-2:]) != (int(season[:4]) + 1) % 100
        or kind not in {"Regular Season", "Playoffs"}
        or type(team) is not int
        or team <= 0
        for season, kind, team in scopes
    ):
        raise ValueError("Choose positive team IDs and explicit NBA season/type scopes")
    if (
        any(type(n) is not int for n in (max_games, max_remote_calls, max_remote_bytes))
        or max_games <= 0
        or min(max_remote_calls, max_remote_bytes) < 0
    ):
        raise ValueError("Choose a positive game limit and nonnegative remote limits")

    manifest_path = root / "metadata/generation_manifest.json"
    manifest = _document(manifest_path)
    if _digest(manifest_path.read_bytes()) != manifest_sha256:
        raise ValueError("Base manifest hash differs from the pinned restore")
    entries = {item["path"]: item for item in manifest["files"]}
    if len(entries) != len(manifest["files"]):
        raise ValueError("Duplicate manifest paths")
    generation = manifest["generation_id"]
    dependencies = {}

    def verify(relative, *, optional=False):
        path = root / relative
        if optional and relative not in entries and not path.exists():
            return None
        if relative not in dependencies:
            if path.resolve() != path or relative not in entries:
                raise ValueError(f"Unmanifested or indirect restore input: {relative}")
            raw = path.read_bytes()
            item = entries[relative]
            if len(raw) != item["size_bytes"] or _digest(raw) != item["sha256"]:
                raise ValueError(f"Restore bytes differ from pinned manifest: {relative}")
            dependencies[relative] = item["sha256"]
        return path

    originals, receipts = _held_originals([path.resolve() for path in held_captures])
    failures, failure_receipts = _known_failures(failed_attempts)
    tree_files = archive_trees or {}
    archive = _reviewed_archive_trees(
        tree_files, archive_index_receipt, archive_index_receipt_sha256
    )
    verify("metadata/player_names.csv")
    games = _collect_sides(root, scopes, dependencies, verify)
    batches, selected_games, selected_calls, selected_bytes = _select_batch(
        root, games, originals, archive, failures, max_games, max_remote_calls, max_remote_bytes
    )
    stage_batches = _write_batches(output, batches, generation, manifest_sha256, originals)
    report = dict(
        schema_version=1,
        base_generation=generation,
        base_manifest_sha256=manifest_sha256,
        archive_repository=MIRROR,
        archive_revision=PIN,
        base_dependencies=dependencies,
        held_capture_manifests=receipts,
        previous_attempt_receipts=failure_receipts,
        archive_index_receipt_sha256=archive_index_receipt_sha256 if tree_files else None,
        archive_year_trees={
            f"{year}/{endpoint}": {
                "archive_tree_sha": archive[year, endpoint][0],
                "document_sha256": _digest(path.read_bytes()),
            }
            for (year, endpoint), path in tree_files.items()
        },
        scopes=[
            dict(season=season, season_type=kind, team_id=team) for season, kind, team in scopes
        ],
        budget=dict(
            games=max_games,
            remote_calls=max_remote_calls,
            remote_body_bytes=max_remote_bytes,
            per_call_body_bound_bytes=REMOTE_BODY_BOUND_BYTES,
        ),
        metrics=dict(
            game_sides=sum(len(game["sides"]) for game in games.values()),
            unique_games=len(games),
            side_states=Counter(side["state"] for game in games.values() for side in game["sides"]),
            batch_games=selected_games,
            planned_remote_calls=selected_calls,
            planned_remote_body_byte_ceiling=selected_bytes,
            batch_states=Counter(game["batch_status"] for game in games.values()),
            actual_remote_calls=0,
            actual_remote_bytes=0,
            r2_writes=0,
            wall_seconds=round(perf_counter() - started, 3),
        ),
        stage_batches=stage_batches,
        games=sorted(games.values(), key=lambda g: (g["game_date"], g["game_id"])),
    )
    _write(output / "plan.json", report)
    return report


def _scheduled_games(schedule, team_id, season, kind):
    fields = ["team_a_id", "team_b_id", "home_team_id", "away_team_id"]
    population = {}
    selected = schedule.loc[schedule[fields].eq(team_id).any(axis="columns")]
    for row in selected.itertuples():
        sides = {row.team_a_id, row.team_b_id}
        venue = tuple(
            value if pd.notna(value) else None for value in (row.home_team_id, row.away_team_id)
        )
        if (
            str(row.status).casefold() != "final"
            or (row.season, row.season_type) != (season, kind)
            or len(sides) != 2
            or team_id not in sides
            or set(venue) - {None} - sides
            or (venue[0] is not None and venue[0] == venue[1])
            or row.game_id in population
        ):
            raise ValueError(f"Unfinished or conflicting scheduled game: {row.game_id}")
        population[row.game_id] = (row.game_date, sides, venue)
    return population


def _collect_sides(root, scopes, dependencies, verify):
    grouped = defaultdict(set)
    for season, kind, team_id in scopes:
        grouped[(season, kind)].add(team_id)
    games = {}
    for (season, kind), team_ids in grouped.items():
        safe = kind.lower().replace(" ", "_")
        suffix = f"{season}_{safe}.csv"
        year = str(int(season[:4]) + 1)
        previous = f"{int(season[:4]) - 1}-{season[2:4]}"
        for relative in (
            f"raw/player_game_stats/{previous}_{safe}.csv",
            f"raw/rosters/{previous}.csv",
            f"raw/rosters/{season}.csv",
        ):
            verify(relative, optional=True)
        catalog = pd.read_csv(verify(f"raw/games/{suffix}"))
        teams = pd.read_csv(verify(f"raw/team_game_stats/{suffix}"))
        verify(f"raw/player_game_stats/{suffix}")
        schedule = pd.read_csv(verify(f"raw/schedule/{suffix}"))
        venues = catalog.set_index("game_id")[["home_team_id", "away_team_id"]]
        csv = verify(f"{DATASET}/{suffix}", optional=True)
        ledger = verify(f"{DATASET}/{suffix.removesuffix('.csv')}.imports.json", optional=True)
        if (csv is None) != (ledger is None):
            raise ValueError(
                "Availability rows and import ledger must be jointly present or absent"
            )
        imports = (
            {int(game_id): value for game_id, value in _document(ledger).items()} if ledger else {}
        )
        occupied = set(pd.read_csv(csv, usecols=["game_id"]).game_id) if csv else set()
        proof = (
            qualify_retained_appearances(root, season, kind, team_ids=team_ids)
            if ledger
            else {"sides": [], "unqualified": []}
        )
        qualified, rejected = {}, {}
        for side in proof["sides"]:
            for relative in side["source_files"]:
                verify(relative)
                if dependencies[relative] != side["source_files"][relative]:
                    raise ValueError(f"Replayed source differs from pinned manifest: {relative}")
            qualified[side["game_id"], side["team_id"]] = side
        for item in proof["unqualified"]:
            rejected[item["game_id"], item.get("team_id")] = item["reason"]
        for team_id in sorted(team_ids):
            observed = _observed_team_games(catalog, teams, season, kind, team_id)
            scheduled = _scheduled_games(schedule, team_id, season, kind)
            if not scheduled or {
                row.game_id: (row.game_date, {team_id, row.opponent_team_id})
                for row in observed.itertuples()
            } != {game: (day, sides) for game, (day, sides, _) in scheduled.items()}:
                raise ValueError(
                    f"Final schedule and reciprocal team games differ: {team_id}, {suffix}"
                )
            for row in observed.itertuples():
                game_id = f"{row.game_id:010d}"
                venue = tuple(
                    int(value) if pd.notna(value) else None for value in venues.loc[row.game_id]
                )
                if venue != scheduled[row.game_id][2]:
                    raise ValueError(f"Canonical and scheduled venue disagree: {game_id}")
                game = games.setdefault(
                    game_id,
                    dict(
                        game_id=game_id,
                        game_date=row.game_date,
                        season=season,
                        season_type=kind,
                        archive_year=year,
                        sides=[],
                        home_team_id=venue[0],
                        away_team_id=venue[1],
                        import_source=imports.get(row.game_id, {}).get("source"),
                        occupied=row.game_id in occupied or row.game_id in imports,
                    ),
                )
                if (game["season"], game["season_type"], game["game_date"]) != (
                    season,
                    kind,
                    row.game_date,
                ):
                    raise ValueError(f"Canonical game appears in conflicting scopes: {game_id}")
                key = (row.game_id, team_id)
                side = dict(team_id=team_id, opponent_team_id=row.opponent_team_id)
                if key in qualified:
                    side.update(
                        state="qualified_retained_side", played=len(qualified[key]["played_ids"])
                    )
                elif game["occupied"]:
                    reason = rejected.get(key) or rejected.get((row.game_id, None))
                    side.update(
                        state="existing_import_side_unqualified",
                        reason=reason or "No complete proof on this side of an existing import",
                    )
                else:
                    side.update(state="complete_side_unknown")
                game["sides"].append(side)

    return games


def _select_batch(
    root, games, originals, archive, failures, max_games, max_remote_calls, max_remote_bytes
):
    eligible = []
    for game_id, game in games.items():
        if game["occupied"]:
            game["batch_status"] = "existing_import_or_rows"
            continue
        if None in (game["home_team_id"], game["away_team_id"]):
            game.update(
                batch_status="canonical_venue_unresolved",
                reason="Structured qualification requires both canonical venue team IDs",
            )
            continue
        year = game["archive_year"]
        sources, captures, missing = {}, [], []
        pending_calls = pending_bytes = 0
        for endpoint in ENDPOINTS:
            name = f"{endpoint}_{game_id}.json"
            source = dict(
                endpoint=endpoint,
                game_id=game_id,
                revision=PIN,
                url=_source_url(year, endpoint, game_id),
            )
            held = originals.get((year, endpoint, game_id))
            tree_sha, tree = archive.get((year, endpoint), (None, {}))
            indexed = tree.get(f"{game_id}.json")
            if indexed:
                source.update(
                    git_blob_sha=indexed["sha"],
                    source_tree_sha=tree_sha,
                )
            if held:
                record = held[0]
                if tree_sha and (not indexed or record["git_blob_sha"] != source["git_blob_sha"]):
                    raise ValueError(f"Held original differs from retained archive tree: {name}")
                source.update(git_blob_sha=record["git_blob_sha"], size_bytes=record["size_bytes"])
                captures.append(held)
                status = "retained_body"
            elif source["url"] in failures:
                source["previous_failure"] = failures[source["url"]]
                status = "known_capture_failure"
            elif indexed:
                pending_calls += 1
                pending_bytes += REMOTE_BODY_BOUND_BYTES
                status = "indexed_body_missing"
            elif tree_sha:
                status = "not_in_held_archive_tree"
            else:
                status = "archive_tree_unknown"
            if status not in {"retained_body", "indexed_body_missing"}:
                missing.append(name)
            sources[name] = dict(**source, status=status)
        game["originals"] = sources
        game["remote_calls"], game["remote_body_byte_ceiling"] = pending_calls, pending_bytes
        if missing:
            game.update(batch_status="original_not_bounded", unresolved_originals=missing)
            continue
        if not pending_calls:
            unknowns, failure = _preflight(
                root, game["season"], game["season_type"], game_id, captures
            )
            for side in game["sides"]:
                unknown = unknowns.get(side["team_id"])
                if failure or unknown != 0:
                    side.update(
                        state="held_side_unqualified",
                        reason=failure or "Incomplete or ambiguous listed participation",
                        unknown_listed_rows=unknown,
                    )
                else:
                    side["state"] = "held_side_preflight_passed"
            if all(side["state"] == "held_side_unqualified" for side in game["sides"]):
                game["batch_status"] = "held_originals_rejected"
                continue
        eligible.append(game)

    batches = defaultdict(list)
    selected_calls = selected_bytes = selected_games = 0
    for game in sorted(eligible, key=lambda g: (g["remote_calls"], g["game_date"], g["game_id"])):
        calls, size = game["remote_calls"], game["remote_body_byte_ceiling"]
        if (
            selected_games == max_games
            or selected_calls + calls > max_remote_calls
            or selected_bytes + size > max_remote_bytes
        ):
            game["batch_status"] = "deferred_by_budget"
            continue
        game["batch_status"] = "awaiting_originals" if calls else "ready_for_staging"
        batches[game["season"], game["season_type"], bool(calls)].append(game)
        selected_calls += calls
        selected_bytes += size
        selected_games += 1

    return batches, selected_games, selected_calls, selected_bytes


def _write_batches(output, batches, generation, manifest_sha256, originals):
    output.mkdir(parents=True)
    stage_batches = []
    for (season, kind, awaiting_originals), selected in batches.items():
        suffix = f"{season}_{kind.lower().replace(' ', '_')}"
        if awaiting_originals:
            suffix += "-awaiting-originals"
        batch = output / suffix
        paths = batch / "capture" / "sources"
        paths.mkdir(parents=True)
        request = dict(
            schema_version=1,
            dataset=DATASET,
            requirement_grain="game",
            season=season,
            season_type=kind,
            base_generation=generation,
            base_manifest_sha256=manifest_sha256,
            repository=MIRROR,
            revision=PIN,
            requirements=[],
            source_files={},
        )
        retained = {}
        for game in selected:
            proposed = []
            for name, source in game["originals"].items():
                source = dict(source)
                is_held = source.pop("status") == "retained_body"
                proposed.append(source)
                request["source_files"][name] = source
                if is_held:
                    item, path, _ = originals[
                        (game["archive_year"], source["endpoint"], game["game_id"])
                    ]
                    raw = path.read_bytes()
                    if _digest(raw) != item["sha256"]:
                        raise ValueError(f"Held original changed during planning: {path}")
                    (paths / name).write_bytes(raw)
                    retained[name] = item
            request["requirements"].append(
                dict(
                    game_id=game["game_id"], game_date=game["game_date"], proposed_sources=proposed
                )
            )
        request_sha = _write(batch / "request.json", request)
        capture_sha = _write(
            batch / "capture" / "sources.json",
            dict(repository=MIRROR, revision=PIN, files=retained),
        )
        stage_batches.append(
            dict(
                directory=suffix,
                games=len(selected),
                status="acquisition_draft" if awaiting_originals else "stage_ready",
                request_sha256=request_sha,
                capture_manifest_sha256=capture_sha,
                held_originals=len(retained),
                held_bytes=sum(item["size_bytes"] for item in retained.values()),
                missing_originals=sorted(request["source_files"].keys() - retained.keys()),
            )
        )
    return stage_batches


def _write(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return _digest(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-data", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument(
        "--scope", action="append", nargs=3, metavar=("SEASON", "TYPE", "TEAM_ID"), required=True
    )
    parser.add_argument("--held-capture", type=Path, action="append", default=[])
    parser.add_argument("--failed-attempts", type=Path, action="append", default=[])
    parser.add_argument(
        "--archive-index-receipt", type=Path, help="Reviewed provider index receipt"
    )
    parser.add_argument(
        "--archive-index-receipt-sha256", help="Independently pinned receipt digest"
    )
    parser.add_argument(
        "--archive-tree",
        action="append",
        nargs=3,
        metavar=("ENDING_YEAR", "ENDPOINT", "FILE"),
        default=[],
    )
    parser.add_argument("--max-games", type=int, required=True)
    parser.add_argument("--max-remote-calls", type=int, default=0)
    parser.add_argument(
        "--max-remote-bytes",
        type=int,
        default=0,
        help="Total conservative response-body ceiling for proposed original reads",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trees = {(year, endpoint): Path(file) for year, endpoint, file in args.archive_tree}
    if len(trees) != len(args.archive_tree):
        parser.error("Duplicate archive year/endpoint tree")
    if bool(args.archive_index_receipt) != bool(args.archive_index_receipt_sha256):
        parser.error(
            "Provide both the reviewed archive index receipt and its independently pinned SHA256"
        )
    report = plan_collection(
        args.base_data,
        args.output,
        manifest_sha256=args.manifest_sha256,
        scopes=[(season, kind, int(team)) for season, kind, team in args.scope],
        held_captures=args.held_capture,
        failed_attempts=args.failed_attempts,
        archive_trees=trees,
        archive_index_receipt=args.archive_index_receipt or REVIEWED_ARCHIVE_INDEX,
        archive_index_receipt_sha256=(
            args.archive_index_receipt_sha256 or REVIEWED_ARCHIVE_INDEX_SHA256
        ),
        max_games=args.max_games,
        max_remote_calls=args.max_remote_calls,
        max_remote_bytes=args.max_remote_bytes,
    )
    print(json.dumps(report["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
