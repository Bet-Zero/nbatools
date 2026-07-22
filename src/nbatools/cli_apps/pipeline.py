"""CLI command group for data pipeline refresh workflows.

Exposes deterministic refresh, rebuild, backfill, status, and auto-refresh
commands that orchestrate the full pull → validate → build → manifest pipeline.
"""

import json
from enum import StrEnum
from pathlib import Path

import typer

from nbatools.commands.pipeline.generation_publication import (
    GenerationPublicationError,
    GenerationPublicationResult,
    publish_local_generation,
    publish_r2_generation,
    rollback_local_generation,
    rollback_r2_generation,
)
from nbatools.commands.pipeline.live_recovery_drill import (
    LiveRecoveryDrillError,
    prepare_live_recovery_drill_plan,
)
from nbatools.commands.pipeline.orchestrator import (
    PipelineResult,
    backfill_seasons,
    pipeline_status,
    refresh_current_season,
)
from nbatools.commands.pipeline.orchestrator import (
    rebuild_season as rebuild_season_fn,
)
from nbatools.commands.pipeline.sync_r2 import R2SyncError, SyncProgress, run_sync_r2
from nbatools.recovery_drill import RecoveryDrillError, run_safe_recovery_drill

app = typer.Typer()


class PublicationTarget(StrEnum):
    LOCAL = "local"
    R2 = "r2"


def _print_result(result: PipelineResult) -> None:
    """Pretty-print a PipelineResult to stdout."""
    for line in result.summary_lines:
        print(line)

    if result.success:
        print(f"\n✅ Pipeline {result.mode} completed successfully.")
    else:
        print(f"\n❌ Pipeline {result.mode} completed with failures.")
        raise typer.Exit(code=1)


def _print_sync_progress(progress: SyncProgress) -> None:
    """Pretty-print one R2 sync progress event."""
    print(
        f"[{progress.processed_files}/{progress.total_files}] "
        f"{progress.action} {progress.key} ({progress.size_bytes} bytes)"
    )


def _print_publication_result(result: GenerationPublicationResult) -> None:
    print(f"Generation {result.action}: {result.generation_id}")
    print(f"Previous generation: {result.previous_generation_id}")
    print(f"Target: {result.target}")
    print(f"Files: {result.file_count}")
    print(f"Bytes: {result.total_bytes}")
    print(f"Pointer: {result.pointer}")


