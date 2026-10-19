from pathlib import Path

import pandas as pd

from nbatools.commands._condition_utils import (
    MARGIN_STATS,
    PLAYER_GAME_CONTEXT_STATS,
    apply_stat_conditions,
    attach_margin_stats,
)
from nbatools.commands._player_identity import select_player_rows
from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import (
    WINDOW_SCOPES,
    apply_last_n_sample,
    apply_player_clutch_filter,
    apply_player_role_filter,
    attach_player_game_context_stats,
    build_clutch_filter_coverage_note,
    build_opponent_mask,
    build_period_filter_coverage_note,
    filter_by_opponent_player,
    filter_period_rows,
    filter_with_player,
    filter_without_player,
    last_n_outcome,
    last_n_window_game_ids,
    load_player_game_period_stats_for_seasons,
    load_player_games_for_seasons,
    period_coverage_failure,
    period_window_label,
    team_value_mask,
)
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.player_occurrence_leaders import _flag_special_event
from nbatools.commands.playoff_history import (
    apply_series_situation_filter,
    series_situation_label,
)
from nbatools.commands.structured_results import FinderResult, NoResult

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
    "fg_pct": "fg_pct",
    "fg3_pct": "fg3_pct",
    "ft_pct": "ft_pct",
    "efg_pct": "efg_pct",
    "ts_pct": "ts_pct",
    "usg_pct": "usg_pct",
    "ast_pct": "ast_pct",
    "reb_pct": "reb_pct",
    "tov_pct": "tov_pct",
    **MARGIN_STATS,
    **PLAYER_GAME_CONTEXT_STATS,
}


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def _apply_filters(
    df: pd.DataFrame,
    player: str | None = None,
    team: str | None = None,
    opponent: str | list[str] | tuple[str, ...] | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    conditions: list[dict] | None = None,
    last_n: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    identity_notes: list[str] | None = None,
) -> pd.DataFrame:
    wanted = {stat, *(c.get("stat") for c in conditions or [])}
    out = attach_player_game_context_stats(attach_margin_stats(df.copy(), wanted), wanted)
    out["game_date"] = pd.to_datetime(out["game_date"]).dt.normalize()

    start_ts = _normalize_date_value(start_date)
    end_ts = _normalize_date_value(end_date)
    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise ValueError("start_date must be less than or equal to end_date")

    if start_ts is not None:
        out = out[out["game_date"] >= start_ts].copy()

    if end_ts is not None:
        out = out[out["game_date"] <= end_ts].copy()

    if player:
        out = select_player_rows(out, player, team=team, notes=identity_notes)

    if team:
        team_upper = team.upper()
        out = out[team_value_mask(out, team_upper)].copy()

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

    if conditions:
        out = apply_stat_conditions(out, conditions, ALLOWED_STATS)

    if out.empty:
        return out

    out = out.sort_values(["game_date", "game_id"], ascending=[False, False]).copy()

    if last_n is not None:
        if last_n <= 0:
            raise ValueError("last_n must be greater than 0")
        out = out.head(last_n).copy()

    return out


def _window_game_ids(
    df: pd.DataFrame,
    last_n: int,
    *,
    seasons: list[str],
    season_type: str,
    player: str | None,
    team: str | None,
    opponent,
    opponent_player: str | None,
    without_player: str | None,
    with_player: str | None,
    home_only: bool,
    away_only: bool,
    start_date: str | None,
    end_date: str | None,
    role: str | None,
    outcome: str | None = None,
) -> set[str]:
    """The player's N most recent games in play, before any game condition."""
    sample = _apply_filters(
        df=df,
        player=player,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        start_date=start_date,
        end_date=end_date,
    )
    if opponent_player and not sample.empty:
        sample = filter_by_opponent_player(sample, opponent_player, seasons, season_type)
    if without_player and not sample.empty:
        sample = filter_without_player(
            sample, without_player, seasons, season_type, team=team, opponent=opponent
        )
    if with_player and not sample.empty:
        sample = filter_with_player(sample, with_player, seasons, season_type, team=team)
    if role and not sample.empty:
        sample, _ = apply_player_role_filter(sample, seasons, season_type, role)
    return last_n_window_game_ids(sample, last_n, outcome)


# A per-game shooting rate ranks only games with this many attempts.
_RATE_SORT_ATTEMPTS = {
    "fg_pct": ("fga", 10, "field goal attempts"),
    "efg_pct": ("fga", 10, "field goal attempts"),
    "ts_pct": ("fga", 10, "field goal attempts"),
    "fg3_pct": ("fg3a", 5, "three-point attempts"),
    "ft_pct": ("fta", 5, "free throw attempts"),
}


