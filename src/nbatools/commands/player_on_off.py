"""Coverage-gated route for player on/off queries."""

from __future__ import annotations

import unicodedata

import pandas as pd

from nbatools.commands._parse_helpers import build_on_off_note
from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_player_on_off_summary_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import NoResult, SummaryResult

RESULT_COLUMNS = [
    "season",
    "season_type",
    "player_name",
    "team_abbr",
    "team_name",
    "presence_state",
    "gp",
    "minutes",
    "plus_minus",
    "off_rating",
    "def_rating",
    "net_rating",
]


def _normalize_name(value: object) -> str:
    text = str(value or "").strip().casefold()
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _unsupported(lineup_members: list[str] | None, presence_state: str | None) -> NoResult:
    notes: list[str] = []
    if on_off_note := build_on_off_note(
        lineup_members=lineup_members,
        presence_state=presence_state,
    ):
        notes.append(on_off_note)
    return NoResult(query_class="summary", reason="unsupported", notes=notes)


def _coverage_unavailable(reason: str) -> NoResult:
    return NoResult(
        query_class="summary",
        reason="unsupported",
        notes=[f"on_off: trustworthy on/off coverage is unavailable ({reason})"],
    )


def _filter_player(df: pd.DataFrame, player: str) -> pd.DataFrame:
    target = _normalize_name(player)
    work = df.copy()
    names = work["player_name"].map(_normalize_name)
    return work.loc[names.eq(target)].copy()


def _filter_team(df: pd.DataFrame, team: str | None) -> pd.DataFrame:
    if not team:
        return df.copy()
    target = str(team).strip().upper()
    work = df.copy()
    return work.loc[
        work["team_abbr"].astype(str).str.upper().eq(target)
        | work["team_name"].astype(str).str.upper().eq(target)
    ].copy()


def _filter_presence_state(df: pd.DataFrame, presence_state: str) -> pd.DataFrame:
    state = presence_state.strip().lower()
    if state == "both":
        return df.copy()
    if state in {"on", "off"}:
        return df.loc[df["presence_state"].astype(str).str.lower().eq(state)].copy()
    raise ValueError(f"Unsupported presence_state: {presence_state}")


def build_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    player: str | None = None,
    team: str | None = None,
    lineup_members: list[str] | None = None,
    presence_state: str | None = None,
    **_: object,
) -> SummaryResult | NoResult:
    """Return trusted on/off splits when source coverage exists."""
    if not lineup_members or presence_state is None:
        raise ValueError("player_on_off requires lineup_members and presence_state")
    if len(lineup_members) != 1:
        return _coverage_unavailable("multi-player on/off is outside the current source contract")

    queried_player = player or lineup_members[0]
    seasons = resolve_seasons(season, start_season, end_season)
    current_through = compute_current_through_for_seasons(seasons, season_type)

    try:
        df = load_team_player_on_off_summary_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return _unsupported(lineup_members, presence_state)

    df = _filter_player(df, queried_player)
    df = _filter_team(df, team)
    if df.empty:
        return NoResult(
            query_class="summary",
            reason="no_match",
            current_through=current_through,
        )

    trusted = pd.to_numeric(df["coverage_trusted"], errors="coerce").fillna(0).eq(1)
    df = df.loc[trusted].copy()
    if df.empty:
        return _coverage_unavailable("trusted on/off rows are missing for the requested slice")

    df = _filter_presence_state(df, presence_state)
    if df.empty:
        return _coverage_unavailable(
            f"presence_state={presence_state!r} is missing for the requested slice"
        )

    for col in ("gp", "minutes", "plus_minus", "off_rating", "def_rating", "net_rating"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    summary = df[RESULT_COLUMNS].sort_values(
        ["season", "team_abbr", "player_name", "presence_state"]
    )

    return SummaryResult(
        summary=summary.reset_index(drop=True),
        current_through=current_through,
    )
