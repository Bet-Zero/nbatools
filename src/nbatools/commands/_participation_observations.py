"""Whole-game participation from qualified game-day observations, never omission."""

from __future__ import annotations

import re

import pandas as pd

from nbatools.commands._player_identity import player_name_mask
from nbatools.commands.entity_resolution import player_ids_for_name
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
                    r"nba_official_finalbox:[0-9]{8}_[A-Z]{4,6}"
                )
                & rows.source_sha256.astype(str).str.fullmatch(r"[0-9a-f]{64}")
            ).all():
                raise ValueError(
                    "Player-game participation lacks retained official report evidence"
                )
            return rows

        key = ("player_game_availability", data_source_cache_key(), season_type, season)
        frames.append(FRAME_CACHE.get_or_load(key, load))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_REQUIRED)


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
) -> pd.DataFrame:
    """Select positive participation with qualified same-game side ownership."""
    return _filter_observed(
        candidates,
        names,
        seasons,
        season_type,
        opponent_context=opponent_context,
        state="played",
    )


def _filter_observed(
    candidates: pd.DataFrame,
    names: str,
    seasons: list[str],
    season_type: str,
    *,
    opponent_context: bool,
    state: str,
) -> pd.DataFrame:
    """Require every named predicate to be known across the original sample."""
    if candidates.empty:
        return candidates.copy()
    team_column = "team_id"
    if not {"game_id", team_column, "game_date"}.issubset(candidates.columns):
        raise ValueError("Participation requires game, date and explicit team identity")
    observations = load_observations(seasons, season_type)
    # Positive played rows establish play, and disprove an absence predicate.
    # They never establish
    # absence, health or membership in a game where that player is omitted.
    from nbatools.commands.data_utils import load_player_games_for_seasons

    try:
        appearances = load_player_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        appearances = pd.DataFrame()
    if {"game_id", "team_id", "player_id", "player_name", "game_date", "minutes"}.issubset(
        appearances.columns
    ):
        played = appearances.loc[pd.to_numeric(appearances.minutes, errors="coerce").gt(0)].copy()
        for col in _KEYS:
            played[col] = _ids(played[col])
        played["participation_state"] = "played"
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
    games, teams = _ids(candidates.game_id), _ids(candidates[team_column])
    dates = pd.to_datetime(candidates.game_date, errors="raise").dt.date
    keep = pd.Series(True, index=candidates.index)
    for name in re.split(r"\s+and\s+", names.strip(), flags=re.IGNORECASE):
        matching = observations.loc[player_name_mask(observations, name)]
        ids = set(matching.player_id) | {
            int(value) for value in player_ids_for_name(name) if str(value).isdigit()
        }
        available_ids = set(observations.loc[observations.player_id.isin(ids), "player_id"])
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
            if (game, team_id) not in lookup.index:
                # Positive same-game membership on the opposing team proves
                # this is not a same-team absence. Omission alone proves nothing.
                if (
                    not opponent_context
                    and other_team != team_id
                    and (game, other_team) in lookup.index
                ):
                    other = lookup.loc[(game, other_team)]
                    if pd.Timestamp(other.game_date).date() == date:
                        states.append(False)
                        continue
                raise ValueError(f"Incomplete game-day participation coverage for {name}")
            row = lookup.loc[(game, team_id)]
            if pd.Timestamp(row.game_date).date() != date or row.participation_state == "unknown":
                raise ValueError(f"Unqualified game-day participation for {name}")
            states.append(row.participation_state == state)
        keep &= pd.Series(states, index=candidates.index)
    return candidates.loc[keep].copy()
