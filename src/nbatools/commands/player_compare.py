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
    load_team_games_for_seasons,
)
from nbatools.commands.structured_results import ComparisonResult, NoResult


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def filter_player_games(
    df: pd.DataFrame,
    player: str,
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
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

    out = out.sort_values(["game_date", "game_id"], ascending=[False, False]).copy()

    if last_n is not None:
        if last_n <= 0:
            raise ValueError("last_n must be greater than 0")
        out = out.head(last_n).copy()

    return out


def summarize_player(df: pd.DataFrame, context_df: pd.DataFrame, player_name: str) -> dict:
    if df.empty:
        return {
            "player_name": player_name,
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
            "plus_minus_avg": None,
            "efg_pct_avg": None,
            "ts_pct_avg": None,
            "usg_pct_avg": None,
            "ast_pct_avg": None,
            "reb_pct_avg": None,
            "pts_sum": 0,
            "reb_sum": 0,
            "ast_sum": 0,
        }

    wins = int((df["wl"] == "W").sum())
    losses = int((df["wl"] == "L").sum())
    games = int(len(df))

    summary_row = {
        "player_name": player_name,
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
        "plus_minus_avg": round(df["plus_minus"].mean(), 3) if "plus_minus" in df.columns else None,
        "efg_pct_avg": round(df["efg_pct"].mean(), 3) if "efg_pct" in df.columns else None,
        "ts_pct_avg": round(df["ts_pct"].mean(), 3) if "ts_pct" in df.columns else None,
        "pts_sum": round(df["pts"].sum(), 3) if "pts" in df.columns else 0,
        "reb_sum": round(df["reb"].sum(), 3) if "reb" in df.columns else 0,
        "ast_sum": round(df["ast"].sum(), 3) if "ast" in df.columns else 0,
    }

    return add_sample_advanced_metrics_to_summary_row(
        context_df,
        summary_row,
        include_sum_fields=False,
    )


def _build_player_head_to_head_frames(
    df: pd.DataFrame,
    player_a: str,
    player_b: str,
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    last_n: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    a_df = filter_player_games(
        df,
        player=player_a,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        last_n=None,
        start_date=start_date,
        end_date=end_date,
    )
    b_df = filter_player_games(
        df,
        player=player_b,
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
        start_date=start_date,
        end_date=end_date,
    )

    if a_df.empty or b_df.empty:
        return a_df.head(0).copy(), b_df.head(0).copy()

    a_pref = a_df.add_prefix("a__")
    b_pref = b_df.add_prefix("b__")

    merged = a_pref.merge(
        b_pref,
        left_on=["a__season", "a__season_type", "a__game_id"],
        right_on=["b__season", "b__season_type", "b__game_id"],
        how="inner",
    )

    if {"a__team_id", "b__team_id"}.issubset(merged.columns):
        merged = merged[merged["a__team_id"] != merged["b__team_id"]]

    if {"a__opponent_team_id", "b__team_id"}.issubset(merged.columns):
        merged = merged[merged["a__opponent_team_id"] == merged["b__team_id"]]

    if {"b__opponent_team_id", "a__team_id"}.issubset(merged.columns):
        merged = merged[merged["b__opponent_team_id"] == merged["a__team_id"]]

    if merged.empty:
        return a_df.head(0).copy(), b_df.head(0).copy()

    merged["a__game_date"] = pd.to_datetime(merged["a__game_date"], errors="coerce")
    merged = merged.sort_values(["a__game_date", "a__game_id"], ascending=[False, False])

    dedupe_keys = [c for c in ["a__season", "a__season_type", "a__game_id"] if c in merged.columns]
    if dedupe_keys:
        merged = merged.drop_duplicates(subset=dedupe_keys, keep="first")

    if last_n is not None:
        if last_n <= 0:
            raise ValueError("last_n must be greater than 0")
        merged = merged.head(last_n).copy()

    a_out = merged[[c for c in merged.columns if c.startswith("a__")]].copy()
    a_out.columns = [c.replace("a__", "", 1) for c in a_out.columns]

    b_out = merged[[c for c in merged.columns if c.startswith("b__")]].copy()
    b_out.columns = [c.replace("b__", "", 1) for c in b_out.columns]

    return a_out.reset_index(drop=True), b_out.reset_index(drop=True)


def build_result(
    player_a: str,
    player_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    last_n: int | None = None,
    head_to_head: bool = False,
) -> ComparisonResult | NoResult:
    if home_only and away_only:
        raise ValueError("Cannot use both home_only and away_only")

    if wins_only and losses_only:
        raise ValueError("Cannot use both wins_only and losses_only")

    seasons = resolve_seasons(season, start_season, end_season)
    try:
        df = load_player_games_for_seasons(seasons, season_type)
        team_df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="comparison", reason="no_data")

    required = ["player_name", "season", "season_type", "wl", "game_date", "game_id"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if head_to_head:
        a_df, b_df = _build_player_head_to_head_frames(
            df,
            player_a=player_a,
            player_b=player_b,
            team=team,
            opponent=opponent,
            home_only=home_only,
            away_only=away_only,
            wins_only=wins_only,
            losses_only=losses_only,
            last_n=last_n,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        a_df = filter_player_games(
            df,
            player=player_a,
            team=team,
            opponent=opponent,
            home_only=home_only,
            away_only=away_only,
            wins_only=wins_only,
            losses_only=losses_only,
            last_n=last_n,
            start_date=start_date,
            end_date=end_date,
        )
        b_df = filter_player_games(
            df,
            player=player_b,
            team=team,
            opponent=opponent,
            home_only=home_only,
            away_only=away_only,
            wins_only=wins_only,
            losses_only=losses_only,
            last_n=last_n,
            start_date=start_date,
            end_date=end_date,
        )

    a_context = build_player_team_context(a_df, team_df) if not a_df.empty else a_df.copy()
    b_context = build_player_team_context(b_df, team_df) if not b_df.empty else b_df.copy()

    summary_a = summarize_player(a_df, a_context, player_a)
    summary_b = summarize_player(b_df, b_context, player_b)

    summary = pd.DataFrame([summary_a, summary_b])

    comparison_rows = [
        ("games", summary_a["games"], summary_b["games"]),
        ("wins", summary_a["wins"], summary_b["wins"]),
        ("losses", summary_a["losses"], summary_b["losses"]),
        ("win_pct", summary_a["win_pct"], summary_b["win_pct"]),
        ("minutes_avg", summary_a["minutes_avg"], summary_b["minutes_avg"]),
        ("pts_avg", summary_a["pts_avg"], summary_b["pts_avg"]),
        ("reb_avg", summary_a["reb_avg"], summary_b["reb_avg"]),
        ("ast_avg", summary_a["ast_avg"], summary_b["ast_avg"]),
        ("stl_avg", summary_a["stl_avg"], summary_b["stl_avg"]),
        ("blk_avg", summary_a["blk_avg"], summary_b["blk_avg"]),
        ("fg3m_avg", summary_a["fg3m_avg"], summary_b["fg3m_avg"]),
        ("plus_minus_avg", summary_a["plus_minus_avg"], summary_b["plus_minus_avg"]),
        ("efg_pct_avg", summary_a["efg_pct_avg"], summary_b["efg_pct_avg"]),
        ("ts_pct_avg", summary_a["ts_pct_avg"], summary_b["ts_pct_avg"]),
        ("usg_pct_avg", summary_a["usg_pct_avg"], summary_b["usg_pct_avg"]),
        ("ast_pct_avg", summary_a["ast_pct_avg"], summary_b["ast_pct_avg"]),
        ("reb_pct_avg", summary_a["reb_pct_avg"], summary_b["reb_pct_avg"]),
        ("pts_sum", summary_a["pts_sum"], summary_b["pts_sum"]),
        ("reb_sum", summary_a["reb_sum"], summary_b["reb_sum"]),
        ("ast_sum", summary_a["ast_sum"], summary_b["ast_sum"]),
    ]

    comp = pd.DataFrame(
        comparison_rows,
        columns=["metric", player_a, player_b],
    )

    current_through = compute_current_through_for_seasons(seasons, season_type)

    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(
            "multi-season comparison aggregated from game logs across "
            f"{seasons[0]} to {seasons[-1]}"
        )

    return ComparisonResult(
        summary=summary,
        comparison=comp,
        current_through=current_through,
        caveats=caveats,
    )


def run(
    player_a: str,
    player_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    last_n: int | None = None,
    head_to_head: bool = False,
) -> None:
    result = build_result(
        player_a=player_a,
        player_b=player_b,
        season=season,
        start_season=start_season,
        end_season=end_season,
        start_date=start_date,
        end_date=end_date,
        season_type=season_type,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        last_n=last_n,
        head_to_head=head_to_head,
    )
    print(result.to_labeled_text(), end="")
