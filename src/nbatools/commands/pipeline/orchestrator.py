"""Refresh orchestration pipeline for nbatools data.

Provides in-process, deterministic refresh workflows that:
- pull raw source data for one or more seasons
- run validation
- build derived/processed datasets
- update the backfill manifest
- compute and return current_through

All workflows return structured ``PipelineResult`` objects with
stage-by-stage status, so callers (CLI, tests, future automation)
can inspect exactly what happened.

Rebuild order follows ``docs/planning/data_freshness_plan.md`` §4:
  1. Raw pulls (games → schedule → rosters → team_game_stats →
     player_game_stats → player_game_starter_roles → game_period_stats →
     standings_snapshots → team_season_advanced → player_season_advanced)
  2. Validation (validate_raw)
  3. Processed builds (team_game_features → game_features →
     schedule_context_features → player_game_features → league_season_stats)
  4. Manifest update
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from nbatools.commands._seasons import (
    LATEST_PLAYOFF_SEASON,
    LATEST_REGULAR_SEASON,
    int_to_season,
    season_to_int,
)
from nbatools.commands.freshness import compute_current_through

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class StageStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Outcome of a single pipeline stage."""

    name: str
    status: StageStatus
    error: str | None = None
    duration_ms: int | None = None


@dataclass
class SeasonResult:
    """Outcome of refreshing one season/season_type pair."""

    season: str
    season_type: str
    stages: list[StageResult] = field(default_factory=list)
    current_through: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    @property
    def success(self) -> bool:
        return all(s.status != StageStatus.FAILED for s in self.stages)

    @property
    def failed_stages(self) -> list[StageResult]:
        return [s for s in self.stages if s.status == StageStatus.FAILED]


@dataclass
class PipelineResult:
    """Aggregate outcome of a pipeline run across one or more seasons."""

    mode: str
    seasons: list[SeasonResult] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None

    @property
    def success(self) -> bool:
        return all(s.success for s in self.seasons)

    @property
    def failed_seasons(self) -> list[SeasonResult]:
        return [s for s in self.seasons if not s.success]

    @property
    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        lines.append(f"Pipeline mode: {self.mode}")
        lines.append(f"Started: {self.started_at}")
        lines.append(f"Finished: {self.finished_at}")
        lines.append(f"Seasons processed: {len(self.seasons)}")
        ok = sum(1 for s in self.seasons if s.success)
        fail = len(self.seasons) - ok
        lines.append(f"Succeeded: {ok}  Failed: {fail}")
        if self.failed_seasons:
            lines.append("Failed seasons:")
            for sr in self.failed_seasons:
                for st in sr.failed_stages:
                    lines.append(f"  {sr.season} ({sr.season_type}) — {st.name}: {st.error}")
        for sr in self.seasons:
            if sr.current_through:
                lines.append(
                    f"  {sr.season} ({sr.season_type}) current_through: {sr.current_through}"
                )
        return lines


# ---------------------------------------------------------------------------
# Stage runners — each calls the underlying module directly
# ---------------------------------------------------------------------------


