"""Data freshness utilities for the nbatools engine.

Provides ``compute_current_through()`` — a local-first, file-based utility
that determines the latest date the loaded data is complete through.

This follows the definition in ``docs/planning/data_freshness_plan.md``:

    current through = the latest game_date in the games CSV where
    is_final = 1, provided the backfill manifest reports both
    raw_complete = 1 and processed_complete = 1 for that season/type.

Status semantics
----------------
``FreshnessStatus`` captures four explicit states:

- **fresh**: manifest complete, current_through is recent (within threshold).
- **stale**: manifest complete, but current_through is older than threshold.
- **unknown**: manifest or games data missing — cannot determine freshness.
- **failed**: last refresh attempt recorded a failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path

import pandas as pd

from nbatools.commands.data_utils import normalize_season_type

# ---------------------------------------------------------------------------
# Status semantics
# ---------------------------------------------------------------------------

# A data snapshot is considered stale if it is older than this many days.
_STALE_THRESHOLD_DAYS = 3


class FreshnessStatus(StrEnum):
    """Explicit freshness state for data trustworthiness."""

    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"
    FAILED = "failed"


@dataclass
class SeasonFreshness:
    """Freshness detail for a single season / season_type pair."""

    season: str
    season_type: str
    status: FreshnessStatus
    current_through: str | None = None
    raw_complete: bool = False
    processed_complete: bool = False
    loaded_at: str | None = None


@dataclass
class FreshnessInfo:
    """Structured freshness report suitable for API/UI consumption."""

    status: FreshnessStatus
    current_through: str | None = None
    checked_at: str | None = None
    seasons: list[SeasonFreshness] = field(default_factory=list)
    last_refresh_ok: bool | None = None
    last_refresh_at: str | None = None
    last_refresh_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "current_through": self.current_through,
            "checked_at": self.checked_at,
            "seasons": [
                {
                    "season": s.season,
                    "season_type": s.season_type,
                    "status": s.status.value,
                    "current_through": s.current_through,
                    "raw_complete": s.raw_complete,
                    "processed_complete": s.processed_complete,
                    "loaded_at": s.loaded_at,
                }
                for s in self.seasons
            ],
            "last_refresh_ok": self.last_refresh_ok,
            "last_refresh_at": self.last_refresh_at,
            "last_refresh_error": self.last_refresh_error,
        }


def classify_freshness(
    current_through: str | None,
    manifest_complete: bool,
    stale_days: int = _STALE_THRESHOLD_DAYS,
    reference_date: date | None = None,
) -> FreshnessStatus:
    """Classify a single season's freshness state.

    Parameters
    ----------
    current_through : str | None
        ISO date string (e.g. "2026-04-10"), or None.
    manifest_complete : bool
        Whether both raw_complete and processed_complete are True.
    stale_days : int
        Number of days before data is considered stale.
    reference_date : date | None
        Date to compare against; defaults to today.
    """
    if not manifest_complete or current_through is None:
        return FreshnessStatus.UNKNOWN

    ref = reference_date or date.today()
    try:
        ct_date = date.fromisoformat(current_through)
    except (ValueError, TypeError):
        return FreshnessStatus.UNKNOWN

    if (ref - ct_date) > timedelta(days=stale_days):
        return FreshnessStatus.STALE

    return FreshnessStatus.FRESH


# Default data root; tests can override via the ``data_root`` parameter.
_DATA_ROOT = Path("data")


def _manifest_complete(
    season: str,
    season_type: str,
    data_root: Path = _DATA_ROOT,
) -> bool:
    """Return True when the backfill manifest says this season/type is fully loaded."""
    manifest_path = data_root / "metadata" / "backfill_manifest.csv"
    if not manifest_path.exists():
        return False
    try:
        df = pd.read_csv(manifest_path)
    except Exception:
        return False

    mask = (df["season"] == season) & (df["season_type"] == season_type)
    rows = df.loc[mask]
    if rows.empty:
        return False

    row = rows.iloc[0]
    return bool(row.get("raw_complete") == 1 and row.get("processed_complete") == 1)


def compute_current_through(
    season: str,
    season_type: str = "Regular Season",
    data_root: Path = _DATA_ROOT,
) -> str | None:
    """Return the latest final game_date for *season*/*season_type*, or None.

    Returns ``None`` when:
    - the games CSV does not exist
    - the manifest does not confirm completeness
    - the file has no rows with ``is_final == 1``
    """
    if not _manifest_complete(season, season_type, data_root):
        return None

    safe = normalize_season_type(season_type)
    games_path = data_root / "raw" / "games" / f"{season}_{safe}.csv"
    if not games_path.exists():
        return None

    try:
        df = pd.read_csv(games_path)
    except Exception:
        return None

    if "is_final" not in df.columns or "game_date" not in df.columns:
        return None

    final = df.loc[df["is_final"] == 1]
    if final.empty:
        return None

    dates = pd.to_datetime(final["game_date"], errors="coerce").dropna()
    if dates.empty:
        return None

    return str(dates.max().date())


def compute_current_through_for_seasons(
    seasons: list[str],
    season_type: str = "Regular Season",
    data_root: Path = _DATA_ROOT,
) -> str | None:
    """Return the latest current_through across multiple seasons, or None.

    If *any* season in the list lacks manifest confirmation, returns None
    for that season but still reports the max across those that are confirmed.
    Returns None only when no season has a determinable current_through.
    """
    latest: str | None = None
    for season in seasons:
        ct = compute_current_through(season, season_type, data_root)
        if ct is not None:
            if latest is None or ct > latest:
                latest = ct
    return latest


def season_data_available(
    season: str,
    season_type: str = "Regular Season",
    dataset: str = "player_game_stats",
    data_root: Path = _DATA_ROOT,
) -> bool:
    """Return True if the raw data file exists for this season/type/dataset."""
    safe = normalize_season_type(season_type)
    path = data_root / "raw" / dataset / f"{season}_{safe}.csv"
    return path.exists()


def manifest_entry(
    season: str,
    season_type: str,
    data_root: Path = _DATA_ROOT,
) -> dict | None:
    """Return the manifest row for a season/type as a dict, or None."""
    manifest_path = data_root / "metadata" / "backfill_manifest.csv"
    if not manifest_path.exists():
        return None
    try:
        df = pd.read_csv(manifest_path)
    except Exception:
        return None
    mask = (df["season"] == season) & (df["season_type"] == season_type)
    rows = df.loc[mask]
    if rows.empty:
        return None
    row = rows.iloc[0]
    return {
        "season": season,
        "season_type": season_type,
        "raw_complete": bool(row.get("raw_complete") == 1),
        "processed_complete": bool(row.get("processed_complete") == 1),
        "loaded_at": str(row.get("loaded_at", "")),
    }


def freshness_report(
    seasons: list[str],
    season_type: str = "Regular Season",
    data_root: Path = _DATA_ROOT,
) -> dict:
    """Build a freshness report across seasons.

    Returns a dict with per-season current_through, manifest status,
    and an overall current_through (the latest across all confirmed seasons).
    """
    entries = []
    overall_ct: str | None = None

    for season in seasons:
        ct = compute_current_through(season, season_type, data_root)
        entry = manifest_entry(season, season_type, data_root)
        entries.append(
            {
                "season": season,
                "season_type": season_type,
                "current_through": ct,
                "manifest": entry,
            }
        )
        if ct is not None:
            if overall_ct is None or ct > overall_ct:
                overall_ct = ct

    return {
        "overall_current_through": overall_ct,
        "season_type": season_type,
        "seasons": entries,
    }


# ---------------------------------------------------------------------------
# Refresh log — lightweight file-based record of last refresh outcome
# ---------------------------------------------------------------------------

_REFRESH_LOG_FILENAME = "last_refresh.json"


def _refresh_log_path(data_root: Path = _DATA_ROOT) -> Path:
    return data_root / "metadata" / _REFRESH_LOG_FILENAME


def write_refresh_log(
    success: bool,
    timestamp: str,
    *,
    error: str | None = None,
    data_root: Path = _DATA_ROOT,
) -> None:
    """Persist last-refresh outcome to a small JSON file."""
    import json

    path = _refresh_log_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"success": success, "timestamp": timestamp, "error": error}
    path.write_text(json.dumps(payload, indent=2) + "\n")


def read_refresh_log(data_root: Path = _DATA_ROOT) -> dict | None:
    """Read last-refresh log, or None if unavailable."""
    import json

    path = _refresh_log_path(data_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Structured freshness report (API-oriented)
# ---------------------------------------------------------------------------


def build_freshness_info(
    seasons: list[str] | None = None,
    season_type: str = "Regular Season",
    data_root: Path = _DATA_ROOT,
    reference_date: date | None = None,
) -> FreshnessInfo:
    """Build a structured ``FreshnessInfo`` for the API/UI.

    If *seasons* is None, defaults to the latest regular season.
    """
    from datetime import datetime

    from nbatools.commands._seasons import LATEST_REGULAR_SEASON

    if seasons is None:
        seasons = [LATEST_REGULAR_SEASON]

    season_details: list[SeasonFreshness] = []
    overall_ct: str | None = None

    for season in seasons:
        ct = compute_current_through(season, season_type, data_root)
        entry = manifest_entry(season, season_type, data_root)

        raw_ok = bool(entry and entry.get("raw_complete"))
        proc_ok = bool(entry and entry.get("processed_complete"))
        manifest_ok = raw_ok and proc_ok
        loaded_at = entry.get("loaded_at") if entry else None

        status = classify_freshness(
            ct,
            manifest_ok,
            reference_date=reference_date,
        )
        season_details.append(
            SeasonFreshness(
                season=season,
                season_type=season_type,
                status=status,
                current_through=ct,
                raw_complete=raw_ok,
                processed_complete=proc_ok,
                loaded_at=loaded_at,
            )
        )

        if ct is not None:
            if overall_ct is None or ct > overall_ct:
                overall_ct = ct

    # Overall status: worst of season statuses
    if any(s.status == FreshnessStatus.FAILED for s in season_details):
        overall = FreshnessStatus.FAILED
    elif any(s.status == FreshnessStatus.UNKNOWN for s in season_details):
        overall = FreshnessStatus.UNKNOWN
    elif any(s.status == FreshnessStatus.STALE for s in season_details):
        overall = FreshnessStatus.STALE
    else:
        overall = FreshnessStatus.FRESH

    # Incorporate refresh log
    log = read_refresh_log(data_root)
    last_ok: bool | None = None
    last_at: str | None = None
    last_err: str | None = None
    if log:
        last_ok = log.get("success")
        last_at = log.get("timestamp")
        last_err = log.get("error")
        # If last refresh failed, override overall to FAILED
        if last_ok is False:
            overall = FreshnessStatus.FAILED

    return FreshnessInfo(
        status=overall,
        current_through=overall_ct,
        checked_at=datetime.now().isoformat(timespec="seconds"),
        seasons=season_details,
        last_refresh_ok=last_ok,
        last_refresh_at=last_at,
        last_refresh_error=last_err,
    )
