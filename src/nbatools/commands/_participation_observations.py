"""Whole-game participation from qualified game-day observations, never omission."""

from __future__ import annotations

import re
from dataclasses import replace

import pandas as pd

from nbatools.commands._player_identity import player_name_key, player_name_mask
from nbatools.commands.entity_resolution import ResolutionResult, player_ids_for_name
from nbatools.data_source import data_exists, data_read_csv, data_source_cache_key
from nbatools.dataframe_cache import FRAME_CACHE

_KEYS = ["game_id", "team_id", "player_id"]
_REQUIRED = [
    *_KEYS,
    "game_date",
    "season",
    "season_type",
    "player_name",
    "participation_state",
    "coverage_scope",
    "source",
    "source_sha256",
]


def _ids(values: pd.Series) -> pd.Series:
    numbers = pd.to_numeric(values, errors="coerce")
    if numbers.isna().any() or (numbers <= 0).any() or (numbers % 1 != 0).any():
        raise ValueError("Invalid identity in player-game participation evidence")
    return numbers.astype("int64")


def load_observations(seasons: list[str], season_type: str) -> pd.DataFrame:
    frames = []
    for season in seasons:

        def load(season=season):
            safe = season_type.lower().replace(" ", "_")
            path = f"data/raw/player_game_availability/{season}_{safe}.csv"
            if not data_exists(path):
                return pd.DataFrame(columns=_REQUIRED)
            rows = data_read_csv(path)
            if not set(_REQUIRED).issubset(rows.columns):
                raise ValueError("Incomplete player-game participation evidence schema")
            rows = rows.copy()
            for col in _KEYS:
                rows[col] = _ids(rows[col])
            if rows.duplicated(["game_id", "player_id"]).any():
                raise ValueError("Duplicate player-game participation observations")
            if not (rows.season.eq(season) & rows.season_type.eq(season_type)).all():
                raise ValueError("Player-game participation scope mismatch")
            if not rows.participation_state.isin(["played", "did_not_play", "unknown"]).all():
                raise ValueError("Invalid player-game participation state")
            if not (
                rows.coverage_scope.eq("listed_player_rows_only")
                & rows.source.astype(str).str.fullmatch(
                    r"(?:nba_official_finalbox:[0-9]{8}_[A-Z]{4,6}|nba_stats_structured_archive:[a-f0-9]{40}:[0-9]{10})"
                )
                & rows.source_sha256.astype(str).str.fullmatch(r"[0-9a-f]{64}")
            ).all():
                raise ValueError(
                    "Player-game participation lacks retained qualified source evidence"
                )
            return rows

        key = ("player_game_availability", data_source_cache_key(), season_type, season)
        frames.append(FRAME_CACHE.get_or_load(key, load))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_REQUIRED)


def resolve_observed_name(phrase: str, seasons: list[str], season_type: str) -> ResolutionResult:
    """Recognize an exact listed full name only for a participation condition.

    An inactive player may have no appearance rows. Recognizing that identity
    proves neither their state nor their team in another game; execution still
    requires qualified observations for every candidate. Never extend the global
    primary-player index or guess an inactive player's surname/first name.
    """
    key = player_name_key(phrase)
    if len(key.split()) < 2:
        return ResolutionResult()
    try:
        rows = load_observations(seasons, season_type)
    except (ValueError, FileNotFoundError):
        # Interpretation happens before the execution error boundary. An
        # unqualified ledger must remain unresolved, not escape as an exception
        # or fall back to a different player sharing a surname.
        return ResolutionResult(confidence="ambiguous", source="participation_unavailable")
    matched = rows.loc[player_name_mask(rows, phrase)]
    if matched.empty:
        return ResolutionResult()
    names = sorted(set(matched.player_name.astype(str)))
    ids = set(matched.player_id.astype(str)) | set(player_ids_for_name(phrase))
    if len(ids) != 1:
        return ResolutionResult(candidates=names, confidence="ambiguous", source="participation")
    return ResolutionResult(
        resolved=names[0], candidates=names, confidence="confident", source="participation"
    )


def filter_absent(
    candidates: pd.DataFrame,
    names: str,
    seasons: list[str],
    season_type: str,
    *,
    opponent_context: bool = False,
) -> pd.DataFrame:
    """Select explicit nonparticipation across the complete requested sample."""
    return _filter_observed(
        candidates,
        names,
        seasons,
        season_type,
        opponent_context=opponent_context,
        state="did_not_play",
    )


def filter_played(
    candidates: pd.DataFrame,
    names: str,
    seasons: list[str],
    season_type: str,
    *,
    opponent_context: bool = False,
    allow_appearance_omission: bool = False,
) -> pd.DataFrame:
    """Select positive participation with qualified same-game side ownership."""
    return _filter_observed(
        candidates,
        names,
        seasons,
        season_type,
        opponent_context=opponent_context,
        state="played",
        allow_appearance_omission=allow_appearance_omission,
    )


