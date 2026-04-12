import subprocess

import typer

from nbatools.cli_apps.analysis import app as analysis_app
from nbatools.cli_apps.ops import app as ops_app
from nbatools.cli_apps.pipeline import app as pipeline_app
from nbatools.cli_apps.processing import app as processing_app
from nbatools.cli_apps.queries import app as queries_app
from nbatools.cli_apps.raw import app as raw_app
from nbatools.commands.natural_query import run as natural_query_run

APP_NAME = "nbatools-cli"
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
APP_VERSION = "0.7.0"

app = typer.Typer(
    help=(
        "NBA Tools CLI\n\n"
        "Query NBA player and team data with either structured commands or natural language.\n\n"
        "Examples:\n"
        '  nbatools-cli ask "Jokic recent form"\n'
        '  nbatools-cli ask "Celtics wins vs losses"\n'
        "  nbatools-cli query player-game-summary"
        ' --player "Nikola Jokić" --season 2025-26 --last-n 10\n'
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.callback()
def main():
    """NBA Tools command line interface."""
    return


@app.command("version")
def version():
    """Show the installed CLI version."""
    print(f"{APP_NAME} {APP_VERSION}")


@app.command("test")
def test():
    """Run the full test suite."""
    subprocess.run(["pytest"])


@app.command("ask")
def ask(
    query: str = typer.Argument(
        ...,
        help="Natural language NBA query.",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Return raw CSV-like command output instead of polished pretty output.",
    ),
    csv: str = typer.Option(
        None,
        "--csv",
        help="Optional path to save raw CSV/tabular output.",
    ),
    txt: str = typer.Option(
        None,
        "--txt",
        help="Optional path to save pretty text output.",
    ),
    json_path: str = typer.Option(
        None,
        "--json",
        help="Optional path to save raw output as JSON.",
    ),
):
    """Run a natural-language NBA query."""
    natural_query_run(
        query,
        pretty=not raw,
        export_csv_path=csv,
        export_txt_path=txt,
        export_json_path=json_path,
    )


app.add_typer(
    queries_app,
    name="query",
    help="Run structured NBA query commands.",
)

app.add_typer(
    raw_app,
    name="raw",
    help="Pull raw data from the NBA API.",
)

app.add_typer(
    processing_app,
    name="processing",
    help="Validate and build processed features from raw data.",
)

app.add_typer(
    ops_app,
    name="ops",
    help="Pipeline operations: backfill, manifest, inventory.",
)

app.add_typer(
    pipeline_app,
    name="pipeline",
    help="Refresh, rebuild, backfill, and status workflows.",
)

app.add_typer(
    analysis_app,
    name="analysis",
    help="Analysis and battle summary commands.",
)


@app.command("serve")
def serve(
    host: str = typer.Option(DEFAULT_API_HOST, "--host", help="Bind host."),
    port: int = typer.Option(DEFAULT_API_PORT, "--port", help="Bind port."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development."),
):
    """Start the local nbatools API server."""
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required. Install with: pip install 'nbatools[api]'")
        raise typer.Exit(code=1)
    uvicorn.run("nbatools.api:app", host=host, port=port, reload=reload)