def _apply_roster_filter(
    df: pd.DataFrame, position: str | None, rookies_only: bool, caveats: list[str]
) -> tuple[pd.DataFrame, str | None]:
    """Filter season-specific roster classifications, disclosing unknown games.

    Roster snapshots do not cover every appearance. A known subset can answer
    with a population caveat, but unknown classifications cannot prove no match.
    """
    from nbatools.commands.season_leaders import POSITION_GROUPS, _resolve_position_filter
    from nbatools.data_source import data_exists, data_read_csv

    codes = _resolve_position_filter(position) if position else None
    if position and not codes:
        return df, f"position filter unavailable: unknown position group {position!r}"
    if df.empty:
        return df, None
    needed = {"season", "player_id"} | ({"position"} if codes else set())
    needed |= {"experience_years"} if rookies_only else set()
    frames = []
    for season in sorted(df["season"].dropna().astype(str).unique()):
        path = Path(f"data/raw/rosters/{season}.csv")
        if not data_exists(path):
            return df, f"roster data unavailable for {season}: position and rookie filters"
        try:
            roster = data_read_csv(path)
        except pd.errors.EmptyDataError:
            return df, f"roster data unavailable for {season}: no roster rows"
        # Validate each slice before concatenating: another season's columns
        # must not conceal missing classification fields in this one.
        if not needed.issubset(roster.columns):
            return (
                df,
                f"roster data unavailable for {season}: missing requested classification columns",
            )
        roster = roster[roster["season"].astype(str) == season].copy()
        if roster.empty:
            return df, f"roster data unavailable for {season}: no roster rows"
        frames.append(roster)
    if not frames:
        return df, "roster classification unavailable: game rows have no season"
    rosters = pd.concat(frames, ignore_index=True)
    rosters["season"] = rosters["season"].astype(str)
    rosters["player_id"] = pd.to_numeric(rosters["player_id"], errors="coerce").astype(float)
    known = pd.Series(True, index=rosters.index)
    keep = pd.Series(True, index=rosters.index)
    if codes:
        positions = rosters["position"].astype("string").str.strip().str.upper()
        known &= positions.isin(set().union(*POSITION_GROUPS.values()))
        keep &= positions.isin(codes)
    if rookies_only:
        experience = pd.to_numeric(rosters["experience_years"], errors="coerce")
        known &= experience.ge(0) & experience.mod(1).eq(0)
        keep &= experience.eq(0)
    rosters["known"] = known
    rosters["matches"] = known & keep
    # Multiple team snapshots can list the same player-season. A positive
    # classification is evidence; a known nonmatch plus an unknown entry is
    # insufficient to exclude that player from the requested population.
    classification = rosters.groupby(["season", "player_id"]).agg(
        known=("known", "all"), matches=("matches", "any")
    )
    ids = pd.to_numeric(df["player_id"], errors="coerce").astype(float)
    games = pd.MultiIndex.from_arrays([df["season"].astype(str), ids])
    kept = games.isin(classification.index[classification["matches"]])
    classified = games.isin(
        classification.index[classification["known"] | classification["matches"]]
    )
    unknown_count = int((~classified).sum())
    if unknown_count:
        requested = " and ".join(
            label
            for label, active in (("position", bool(codes)), ("rookie", rookies_only))
            if active
        )
        if not kept.any():
            return df, (
                f"roster classification unavailable: {unknown_count} candidate games have unknown "
                f"{requested} classification; no matching games can be verified"
            )
        caveats.append(
            f"Incomplete population: ranking covers only games with known {requested} "
            f"classification; {unknown_count} games with missing roster entries or unknown "
            "requested classifications are left out"
        )
    return df[kept].copy(), None