def _run_stage(name: str, fn, *args, **kwargs) -> StageResult:
    """Execute a single stage function, capturing errors."""
    import time

    t0 = time.monotonic()
    try:
        fn(*args, **kwargs)
        elapsed = int((time.monotonic() - t0) * 1000)
        return StageResult(name=name, status=StageStatus.SUCCESS, duration_ms=elapsed)
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        return StageResult(
            name=name,
            status=StageStatus.FAILED,
            error=f"{type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


def _raw_pull_stages(
    season: str,
    season_type: str,
    *,
    allow_no_data_skip: bool = False,
) -> list[StageResult]:
    """Run all raw pull stages in the correct order.

    Returns a list of StageResults.  If ``allow_no_data_skip`` is True and
    ``pull_games`` raises a "No data returned" error, the remaining raw stages
    are skipped cleanly (useful for upcoming playoff seasons).
    """
    from nbatools.commands.pipeline.pull_game_period_stats import run as pull_game_period_stats
    from nbatools.commands.pipeline.pull_games import run as pull_games
    from nbatools.commands.pipeline.pull_player_game_starter_roles import (
        run as pull_player_game_starter_roles,
    )
    from nbatools.commands.pipeline.pull_player_game_stats import run as pull_player_game_stats
    from nbatools.commands.pipeline.pull_player_season_advanced import (
        run as pull_player_season_advanced,
    )
    from nbatools.commands.pipeline.pull_rosters import run as pull_rosters
    from nbatools.commands.pipeline.pull_schedule import run as pull_schedule
    from nbatools.commands.pipeline.pull_standings_snapshots import run as pull_standings
    from nbatools.commands.pipeline.pull_team_game_stats import run as pull_team_game_stats
    from nbatools.commands.pipeline.pull_team_season_advanced import (
        run as pull_team_season_advanced,
    )

    results: list[StageResult] = []

    # 1. pull-games (gate — if no data, skip rest)
    games_result = _run_stage("pull_games", pull_games, season, season_type)
    if games_result.status == StageStatus.FAILED:
        if allow_no_data_skip and games_result.error and "No data returned" in games_result.error:
            games_result = StageResult(
                name="pull_games",
                status=StageStatus.SKIPPED,
                error="No data available yet — skipping season cleanly",
                duration_ms=games_result.duration_ms,
            )
            results.append(games_result)
            return results
        results.append(games_result)
        return results  # Hard fail — don't continue
    results.append(games_result)

    # 2. pull-schedule
    results.append(_run_stage("pull_schedule", pull_schedule, season, season_type))

    # 3. pull-rosters
    results.append(_run_stage("pull_rosters", pull_rosters, season))

    # 4. pull-team-game-stats
    results.append(_run_stage("pull_team_game_stats", pull_team_game_stats, season, season_type))

    # 5. pull-player-game-stats
    results.append(
        _run_stage("pull_player_game_stats", pull_player_game_stats, season, season_type)
    )

    # 6. pull-player-game-starter-roles
    results.append(
        _run_stage(
            "pull_player_game_starter_roles",
            pull_player_game_starter_roles,
            season,
            season_type,
        )
    )

    # 7. pull-game-period-stats
    results.append(
        _run_stage("pull_game_period_stats", pull_game_period_stats, season, season_type)
    )

    # 8. pull-standings-snapshots (regular season only)
    if season_type != "Playoffs":
        results.append(_run_stage("pull_standings_snapshots", pull_standings, season, season_type))
    else:
        results.append(StageResult(name="pull_standings_snapshots", status=StageStatus.SKIPPED))

    # 9. pull-team-season-advanced
    results.append(
        _run_stage("pull_team_season_advanced", pull_team_season_advanced, season, season_type)
    )

    # 10. pull-player-season-advanced
    results.append(
        _run_stage("pull_player_season_advanced", pull_player_season_advanced, season, season_type)
    )

    return results


def _validate_stage(season: str, season_type: str) -> StageResult:
    from nbatools.commands.pipeline.validate_raw import run as validate_raw

    return _run_stage("validate_raw", validate_raw, season, season_type)


def _build_stages(season: str, season_type: str) -> list[StageResult]:
    from nbatools.commands.pipeline.build_game_features import run as build_game_features
    from nbatools.commands.pipeline.build_league_season_stats import (
        run as build_league_season_stats,
    )
    from nbatools.commands.pipeline.build_player_game_features import (
        run as build_player_game_features,
    )
    from nbatools.commands.pipeline.build_schedule_context_features import (
        run as build_schedule_context_features,
    )
    from nbatools.commands.pipeline.build_team_game_features import run as build_team_game_features

    results: list[StageResult] = []
    results.append(
        _run_stage("build_team_game_features", build_team_game_features, season, season_type)
    )
    results.append(_run_stage("build_game_features", build_game_features, season, season_type))
    results.append(
        _run_stage(
            "build_schedule_context_features",
            build_schedule_context_features,
            season,
            season_type,
        )
    )
    results.append(
        _run_stage("build_player_game_features", build_player_game_features, season, season_type)
    )
    results.append(
        _run_stage("build_league_season_stats", build_league_season_stats, season, season_type)
    )
    return results


def _manifest_stage(season: str, season_type: str) -> StageResult:
    from nbatools.commands.ops.update_manifest import run as update_manifest

    return _run_stage("update_manifest", update_manifest, season, season_type)


# ---------------------------------------------------------------------------
# Season-level orchestration
# ---------------------------------------------------------------------------


def refresh_season(
    season: str,
    season_type: str,
    *,
    skip_existing: bool = False,
    allow_no_data_skip: bool = False,
    dry_run: bool = False,
) -> SeasonResult:
    """Full refresh of one season/season_type: raw pulls → validate → build → manifest.

    Parameters
    ----------
    season : str
        e.g. "2025-26"
    season_type : str
        "Regular Season" or "Playoffs"
    skip_existing : bool
        If True and all processed outputs already exist, skip this season.
    allow_no_data_skip : bool
        If True, a "No data returned" from the games pull skips cleanly
        (useful for upcoming playoffs).
    dry_run : bool
        If True, return the planned stages without executing them.
    """
    result = SeasonResult(
        season=season,
        season_type=season_type,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    # --- skip-existing check ---
    if skip_existing:
        from nbatools.commands.pipeline.backfill_season import outputs_exist

        if outputs_exist(season, season_type):
            result.stages.append(
                StageResult(
                    name="skip_check",
                    status=StageStatus.SKIPPED,
                    error="All processed outputs already exist",
                )
            )
            result.finished_at = datetime.now().isoformat(timespec="seconds")
            result.current_through = compute_current_through(season, season_type)
            return result

    if dry_run:
        planned = [
            "pull_games",
            "pull_schedule",
            "pull_rosters",
            "pull_team_game_stats",
            "pull_player_game_stats",
            "pull_player_game_starter_roles",
            "pull_game_period_stats",
            "pull_standings_snapshots",
            "pull_team_season_advanced",
            "pull_player_season_advanced",
            "validate_raw",
            "build_team_game_features",
            "build_game_features",
            "build_schedule_context_features",
            "build_player_game_features",
            "build_league_season_stats",
            "update_manifest",
        ]
        result.stages = [
            StageResult(name=name, status=StageStatus.SKIPPED, error="dry_run") for name in planned
        ]
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    # --- 1. Raw pulls ---
    raw_results = _raw_pull_stages(season, season_type, allow_no_data_skip=allow_no_data_skip)
    result.stages.extend(raw_results)

    # If games were skipped (no data), we're done
    if raw_results and raw_results[0].status == StageStatus.SKIPPED:
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    # If any raw stage failed, stop early
    if any(s.status == StageStatus.FAILED for s in raw_results):
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    # --- 2. Validation ---
    val = _validate_stage(season, season_type)
    result.stages.append(val)
    if val.status == StageStatus.FAILED:
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    # --- 3. Build processed features ---
    build_results = _build_stages(season, season_type)
    result.stages.extend(build_results)
    if any(s.status == StageStatus.FAILED for s in build_results):
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    # --- 4. Update manifest ---
    manifest = _manifest_stage(season, season_type)
    result.stages.append(manifest)

    # --- 5. Compute current_through ---
    result.current_through = compute_current_through(season, season_type)

    result.finished_at = datetime.now().isoformat(timespec="seconds")
    return result


# ---------------------------------------------------------------------------
# Pipeline-level workflows
# ---------------------------------------------------------------------------


def refresh_current_season(
    *,
    include_playoffs: bool = False,
    dry_run: bool = False,
) -> PipelineResult:
    """Refresh the current regular season (and optionally playoffs).

    This is the daily/in-season workflow: pull latest data for the active
    season, rebuild derived features, update manifest, compute current_through.

    Also writes a refresh log so the freshness API can report last-refresh
    outcome.
    """
    from nbatools.commands.freshness import write_refresh_log

    pipeline = PipelineResult(
        mode="current_season_refresh",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    # Regular season
    season = LATEST_REGULAR_SEASON
    sr = refresh_season(
        season,
        "Regular Season",
        allow_no_data_skip=False,
        dry_run=dry_run,
    )
    pipeline.seasons.append(sr)

    # Playoffs if requested
    if include_playoffs:
        playoff_season = LATEST_PLAYOFF_SEASON
        # If the playoff season matches the regular season, refresh it.
        # Otherwise, refresh the latest known playoff season.
        sr_playoffs = refresh_season(
            playoff_season,
            "Playoffs",
            allow_no_data_skip=True,
            dry_run=dry_run,
        )
        pipeline.seasons.append(sr_playoffs)

    pipeline.finished_at = datetime.now().isoformat(timespec="seconds")

    # Write refresh log (skip during dry-run—no real work was done)
    if not dry_run:
        ts = pipeline.finished_at or datetime.now().isoformat(timespec="seconds")
        if pipeline.success:
            write_refresh_log(success=True, timestamp=ts)
        else:
            errors = []
            for fsr in pipeline.failed_seasons:
                for fst in fsr.failed_stages:
                    errors.append(f"{fsr.season}/{fst.name}: {fst.error}")
            write_refresh_log(
                success=False,
                timestamp=ts,
                error="; ".join(errors) if errors else "unknown",
            )

    return pipeline


def rebuild_season(
    season: str,
    season_type: str = "Regular Season",
    *,
    include_playoffs: bool = False,
    dry_run: bool = False,
) -> PipelineResult:
    """Force a full rebuild of one season (no skip-existing).

    Use when a contract regression, pipeline change, or data corruption
    requires a clean rebuild from raw pulls through processed artifacts.
    """
    pipeline = PipelineResult(
        mode="season_rebuild",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    sr = refresh_season(
        season,
        season_type,
        skip_existing=False,
        allow_no_data_skip=False,
        dry_run=dry_run,
    )
    pipeline.seasons.append(sr)

    if include_playoffs:
        sr_playoffs = refresh_season(
            season,
            "Playoffs",
            skip_existing=False,
            allow_no_data_skip=True,
            dry_run=dry_run,
        )
        pipeline.seasons.append(sr_playoffs)

    pipeline.finished_at = datetime.now().isoformat(timespec="seconds")
    return pipeline


def backfill_seasons(
    start_season: str,
    end_season: str,
    *,
    include_playoffs: bool = False,
    skip_existing: bool = True,
    dry_run: bool = False,
) -> PipelineResult:
    """Historical backfill across a range of seasons.

    Parameters
    ----------
    start_season / end_season : str
        e.g. "2020-21", "2024-25"
    include_playoffs : bool
        Also backfill playoff data for each season.
    skip_existing : bool
        Skip seasons where all processed outputs already exist (default True).
    dry_run : bool
        Plan without executing.
    """
    pipeline = PipelineResult(
        mode="historical_backfill",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    start = season_to_int(start_season)
    end = season_to_int(end_season)

    for year in range(start, end + 1):
        season = int_to_season(year)

        sr = refresh_season(
            season,
            "Regular Season",
            skip_existing=skip_existing,
            allow_no_data_skip=False,
            dry_run=dry_run,
        )
        pipeline.seasons.append(sr)

        if include_playoffs:
            sr_playoffs = refresh_season(
                season,
                "Playoffs",
                skip_existing=skip_existing,
                allow_no_data_skip=True,
                dry_run=dry_run,
            )
            pipeline.seasons.append(sr_playoffs)

    pipeline.finished_at = datetime.now().isoformat(timespec="seconds")
    return pipeline


# ---------------------------------------------------------------------------
# Status / freshness reporting
# ---------------------------------------------------------------------------


def pipeline_status(
    season: str | None = None,
    season_type: str = "Regular Season",
) -> dict:
    """Return current freshness status for a season (or the latest season).

    Returns a dict with manifest info, current_through, and file inventory.
    """
    import pandas as pd

    from nbatools.commands.ops.update_manifest import (
        processed_paths,
        raw_paths,
    )

    if season is None:
        season = LATEST_REGULAR_SEASON

    manifest_path = Path("data/metadata/backfill_manifest.csv")

    # Manifest row
    manifest_row = None
    if manifest_path.exists():
        try:
            df = pd.read_csv(manifest_path)
            mask = (df["season"] == season) & (df["season_type"] == season_type)
            rows = df.loc[mask]
            if not rows.empty:
                row = rows.iloc[0]
                manifest_row = {
                    "raw_complete": bool(row.get("raw_complete") == 1),
                    "processed_complete": bool(row.get("processed_complete") == 1),
                    "loaded_at": str(row.get("loaded_at", "")),
                }
        except Exception:
            pass

    # File existence
    raw_exist = {str(p): p.exists() for p in raw_paths(season, season_type)}
    proc_exist = {str(p): p.exists() for p in processed_paths(season, season_type)}

    ct = compute_current_through(season, season_type)

    return {
        "season": season,
        "season_type": season_type,
        "manifest": manifest_row,
        "current_through": ct,
        "raw_files": raw_exist,
        "processed_files": proc_exist,
        "raw_complete": all(raw_exist.values()),
        "processed_complete": all(proc_exist.values()),
    }
