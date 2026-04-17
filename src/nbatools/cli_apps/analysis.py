import typer

from nbatools.commands.analysis.battle_summary import run as battle_summary_run

app = typer.Typer()


@app.command("battle-summary")
def battle_summary(
    season: str = typer.Option(...),
    battle: str = typer.Option(...),
    season_type: str = typer.Option("Regular Season", "--season-type"),
    exclude_ties: bool = typer.Option(False, "--exclude-ties"),
):
    battle_summary_run(season, battle, season_type, exclude_ties)
