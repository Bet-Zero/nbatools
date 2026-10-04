"""Playoff history and era-bucket query module.

Provides playoff-round/series/appearance/era-bucketed history for teams
(and players where grounded).

Capabilities:
- Playoff record / summary by round (first round, conference finals, finals, etc.)
- Playoff appearances counting by round stage
- Playoff matchup history (team vs team playoff record)
- Era-bucket (by-decade) breakdowns of any team record or leaderboard
- Appearance leaderboard (most finals appearances, most playoff appearances, etc.)

Data model:
- Playoff round is read from game_id positions 7-8 where the id carries it
  (2001-02+); otherwise it is the order of the team's series that season
  (first opponent = first round), which also covers 1996-97 through 2000-01
- A series is every playoff game between two teams in one season; play-in
  games (game ids starting "005") are not playoff games
- Era buckets group seasons by decade (e.g., 2000s = 1999-00 through 2008-09)

All functions return structured result objects (SummaryResult,
ComparisonResult, LeaderboardResult, NoResult).
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import (
    EARLIEST_SEASON,
    default_end_season,
    int_to_season,
    resolve_seasons,
    season_to_int,
)
from nbatools.commands.data_utils import load_team_games_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Playoff round codes extracted from game_id[6:8]
ROUND_CODES = {
    "01": "First Round",
    "02": "Second Round",
    "03": "Conference Finals",
    "04": "Finals",
}

ROUND_ALIASES: dict[str, str] = {
    "first round": "01",
    "1st round": "01",
    "round 1": "01",
    "round one": "01",
    "second round": "02",
    "2nd round": "02",
    "round 2": "02",
    "round two": "02",
    "semifinals": "02",
    "semis": "02",
    "third round": "03",
    "3rd round": "03",
    "round 3": "03",
    "round three": "03",
    "conference finals": "03",
    "conf finals": "03",
    "conference final": "03",
    "conf final": "03",
    "finals": "04",
    "the finals": "04",
    "nba finals": "04",
    "championship": "04",
}

# Minimum season for round-level data
ROUND_DATA_START_SEASON = "2001-02"
ROUND_DATA_START_YEAR = 2001
# Playoff game rows start with the 1996-97 season.
DATA_START_YEAR = 1996

# ---------------------------------------------------------------------------
# Helpers: round extraction
# ---------------------------------------------------------------------------


def _game_id_text(game_ids: pd.Series) -> pd.Series:
    """Ten-character game ids: CSVs read as numbers drop the leading zeros
    ("0042300401" becomes 42300401), which moves the round code."""
    text = game_ids.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    dropped_zeros = text.str.isdigit() & text.str.len().isin([8, 9])
    return text.where(~dropped_zeros, text.str.zfill(10))


def extract_playoff_round(game_id: str) -> str | None:
    """Extract the playoff round code from a game_id.

    Returns the 2-char round code ('01'-'04') or None if not determinable.
    game_id format: 004YYRRGSN where positions 6-7 (0-indexed) hold RR.
    """
    gid = _game_id_text(pd.Series([game_id])).iloc[0]
    if len(gid) < 8:
        return None
    code = gid[6:8]
    if code in ROUND_CODES:
        return code
    return None


def round_code_to_label(code: str) -> str:
    """Convert a round code to a human-readable label."""
    return ROUND_CODES.get(code, f"Round {code}")


def resolve_round_filter(text: str) -> str | None:
    """Resolve a natural-language round reference to a round code.

    Returns a 2-char code like '01', '04', or None if not matched.
    """
    t = text.lower().strip()
    return ROUND_ALIASES.get(t)


# ---------------------------------------------------------------------------
# Helpers: era/decade bucketing
# ---------------------------------------------------------------------------


def season_to_decade(season: str) -> str:
    """Map a season string to its decade bucket label.

    '2003-04' → '2000s', '2019-20' → '2010s', '1999-00' → '1990s'.
    The decade is determined by the start year of the season.
    """
    year = season_to_int(season)
    decade_start = (year // 10) * 10
    return f"{decade_start}s"


def decade_season_range(decade_label: str) -> tuple[str, str]:
    """Given a decade label like '2000s', return (start_season, end_season).

    '2000s' → ('2000-01', '2009-10')
    Clamped to EARLIEST_SEASON and the latest served season.
    """
    decade_start = int(decade_label.rstrip("s"))
    decade_end = decade_start + 9
    earliest = season_to_int(EARLIEST_SEASON)
    start = max(decade_start, earliest)
    end = min(decade_end, season_to_int(default_end_season("Regular Season")))
    return int_to_season(start), int_to_season(end)


def _series_order_codes(df: pd.DataFrame) -> pd.Series:
    """Round code from the order of each team's series within a season.

    Needs every playoff game of the team that season: the first opponent is
    the first round, the second the second round, and so on.
    """
    key = ["season", "team_id", "opponent_team_id"]
    first_game = pd.to_datetime(df["game_date"]).groupby([df[k] for k in key]).transform("min")
    order = first_game.groupby([df["season"], df["team_id"]]).rank(method="dense")
    return order.map(lambda n: f"{int(n):02d}" if pd.notna(n) and 1 <= n <= 4 else None)


def _add_round_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'playoff_round_code' and 'playoff_round' columns.

    Call on the full playoff game log (see ``_load_playoff_games``) before any
    team or opponent filter, since the series-order fallback counts series.
    Already-labelled frames are returned unchanged.
    """
    if "playoff_round_code" in df.columns:
        return df
    out = df.copy()
    id_code = _game_id_text(out["game_id"]).str[6:8]
    id_code = id_code.where(id_code.isin(list(ROUND_CODES)))
    if out.empty:
        out["playoff_round_code"] = id_code
    else:
        out["playoff_round_code"] = id_code.fillna(_series_order_codes(out))
    out["playoff_round"] = out["playoff_round_code"].map(ROUND_CODES).fillna("Unknown Round")
    return out


