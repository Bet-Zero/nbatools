from pathlib import Path

import pandas as pd

from nbatools.commands.freshness import compute_current_through
from nbatools.commands.structured_results import LeaderboardResult, NoResult

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
}


def build_result(
    season: str,
    stat: str,
    limit: int = 10,
    season_type: str = "Regular Season",
    ascending: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    last_n: int | None = None,
    opponent: str | None = None,
) -> LeaderboardResult | NoResult:
    safe = season_type.lower().replace(" ", "_")
    path = Path(f"data/raw/player_game_stats/{season}_{safe}.csv")

    if not path.exists():
        return NoResult(query_class="leaderboard", reason="no_data")

    stat = stat.lower().strip()
    if stat not in ALLOWED_STATS:
        allowed = ", ".join(sorted(ALLOWED_STATS.keys()))
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            result_status="no_result",
            notes=[f"Unsupported stat '{stat}'. Allowed stats: {allowed}"],
        )

    if limit <= 0:
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            result_status="no_result",
            notes=["limit must be greater than 0"],
        )

    df = pd.read_csv(path)

    # Player game logs lack a 'wl' column — derive it from team game stats
    # so that wins_only / losses_only filters can be applied.
    if (wins_only or losses_only) and "wl" not in df.columns:
        team_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")
        if team_path.exists():
            team_wl = pd.read_csv(team_path, usecols=["game_id", "team_id", "wl"])
            team_wl = team_wl.drop_duplicates(subset=["game_id", "team_id"])
            df = df.merge(team_wl, on=["game_id", "team_id"], how="left")

    col = ALLOWED_STATS[stat]
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in {path}")

    # Apply filters
    if "game_date" in df.columns:
        df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")

    if start_date is not None and "game_date" in df.columns:
        df = df[df["game_date"] >= pd.to_datetime(start_date)].copy()

    if end_date is not None and "game_date" in df.columns:
        df = df[df["game_date"] <= pd.to_datetime(end_date)].copy()

    if opponent:
        opp_upper = opponent.upper()
        opp_mask = pd.Series(False, index=df.index)
        if "opponent_team_abbr" in df.columns:
            opp_mask = opp_mask | df["opponent_team_abbr"].astype(str).str.upper().eq(opp_upper)
        df = df[opp_mask].copy()

    if home_only and "is_home" in df.columns:
        df = df[df["is_home"] == 1].copy()

    if away_only and "is_away" in df.columns:
        df = df[df["is_away"] == 1].copy()

    if wins_only and "wl" in df.columns:
        df = df[df["wl"] == "W"].copy()

    if losses_only and "wl" in df.columns:
        df = df[df["wl"] == "L"].copy()

    if last_n is not None and last_n > 0 and "game_date" in df.columns:
        df = df.sort_values(["game_date", "game_id"], ascending=[False, False]).head(last_n).copy()

    if df.empty:
        return NoResult(
            query_class="leaderboard",
            reason="no_match",
            notes=["No games matched the specified filters"],
        )

    out_cols = [
        "player_name",
        "player_id",
        "team_abbr",
        "game_date",
        "game_id",
        col,
        "opponent_team_abbr",
        "is_home",
        "is_away",
        "season",
        "season_type",
    ]

    missing = [c for c in out_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for output: {missing}")

    result = (
        df[out_cols]
        .sort_values(
            by=[col, "game_date", "player_name"],
            ascending=[ascending, True, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )

    result.insert(0, "rank", range(1, len(result) + 1))

    current_through = compute_current_through(season, season_type)

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
    )


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
    if isinstance(result, NoResult):
        print("no matching games")
        return
    print(result.to_labeled_text(), end="")
