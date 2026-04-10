from __future__ import annotations

from pathlib import Path

import pandas as pd

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
    "usage": "usage_rate",
    "usage_rate": "usage_rate",
    "usg": "usage_rate",
    "usg_pct": "usage_rate",
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
}

DEFAULT_MIN_GAMES = 1
PERCENTAGE_STATS = {"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"}
COUNT_LEADERBOARD_STATS = {"games_20p", "games_30p", "games_40p", "games_10r", "games_10a"}
DATE_WINDOW_UNSUPPORTED_ADVANCED = {"usage_rate", "net_rating", "off_rating", "def_rating"}


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = denominator.where(denominator != 0)
    return numerator / denom


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


def _recommended_min_games(target_col: str, date_window_active: bool = False) -> int:
    if target_col == "games_played":
        return 1
    if date_window_active:
        if target_col in COUNT_LEADERBOARD_STATS:
            return 3
        return 5
    if target_col in COUNT_LEADERBOARD_STATS:
        return 10
    if target_col in PERCENTAGE_STATS:
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
    grouped = basic.groupby(["player_id", "player_name"], as_index=False).agg(
        games_played=("game_id", "nunique"),
        pts_total=("pts", "sum"),
        reb_total=("reb", "sum"),
        ast_total=("ast", "sum"),
        fg3m_total=("fg3m", "sum"),
        fgm_total=("fgm", "sum"),
        fga_total=("fga", "sum"),
        fg3a_total=("fg3a", "sum"),
        ftm_total=("ftm", "sum"),
        fta_total=("fta", "sum"),
        games_20p=("pts", lambda s: int((s >= 20).sum())),
        games_30p=("pts", lambda s: int((s >= 30).sum())),
        games_40p=("pts", lambda s: int((s >= 40).sum())),
        games_10r=("reb", lambda s: int((s >= 10).sum())),
        games_10a=("ast", lambda s: int((s >= 10).sum())),
    )

    grouped["pts_per_game"] = grouped["pts_total"] / grouped["games_played"]
    grouped["reb_per_game"] = grouped["reb_total"] / grouped["games_played"]
    grouped["ast_per_game"] = grouped["ast_total"] / grouped["games_played"]
    grouped["fg3m_per_game"] = grouped["fg3m_total"] / grouped["games_played"]

    grouped["fg_pct"] = _safe_divide(grouped["fgm_total"], grouped["fga_total"])
    grouped["fg3_pct"] = _safe_divide(grouped["fg3m_total"], grouped["fg3a_total"])
    grouped["ft_pct"] = _safe_divide(grouped["ftm_total"], grouped["fta_total"])
    grouped["efg_pct"] = _safe_divide(
        grouped["fgm_total"] + 0.5 * grouped["fg3m_total"], grouped["fga_total"]
    )
    grouped["ts_pct"] = _safe_divide(
        grouped["pts_total"], 2 * (grouped["fga_total"] + 0.44 * grouped["fta_total"])
    )

    return grouped


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

    return merged


def _apply_default_guardrails(
    df: pd.DataFrame, target_col: str, min_games: int, date_window_active: bool = False
) -> pd.DataFrame:
    effective_min_games = max(
        min_games, _recommended_min_games(target_col, date_window_active=date_window_active)
    )
    df = df[df["games_played"] >= effective_min_games].copy()

    if target_col in {"fg_pct", "efg_pct", "ts_pct"} and "fga_total" in df.columns:
        df = df[df["fga_total"] >= 200].copy()

    if target_col == "fg3_pct" and "fg3a_total" in df.columns:
        df = df[df["fg3a_total"] >= 100].copy()

    if target_col == "ft_pct" and "fta_total" in df.columns:
        df = df[df["fta_total"] >= 50].copy()

    return df


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
    safe = season_type.lower().replace(" ", "_")
    adv_path = Path(f"data/raw/player_season_advanced/{season}_{safe}.csv")
    basic_path = Path(f"data/raw/player_game_stats/{season}_{safe}.csv")

    if not basic_path.exists():
        raise FileNotFoundError(f"Missing file: {basic_path}")

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
    if date_window_active and target_col in DATE_WINDOW_UNSUPPORTED_ADVANCED:
        raise ValueError(
            f"Date-window leaderboard not supported for '{target_col}'. "
            "Use scoring, rebounds, assists, threes, eFG%, TS%, or threshold game counts."
        )

    basic = pd.read_csv(basic_path)
    if "game_date" in basic.columns:
        basic["game_date"] = pd.to_datetime(basic["game_date"], errors="coerce").dt.normalize()

    if start_ts is not None and "game_date" in basic.columns:
        basic = basic[basic["game_date"] >= start_ts].copy()

    if end_ts is not None and "game_date" in basic.columns:
        basic = basic[basic["game_date"] <= end_ts].copy()

    df = _build_from_game_logs(basic)

    latest_team_lookup = _latest_team_lookup_from_games(basic)
    if not latest_team_lookup.empty:
        df = df.merge(latest_team_lookup, on="player_id", how="left")

    roster_lookup = _load_roster_lookup(season)
    if roster_lookup is not None and "team_abbr" not in df.columns:
        df = df.merge(
            roster_lookup[["player_id", "team_abbr"]].drop_duplicates("player_id"),
            on="player_id",
            how="left",
        )

    if not date_window_active:
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

    if "games_played" not in df.columns:
        raise ValueError("games_played column required")

    if target_col not in df.columns:
        raise ValueError(f"Column '{target_col}' not available for season leaders output")

    df = _apply_default_guardrails(df, target_col, min_games, date_window_active=date_window_active)

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
    result["season"] = season
    result["season_type"] = season_type

    print(result.to_csv(index=False))
