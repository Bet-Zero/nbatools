from __future__ import annotations

from pathlib import Path

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import safe_divide
from nbatools.commands.freshness import compute_current_through, compute_current_through_for_seasons
from nbatools.commands.structured_results import LeaderboardResult, NoResult

ALLOWED_STATS = {
    "games_played": "games_played",
    "games": "games_played",
    "pts": "pts_per_game",
    "points": "pts_per_game",
    "scoring": "pts_per_game",
    "ppg": "pts_per_game",
    "points per game": "pts_per_game",
    "pts_per_game": "pts_per_game",
    "reb": "reb_per_game",
    "rebounds": "reb_per_game",
    "rpg": "reb_per_game",
    "rebounds per game": "reb_per_game",
    "reb_per_game": "reb_per_game",
    "ast": "ast_per_game",
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
    "threes per game": "fg3m_per_game",
    "fg3m_per_game": "fg3m_per_game",
    "fg_pct": "fg_pct",
    "field goal percentage": "fg_pct",
    "field goal %": "fg_pct",
    "fg3_pct": "fg3_pct",
    "3pt_pct": "fg3_pct",
    "3p_pct": "fg3_pct",
    "three point percentage": "fg3_pct",
    "three-point percentage": "fg3_pct",
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
    "off_rating": "off_rating",
    "offense": "off_rating",
    "offensive rating": "off_rating",
    "off rating": "off_rating",
    "def_rating": "def_rating",
    "defense": "def_rating",
    "defensive rating": "def_rating",
    "def rating": "def_rating",
    "net_rating": "net_rating",
    "net": "net_rating",
    "net rating": "net_rating",
    "pace": "pace",
}

DEFAULT_MIN_GAMES = 1
PERCENTAGE_STATS = {"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"}
DATE_WINDOW_UNSUPPORTED_ADVANCED = {"off_rating", "def_rating", "net_rating", "pace"}


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
        return 5
    if target_col in PERCENTAGE_STATS:
        return 20
    return 20


def _build_from_game_logs(basic: pd.DataFrame) -> pd.DataFrame:
    grouped = basic.groupby(["team_id", "team_name", "team_abbr"], as_index=False).agg(
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
    )

    grouped["pts_per_game"] = grouped["pts_total"] / grouped["games_played"]
    grouped["reb_per_game"] = grouped["reb_total"] / grouped["games_played"]
    grouped["ast_per_game"] = grouped["ast_total"] / grouped["games_played"]
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


def _latest_advanced_team_rows(adv: pd.DataFrame) -> pd.DataFrame:
    work = adv.copy()

    if "as_of_date" in work.columns:
        work["_as_of_date_sort"] = pd.to_datetime(work["as_of_date"], errors="coerce")
    else:
        work["_as_of_date_sort"] = pd.NaT

    work = work.sort_values(
        by=["team_id", "_as_of_date_sort"],
        ascending=[True, False],
        na_position="last",
    ).drop_duplicates(subset=["team_id"], keep="first")

    keep_cols = [
        c
        for c in [
            "team_id",
            "team_name",
            "team_abbr",
            "games_played",
            "off_rating",
            "def_rating",
            "net_rating",
            "pace",
        ]
        if c in work.columns
    ]
    return work[keep_cols].copy()


def _merge_advanced_if_available(df: pd.DataFrame, adv_path: Path) -> pd.DataFrame:
    if not adv_path.exists():
        return df

    adv = pd.read_csv(adv_path)
    adv = _latest_advanced_team_rows(adv)

    if adv.empty:
        return df

    merged = df.merge(adv, on="team_id", how="left", suffixes=("", "_adv"))

    for col in ["team_name", "team_abbr", "off_rating", "def_rating", "net_rating", "pace"]:
        adv_col = f"{col}_adv"
        if adv_col in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].combine_first(merged[adv_col])
            else:
                merged[col] = merged[adv_col]
            merged = merged.drop(columns=[adv_col])

    if "games_played_adv" in merged.columns:
        merged["games_played"] = pd.to_numeric(merged["games_played"], errors="coerce")
        merged["games_played_adv"] = pd.to_numeric(merged["games_played_adv"], errors="coerce")
        merged["games_played"] = merged[["games_played", "games_played_adv"]].max(
            axis=1, skipna=True
        )
        merged = merged.drop(columns=["games_played_adv"])

    return merged


def _apply_default_guardrails(
    df: pd.DataFrame,
    target_col: str,
    min_games: int,
    date_window_active: bool = False,
    num_seasons: int = 1,
) -> pd.DataFrame:
    effective_min_games = max(
        min_games, _recommended_min_games(target_col, date_window_active=date_window_active)
    )
    df = df[df["games_played"] >= effective_min_games].copy()

    fga_floor = 400 * num_seasons
    fg3a_floor = 150 * num_seasons
    fta_floor = 100 * num_seasons

    if target_col in {"fg_pct", "efg_pct", "ts_pct"} and "fga_total" in df.columns:
        df = df[df["fga_total"] >= fga_floor].copy()

    if target_col == "fg3_pct" and "fg3a_total" in df.columns:
        df = df[df["fg3a_total"] >= fg3a_floor].copy()

    if target_col == "ft_pct" and "fta_total" in df.columns:
        df = df[df["fta_total"] >= fta_floor].copy()

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
) -> LeaderboardResult | NoResult:
    safe = season_type.lower().replace(" ", "_")

    try:
        seasons = resolve_seasons(season, start_season, end_season)
    except ValueError:
        return NoResult(query_class="leaderboard", reason="no_data")

    multi_season = len(seasons) > 1

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

    if multi_season and target_col in DATE_WINDOW_UNSUPPORTED_ADVANCED:
        raise ValueError(
            f"Multi-season leaderboard not supported for '{target_col}'. "
            "Use points, threes, eFG%, TS%, rebounds, or assists."
        )
    if date_window_active and target_col in DATE_WINDOW_UNSUPPORTED_ADVANCED:
        raise ValueError(
            f"Date-window leaderboard not supported for '{target_col}'. "
            "Use points, threes, eFG%, TS%, rebounds, or assists in a date window."
        )

    # Load and concatenate game logs across all seasons
    frames: list[pd.DataFrame] = []
    for s in seasons:
        basic_path = Path(f"data/raw/team_game_stats/{s}_{safe}.csv")
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

    if basic.empty:
        return NoResult(query_class="leaderboard", reason="no_data")

    df = _build_from_game_logs(basic)

    if not multi_season and not date_window_active:
        adv_path = Path(f"data/raw/team_season_advanced/{seasons[0]}_{safe}.csv")
        df = _merge_advanced_if_available(df, adv_path)

    if "games_played" not in df.columns:
        raise ValueError("games_played column is required")

    if target_col not in df.columns:
        raise ValueError(f"Column '{target_col}' not available")

    df = _apply_default_guardrails(
        df,
        target_col,
        min_games,
        date_window_active=date_window_active,
        num_seasons=len(seasons),
    )

    if df.empty:
        return NoResult(query_class="leaderboard")

    out_cols = ["team_name", "team_abbr", "team_id", "games_played", target_col]
    missing = [c for c in out_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required output columns: {missing}")

    result = (
        df[out_cols]
        .sort_values(
            by=[target_col, "games_played", "team_name"],
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
