"""Read-only inventory of authenticated generation bytes and precise collection requests.

This extends the existing served-coverage/contract model. It never collects NBA
sources, mutates datasets, uploads R2 objects or changes publication approvals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from nbatools.commands.ops.served_coverage import _SEASON_FILE, _SLICE_FILE, _TYPE_LABELS
from nbatools.commands.pipeline.generation_publication import _resolve_r2_target
from nbatools.commands.pipeline.pull_player_game_availability import COLUMNS as AVAILABILITY_COLUMNS
from nbatools.commands.source_invariants import validate_team_game_pair_invariants
from nbatools.commands.validation_control import DATASET_SPECS, STANDARD_PERIOD_WINDOWS, DatasetSpec
from nbatools.data_source import (
    current_data_generation,
    data_generation_context,
    data_path,
    data_prefetch,
)
from tools.cloud_backup import inventory as manifest_inventory
from tools.r2_publication import verify_pointer_manifest

SPECS = {f"{s.layer}/{s.name}": s for s in DATASET_SPECS}
SPECS["raw/player_game_availability"] = DatasetSpec(
    "player_game_availability",
    "raw",
    "listed player-game participation",
    ("game_id", "team_id", "player_id"),
    "official boxscore participation or qualified final report",
    AVAILABILITY_COLUMNS,
    required=False,
)
CORE_STATS = (
    "pts",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "plus_minus",
)
ROOT = Path(__file__).resolve().parents[1]


def _id(value):
    text = re.sub(r"\.0$", "", str(value).strip())
    return str(int(text)) if re.fullmatch(r"\d+", text) else text


def _game_ids(frame):
    if "game_id" not in frame:
        return set()
    return {_id(v) for v in frame.game_id.dropna()}


def profile_frame(frame, dataset):
    """Observed quality, not an assertion of official statistical completeness."""
    spec = SPECS.get(dataset)
    required = set(spec.required_columns + spec.key_columns) if spec else set()
    if dataset in {"raw/player_game_stats", "raw/team_game_stats"}:
        required.update(CORE_STATS)
    columns = list(frame.columns)
    missing = sorted(required - set(columns))
    keys = list(spec.key_columns) if spec else []
    errors = []
    duplicates = None
    if keys and set(keys).issubset(columns):
        duplicates = int(frame.duplicated(keys).sum())
        if duplicates:
            errors.append(f"{duplicates} duplicate grain keys")
        if frame[keys].isna().any().any():
            errors.append("null grain keys")
    if missing:
        errors.append("missing contract columns: " + ", ".join(missing))
    numeric = {}
    for column in CORE_STATS:
        if column in frame:
            values = pd.to_numeric(frame[column], errors="coerce")
            invalid = int((frame[column].notna() & values.isna()).sum())
            if int((values.notna() & ~np.isfinite(values)).sum()):
                errors.append(f"{column}: nonfinite values")
            if (
                dataset in {"raw/player_game_stats", "raw/team_game_stats"}
                and values.dropna().mod(1).ne(0).any()
            ):
                errors.append(f"{column}: fractional count")
            if invalid:
                errors.append(f"{column}: {invalid} nonnumeric values")
            if column != "plus_minus" and (values < 0).any():
                errors.append(f"{column}: negative count")
            numeric[column] = {"null_rows": int(values.isna().sum()), "nonnumeric_rows": invalid}
    trusts = {}
    for column in columns:
        if column.endswith("_trusted") or column == "coverage_trusted":
            values = pd.to_numeric(frame[column], errors="coerce")
            trusts[column] = {
                "trusted_rows": int(values.eq(1).sum()),
                "other_rows": int((~values.eq(1)).sum()),
            }
    dates = {}
    for column in ("game_date", "snapshot_date", "as_of_date", "source_pull_date"):
        if column in frame:
            values = pd.to_datetime(frame[column], errors="coerce")
            dates[column] = {
                "first": str(values.min().date()) if values.notna().any() else None,
                "last": str(values.max().date()) if values.notna().any() else None,
                "invalid_or_missing_rows": int(values.isna().sum()),
            }
    windows = []
    if {"period_family", "period_value"}.issubset(frame.columns):
        windows = sorted({f"{a}:{b}" for a, b in zip(frame.period_family, frame.period_value)})
    return {
        "rows": len(frame),
        "columns": columns,
        "required_columns": sorted(required),
        "missing_columns": missing,
        "grain": spec.grain if spec else "unregistered",
        "key_columns": keys,
        "duplicate_keys": duplicates,
        "null_counts": {c: int(frame[c].isna().sum()) for c in columns},
        "numeric_checks": numeric,
        "source_labels": {
            c: frame[c].fillna("unknown").astype(str).value_counts().to_dict()
            for c in ("source", "coverage_scope", "source_endpoint", "source_schema_version")
            if c in frame
        },
        "trust": trusts,
        "dates": dates,
        "game_ids": sorted(_game_ids(frame)),
        "period_windows_observed": windows,
        "quality_state": "issues" if errors else "structural_checks_passed",
        "quality_errors": errors,
        "completeness": "unknown: file/schema checks do not establish full NBA coverage",
    }


def _slice(path):
    match = _SLICE_FILE.fullmatch(Path(path).name)
    if match:
        return match["season"], _TYPE_LABELS[match["type"]]
    match = _SEASON_FILE.fullmatch(Path(path).name)
    return (match["season"], "season snapshot") if match else (None, None)


def scan_generation(manifest, path_for, *, origin, evidence):
    entries = manifest_inventory(manifest)
    records = []
    catalogs = {}
    team_keys = {}
    player_team_keys = {}
    for name, expected in sorted(entries.items()):
        path = path_for(name)
        raw = path.read_bytes()
        if (
            len(raw) != expected["size_bytes"]
            or hashlib.sha256(raw).hexdigest() != expected["sha256"]
        ):
            raise ValueError(f"Generation object integrity mismatch: {name}")
        season, kind = _slice(name)
        record = {
            "path": name,
            "bytes": len(raw),
            "sha256": expected["sha256"],
            "season": season,
            "season_type": kind,
            "integrity": "verified",
        }
        if path.suffix == ".csv":
            dataset = "/".join(Path(name).parts[:2])
            try:
                frame = pd.read_csv(path, dtype={"game_id": "string"})
            except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as exc:
                record.update(
                    dataset=dataset, quality_state="issues", quality_errors=[type(exc).__name__]
                )
                records.append(record)
                continue
            record.update(dataset=dataset, **profile_frame(frame, dataset))
            slice_key = f"{season} {kind}"
            if dataset == "raw/games":
                final = frame
                if "is_final" in frame:
                    final = frame.loc[
                        frame.is_final.astype(str).str.lower().isin({"1", "1.0", "true"})
                    ]
                catalogs[slice_key] = {
                    "observed_final_game_ids": sorted(_game_ids(final)),
                    "full_season_completeness": "unknown: no external complete-season denominator",
                }
                pairs = set()
                if {"home_team_id", "away_team_id"}.issubset(final):
                    for row in final.itertuples():
                        pairs.update(
                            {
                                (_id(row.game_id), _id(row.home_team_id)),
                                (_id(row.game_id), _id(row.away_team_id)),
                            }
                        )
                team_keys[slice_key] = pairs
            if dataset in {"raw/player_game_stats", "raw/team_game_stats"} and {
                "game_id",
                "team_id",
            }.issubset(frame):
                pairs = {(_id(g), _id(t)) for g, t in zip(frame.game_id, frame.team_id)}
                player_team_keys[(slice_key, dataset)] = pairs
                if dataset == "raw/team_game_stats":
                    try:
                        validate_team_game_pair_invariants(frame)
                    except (ValueError, KeyError) as exc:
                        record["quality_state"] = "issues"
                        record["quality_errors"].append(str(exc))
        elif name.startswith("metadata/dataset_manifests/"):
            document = json.loads(raw)
            record["recorded_validation"] = {
                "state": document.get("validation_state"),
                "errors": document.get("validation_errors", []),
                "note": "recorded pipeline receipt, separate from inventory recomputation",
            }
        records.append(record)
    for record in records:
        if "dataset" not in record or not record["season"]:
            continue
        key = f"{record['season']} {record['season_type']}"
        catalog = catalogs.get(key)
        if catalog and "game_ids" in record:
            expected_games = set(catalog["observed_final_game_ids"])
            observed = set(record["game_ids"])
            record["game_coverage"] = {
                "denominator": (
                    "observed final games in this generation, not independently complete season"
                ),
                "expected_games": len(expected_games),
                "observed_games": len(observed),
                "missing_game_ids": sorted(expected_games - observed),
                "unexpected_game_ids": sorted(observed - expected_games),
            }
            pair_key = (key, record["dataset"])
            if pair_key in player_team_keys:
                missing = team_keys[key] - player_team_keys[pair_key]
                extra = player_team_keys[pair_key] - team_keys[key]
                record["team_game_coverage"] = {
                    "missing_keys": sorted(missing),
                    "unexpected_keys": sorted(extra),
                }
                record["completeness"] = (
                    "team-game presence checked; complete played-player denominator unknown"
                    if record["dataset"] == "raw/player_game_stats"
                    else "paired coverage against observed final games; full NBA season unknown"
                )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "generation_id": manifest["generation_id"],
        "origin": origin,
        "evidence": evidence,
        "file_count": len(entries),
        "total_bytes": sum(f["size_bytes"] for f in entries.values()),
        "files": records,
        "game_catalogs": catalogs,
        "scope": (
            "manifest-listed objects only; inactive generations and staging "
            "never counted as production"
        ),
        "quality_scope": (
            "recomputed schema/keys/null/numeric/trust and team-pair checks; "
            "not full numerical or semantic feature acceptance"
        ),
        "production_writes": 0,
    }


def staged_inventory(root=ROOT / "working/nba-tools-completion-program/cloud-operations"):
    result = []
    for path in sorted(root.glob("*-receipt.json")):
        receipt = json.loads(path.read_text())
        bundle = receipt.get("durable_bundle")
        if not bundle and path.name == "espn-receipt.json":
            bundle = {"path": "espn-development-staging.zip", "sha256": receipt["bundle_sha256"]}
        if not bundle:
            continue
        name = bundle.get("path")
        if not name or Path(name).name != name:
            continue
        zipped = root / name
        if not zipped.is_file():
            continue
        if hashlib.sha256(zipped.read_bytes()).hexdigest() != bundle["sha256"]:
            raise ValueError(f"Staged bundle checksum mismatch: {name}")
        with zipfile.ZipFile(zipped) as archive:
            members = sorted(
                n for n in archive.namelist() if n.startswith("data/") and n.endswith(".csv")
            )
        result.append(
            {
                "location": "development_staging_in_git",
                "bundle": name,
                "sha256": bundle["sha256"],
                "dataset_paths": members,
                "note": (
                    "staged copy, not evidence of production coverage; paths may overlap production"
                ),
            }
        )
    return result


def collect_production():
    client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    with data_generation_context() as generation:
        before, manifest, digest = verify_pointer_manifest(client, bucket, generation)
        entries = manifest_inventory(manifest)
        data_prefetch(entries)
        report = scan_generation(
            manifest,
            data_path,
            origin="active_production_r2",
            evidence={"manifest_sha256": digest, "active_pointer": before},
        )
        after, _, after_digest = verify_pointer_manifest(client, bucket, generation)
        if before != after or digest != after_digest or generation != current_data_generation():
            raise ValueError("Active generation changed during inventory; rerun before use")
    report["staged_bundles"] = staged_inventory()
    return report


def format_inventory(report):
    counts = Counter(f.get("dataset", "non-CSV evidence") for f in report["files"])
    issues = [f for f in report["files"] if f.get("quality_state") == "issues"]
    lines = [
        "# NBA Tools data availability",
        "",
        f"Generation: `{report['generation_id']}`",
        f"Location: **{report['origin']}**. Generated: {report['generated_at']}",
        f"Verified: {report['file_count']} objects / {report['total_bytes']} bytes.",
        f"CSV files with structural issues: {len(issues)}. "
        "Full-season completeness is not inferred.",
        "",
        "| Dataset | Files | Seasons |",
        "| --- | ---: | --- |",
    ]
    for dataset, count in sorted(counts.items()):
        seasons = sorted(
            {f["season"] for f in report["files"] if f.get("dataset") == dataset and f["season"]}
        )
        lines.append(f"| {dataset} | {count} | {', '.join(seasons)} |")
    lines.extend(["", "## Quality findings"])
    for f in issues:
        lines.append(f"- `{f['path']}`: {'; '.join(f['quality_errors'])}")
    lines.extend(["", "## Development staging (not production coverage)"])
    for b in report.get("staged_bundles", []):
        lines.append(
            f"- `{b['bundle']}`: {len(b['dataset_paths'])} staged CSV files; "
            "inspect JSON for paths/hashes."
        )
    lines.extend(
        [
            "",
            "Read inventory.json for exact columns, null/trust counts, game IDs and missing keys.",
            (
                "Use the request command for a precise collection packet. "
                "Production publication still needs approval."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def collection_request(
    report, dataset, season, kind, *, games=(), fields=(), team_ids=(), player_ids=()
):
    if dataset not in SPECS:
        raise ValueError("Dataset must be an existing canonical contract")
    if not re.fullmatch(r"\d{4}-\d{2}", season) or kind not in {"Regular Season", "Playoffs"}:
        raise ValueError("Explicit canonical season and season type required")
    if int(season[5:]) != (int(season[:4]) + 1) % 100:
        raise ValueError("Season end must follow start")
    spec = SPECS[dataset]
    if not dataset.startswith("raw/"):
        raise ValueError("Processed data is built in cloud; request its raw inputs")
    if "game_id" in spec.key_columns and not games:
        raise ValueError("Explicit bounded game IDs required")
    source = [
        f
        for f in report["files"]
        if f.get("dataset") == dataset
        and f["season"] == season
        and f["season_type"] in {kind, "season snapshot"}
    ]
    available = set(source[0].get("columns", [])) if source else set()
    requested_games = sorted({_id(g) for g in games})
    if any(not re.fullmatch(r"\d{1,10}", g) or int(g) <= 0 for g in requested_games):
        raise ValueError("Invalid NBA game IDs")
    prefix = ("002" if kind == "Regular Season" else "004") + season[2:4]
    if any(not g.zfill(10).startswith(prefix) for g in requested_games):
        raise ValueError("Game IDs must match requested NBA season and type")
    catalog = report["game_catalogs"].get(f"{season} {kind}", {})
    observed_games = set(source[0].get("game_ids", [])) if source else set()
    missing = sorted(set(requested_games) - observed_games)
    requested_fields = sorted(set(fields) | set(spec.required_columns) | set(spec.key_columns))
    if dataset in {"raw/player_game_stats", "raw/team_game_stats"}:
        requested_fields = sorted(set(requested_fields) | set(CORE_STATS))
    return {
        "schema_version": 1,
        "status": "collection_requirement_not_publication_approval",
        "base_generation": report["generation_id"],
        "base_manifest_sha256": report["evidence"]["manifest_sha256"],
        "dataset": dataset,
        "season": season,
        "season_type": kind,
        "requested_nba_game_ids": [g.zfill(10) for g in requested_games],
        "missing_nba_game_ids": [g.zfill(10) for g in missing],
        "game_ids_not_in_production_catalog": sorted(
            set(requested_games) - set(catalog.get("observed_final_game_ids", []))
        ),
        "team_ids": sorted(set(team_ids)),
        "player_ids": sorted(set(player_ids)),
        "required_columns": requested_fields,
        "missing_columns": sorted(set(requested_fields) - available),
        "collection_needed": not source or bool(missing) or bool(set(requested_fields) - available),
        "quality_review_required": bool(source and source[0].get("quality_errors")),
        "unusable_fields": [
            c
            for c in requested_fields
            if source
            and source[0].get("rows", 0) > 0
            and source[0].get("null_counts", {}).get(c) == source[0]["rows"]
        ],
        "availability_note": "Present rows need trust review; player completeness is unknown",
        "grain": spec.grain,
        "key_columns": list(spec.key_columns),
        "source": spec.source,
        "period_windows": list(STANDARD_PERIOD_WINDOWS) if "period_stats" in dataset else [],
        "completeness_requirement": (
            "exact requested games/keys/windows; return all actual played rows,"
            " explicit DNP only from a complete qualified source; no inference "
            "from absence"
        ),
        "acquisition_only": (
            "backup laptop collects original responses + parameters + capture "
            "times; Codex validates/builds/tests in cloud"
        ),
        "handoff": (
            "immutable checksum-bound staging bundle; cloud review/read-only "
            "validation; registered package; separate owner-approved protected "
            "R2 publication"
        ),
    }


def collect_backup(root, receipt):
    root = Path(root)
    raw = (root / "metadata/generation_manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["manifest_sha256"]:
        raise ValueError("Restored generation manifest differs from authenticated backup")
    manifest = json.loads(raw)
    if manifest["generation_id"] != receipt["generation_id"]:
        raise ValueError("Restored generation identity mismatch")
    report = scan_generation(
        manifest,
        lambda name: root / name,
        origin="authenticated_published_r2_backup",
        evidence={
            "manifest_sha256": receipt["manifest_sha256"],
            "note": "verified publication snapshot; check live pointer before assuming current",
        },
    )
    report["staged_bundles"] = staged_inventory()
    return report


def write_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "inventory.md").write_text(format_inventory(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--output", type=Path, required=True)
    backup = sub.add_parser("from-backup")
    backup.add_argument("root", type=Path)
    backup.add_argument("--receipt", type=Path, required=True)
    backup.add_argument("--output", type=Path, required=True)
    request = sub.add_parser("request")
    request.add_argument("inventory", type=Path)
    request.add_argument("--dataset", required=True)
    request.add_argument("--season", required=True)
    request.add_argument("--season-type", default="Regular Season")
    request.add_argument("--game-ids", nargs="*", default=[])
    request.add_argument("--fields", nargs="*", default=[])
    request.add_argument("--team-ids", nargs="*", default=[])
    request.add_argument("--player-ids", nargs="*", default=[])
    args = parser.parse_args()
    if args.command == "collect":
        write_report(collect_production(), args.output)
    elif args.command == "from-backup":
        write_report(collect_backup(args.root, json.loads(args.receipt.read_text())), args.output)
    else:
        print(
            json.dumps(
                collection_request(
                    json.loads(args.inventory.read_text()),
                    args.dataset,
                    args.season,
                    args.season_type,
                    games=args.game_ids,
                    fields=args.fields,
                    team_ids=args.team_ids,
                    player_ids=args.player_ids,
                ),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