def combined_observations(seasons: list[str], season_type: str) -> tuple[pd.DataFrame, set[int]]:
    """Join qualified listed evidence with canonical positive appearances."""
    observations = load_observations(seasons, season_type)
    # Positive played rows establish play, and disprove an absence predicate.
    # They never establish
    # absence, health or membership in a game where that player is omitted.
    from nbatools.commands.data_utils import load_player_games_for_seasons

    try:
        appearances = load_player_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        appearances = pd.DataFrame()
    appearance_ids = set()
    if {"game_id", "team_id", "player_id", "player_name", "game_date", "minutes"}.issubset(
        appearances.columns
    ):
        played = appearances.loc[pd.to_numeric(appearances.minutes, errors="coerce").gt(0)].copy()
        for col in _KEYS:
            played[col] = _ids(played[col])
        played["participation_state"] = "played"
        appearance_ids = set(played.player_id)
        if played.duplicated(["game_id", "player_id"]).any():
            raise ValueError("Duplicate positive participation observations")
        shared = observations.merge(played, on=["game_id", "player_id"], suffixes=("", "_played"))
        if (
            not shared.empty
            and not (
                shared.participation_state.eq("played")
                & shared.team_id.eq(shared.team_id_played)
                & pd.to_datetime(shared.game_date).eq(pd.to_datetime(shared.game_date_played))
            ).all()
        ):
            raise ValueError("Contradictory positive and report participation observations")
        known = set(zip(observations.game_id, observations.player_id))
        extra = played.loc[[key not in known for key in zip(played.game_id, played.player_id)]]
        observations = pd.concat([observations, extra], ignore_index=True)
    return observations, appearance_ids


def _filter_observed(
    candidates: pd.DataFrame,
    names: str,
    seasons: list[str],
    season_type: str,
    *,
    opponent_context: bool,
    state: str,
    allow_appearance_omission: bool = False,
) -> pd.DataFrame:
    """Require every named predicate to be known across the original sample."""
    if candidates.empty:
        return candidates.copy()
    team_column = "team_id"
    if not {"game_id", team_column, "game_date"}.issubset(candidates.columns):
        raise ValueError("Participation requires game, date and explicit team identity")
    from nbatools.commands._dated_membership import load_membership

    observations, appearance_ids = combined_observations(seasons, season_type)
    intervals = load_membership(seasons)
    games, teams = _ids(candidates.game_id), _ids(candidates[team_column])
    dates = pd.to_datetime(candidates.game_date, errors="raise").dt.date
    keep = pd.Series(True, index=candidates.index)
    for name in re.split(r"\s+and\s+", names.strip(), flags=re.IGNORECASE):
        matching = pd.concat([observations, intervals], ignore_index=True)
        matching = matching.loc[player_name_mask(matching, name)]
        ids = set(matching.player_id) | {
            int(value) for value in player_ids_for_name(name) if str(value).isdigit()
        }
        available_ids = ids & (set(intervals.player_id) | set(observations.player_id))
        if len(available_ids) != 1:
            raise ValueError(f"Unavailable or ambiguous participation identity for {name}")
        player_id = available_ids.pop()
        rows = observations.loc[observations.player_id.eq(player_id)]
        lookup = rows.set_index(["game_id", "team_id"])
        predicate_teams = teams
        if opponent_context:
            if "opponent_team_id" not in candidates:
                raise ValueError("Opposing participation requires explicit opponent identity")
            opposing = _ids(candidates.opponent_team_id)
            on_own = any((g, t) in lookup.index for g, t in zip(games, teams))
            on_opponent = any((g, t) in lookup.index for g, t in zip(games, opposing))
            if not intervals.empty:
                from nbatools.commands._dated_membership import membership_on_date

                memberships = [
                    membership_on_date(intervals, player_id, day).team_id for day in dates
                ]
                on_own |= any(m == t for m, t in zip(memberships, teams))
                on_opponent |= any(m == t for m, t in zip(memberships, opposing))
            if on_own and on_opponent:
                raise ValueError(f"Ambiguous team ownership for {name}'s participation")
            if on_opponent:
                predicate_teams = opposing
        states = []
        opponent_ids = (
            _ids(candidates.opponent_team_id).tolist()
            if "opponent_team_id" in candidates
            else [None] * len(candidates)
        )
        for game, team_id, date, other_team in zip(games, predicate_teams, dates, opponent_ids):
            status, _ = game_participation(
                rows,
                intervals,
                player_id,
                int(game),
                int(team_id),
                date,
                other_team=other_team if not opponent_context else None,
            )
            if status == "unknown":
                if (
                    state == "played"
                    and allow_appearance_omission
                    and player_id in appearance_ids
                    and not rows.game_id.eq(game).any()
                ):
                    states.append(False)
                    continue
                qualifier = "Unqualified" if rows.game_id.eq(game).any() else "Incomplete"
                raise ValueError(f"{qualifier} game-day participation coverage for {name}")
            states.append(status == state)
        keep &= pd.Series(states, index=candidates.index)
    return candidates.loc[keep].copy()


