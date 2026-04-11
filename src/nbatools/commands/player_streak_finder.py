from __future__ import annotations

import pandas as pd

from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.player_game_finder import (
    ALLOWED_STATS,
    _apply_filters,
    load_player_games_for_seasons,
    resolve_seasons,
)
from nbatools.commands.structured_results import NoResult, StreakResult


def _format_value(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _condition_label(
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    special_condition: str | None = None,
) -> str:
    if special_condition == "triple_double":
        return "triple_double"
    if special_condition == "made_three":
        return "made_three"

    if stat is None:
        return "condition"

    if min_value is not None and max_value is not None:
        return f"{stat}:{_format_value(min_value)}-{_format_value(max_value)}"
    if min_value is not None:
        return f"{stat}>={_format_value(min_value)}"
    if max_value is not None:
        return f"{stat}<={_format_value(max_value)}"
    return stat


def _build_condition_mask(
    df: pd.DataFrame,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    special_condition: str | None = None,
) -> pd.Series:
    if special_condition == "triple_double":
        categories = []
        for col in ["pts", "reb", "ast", "stl", "blk"]:
            if col in df.columns:
                categories.append(
                    (pd.to_numeric(df[col], errors="coerce").fillna(0) >= 10).astype(int)
                )
            else:
                categories.append(pd.Series(0, index=df.index))
        total = categories[0]
        for series in categories[1:]:
            total = total + series
        return total >= 3

    if special_condition == "made_three":
        if "fg3m" not in df.columns:
            raise ValueError("fg3m column required for made_three streaks")
        return pd.to_numeric(df["fg3m"], errors="coerce").fillna(0) >= 1

    if stat is None:
        raise ValueError("A stat is required for generic streak queries")

    stat_key = stat.lower()
    if stat_key not in ALLOWED_STATS:
        raise ValueError(f"Unsupported stat: {stat}")

    stat_col = ALLOWED_STATS[stat_key]
    if stat_col not in df.columns:
        raise ValueError(f"Column '{stat_col}' not available for streak queries")

    values = pd.to_numeric(df[stat_col], errors="coerce")
    mask = pd.Series(True, index=df.index)

    if min_value is not None:
        mask = mask & values.ge(min_value)

    if max_value is not None:
        mask = mask & values.le(max_value)

    return mask.fillna(False)


def _finalize_streak(
    streak_df: pd.DataFrame, player_name: str, condition: str, is_active: bool
) -> dict:
    wins = int((streak_df["wl"] == "W").sum()) if "wl" in streak_df.columns else 0
    losses = int((streak_df["wl"] == "L").sum()) if "wl" in streak_df.columns else 0

    row = {
        "player_name": player_name,
        "condition": condition,
        "streak_length": int(len(streak_df)),
        "games": int(len(streak_df)),
        "start_date": pd.to_datetime(streak_df.iloc[0]["game_date"]).date().isoformat(),
        "end_date": pd.to_datetime(streak_df.iloc[-1]["game_date"]).date().isoformat(),
        "start_game_id": streak_df.iloc[0]["game_id"],
        "end_game_id": streak_df.iloc[-1]["game_id"],
        "wins": wins,
        "losses": losses,
        "is_active": int(bool(is_active)),
    }

    for col in ["minutes", "pts", "reb", "ast", "stl", "blk", "fg3m", "tov", "plus_minus"]:
        if col in streak_df.columns:
            row[f"{col}_avg"] = round(pd.to_numeric(streak_df[col], errors="coerce").mean(), 3)

    return row


def _extract_streak_rows(
    df: pd.DataFrame, mask: pd.Series, player_name: str, condition: str
) -> list[dict]:
    if df.empty:
        return []

    work = df.copy()
    work["_condition_met"] = pd.Series(mask, index=df.index).fillna(False).astype(bool).values
    work["game_date"] = pd.to_datetime(work["game_date"])
    work = work.sort_values(["game_date", "game_id"], ascending=[True, True]).reset_index(drop=True)

    ordered_mask = work["_condition_met"].astype(bool)

    rows: list[dict] = []
    start_idx: int | None = None

    for idx, ok in enumerate(ordered_mask.tolist()):
        if ok:
            if start_idx is None:
                start_idx = idx
            continue

        if start_idx is not None:
            streak_df = (
                work.iloc[start_idx:idx].drop(columns=["_condition_met"], errors="ignore").copy()
            )
            rows.append(
                _finalize_streak(
                    streak_df,
                    player_name=player_name,
                    condition=condition,
                    is_active=idx == len(work),
                )
            )
            start_idx = None

    if start_idx is not None:
        streak_df = work.iloc[start_idx:].drop(columns=["_condition_met"], errors="ignore").copy()
        rows.append(
            _finalize_streak(
                streak_df,
                player_name=player_name,
                condition=condition,
                is_active=True,
            )
        )

    return rows


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
    special_condition: str | None = None,
    min_streak_length: int | None = None,
    longest: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    last_n: int | None = None,
    limit: int = 25,
) -> StreakResult | NoResult:
    if player is None:
        raise ValueError("player is required for player streak queries")

    if min_streak_length is not None and min_streak_length <= 0:
        raise ValueError("min_streak_length must be greater than 0")

    seasons = resolve_seasons(season, start_season, end_season)
    try:
        df = load_player_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="streak", reason="no_data")

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

    filtered = _apply_filters(
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
        last_n=last_n,
        start_date=start_date,
        end_date=end_date,
    )

    if filtered.empty:
        return NoResult(query_class="streak")

    mask = _build_condition_mask(
        filtered,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        special_condition=special_condition,
    )
    condition = _condition_label(
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        special_condition=special_condition,
    )

    rows = _extract_streak_rows(filtered, mask, player_name=player, condition=condition)

    if min_streak_length is not None:
        rows = [row for row in rows if row["streak_length"] >= min_streak_length]

    if longest and rows:
        max_len = max(row["streak_length"] for row in rows)
        rows = [row for row in rows if row["streak_length"] == max_len]

    if not rows:
        return NoResult(query_class="streak")

    out = pd.DataFrame(rows)
    out["end_date"] = pd.to_datetime(out["end_date"])
    out = out.sort_values(["streak_length", "end_date"], ascending=[False, False]).reset_index(
        drop=True
    )
    out["end_date"] = out["end_date"].dt.date.astype(str)
    out.insert(0, "rank", range(1, len(out) + 1))

    if limit is not None:
        out = out.head(limit).copy()

    output_cols = [
        "rank",
        "player_name",
        "condition",
        "streak_length",
        "games",
        "start_date",
        "end_date",
        "start_game_id",
        "end_game_id",
        "wins",
        "losses",
        "is_active",
        "minutes_avg",
        "pts_avg",
        "reb_avg",
        "ast_avg",
        "stl_avg",
        "blk_avg",
        "fg3m_avg",
        "tov_avg",
        "plus_minus_avg",
    ]
    output_cols = [c for c in output_cols if c in out.columns]

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return StreakResult(
        streaks=out[output_cols].copy(),
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
    special_condition: str | None = None,
    min_streak_length: int | None = None,
    longest: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    last_n: int | None = None,
    limit: int = 25,
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
        special_condition=special_condition,
        min_streak_length=min_streak_length,
        longest=longest,
        start_date=start_date,
        end_date=end_date,
        last_n=last_n,
        limit=limit,
    )
    if isinstance(result, NoResult):
        print("no matching games")
        return
    print(result.to_labeled_text(), end="")
