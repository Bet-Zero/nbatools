"""CLI command group for data pipeline refresh workflows.

Exposes deterministic refresh, rebuild, backfill, status, and auto-refresh
commands that orchestrate the full pull → validate → build → manifest pipeline.
"""

import typer

from nbatools.commands.pipeline import (
    PipelineResult,
    backfill_seasons,
    pipeline_status,
    refresh_current_season,
)
from nbatools.commands.pipeline import (
    rebuild_season as rebuild_season_fn,
)

app = typer.Typer()


def _print_result(result: PipelineResult) -> None:
    """Pretty-print a PipelineResult to stdout."""
    for line in result.summary_lines:
        print(line)

    if result.success:
        print(f"\n✅ Pipeline {result.mode} completed successfully.")
    else:
        print(f"\n❌ Pipeline {result.mode} completed with failures.")
        raise typer.Exit(code=1)


@app.command("refresh")
def refresh(
    include_playoffs: bool = typer.Option(
        False,
        "--include-playoffs",
        help="Also refresh the latest playoff season.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned stages without executing them.",
    ),
):
    """Refresh the current season — daily/in-season workflow.

    Pulls latest raw data for the active season, validates, rebuilds
    all derived features, updates the manifest, and reports current_through.
    """
    result = refresh_current_season(include_playoffs=include_playoffs, dry_run=dry_run)
    _print_result(result)


@app.command("rebuild")
def rebuild(
    season: str = typer.Option(
        ...,
        "--season",
        help="Season to rebuild, e.g. '2024-25'.",
    ),
    season_type: str = typer.Option(
        "Regular Season",
        "--season-type",
        help="'Regular Season' or 'Playoffs'.",
    ),
    include_playoffs: bool = typer.Option(
        False,
        "--include-playoffs",
        help="Also rebuild playoffs for this season.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned stages without executing them.",
    ),
):
    """Force a full rebuild of one season from scratch.

    Does not skip existing files — re-pulls raw data, re-validates,
    re-builds all processed features, and updates the manifest.
    Use when a data regression or pipeline change requires a clean rebuild.
    """
    result = rebuild_season_fn(
        season,
        season_type,
        include_playoffs=include_playoffs,
        dry_run=dry_run,
    )
    _print_result(result)


@app.command("backfill")
def backfill(
    start_season: str = typer.Option(
        ...,
        "--start-season",
        help="First season in range, e.g. '2020-21'.",
    ),
    end_season: str = typer.Option(
        ...,
        "--end-season",
        help="Last season in range, e.g. '2024-25'.",
    ),
    include_playoffs: bool = typer.Option(
        False,
        "--include-playoffs",
        help="Also backfill playoff data for each season.",
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--no-skip-existing",
        help="Skip seasons where processed outputs already exist.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned stages without executing them.",
    ),
):
    """Backfill historical data across a range of seasons.

    Runs the full pipeline for each season in [start_season, end_season].
    By default skips seasons whose processed outputs already exist.
    Use --no-skip-existing to force a full re-pull of every season.
    """
    result = backfill_seasons(
        start_season,
        end_season,
        include_playoffs=include_playoffs,
        skip_existing=skip_existing,
        dry_run=dry_run,
    )
    _print_result(result)


@app.command("status")
def status(
    season: str = typer.Option(
        None,
        "--season",
        help="Season to check (defaults to current season).",
    ),
    season_type: str = typer.Option(
        "Regular Season",
        "--season-type",
        help="'Regular Season' or 'Playoffs'.",
    ),
):
    """Show data freshness status for a season.

    Reports manifest state, current_through date, and file existence
    for raw and processed datasets.
    """
    info = pipeline_status(season=season, season_type=season_type)

    print(f"Season: {info['season']}  Type: {info['season_type']}")
    print(f"Current through: {info['current_through'] or '(unknown)'}")
    print(f"Raw complete: {info['raw_complete']}")
    print(f"Processed complete: {info['processed_complete']}")

    if info["manifest"]:
        m = info["manifest"]
        print(
            f"Manifest: raw={m['raw_complete']}  processed={m['processed_complete']}  loaded_at={m['loaded_at']}"
        )
    else:
        print("Manifest: (no entry)")

    # Show missing files
    missing_raw = [p for p, exists in info["raw_files"].items() if not exists]
    missing_proc = [p for p, exists in info["processed_files"].items() if not exists]

    if missing_raw:
        print("\nMissing raw files:")
        for p in missing_raw:
            print(f"  {p}")

    if missing_proc:
        print("\nMissing processed files:")
        for p in missing_proc:
            print(f"  {p}")

    if not missing_raw and not missing_proc:
        print("\nAll expected files present.")


@app.command("auto-refresh")
def auto_refresh(
    interval: str = typer.Option(
        "6h",
        "--interval",
        help="Time between refresh cycles (e.g. '6h', '30m', '90s').",
    ),
    include_playoffs: bool = typer.Option(
        False,
        "--include-playoffs",
        help="Also refresh the latest playoff season each cycle.",
    ),
):
    """Run an automated refresh loop for the current season.

    Executes 'pipeline refresh' on a repeating schedule.  Writes a
    last_refresh.json log after each attempt.  Press Ctrl-C to stop.
    """
    from nbatools.commands.auto_refresh import parse_interval, run_auto_refresh

    try:
        seconds = parse_interval(interval)
    except ValueError:
        print(f"Invalid interval: {interval!r}  (use e.g. '6h', '30m', '90s')")
        raise typer.Exit(code=1)

    if seconds < 60:
        print("Interval must be at least 60 seconds.")
        raise typer.Exit(code=1)

    run_auto_refresh(seconds, include_playoffs=include_playoffs)
