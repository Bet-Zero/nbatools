from __future__ import annotations

from pathlib import Path

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import safe_divide
from nbatools.commands.freshness import compute_current_through, compute_current_through_for_seasons
from nbatools.commands.structured_results import LeaderboardResult, NoResult

ALLOWED_STATS = {
    "pts": "pts_per_game",
    "points": "pts_per_game",
    "scoring": "pts_per_game",
    "ppg": "pts_per_game",
    "points per game": "pts_per_game",
    "pts_per_game": "pts_per_game",
    "reb": "reb_per_game",
    "rebound": "reb_per_game",
    "rebounds": "reb_per_game",
    "rpg": "reb_per_game",
    "rebounds per game": "reb_per_game",
    "reb_per_game": "reb_per_game",
    "ast": "ast_per_game",
    "assist": "ast_per_game",
    "assists": "ast_per_game",
    "apg": "ast_per_game",
    "assists per game": "ast_per_game",
    "ast_per_game": "ast_per_game",
    "stl": "stl_per_game",
    "steal": "stl_per_game",
    "steals": "stl_per_game",
    "spg": "stl_per_game",
    "steals per game": "stl_per_game",
    "stl_per_game": "stl_per_game",
    "blk": "blk_per_game",
    "block": "blk_per_game",
    "blocks": "blk_per_game",
    "bpg": "blk_per_game",
    "blocks per game": "blk_per_game",
    "blk_per_game": "blk_per_game",
    "tov": "tov_per_game",
    "turnover": "tov_per_game",
    "turnovers": "tov_per_game",
    "turnovers per game": "tov_per_game",
    "tov_per_game": "tov_per_game",
    "plus_minus": "plus_minus_per_game",
    "plus minus": "plus_minus_per_game",
    "plus/minus": "plus_minus_per_game",
    "+/-": "plus_minus_per_game",
    "plus_minus_per_game": "plus_minus_per_game",
    "fg3m": "fg3m_per_game",
    "3pm": "fg3m_per_game",
    "threes": "fg3m_per_game",
    "threes made": "fg3m_per_game",
    "three pointers made": "fg3m_per_game",
    "three-point makes": "fg3m_per_game",
    "3 pointers made": "fg3m_per_game",
    "3-pointers made": "fg3m_per_game",
    "fg3m_per_game": "fg3m_per_game",
    "fg_pct": "fg_pct",
    "field goal percentage": "fg_pct",
    "field goal %": "fg_pct",
    "fg3_pct": "fg3_pct",
    "3pt_pct": "fg3_pct",
    "3p_pct": "fg3_pct",
    "three point percentage": "fg3_pct",
    "three-point percentage": "fg3_pct",
    "three point %": "fg3_pct",
    "three-point %": "fg3_pct",
    "ft_pct": "ft_pct",
    "free throw percentage": "ft_pct",
    "free throw %": "ft_pct",
    "efg": "efg_pct",
    "efg_pct": "efg_pct",
    "effective fg": "efg_pct",
    "effective field goal": "efg_pct",
    "effective field goal percentage": "efg_pct",
    "effective field goal %": "efg_pct",
    "ts": "ts_pct",
    "ts_pct": "ts_pct",
    "true shooting": "ts_pct",
    "true shooting percentage": "ts_pct",
    "true shooting %": "ts_pct",
    "net_rating": "net_rating",
    "off_rating": "off_rating",
    "def_rating": "def_rating",
    "games": "games_played",
    "games_played": "games_played",
    "games_20p": "games_20p",
    "20 point games": "games_20p",
    "20-point games": "games_20p",
    "games_30p": "games_30p",
    "30 point games": "games_30p",
    "30-point games": "games_30p",
    "games_40p": "games_40p",
    "40 point games": "games_40p",
    "40-point games": "games_40p",
    "games_10r": "games_10r",
    "10 rebound games": "games_10r",
    "10-rebound games": "games_10r",
    "double digit rebound games": "games_10r",
    "games_10a": "games_10a",
    "10 assist games": "games_10a",
    "10-assist games": "games_10a",
    "double digit assist games": "games_10a",
    # Game-log-derived advanced metrics
    "usage": "usg_pct",
    "usage_rate": "usg_pct",
    "usage rate": "usg_pct",
    "usage %": "usg_pct",
    "usage percentage": "usg_pct",
    "usg": "usg_pct",
    "usg_pct": "usg_pct",
    "usg%": "usg_pct",
    "assist percentage": "ast_pct",
    "assist %": "ast_pct",
    "ast%": "ast_pct",
    "ast_pct": "ast_pct",
    "rebound percentage": "reb_pct",
    "rebound %": "reb_pct",
    "reb%": "reb_pct",
    "reb_pct": "reb_pct",
    "turnover percentage": "tov_pct",
    "turnover %": "tov_pct",
    "turnover rate": "tov_pct",
    "tov%": "tov_pct",
    "tov_pct": "tov_pct",
}

