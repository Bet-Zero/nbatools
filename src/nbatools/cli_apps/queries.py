from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd
import typer

from nbatools.commands.game_finder import run as game_finder_run
from nbatools.commands.game_summary import run as game_summary_run
from nbatools.commands.player_compare import run as player_compare_run
from nbatools.commands.player_game_finder import run as player_game_finder_run
from nbatools.commands.player_game_summary import run as player_game_summary_run
from nbatools.commands.player_split_summary import run as player_split_summary_run
from nbatools.commands.season_leaders import run as season_leaders_run
from nbatools.commands.season_team_leaders import run as season_team_leaders_run
from nbatools.commands.team_compare import run as team_compare_run
from nbatools.commands.team_split_summary import run as team_split_summary_run
from nbatools.commands.top_player_games import run as top_player_games_run
from nbatools.commands.top_team_games import run as top_team_games_run

app = typer.Typer(
    help=(
        "Structured NBA query commands.\n\n"
        "Use these when you want explicit control instead of natural language.\n\n"
        "Examples:\n"
        '  nbatools-cli query player-game-summary'
        ' --player "Nikola Joki\u0107" --season 2025-26 --last-n 10\n'
        "  nbatools-cli query team-compare"
        " --team-a BOS --team-b MIL --start-season 2021-22 --end-season 2023-24\n"
        '  nbatools-cli query player-split-summary'
        ' --player "Nikola Joki\u0107" --season 2025-26 --split home_away\n'
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _ensure_parent_dir(path_str: str) -> None:
    path = Path(path_str)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_text_file(path_str: str, text: str) -> None:
    _ensure_parent_dir(path_str)
    Path(path_str).write_text(text, encoding="utf-8")


def _split_summary_sections(text: str) -> dict[str, str]:
    text = text.strip()
    if not text.startswith("SUMMARY\n"):
        return {"raw": text}

    remaining = text[len("SUMMARY\n") :]

    if "\nCOMPARISON\n" in remaining:
        summary_part, comparison_part = remaining.split("\nCOMPARISON\n", 1)
        return {
            "summary": summary_part.strip(),
            "comparison": comparison_part.strip(),
        }

    if "\nSPLIT_COMPARISON\n" in remaining:
        summary_part, split_part = remaining.split("\nSPLIT_COMPARISON\n", 1)
        return {
            "summary": summary_part.strip(),
            "split_comparison": split_part.strip(),
        }

    if "\nBY_SEASON\n" in remaining:
        summary_part, by_season_part = remaining.split("\nBY_SEASON\n", 1)
        return {
            "summary": summary_part.strip(),
            "by_season": by_season_part.strip(),
        }

    return {"summary": remaining.strip()}


def _write_csv_from_raw_output(raw_text: str, path_str: str) -> None:
    _ensure_parent_dir(path_str)
    text = raw_text.strip()

    if not text:
        Path(path_str).write_text("", encoding="utf-8")
        return

    if text.lower() == "no matching games":
        Path(path_str).write_text("message\nno matching games\n", encoding="utf-8")
        return

    if text.startswith("SUMMARY\n"):
        Path(path_str).write_text(
            text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8"
        )
        return

    try:
        df = pd.read_csv(StringIO(text))
        df.to_csv(path_str, index=False)
    except Exception:
        Path(path_str).write_text(
            text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8"
        )


def _write_json_from_raw_output(raw_text: str, path_str: str) -> None:
    _ensure_parent_dir(path_str)
    text = raw_text.strip()

    if not text:
        Path(path_str).write_text("[]\n", encoding="utf-8")
        return

    if text.lower() == "no matching games":
        payload = {"message": "no matching games"}
        Path(path_str).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return

    if not text.startswith("SUMMARY\n"):
        try:
            df = pd.read_csv(StringIO(text))
            payload = df.to_dict(orient="records")
            Path(path_str).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            return
        except Exception:
            payload = {"raw_text": text}
            Path(path_str).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            return

    sections = _split_summary_sections(text)
    payload: dict[str, object] = {}

    for key, block in sections.items():
        if not block:
            continue
        try:
            df = pd.read_csv(StringIO(block))
            payload[key] = df.to_dict(orient="records")
        except Exception:
            payload[key] = block

    Path(path_str).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _run_and_handle_exports(
    func: Callable,
    *args,
    csv: str | None = None,
    txt: str | None = None,
    json_path: str | None = None,
    **kwargs,
) -> None:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    raw_text = buffer.getvalue()

    if csv:
        _write_csv_from_raw_output(raw_text, csv)
    if txt:
        _write_text_file(txt, raw_text if raw_text.endswith("\n") else raw_text + "\n")
    if json_path:
        _write_json_from_raw_output(raw_text, json_path)

    print(raw_text, end="" if raw_text.endswith("\n") else "\n")


def _export_options():
    return {
        "csv": typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
        "txt": typer.Option(None, "--txt", help="Optional path to save raw text output."),
        "json_path": typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
    }


@app.command("top-player-games", help="Show the top player games for a stat in a season.")
def top_player_games(
    season: str = typer.Option(..., help="Season, for example 2025-26."),
    stat: str = typer.Option(..., help="Stat to rank by, for example pts or ast."),
    limit: int = typer.Option(10, help="Maximum number of rows to return."),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    ascending: bool = typer.Option(
        False, "--ascending", help="Sort lowest to highest instead of highest to lowest."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        top_player_games_run,
        season,
        stat,
        limit,
        season_type,
        ascending,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("top-team-games", help="Show the top team games for a stat in a season.")
def top_team_games(
    season: str = typer.Option(..., help="Season, for example 2025-26."),
    stat: str = typer.Option(..., help="Stat to rank by, for example pts."),
    limit: int = typer.Option(10, help="Maximum number of rows to return."),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    ascending: bool = typer.Option(
        False, "--ascending", help="Sort lowest to highest instead of highest to lowest."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        top_team_games_run,
        season,
        stat,
        limit,
        season_type,
        ascending,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("season-leaders", help="Show season leaders for a player stat.")
def season_leaders(
    season: str = typer.Option(..., help="Season, for example 2023-24."),
    stat: str = typer.Option(..., help="Stat to rank by, for example ast."),
    limit: int = typer.Option(10, help="Maximum number of rows to return."),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    min_games: int = typer.Option(1, "--min-games", help="Minimum games played required."),
    ascending: bool = typer.Option(
        False, "--ascending", help="Sort lowest to highest instead of highest to lowest."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        season_leaders_run,
        season,
        stat,
        limit,
        season_type,
        min_games,
        ascending,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("season-team-leaders", help="Show season leaders for a team stat.")
def season_team_leaders(
    season: str = typer.Option(..., help="Season, for example 2023-24."),
    stat: str = typer.Option(..., help="Stat to rank by, for example pts."),
    limit: int = typer.Option(10, help="Maximum number of rows to return."),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    min_games: int = typer.Option(1, "--min-games", help="Minimum games played required."),
    ascending: bool = typer.Option(
        False, "--ascending", help="Sort lowest to highest instead of highest to lowest."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        season_team_leaders_run,
        season,
        stat,
        limit,
        season_type,
        min_games,
        ascending,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command(
    "game-finder",
    help="Find team games using filters like team, opponent, stat thresholds, and last-N.",
)
def game_finder(
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    team: str = typer.Option(None, "--team", help="Team abbreviation or full team name."),
    opponent: str = typer.Option(
        None, "--opponent", help="Opponent team abbreviation or full team name."
    ),
    home_only: bool = typer.Option(False, "--home-only", help="Only include home games."),
    away_only: bool = typer.Option(False, "--away-only", help="Only include away games."),
    wins_only: bool = typer.Option(False, "--wins-only", help="Only include wins."),
    losses_only: bool = typer.Option(False, "--losses-only", help="Only include losses."),
    stat: str = typer.Option(None, "--stat", help="Optional stat filter, for example pts or fg3m."),
    min_value: float = typer.Option(
        None, "--min-value", help="Minimum value for the selected stat."
    ),
    max_value: float = typer.Option(
        None, "--max-value", help="Maximum value for the selected stat."
    ),
    limit: int = typer.Option(25, "--limit", help="Maximum number of rows to return."),
    sort_by: str = typer.Option("game_date", "--sort-by", help="Sort by game_date or stat."),
    ascending: bool = typer.Option(False, "--ascending", help="Sort oldest/lowest first."),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        game_finder_run,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        limit=limit,
        sort_by=sort_by,
        ascending=ascending,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command(
    "player-game-finder",
    help="Find player games using filters like player, opponent, stat thresholds, and last-N.",
)
def player_game_finder(
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    player: str = typer.Option(None, "--player", help="Exact player name."),
    team: str = typer.Option(None, "--team", help="Team abbreviation or full team name."),
    opponent: str = typer.Option(
        None, "--opponent", help="Opponent team abbreviation or full team name."
    ),
    home_only: bool = typer.Option(False, "--home-only", help="Only include home games."),
    away_only: bool = typer.Option(False, "--away-only", help="Only include away games."),
    wins_only: bool = typer.Option(False, "--wins-only", help="Only include wins."),
    losses_only: bool = typer.Option(False, "--losses-only", help="Only include losses."),
    stat: str = typer.Option(None, "--stat", help="Optional stat filter, for example pts or ast."),
    min_value: float = typer.Option(
        None, "--min-value", help="Minimum value for the selected stat."
    ),
    max_value: float = typer.Option(
        None, "--max-value", help="Maximum value for the selected stat."
    ),
    limit: int = typer.Option(25, "--limit", help="Maximum number of rows to return."),
    sort_by: str = typer.Option("game_date", "--sort-by", help="Sort by game_date or stat."),
    ascending: bool = typer.Option(False, "--ascending", help="Sort oldest/lowest first."),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        player_game_finder_run,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        player=player,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        limit=limit,
        sort_by=sort_by,
        ascending=ascending,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("player-game-summary", help="Summarize a filtered player sample.")
def player_game_summary(
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    player: str = typer.Option(None, "--player", help="Exact player name."),
    team: str = typer.Option(None, "--team", help="Team abbreviation or full team name."),
    opponent: str = typer.Option(
        None, "--opponent", help="Opponent team abbreviation or full team name."
    ),
    home_only: bool = typer.Option(False, "--home-only", help="Only include home games."),
    away_only: bool = typer.Option(False, "--away-only", help="Only include away games."),
    wins_only: bool = typer.Option(False, "--wins-only", help="Only include wins."),
    losses_only: bool = typer.Option(False, "--losses-only", help="Only include losses."),
    stat: str = typer.Option(None, "--stat", help="Optional stat threshold field."),
    min_value: float = typer.Option(
        None, "--min-value", help="Minimum value for the selected stat."
    ),
    max_value: float = typer.Option(
        None, "--max-value", help="Maximum value for the selected stat."
    ),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        player_game_summary_run,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        player=player,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("game-summary", help="Summarize a filtered team sample.")
def game_summary(
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    team: str = typer.Option(None, "--team", help="Team abbreviation or full team name."),
    opponent: str = typer.Option(
        None, "--opponent", help="Opponent team abbreviation or full team name."
    ),
    home_only: bool = typer.Option(False, "--home-only", help="Only include home games."),
    away_only: bool = typer.Option(False, "--away-only", help="Only include away games."),
    wins_only: bool = typer.Option(False, "--wins-only", help="Only include wins."),
    losses_only: bool = typer.Option(False, "--losses-only", help="Only include losses."),
    stat: str = typer.Option(None, "--stat", help="Optional stat threshold field."),
    min_value: float = typer.Option(
        None, "--min-value", help="Minimum value for the selected stat."
    ),
    max_value: float = typer.Option(
        None, "--max-value", help="Maximum value for the selected stat."
    ),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        game_summary_run,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("player-compare", help="Compare two players over the same filtered sample.")
def player_compare(
    player_a: str = typer.Option(..., "--player-a", help="First player name."),
    player_b: str = typer.Option(..., "--player-b", help="Second player name."),
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    team: str = typer.Option(None, "--team", help="Optional team filter."),
    opponent: str = typer.Option(None, "--opponent", help="Optional opponent filter."),
    home_only: bool = typer.Option(False, "--home-only", help="Only include home games."),
    away_only: bool = typer.Option(False, "--away-only", help="Only include away games."),
    wins_only: bool = typer.Option(False, "--wins-only", help="Only include wins."),
    losses_only: bool = typer.Option(False, "--losses-only", help="Only include losses."),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        player_compare_run,
        player_a=player_a,
        player_b=player_b,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command("team-compare", help="Compare two teams over the same filtered sample.")
def team_compare(
    team_a: str = typer.Option(..., "--team-a", help="First team abbreviation or name."),
    team_b: str = typer.Option(..., "--team-b", help="Second team abbreviation or name."),
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    opponent: str = typer.Option(None, "--opponent", help="Optional opponent filter."),
    home_only: bool = typer.Option(False, "--home-only", help="Only include home games."),
    away_only: bool = typer.Option(False, "--away-only", help="Only include away games."),
    wins_only: bool = typer.Option(False, "--wins-only", help="Only include wins."),
    losses_only: bool = typer.Option(False, "--losses-only", help="Only include losses."),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        team_compare_run,
        team_a=team_a,
        team_b=team_b,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command(
    "player-split-summary",
    help="Summarize a player sample by split buckets like home vs away or wins vs losses.",
)
def player_split_summary(
    split: str = typer.Option(..., "--split", help="Split type: home_away or wins_losses."),
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    player: str = typer.Option(None, "--player", help="Exact player name."),
    team: str = typer.Option(None, "--team", help="Optional team filter."),
    opponent: str = typer.Option(None, "--opponent", help="Optional opponent filter."),
    stat: str = typer.Option(None, "--stat", help="Optional stat threshold field."),
    min_value: float = typer.Option(
        None, "--min-value", help="Minimum value for the selected stat."
    ),
    max_value: float = typer.Option(
        None, "--max-value", help="Maximum value for the selected stat."
    ),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        player_split_summary_run,
        split=split,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        player=player,
        team=team,
        opponent=opponent,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )


@app.command(
    "team-split-summary",
    help="Summarize a team sample by split buckets like home vs away or wins vs losses.",
)
def team_split_summary(
    split: str = typer.Option(..., "--split", help="Split type: home_away or wins_losses."),
    season: str = typer.Option(None, help="Single season, for example 2025-26."),
    start_season: str = typer.Option(
        None, "--start-season", help="Start season for a multi-season query."
    ),
    end_season: str = typer.Option(
        None, "--end-season", help="End season for a multi-season query."
    ),
    season_type: str = typer.Option(
        "Regular Season", "--season-type", help="Regular Season or Playoffs."
    ),
    team: str = typer.Option(None, "--team", help="Team abbreviation or full team name."),
    opponent: str = typer.Option(None, "--opponent", help="Optional opponent filter."),
    stat: str = typer.Option(None, "--stat", help="Optional stat threshold field."),
    min_value: float = typer.Option(
        None, "--min-value", help="Minimum value for the selected stat."
    ),
    max_value: float = typer.Option(
        None, "--max-value", help="Maximum value for the selected stat."
    ),
    last_n: int = typer.Option(
        None, "--last-n", help="Only use the most recent N games after filtering."
    ),
    csv: str = typer.Option(None, "--csv", help="Optional path to save raw CSV/tabular output."),
    txt: str = typer.Option(None, "--txt", help="Optional path to save raw text output."),
    json_path: str = typer.Option(None, "--json", help="Optional path to save raw output as JSON."),
):
    _run_and_handle_exports(
        team_split_summary_run,
        split=split,
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        team=team,
        opponent=opponent,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        last_n=last_n,
        csv=csv,
        txt=txt,
        json_path=json_path,
    )
