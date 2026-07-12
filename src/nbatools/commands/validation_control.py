"""Versioned dataset validation receipts for one season/type slice."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from nbatools.commands.data_utils import (
    LEAGUE_LINEUP_VIZ_REQUIRED_COLUMNS,
    PLAY_BY_PLAY_EVENT_REQUIRED_COLUMNS,
    PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS,
    PLAYER_GAME_PERIOD_REQUIRED_COLUMNS,
    PLAYER_GAME_STARTER_ROLE_REQUIRED_COLUMNS,
    SCHEDULE_CONTEXT_REQUIRED_COLUMNS,
    TEAM_GAME_CLUTCH_REQUIRED_COLUMNS,
    TEAM_GAME_PERIOD_REQUIRED_COLUMNS,
    TEAM_PLAYER_ON_OFF_REQUIRED_COLUMNS,
)
from nbatools.data_source import data_exists, data_path

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_DIR = "dataset_manifests"
STANDARD_PERIOD_WINDOWS = (
    ("quarter", "1"),
    ("quarter", "2"),
    ("quarter", "3"),
    ("quarter", "4"),
    ("half", "first"),
    ("half", "second"),
)


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    name: str
    layer: str
    grain: str
    key_columns: tuple[str, ...]
    source: str
    required_columns: tuple[str, ...] = ()
    required: bool = True
    season_only: bool = False
    regular_season_only: bool = False
    trust_column: str | None = None
    trust_reason_column: str | None = None

    def applies(self, season_type: str) -> bool:
        return not self.regular_season_only or season_type == "Regular Season"


DATASET_SPECS = (
    DatasetSpec(
        "games",
        "raw",
        "game",
        ("game_id",),
        "league_game_log",
        (
            "season",
            "season_type",
            "game_date",
            "is_final",
            "home_team_id",
            "away_team_id",
            "site_type",
            "neutral_site",
            "home_away_designation_trusted",
            "home_away_source",
        ),
    ),
    DatasetSpec(
        "schedule",
        "raw",
        "game",
        ("game_id",),
        "league_schedule",
        (
            "season",
            "season_type",
            "game_date",
            "home_team_id",
            "away_team_id",
            "site_type",
            "neutral_site",
            "home_away_designation_trusted",
            "home_away_source",
        ),
    ),
    DatasetSpec(
        "team_game_stats",
        "raw",
        "team-game",
        ("game_id", "team_id"),
        "league_game_log",
        (
            "season",
            "season_type",
            "game_date",
            "opponent_team_id",
            "is_home",
            "is_away",
            "wl",
            "pts",
            "fgm",
            "fga",
            "fg3m",
            "fg3a",
            "ftm",
            "fta",
            "reb",
            "tov",
            "plus_minus",
        ),
    ),
    DatasetSpec(
        "player_game_stats",
        "raw",
        "player-game",
        ("game_id", "team_id", "player_id"),
        "league_game_log",
        (
            "season",
            "season_type",
            "game_date",
            "player_name",
            "opponent_team_id",
            "minutes",
            "pts",
            "fgm",
            "fga",
            "fg3m",
            "fg3a",
            "ftm",
            "fta",
            "reb",
            "ast",
            "tov",
            "plus_minus",
        ),
    ),
    DatasetSpec(
        "player_game_starter_roles",
        "raw",
        "player-game role",
        ("game_id", "team_id", "player_id"),
        "boxscore_traditional_v3.position",
        tuple(PLAYER_GAME_STARTER_ROLE_REQUIRED_COLUMNS),
        trust_column="role_source_trusted",
        trust_reason_column="role_validation_reason",
    ),
    DatasetSpec(
        "player_game_period_stats",
        "raw",
        "player-game period window",
        ("game_id", "team_id", "player_id", "period_family", "period_value"),
        "boxscore_traditional_v3+advanced_v3",
        tuple(PLAYER_GAME_PERIOD_REQUIRED_COLUMNS),
    ),
    DatasetSpec(
        "team_game_period_stats",
        "raw",
        "team-game period window",
        ("game_id", "team_id", "period_family", "period_value"),
        "boxscore_traditional_v3",
        tuple(TEAM_GAME_PERIOD_REQUIRED_COLUMNS),
    ),
    DatasetSpec(
        "team_season_advanced",
        "raw",
        "team-season snapshot",
        ("team_id", "as_of_date"),
        "league_dash_team_stats",
        ("season", "season_type", "off_rating", "def_rating", "net_rating"),
    ),
    DatasetSpec(
        "player_season_advanced",
        "raw",
        "player-season snapshot",
        ("player_id", "as_of_date"),
        "league_dash_player_stats",
        ("season", "season_type", "usage_rate", "ts_pct"),
    ),
    DatasetSpec(
        "rosters",
        "raw",
        "player-team-season stint",
        ("player_id", "team_id", "season", "stint"),
        "common_team_roster",
        ("player_name",),
        season_only=True,
    ),
    DatasetSpec(
        "standings_snapshots",
        "raw",
        "team-date snapshot",
        ("team_id", "snapshot_date"),
        "league_standings",
        ("season", "season_type", "wins", "losses", "win_pct"),
        regular_season_only=True,
    ),
    DatasetSpec(
        "team_game_features",
        "processed",
        "team-game",
        ("game_id", "team_id"),
        "team_game_stats",
        ("season", "season_type", "game_date", "days_rest", "is_back_to_back"),
    ),
    DatasetSpec(
        "game_features",
        "processed",
        "game",
        ("game_id",),
        "games+team_game_stats",
        ("season", "season_type", "game_date", "home_team_id", "away_team_id"),
    ),
    DatasetSpec(
        "schedule_context_features",
        "processed",
        "team-game schedule context",
        ("game_id", "team_id"),
        "schedule+team_game_stats",
        tuple(SCHEDULE_CONTEXT_REQUIRED_COLUMNS),
        trust_column="schedule_context_source_trusted",
    ),
    DatasetSpec(
        "player_game_features",
        "processed",
        "player-game",
        ("game_id", "team_id", "player_id"),
        "player_game_stats",
        ("season", "season_type", "game_date", "minutes_last_5", "pts_last_5"),
    ),
    DatasetSpec(
        "league_season_stats",
        "processed",
        "league-season",
        ("season", "season_type"),
        "team_game_stats+player_game_stats",
        ("games", "avg_pts", "avg_fg3m", "avg_fg3a", "avg_fg3_pct", "avg_reb", "avg_tov"),
    ),
    DatasetSpec(
        "play_by_play_events",
        "raw",
        "play-by-play event",
        ("season", "season_type", "game_id", "action_number"),
        "play_by_play_v3",
        tuple(PLAY_BY_PLAY_EVENT_REQUIRED_COLUMNS),
        required=False,
        trust_column="pbp_source_trusted",
        trust_reason_column="pbp_validation_reason",
    ),
    DatasetSpec(
        "player_game_clutch_stats",
        "processed",
        "player-game clutch sample",
        ("season", "season_type", "game_id", "team_id", "player_id"),
        "play_by_play_events",
        tuple(PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS),
        required=False,
        trust_column="clutch_source_trusted",
        trust_reason_column="clutch_validation_reason",
    ),
    DatasetSpec(
        "team_game_clutch_stats",
        "processed",
        "team-game clutch sample",
        ("season", "season_type", "game_id", "team_id"),
        "play_by_play_events",
        tuple(TEAM_GAME_CLUTCH_REQUIRED_COLUMNS),
        required=False,
        trust_column="clutch_source_trusted",
        trust_reason_column="clutch_validation_reason",
    ),
    DatasetSpec(
        "team_player_on_off_summary",
        "raw",
        "team-player presence split",
        ("season", "season_type", "team_id", "player_id", "presence_state"),
        "team_player_on_off_summary",
        tuple(TEAM_PLAYER_ON_OFF_REQUIRED_COLUMNS),
        required=False,
        trust_column="coverage_trusted",
        trust_reason_column="coverage_validation_reason",
    ),
    DatasetSpec(
        "league_lineup_viz",
        "raw",
        "team-lineup threshold",
        ("season", "season_type", "team_id", "unit_size", "lineup_id", "minute_minimum"),
        "league_lineup_viz",
        tuple(LEAGUE_LINEUP_VIZ_REQUIRED_COLUMNS),
        required=False,
        trust_column="coverage_trusted",
        trust_reason_column="coverage_validation_reason",
    ),
)


def safe_season_type(season_type: str) -> str:
    return season_type.lower().replace(" ", "_")


def dataset_path(data_root: Path, spec: DatasetSpec, season: str, season_type: str) -> Path:
    filename = (
        f"{season}.csv" if spec.season_only else f"{season}_{safe_season_type(season_type)}.csv"
    )
    return data_root / spec.layer / spec.name / filename


def manifest_path(data_root: Path, season: str, season_type: str) -> Path:
    return data_root / "metadata" / MANIFEST_DIR / f"{season}_{safe_season_type(season_type)}.json"


def _value(value: Any) -> str:
    if pd.isna(value):
        return "<missing>"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().lower()


def _keys(df: pd.DataFrame, columns: tuple[str, ...]) -> set[tuple[str, ...]]:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"missing key columns: {missing}")
    return {
        tuple(_value(value) for value in row)
        for row in df[list(columns)].itertuples(index=False, name=None)
    }


def _key_hash(keys: set[tuple[str, ...]]) -> str:
    payload = "\n".join("|".join(key) for key in sorted(keys)).encode()
    return hashlib.sha256(payload).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(spec: DatasetSpec, path: Path, generation_id: str) -> dict[str, Any]:
    required_columns = tuple(
        dict.fromkeys(
            (
                *spec.key_columns,
                *spec.required_columns,
                *(() if spec.trust_column is None else (spec.trust_column,)),
                *(() if spec.trust_reason_column is None else (spec.trust_reason_column,)),
            )
        )
    )
    return {
        "name": spec.name,
        "layer": spec.layer,
        "path": str(path),
        "required": spec.required,
        "grain": spec.grain,
        "key_columns": list(spec.key_columns),
        "required_columns": list(required_columns),
        "source": spec.source,
        "generation_id": generation_id,
        "row_count": 0,
        "file_sha256": None,
        "key_set_sha256": None,
        "coverage": {
            "state": "unknown",
            "expected_keys": None,
            "observed_keys": None,
            "missing_keys": [],
            "unexpected_keys": [],
            "missing_windows": [],
        },
        "trust": {
            "state": "not_applicable",
            "trusted_rows": None,
            "total_rows": None,
            "reasons": [],
        },
        "validation": {"state": "unknown", "errors": []},
    }


def _fail(record: dict[str, Any], message: str) -> None:
    record["validation"]["state"] = "failed"
    if message not in record["validation"]["errors"]:
        record["validation"]["errors"].append(message)


def _apply_trust_validation(spec: DatasetSpec, frame: pd.DataFrame, record: dict[str, Any]) -> None:
    if not spec.trust_column:
        return
    if spec.trust_column not in frame.columns:
        _fail(record, f"trust column missing: {spec.trust_column}")
        record["trust"]["state"] = "failed"
        return
    trusted = pd.to_numeric(frame[spec.trust_column], errors="coerce").eq(1)
    reasons = []
    if spec.trust_reason_column and spec.trust_reason_column in frame.columns:
        reasons = sorted(
            reason
            for reason in frame.loc[~trusted, spec.trust_reason_column]
            .fillna("")
            .astype(str)
            .str.strip()
            .unique()
            if reason
        )
    record["trust"] = {
        "state": "trusted" if trusted.all() else "failed",
        "trusted_rows": int(trusted.sum()),
        "total_rows": len(frame),
        "reasons": reasons,
    }
    if not trusted.all():
        _fail(record, f"{int((~trusted).sum())} untrusted rows")


def _missing_detail(keys: set[tuple[str, ...]], columns: tuple[str, ...]) -> list[str]:
    return [
        ", ".join(f"{column}={value}" for column, value in zip(columns, key))
        for key in sorted(keys)
    ]


def _apply_expected_coverage(
    record: dict[str, Any],
    observed: set[tuple[str, ...]],
    expected: set[tuple[str, ...]],
    columns: tuple[str, ...],
    *,
    missing_windows: list[str] | None = None,
    allow_additional_keys: bool = False,
) -> None:
    missing = expected - observed
    unexpected = observed - expected
    failed = bool(missing or (unexpected and not allow_additional_keys))
    record["coverage"] = {
        "state": "failed" if failed else "complete",
        "expected_keys": len(expected),
        "observed_keys": len(observed & expected),
        "missing_keys": _missing_detail(missing, columns),
        "unexpected_keys": _missing_detail(unexpected, columns),
        "missing_windows": missing_windows or [],
    }
    if missing:
        _fail(record, f"coverage missing {len(missing)} requested keys")
    if unexpected and not allow_additional_keys:
        _fail(record, f"coverage includes {len(unexpected)} unexpected keys")


def apply_cross_dataset_coverage(
    frames: dict[str, pd.DataFrame],
    records: dict[str, dict[str, Any]],
    *,
    season: str | None = None,
    season_type: str | None = None,
) -> None:
    def available(name: str) -> bool:
        return name in frames and records[name]["validation"]["state"] != "failed"

    if not available("team_game_stats"):
        return
    team_games = _keys(frames["team_game_stats"], ("game_id",))
    team_keys = _keys(frames["team_game_stats"], ("game_id", "team_id"))
    player_keys = (
        _keys(frames["player_game_stats"], ("game_id", "team_id", "player_id"))
        if available("player_game_stats")
        else set()
    )

    for name in ("games", "schedule"):
        if available(name):
            _apply_expected_coverage(
                records[name], _keys(frames[name], ("game_id",)), team_games, ("game_id",)
            )
    if available("player_game_stats"):
        _apply_expected_coverage(
            records["player_game_stats"],
            {(key[0], key[1]) for key in player_keys},
            team_keys,
            ("game_id", "team_id"),
        )
    if available("player_game_starter_roles") and player_keys:
        _apply_expected_coverage(
            records["player_game_starter_roles"],
            _keys(frames["player_game_starter_roles"], ("game_id", "team_id", "player_id")),
            player_keys,
            ("game_id", "team_id", "player_id"),
        )

    expected_team_windows = {
        (*key, family, value) for key in team_keys for family, value in STANDARD_PERIOD_WINDOWS
    }
    if available("team_game_period_stats"):
        columns = ("game_id", "team_id", "period_family", "period_value")
        observed = _keys(frames["team_game_period_stats"], columns)
        missing = expected_team_windows - observed
        windows = sorted({f"{key[-2]}:{key[-1]}" for key in missing})
        _apply_expected_coverage(
            records["team_game_period_stats"],
            observed,
            expected_team_windows,
            columns,
            missing_windows=windows,
            allow_additional_keys=True,
        )

    if available("player_game_period_stats"):
        columns = ("game_id", "team_id", "player_id", "period_family", "period_value")
        expected = {
            (*player, family, value)
            for player in player_keys
            for family, value in STANDARD_PERIOD_WINDOWS
        }
        observed = _keys(frames["player_game_period_stats"], columns)
        missing = expected - observed
        windows = sorted({f"{key[-2]}:{key[-1]}" for key in missing})
        _apply_expected_coverage(
            records["player_game_period_stats"],
            observed,
            expected,
            columns,
            missing_windows=windows,
            allow_additional_keys=True,
        )

    for name, expected, columns in (
        ("team_game_features", team_keys, ("game_id", "team_id")),
        ("schedule_context_features", team_keys, ("game_id", "team_id")),
        ("game_features", team_games, ("game_id",)),
        ("player_game_features", player_keys, ("game_id", "team_id", "player_id")),
    ):
        if available(name) and expected:
            _apply_expected_coverage(records[name], _keys(frames[name], columns), expected, columns)

    team_ids = {(key[1],) for key in team_keys}
    player_ids = {(key[2],) for key in player_keys}
    player_team_ids = {(key[2], key[1]) for key in player_keys}
    for name, expected, columns, allow_additional in (
        ("team_season_advanced", team_ids, ("team_id",), False),
        ("player_season_advanced", player_ids, ("player_id",), True),
        ("rosters", player_team_ids, ("player_id", "team_id"), True),
        ("standings_snapshots", team_ids, ("team_id",), False),
    ):
        if available(name) and expected:
            _apply_expected_coverage(
                records[name],
                _keys(frames[name], columns),
                expected,
                columns,
                allow_additional_keys=allow_additional,
            )

    if available("league_season_stats") and season and season_type:
        _apply_expected_coverage(
            records["league_season_stats"],
            _keys(frames["league_season_stats"], ("season", "season_type")),
            {(_value(season), _value(season_type))},
            ("season", "season_type"),
        )

    if available("play_by_play_events"):
        _apply_expected_coverage(
            records["play_by_play_events"],
            _keys(frames["play_by_play_events"], ("game_id",)),
            team_games,
            ("game_id",),
        )


def build_slice_manifest(
    season: str,
    season_type: str,
    *,
    data_root: Path = Path("data"),
    specs: tuple[DatasetSpec, ...] = DATASET_SPECS,
    generation_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generation = generation_id or uuid.uuid4().hex
    records: dict[str, dict[str, Any]] = {}
    frames: dict[str, pd.DataFrame] = {}

    for spec in specs:
        if not spec.applies(season_type):
            continue
        path = dataset_path(data_root, spec, season, season_type)
        record = _record(spec, path, generation)
        records[spec.name] = record
        if not path.exists():
            record["validation"]["state"] = "failed" if spec.required else "unavailable"
            record["coverage"]["state"] = "failed" if spec.required else "unavailable"
            if spec.required:
                record["validation"]["errors"].append("required file missing")
            continue
        try:
            frame = pd.read_csv(path)
            missing_columns = [
                column for column in record["required_columns"] if column not in frame.columns
            ]
            if missing_columns:
                raise ValueError(f"missing required columns: {missing_columns}")
            keys = _keys(frame, spec.key_columns)
            record["row_count"] = len(frame)
            record["file_sha256"] = _file_hash(path)
            record["key_set_sha256"] = _key_hash(keys)
            record["coverage"] = {
                "state": "present",
                "expected_keys": None,
                "observed_keys": len(keys),
                "missing_keys": [],
                "unexpected_keys": [],
                "missing_windows": [],
            }
            record["validation"]["state"] = "passed"
            if len(keys) != len(frame):
                _fail(record, f"grain keys contain {len(frame) - len(keys)} duplicate rows")
            for column, expected_value in (("season", season), ("season_type", season_type)):
                if column in frame.columns:
                    observed_values = set(frame[column].map(_value))
                    if observed_values != {_value(expected_value)}:
                        _fail(record, f"{column} values do not match requested slice")
            _apply_trust_validation(spec, frame, record)
            frames[spec.name] = frame
        except Exception as exc:
            _fail(record, f"file validation failed: {exc}")
            record["coverage"]["state"] = "failed"

    apply_cross_dataset_coverage(
        frames,
        records,
        season=season,
        season_type=season_type,
    )
    failed = [name for name, record in records.items() if record["validation"]["state"] == "failed"]
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "season": season,
        "season_type": season_type,
        "generation_id": generation,
        "generated_at": generated_at or datetime.now().isoformat(timespec="seconds"),
        "validation_state": "failed" if failed else "passed",
        "validation_errors": [
            f"{name}: {error}" for name in failed for error in records[name]["validation"]["errors"]
        ],
        "datasets": list(records.values()),
    }


def validate_manifest_document(
    document: dict[str, Any], *, specs: tuple[DatasetSpec, ...] = DATASET_SPECS
) -> list[str]:
    errors: list[str] = []
    for field in ("season", "season_type", "generated_at", "validation_state"):
        if not document.get(field):
            errors.append(f"missing {field}")
    if document.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("unsupported or missing schema_version")
    generation = str(document.get("generation_id") or "")
    if not generation:
        errors.append("missing generation_id")
    datasets = document.get("datasets")
    if not isinstance(datasets, list):
        return [*errors, "datasets must be a list"]
    names: set[str] = set()
    applicable_specs = {
        spec.name: spec for spec in specs if spec.applies(str(document.get("season_type")))
    }
    for record in datasets:
        if not isinstance(record, dict):
            errors.append("dataset record must be an object")
            continue
        name = str(record.get("name") or "")
        if not name or name in names:
            errors.append(f"duplicate or missing dataset name: {name!r}")
        names.add(name)
        if record.get("generation_id") != generation:
            errors.append(f"{name}: generation mismatch")
        for field in (
            "layer",
            "path",
            "required",
            "source",
            "grain",
            "key_columns",
            "required_columns",
            "row_count",
            "key_set_sha256",
            "file_sha256",
            "coverage",
            "trust",
            "validation",
        ):
            if field not in record:
                errors.append(f"{name}: missing field {field}")
        spec = applicable_specs.get(name)
        validation = record.get("validation")
        trust = record.get("trust")
        coverage = record.get("coverage")
        if not isinstance(validation, dict):
            errors.append(f"{name}: validation must be an object")
            validation = {}
        if not isinstance(trust, dict):
            errors.append(f"{name}: trust must be an object")
            trust = {}
        if not isinstance(coverage, dict):
            errors.append(f"{name}: coverage must be an object")
        state = validation.get("state")
        if spec and spec.required and state != "passed":
            errors.append(f"{name}: required dataset validation is not passed")
        if spec and not spec.required and state not in {"passed", "unavailable"}:
            errors.append(f"{name}: optional dataset validation is neither passed nor unavailable")
        if spec and state == "passed" and spec.trust_column:
            if trust.get("state") != "trusted":
                errors.append(f"{name}: trust state is not trusted")
        if state == "passed":
            if not isinstance(record.get("row_count"), int) or record["row_count"] < 0:
                errors.append(f"{name}: row_count must be a nonnegative integer")
            for field in ("key_set_sha256", "file_sha256"):
                value = record.get(field)
                if not isinstance(value, str) or len(value) != 64:
                    errors.append(f"{name}: invalid {field}")
    for name in sorted(applicable_specs.keys() - names):
        errors.append(f"missing dataset record: {name}")
    for name in sorted(names - applicable_specs.keys()):
        errors.append(f"unexpected dataset record: {name}")
    return errors


def write_slice_manifest(document: dict[str, Any], *, data_root: Path = Path("data")) -> Path:
    path = manifest_path(data_root, document["season"], document["season_type"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def inspect_slice_manifest(
    season: str,
    season_type: str,
    *,
    data_root: Path = Path("data"),
    specs: tuple[DatasetSpec, ...] = DATASET_SPECS,
    verify_files: bool = True,
) -> dict[str, Any]:
    path = manifest_path(data_root, season, season_type)
    if not data_exists(path):
        return {
            "validation_state": "unknown",
            "generation_id": None,
            "errors": ["versioned manifest missing"],
            "path": str(path),
            "manifest": None,
        }
    try:
        document = json.loads(data_path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "validation_state": "failed",
            "generation_id": None,
            "errors": [f"manifest is corrupt: {exc}"],
            "path": str(path),
            "manifest": None,
        }
    if not isinstance(document, dict):
        return {
            "validation_state": "failed",
            "generation_id": None,
            "errors": ["manifest root must be an object"],
            "path": str(path),
            "manifest": None,
        }
    errors = validate_manifest_document(document, specs=specs)
    if document.get("season") != season:
        errors.append("manifest season does not match requested slice")
    if document.get("season_type") != season_type:
        errors.append("manifest season_type does not match requested slice")
    if document.get("validation_state") != "passed":
        errors.extend(
            document.get("validation_errors") or ["manifest validation_state is not passed"]
        )
    if verify_files:
        datasets = document.get("datasets")
        for record in datasets if isinstance(datasets, list) else []:
            if not isinstance(record, dict):
                continue
            validation = record.get("validation")
            if isinstance(validation, dict) and validation.get("state") == "unavailable":
                continue
            file_path = Path(record.get("path", ""))
            try:
                if not record.get("path") or not data_exists(file_path):
                    errors.append(f"{record.get('name')}: manifested file missing")
                    continue
                expected = record.get("file_sha256")
                if not expected or _file_hash(data_path(file_path)) != expected:
                    errors.append(f"{record.get('name')}: checksum mismatch")
            except Exception as exc:
                errors.append(f"{record.get('name')}: file inspection failed: {exc}")
    return {
        "validation_state": "failed" if errors else "passed",
        "generation_id": document.get("generation_id"),
        "errors": list(dict.fromkeys(errors)),
        "path": str(path),
        "manifest": document,
    }


def validate_raw_coverage(frames: dict[str, pd.DataFrame]) -> None:
    generation = "raw-validation"
    specs = tuple(spec for spec in DATASET_SPECS if spec.name in frames)
    records: dict[str, dict[str, Any]] = {}
    for spec in specs:
        record = _record(spec, Path(spec.name), generation)
        record["validation"]["state"] = "passed"
        record["coverage"]["state"] = "present"
        _apply_trust_validation(spec, frames[spec.name], record)
        records[spec.name] = record
    apply_cross_dataset_coverage(frames, records)
    errors = [
        f"{name}: {error}"
        for name, record in records.items()
        for error in record["validation"]["errors"]
    ]
    if errors:
        raise ValueError("Cross-dataset coverage validation failed: " + "; ".join(errors))
