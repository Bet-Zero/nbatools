from pathlib import Path

import pandas as pd

from nbatools.commands.structured_results import LeaderboardResult

ALLOWED_STATS = {
    "pts": "pts",
    "reb": "reb",
    "ast": "ast",
    "stl": "stl",
    "blk": "blk",
    "fgm": "fgm",
    "fga": "fga",
    "fg3m": "fg3m",
    "fg3a": "fg3a",
    "ftm": "ftm",
    "fta": "fta",
    "tov": "tov",
    "pf": "pf",
    "minutes": "minutes",
    "plus_minus": "plus_minus",
    "oreb": "oreb",
    "dreb": "dreb",
}


def build_result(
    season: str,
    stat: str,
    limit: int = 10,
    season_type: str = "Regular Season",
    ascending: bool = False,
) -> LeaderboardResult:
    safe = season_type.lower().replace(" ", "_")
    path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    stat = stat.lower().strip()
    if stat not in ALLOWED_STATS:
        allowed = ", ".join(sorted(ALLOWED_STATS.keys()))
        raise ValueError(f"Unsupported stat '{stat}'. Allowed stats: {allowed}")

    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    df = pd.read_csv(path)

    col = ALLOWED_STATS[stat]
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in {path}")

    out_cols = [
        "team_name",
        "team_abbr",
        "team_id",
        "game_date",
        "game_id",
        col,
        "opponent_team_abbr",
        "is_home",
        "is_away",
        "wl",
        "season",
        "season_type",
    ]

    missing = [c for c in out_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for output: {missing}")

    result = (
        df[out_cols]
        .sort_values(
            by=[col, "game_date", "team_name"],
            ascending=[ascending, True, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )

    result.insert(0, "rank", range(1, len(result) + 1))

    return LeaderboardResult(leaders=result)


def run(
    season: str,
    stat: str,
    limit: int = 10,
    season_type: str = "Regular Season",
    ascending: bool = False,
) -> None:
    result = build_result(
        season=season,
        stat=stat,
        limit=limit,
        season_type=season_type,
        ascending=ascending,
    )
    print(result.to_labeled_text(), end="")
