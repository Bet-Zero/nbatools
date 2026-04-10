import typer

from nbatools.commands.pull_games import run as pull_games_run
from nbatools.commands.pull_player_game_stats import run as pull_player_game_stats_run
from nbatools.commands.pull_player_season_advanced import run as pull_player_season_advanced_run
from nbatools.commands.pull_rosters import run as pull_rosters_run
from nbatools.commands.pull_schedule import run as pull_schedule_run
from nbatools.commands.pull_standings_snapshots import run as pull_standings_snapshots_run
from nbatools.commands.pull_team_game_stats import run as pull_team_game_stats_run
from nbatools.commands.pull_team_season_advanced import run as pull_team_season_advanced_run
from nbatools.commands.pull_teams import run as pull_teams_run

app = typer.Typer()


@app.command("pull-teams")
def pull_teams():
    pull_teams_run()


@app.command("pull-games")
def pull_games(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_games_run(season, season_type)


@app.command("pull-schedule")
def pull_schedule(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_schedule_run(season, season_type)


@app.command("pull-rosters")
def pull_rosters(season: str = typer.Option(...)):
    pull_rosters_run(season)


@app.command("pull-standings-snapshots")
def pull_standings_snapshots(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_standings_snapshots_run(season, season_type)


@app.command("pull-team-season-advanced")
def pull_team_season_advanced(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_team_season_advanced_run(season, season_type)


@app.command("pull-player-season-advanced")
def pull_player_season_advanced(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_player_season_advanced_run(season, season_type)


@app.command("pull-team-game-stats")
def pull_team_game_stats(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_team_game_stats_run(season, season_type)


@app.command("pull-player-game-stats")
def pull_player_game_stats(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_player_game_stats_run(season, season_type)
