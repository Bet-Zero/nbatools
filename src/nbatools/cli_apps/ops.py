import typer

from nbatools.commands.backfill_range import run as backfill_range_run
from nbatools.commands.backfill_season import run as backfill_season_run
from nbatools.commands.inventory import run as inventory_run
from nbatools.commands.run_tests import run as run_tests_run
from nbatools.commands.show_manifest import run as show_manifest_run
from nbatools.commands.show_team_history import run as show_team_history_run
from nbatools.commands.update_manifest import run as update_manifest_run

app = typer.Typer()


@app.command("backfill-season")
def backfill_season(
    season: str = typer.Option(...),
    season_type: str = typer.Option(...),
    skip_existing: bool = typer.Option(False, "--skip-existing"),
):
    backfill_season_run(season, season_type, skip_existing)


@app.command("backfill-range")
def backfill_range(
    start_season: str = typer.Option(..., "--start-season"),
    end_season: str = typer.Option(..., "--end-season"),
    include_playoffs: bool = typer.Option(False, "--include-playoffs"),
    skip_existing: bool = typer.Option(False, "--skip-existing"),
):
    backfill_range_run(start_season, end_season, include_playoffs, skip_existing)


@app.command("inventory")
def inventory():
    inventory_run()


@app.command("show-team-history")
def show_team_history(
    team_id: int = typer.Option(None, "--team-id"),
    season: int = typer.Option(None, "--season"),
):
    show_team_history_run(team_id, season)


@app.command("update-manifest")
def update_manifest(
    season: str = typer.Option(...),
    season_type: str = typer.Option(..., "--season-type"),
):
    update_manifest_run(season, season_type)


@app.command("show-manifest")
def show_manifest():
    show_manifest_run()


@app.command("test")
def test(
    verbose: bool = typer.Option(False, "--verbose"),
):
    run_tests_run(verbose)
