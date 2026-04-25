import typer

from nbatools.commands.pipeline.pull_game_period_stats import run as pull_game_period_stats_run
from nbatools.commands.pipeline.pull_games import run as pull_games_run
from nbatools.commands.pipeline.pull_league_lineup_viz import run as pull_league_lineup_viz_run
from nbatools.commands.pipeline.pull_play_by_play_events import (
    run as pull_play_by_play_events_run,
)
from nbatools.commands.pipeline.pull_player_game_starter_roles import (
    run as pull_player_game_starter_roles_run,
)
from nbatools.commands.pipeline.pull_player_game_stats import run as pull_player_game_stats_run
from nbatools.commands.pipeline.pull_player_season_advanced import (
    run as pull_player_season_advanced_run,
)
from nbatools.commands.pipeline.pull_rosters import run as pull_rosters_run
from nbatools.commands.pipeline.pull_schedule import run as pull_schedule_run
from nbatools.commands.pipeline.pull_standings_snapshots import run as pull_standings_snapshots_run
from nbatools.commands.pipeline.pull_team_game_stats import run as pull_team_game_stats_run
from nbatools.commands.pipeline.pull_team_player_on_off_summary import (
    run as pull_team_player_on_off_summary_run,
)
from nbatools.commands.pipeline.pull_team_season_advanced import (
    run as pull_team_season_advanced_run,
)
from nbatools.commands.pipeline.pull_teams import run as pull_teams_run

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


@app.command("pull-player-game-starter-roles")
def pull_player_game_starter_roles(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_player_game_starter_roles_run(season, season_type)


@app.command("pull-game-period-stats")
def pull_game_period_stats(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_game_period_stats_run(season, season_type)


@app.command("pull-team-player-on-off-summary")
def pull_team_player_on_off_summary(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_team_player_on_off_summary_run(season, season_type)


@app.command("pull-league-lineup-viz")
def pull_league_lineup_viz(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
    unit_size: int = typer.Option(5, "--unit-size"),
    minute_minimum: int = typer.Option(0, "--minute-minimum"),
):
    pull_league_lineup_viz_run(season, season_type, unit_size, minute_minimum)


@app.command("pull-play-by-play-events")
def pull_play_by_play_events(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    pull_play_by_play_events_run(season, season_type)