DEFAULT_MIN_GAMES = 1
PERCENTAGE_STATS = {"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"}
ADVANCED_RATE_STATS = {"usg_pct", "ast_pct", "reb_pct", "tov_pct"}
COUNT_LEADERBOARD_STATS = {"games_20p", "games_30p", "games_40p", "games_10r", "games_10a"}
# Season-advanced-only metrics that cannot be computed from game logs.
DATE_WINDOW_UNSUPPORTED_ADVANCED = {"net_rating", "off_rating", "def_rating"}
# Game-log-derived advanced metrics require team context merge.
GAME_LOG_DERIVED_ADVANCED = {"usg_pct", "ast_pct", "reb_pct", "tov_pct"}


def _normalize_stat(stat: str) -> str:
    key = stat.lower().strip()
    if key not in ALLOWED_STATS:
        allowed = ", ".join(sorted(ALLOWED_STATS.keys()))
        raise ValueError(f"Unsupported stat '{stat}'. Allowed stats: {allowed}")
    return ALLOWED_STATS[key]


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def _recommended_min_games(
    target_col: str,
    date_window_active: bool = False,
    opponent_active: bool = False,
) -> int:
    if target_col == "games_played":
        return 1
    if date_window_active or opponent_active:
        if target_col in COUNT_LEADERBOARD_STATS:
            return 1
        return 3
    if target_col in COUNT_LEADERBOARD_STATS:
        return 10
    if target_col in PERCENTAGE_STATS:
        return 20
    if target_col in ADVANCED_RATE_STATS:
        return 20
    return 20


def _latest_team_lookup_from_games(basic: pd.DataFrame) -> pd.DataFrame:
    keep = [
        c
        for c in ["player_id", "team_id", "team_abbr", "game_date", "game_id"]
        if c in basic.columns
    ]
    if "player_id" not in keep or len(keep) == 1:
        return pd.DataFrame(columns=["player_id", "team_id", "team_abbr"])

    latest = basic[keep].copy()

    if "game_date" in latest.columns:
        latest["_game_date_sort"] = pd.to_datetime(latest["game_date"], errors="coerce")
    else:
        latest["_game_date_sort"] = pd.NaT

    if "game_id" in latest.columns:
        latest["_game_id_sort"] = pd.to_numeric(latest["game_id"], errors="coerce")
    else:
        latest["_game_id_sort"] = range(len(latest))

    latest = latest.sort_values(
        by=["player_id", "_game_date_sort", "_game_id_sort"],
        ascending=[True, True, True],
        na_position="last",
    ).drop_duplicates(subset=["player_id"], keep="last")

    out_cols = [c for c in ["player_id", "team_id", "team_abbr"] if c in latest.columns]
    return latest[out_cols].copy()


def _load_roster_lookup(season: str) -> pd.DataFrame | None:
    rosters_path = Path(f"data/raw/rosters/{season}.csv")
    if not rosters_path.exists():
        return None

    rosters = pd.read_csv(rosters_path)
    needed = [c for c in ["player_id", "team_id", "team_abbr"] if c in rosters.columns]
    if len(needed) < 3:
        return None

    return rosters[needed].drop_duplicates()


