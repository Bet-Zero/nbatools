"""Data freshness utilities for the nbatools engine.

Provides ``compute_current_through()`` — a local-first, file-based utility
that determines the latest date the loaded data is complete through.

This follows the definition in ``docs/data_freshness_plan.md``:

    current through = the latest game_date in the games CSV where
    is_final = 1, provided the backfill manifest reports both
    raw_complete = 1 and processed_complete = 1 for that season/type.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nbatools.commands.data_utils import normalize_season_type

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
