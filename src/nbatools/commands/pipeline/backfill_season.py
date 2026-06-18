import sys
from pathlib import Path


def outputs_exist(season: str, season_type: str) -> bool:
    safe = season_type.lower().replace(" ", "_")

    paths = [
        Path(f"data/processed/team_game_features/{season}_{safe}.csv"),
        Path(f"data/processed/game_features/{season}_{safe}.csv"),
        Path(f"data/processed/schedule_context_features/{season}_{safe}.csv"),
        Path(f"data/processed/player_game_features/{season}_{safe}.csv"),
        Path(f"data/processed/league_season_stats/{season}_{safe}.csv"),
    ]

    return all(p.exists() for p in paths)


def run(season: str, season_type: str, skip_existing: bool = False):
    """Backfill one season/season_type via the in-process orchestrator.

    Delegates to ``refresh_season`` (raw pulls → validate → build →
    manifest) instead of re-spawning the CLI per stage. Playoffs that have
    not started yet skip cleanly rather than failing.
    """
    from nbatools.commands.pipeline.orchestrator import refresh_season

    result = refresh_season(
        season,
        season_type,
        skip_existing=skip_existing,
        allow_no_data_skip=(season_type == "Playoffs"),
    )

    for stage in result.stages:
        print(f">>> {stage.name}: {stage.status}" + (f" ({stage.error})" if stage.error else ""))

    if not result.success:
        print(f"\n❌ Backfill failed for {season} ({season_type})")
        for st in result.failed_stages:
            print(f"   {st.name}: {st.error}")
        sys.exit(1)

    print(f"\n✅ Backfill complete for {season} ({season_type})")
    if result.current_through:
        print(f"   current_through: {result.current_through}")
