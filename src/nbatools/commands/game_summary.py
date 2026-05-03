from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import (
    build_opponent_mask,
    describe_opponent_filter,
    filter_without_player,
    load_team_games_for_seasons,
)
from nbatools.commands.freshness import compute_current_through_for_seasons
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
    "efg_pct": "efg_pct",
    "ts_pct": "ts_pct",
}

GAME_LOG_COLUMNS = [
    "game_date",
    "game_id",
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
    "pts",
    "reb",
    "ast",
    "fg3m",
    "fg3a",
    "tov",
    "plus_minus",
    "fg_pct",
    "fg3_pct",
    "ft_pct",
    "efg_pct",
    "ts_pct",
]


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def _apply_filters(
    df: pd.DataFrame,
    team: str | None = None,
    opponent: str | list[str] | tuple[str, ...] | None = None,
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

    if team:
        team_upper = team.upper()
        out = out[
            out["team_abbr"].astype(str).str.upper().eq(team_upper)
            | out["team_name"].astype(str).str.upper().eq(team_upper)
        ].copy()

    if opponent:
        out = out[build_opponent_mask(out, opponent)].copy()

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


def _build_game_log_section(df: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col in GAME_LOG_COLUMNS if col in df.columns]
    game_log = (
        df.sort_values(["game_date", "game_id"], ascending=[True, True])
        .loc[:, cols]
        .reset_index(drop=True)
        .copy()
    )
    if "pts" in game_log.columns and "plus_minus" in game_log.columns:
        game_log["opponent_pts"] = (
            pd.to_numeric(game_log["pts"], errors="coerce")
            - pd.to_numeric(game_log["plus_minus"], errors="coerce")
        ).round(3)
    if "game_date" in game_log.columns:
        game_log["game_date"] = pd.to_datetime(game_log["game_date"]).dt.strftime("%Y-%m-%d")
    return game_log


def build_result(
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    opponent: str | None = None,
    without_player: str | None = None,
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
            df = load_team_games_for_seasons(seasons, season_type)
        except FileNotFoundError:
            return NoResult(query_class="summary", reason="no_data")

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

        df = _apply_filters(
            df=df,
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

        if without_player and not df.empty:
            df = filter_without_player(df, without_player, seasons, season_type, team=team)
    else:
        df = df.copy()
        if "game_date" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date"]).dt.normalize()

    if df.empty:
        return NoResult(query_class="summary")

    numeric_cols = [
        "minutes",
        "pts",
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
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
    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else None

    summary_row = {
        "team_name": team_name,
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

    summary = pd.DataFrame([summary_row])
    include_game_log = (
        last_n is not None or start_date is not None or end_date is not None or total_games <= 5
    )
    game_log = _build_game_log_section(df) if include_game_log else None

    agg_map = {
        "games": ("game_id", "count"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
    }
    for col in ["pts", "reb", "ast", "fg3m", "tov", "plus_minus", "efg_pct", "ts_pct"]:
        if col in df.columns:
            agg_map[f"{col}_avg"] = (col, "mean")

    by_season = (
        df.groupby("season", as_index=False)
        .agg(**agg_map)
        .round(3)
        .sort_values("season")
        .reset_index(drop=True)
    )

    current_through = compute_current_through_for_seasons(seasons, season_type)

    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(
            f"multi-season summary aggregated from game logs across {seasons[0]} to {seasons[-1]}"
        )
    if opponent:
        caveats.append(f"filtered to games vs {describe_opponent_filter(opponent)}")
    if home_only:
        caveats.append("filtered to home games only")
    if away_only:
        caveats.append("filtered to away games only")
    if wins_only:
        caveats.append("filtered to wins only")
    if losses_only:
        caveats.append("filtered to losses only")
    if start_date or end_date:
        date_parts = []
        if start_date:
            date_parts.append(f"from {start_date}")
        if end_date:
            date_parts.append(f"to {end_date}")
        caveats.append(f"date window: {' '.join(date_parts)}")
    if stat and (min_value is not None or max_value is not None):
        threshold_parts = [f"games where {stat}"]
        if min_value is not None:
            threshold_parts.append(f">= {min_value}")
        if max_value is not None:
            threshold_parts.append(f"<= {max_value}")
        caveats.append(" ".join(threshold_parts))

    return SummaryResult(
        summary=summary,
        by_season=by_season,
        game_log=game_log,
        current_through=current_through,
        caveats=caveats,
    )


def run(
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
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