def game_participation(
    observations: pd.DataFrame,
    intervals: pd.DataFrame,
    player_id: int,
    game_id: int,
    team_id: int,
    day,
    *,
    other_team: int | None = None,
):
    """Four-state game classifier shared by filters, coverage and API consumers."""
    from nbatools.commands._dated_membership import membership_on_date

    exact = observations.loc[
        observations.player_id.eq(player_id) & observations.game_id.eq(game_id)
    ]
    if len(exact) > 1:
        raise ValueError("Duplicate exact-game membership evidence")
    row = exact.iloc[0] if len(exact) else None
    exact_team = None
    if row is not None:
        if pd.Timestamp(row.game_date).date() != day:
            raise ValueError("Unqualified game-day participation date")
        if row.participation_state in {"played", "did_not_play"}:
            if int(row.team_id) not in {team_id, other_team}:
                raise ValueError("Exact-game membership outside the requested game sides")
            exact_team = int(row.team_id)
    membership = membership_on_date(intervals, player_id, day, team_id, exact_team_id=exact_team)
    if exact_team is not None and row is not None:
        digest = row.get("source_sha256")
        if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
            membership = replace(
                membership,
                source_hashes=tuple(sorted(set(membership.source_hashes) | {digest})),
            )
    if membership.state == "not_member":
        return "not_member", membership
    if row is not None and exact_team == team_id:
        return row.participation_state, membership
    return "unknown", membership


def qualified_report_observation(
    candidate: pd.Series, player: str, seasons: list[str], season_type: str
) -> pd.Series:
    """One retained report identity on the selected original game and actual side."""
    rows = load_observations(seasons, season_type)
    matching = rows.loc[player_name_mask(rows, player)]
    ids = set(matching.player_id) | {
        int(value) for value in player_ids_for_name(player) if str(value).isdigit()
    }
    rows = rows.loc[rows.player_id.isin(ids)]
    if rows.player_id.nunique() != 1:
        raise ValueError(f"Unavailable or ambiguous precise minutes identity for {player}")
    rows = rows.loc[
        rows.game_id.eq(int(candidate.game_id))
        & rows.team_id.isin([int(candidate.team_id), int(candidate.opponent_team_id)])
        & pd.to_datetime(rows.game_date).dt.date.eq(pd.Timestamp(candidate.game_date).date())
    ]
    if len(rows) != 1:
        raise ValueError(f"No qualified precise report time for {player} on the original game")
    return rows.iloc[0]


def qualified_report_seconds(
    candidate: pd.Series, player: str, seasons: list[str], season_type: str, *, played: bool
) -> int | None:
    """Exact report time AFTER protected participation qualification on this game.

    Positive appearance minutes can qualify play, but cannot substitute for
    precise report time. Resolve the actual side from this game's observation.
    """
    import math

    row = qualified_report_observation(candidate, player, seasons, season_type)
    if row.participation_state != ("played" if played else "did_not_play"):
        raise ValueError(f"Conflicting report participation state for {player}")
    raw_minutes = row.get("source_minutes")
    if not played:
        if raw_minutes is None or pd.isna(raw_minutes) or str(raw_minutes).strip() == "":
            return None
        try:
            value = float(raw_minutes)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unqualified DNP report time for {player}") from exc
        if not math.isfinite(value) or value != 0:
            raise ValueError(f"DNP conflicts with report time for {player}")
        return None
    if not re.fullmatch(r"nba_official_finalbox:[0-9]{8}_[A-Z]{4,6}", str(row.get("source", ""))):
        # Positive structured participation does not certify original-scorer
        # MM:SS precision. Explicit DNP above needs no clock to prove No.
        raise ValueError(f"No qualified precise report time for {player} on the original game")
    try:
        minutes = float(raw_minutes)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"No qualified precise report time for {player} on the original game"
        ) from exc
    if row.participation_state != "played" or not math.isfinite(minutes) or minutes <= 0:
        raise ValueError(f"No qualified positive report time for {player} on the original game")
    seconds = minutes * 60
    if round(seconds) <= 0 or not math.isclose(seconds, round(seconds), rel_tol=0.0, abs_tol=1e-8):
        raise ValueError(f"Report time for {player} does not have qualified whole-second precision")
    return round(seconds)