def _build_from_game_logs(basic: pd.DataFrame) -> pd.DataFrame:
    agg_spec: dict = {
        "games_played": ("game_id", "nunique"),
        "pts_total": ("pts", "sum"),
        "reb_total": ("reb", "sum"),
        "ast_total": ("ast", "sum"),
        "fg3m_total": ("fg3m", "sum"),
        "fgm_total": ("fgm", "sum"),
        "fga_total": ("fga", "sum"),
        "fg3a_total": ("fg3a", "sum"),
        "ftm_total": ("ftm", "sum"),
        "fta_total": ("fta", "sum"),
        "games_20p": ("pts", lambda s: int((s >= 20).sum())),
        "games_30p": ("pts", lambda s: int((s >= 30).sum())),
        "games_40p": ("pts", lambda s: int((s >= 40).sum())),
        "games_10r": ("reb", lambda s: int((s >= 10).sum())),
        "games_10a": ("ast", lambda s: int((s >= 10).sum())),
    }
    # Only aggregate optional columns when they exist in the data
    for col in ("stl", "blk", "tov", "plus_minus"):
        if col in basic.columns:
            agg_spec[f"{col}_total"] = (col, "sum")

    grouped = basic.groupby(["player_id", "player_name"], as_index=False).agg(**agg_spec)

    grouped["pts_per_game"] = grouped["pts_total"] / grouped["games_played"]
    grouped["reb_per_game"] = grouped["reb_total"] / grouped["games_played"]
    grouped["ast_per_game"] = grouped["ast_total"] / grouped["games_played"]
    for col in ("stl", "blk", "tov", "plus_minus"):
        total_col = f"{col}_total"
        if total_col in grouped.columns:
            grouped[f"{col}_per_game"] = grouped[total_col] / grouped["games_played"]
    grouped["fg3m_per_game"] = grouped["fg3m_total"] / grouped["games_played"]

    grouped["fg_pct"] = safe_divide(grouped["fgm_total"], grouped["fga_total"], fill=None)
    grouped["fg3_pct"] = safe_divide(grouped["fg3m_total"], grouped["fg3a_total"], fill=None)
    grouped["ft_pct"] = safe_divide(grouped["ftm_total"], grouped["fta_total"], fill=None)
    grouped["efg_pct"] = safe_divide(
        grouped["fgm_total"] + 0.5 * grouped["fg3m_total"], grouped["fga_total"], fill=None
    )
    grouped["ts_pct"] = safe_divide(
        grouped["pts_total"],
        2 * (grouped["fga_total"] + 0.44 * grouped["fta_total"]),
        fill=None,
    )

    return grouped