def build_result(
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    opponent_player: str | None = None,
    without_player: str | None = None,
    with_player: str | None = None,
    special_event: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    conditions: list[dict] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 25,
    sort_by: str = "game_date",
    ascending: bool = False,
    last_n: int | None = None,
    clutch: bool = False,
    quarter: str | None = None,
    half: str | None = None,
    role: str | None = None,
    last_n_scope: str = "qualifying",
    series_situation: str | None = None,
    position: str | None = None,
    rookies_only: bool = False,
    per_season_limit: int | None = None,
) -> FinderResult | NoResult:
    from nbatools.commands.data_utils import validate_last_n_scope

    validate_last_n_scope(last_n_scope)
    seasons = resolve_seasons(season, start_season, end_season)
    notes: list[str] = []

    if home_only and away_only:
        return NoResult(
            query_class="finder",
            reason="unsupported",
            result_status="no_result",
            notes=["Cannot use both home_only and away_only"],
        )

    if wins_only and losses_only:
        return NoResult(
            query_class="finder",
            reason="unsupported",
            result_status="no_result",
            notes=["Cannot use both wins_only and losses_only"],
        )

    if sort_by not in {"game_date", "stat"}:
        return NoResult(
            query_class="finder",
            reason="unsupported",
            result_status="no_result",
            notes=["sort_by must be either 'game_date' or 'stat'"],
        )

    period_filter_requested = quarter is not None or half is not None

    try:
        base_df = load_player_games_for_seasons(seasons, season_type, player=player)
    except FileNotFoundError:
        if clutch:
            notes.append(build_clutch_filter_coverage_note("missing player game dataset"))
        return NoResult(query_class="finder", reason="no_data", notes=notes)
    base_df = apply_series_situation_filter(base_df, seasons, series_situation)

    if period_filter_requested:
        try:
            period_df = load_player_game_period_stats_for_seasons(seasons, season_type)
        except FileNotFoundError:
            coverage_note = build_period_filter_coverage_note(
                quarter=quarter,
                half=half,
                reason=(
                    "missing player_game_period_stats dataset for requested slice; "
                    f"window={period_window_label(quarter=quarter, half=half)}"
                ),
            )
            return NoResult(
                query_class="finder",
                reason="filter_not_supported",
                notes=[coverage_note] if coverage_note else [],
            )
        period_df = apply_series_situation_filter(period_df, seasons, series_situation)
        df = filter_period_rows(period_df, quarter=quarter, half=half)
    else:
        df = base_df

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

    if period_filter_requested:
        coverage_base = _apply_filters(
            df=base_df,
            player=player,
            team=team,
            opponent=opponent,
            home_only=home_only,
            away_only=away_only,
            start_date=start_date,
            end_date=end_date,
        )
        coverage_period = _apply_filters(
            df=df,
            player=player,
            team=team,
            opponent=opponent,
            home_only=home_only,
            away_only=away_only,
            start_date=start_date,
            end_date=end_date,
        )
        if opponent_player and not coverage_base.empty:
            coverage_base = filter_by_opponent_player(
                coverage_base, opponent_player, seasons, season_type
            )
            coverage_period = filter_by_opponent_player(
                coverage_period, opponent_player, seasons, season_type
            )
        if without_player and not coverage_base.empty:
            coverage_base = filter_without_player(
                coverage_base, without_player, seasons, season_type, team=team, opponent=opponent
            )
            coverage_period = filter_without_player(
                coverage_period, without_player, seasons, season_type, team=team, opponent=opponent
            )
        if with_player and not coverage_base.empty:
            coverage_base = filter_with_player(
                coverage_base, with_player, seasons, season_type, team=team
            )
            coverage_period = filter_with_player(
                coverage_period, with_player, seasons, season_type, team=team
            )
        if special_event and not coverage_base.empty:
            coverage_base = coverage_base[_flag_special_event(coverage_base, special_event)].copy()
            coverage_period = coverage_period[
                _flag_special_event(coverage_period, special_event)
            ].copy()
        coverage_failure = period_coverage_failure(
            coverage_base,
            coverage_period,
            dataset="player_game_period_stats",
            entity_key_columns=["team_id", "player_id"],
            quarter=quarter,
            half=half,
        )
        if coverage_failure:
            coverage_note = build_period_filter_coverage_note(
                quarter=quarter,
                half=half,
                reason=coverage_failure,
            )
            return NoResult(
                query_class="finder",
                reason="filter_not_supported",
                notes=[coverage_note] if coverage_note else [],
            )

    window_game_ids = None
    if last_n is not None and last_n_scope in WINDOW_SCOPES:
        window_game_ids = _window_game_ids(
            base_df,
            last_n,
            seasons=seasons,
            season_type=season_type,
            player=player,
            team=team,
            opponent=opponent,
            opponent_player=opponent_player,
            without_player=without_player,
            with_player=with_player,
            home_only=home_only,
            away_only=away_only,
            start_date=start_date,
            end_date=end_date,
            role=role,
            outcome=last_n_outcome(last_n_scope, wins_only, losses_only),
        )

    df = _apply_filters(
        df=df,
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
        conditions=conditions,
        start_date=start_date,
        end_date=end_date,
        identity_notes=notes,
    )

    # Cross-reference filters: opponent_player and without_player
    if opponent_player and not df.empty:
        df = filter_by_opponent_player(df, opponent_player, seasons, season_type)

    if without_player and not df.empty:
        df = filter_without_player(
            df, without_player, seasons, season_type, team=team, opponent=opponent
        )

    if with_player and not df.empty:
        df = filter_with_player(df, with_player, seasons, season_type, team=team)

    if special_event and not df.empty:
        df = df[_flag_special_event(df, special_event)].copy()

    if clutch:
        df, clutch_note = apply_player_clutch_filter(df, seasons, season_type)
        if clutch_note:
            return NoResult(
                query_class="finder",
                reason="filter_not_supported",
                notes=[clutch_note],
            )

    df, role_note = apply_player_role_filter(df, seasons, season_type, role)
    if role_note:
        return NoResult(
            query_class="finder",
            reason="filter_not_supported",
            notes=[role_note],
        )

    roster_caveats: list[str] = []
    if position or rookies_only:
        df, roster_note = _apply_roster_filter(df, position, rookies_only, roster_caveats)
        if roster_note:
            return NoResult(
                query_class="finder",
                reason="filter_not_supported",
                notes=[roster_note],
            )

    # Last N runs after every filter: on the qualifying games, or (window
    # scope) on the N most recent games in play.
    if last_n is not None and not df.empty:
        df = apply_last_n_sample(df, last_n, window_game_ids)

    if df.empty:
        return NoResult(
            query_class="finder",
            reason="filter_not_supported" if roster_caveats else "no_match",
            notes=notes + roster_caveats,
        )

    stat_col = None
    if stat:
        stat_col = ALLOWED_STATS[stat.lower()]

    caveats: list[str] = list(roster_caveats)
    if sort_by == "game_date":
        df = df.sort_values(["game_date", "game_id"], ascending=[ascending, ascending]).copy()
    else:
        if stat_col is None:
            raise ValueError("sort_by='stat' requires --stat")
        attempts = _RATE_SORT_ATTEMPTS.get(stat_col)
        if (
            attempts
            and min_value is None
            and max_value is None
            and last_n is None
            and attempts[0] in df.columns
        ):
            # "best shooting game": a 2-for-2 cameo is not one; rank games
            # with a real number of attempts and say so.
            column, floor, label = attempts
            kept = df[pd.to_numeric(df[column], errors="coerce") >= floor]
            if len(kept) < len(df):
                caveats.append(f"games with fewer than {floor} {label} left out")
            df = kept
            if df.empty:
                return NoResult(
                    query_class="finder",
                    reason="filter_not_supported" if roster_caveats else "no_match",
                    notes=notes + caveats,
                )
            # 10-for-10 ranks above 5-for-5.
            df = df.sort_values(
                [stat_col, column, "game_date"], ascending=[ascending, False, ascending]
            ).copy()
        else:
            df = df.sort_values([stat_col, "game_date"], ascending=[ascending, ascending]).copy()

    if per_season_limit is not None and sort_by == "stat":
        # "biggest win each season": each season's top games, newest season
        # first, in place of the span's top games.
        df = df.groupby("season", sort=False).head(per_season_limit)
        df = df.sort_values("season", ascending=False, kind="stable").copy()
        limit = None

    df = df.reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    if roster_caveats:
        # CSV/labeled text export contains the table without result caveats.
        # Keep the population limit attached to those rows as well.
        df["population_scope"] = "Incomplete population: known roster classifications only"

    if limit is not None:
        df = df.head(limit).copy()

    output_cols = [
        "rank",
        "population_scope",
        "game_date",
        "game_id",
        "season",
        "season_type",
        "player_name",
        "player_id",
        "team_name",
        "team_abbr",
        "opponent_team_name",
        "opponent_team_abbr",
        "is_home",
        "is_away",
        "wl",
        "minutes",
        "pts",
        "reb",
        "ast",
        "stl",
        "blk",
        "fgm",
        "fga",
        "fg_pct",
        "fg3m",
        "fg3a",
        "fg3_pct",
        "ftm",
        "fta",
        "ft_pct",
        "tov",
        "plus_minus",
        "efg_pct",
        "ts_pct",
        "clutch_events",
        "clutch_seconds",
        "usg_pct",
        "ast_pct",
        "reb_pct",
        "tov_pct",
    ]
    if stat_col in ("margin", "win_margin", "loss_margin") and stat_col not in output_cols:
        # "LeBron biggest wins": the team's final margin the list ranks by.
        output_cols.append(stat_col)
    output_cols = [c for c in output_cols if c in df.columns]

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return FinderResult(
        games=df[output_cols].copy(),
        current_through=current_through,
        notes=notes,
        caveats=(
            [f"playoff series situation: {series_situation_label(series_situation)}"]
            if series_situation
            else []
        )
        + caveats,
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
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 25,
    sort_by: str = "game_date",
    ascending: bool = False,
    last_n: int | None = None,
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
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        sort_by=sort_by,
        ascending=ascending,
        last_n=last_n,
    )
    if isinstance(result, NoResult):
        print("no matching games")
        return
    print(result.to_labeled_text(), end="")
