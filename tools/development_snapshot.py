"""Offline provisional snapshots and deduplicated initial-validation intake.

Existing validators and builders keep their verdicts. This module neither acquires
sources nor qualifies NBA values, publishes data, or changes an active pointer.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.validation_control import DATASET_SPECS, build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, safe_file, sha256

BUILDERS = (
    "build_game_features",
    "build_team_game_features",
    "build_player_game_features",
    "build_league_season_stats",
    "build_schedule_context_features",
)


def write_json(path: Path, value) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return sha256(raw)


def intake(backlog: Path, failure: dict) -> str:
    """Write one immutable failure identity; reruns retain its claim/resolution.

    The caller owns this backlog branch. A changed source gets a new linked item;
    rerunning the same source/check/scope cannot reset an investigation's state.
    """
    required = (
        "dataset",
        "source_sha256",
        "scope",
        "check",
        "observed",
        "expected",
        "impact",
        "evidence",
        "next_evidence",
    )
    if any(k not in failure or failure[k] is None for k in required):
        raise ValueError("Failure intake requires actionable source, scope and evidence")
    identity = {k: failure[k] for k in ("dataset", "source_sha256", "scope", "check")}
    fingerprint = sha256(json.dumps(identity, sort_keys=True).encode())
    item_id = "DQ-auto-" + fingerprint
    path = backlog / (item_id + ".json")
    document = dict(
        schema_version=1,
        kind="data_quality_work_item",
        id=item_id,
        fingerprint=fingerprint,
        status="open",
        owner_role="agent_2_data_quality",
        claim=None,
        created_at=datetime.now(UTC).isoformat(),
        observations=[{"snapshot": failure.get("snapshot"), "evidence": failure["evidence"]}],
        last_attempt={"snapshot": failure.get("snapshot"), "evidence": failure["evidence"]},
        resolution=None,
        independent_review=None,
        **failure,
    )
    backlog.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError:
        previous = json.loads(path.read_bytes())
        if previous["fingerprint"] != fingerprint:
            raise ValueError("Failure identity conflict") from None
        snapshot = failure.get("snapshot")
        if snapshot and snapshot not in {
            o.get("snapshot") for o in previous.get("observations", [])
        }:
            previous.setdefault("observations", []).append(
                {"snapshot": snapshot, "evidence": failure["evidence"]}
            )
            previous["last_attempt"] = previous["observations"][-1]
            write_json(path, previous)
    return item_id


def intake_report(backlog: Path, report: dict, evidence: dict) -> list[str]:
    """Adapt unchanged build_slice_manifest failures into source-linked items."""
    ids = []
    for record in report["datasets"]:
        for error in record["validation"]["errors"]:
            ids.append(
                intake(
                    backlog,
                    dict(
                        dataset=record["name"],
                        source_sha256=record["file_sha256"] or evidence["source_sha256"],
                        scope={
                            "season": report["season"],
                            "season_type": report["season_type"],
                            "coverage": record["coverage"],
                            "key_columns": record["key_columns"],
                        },
                        check=error,
                        observed=record["validation"],
                        expected="existing dataset contract",
                        impact="dependent fields/consumers and data acceptance remain unqualified",
                        evidence=evidence,
                        next_evidence="Diagnose exact recorded scope against retained source",
                        snapshot=report["generation_id"],
                    ),
                )
            )
    return ids


def _safe_contracts(root: Path, season: str, season_type: str) -> None:
    """Reject schema/identity corruption independently of numerical qualification."""
    suffix = f"{season}_{season_type.lower().replace(' ', '_')}.csv"
    frames = {}
    for spec in DATASET_SPECS:
        filename = f"{season}.csv" if spec.season_only else suffix
        path = root / "data" / spec.layer / spec.name / filename
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        frames[spec.name] = frame
        required = set(spec.required_columns) | set(spec.key_columns)
        if not required <= set(frame.columns):
            raise ValueError(f"Unsafe schema for {spec.name}")
        if (
            frame[list(spec.key_columns)].isna().any().any()
            or frame.duplicated(list(spec.key_columns)).any()
        ):
            raise ValueError(f"Unsafe grain/identity for {spec.name}")
        for key in spec.key_columns:
            if key.endswith("_id"):
                values = pd.to_numeric(frame[key], errors="coerce")
                if values.isna().any() or not values.gt(0).all() or not values.mod(1).eq(0).all():
                    raise ValueError(f"Unsafe numeric identity for {spec.name}")
        for column, expected in (("season", season), ("season_type", season_type)):
            if column in frame and not frame[column].eq(expected).all():
                raise ValueError(f"Unsafe slice identity for {spec.name}")

    # Missing coverage remains unqualified; an observed row with a contradictory
    # game/team/player identity is unsafe and must never enter usable data.
    if "player_game_stats" in frames:
        if not {"games", "team_game_stats"} <= set(frames):
            raise ValueError("Player inputs require their game/team identity catalogs")
        games, teams, players = (
            frames[k] for k in ("games", "team_game_stats", "player_game_stats")
        )
        if not set(teams.game_id) <= set(games.game_id):
            raise ValueError("Unsafe team-game identity outside catalog")
        for game in games.itertuples():
            rows = teams.loc[teams.game_id.eq(game.game_id)]
            sides = {game.home_team_id, game.away_team_id}
            if len(rows) != 2 or set(rows.team_id) != sides:
                raise ValueError("Unsafe team sides or missing game/team identity catalog")
            if any(r.opponent_team_id not in sides - {r.team_id} for r in rows.itertuples()):
                raise ValueError("Unsafe opponent identity outside catalog")
        allowed = set(zip(teams.game_id, teams.team_id))
        if not set(zip(players.game_id, players.team_id)) <= allowed:
            raise ValueError("Unsafe player-game/team identity outside catalog")
        if "player_game_period_stats" in frames:
            period = frames["player_game_period_stats"]
            keys = ["game_id", "team_id", "player_id"]
            if not set(period[keys].itertuples(index=False, name=None)) <= set(
                players[keys].itertuples(index=False, name=None)
            ):
                raise ValueError("Unsafe period/player identity outside catalog")


def prepare(
    source: Path,
    output: Path,
    *,
    version: str,
    season: str,
    season_type: str,
    scope: str,
    source_evidence: dict,
    backlog: Path,
    exceptions: list[str],
    fixture: bool = False,
    correction: dict | None = None,
) -> str:
    """Copy safe inputs to a NEW snapshot; optionally apply reviewed keyed data.

    A correction is restricted to raw player AST/STL/BLK/PF count fields, whose
    dependent rolling values the existing player builder recalculates. Other raw
    families/derived rate inputs require their existing qualified preparation path.
    """
    source, output = source.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(source):
        raise ValueError("Snapshot output must be new and separate from its source")
    if not source_evidence.get("reference") or not source_evidence.get("sha256") or not scope:
        raise ValueError("Snapshot requires source evidence and explicit scope/cutoff")
    if (source / MANIFEST).exists():
        expected = correction["base_manifest_sha256"] if correction else source_evidence["sha256"]
        DevelopmentSnapshot(source, expected)  # hash-only complete inventory authentication
    try:
        _safe_contracts(source, season, season_type)
    except ValueError as exc:
        intake(
            backlog,
            dict(
                dataset="snapshot_safe_contract",
                source_sha256=source_evidence["sha256"],
                scope={"season": season, "season_type": season_type},
                check="safe schema and identity",
                observed=str(exc),
                expected="unambiguous intact schema, grain and game/team identities",
                impact="input quarantined; no development snapshot produced",
                evidence=source_evidence,
                next_evidence="Repair contract or qualify correct source identity",
            ),
        )
        raise
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="snapshot-") as temp:
        stage = Path(temp)
        suffix = f"{season}_{season_type.lower().replace(' ', '_')}.csv"
        for path in sorted((source / "data").rglob("*")):
            relative = path.relative_to(source).as_posix()
            safe_file(source, relative)
            selected = path.name in {suffix, f"{season}.csv"}
            correction_history = relative.startswith("data/metadata/corrections/")
            if path.is_file() and (selected or correction_history):
                if path.suffix not in {".csv", ".json"}:
                    raise ValueError("Only portable CSV/JSON data may enter development")
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        if correction is not None:
            original_manifest = source / MANIFEST
            if (
                not original_manifest.exists()
                or sha256(original_manifest.read_bytes()) != correction["base_manifest_sha256"]
            ):
                raise ValueError("Correction base snapshot changed")
            review = correction["independent_review"]
            if (
                not review.get("reference")
                or not review.get("reviewer")
                or review["reviewer"] == correction["author"]
            ):
                raise ValueError("Correction requires actual separate review evidence")
            relative = (
                f"data/raw/player_game_stats/{season}_{season_type.lower().replace(' ', '_')}.csv"
            )
            path = stage / relative
            if sha256(path.read_bytes()) != correction["source_sha256"]:
                raise ValueError("Correction source precondition changed")
            frame = pd.read_csv(path, dtype=str, keep_default_na=False)
            touched = set()
            for change in correction["changes"]:
                if set(change["key"]) != {"game_id", "player_id", "team_id"}:
                    raise ValueError("Correction requires the complete player-game key")
                field = change["field"]
                if field not in {"ast", "stl", "blk", "pf"}:
                    raise ValueError(
                        "Use existing qualified preparation for other dependent fields"
                    )
                mask = pd.Series(True, index=frame.index)
                for key, value in change["key"].items():
                    mask &= frame[key].str.lstrip("0").eq(str(value).lstrip("0"))
                identity = (
                    tuple(sorted((k, str(v).lstrip("0") or "0") for k, v in change["key"].items())),
                    field,
                )
                if (
                    identity in touched
                    or mask.sum() != 1
                    or frame.loc[mask, field].iloc[0] != str(change["before"])
                ):
                    raise ValueError("Correction conflict or stale old value")
                value = change["after"]
                if type(value) is not int or value < 0 or not change.get("evidence"):
                    raise ValueError("Correction requires supported nonnegative source count")
                touched.add(identity)
                frame.loc[mask, field] = str(value)
            frame.to_csv(path, index=False)
            # No process-wide cwd mutation; existing pure builders run in isolated work.
            code = (
                "from nbatools.commands.pipeline.build_player_game_features import run; "
                "import sys; run(sys.argv[1],sys.argv[2])"
            )
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
            subprocess.run(
                [sys.executable, "-c", code, season, season_type],
                cwd=stage,
                env=env,
                check=True,
                capture_output=True,
            )
            write_json(
                stage
                / "data/metadata/corrections"
                / (sha256(json.dumps(correction, sort_keys=True).encode()) + ".json"),
                correction,
            )
        _safe_contracts(stage, season, season_type)
        report = build_slice_manifest(
            season, season_type, data_root=stage / "data", generation_id=version
        )
        evidence = dict(
            reference=source_evidence["reference"],
            source_sha256=source_evidence["sha256"],
            sha256=sha256(json.dumps(report, sort_keys=True).encode()),
        )
        ids = sorted(set(exceptions + intake_report(backlog, report, evidence)))
        report_sha = write_json(stage / "data/metadata/initial-validation.json", report)
        files = {
            p.relative_to(stage).as_posix(): sha256(p.read_bytes())
            for p in sorted((stage / "data").rglob("*"))
            if p.is_file()
        }
        digest = write_json(
            stage / MANIFEST,
            dict(
                schema_version=1,
                version=version,
                quality="provisional",
                scope=scope,
                source_evidence=source_evidence,
                fixture=fixture,
                exceptions=ids,
                files=files,
                validation_reports=[
                    {
                        "path": "data/metadata/initial-validation.json",
                        "sha256": report_sha,
                        "state": report["validation_state"],
                    }
                ],
            ),
        )
        # Rename only after all preparation succeeds; an existing version is never replaced.
        stage.rename(output)
    return digest