def _merge_game_log_derived_advanced(
    grouped: pd.DataFrame,
    basic: pd.DataFrame,
    seasons: list[str],
    season_type: str,
) -> pd.DataFrame:
    """Compute USG%, AST%, REB%, TOV% from game-log aggregates with team context.

    These metrics are computed by aggregating raw box-score totals per player
    and matching them with the corresponding team totals for the games the
    player appeared in.  The formulas match those in player_advanced_metrics.py.
    """
    safe = season_type.lower().replace(" ", "_")

    # Load team game logs for the same seasons
    team_frames: list[pd.DataFrame] = []
    for s in seasons:
        tpath = Path(f"data/raw/team_game_stats/{s}_{safe}.csv")
        if tpath.exists():
            team_frames.append(pd.read_csv(tpath))
    if not team_frames:
        return grouped

    team_df = pd.concat(team_frames, ignore_index=True)

    # Coerce numeric columns in team_df
    for col in ("minutes", "fgm", "fga", "fta", "tov", "reb"):
        if col in team_df.columns:
            team_df[col] = pd.to_numeric(team_df[col], errors="coerce").fillna(0)

    player_context_cols = ["game_id", "player_id", "team_id"]
    if not all(c in basic.columns for c in player_context_cols):
        return grouped

    # Build team context at (game_id, team_id) level — one row per team per game
    team_ctx = team_df[["game_id", "team_id", "minutes", "fgm", "fga", "fta", "tov", "reb"]].copy()
    team_ctx = team_ctx.rename(
        columns={
            "minutes": "team_minutes",
            "fgm": "team_fgm",
            "fga": "team_fga",
            "fta": "team_fta",
            "tov": "team_tov",
            "reb": "team_reb",
        }
    ).drop_duplicates(subset=["game_id", "team_id"])

    # Build opponent reb lookup at (game_id, team_id) level
    if "opponent_team_id" in basic.columns:
        opp_map = basic[["game_id", "team_id", "opponent_team_id"]].drop_duplicates(
            subset=["game_id", "team_id"]
        )
        opp_reb = (
            team_df[["game_id", "team_id", "reb"]]
            .rename(columns={"team_id": "opponent_team_id", "reb": "opp_reb"})
            .drop_duplicates(subset=["game_id", "opponent_team_id"])
        )
        opp_map = opp_map.merge(opp_reb, on=["game_id", "opponent_team_id"], how="left")
        team_ctx = team_ctx.merge(
            opp_map[["game_id", "team_id", "opp_reb"]].drop_duplicates(
                subset=["game_id", "team_id"]
            ),
            on=["game_id", "team_id"],
            how="left",
        )

    # Gather per-player-game stats
    player_stat_cols = ["game_id", "player_id", "team_id"]
    for col in ("fga", "fta", "tov", "minutes", "ast", "fgm", "reb"):
        if col in basic.columns:
            player_stat_cols.append(col)
    player_stats = basic[player_stat_cols].drop_duplicates()

    # Many-to-one merge: each player row finds its team context row
    merged = player_stats.merge(team_ctx, on=["game_id", "team_id"], how="left")

    # Coerce numerics
    for col in (
        "fga",
        "fta",
        "tov",
        "minutes",
        "ast",
        "fgm",
        "reb",
        "team_minutes",
        "team_fgm",
        "team_fga",
        "team_fta",
        "team_tov",
        "team_reb",
    ):
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    if "opp_reb" in merged.columns:
        merged["opp_reb"] = pd.to_numeric(merged["opp_reb"], errors="coerce").fillna(0)

    # Aggregate per player
    player_agg = merged.groupby("player_id", as_index=False).agg(
        p_fga=("fga", "sum"),
        p_fta=("fta", "sum"),
        p_tov=("tov", "sum"),
        p_minutes=("minutes", "sum"),
        p_ast=("ast", "sum"),
        p_fgm=("fgm", "sum"),
        p_reb=("reb", "sum"),
        t_minutes=("team_minutes", "sum"),
        t_fgm=("team_fgm", "sum"),
        t_fga=("team_fga", "sum"),
        t_fta=("team_fta", "sum"),
        t_tov=("team_tov", "sum"),
        t_reb=("team_reb", "sum"),
        **(
            {
                "o_reb": ("opp_reb", "sum"),
            }
            if "opp_reb" in merged.columns
            else {}
        ),
    )

    # USG%: 100 * ((FGA + 0.44*FTA + TOV) * (TeamMin/5)) / (Min * (TeamFGA + 0.44*TeamFTA + TeamTOV))
    player_actions = player_agg["p_fga"] + 0.44 * player_agg["p_fta"] + player_agg["p_tov"]
    team_actions = player_agg["t_fga"] + 0.44 * player_agg["t_fta"] + player_agg["t_tov"]
    usg_numer = player_actions * (player_agg["t_minutes"] / 5.0)
    usg_denom = player_agg["p_minutes"] * team_actions
    player_agg["usg_pct"] = (100.0 * usg_numer / usg_denom).where(usg_denom > 0)

    # AST%: 100 * AST / (((MIN / (TeamMIN/5)) * TeamFGM) - FGM)
    min_share = player_agg["p_minutes"] / (player_agg["t_minutes"] / 5.0)
    ast_denom = (min_share * player_agg["t_fgm"]) - player_agg["p_fgm"]
    player_agg["ast_pct"] = (100.0 * player_agg["p_ast"] / ast_denom).where(ast_denom > 0)

    # REB%: 100 * (REB * (TeamMIN/5)) / (MIN * (TeamREB + OppREB))
    if "o_reb" in player_agg.columns:
        reb_numer = player_agg["p_reb"] * (player_agg["t_minutes"] / 5.0)
        reb_denom = player_agg["p_minutes"] * (player_agg["t_reb"] + player_agg["o_reb"])
        player_agg["reb_pct"] = (100.0 * reb_numer / reb_denom).where(reb_denom > 0)

    # TOV%: 100 * TOV / (FGA + 0.44*FTA + TOV)
    tov_denom = player_agg["p_fga"] + 0.44 * player_agg["p_fta"] + player_agg["p_tov"]
    player_agg["tov_pct"] = (100.0 * player_agg["p_tov"] / tov_denom).where(tov_denom > 0)

    # Merge back into grouped
    adv_cols = ["player_id"]
    for col in ("usg_pct", "ast_pct", "reb_pct", "tov_pct"):
        if col in player_agg.columns:
            adv_cols.append(col)

    result = grouped.merge(player_agg[adv_cols], on="player_id", how="left", suffixes=("", "_gldr"))
    # If season-advanced already had usage_rate, keep it; game-log-derived is fallback
    for col in ("usg_pct", "ast_pct", "reb_pct", "tov_pct"):
        gldr_col = f"{col}_gldr"
        if gldr_col in result.columns:
            if col in result.columns:
                result[col] = result[col].combine_first(result[gldr_col])
            else:
                result[col] = result[gldr_col]
            result = result.drop(columns=[gldr_col])

    return result


