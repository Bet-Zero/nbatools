import subprocess
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


def run_command(cmd: list[str], allow_no_data_skip: bool = False) -> bool:
    print(f"\n>>> Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        if result.stdout:
            print(result.stdout, end="")
        return True

    combined_output = "\n".join(part for part in [result.stdout, result.stderr] if part)

    if allow_no_data_skip and "No data returned" in combined_output:
        print(">>> No data available yet for this season/type. Skipping cleanly.")
        return False

    print(combined_output)
    print(f"\n❌ Command failed: {' '.join(cmd)}")
    sys.exit(result.returncode)


def run(season: str, season_type: str, skip_existing: bool = False):
    if skip_existing and outputs_exist(season, season_type):
        print(f"\n>>> Skipping {season} ({season_type}) — already exists")
        return

    base_cmd = ["nbatools-cli"]

    games_ok = run_command(
        base_cmd + ["pull-games", "--season", season, "--season-type", season_type],
        allow_no_data_skip=(season_type == "Playoffs"),
    )
    if not games_ok:
        print(f">>> Skipping {season} ({season_type}) because no games exist yet.")
        print(f"\n✅ Backfill skipped cleanly for {season} ({season_type})")
        return

    run_command(base_cmd + ["pull-schedule", "--season", season, "--season-type", season_type])
    run_command(base_cmd + ["pull-rosters", "--season", season])
    run_command(
        base_cmd + ["pull-team-game-stats", "--season", season, "--season-type", season_type]
    )
    run_command(
        base_cmd + ["pull-player-game-stats", "--season", season, "--season-type", season_type]
    )

    if season_type != "Playoffs":
        run_command(
            base_cmd
            + ["pull-standings-snapshots", "--season", season, "--season-type", season_type]
        )
    else:
        print("\n>>> Skipping standings for playoffs")

    run_command(
        base_cmd + ["pull-team-season-advanced", "--season", season, "--season-type", season_type]
    )
    run_command(
        base_cmd + ["pull-player-season-advanced", "--season", season, "--season-type", season_type]
    )

    run_command(base_cmd + ["validate-raw", "--season", season, "--season-type", season_type])

    run_command(
        base_cmd + ["build-team-game-features", "--season", season, "--season-type", season_type]
    )
    run_command(
        base_cmd + ["build-game-features", "--season", season, "--season-type", season_type]
    )
    run_command(
        base_cmd
        + ["build-schedule-context-features", "--season", season, "--season-type", season_type]
    )
    run_command(
        base_cmd + ["build-player-game-features", "--season", season, "--season-type", season_type]
    )
    run_command(
        base_cmd + ["build-league-season-stats", "--season", season, "--season-type", season_type]
    )

    run_command(base_cmd + ["update-manifest", "--season", season, "--season-type", season_type])

    print(f"\n✅ Backfill complete for {season} ({season_type})")