def _load_playoff_games(seasons: list[str]) -> pd.DataFrame:
    """Every playoff game in ``seasons`` with its round, play-in games dropped."""
    df = load_team_games_for_seasons(seasons, "Playoffs")
    df = df[~_game_id_text(df["game_id"]).str.startswith("005")].copy()
    return _add_round_column(df)


def _series_wins_needed(season: str, round_code: str | None) -> int:
    """First rounds were best-of-five through 2001-02, every other series best-of-seven."""
    if round_code == "01" and season_to_int(season) <= ROUND_DATA_START_YEAR:
        return 3
    return 4


def _build_series_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per series in a team's playoff game log, oldest first."""
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    work["_win"] = work["wl"].astype(str).eq("W").astype(int)
    work["_loss"] = work["wl"].astype(str).eq("L").astype(int)
    series = (
        work.groupby(
            ["season", "team_name", "opponent_team_id", "opponent_team_name"], as_index=False
        )
        .agg(
            opponent_team_abbr=("opponent_team_abbr", "last"),
            playoff_round_code=("playoff_round_code", "first"),
            wins=("_win", "sum"),
            losses=("_loss", "sum"),
            start_date=("game_date", "min"),
            end_date=("game_date", "max"),
        )
        .sort_values(["season", "start_date"])
        .reset_index(drop=True)
    )
    needed = [
        _series_wins_needed(season, code)
        for season, code in zip(series["season"], series["playoff_round_code"], strict=True)
    ]
    series["result"] = [
        "Won" if wins >= need else "Lost" if losses >= need else "In progress"
        for wins, losses, need in zip(series["wins"], series["losses"], needed, strict=True)
    ]
    series["playoff_round"] = series["playoff_round_code"].map(ROUND_CODES).fillna("Unknown Round")
    series["start_date"] = pd.to_datetime(series["start_date"]).dt.date.astype(str)
    series["end_date"] = pd.to_datetime(series["end_date"]).dt.date.astype(str)
    return series[
        [
            "season",
            "playoff_round",
            "opponent_team_name",
            "opponent_team_abbr",
            "wins",
            "losses",
            "result",
            "start_date",
            "end_date",
        ]
    ]


# ---------------------------------------------------------------------------
# Series situations: game 7s, elimination and closeout games, series scores
# ---------------------------------------------------------------------------

_SERIES_STATE_COLUMNS = [
    "_series_game_number",
    "_series_wins_before",
    "_series_losses_before",
    "_series_wins_needed",
]


def series_situation_label(situation: str) -> str:
    """Plain words for a series situation code."""
    if situation.startswith("game_"):
        numbers = situation.removeprefix("game_").split("_")
        if len(numbers) == 1:
            return f"game {numbers[0]}s"
        return "games " + ", ".join(numbers[:-1]) + f" and {numbers[-1]}"
    if situation.startswith("score_"):
        wins, losses = situation.removeprefix("score_").split("_")
        return f"games played with the series at {wins}-{losses}"
    return {
        "elimination": "elimination games (one loss from going home)",
        "closeout": "closeout games (one win from taking the series)",
        "deciding": "deciding games (winner takes the series)",
    }.get(situation, situation)


def _series_game_key(game_ids: pd.Series) -> pd.Series:
    """Game id without leading zeros: loaders read ids as numbers or as text."""
    return _game_id_text(game_ids).str.lstrip("0")


def _series_state(seasons: list[str]) -> pd.DataFrame:
    """Series state before each team's playoff game.

    One row per (game, team): the game's number in its series and the team's
    series wins and losses before it, from every playoff game of the seasons.
    """
    games = _load_playoff_games(seasons)
    if games.empty:
        return pd.DataFrame(columns=["_game_key", "team_id", *_SERIES_STATE_COLUMNS])
    work = games.copy()
    work["_game_key"] = _series_game_key(work["game_id"])
    work["_date"] = pd.to_datetime(work["game_date"], errors="coerce")
    work = work.drop_duplicates(["_game_key", "team_id"]).sort_values(["_date", "_game_key"])
    key = [work["season"], work["team_id"], work["opponent_team_id"]]
    win = work["wl"].astype(str).eq("W").astype(int)
    loss = work["wl"].astype(str).eq("L").astype(int)
    work["_series_game_number"] = work.groupby(key).cumcount() + 1
    work["_series_wins_before"] = win.groupby(key).cumsum() - win
    work["_series_losses_before"] = loss.groupby(key).cumsum() - loss
    work["_series_wins_needed"] = [
        _series_wins_needed(season, code)
        for season, code in zip(work["season"], work["playoff_round_code"], strict=True)
    ]
    return work[["_game_key", "team_id", *_SERIES_STATE_COLUMNS]]


