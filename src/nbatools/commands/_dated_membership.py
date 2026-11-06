"""Qualified finite NBA membership intervals; omission never establishes tenure."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

from nbatools.data_source import data_exists, data_path, data_read_csv, data_source_cache_key
from nbatools.dataframe_cache import FRAME_CACHE

COLUMNS = [
    "season",
    "player_id",
    "player_name",
    "team_id",
    "start_date",
    "end_date",
    "membership_state",
    "coverage_scope",
    "source",
    "source_sha256",
]


def calendar_date(value: str) -> date:
    """Accept an unambiguous calendar date, without silently dropping a clock."""
    if not isinstance(value, str):
        raise ValueError("Membership requires an ISO calendar date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Membership requires an ISO calendar date") from exc
    if parsed.isoformat() != value:
        raise ValueError("Membership requires an ISO calendar date")
    return parsed


def validate_intervals(rows: pd.DataFrame, season: str) -> pd.DataFrame:
    """Validate a qualified data contract, not certify the underlying NBA facts.

    A positive row must independently certify exclusive NBA team membership
    throughout BOTH inclusive boundaries. A negative row certifies only the
    named team. Acquisition/qualification retains original sources separately.
    No first/last appearance or snapshot can create one of these intervals.
    """
    from nbatools.commands._participation_observations import _ids

    if not set(COLUMNS) <= set(rows):
        raise ValueError("Incomplete dated membership evidence schema")
    rows = rows.copy()
    for col in ("team_id", "player_id"):
        if rows[col].map(pd.api.types.is_bool).any():
            raise ValueError("Boolean identity in dated membership evidence")
        rows[col] = _ids(rows[col])
    if not rows.season.eq(season).all():
        raise ValueError("Dated membership season mismatch")
    for col in ("start_date", "end_date"):
        rows[col] = rows[col].map(calendar_date)
    if (rows.start_date > rows.end_date).any():
        raise ValueError("Reversed dated membership boundaries")
    if not (
        rows.membership_state.isin(["member", "not_member"])
        & rows.coverage_scope.eq("explicit_dated_nba_membership")
        & rows.player_name.fillna("").astype(str).str.strip().ne("")
        & rows.source.fillna("").astype(str).str.fullmatch(r"https://(?:www\.)?nba\.com/[^\s]+")
        & rows.source_sha256.fillna("").astype(str).str.fullmatch(r"[0-9a-f]{64}")
    ).all():
        raise ValueError("Unqualified dated membership evidence")
    if rows.duplicated(COLUMNS[:7]).any():
        raise ValueError("Duplicate dated membership evidence")
    # Contradictory positive clubs or positive/negative facts invalidate a
    # ledger, including an overlap only on an inclusive boundary day.
    for _, group in rows.groupby("player_id"):
        records = list(group.itertuples())
        for i, a in enumerate(records):
            for b in records[i + 1 :]:
                if a.start_date > b.end_date or b.start_date > a.end_date:
                    continue
                positives = a.membership_state == b.membership_state == "member"
                opposed = a.membership_state != b.membership_state
                if (positives and a.team_id != b.team_id) or (opposed and a.team_id == b.team_id):
                    raise ValueError("Contradictory dated membership evidence")
    return rows


def load_membership(seasons: list[str]) -> pd.DataFrame:
    frames = []
    for season in seasons:
        if (
            not isinstance(season, str)
            or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", season)
            or int(season[-2:]) != (int(season[:4]) + 1) % 100
        ):
            raise ValueError("Invalid membership season")

        def load(season=season):
            path = f"data/raw/player_team_membership/{season}.csv"
            if not data_exists(path):
                return pd.DataFrame(columns=COLUMNS)
            rows = validate_intervals(data_read_csv(path), season)
            for digest in set(rows.source_sha256):
                source = data_path(f"data/raw/player_team_membership_sources/{digest}.source")
                if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                    raise ValueError("Dated membership original source hash mismatch")
            return rows

        frames.append(
            FRAME_CACHE.get_or_load(("dated_membership", data_source_cache_key(), season), load)
        )
    # The resolver checks active facts across all selected seasons together.
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    rows = pd.concat(frames, ignore_index=True)
    return rows


@dataclass(frozen=True)
class Membership:
    state: str
    team_id: int | None = None
    basis: str = "insufficient_evidence"
    source_hashes: tuple[str, ...] = ()


def membership_on_date(
    intervals: pd.DataFrame,
    player_id: int,
    day: date,
    team_id: int | None = None,
    *,
    exact_team_id: int | None = None,
) -> Membership:
    """Combine dated facts and (optionally) one qualified EXACT-game association.

    ``exact_team_id`` must come from the requested game's positive appearance
    or explicit listed observation. Another game on this date is not a caller
    substitute. This function never derives participation from membership.
    """
    rows = intervals.loc[
        intervals.player_id.eq(player_id)
        & intervals.start_date.le(day)
        & intervals.end_date.ge(day)
    ]
    members = set(rows.loc[rows.membership_state.eq("member"), "team_id"])
    negatives = set(rows.loc[rows.membership_state.eq("not_member"), "team_id"])
    if exact_team_id is not None:
        members.add(exact_team_id)
    if len(members) > 1 or members & negatives:
        raise ValueError("Contradictory dated and exact-game membership evidence")
    known_team = next(iter(members), None)
    hashes = tuple(sorted(set(rows.source_sha256.astype(str))))
    basis = "exact_game" if exact_team_id is not None else "explicit_dated_interval"
    if known_team is not None:
        return Membership(
            "member" if team_id is None or team_id == known_team else "not_member",
            int(known_team),
            basis,
            hashes,
        )
    if team_id in negatives:
        return Membership("not_member", None, basis, hashes)
    return Membership("unknown")