def _prepare_advanced_rows(adv: pd.DataFrame) -> pd.DataFrame:
    if "player_id" not in adv.columns:
        return pd.DataFrame(columns=["player_id"])

    work = adv.copy()

    if "games_played" in work.columns:
        work["games_played"] = pd.to_numeric(work["games_played"], errors="coerce")
    else:
        work["games_played"] = pd.NA

    if "as_of_date" in work.columns:
        work["_as_of_date_sort"] = pd.to_datetime(work["as_of_date"], errors="coerce")
    else:
        work["_as_of_date_sort"] = pd.NaT

    if "team_abbr" in work.columns:
        work["_is_tot"] = work["team_abbr"].astype(str).str.upper().eq("TOT")
    else:
        work["_is_tot"] = False

    work = work.sort_values(
        by=["player_id", "_is_tot", "games_played", "_as_of_date_sort"],
        ascending=[True, False, False, False],
        na_position="last",
    ).drop_duplicates(subset=["player_id"], keep="first")

    keep_cols = [
        c
        for c in [
            "player_id",
            "team_id",
            "team_abbr",
            "games_played",
            "ts_pct",
            "usage_rate",
            "net_rating",
            "off_rating",
            "def_rating",
        ]
        if c in work.columns
    ]
    return work[keep_cols].copy()


def _merge_advanced_if_available(grouped: pd.DataFrame, adv_path: Path) -> pd.DataFrame:
    if not adv_path.exists():
        return grouped

    adv = pd.read_csv(adv_path)
    adv = _prepare_advanced_rows(adv)

    if adv.empty or "player_id" not in adv.columns:
        return grouped

    merged = grouped.merge(adv, on="player_id", how="left", suffixes=("", "_adv"))

    if "games_played_adv" in merged.columns:
        merged["games_played"] = merged["games_played"].combine_first(merged["games_played_adv"])
        merged = merged.drop(columns=["games_played_adv"])

    for col in [
        "ts_pct",
        "usage_rate",
        "net_rating",
        "off_rating",
        "def_rating",
        "team_id",
        "team_abbr",
    ]:
        adv_col = f"{col}_adv"
        if adv_col in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].combine_first(merged[adv_col])
            else:
                merged[col] = merged[adv_col]
            merged = merged.drop(columns=[adv_col])

    # Map usage_rate (season-advanced column name) -> usg_pct (canonical name)
    if "usage_rate" in merged.columns and "usg_pct" not in merged.columns:
        merged["usg_pct"] = merged["usage_rate"]
    elif "usage_rate" in merged.columns and "usg_pct" in merged.columns:
        merged["usg_pct"] = merged["usg_pct"].combine_first(merged["usage_rate"])

    return merged