def _situation_mask(state: pd.DataFrame, situation: str) -> pd.Series:
    number = state["_series_game_number"]
    wins = state["_series_wins_before"]
    losses = state["_series_losses_before"]
    needed = state["_series_wins_needed"]
    if situation.startswith("game_"):
        return number.isin([int(n) for n in situation.removeprefix("game_").split("_")])
    if situation.startswith("score_"):
        want_wins, want_losses = (int(n) for n in situation.removeprefix("score_").split("_"))
        return wins.eq(want_wins) & losses.eq(want_losses)
    live = wins.lt(needed) & losses.lt(needed)
    if situation == "elimination":
        return live & losses.eq(needed - 1)
    if situation == "closeout":
        return live & wins.eq(needed - 1)
    if situation == "deciding":
        return wins.eq(needed - 1) & losses.eq(needed - 1)
    raise ValueError(f"Unknown series situation: {situation}")


def apply_series_situation_filter(
    df: pd.DataFrame, seasons: list[str], situation: str | None
) -> pd.DataFrame:
    """Keep the playoff game rows (team or player) played in ``situation``.

    Rows need ``game_id`` and ``team_id``; the series state is the row's team's.
    """
    if not situation or df.empty:
        return df.copy()
    try:
        state = _series_state(seasons)
    except FileNotFoundError:
        return df.iloc[0:0].copy()
    state = state[_situation_mask(state, situation)]
    keys = pd.MultiIndex.from_arrays(
        [state["_game_key"], pd.to_numeric(state["team_id"], errors="coerce")]
    )
    row_keys = pd.MultiIndex.from_arrays(
        [_series_game_key(df["game_id"]), pd.to_numeric(df["team_id"], errors="coerce")]
    )
    return df[row_keys.isin(keys)].copy()


