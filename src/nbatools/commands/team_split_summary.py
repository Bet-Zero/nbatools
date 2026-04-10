import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_games_for_seasons

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
    "efg_pct": "efg_pct",
    "ts_pct": "ts_pct",
}

ALLOWED_SPLITS = {"home_away", "wins_losses"}


def apply_base_filters(
    df: pd.DataFrame,
    team: str | None = None,
    opponent: str | None = None,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    out["game_date"] = pd.to_datetime(out["game_date"])

    if team:
        team_upper = team.upper()
        out = out[
            out["team_abbr"].astype(str).str.upper().eq(team_upper)
            | out["team_name"].astype(str).str.upper().eq(team_upper)
        ].copy()

    if opponent:
        opp_upper = opponent.upper()
        out = out[
            out["opponent_team_abbr"].astype(str).str.upper().eq(opp_upper)
            | out["opponent_team_name"].astype(str).str.upper().eq(opp_upper)
        ].copy()

    if stat:
        stat = stat.lower()
        if stat not in ALLOWED_STATS:
            raise ValueError(f"Unsupported stat: {stat}")
        stat_col = ALLOWED_STATS[stat]

        if min_value is not None:
            out = out[out[stat_col] >= min_value].copy()

        if max_value is not None:
            out = out[out[stat_col] <= max_value].copy()

    out = out.sort_values(["game_date", "game_id"], ascending=[False, False]).copy()

    if last_n is not None:
        if last_n <= 0:
            raise ValueError("last_n must be greater than 0")
        out = out.head(last_n).copy()

    return out


def _summarize_bucket(df: pd.DataFrame, bucket_name: str) -> dict:
    if df.empty:
        return {
            "bucket": bucket_name,
            "games": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": None,
            "pts_avg": None,
            "reb_avg": None,
            "ast_avg": None,
            "stl_avg": None,
            "blk_avg": None,
            "fg3m_avg": None,
            "tov_avg": None,
            "efg_pct_avg": None,
            "ts_pct_avg": None,
            "plus_minus_avg": None,
        }

    wins = int((df["wl"] == "W").sum())
    losses = int((df["wl"] == "L").sum())
    games = int(len(df))

    return {
        "bucket": bucket_name,
        "games": games,
        "wins": wins,
        "losses": losses,
        "win_pct": round(wins / games, 3) if games else None,
        "pts_avg": round(df["pts"].mean(), 3) if "pts" in df.columns else None,
        "reb_avg": round(df["reb"].mean(), 3) if "reb" in df.columns else None,
        "ast_avg": round(df["ast"].mean(), 3) if "ast" in df.columns else None,
        "stl_avg": round(df["stl"].mean(), 3) if "stl" in df.columns else None,
        "blk_avg": round(df["blk"].mean(), 3) if "blk" in df.columns else None,
        "fg3m_avg": round(df["fg3m"].mean(), 3) if "fg3m" in df.columns else None,
        "tov_avg": round(df["tov"].mean(), 3) if "tov" in df.columns else None,
        "efg_pct_avg": round(df["efg_pct"].mean(), 3) if "efg_pct" in df.columns else None,
        "ts_pct_avg": round(df["ts_pct"].mean(), 3) if "ts_pct" in df.columns else None,
        "plus_minus_avg": round(df["plus_minus"].mean(), 3) if "plus_minus" in df.columns else None,
    }


def run(
    split: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    opponent: str | None = None,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
    df: pd.DataFrame | None = None,
) -> None:
    split = split.lower()
    if split not in ALLOWED_SPLITS:
        raise ValueError(f"Unsupported split: {split}. Allowed: {sorted(ALLOWED_SPLITS)}")

    seasons = resolve_seasons(season, start_season, end_season)

    if df is None:
        df = load_team_games_for_seasons(seasons, season_type)

        required = [
            "game_id",
            "game_date",
            "season",
            "season_type",
            "team_id",
            "team_abbr",
            "team_name",
            "opponent_team_id",
            "opponent_team_abbr",
            "opponent_team_name",
            "is_home",
            "is_away",
            "wl",
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = apply_base_filters(
            df=df,
            team=team,
            opponent=opponent,
            stat=stat,
            min_value=min_value,
            max_value=max_value,
            last_n=last_n,
        )
    else:
        df = df.copy()
        if "game_date" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date"])

    if df.empty:
        print("SUMMARY")
        print("no matching games")
        return

    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    season_min = df["season"].min()
    season_max = df["season"].max()

    if split == "home_away":
        bucket_a_name = "home"
        bucket_b_name = "away"
        bucket_a = df[df["is_home"] == 1].copy()
        bucket_b = df[df["is_away"] == 1].copy()
    else:
        bucket_a_name = "wins"
        bucket_b_name = "losses"
        bucket_a = df[df["wl"] == "W"].copy()
        bucket_b = df[df["wl"] == "L"].copy()

    summary = pd.DataFrame(
        [
            {
                "team_name": team_name,
                "season_start": season_min,
                "season_end": season_max,
                "season_type": season_type,
                "split": split,
                "games_total": int(len(df)),
            }
        ]
    )

    split_comparison = pd.DataFrame(
        [
            _summarize_bucket(bucket_a, bucket_a_name),
            _summarize_bucket(bucket_b, bucket_b_name),
        ]
    )

    print("SUMMARY")
    print(summary.to_csv(index=False))

    print("SPLIT_COMPARISON")
    print(split_comparison.to_csv(index=False))
