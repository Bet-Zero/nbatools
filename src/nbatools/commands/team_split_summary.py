from __future__ import annotations

import pandas as pd

from nbatools.commands._month_split import (
    MONTH_KEY_COLUMN,
    add_requested_stat,
    assign_month_buckets,
    order_month_buckets,
    rank_column,
    sample_stat,
)
from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.aggregate_metrics import add_aggregate_metric_fields
from nbatools.commands.data_utils import describe_opponent_filter, team_value_mask
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.game_summary import select_team_summary_sample
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
    "efg_pct": "efg_pct",
    "ts_pct": "ts_pct",
}

ALLOWED_SPLITS = {"home_away", "wins_losses", "month"}
_SPLIT_AXIS_FIELDS = {
    "home_away": ("home_only", "away_only"),
    "wins_losses": ("wins_only", "losses_only"),
    "month": (),
}


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
        out = out[team_value_mask(out, team_upper)].copy()

    if opponent:
        opp_upper = opponent.upper()
        out = out[team_value_mask(out, opp_upper, prefix="opponent_")].copy()

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

    summary_row = {
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
        "plus_minus_avg": round(df["plus_minus"].mean(), 3) if "plus_minus" in df.columns else None,
    }
    return add_aggregate_metric_fields(summary_row, df, ["efg_pct", "ts_pct"])


def build_result(
    split: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    opponent: str | list[str] | tuple[str, ...] | None = None,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    conditions: list[dict] | None = None,
    last_n: int | None = None,
    df: pd.DataFrame | None = None,
    last_n_scope: str = "qualifying",
    rank_stat: str | None = None,
    rank_order: str | None = None,
    **sample_filters,
) -> SplitSummaryResult | NoResult:
    """Split one team's sample by home/away, wins/losses or month.

    The sample is exactly what the team summary would describe (dates,
    opponent, the other location/outcome flag, stat conditions, teammate
    availability, last-N window); the split then divides those games. A
    month split can be ranked by ``rank_stat`` ("best month" is the record).
    """
    split = split.lower()
    if split not in ALLOWED_SPLITS:
        raise ValueError(f"Unsupported split: {split}. Allowed: {sorted(ALLOWED_SPLITS)}")

    for axis_field in _SPLIT_AXIS_FIELDS[split]:
        sample_filters.pop(axis_field, None)

    seasons = resolve_seasons(season, start_season, end_season)
    df = select_team_summary_sample(
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        team=team,
        opponent=opponent,
        stat=sample_stat(stat, min_value, max_value) if split == "month" else stat,
        min_value=min_value,
        max_value=max_value,
        conditions=conditions,
        last_n=last_n,
        df=df,
        last_n_scope=last_n_scope,
        **sample_filters,
    )
    if isinstance(df, NoResult):
        return NoResult(query_class="split_summary", reason=df.reason, notes=list(df.notes or []))

    if df.empty:
        return NoResult(query_class="split_summary")

    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    season_min = df["season"].min()
    season_max = df["season"].max()

    if split == "month":
        return _month_split_result(
            df,
            team_name=team_name,
            season_type=season_type,
            seasons=seasons,
            opponent=opponent,
            stat=stat,
            rank_stat=rank_stat,
            rank_order=rank_order,
        )

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

    return SplitSummaryResult(
        summary=summary,
        split_comparison=split_comparison,
        current_through=compute_current_through_for_seasons(seasons, season_type),
        caveats=_caveats(seasons, opponent),
    )


def _caveats(seasons: list[str], opponent) -> list[str]:
    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(
            "multi-season split summary aggregated from game logs across "
            f"{seasons[0]} to {seasons[-1]}"
        )
    if opponent:
        # "against winning teams" passes a list of opponents.
        caveats.append(f"filtered to games vs {describe_opponent_filter(opponent)}")
    return caveats


def _month_split_result(
    df: pd.DataFrame,
    *,
    team_name: str | None,
    season_type: str,
    seasons: list[str],
    opponent,
    stat: str | None,
    rank_stat: str | None,
    rank_order: str | None,
) -> SplitSummaryResult:
    """One row per calendar month; "best month" ranks by record by default."""
    df = assign_month_buckets(df)
    rows = []
    for bucket, bucket_df in df.groupby("bucket", sort=False):
        row = add_requested_stat(_summarize_bucket(bucket_df, bucket), bucket_df, stat)
        rows.append(add_requested_stat(row, bucket_df, rank_stat))
    month_keys = dict(zip(df["bucket"], df[MONTH_KEY_COLUMN], strict=False))
    ranked_by = rank_column(rank_stat, "win_pct") if rank_order else None
    split_comparison = order_month_buckets(
        pd.DataFrame(rows),
        month_keys,
        rank_column=ranked_by,
        rank_order=rank_order,
    )
    summary_row = {
        "team_name": team_name,
        "season_start": df["season"].min(),
        "season_end": df["season"].max(),
        "season_type": season_type,
        "split": "month",
        "games_total": int(len(df)),
    }
    if ranked_by:
        summary_row["ranked_by"] = ranked_by
        summary_row["rank_order"] = rank_order
    return SplitSummaryResult(
        summary=pd.DataFrame([summary_row]),
        split_comparison=split_comparison,
        current_through=compute_current_through_for_seasons(seasons, season_type),
        caveats=_caveats(seasons, opponent),
    )


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
    result = build_result(
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
        df=df,
    )
    print(result.to_labeled_text(), end="")
