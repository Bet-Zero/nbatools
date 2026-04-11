import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_games_for_seasons
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
    "efg_pct": "efg_pct",
    "ts_pct": "ts_pct",
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
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
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

    if team:
        team_upper = team.upper()
        out = out[
            out["team_abbr"].astype(str).str.upper().eq(team_upper)
            | out["team_name"].astype(str).str.upper().eq(team_upper)
        ].copy()

    if opponent:
        opponent_upper = opponent.upper()
        out = out[
            out["opponent_team_abbr"].astype(str).str.upper().eq(opponent_upper)
            | out["opponent_team_name"].astype(str).str.upper().eq(opponent_upper)
        ].copy()

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

    if out.empty:
        return out

    out = out.sort_values(["game_date", "game_id"], ascending=[False, False]).copy()

    if last_n is not None:
        if last_n <= 0:
            raise ValueError("last_n must be greater than 0")
        out = out.head(last_n).copy()

    return out


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
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 25,
    sort_by: str = "game_date",
    ascending: bool = False,
    last_n: int | None = None,
) -> FinderResult | NoResult:
    seasons = resolve_seasons(season, start_season, end_season)

    if home_only and away_only:
        raise ValueError("Cannot use both home_only and away_only")

    if wins_only and losses_only:
        raise ValueError("Cannot use both wins_only and losses_only")

    if sort_by not in {"game_date", "stat"}:
        raise ValueError("sort_by must be either 'game_date' or 'stat'")

    df = load_team_games_for_seasons(seasons, season_type)

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

    df = _apply_filters(
        df=df,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        last_n=last_n,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        return NoResult(query_class="finder")

    stat_col = None
    if stat:
        stat_col = ALLOWED_STATS[stat.lower()]

    if sort_by == "game_date":
        df = df.sort_values(["game_date", "game_id"], ascending=[ascending, ascending]).copy()
    else:
        if stat_col is None:
            raise ValueError("sort_by='stat' requires --stat")
        df = df.sort_values([stat_col, "game_date"], ascending=[ascending, ascending]).copy()

    df = df.reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))

    if limit is not None:
        df = df.head(limit).copy()

    output_cols = [
        "rank",
        "game_date",
        "game_id",
        "season",
        "season_type",
        "team_name",
        "team_abbr",
        "opponent_team_name",
        "opponent_team_abbr",
        "is_home",
        "is_away",
        "wl",
        "pts",
        "reb",
        "ast",
        "fg3m",
        "fg3a",
        "tov",
        "plus_minus",
        "efg_pct",
        "ts_pct",
    ]
    output_cols = [c for c in output_cols if c in df.columns]

    return FinderResult(games=df[output_cols].copy())


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
