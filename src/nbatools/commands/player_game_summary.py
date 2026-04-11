from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import (
    load_player_games_for_seasons,
)
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.player_advanced_metrics import (
    add_sample_advanced_metrics_to_summary_row,
    build_player_team_context,
    compute_season_grouped_sample_advanced_metrics,
    load_team_games_for_seasons,
)
from nbatools.commands.structured_results import NoResult, SummaryResult

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


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def _apply_filters(
    df: pd.DataFrame,
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    out = df.copy()
    out["game_date"] = pd.to_datetime(out["game_date"]).dt.normalize()

    start_ts = _normalize_date_value(start_date)
    end_ts = _normalize_date_value(end_date)
    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise ValueError("start_date must be less than or equal to end_date")

    if start_ts is not None:
        out = out[out["game_date"] >= start_ts].copy()

    if end_ts is not None:
        out = out[out["game_date"] <= end_ts].copy()

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

    if home_only:
        out = out[out["is_home"] == 1].copy()

    if away_only:
        out = out[out["is_away"] == 1].copy()

    if wins_only:
        out = out[out["wl"] == "W"].copy()

    if losses_only:
        out = out[out["wl"] == "L"].copy()

    if stat:
        stat = stat.lower()
        if stat not in ALLOWED_STATS:
            raise ValueError(f"Unsupported stat: {stat}")
        stat_col = ALLOWED_STATS[stat]

        if min_value is not None:
            out = out[out[stat_col] >= min_value].copy()

        if max_value is not None:
            out = out[out[stat_col] <= max_value].copy()

    if out.empty:
        return out

    if last_n is not None:
        if last_n <= 0:
            raise ValueError("last_n must be greater than 0")
        out = (
            out.sort_values(["game_date", "game_id"], ascending=[False, False]).head(last_n).copy()
        )

    return out


def build_result(
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    df: pd.DataFrame | None = None,
) -> SummaryResult | NoResult:
    seasons = resolve_seasons(season, start_season, end_season)

    if home_only and away_only:
        raise ValueError("Cannot use both home_only and away_only")

    if wins_only and losses_only:
        raise ValueError("Cannot use both wins_only and losses_only")

    if df is None:
        try:
            df = load_player_games_for_seasons(seasons, season_type)
        except FileNotFoundError:
            return NoResult(query_class="summary", reason="no_data")

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

        df = _apply_filters(
            df=df,
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
            start_date=start_date,
            end_date=end_date,
        )
    else:
        df = df.copy()
        if "game_date" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date"]).dt.normalize()

    if df.empty:
        return NoResult(query_class="summary")

    team_df = load_team_games_for_seasons(seasons, season_type)
    context_df = build_player_team_context(df, team_df)

    numeric_cols = [
        "minutes",
        "pts",
        "fgm",
        "fga",
        "fg_pct",
        "fg3m",
        "fg3a",
        "fg3_pct",
        "ftm",
        "fta",
        "ft_pct",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "plus_minus",
        "efg_pct",
        "ts_pct",
    ]
    numeric_cols = [c for c in numeric_cols if c in df.columns]

    wins = int((df["wl"] == "W").sum())
    losses = int((df["wl"] == "L").sum())
    total_games = int(len(df))
    win_pct = round(wins / total_games, 3) if total_games > 0 else None

    season_min = df["season"].min()
    season_max = df["season"].max()
    player_name = df["player_name"].mode().iloc[0] if "player_name" in df.columns else None

    summary_row = {
        "player_name": player_name,
        "season_start": season_min,
        "season_end": season_max,
        "season_type": season_type,
        "games": total_games,
        "wins": wins,
        "losses": losses,
        "win_pct": win_pct,
    }

    for col in numeric_cols:
        summary_row[f"{col}_avg"] = round(df[col].mean(), 3)
        summary_row[f"{col}_sum"] = round(df[col].sum(), 3)

    summary_row = add_sample_advanced_metrics_to_summary_row(
        context_df,
        summary_row,
        include_sum_fields=True,
    )

    summary = pd.DataFrame([summary_row])

    agg_map = {
        "games": ("game_id", "count"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
    }
    for col in ["pts", "reb", "ast", "minutes", "efg_pct", "ts_pct"]:
        if col in df.columns:
            agg_map[f"{col}_avg"] = (col, "mean")

    by_season = (
        df.groupby("season", as_index=False)
        .agg(**agg_map)
        .round(3)
        .sort_values("season")
        .reset_index(drop=True)
    )

    season_adv = compute_season_grouped_sample_advanced_metrics(context_df)
    by_season = by_season.merge(season_adv, on="season", how="left")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return SummaryResult(
        summary=summary,
        by_season=by_season,
        current_through=current_through,
    )


def run(
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    last_n: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    df: pd.DataFrame | None = None,
) -> None:
    result = build_result(
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
        start_date=start_date,
        end_date=end_date,
        df=df,
    )
    print(result.to_labeled_text(), end="")