@app.command("refresh")
def refresh(
    include_playoffs: bool = typer.Option(
        True,
        "--include-playoffs/--no-playoffs",
        help="Refresh the latest playoff season too. Enabled by default.",
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
    print(f"Validation state: {info['validation_state']}")
    print(f"Generation: {info['generation_id'] or '(none)'}")

    if info["manifest"]:
        m = info["manifest"]
        print(
            f"Manifest: raw={m['raw_complete']}  processed={m['processed_complete']}"
            f"  loaded_at={m['loaded_at']}"
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
        if info["validation_state"] == "passed":
            print("\nAll expected files present and validated.")
        else:
            print("\nAll expected files are present, but validation has not passed.")

    if info["validation_errors"]:
        print("\nValidation errors:")
        for error in info["validation_errors"]:
            print(f"  {error}")

    if info["validation_state"] != "passed":
        raise typer.Exit(code=1)


@app.command("sync-r2")
def sync_r2(
    data_dir: Path = typer.Option(
        Path("data"),
        "--data-dir",
        help="Local data directory to sync.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned uploads without writing to R2.",
    ),
    prefix: str = typer.Option(
        "",
        "--prefix",
        help="Optional object-key prefix inside the R2 bucket.",
    ),
):
    """Preview legacy canonical-key differences without writing to R2."""
    try:
        result = run_sync_r2(
            data_dir=data_dir,
            dry_run=dry_run,
            prefix=prefix,
            progress=_print_sync_progress,
        )
    except R2SyncError as exc:
        print(f"R2 sync failed: {exc}")
        raise typer.Exit(code=1)

    for line in result.summary_lines:
        print(line)

    if not result.success:
        raise typer.Exit(code=1)


@app.command("publish-generation")
def publish_generation(
    generation_id: str = typer.Option(
        ...,
        "--generation-id",
        help="Unique immutable runtime generation identifier.",
    ),
    data_dir: Path = typer.Option(
        Path("data"),
        "--data-dir",
        help="Validated canonical data staging directory.",
    ),
    target: PublicationTarget = typer.Option(
        PublicationTarget.LOCAL,
        "--target",
        help="Publication target: local or r2.",
    ),
):
    """Validate, publish, and atomically activate one immutable generation."""
    try:
        if target is PublicationTarget.LOCAL:
            result = publish_local_generation(
                generation_id,
                source_dir=data_dir,
                data_root=data_dir,
            )
        else:
            result = publish_r2_generation(generation_id, source_dir=data_dir)
    except GenerationPublicationError as exc:
        print(f"Generation publication failed: {exc}")
        raise typer.Exit(code=1)
    _print_publication_result(result)


@app.command("rollback-generation")
def rollback_generation(
    data_dir: Path = typer.Option(
        Path("data"),
        "--data-dir",
        help="Local data root when target is local.",
    ),
    target: PublicationTarget = typer.Option(
        PublicationTarget.LOCAL,
        "--target",
        help="Rollback target: local or r2.",
    ),
):
    """Atomically reactivate the retained previous generation."""
    try:
        if target is PublicationTarget.LOCAL:
            result = rollback_local_generation(data_root=data_dir)
        else:
            result = rollback_r2_generation()
    except GenerationPublicationError as exc:
        print(f"Generation rollback failed: {exc}")
        raise typer.Exit(code=1)
    _print_publication_result(result)


@app.command("recovery-drill")
def recovery_drill(
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional JSON receipt path. The drill itself uses temporary data only.",
    ),
):
    """Run the network-free local and in-memory R2 recovery drill."""
    try:
        receipt = run_safe_recovery_drill()
    except RecoveryDrillError as exc:
        print(f"Recovery drill failed: {exc}")
        raise typer.Exit(code=1)
    rendered = json.dumps(receipt.to_dict(), indent=2, sort_keys=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n")
    print(rendered)


@app.command("live-recovery-drill-plan")
def live_recovery_drill_plan(
    source_generation_dir: Path = typer.Option(
        ...,
        "--source-generation-dir",
        help="Existing immutable local generation directory; read only.",
    ),
    source_generation: str = typer.Option(
        ...,
        "--source-generation",
        help="Expected immutable local source generation identifier.",
    ),
    repository_commit: str = typer.Option(
        ...,
        "--repository-commit",
        help="Current-main commit bound into the plan.",
    ),
    drill_id: str = typer.Option(
        ...,
        "--drill-id",
        help="Unique e03b-* isolated drill identifier.",
    ),
    r2_account_id_sha256: str = typer.Option(
        ...,
        "--r2-account-id-sha256",
        help="SHA-256 of the exact target R2 account ID; the account ID is not written.",
    ),
    bucket_name: str = typer.Option(
        "nbatools-data",
        "--bucket-name",
        help="Exact bucket name for later separately authorized execution.",
    ),
    production_url: str = typer.Option(
        ...,
        "--production-url",
        help="Accepted production URL bound into the plan.",
    ),
    expected_production_generation: str = typer.Option(
        ...,
        "--expected-production-generation",
        help="Production generation that later read-only preflight must prove.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional JSON plan path. This command never opens a network connection.",
    ),
):
    """Prepare a hash-bound E-03B plan without credentials or provider access."""
    try:
        plan = prepare_live_recovery_drill_plan(
            source_generation_dir=source_generation_dir,
            source_generation=source_generation,
            repository_commit=repository_commit,
            drill_id=drill_id,
            r2_account_id_sha256=r2_account_id_sha256,
            bucket_name=bucket_name,
            production_url=production_url,
            expected_production_generation=expected_production_generation,
        )
    except LiveRecoveryDrillError as exc:
        print(f"Live recovery drill plan failed: {exc.code}")
        raise typer.Exit(code=1)
    rendered = json.dumps(plan.to_dict(), indent=2, sort_keys=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


@app.command("auto-refresh")
def auto_refresh(
    interval: str = typer.Option(
        "6h",
        "--interval",
        help="Time between refresh cycles (e.g. '6h', '30m', '90s').",
    ),
    include_playoffs: bool = typer.Option(
        True,
        "--include-playoffs/--no-playoffs",
        help="Refresh the latest playoff season on each cycle too. Enabled by default.",
    ),
):
    """Run an automated refresh loop for the current season.

    Executes 'pipeline refresh' on a repeating schedule.  Writes a
    last_refresh.json log after each attempt.  Press Ctrl-C to stop.
    """
    from nbatools.commands.pipeline.auto_refresh import parse_interval, run_auto_refresh

    try:
        seconds = parse_interval(interval)
    except ValueError:
        print(f"Invalid interval: {interval!r}  (use e.g. '6h', '30m', '90s')")
        raise typer.Exit(code=1)

    if seconds < 60:
        print("Interval must be at least 60 seconds.")
        raise typer.Exit(code=1)

    run_auto_refresh(seconds, include_playoffs=include_playoffs)
