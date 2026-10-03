"""Rolling-window leaderboard for team stretch queries.

"Celtics best 10 game stretch" or "which team had the best 10 game stretch":
every run of N consecutive team games in the filtered sample, scored by
the requested metric. Wins (point differential breaks ties) is the default.
Windows stay inside one season, so the offseason never joins two runs.
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_games_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.game_finder import _apply_filters
from nbatools.commands.structured_results import LeaderboardResult, NoResult

PER_GAME_METRICS = {"pts", "reb", "ast", "stl", "blk", "fg3m", "tov", "plus_minus", "opp_pts"}
PERCENTAGE_COMPONENTS: dict[str, tuple[str, str]] = {
    "fg_pct": ("fgm", "fga"),
    "fg3_pct": ("fg3m", "fg3a"),
    "ft_pct": ("ftm", "fta"),
}
SUPPORTED_TEAM_STRETCH_METRICS = {
    "wins",
    *PER_GAME_METRICS,
    *PERCENTAGE_COMPONENTS,
    "efg_pct",
    "ts_pct",
    "off_rating",
    "def_rating",
    "net_rating",
}
RATING_METRICS = {"off_rating", "def_rating", "net_rating"}
# Metrics where a smaller number is the better stretch.
LOWER_IS_BETTER = {"opp_pts", "tov", "def_rating"}

_GROUP = ["team_id", "season"]
_NUMERIC = [
    "pts",
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "oreb",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
]


def _rolling_sum(frame: pd.DataFrame, column: str, window_size: int) -> pd.Series:
    return frame.groupby(_GROUP)[column].transform(
        lambda series: series.rolling(window_size, min_periods=window_size).sum()
    )


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.where(denominator != 0)


def _compute_windows(frame: pd.DataFrame, metric: str, window_size: int) -> pd.DataFrame:
    out = frame.copy()
    for column in [*_NUMERIC, "plus_minus"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    out["win"] = out["wl"].astype(str).eq("W").astype(int)
    out["opp_pts"] = out["pts"] - out["plus_minus"]
    # Box-score possession estimate (FGA - OREB + TOV + 0.44 * FTA).
    out["poss"] = out["fga"] - out["oreb"] + out["tov"] + 0.44 * out["fta"]

    def total(column: str) -> pd.Series:
        return _rolling_sum(out, column, window_size)

    out["wins"] = total("win")
    out["net_per_game"] = total("plus_minus") / window_size
    if metric == "wins":
        out["stretch_value"] = out["wins"]
    elif metric in PER_GAME_METRICS:
        out["stretch_value"] = total(metric) / window_size
    elif metric in PERCENTAGE_COMPONENTS:
        made, attempted = PERCENTAGE_COMPONENTS[metric]
        out["stretch_value"] = _ratio(total(made), total(attempted))
    elif metric == "efg_pct":
        out["stretch_value"] = _ratio(total("fgm") + 0.5 * total("fg3m"), total("fga"))
    elif metric == "ts_pct":
        out["stretch_value"] = _ratio(total("pts"), 2 * (total("fga") + 0.44 * total("fta")))
    elif metric in RATING_METRICS:
        points = {
            "off_rating": total("pts"),
            "def_rating": total("opp_pts"),
            "net_rating": total("plus_minus"),
        }[metric]
        out["stretch_value"] = 100 * _ratio(points, total("poss"))
    else:
        raise ValueError(f"Unsupported team stretch metric: {metric}")

    grouped = out.groupby(_GROUP)
    out["window_start_date"] = grouped["game_date"].shift(window_size - 1)
    out["window_start_game_id"] = grouped["game_id"].shift(window_size - 1)
    out["_pos"] = grouped.cumcount()
    return out


def _pick_windows(windows: pd.DataFrame, window_size: int, *, per_team: int | None) -> pd.DataFrame:
    """Best windows first, never two that share a game of the same team.

    Overlapping windows of one team are the same hot stretch counted again,
    so each team keeps its best window and then only windows clear of it.
    """
    kept: list[int] = []
    taken: dict[tuple, list[int]] = {}
    for index, row in windows.iterrows():
        key = (row["team_id"], row["season"])
        ends = taken.setdefault(key, [])
        team_count = sum(len(v) for k, v in taken.items() if k[0] == row["team_id"])
        if per_team is not None and team_count >= per_team:
            continue
        if any(abs(row["_pos"] - end) < window_size for end in ends):
            continue
        ends.append(row["_pos"])
        kept.append(index)
    return windows.loc[kept]


def build_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    opponent: str | list[str] | tuple[str, ...] | None = None,
    home_only: bool = False,
    away_only: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    last_n: int | None = None,
    window_size: int | None = None,
    stretch_metric: str = "wins",
    worst: bool = False,
    limit: int = 10,
) -> LeaderboardResult | NoResult:
    if window_size is None or window_size <= 0:
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            notes=["window_size must be greater than 0"],
        )
    if stretch_metric not in SUPPORTED_TEAM_STRETCH_METRICS:
        allowed = ", ".join(sorted(SUPPORTED_TEAM_STRETCH_METRICS))
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            notes=[
                f"team stretches can't be ranked by '{stretch_metric}'; try record, "
                f"points, points allowed, point differential or a rating ({allowed})"
            ],
        )
    if limit <= 0 or (last_n is not None and last_n <= 0):
        return NoResult(
            query_class="leaderboard",
            reason="unsupported",
            notes=["limit and last_n must be greater than 0"],
        )

    seasons = resolve_seasons(season, start_season, end_season)
    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    df = _apply_filters(
        df,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        start_date=start_date,
        end_date=end_date,
    )
    if df.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    df = df.sort_values(["team_id", "game_date", "game_id"]).reset_index(drop=True)
    if last_n is not None:
        df = df.groupby("team_id", group_keys=False).tail(last_n).reset_index(drop=True)

    windows = _compute_windows(df, stretch_metric, window_size)
    windows = windows[windows["stretch_value"].notna()].copy()
    if windows.empty:
        return NoResult(
            query_class="leaderboard",
            reason="no_match",
            notes=[f"No team played {window_size} games in one season of the filtered sample"],
        )

    descending = (stretch_metric in LOWER_IS_BETTER) == worst
    tie_break = not worst  # a better point differential breaks ties among the best
    windows = windows.sort_values(
        ["stretch_value", "net_per_game", "game_date"],
        ascending=[not descending, not tie_break, False],
    )
    windows = _pick_windows(windows, window_size, per_team=None if team else 1).head(limit)

    rows = pd.DataFrame(
        {
            "rank": range(1, len(windows) + 1),
            "team_name": windows["team_name"].values,
            "team_abbr": windows["team_abbr"].values,
            "season": windows["season"].values,
            "window_start_date": (
                pd.to_datetime(windows["window_start_date"]).dt.date.astype(str).values
            ),
            "window_end_date": windows["game_date"].dt.date.astype(str).values,
            "window_size": window_size,
            "stretch_metric": stretch_metric,
            "stretch_value": pd.to_numeric(windows["stretch_value"]).round(3).values,
            "wins": windows["wins"].astype(int).values,
            "losses": (window_size - windows["wins"]).astype(int).values,
            "net_per_game": windows["net_per_game"].round(2).values,
        }
    )
    caveats = [f"each stretch is {window_size} consecutive games within one season"]
    if stretch_metric in RATING_METRICS:
        caveats.append(
            "ratings are per 100 possessions, estimated from the team's box score "
            "(FGA - OREB + TOV + 0.44 x FTA)"
        )
    if not team:
        caveats.append("each team's best stretch, ranked")
    return LeaderboardResult(
        leaders=rows,
        caveats=caveats,
        metadata={"worst": worst, "stretch_metric": stretch_metric},
        current_through=compute_current_through_for_seasons(seasons, season_type),
    )
