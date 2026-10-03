from __future__ import annotations

import pandas as pd

from nbatools.commands._streak_runs import best_runs_per_entity
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.game_finder import (
    ALLOWED_STATS,
    _apply_filters,
    load_team_games_for_seasons,
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
    if special_condition == "wins":
        return "wins"
    if special_condition == "losses":
        return "losses"

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
    if special_condition == "wins":
        if "wl" not in df.columns:
            raise ValueError("wl column required for winning streaks")
        return df["wl"].astype(str).eq("W")

    if special_condition == "losses":
        if "wl" not in df.columns:
            raise ValueError("wl column required for losing streaks")
        return df["wl"].astype(str).eq("L")

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
    streak_df: pd.DataFrame, team_name: str, condition: str, is_active: bool
) -> dict:
    wins = int((streak_df["wl"] == "W").sum()) if "wl" in streak_df.columns else 0
    losses = int((streak_df["wl"] == "L").sum()) if "wl" in streak_df.columns else 0

    row = {
        "team_name": team_name,
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

    for col in [
        "pts",
        "reb",
        "ast",
        "stl",
        "blk",
        "fg3m",
        "tov",
        "plus_minus",
        "efg_pct",
        "ts_pct",
    ]:
        if col in streak_df.columns:
            row[f"{col}_avg"] = round(pd.to_numeric(streak_df[col], errors="coerce").mean(), 3)

    return row


def _extract_streak_rows(
    df: pd.DataFrame, mask: pd.Series, team_name: str, condition: str
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
                    team_name=team_name,
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
                team_name=team_name,
                condition=condition,
                is_active=True,
            )
        )

    return rows


def _no_active_streak_row(df: pd.DataFrame, name: str, condition: str) -> dict:
    last = (
        df.assign(game_date=pd.to_datetime(df["game_date"]))
        .sort_values(["game_date", "game_id"])
        .iloc[-1]
    )
    return {
        "team_name": name,
        "condition": condition,
        "streak_length": 0,
        "games": 0,
        "start_date": None,
        "end_date": last["game_date"].date().isoformat(),
        "start_game_id": None,
        "end_game_id": last["game_id"],
        "wins": 0,
        "losses": 0,
        "is_active": 0,
    }


def build_result(
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
    special_condition: str | None = None,
    min_streak_length: int | None = None,
    longest: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    last_n: int | None = None,
    limit: int = 25,
    current: bool = False,
) -> StreakResult | NoResult:
    """Streaks of consecutive team games meeting a condition.

    With ``team`` set, list that team's streaks (``longest`` keeps the longest,
    ``current`` the one alive at its latest game). Without it, rank every team
    by its longest (or current) streak.
    """

    if min_streak_length is not None and min_streak_length <= 0:
        raise ValueError("min_streak_length must be greater than 0")

    seasons = resolve_seasons(season, start_season, end_season)
    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="streak", reason="no_data")

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

    filtered = _apply_filters(
        df=df,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=False,
        losses_only=False,
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

    if team is None:
        rows = [
            _finalize_streak(games, games["team_name"].iloc[-1], condition, active)
            for games, active in best_runs_per_entity(
                filtered, mask, "team_id", current=current, limit=limit
            )
        ]
    else:
        rows = _extract_streak_rows(filtered, mask, team_name=team, condition=condition)
        if current:
            rows = [row for row in rows if row["is_active"]]

    if min_streak_length is not None:
        rows = [row for row in rows if row["streak_length"] >= min_streak_length]

    no_active_streak = current and not rows and team is not None
    if no_active_streak:
        # The answer to "current streak" when the latest game missed is zero,
        # anchored on that game, not "no matching games".
        rows = [_no_active_streak_row(filtered, team, condition)]
    if current and not rows:
        return NoResult(
            query_class="streak",
            caveats=[f"no active streak: the latest game in range did not meet {condition}"],
        )

    if longest and rows and team is not None:
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
        "team_name",
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
        "pts_avg",
        "reb_avg",
        "ast_avg",
        "stl_avg",
        "blk_avg",
        "fg3m_avg",
        "tov_avg",
        "plus_minus_avg",
        "efg_pct_avg",
        "ts_pct_avg",
    ]
    output_cols = [c for c in output_cols if c in out.columns]

    current_through = compute_current_through_for_seasons(seasons, season_type)

    caveats: list[str] = []
    if no_active_streak:
        caveats.append(f"no active streak: the latest game in range did not meet {condition}")
    if team is None:
        caveats.append("each team's best streak in range, ranked by length")
    if len(seasons) > 1:
        caveats.append(
            f"streaks computed across {len(seasons)} seasons ({seasons[0]} to {seasons[-1]})"
        )
    if opponent:
        caveats.append(f"filtered to games vs {opponent.upper()}")
    if home_only:
        caveats.append("filtered to home games only")
    if away_only:
        caveats.append("filtered to away games only")

    return StreakResult(
        streaks=out[output_cols].copy(),
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
    special_condition: str | None = None,
    min_streak_length: int | None = None,
    longest: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    last_n: int | None = None,
    limit: int = 25,
    current: bool = False,
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
        special_condition=special_condition,
        min_streak_length=min_streak_length,
        longest=longest,
        start_date=start_date,
        end_date=end_date,
        last_n=last_n,
        limit=limit,
        current=current,
    )
    if isinstance(result, NoResult):
        print("no matching games")
        return
    print(result.to_labeled_text(), end="")
