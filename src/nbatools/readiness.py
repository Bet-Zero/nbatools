"""Schedule-aware release readiness for the public query service.

Freshness is descriptive UI metadata.  Readiness is the stricter deployment
gate: it requires a coherent immutable runtime generation, trusted required
dataset slices, and schedule-aware coverage for the current season.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd

from nbatools.commands._seasons import LATEST_REGULAR_SEASON
from nbatools.commands.data_utils import normalize_season_type
from nbatools.commands.freshness import manifest_entry, read_refresh_log
from nbatools.data_source import (
    LEGACY_GENERATION,
    current_data_generation,
    data_exists,
    data_generation_context,
    data_read_csv,
    data_read_text,
)

MAX_ACTIVE_LAG_HOURS = 24
RELEASE_EXCEPTION_OWNER = "John Matthew, project owner"
READINESS_EXCEPTION_REASON_ENV = "NBATOOLS_READINESS_EXCEPTION_REASON"
READINESS_EXCEPTION_CREATED_AT_ENV = "NBATOOLS_READINESS_EXCEPTION_CREATED_AT"
READINESS_EXCEPTION_EXPIRES_AT_ENV = "NBATOOLS_READINESS_EXCEPTION_EXPIRES_AT"


class SeasonState(StrEnum):
    """Schedule-aware state of the latest supported season."""

    ACTIVE = "active_season"
    POSTSEASON_COMPLETE = "postseason_complete"
    OFFSEASON = "offseason"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReadinessBlocker:
    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class SliceEvidence:
    season: str
    season_type: str
    trusted: bool
    validation_state: str
    generation_id: str | None
    current_through: str | None
    expected_current_through: str | None
    schedule_complete: bool
    postseason_complete: bool = False
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "season_type": self.season_type,
            "trusted": self.trusted,
            "validation_state": self.validation_state,
            "generation_id": self.generation_id,
            "current_through": self.current_through,
            "expected_current_through": self.expected_current_through,
            "schedule_complete": self.schedule_complete,
            "postseason_complete": self.postseason_complete,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class ReadinessSnapshot:
    active_generation: str
    immutable_generation: bool
    generation_error: str | None
    regular_season: SliceEvidence
    playoffs: SliceEvidence | None
    last_refresh_ok: bool | None = None
    last_refresh_error: str | None = None


@dataclass(frozen=True)
class ReadinessException:
    applied: bool = False
    owner: str = RELEASE_EXCEPTION_OWNER
    reason: str | None = None
    created_at: str | None = None
    expires_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "owner": self.owner,
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "error": self.error,
        }


@dataclass(frozen=True)
class ReadinessInfo:
    ready: bool
    status: str
    checked_at: str
    season: str
    season_state: SeasonState
    max_active_lag_hours: int
    active_generation: str
    immutable_generation: bool
    release_exception_owner: str
    slices: tuple[SliceEvidence, ...] = ()
    blockers: tuple[ReadinessBlocker, ...] = ()
    exception: ReadinessException = field(default_factory=ReadinessException)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "checked_at": self.checked_at,
            "season": self.season,
            "season_state": self.season_state.value,
            "max_active_lag_hours": self.max_active_lag_hours,
            "active_generation": self.active_generation,
            "immutable_generation": self.immutable_generation,
            "release_exception_owner": self.release_exception_owner,
            "slices": [item.to_dict() for item in self.slices],
            "blockers": [item.to_dict() for item in self.blockers],
            "exception": self.exception.to_dict(),
        }


def evaluate_readiness(
    snapshot: ReadinessSnapshot,
    *,
    checked_at: datetime,
    env: dict[str, str] | None = None,
) -> ReadinessInfo:
    """Apply the approved readiness policy to collected runtime evidence."""
    blockers: list[ReadinessBlocker] = []
    regular = snapshot.regular_season
    playoffs = snapshot.playoffs

    if not snapshot.immutable_generation:
        blockers.append(
            ReadinessBlocker(
                "immutable_generation_required",
                snapshot.generation_error
                or "The runtime is not pinned to a validated immutable generation.",
            )
        )
    if not regular.trusted:
        blockers.append(
            ReadinessBlocker(
                "regular_season_slice_untrusted",
                _slice_error_detail(regular),
            )
        )

    season_state = _season_state(snapshot)
    if season_state is SeasonState.UNKNOWN:
        blockers.append(
            ReadinessBlocker(
                "season_state_unknown",
                "Trusted schedule evidence cannot establish active, completed-postseason, "
                "or offseason state.",
            )
        )

    if playoffs is not None and not playoffs.trusted:
        blockers.append(
            ReadinessBlocker(
                "playoff_slice_untrusted",
                _slice_error_detail(playoffs),
            )
        )

    active_slice = playoffs if playoffs is not None and playoffs.trusted else regular
    if season_state is SeasonState.ACTIVE and active_slice.trusted:
        if active_slice.expected_current_through is None:
            blockers.append(
                ReadinessBlocker(
                    "active_schedule_coverage_unknown",
                    "No trusted scheduled game old enough to evaluate the 24-hour lag budget.",
                )
            )
        elif (
            active_slice.current_through is None
            or active_slice.current_through < active_slice.expected_current_through
        ):
            blockers.append(
                ReadinessBlocker(
                    "active_season_lag",
                    "Trusted game coverage is behind the latest scheduled game outside the "
                    "24-hour grace window "
                    f"(expected {active_slice.expected_current_through}, actual "
                    f"{active_slice.current_through or 'unknown'}).",
                )
            )

    if snapshot.last_refresh_ok is False:
        blockers.append(
            ReadinessBlocker(
                "last_refresh_failed",
                snapshot.last_refresh_error or "The last refresh attempt failed.",
            )
        )

    exception = _read_exception(checked_at, env or dict(os.environ))
    if exception.applied:
        non_lag = [item for item in blockers if item.code != "active_season_lag"]
        if season_state is SeasonState.ACTIVE and len(non_lag) < len(blockers):
            blockers = non_lag
        else:
            exception = ReadinessException(
                owner=exception.owner,
                reason=exception.reason,
                created_at=exception.created_at,
                expires_at=exception.expires_at,
                error=(
                    "Exceptions may waive only active-season lag and cannot waive other blockers."
                ),
            )

    ready = not blockers
    return ReadinessInfo(
        ready=ready,
        status="ready" if ready else "not_ready",
        checked_at=_iso_z(checked_at),
        season=regular.season,
        season_state=season_state,
        max_active_lag_hours=MAX_ACTIVE_LAG_HOURS,
        active_generation=snapshot.active_generation,
        immutable_generation=snapshot.immutable_generation,
        release_exception_owner=RELEASE_EXCEPTION_OWNER,
        slices=tuple(item for item in (regular, playoffs) if item is not None),
        blockers=tuple(blockers),
        exception=exception,
    )


def build_readiness_info(
    *,
    season: str = LATEST_REGULAR_SEASON,
    data_root: Path = Path("data"),
    checked_at: datetime | None = None,
    env: dict[str, str] | None = None,
) -> ReadinessInfo:
    """Collect one pinned runtime snapshot and evaluate release readiness."""
    now = _as_utc(checked_at or datetime.now(UTC))
    try:
        with data_generation_context() as generation:
            immutable, generation_error = _inspect_runtime_generation(generation)
            regular = _collect_slice(season, "Regular Season", data_root, now)
            playoffs = None
            if _slice_files_exist(season, "Playoffs", data_root):
                playoffs = _collect_slice(season, "Playoffs", data_root, now)
            refresh = read_refresh_log(data_root) or {}
            snapshot = ReadinessSnapshot(
                active_generation=generation,
                immutable_generation=immutable,
                generation_error=generation_error,
                regular_season=regular,
                playoffs=playoffs,
                last_refresh_ok=refresh.get("success"),
                last_refresh_error=refresh.get("error"),
            )
    except Exception as exc:
        unknown = SliceEvidence(
            season=season,
            season_type="Regular Season",
            trusted=False,
            validation_state="unknown",
            generation_id=None,
            current_through=None,
            expected_current_through=None,
            schedule_complete=False,
            errors=(f"{type(exc).__name__}: {exc}",),
        )
        snapshot = ReadinessSnapshot(
            active_generation=_safe_generation_name(),
            immutable_generation=False,
            generation_error=f"Runtime generation inspection failed: {type(exc).__name__}: {exc}",
            regular_season=unknown,
            playoffs=None,
        )
    return evaluate_readiness(snapshot, checked_at=now, env=env)


def _collect_slice(
    season: str,
    season_type: str,
    data_root: Path,
    checked_at: datetime,
) -> SliceEvidence:
    entry = manifest_entry(season, season_type, data_root) or {}
    trusted = (
        entry.get("validation_state") == "passed"
        and bool(entry.get("raw_complete"))
        and bool(entry.get("processed_complete"))
    )
    errors = tuple(str(item) for item in entry.get("validation_errors", []))
    schedule = _read_slice_csv(data_root, "raw", "schedule", season, season_type)
    games = _read_slice_csv(data_root, "raw", "games", season, season_type)
    expected = _expected_current_through(schedule, checked_at)
    actual = _actual_current_through(games)
    schedule_complete = _all_schedule_rows_final(schedule)
    postseason_complete = False
    if season_type == "Playoffs" and trusted and schedule_complete:
        team_stats = _read_slice_csv(data_root, "raw", "team_game_stats", season, season_type)
        postseason_complete = _postseason_complete(schedule, games, team_stats)
    return SliceEvidence(
        season=season,
        season_type=season_type,
        trusted=trusted,
        validation_state=str(entry.get("validation_state", "unknown")),
        generation_id=entry.get("generation_id"),
        current_through=actual if trusted else None,
        expected_current_through=expected if trusted else None,
        schedule_complete=schedule_complete if trusted else False,
        postseason_complete=postseason_complete,
        errors=errors,
    )


def _season_state(snapshot: ReadinessSnapshot) -> SeasonState:
    regular = snapshot.regular_season
    playoffs = snapshot.playoffs
    if not regular.trusted:
        return SeasonState.UNKNOWN
    if playoffs is not None:
        if not playoffs.trusted:
            return SeasonState.UNKNOWN
        if playoffs.postseason_complete:
            return (
                SeasonState.OFFSEASON
                if snapshot.immutable_generation
                else SeasonState.POSTSEASON_COMPLETE
            )
        return SeasonState.ACTIVE
    if regular.schedule_complete:
        return SeasonState.UNKNOWN
    return SeasonState.ACTIVE


def _inspect_runtime_generation(generation: str) -> tuple[bool, str | None]:
    if generation == LEGACY_GENERATION:
        return False, "The active runtime uses mutable legacy canonical paths."
    path = Path("data/metadata/generation_manifest.json")
    if not data_exists(path):
        return False, "The active immutable generation manifest is missing."
    try:
        document = json.loads(data_read_text(path))
    except Exception as exc:
        return False, f"The active generation manifest is unreadable: {exc}"
    if not isinstance(document, dict):
        return False, "The active generation manifest is not a JSON object."
    if document.get("schema_version") != 1:
        return False, "The active generation manifest schema is unsupported."
    if document.get("generation_id") != generation:
        return False, "The active pointer and generation manifest identifiers differ."
    if not isinstance(document.get("files"), list) or not document["files"]:
        return False, "The active generation manifest has no immutable file inventory."
    return True, None


def _slice_files_exist(season: str, season_type: str, data_root: Path) -> bool:
    safe = normalize_season_type(season_type)
    return data_exists(data_root / "raw" / "schedule" / f"{season}_{safe}.csv") or data_exists(
        data_root / "raw" / "games" / f"{season}_{safe}.csv"
    )


def _read_slice_csv(
    data_root: Path,
    layer: str,
    dataset: str,
    season: str,
    season_type: str,
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    path = data_root / layer / dataset / f"{season}_{safe}.csv"
    if not data_exists(path):
        return pd.DataFrame()
    try:
        return data_read_csv(path)
    except Exception:
        return pd.DataFrame()


def _expected_current_through(schedule: pd.DataFrame, checked_at: datetime) -> str | None:
    if schedule.empty or "game_date" not in schedule.columns:
        return None
    timestamps = pd.to_datetime(schedule.get("game_datetime"), errors="coerce", utc=True)
    fallback_dates = pd.to_datetime(schedule["game_date"], errors="coerce", utc=True)
    if timestamps is None:
        timestamps = fallback_dates
    else:
        timestamps = timestamps.fillna(fallback_dates)
    cutoff = pd.Timestamp(checked_at - timedelta(hours=MAX_ACTIVE_LAG_HOURS))
    eligible = fallback_dates.loc[timestamps <= cutoff].dropna()
    if eligible.empty:
        return None
    return str(eligible.max().date())


def _actual_current_through(games: pd.DataFrame) -> str | None:
    if games.empty or "game_date" not in games.columns or "is_final" not in games.columns:
        return None
    final = games.loc[pd.to_numeric(games["is_final"], errors="coerce") == 1]
    dates = pd.to_datetime(final["game_date"], errors="coerce").dropna()
    return str(dates.max().date()) if not dates.empty else None


def _all_schedule_rows_final(schedule: pd.DataFrame) -> bool:
    if schedule.empty or "status" not in schedule.columns:
        return False
    statuses = schedule["status"].fillna("").astype(str).str.strip().str.lower()
    return bool((statuses == "final").all())


def _postseason_complete(
    schedule: pd.DataFrame,
    games: pd.DataFrame,
    team_stats: pd.DataFrame,
) -> bool:
    required = {"game_id", "team_id", "wl"}
    if schedule.empty or games.empty or team_stats.empty or not required.issubset(team_stats):
        return False
    schedule_ids = set(schedule["game_id"].astype(str))
    final_game_ids = set(
        games.loc[pd.to_numeric(games.get("is_final"), errors="coerce") == 1, "game_id"].astype(str)
    )
    if not schedule_ids or not schedule_ids.issubset(final_game_ids):
        return False
    ids = team_stats["game_id"].astype(str)
    finals = team_stats.loc[ids.str.len().ge(8) & ids.str.slice(3, 6).eq("004")]
    winners = finals.loc[finals["wl"].astype(str).str.upper().eq("W")]
    if winners.empty:
        return False
    return bool(winners.groupby("team_id").size().max() >= 4)


def _read_exception(checked_at: datetime, env: dict[str, str]) -> ReadinessException:
    values = {
        "reason": env.get(READINESS_EXCEPTION_REASON_ENV, "").strip(),
        "created_at": env.get(READINESS_EXCEPTION_CREATED_AT_ENV, "").strip(),
        "expires_at": env.get(READINESS_EXCEPTION_EXPIRES_AT_ENV, "").strip(),
    }
    if not any(values.values()):
        return ReadinessException()
    if not all(values.values()):
        return ReadinessException(
            error="A readiness exception requires reason, created_at, and expires_at."
        )
    try:
        created = _parse_datetime(values["created_at"])
        expires = _parse_datetime(values["expires_at"])
    except ValueError as exc:
        return ReadinessException(
            reason=values["reason"],
            created_at=values["created_at"],
            expires_at=values["expires_at"],
            error=str(exc),
        )
    error = None
    if expires <= checked_at:
        error = "The readiness exception has expired."
    elif expires > created + timedelta(hours=MAX_ACTIVE_LAG_HOURS):
        error = "The readiness exception exceeds the 24-hour maximum."
    elif created > checked_at:
        error = "The readiness exception creation time is in the future."
    return ReadinessException(
        applied=error is None,
        reason=values["reason"],
        created_at=_iso_z(created),
        expires_at=_iso_z(expires),
        error=error,
    )


def _parse_datetime(value: str) -> datetime:
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError as exc:
        raise ValueError("Readiness exception timestamps must be ISO-8601 values.") from exc


def _slice_error_detail(item: SliceEvidence) -> str:
    return "; ".join(item.errors) or f"Validation state is {item.validation_state}."


def _safe_generation_name() -> str:
    try:
        return current_data_generation()
    except Exception:
        return "unknown"


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _iso_z(value: datetime) -> str:
    return _as_utc(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")
