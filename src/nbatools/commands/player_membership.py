"""Dated membership and exact-game participation through the shared result/API path."""

from __future__ import annotations

import pandas as pd

from nbatools.commands._dated_membership import calendar_date, load_membership, membership_on_date
from nbatools.commands._participation_observations import combined_observations, game_participation
from nbatools.commands.structured_results import SummaryResult


def build_result(
    player_id: int,
    date: str,
    season: str,
    team_id: int | None = None,
    game_id: int | None = None,
    season_type: str = "Regular Season",
) -> SummaryResult:
    """Return explicit unknowns when qualified date/game evidence is absent.

    A date-only query uses certified dated intervals. Add game_id to use an
    exact-game association as well. An observation in another game on the same
    date cannot certify membership for the requested game.
    """
    if player_id is None or any(
        type(value) is not int or value <= 0
        for value in (player_id, team_id, game_id)
        if value is not None
    ):
        raise ValueError("Positive player/team identity is required")
    if season_type not in {"Regular Season", "Playoffs"}:
        raise ValueError("Invalid membership season type")
    day = calendar_date(date)
    intervals = load_membership([season])
    membership = membership_on_date(intervals, player_id, day, team_id)
    participation = "unknown"
    identity = intervals.loc[intervals.player_id.eq(player_id)]
    player_name = str(identity.player_name.iloc[0]) if len(identity) else None
    team_abbr = None
    if game_id is not None:
        from nbatools.commands.data_utils import load_team_games_for_seasons

        games = load_team_games_for_seasons([season], season_type)
        games = games.loc[pd.to_numeric(games.game_id).eq(game_id)]
        if games.empty or not pd.to_datetime(games.game_date).dt.date.eq(day).all():
            raise ValueError("Requested game/date is absent from the selected season/type")
        sides = set(games.team_id.astype(int))
        sides.update(games.opponent_team_id.astype(int))
        if len(sides) != 2 or (team_id is not None and team_id not in sides):
            raise ValueError("Requested team is outside the game sides")
        observations, _ = combined_observations([season], season_type)
        exact = observations.loc[
            observations.player_id.eq(player_id) & observations.game_id.eq(game_id)
        ]
        if len(exact):
            player_name = str(exact.player_name.iloc[0])
        target = team_id
        if target is None:
            target = int(exact.team_id.iloc[0]) if len(exact) else membership.team_id
        # With no known club, either actual side can establish only unknown
        # or an explicit negative for that side; it cannot identify a club.
        target = target if target is not None else min(sides)
        if target not in sides:
            raise ValueError("Qualified member team is outside the game sides")
        participation, membership = game_participation(
            observations,
            intervals,
            player_id,
            game_id,
            target,
            day,
            other_team=next(t for t in sides if t != target),
        )
        if team_id is None and membership.state == "not_member":
            # A side-specific negative does not answer which club the player joined.
            membership = membership_on_date(intervals, player_id, day)
            participation = "unknown"
        known_club = games.loc[games.team_id.eq(membership.team_id)]
        if not known_club.empty and "team_abbr" in known_club:
            team_abbr = str(known_club.team_abbr.iloc[0])
    summary = pd.DataFrame(
        [
            dict(
                player_id=player_id,
                player_name=player_name,
                member_team_abbr=team_abbr,
                date=date,
                requested_team_id=team_id,
                member_team_id=membership.team_id,
                membership_state=membership.state,
                game_id=game_id,
                participation_state=participation,
                evidence_basis=membership.basis,
            )
        ]
    )
    return SummaryResult(
        summary=summary,
        metadata={"source_hashes": list(membership.source_hashes)},
        caveats=[
            "Unknown means insufficient qualified evidence, never zero missed games.",
            "Membership alone establishes no participation, injury, health or absence reason.",
        ],
    )
