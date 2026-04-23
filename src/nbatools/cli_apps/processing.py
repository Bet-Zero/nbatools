import typer

from nbatools.commands.analysis.analyze_3pt_battles import run as analyze_3pt_battles_run
from nbatools.commands.pipeline.build_game_features import run as build_game_features_run
from nbatools.commands.pipeline.build_league_season_stats import (
    run as build_league_season_stats_run,
)
from nbatools.commands.pipeline.build_player_game_features import (
    run as build_player_game_features_run,
)
from nbatools.commands.pipeline.build_schedule_context_features import (
    run as build_schedule_context_features_run,
)
from nbatools.commands.pipeline.build_team_game_features import run as build_team_game_features_run
from nbatools.commands.pipeline.validate_raw import run as validate_raw_run

app = typer.Typer()


@app.command("validate-raw")
def validate_raw(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    validate_raw_run(season, season_type)


@app.command("build-team-game-features")
def build_team_game_features(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    build_team_game_features_run(season, season_type)


@app.command("build-game-features")
def build_game_features(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    build_game_features_run(season, season_type)


@app.command("build-schedule-context-features")
def build_schedule_context_features(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    build_schedule_context_features_run(season, season_type)


@app.command("build-player-game-features")
def build_player_game_features(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    build_player_game_features_run(season, season_type)


@app.command("build-league-season-stats")
def build_league_season_stats(
    season: str = typer.Option(...),
    season_type: str = typer.Option(...),
):
    build_league_season_stats_run(season, season_type)


@app.command("analyze-3pt-battles")
def analyze_3pt_battles(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    analyze_3pt_battles_run(season, season_type)
