"""Select a player's dated club games without deriving absence from omission."""

from __future__ import annotations

import pandas as pd

from nbatools.commands._dated_membership import load_membership, membership_on_date
from nbatools.commands._participation_observations import combined_observations, game_participation
from nbatools.commands._player_identity import player_name_mask
from nbatools.commands.entity_resolution import player_ids_for_name


def missed_membership_games(candidates, player, seasons, season_type, *, team_scoped=False):
    """Return verified DNP rows and an auditable population; unknowns withhold totals.

    For a club-independent question, require a qualified club on every selected
    candidate-club game date. Otherwise an unobserved club could be silently omitted.
    Exact-game observations qualify participation, never intervening tenure.
    """
    if not isinstance(player, str) or not player.strip():
        raise ValueError("Membership missed-game scope requires a player name")
    observations, _ = combined_observations(seasons, season_type)
    intervals = load_membership(seasons)
    identities = pd.concat([observations, intervals], ignore_index=True)
    identities = identities.loc[player_name_mask(identities, player)]
    ids = set(identities.player_id) | {
        int(value) for value in player_ids_for_name(player) if str(value).isdigit()
    }
    if len(ids) != 1:
        raise ValueError(f"Unavailable or ambiguous participation identity for {player}")
    pid = ids.pop()
    observations = observations.loc[observations.player_id.eq(pid)]
    intervals = intervals.loc[intervals.player_id.eq(pid)]
    clubs = set(observations.team_id) | set(
        intervals.loc[intervals.membership_state.eq("member"), "team_id"]
    )
    population = candidates.loc[candidates.team_id.isin(clubs)].copy()
    unknown_dates = []
    if not team_scoped:
        for day in sorted(set(pd.to_datetime(population.game_date).dt.date)):
            if membership_on_date(intervals, pid, day).state == "unknown":
                unknown_dates.append(day.isoformat())
    audit, selected = [], []
    for index, row in population.iterrows():
        state, membership = game_participation(
            observations,
            intervals,
            pid,
            int(row.game_id),
            int(row.team_id),
            pd.Timestamp(row.game_date).date(),
            other_team=int(row.opponent_team_id),
        )
        audit.append(
            dict(
                season=str(row.season),
                game_id=int(row.game_id),
                game_date=pd.Timestamp(row.game_date).date().isoformat(),
                team_id=int(row.team_id),
                team_abbr=str(row.team_abbr),
                membership_state=membership.state,
                participation_state=state,
            )
        )
        if state == "did_not_play":
            selected.append(index)
    by_team = []
    for (season, club), rows in population.groupby(["season", "team_abbr"], sort=True):
        facts = [r for r in audit if r["season"] == season and r["team_abbr"] == club]
        counts = {
            state: sum(r["participation_state"] == state for r in facts)
            for state in ("played", "did_not_play", "not_member", "unknown")
        }
        by_team.append(
            dict(
                season=str(season),
                team_abbr=str(club),
                team_name=str(rows.team_name.iloc[0]) if "team_name" in rows else str(club),
                candidate_games=len(rows),
                eligible_games=sum(r["membership_state"] == "member" for r in facts),
                **counts,
            )
        )
    unknown = any(r["participation_state"] == "unknown" for r in audit)
    complete = not unknown_dates and not unknown and bool(clubs)
    coverage = dict(
        player=player,
        player_id=pid,
        complete=complete,
        population_basis="qualified_dated_membership_and_exact_game_participation",
        coverage_scope="observed_candidate_club_games; source-qualified_club_chronology_required",
        unknown_membership_dates=unknown_dates,
        by_team=by_team,
        games=audit,
        verified_missed_games=sum(r["participation_state"] == "did_not_play" for r in audit),
        missed_games=len(selected) if complete else None,
    )
    return population.loc[selected].copy(), coverage


def read_missed_team_conditions(text: str) -> tuple[str, list[dict]]:
    """Reuse shared ownership/span readers for team-owned absence predicates."""
    from nbatools.commands._parse_helpers import extract_opponent_points_allowed_conditions
    from nbatools.commands._player_game_context import (
        _without_team_clauses,
        team_subject_stat_conditions,
    )

    owned = [item for item in team_subject_stat_conditions(text) if item["team"] == "TEAM"]
    opposing = extract_opponent_points_allowed_conditions(text)
    conditions = [
        {key: item.get(key) for key in ("stat", "min_value", "max_value")}
        for item in [*owned, *opposing]
    ]
    return _without_team_clauses(text, [*owned, *opposing]), conditions
