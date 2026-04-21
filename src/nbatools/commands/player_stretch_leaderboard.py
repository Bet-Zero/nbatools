"""Rolling-window leaderboard for player stretch queries."""

from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import (
    filter_by_opponent_player,
    filter_without_player,
    load_player_games_for_seasons,
)
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.player_game_summary import _apply_filters
from nbatools.commands.structured_results import LeaderboardResult, NoResult

RAW_AVG_METRICS: dict[str, str] = {
    "pts": "pts",
    "reb": "reb",
    "ast": "ast",
    "stl": "stl",
    "blk": "blk",
    "fg3m": "fg3m",
    "minutes": "minutes",
    "plus_minus": "plus_minus",
}

PERCENTAGE_COMPONENTS: dict[str, tuple[str, str]] = {
    "fg_pct": ("fgm", "fga"),
    "fg3_pct": ("fg3m", "fg3a"),
    "ft_pct": ("ftm", "fta"),
}

SUPPORTED_STRETCH_METRICS = {
    *RAW_AVG_METRICS.keys(),
    *PERCENTAGE_COMPONENTS.keys(),
    "efg_pct",
    "ts_pct",
    "game_score",
}


def _rolling_sum(frame: pd.DataFrame, column: str, window_size: int) -> pd.Series:
    return frame.groupby("player_id")[column].transform(
        lambda series: series.rolling(window_size, min_periods=window_size).sum()
    )


def _rolling_mean(frame: pd.DataFrame, column: str, window_size: int) -> pd.Series:
    return frame.groupby("player_id")[column].transform(
        lambda series: series.rolling(window_size, min_periods=window_size).mean()
    )


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, pd.NA)


def _compute_game_score(frame: pd.DataFrame) -> pd.Series:
    numeric_cols = [
        "pts",
        "fgm",
        "fga",
        "fta",
        "ftm",
        "oreb",
        "dreb",
        "stl",
        "ast",
        "blk",
        "pf",
        "tov",
    ]
    out = frame[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    return (
        out["pts"]
        + 0.4 * out["fgm"]
        - 0.7 * out["fga"]
        - 0.4 * (out["fta"] - out["ftm"])
        + 0.7 * out["oreb"]
        + 0.3 * out["dreb"]
        + out["stl"]
        + 0.7 * out["ast"]
        + 0.7 * out["blk"]
        - 0.4 * out["pf"]
        - out["tov"]
    )


def _compute_stretch_values(
    frame: pd.DataFrame,
    *,
    stretch_metric: str,
    window_size: int,
) -> pd.DataFrame:
    out = frame.copy()

    if stretch_metric in RAW_AVG_METRICS:
        out["stretch_value"] = _rolling_mean(out, RAW_AVG_METRICS[stretch_metric], window_size)
    elif stretch_metric in PERCENTAGE_COMPONENTS:
        numerator_col, denominator_col = PERCENTAGE_COMPONENTS[stretch_metric]
        numerator = _rolling_sum(out, numerator_col, window_size)
        denominator = _rolling_sum(out, denominator_col, window_size)
        out["stretch_value"] = _safe_divide(numerator, denominator)
    elif stretch_metric == "efg_pct":
        fgm = _rolling_sum(out, "fgm", window_size)
        fg3m = _rolling_sum(out, "fg3m", window_size)
        fga = _rolling_sum(out, "fga", window_size)
        out["stretch_value"] = _safe_divide(fgm + 0.5 * fg3m, fga)
    elif stretch_metric == "ts_pct":
        pts = _rolling_sum(out, "pts", window_size)
        fga = _rolling_sum(out, "fga", window_size)
        fta = _rolling_sum(out, "fta", window_size)
        out["stretch_value"] = _safe_divide(pts, 2 * (fga + 0.44 * fta))
    elif stretch_metric == "game_score":
        out["game_score"] = _compute_game_score(out)
        out["stretch_value"] = _rolling_mean(out, "game_score", window_size)
    else:
        raise ValueError(f"Unsupported stretch metric: {stretch_metric}")

    out["window_start_date"] = out.groupby("player_id")["game_date"].shift(window_size - 1)
    out["window_start_season"] = out.groupby("player_id")["season"].shift(window_size - 1)
    return out


def build_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    opponent: str | list[str] | tuple[str, ...] | None = None,
    opponent_player: str | None = None,
    without_player: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    last_n: int | None = None,
    window_size: int | None = None,
    stretch_metric: str = "game_score",
    limit: int = 10,
) -> LeaderboardResult | NoResult:
    if window_size is None or window_size <= 0:
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            notes=["window_size must be greater than 0"],
        )

    if stretch_metric not in SUPPORTED_STRETCH_METRICS:
        allowed = ", ".join(sorted(SUPPORTED_STRETCH_METRICS))
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            notes=[f"Unsupported stretch metric '{stretch_metric}'. Allowed metrics: {allowed}"],
        )

    if limit <= 0:
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            notes=["limit must be greater than 0"],
        )

    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_player_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    df = _apply_filters(
        df=df,
        player=player,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
        start_date=start_date,
        end_date=end_date,
    )

    if opponent_player and not df.empty:
        df = filter_by_opponent_player(df, opponent_player, seasons, season_type)

    if without_player and not df.empty:
        df = filter_without_player(df, without_player, seasons, season_type, team=team)

    if df.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    df = df.copy()
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce").dt.normalize()
    df = df.sort_values(["player_id", "game_date", "game_id"]).reset_index(drop=True)

    if last_n is not None:
        if last_n <= 0:
            return NoResult(
                query_class="leaderboard",
                reason="unsupported",
                notes=["last_n must be greater than 0"],
            )
        df = df.groupby("player_id", group_keys=False).tail(last_n).copy()

    df = _compute_stretch_values(
        df,
        stretch_metric=stretch_metric,
        window_size=window_size,
    )

    windows = df[df["stretch_value"].notna()].copy()
    if windows.empty:
        return NoResult(
            query_class="leaderboard",
            reason="no_match",
            notes=[f"No players had at least {window_size} games in the filtered sample"],
        )

    windows["stretch_value"] = pd.to_numeric(windows["stretch_value"], errors="coerce").round(3)
    windows = windows.sort_values(
        ["stretch_value", "game_date", "player_name"],
        ascending=[False, False, True],
    ).head(limit)

    result = windows[
        [
            "player_name",
            "player_id",
            "team_abbr",
            "window_start_date",
            "game_date",
            "window_start_season",
            "season",
            "stretch_value",
        ]
    ].rename(
        columns={
            "game_date": "window_end_date",
            "season": "window_end_season",
        }
    )
    result.insert(3, "window_size", window_size)
    result.insert(4, "stretch_metric", stretch_metric)
    result.insert(8, "games_in_window", window_size)
    result.insert(0, "rank", range(1, len(result) + 1))
    result = result.reset_index(drop=True)

    return LeaderboardResult(
        leaders=result,
        current_through=compute_current_through_for_seasons(seasons, season_type),
    )


def run(
    season: str,
    window_size: int,
    stretch_metric: str = "game_score",
    limit: int = 10,
    season_type: str = "Regular Season",
) -> None:
    result = build_result(
        season=season,
        window_size=window_size,
        stretch_metric=stretch_metric,
        limit=limit,
        season_type=season_type,
    )
    if isinstance(result, NoResult):
        print("no matching stretches")
        return
    print(result.to_labeled_text(), end="")