def _add_decade_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'decade' column from the season column."""
    out = df.copy()
    out["decade"] = out["season"].apply(season_to_decade)
    return out


def _compute_record(df: pd.DataFrame) -> dict:
    """Compute wins/losses/win_pct from a filtered game log."""
    if df.empty:
        return {"games": 0, "wins": 0, "losses": 0, "win_pct": None}
    games = len(df)
    wins = int((df["wl"] == "W").sum())
    losses = int((df["wl"] == "L").sum())
    win_pct = round(wins / games, 3) if games > 0 else None
    return {"games": games, "wins": wins, "losses": losses, "win_pct": win_pct}


def _has_round_data(seasons: list[str]) -> bool:
    """Check whether any season in the list supports round-level data."""
    return any(season_to_int(s) >= ROUND_DATA_START_YEAR for s in seasons)


def _round_data_caveat(seasons: list[str]) -> str | None:
    """Caveat for seasons whose rounds come from series order, not game ids."""
    early = [s for s in seasons if DATA_START_YEAR <= season_to_int(s) < ROUND_DATA_START_YEAR]
    if early:
        return (
            f"round data for {early[0]} to {early[-1]} is read from the order of each "
            "team's series (game ids before 2001-02 do not carry the round)"
        )
    return None


# ---------------------------------------------------------------------------
# Public API: team playoff history / record by round
# ---------------------------------------------------------------------------


def build_playoff_history_result(
    *,
    team: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    by_decade: bool = False,
    opponent: str | None = None,
) -> SummaryResult | NoResult:
    """Build a playoff history summary for a single team.

    Optionally filtered by round and/or bucketed by decade.

    Parameters
    ----------
    team : str
        Team abbreviation or name.
    playoff_round : str | None
        Round code ('01'-'04') to filter by, or None for all rounds.
    by_decade : bool
        If True, break down by decade instead of by season.
    opponent : str | None
        Optional opponent filter.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = _load_playoff_games(seasons)
    except FileNotFoundError:
        return NoResult(query_class="summary", reason="no_data")

    # Filter to the requested team
    t = team.upper()
    df = df[
        df["team_abbr"].astype(str).str.upper().eq(t)
        | df["team_name"].astype(str).str.upper().eq(t)
    ].copy()

    if df.empty:
        span = f"in {seasons[0]}" if len(seasons) == 1 else f"from {seasons[0]} to {seasons[-1]}"
        return NoResult(
            query_class="summary",
            reason="no_match",
            notes=[f"{t} played no playoff games {span}"],
        )

    if opponent:
        o = opponent.upper()
        mask = pd.Series(False, index=df.index)
        if "opponent_team_abbr" in df.columns:
            mask = mask | df["opponent_team_abbr"].astype(str).str.upper().eq(o)
        if "opponent_team_name" in df.columns:
            mask = mask | df["opponent_team_name"].astype(str).str.upper().eq(o)
        df = df[mask].copy()
        if df.empty:
            return NoResult(query_class="summary", reason="no_match")

    df = _add_round_column(df)
    df = _add_decade_column(df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)
    if season_to_int(seasons[0]) < DATA_START_YEAR:
        caveats.append("playoff data starts in 1996-97; earlier seasons are not counted")

    # Filter by round if requested
    if playoff_round:
        df = df[df["playoff_round_code"] == playoff_round].copy()
        if df.empty:
            round_label = round_code_to_label(playoff_round)
            return NoResult(
                query_class="summary",
                reason="no_match",
                notes=[f"No {round_label} games found for {team.upper()}"],
            )

    # Overall record
    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    rec = _compute_record(df)
    season_min = df["season"].min()
    season_max = df["season"].max()

    summary_row = {
        "team_name": team_name,
        "season_start": season_min,
        "season_end": season_max,
        "season_type": "Playoffs",
        **rec,
    }
    if playoff_round:
        summary_row["playoff_round"] = round_code_to_label(playoff_round)

    series = _build_series_table(df)
    summary_row["series_won"] = int((series["result"] == "Won").sum())
    summary_row["series_lost"] = int((series["result"] == "Lost").sum())
    if not playoff_round and not opponent:
        finals = series[series["playoff_round"] == "Finals"]
        summary_row["finals_appearances"] = int(finals["season"].nunique())
        summary_row["titles"] = int((finals["result"] == "Won").sum())

    # Appearances by season
    appearances = df.groupby("season")["game_id"].nunique().reset_index()
    appearances.columns = ["season", "games"]
    summary_row["seasons_appeared"] = len(appearances)

    summary = pd.DataFrame([summary_row])

    # Breakdown: by decade or by season
    if by_decade:
        by_group = _build_decade_breakdown(df, playoff_round=playoff_round)
    else:
        by_group = _build_season_breakdown(df, playoff_round=playoff_round)

    if len(seasons) > 1:
        caveats.append(f"playoff history aggregated across {seasons[0]} to {seasons[-1]}")
    if opponent:
        caveats.append(f"filtered to playoff games vs {opponent.upper()}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    # Use by_season field for backward compatibility; by_decade goes there too
    return SummaryResult(
        summary=summary,
        by_season=by_group,
        series=series,
        current_through=current_through,
        caveats=caveats,
    )


def _build_season_breakdown(df: pd.DataFrame, *, playoff_round: str | None = None) -> pd.DataFrame:
    """Build a by-season breakdown of playoff record."""
    agg_map: dict = {
        "games": ("game_id", "nunique"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
    }
    by_season = (
        df.groupby("season", as_index=False)
        .agg(**agg_map)
        .sort_values("season")
        .reset_index(drop=True)
    )
    if not by_season.empty:
        by_season["win_pct"] = (by_season["wins"] / by_season["games"]).round(3)

    # Add round-level detail per season if no round filter
    if playoff_round is None and "playoff_round" in df.columns:
        # Add deepest round reached per season
        round_order = {"First Round": 1, "Second Round": 2, "Conference Finals": 3, "Finals": 4}
        deepest = (
            df.groupby("season")["playoff_round"]
            .apply(lambda x: max(x, key=lambda r: round_order.get(r, 0)))
            .reset_index()
        )
        deepest.columns = ["season", "deepest_round"]
        by_season = by_season.merge(deepest, on="season", how="left")

    return by_season


def _build_decade_breakdown(df: pd.DataFrame, *, playoff_round: str | None = None) -> pd.DataFrame:
    """Build a by-decade breakdown of playoff record."""
    agg_map: dict = {
        "games": ("game_id", "nunique"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
        "seasons_appeared": ("season", "nunique"),
    }
    by_decade = (
        df.groupby("decade", as_index=False)
        .agg(**agg_map)
        .sort_values("decade")
        .reset_index(drop=True)
    )
    if not by_decade.empty:
        by_decade["win_pct"] = (by_decade["wins"] / by_decade["games"]).round(3)

    return by_decade


# ---------------------------------------------------------------------------
# Public API: team record by decade (regular season or playoffs)
# ---------------------------------------------------------------------------


def build_record_by_decade_result(
    *,
    team: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Playoffs",
    opponent: str | None = None,
) -> SummaryResult | NoResult:
    """Build a team record broken down by decade.

    Works for both regular season and playoffs.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = (
            _load_playoff_games(seasons)
            if season_type == "Playoffs"
            else load_team_games_for_seasons(seasons, season_type)
        )
    except FileNotFoundError:
        return NoResult(query_class="summary", reason="no_data")

    t = team.upper()
    df = df[
        df["team_abbr"].astype(str).str.upper().eq(t)
        | df["team_name"].astype(str).str.upper().eq(t)
    ].copy()

    if df.empty:
        span = f"in {seasons[0]}" if len(seasons) == 1 else f"from {seasons[0]} to {seasons[-1]}"
        return NoResult(
            query_class="summary",
            reason="no_match",
            notes=[f"{t} played no playoff games {span}"],
        )

    if opponent:
        o = opponent.upper()
        mask = pd.Series(False, index=df.index)
        if "opponent_team_abbr" in df.columns:
            mask = mask | df["opponent_team_abbr"].astype(str).str.upper().eq(o)
        if "opponent_team_name" in df.columns:
            mask = mask | df["opponent_team_name"].astype(str).str.upper().eq(o)
        df = df[mask].copy()
        if df.empty:
            return NoResult(query_class="summary", reason="no_match")

    df = _add_decade_column(df)

    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    rec = _compute_record(df)

    summary_row = {
        "team_name": team_name,
        "season_start": df["season"].min(),
        "season_end": df["season"].max(),
        "season_type": season_type,
        **rec,
    }
    summary = pd.DataFrame([summary_row])

    by_decade = _build_decade_breakdown(df)

    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(f"record by decade aggregated across {seasons[0]} to {seasons[-1]}")
    if opponent:
        caveats.append(f"filtered to games vs {opponent.upper()}")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return SummaryResult(
        summary=summary,
        by_season=by_decade,  # by_decade goes in the by_season slot
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: matchup record by decade
# ---------------------------------------------------------------------------


def build_matchup_by_decade_result(
    *,
    team_a: str,
    team_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
) -> ComparisonResult | NoResult:
    """Build a matchup record comparison broken down by decade.

    Returns overall comparison plus decade-level breakdown.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = (
            _load_playoff_games(seasons)
            if season_type == "Playoffs"
            else load_team_games_for_seasons(seasons, season_type)
        )
    except FileNotFoundError:
        return NoResult(query_class="comparison", reason="no_data")

    # Filter team A vs team B
    a_upper, b_upper = team_a.upper(), team_b.upper()

    a_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["team_name"].astype(str).str.upper().eq(a_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(b_upper)
        )
    ].copy()

    b_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["team_name"].astype(str).str.upper().eq(b_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(a_upper)
        )
    ].copy()

    if a_df.empty and b_df.empty:
        return NoResult(query_class="comparison", reason="no_match")

    a_df = _add_decade_column(a_df)
    b_df = _add_decade_column(b_df)

    rec_a = _compute_record(a_df)
    rec_b = _compute_record(b_df)

    team_a_name = (
        a_df["team_name"].mode().iloc[0]
        if not a_df.empty and "team_name" in a_df.columns
        else team_a
    )
    team_b_name = (
        b_df["team_name"].mode().iloc[0]
        if not b_df.empty and "team_name" in b_df.columns
        else team_b
    )

    summary = pd.DataFrame(
        [
            {"team_name": team_a_name, **rec_a},
            {"team_name": team_b_name, **rec_b},
        ]
    )

    # By-decade breakdown: show both teams' records per decade
    all_decades = sorted(set(a_df["decade"].unique()) | set(b_df["decade"].unique()))
    decade_rows = []
    for dec in all_decades:
        a_dec = a_df[a_df["decade"] == dec]
        b_dec = b_df[b_df["decade"] == dec]
        ra = _compute_record(a_dec)
        rb = _compute_record(b_dec)
        decade_rows.append(
            {
                "decade": dec,
                f"{team_a.upper()}_wins": ra["wins"],
                f"{team_a.upper()}_losses": ra["losses"],
                f"{team_a.upper()}_win_pct": ra["win_pct"],
                f"{team_b.upper()}_wins": rb["wins"],
                f"{team_b.upper()}_losses": rb["losses"],
                f"{team_b.upper()}_win_pct": rb["win_pct"],
            }
        )

    comparison = pd.DataFrame(decade_rows) if decade_rows else pd.DataFrame()

    caveats = [
        f"matchup history: {team_a.upper()} vs {team_b.upper()} by decade",
    ]
    if season_type == "Playoffs":
        caveats.append("playoff games only")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return ComparisonResult(
        summary=summary,
        comparison=comparison,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: playoff appearances (leaderboard)
# ---------------------------------------------------------------------------


def build_playoff_appearances_result(
    *,
    player: str | None = None,
    team: str | None = None,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    limit: int = 10,
    ascending: bool = False,
    titles: bool = False,
    player_titles: bool = False,
) -> LeaderboardResult | SummaryResult | NoResult:
    """Count playoff appearances, optionally filtered by round stage.

    With ``titles`` (and no team), rank teams by Finals series won instead;
    with ``titles`` and ``player`` or ``player_titles``, count a player's
    rings (titles won with a team he played for in those playoffs).

    A *player* without ``titles`` returns an explicit unsupported result
    because appearances are team-grain. If *team* is given, returns a
    SummaryResult for that team.
    If no team, returns a LeaderboardResult ranking all teams.

    An "appearance" = the team played at least one game in that
    season at the specified round (or any playoff game if no round).
    """
    seasons = resolve_seasons(season, start_season, end_season)

    if titles and (player or player_titles):
        return _player_titles_result(seasons, player=player, limit=limit)
    if player or player_titles:
        return NoResult(
            query_class="leaderboard",
            reason="filter_not_supported",
            notes=[
                "player playoff-appearance counts are not supported because "
                "the current route has team-grain data only"
            ],
        )

    try:
        df = _load_playoff_games(seasons)
    except FileNotFoundError:
        return NoResult(
            query_class="leaderboard" if not team else "summary",
            reason="no_data",
        )

    df = _add_round_column(df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)

    # Apply round filter
    round_label = "Playoffs"
    if playoff_round:
        round_label = round_code_to_label(playoff_round)
        df = df[df["playoff_round_code"] == playoff_round].copy()
        if df.empty:
            return NoResult(
                query_class="leaderboard" if not team else "summary",
                reason="no_match",
                notes=[f"No {round_label} games found in the specified span"],
            )

    # Count appearances: distinct seasons per team at this stage
    appearances = df.groupby(["team_abbr", "team_name"])["season"].nunique().reset_index()
    appearances.columns = ["team_abbr", "team_name", "appearances"]

    if team:
        # Single-team summary
        t = team.upper()
        team_rows = appearances[
            appearances["team_abbr"].astype(str).str.upper().eq(t)
            | appearances["team_name"].astype(str).str.upper().eq(t)
        ]
        if team_rows.empty:
            return NoResult(query_class="summary", reason="no_match")

        row = team_rows.iloc[0]
        summary_row = {
            "team_name": row["team_name"],
            "appearances": int(row["appearances"]),
            "round": round_label,
            "season_start": df["season"].min(),
            "season_end": df["season"].max(),
        }

        # Breakdown: which seasons they appeared
        team_df = df[
            df["team_abbr"].astype(str).str.upper().eq(t)
            | df["team_name"].astype(str).str.upper().eq(t)
        ]
        season_detail = (
            team_df.groupby("season")
            .agg(
                games=("game_id", "nunique"),
                wins=("wl", lambda s: int((s == "W").sum())),
                losses=("wl", lambda s: int((s == "L").sum())),
            )
            .reset_index()
            .sort_values("season")
        )
        if not season_detail.empty:
            season_detail["win_pct"] = (season_detail["wins"] / season_detail["games"]).round(3)

        caveats.append(f"{round_label} appearances for {row['team_name']}")
        current_through = compute_current_through_for_seasons(seasons, "Playoffs")

        return SummaryResult(
            summary=pd.DataFrame([summary_row]),
            by_season=season_detail,
            current_through=current_through,
            caveats=caveats,
        )

    if titles:
        return _titles_leaderboard(df, seasons, limit=limit, caveats=caveats)

    # Leaderboard: all teams ranked by appearances
    result = (
        appearances.sort_values(
            by=["appearances", "team_name"],
            ascending=[ascending, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )
    result.insert(0, "rank", range(1, len(result) + 1))
    result["round"] = round_label
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        result["season"] = seasons[0]

    caveats.append(f"{round_label} appearances leaderboard")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
        caveats=caveats,
    )


def _champions(df: pd.DataFrame) -> pd.DataFrame:
    """The team that won each completed Finals in ``df``: season, team id and names."""
    finals = df[df["playoff_round_code"] == "04"]
    if finals.empty:
        return pd.DataFrame(columns=["season", "_team_key", "team_abbr", "team_name"])
    work = finals.assign(
        _team_key=finals["team_id"].astype(str).str.removesuffix(".0"),
        _win=finals["wl"].astype(str).eq("W").astype(int),
    )
    # A repeated game row must not count as a second win.
    work = work.drop_duplicates(["season", "game_id", "_team_key"])
    wins = work.groupby(["season", "_team_key"], as_index=False).agg(
        team_abbr=("team_abbr", "last"), team_name=("team_name", "last"), wins=("_win", "sum")
    )
    needed = wins["season"].map(lambda value: _series_wins_needed(value, "04"))
    return wins[wins["wins"] >= needed].drop(columns="wins").reset_index(drop=True)


def _player_titles_result(
    seasons: list[str], *, player: str | None, limit: int
) -> LeaderboardResult | NoResult:
    """Rings: titles won by a team the player played for in those playoffs.

    A player counts a title when he played at least one playoff game that
    season for the team that won the Finals.
    """
    from nbatools.commands._player_identity import player_ids_for_name, select_player_rows
    from nbatools.commands.data_utils import load_player_games_for_seasons

    caveats = ["rings are titles won while playing at least one playoff game for the champion"]
    notes: list[str] = []
    if player and not player_ids_for_name(player):
        return NoResult(
            query_class="leaderboard", reason="no_match", notes=[f"No player named {player}"]
        )
    try:
        champions = _champions(_load_playoff_games(seasons))
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")
    if champions.empty:
        return NoResult(
            query_class="leaderboard",
            reason="no_match",
            notes=["No completed Finals found in the specified span"],
        )
    games = load_player_games_for_seasons(
        sorted(champions["season"].unique()), "Playoffs", player=player
    )
    if player:
        games = select_player_rows(games, player, notes=notes)
    games = games.assign(_team_key=games["team_id"].astype(str).str.removesuffix(".0"))
    won = games.merge(champions, on=["season", "_team_key"], suffixes=("", "_champion"))
    won = won.drop_duplicates(["player_id", "season"]).sort_values("season")
    rows = []
    for player_id, titles in won.groupby("player_id"):
        rows.append(
            {
                "player_id": player_id,
                "player_name": str(titles["player_name"].mode().iloc[0]),
                "titles": len(titles),
                "title_seasons": ", ".join(titles["season"]),
                "title_teams": ", ".join(titles["team_abbr_champion"]),
            }
        )
    board = pd.DataFrame(rows)
    if player and board.empty:
        from nbatools.commands._player_identity import canonical_player_names_by_id

        canonical = canonical_player_names_by_id()
        ids = list(player_ids_for_name(player))
        name = canonical.get(ids[0], player) if ids else player
        board = pd.DataFrame(
            [{"player_name": name, "titles": 0, "title_seasons": "", "title_teams": ""}]
        )
    if board.empty:
        return NoResult(query_class="leaderboard", reason="no_match")
    ranked = board.sort_values(["titles", "player_name"], ascending=[False, True])
    if not player and len(ranked) > limit:
        # Never cut a tie: every player level with the last one kept stays.
        cutoff = ranked["titles"].iloc[limit - 1]
        ranked = ranked[ranked["titles"] >= cutoff]
    result = ranked.drop(columns=["player_id"], errors="ignore").reset_index(drop=True)
    result.insert(0, "rank", range(1, len(result) + 1))
    if season_to_int(seasons[0]) < DATA_START_YEAR:
        caveats.append("playoff data starts in 1996-97; earlier titles are not counted")
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")
    else:
        result["season"] = seasons[0]
    return LeaderboardResult(
        leaders=result,
        current_through=compute_current_through_for_seasons(seasons, "Playoffs"),
        caveats=caveats + notes,
    )


def _titles_leaderboard(
    df: pd.DataFrame, seasons: list[str], *, limit: int, caveats: list[str]
) -> LeaderboardResult | NoResult:
    """Teams ranked by Finals series won, from Finals game rows."""
    finals = df[df["playoff_round_code"] == "04"]
    rows = []
    for (abbr, name), team_games in finals.groupby(["team_abbr", "team_name"]):
        series = _build_series_table(team_games)
        won = series[series["result"] == "Won"]
        row = {
            "team_abbr": abbr,
            "team_name": name,
            "titles": len(won),
            "finals_appearances": len(series),
            "title_seasons": ", ".join(str(s) for s in won["season"]),
        }
        if len(seasons) == 1 and len(won):
            # One season: name who the champion beat and the series score.
            final = won.iloc[-1]
            row["finals_opponent"] = final["opponent_team_name"]
            row["finals_score"] = f"{int(final['wins'])}-{int(final['losses'])}"
        rows.append(row)
    board = pd.DataFrame(rows)
    if board.empty or not (board["titles"] > 0).any():
        return NoResult(
            query_class="leaderboard",
            reason="no_match",
            notes=["No completed Finals found in the specified span"],
        )
    board = board[board["titles"] > 0]
    ranked = board.sort_values(
        by=["titles", "finals_appearances", "team_name"], ascending=[False, True, True]
    )
    if len(ranked) > limit:
        # Never cut a tie: every team level with the last one kept stays.
        cutoff = ranked["titles"].iloc[limit - 1]
        ranked = ranked[ranked["titles"] >= cutoff]
    result = ranked.reset_index(drop=True)
    result.insert(0, "rank", range(1, len(result) + 1))
    caveats.append("titles are Finals series won")
    if season_to_int(seasons[0]) < DATA_START_YEAR:
        caveats.append("playoff data starts in 1996-97; earlier seasons are not counted")
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")
    else:
        result["season"] = seasons[0]
    return LeaderboardResult(
        leaders=result,
        current_through=compute_current_through_for_seasons(seasons, "Playoffs"),
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: record leaderboard by decade
# ---------------------------------------------------------------------------


def build_record_by_decade_leaderboard_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    stat: str = "wins",
    limit: int = 10,
    ascending: bool = False,
    playoff_round: str | None = None,
) -> LeaderboardResult | NoResult:
    """Rank teams by record stats grouped by decade.

    E.g., "most wins by decade since 1980".
    Returns a leaderboard with one row per team-decade combination.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = (
            _load_playoff_games(seasons)
            if season_type == "Playoffs"
            else load_team_games_for_seasons(seasons, season_type)
        )
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    if season_type == "Playoffs":
        df = _add_round_column(df)
        if playoff_round:
            df = df[df["playoff_round_code"] == playoff_round].copy()

    df = _add_decade_column(df)

    if df.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    caveats: list[str] = []
    if season_type == "Playoffs":
        caveat = _round_data_caveat(seasons)
        if caveat:
            caveats.append(caveat)

    # Aggregate per team per decade
    if "wl" in df.columns:
        df["_is_win"] = (df["wl"] == "W").astype(int)

    agg = df.groupby(["team_abbr", "team_name", "decade"], as_index=False).agg(
        games_played=("game_id", "nunique"),
        wins=("_is_win", "sum"),
    )
    agg["losses"] = agg["games_played"] - agg["wins"]
    agg["win_pct"] = (agg["wins"] / agg["games_played"]).round(3)

    # Sort by target stat within each decade
    target_col = stat if stat in ("wins", "losses", "win_pct") else "wins"
    result = agg[
        ["team_name", "team_abbr", "decade", "games_played", "wins", "losses", "win_pct"]
    ].sort_values(
        by=["decade", target_col, "games_played", "team_name"],
        ascending=[True, ascending, False, True],
    )

    # Take top N per decade
    top_results = []
    for decade, group in result.groupby("decade"):
        top_n = group.head(limit).copy()
        top_n.insert(0, "rank", range(1, len(top_n) + 1))
        top_results.append(top_n)

    if not top_results:
        return NoResult(query_class="leaderboard", reason="no_match")

    leaders = pd.concat(top_results, ignore_index=True)
    leaders["season_type"] = season_type
    if len(seasons) > 1:
        leaders["seasons"] = f"{seasons[0]} to {seasons[-1]}"

    caveats.append(f"record by decade leaderboard ({target_col})")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")
    if playoff_round:
        caveats.append(f"filtered to {round_code_to_label(playoff_round)}")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return LeaderboardResult(
        leaders=leaders,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: playoff matchup history (team vs team in playoffs)
# ---------------------------------------------------------------------------


def build_playoff_matchup_history_result(
    *,
    team_a: str,
    team_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    by_round: bool = False,
) -> ComparisonResult | NoResult:
    """Build playoff matchup history between two teams.

    Shows playoff record of team_a vs team_b, optionally filtered by
    round or broken down by round.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = _load_playoff_games(seasons)
    except FileNotFoundError:
        return NoResult(query_class="comparison", reason="no_data")

    a_upper, b_upper = team_a.upper(), team_b.upper()

    # Team A games vs Team B in playoffs
    a_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["team_name"].astype(str).str.upper().eq(a_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(b_upper)
        )
    ].copy()

    b_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["team_name"].astype(str).str.upper().eq(b_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(a_upper)
        )
    ].copy()

    if a_df.empty and b_df.empty:
        return NoResult(query_class="comparison", reason="no_match")

    a_df = _add_round_column(a_df)
    b_df = _add_round_column(b_df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)

    if playoff_round:
        a_df = a_df[a_df["playoff_round_code"] == playoff_round].copy()
        b_df = b_df[b_df["playoff_round_code"] == playoff_round].copy()
        if a_df.empty and b_df.empty:
            return NoResult(query_class="comparison", reason="no_match")

    rec_a = _compute_record(a_df)
    rec_b = _compute_record(b_df)

    team_a_name = (
        a_df["team_name"].mode().iloc[0]
        if not a_df.empty and "team_name" in a_df.columns
        else team_a
    )
    team_b_name = (
        b_df["team_name"].mode().iloc[0]
        if not b_df.empty and "team_name" in b_df.columns
        else team_b
    )

    summary = pd.DataFrame(
        [
            {"team_name": team_a_name, **rec_a},
            {"team_name": team_b_name, **rec_b},
        ]
    )

    # Build comparison breakdown
    if by_round:
        # By-round breakdown
        all_rounds = sorted(
            set(a_df["playoff_round_code"].unique()) | set(b_df["playoff_round_code"].unique())
        )
        comparison_rows = []
        for rc in all_rounds:
            if rc not in ROUND_CODES:
                continue
            a_round = a_df[a_df["playoff_round_code"] == rc]
            b_round = b_df[b_df["playoff_round_code"] == rc]
            ra = _compute_record(a_round)
            rb = _compute_record(b_round)
            comparison_rows.append(
                {
                    "round": round_code_to_label(rc),
                    f"{team_a.upper()}_wins": ra["wins"],
                    f"{team_a.upper()}_losses": ra["losses"],
                    f"{team_b.upper()}_wins": rb["wins"],
                    f"{team_b.upper()}_losses": rb["losses"],
                }
            )
        comparison = pd.DataFrame(comparison_rows) if comparison_rows else pd.DataFrame()
        caveats.append(f"playoff matchup history by round: {team_a.upper()} vs {team_b.upper()}")
    else:
        # By-season breakdown
        all_seasons = sorted(set(a_df["season"].unique()) | set(b_df["season"].unique()))
        comparison_rows = []
        for szn in all_seasons:
            a_szn = a_df[a_df["season"] == szn]
            b_szn = b_df[b_df["season"] == szn]
            ra = _compute_record(a_szn)
            rb = _compute_record(b_szn)
            # Determine round played
            round_label = "Unknown"
            rounds_played = set()
            for rdf in [a_szn, b_szn]:
                if not rdf.empty and "playoff_round_code" in rdf.columns:
                    rounds_played.update(rdf["playoff_round_code"].unique())
            valid_rounds = [r for r in rounds_played if r in ROUND_CODES]
            if valid_rounds:
                round_label = round_code_to_label(max(valid_rounds))

            comparison_rows.append(
                {
                    "season": szn,
                    "round": round_label,
                    f"{team_a.upper()}_wins": ra["wins"],
                    f"{team_a.upper()}_losses": ra["losses"],
                    f"{team_b.upper()}_wins": rb["wins"],
                    f"{team_b.upper()}_losses": rb["losses"],
                }
            )
        comparison = pd.DataFrame(comparison_rows) if comparison_rows else pd.DataFrame()
        caveats.append(f"playoff matchup history: {team_a.upper()} vs {team_b.upper()}")

    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    return ComparisonResult(
        summary=summary,
        comparison=comparison,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: playoff round record leaderboard
# ---------------------------------------------------------------------------


def build_playoff_round_record_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    stat: str = "win_pct",
    limit: int = 10,
    ascending: bool = False,
    series_situation: str | None = None,
) -> LeaderboardResult | NoResult:
    """Rank teams by playoff record in a specific round or series situation.

    E.g., "best finals record since 1980", "most conference finals wins".
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = _load_playoff_games(seasons)
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    df = _add_round_column(df)
    df = apply_series_situation_filter(df, seasons, series_situation)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)
    if series_situation:
        caveats.append(f"playoff series situation: {series_situation_label(series_situation)}")

    round_label = "Playoffs"
    if playoff_round:
        round_label = round_code_to_label(playoff_round)
        df = df[df["playoff_round_code"] == playoff_round].copy()
        if df.empty:
            return NoResult(
                query_class="leaderboard",
                reason="no_match",
                notes=[f"No {round_label} games found in the specified span"],
            )

    if "wl" in df.columns:
        df["_is_win"] = (df["wl"] == "W").astype(int)

    agg = df.groupby(["team_id", "team_name", "team_abbr"], as_index=False).agg(
        games_played=("game_id", "nunique"),
        wins=("_is_win", "sum"),
    )
    agg["losses"] = agg["games_played"] - agg["wins"]
    agg["win_pct"] = (agg["wins"] / agg["games_played"]).round(3)

    target_col = stat if stat in ("wins", "losses", "win_pct", "games_played") else "win_pct"

    # Minimum games guardrail. Series situations are rare (a team plays a
    # handful of game 7s a decade): counts need no floor, rates over a span
    # of seasons need three.
    if series_situation:
        min_games = 3 if target_col == "win_pct" and len(seasons) > 1 else 1
    else:
        min_games = max(1, len(seasons) // 5)
    agg = agg[agg["games_played"] >= min_games].copy()
    if series_situation and min_games > 1:
        caveats.append(f"teams with at least {min_games} such games")

    if agg.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    result = (
        agg[["team_name", "team_abbr", "team_id", "games_played", "wins", "losses", "win_pct"]]
        .sort_values(
            by=[target_col, "games_played", "team_name"],
            ascending=[ascending, False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )

    result.insert(0, "rank", range(1, len(result) + 1))
    result["round"] = round_label
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        result["season"] = seasons[0]
    result["season_type"] = "Playoffs"

    caveats.append(f"{round_label} record leaderboard ({target_col})")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
        caveats=caveats,
    )
