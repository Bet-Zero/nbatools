from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import (
    load_player_games_for_seasons,
)
from nbatools.commands.player_advanced_metrics import (
    build_player_team_context,
    compute_grouped_sample_advanced_metrics,
    load_team_games_for_seasons,
)
from nbatools.commands.structured_results import NoResult, SplitSummaryResult

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
    "fg_pct": "fg_pct",
    "fg3_pct": "fg3_pct",
    "ft_pct": "ft_pct",
    "efg_pct": "efg_pct",
    "ts_pct": "ts_pct",
    "usg_pct": "usg_pct",
    "ast_pct": "ast_pct",
    "reb_pct": "reb_pct",
}

ALLOWED_SPLITS = {"home_away", "wins_losses"}


def apply_base_filters(
    df: pd.DataFrame,
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    out["game_date"] = pd.to_datetime(out["game_date"])

    if player:
        out = out[out["player_name"].astype(str).str.upper() == player.upper()].copy()

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
            "minutes_avg": None,
            "pts_avg": None,
            "reb_avg": None,
            "ast_avg": None,
            "stl_avg": None,
            "blk_avg": None,
            "fg3m_avg": None,
            "efg_pct_avg": None,
            "ts_pct_avg": None,
            "usg_pct_avg": None,
            "ast_pct_avg": None,
            "reb_pct_avg": None,
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
        "minutes_avg": round(df["minutes"].mean(), 3) if "minutes" in df.columns else None,
        "pts_avg": round(df["pts"].mean(), 3) if "pts" in df.columns else None,
        "reb_avg": round(df["reb"].mean(), 3) if "reb" in df.columns else None,
        "ast_avg": round(df["ast"].mean(), 3) if "ast" in df.columns else None,
        "stl_avg": round(df["stl"].mean(), 3) if "stl" in df.columns else None,
        "blk_avg": round(df["blk"].mean(), 3) if "blk" in df.columns else None,
        "fg3m_avg": round(df["fg3m"].mean(), 3) if "fg3m" in df.columns else None,
        "efg_pct_avg": round(df["efg_pct"].mean(), 3) if "efg_pct" in df.columns else None,
        "ts_pct_avg": round(df["ts_pct"].mean(), 3) if "ts_pct" in df.columns else None,
        "plus_minus_avg": round(df["plus_minus"].mean(), 3) if "plus_minus" in df.columns else None,
    }


def build_result(
    split: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
    df: pd.DataFrame | None = None,
) -> SplitSummaryResult | NoResult:
    split = split.lower()
    if split not in ALLOWED_SPLITS:
        raise ValueError(f"Unsupported split: {split}. Allowed: {sorted(ALLOWED_SPLITS)}")

    seasons = resolve_seasons(season, start_season, end_season)

    if df is None:
        df = load_player_games_for_seasons(seasons, season_type)

        required = [
            "game_id",
            "game_date",
            "season",
            "season_type",
            "player_id",
            "player_name",
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
            player=player,
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
        return NoResult(query_class="split_summary")

    player_name = df["player_name"].mode().iloc[0] if "player_name" in df.columns else player
    season_min = df["season"].min()
    season_max = df["season"].max()

    if split == "home_away":
        df["bucket"] = df["is_home"].map({1: "home"}).fillna("away")
    else:
        df["bucket"] = df["wl"].map({"W": "wins", "L": "losses"})

    split_df = df[df["bucket"].notna()].copy()

    if split_df.empty:
        return NoResult(query_class="split_summary")

    team_df = load_team_games_for_seasons(seasons, season_type)
    context_df = build_player_team_context(split_df, team_df)

    summary = pd.DataFrame(
        [
            {
                "player_name": player_name,
                "season_start": season_min,
                "season_end": season_max,
                "season_type": season_type,
                "split": split,
                "games_total": int(len(split_df)),
            }
        ]
    )

    bucket_rows = []
    for bucket_name, bucket_df in split_df.groupby("bucket", sort=False):
        bucket_rows.append(_summarize_bucket(bucket_df, bucket_name))

    split_comparison = pd.DataFrame(bucket_rows)

    grouped_adv = compute_grouped_sample_advanced_metrics(context_df, "bucket")
    split_comparison = split_comparison.merge(grouped_adv, on="bucket", how="left")

    bucket_order = {
        "home": 0,
        "away": 1,
        "wins": 0,
        "losses": 1,
    }
    split_comparison["_sort"] = split_comparison["bucket"].map(bucket_order).fillna(999)
    split_comparison = (
        split_comparison.sort_values(["_sort", "bucket"])
        .drop(columns="_sort")
        .reset_index(drop=True)
    )

    return SplitSummaryResult(
        summary=summary,
        split_comparison=split_comparison,
    )


def run(
    split: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
    df: pd.DataFrame | None = None,
) -> None:
    result = build_result(
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
        df=df,
    )
    print(result.to_labeled_text(), end="")