def _apply_default_guardrails(
    df: pd.DataFrame,
    target_col: str,
    min_games: int,
    date_window_active: bool = False,
    opponent_active: bool = False,
    num_seasons: int = 1,
) -> pd.DataFrame:
    effective_min_games = max(
        min_games,
        _recommended_min_games(
            target_col,
            date_window_active=date_window_active,
            opponent_active=opponent_active,
        ),
    )
    df = df[df["games_played"] >= effective_min_games].copy()

    fga_floor = 200 * num_seasons
    fg3a_floor = 100 * num_seasons
    fta_floor = 50 * num_seasons

    if target_col in {"fg_pct", "efg_pct", "ts_pct"} and "fga_total" in df.columns:
        df = df[df["fga_total"] >= fga_floor].copy()

    if target_col == "fg3_pct" and "fg3a_total" in df.columns:
        df = df[df["fg3a_total"] >= fg3a_floor].copy()

    if target_col == "ft_pct" and "fta_total" in df.columns:
        df = df[df["fta_total"] >= fta_floor].copy()

    # Advanced rate stats also need sufficient volume
    if target_col in ADVANCED_RATE_STATS and "fga_total" in df.columns:
        df = df[df["fga_total"] >= fga_floor].copy()

    return df


def build_result(
    season: str | None = None,
    stat: str = "pts",
    limit: int = 10,
    season_type: str = "Regular Season",
    min_games: int = DEFAULT_MIN_GAMES,
    ascending: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    opponent: str | None = None,
) -> LeaderboardResult | NoResult:
    safe = season_type.lower().replace(" ", "_")

    # Resolve the list of seasons to load
    try:
        seasons = resolve_seasons(season, start_season, end_season)
    except ValueError:
        return NoResult(query_class="leaderboard", reason="no_data")

    multi_season = len(seasons) > 1

    # Validate params
    if limit <= 0:
        raise ValueError("limit must be greater than 0")
    if min_games < 1:
        raise ValueError("min_games must be at least 1")

    target_col = _normalize_stat(stat)
    start_ts = _normalize_date_value(start_date)
    end_ts = _normalize_date_value(end_date)
    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise ValueError("start_date must be less than or equal to end_date")

    date_window_active = start_ts is not None or end_ts is not None

    # For multi-season, advanced stats (usage_rate, net_rating, etc.) are not
    # reliable across season boundaries — disable them.
    if multi_season and target_col in DATE_WINDOW_UNSUPPORTED_ADVANCED:
        raise ValueError(
            f"Multi-season leaderboard not supported for '{target_col}'. "
            "Use scoring, rebounds, assists, threes, eFG%, TS%, or threshold game counts."
        )
    if date_window_active and target_col in DATE_WINDOW_UNSUPPORTED_ADVANCED:
        raise ValueError(
            f"Date-window leaderboard not supported for '{target_col}'. "
            "Use scoring, rebounds, assists, threes, eFG%, TS%, or threshold game counts."
        )
    if opponent and target_col in DATE_WINDOW_UNSUPPORTED_ADVANCED:
        raise ValueError(
            f"Opponent-filtered leaderboard not supported for '{target_col}'. "
            "Use scoring, rebounds, assists, threes, eFG%, TS%, or threshold game counts."
        )

    # Load and concatenate game logs across all seasons
    frames: list[pd.DataFrame] = []
    for s in seasons:
        basic_path = Path(f"data/raw/player_game_stats/{s}_{safe}.csv")
        if basic_path.exists():
            frames.append(pd.read_csv(basic_path))

    if not frames:
        return NoResult(query_class="leaderboard", reason="no_data")

    basic = pd.concat(frames, ignore_index=True)

    if "game_date" in basic.columns:
        basic["game_date"] = pd.to_datetime(basic["game_date"], errors="coerce").dt.normalize()

    if start_ts is not None and "game_date" in basic.columns:
        basic = basic[basic["game_date"] >= start_ts].copy()

    if end_ts is not None and "game_date" in basic.columns:
        basic = basic[basic["game_date"] <= end_ts].copy()

    if opponent:
        opp_upper = opponent.upper()
        opp_mask = pd.Series(False, index=basic.index)
        if "opponent_team_abbr" in basic.columns:
            opp_mask = opp_mask | basic["opponent_team_abbr"].astype(str).str.upper().eq(opp_upper)
        if "opponent_team_name" in basic.columns:
            opp_mask = opp_mask | basic["opponent_team_name"].astype(str).str.upper().eq(opp_upper)
        basic = basic[opp_mask].copy()

    if basic.empty:
        return NoResult(query_class="leaderboard", reason="no_data")

    df = _build_from_game_logs(basic)

    # Compute game-log-derived advanced metrics (USG%, AST%, REB%, TOV%)
    # These work in any context (multi-season, date-window, opponent-filtered).
    if target_col in GAME_LOG_DERIVED_ADVANCED:
        df = _merge_game_log_derived_advanced(df, basic, seasons, season_type)

    latest_team_lookup = _latest_team_lookup_from_games(basic)
    if not latest_team_lookup.empty:
        df = df.merge(latest_team_lookup, on="player_id", how="left")

    # For single season, try roster lookup and advanced stats merge
    if not multi_season:
        the_season = seasons[0]
        roster_lookup = _load_roster_lookup(the_season)
        if roster_lookup is not None and "team_abbr" not in df.columns:
            df = df.merge(
                roster_lookup[["player_id", "team_abbr"]].drop_duplicates("player_id"),
                on="player_id",
                how="left",
            )

        adv_path = Path(f"data/raw/player_season_advanced/{the_season}_{safe}.csv")
        if not date_window_active and not opponent:
            df = _merge_advanced_if_available(df, adv_path)

        if roster_lookup is not None and "team_abbr" in df.columns:
            roster_fill = (
                roster_lookup[["player_id", "team_abbr"]]
                .drop_duplicates("player_id")
                .rename(columns={"team_abbr": "team_abbr_roster"})
            )
            df = df.merge(roster_fill, on="player_id", how="left")
            df["team_abbr"] = df["team_abbr"].fillna(df["team_abbr_roster"])
            df = df.drop(columns=["team_abbr_roster"])
    else:
        # Multi-season: use latest season roster for team_abbr backfill
        latest_season = seasons[-1]
        roster_lookup = _load_roster_lookup(latest_season)
        if roster_lookup is not None and "team_abbr" not in df.columns:
            df = df.merge(
                roster_lookup[["player_id", "team_abbr"]].drop_duplicates("player_id"),
                on="player_id",
                how="left",
            )

    if "games_played" not in df.columns:
        raise ValueError("games_played column required")

    if target_col not in df.columns:
        raise ValueError(f"Column '{target_col}' not available for season leaders output")

    df = _apply_default_guardrails(
        df,
        target_col,
        min_games,
        date_window_active=date_window_active,
        opponent_active=bool(opponent),
        num_seasons=len(seasons),
    )

    if df.empty:
        return NoResult(query_class="leaderboard")

    out_cols = ["player_name", "player_id"]
    if "team_abbr" in df.columns:
        out_cols.append("team_abbr")
    out_cols.extend(["games_played", target_col])

    result = (
        df[out_cols]
        .sort_values(
            by=[target_col, "games_played", "player_name"],
            ascending=[ascending, False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )

    result.insert(0, "rank", range(1, len(result) + 1))

    if multi_season:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        result["season"] = seasons[0]
    result["season_type"] = season_type

    # Freshness
    if multi_season:
        current_through = compute_current_through_for_seasons(seasons, season_type)
    else:
        current_through = compute_current_through(seasons[0], season_type)

    caveats: list[str] = []
    if date_window_active:
        caveats.append("leaderboard computed from game-log window; season-advanced stats excluded")
    if multi_season:
        caveats.append(
            "multi-season leaderboard aggregated from game logs; season-advanced stats excluded"
        )
    if opponent:
        caveats.append(f"filtered to games vs {opponent.upper()}")
    if target_col in GAME_LOG_DERIVED_ADVANCED:
        if date_window_active or multi_season or opponent:
            caveats.append(f"{target_col} recomputed from filtered game-log sample")

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
        caveats=caveats,
    )


def run(
    season: str,
    stat: str,
    limit: int = 10,
    season_type: str = "Regular Season",
    min_games: int = DEFAULT_MIN_GAMES,
    ascending: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    result = build_result(
        season=season,
        stat=stat,
        limit=limit,
        season_type=season_type,
        min_games=min_games,
        ascending=ascending,
        start_date=start_date,
        end_date=end_date,
    )
    if isinstance(result, NoResult):
        print("no matching games")
        return
    print(result.to_labeled_text(), end="")
