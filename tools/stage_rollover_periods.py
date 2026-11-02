"""Offline admission of captured period windows through the existing importer.

Call only with hash/provenance-bound originals and qualified whole-game context.
No fetching, publication, completeness flags or unobserved windows are supplied.
"""

from __future__ import annotations

import json
import math

import pandas as pd
from nba_api.stats.endpoints import BoxScoreAdvancedV3, BoxScoreTraditionalV3
from nba_api.stats.library.http import NBAStatsResponse

from nbatools.commands.data_utils import add_advanced_pct_columns
from nbatools.commands.pipeline import pull_game_period_stats as importer
from nbatools.commands.pipeline.validate_raw import (
    validate_player_game_period_stats_df,
    validate_team_game_period_stats_df,
)
from tools.season_rollover_core_bridge import FIELDS, _integer, _literal_clock_seconds


def _endpoint(cls, raw, game_id):
    endpoint = cls(game_id=game_id, get_request=False)
    endpoint.nba_response = NBAStatsResponse(
        response=raw.decode(),
        status_code=200,
        url=f"https://stats.nba.com/stats/{endpoint.endpoint}",
    )
    endpoint.load_response()
    return endpoint


def import_window(
    traditional_raw: bytes,
    advanced_raw: bytes,
    *,
    game_id: str,
    window: importer.PeriodWindow,
    summary: dict,
    player_context: pd.DataFrame,
    team_context: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate literal source semantics before normalization; keep missing missing.

    Summary is a separately qualified full-game original. The caller binds request
    parameters/transport timestamps and bytes independently, never meta.request.
    """
    if window not in importer.PERIOD_WINDOWS:
        raise ValueError("Unsupported captured period window")
    boxes = [
        json.loads(raw)[key]
        for raw, key in [
            (traditional_raw, "boxScoreTraditional"),
            (advanced_raw, "boxScoreAdvanced"),
        ]
    ]
    oracle = summary["boxScoreSummary"]
    if oracle["gameId"] != game_id or any(box["gameId"] != game_id for box in boxes):
        raise ValueError("Period/summary game identity differs")
    player_context = player_context.loc[player_context.game_id.eq(int(game_id))].copy()
    team_context = team_context.loc[team_context.game_id.eq(int(game_id))].copy()
    if len(team_context) != 2 or player_context.empty:
        raise ValueError("Qualified whole-game context required")
    if player_context.duplicated(["game_id", "team_id", "player_id"]).any():
        raise ValueError("Duplicate whole-game context")
    seen = set()
    for side in ("homeTeam", "awayTeam"):
        team, advanced = [box[side] for box in boxes]
        ref = oracle[side]
        tid = ref["teamId"]
        if team["teamId"] != tid or advanced["teamId"] != tid:
            raise ValueError("Period source side differs from Summary")
        context = team_context.loc[team_context.team_id.eq(tid)]
        if len(context) != 1:
            raise ValueError("Period source team missing from context")
        periods = [
            p for p in ref["periods"] if window.start_period <= p["period"] <= window.end_period
        ]
        expected_periods = set(
            range(window.start_period, min(window.end_period, oracle["period"]) + 1)
        )
        if not expected_periods or {p["period"] for p in periods} != expected_periods:
            raise ValueError("Summary window coverage incomplete")
        expected_seconds = 5 * sum(720 if p <= 4 else 300 for p in expected_periods)
        stats = team["statistics"]
        if _integer(stats["points"]) != sum(_integer(p["score"]) for p in periods):
            raise ValueError("Period score differs from Summary")
        opposite = oracle["awayTeam" if side == "homeTeam" else "homeTeam"]
        opposite_points = sum(
            _integer(p["score"])
            for p in opposite["periods"]
            if window.start_period <= p["period"] <= window.end_period
        )
        margin = stats["plusMinusPoints"]
        if (
            type(margin) not in (int, float)
            or not math.isfinite(margin)
            or margin != stats["points"] - opposite_points
        ):
            raise ValueError("Period team margin differs from Summary scores")
        for source_team in (team, advanced):
            if _literal_clock_seconds(source_team["statistics"]["minutes"]) != expected_seconds:
                raise ValueError("Period team clock differs from window")
        source_players = []
        for source_team in (team, advanced):
            listed = source_team["players"]
            ids = [p["personId"] for p in listed]
            if any(type(pid) is not int or pid <= 0 for pid in ids) or len(set(ids)) != len(ids):
                raise ValueError("Duplicate/invalid period player identity")
            played = {
                p["personId"]: p["statistics"]
                for p in listed
                if _literal_clock_seconds(p["statistics"]["minutes"]) > 0
            }
            if (
                abs(
                    sum(_literal_clock_seconds(p["minutes"]) for p in played.values())
                    - expected_seconds
                )
                > 2
            ):
                raise ValueError("Period player clock denominator differs")
            source_players.append(played)
        players, rates = source_players
        if not players or players.keys() != rates.keys() or seen.intersection(players):
            raise ValueError("Period player identity sets differ")
        seen.update(players)
        known = set(player_context.loc[player_context.team_id.eq(tid), "player_id"])
        if not set(players).issubset(known):
            raise ValueError("Period played identity absent from whole-game context")
        if sum(_integer(p["points"]) for p in players.values()) != stats["points"]:
            raise ValueError("Period player points differ from team")
        for p in [stats, *players.values()]:
            for field in FIELDS:
                _integer(p[field])
            if (
                p["fieldGoalsMade"] > p["fieldGoalsAttempted"]
                or p["threePointersMade"] > p["threePointersAttempted"]
                or p["freeThrowsMade"] > p["freeThrowsAttempted"]
                or p["reboundsOffensive"] + p["reboundsDefensive"] != p["reboundsTotal"]
                or 2 * p["fieldGoalsMade"] + p["threePointersMade"] + p["freeThrowsMade"]
                != p["points"]
            ):
                raise ValueError("Invalid period count arithmetic")
        for pid, p in players.items():
            seconds = _literal_clock_seconds(p["minutes"])
            if (
                seconds > expected_seconds / 5
                or abs(seconds - _literal_clock_seconds(rates[pid]["minutes"])) > 1
            ):
                raise ValueError("Period player clocks disagree/exceed window")
            for field, ceiling in [
                ("usagePercentage", 1),
                ("assistPercentage", 1),
                ("reboundPercentage", 1),
                ("turnoverRatio", 100),
            ]:
                value = float(rates[pid][field])
                if not math.isfinite(value) or not 0 <= value <= ceiling:
                    raise ValueError("Invalid period Advanced rate")
    traditional = _endpoint(BoxScoreTraditionalV3, traditional_raw, game_id)
    advanced = _endpoint(BoxScoreAdvancedV3, advanced_raw, game_id)
    players = importer.normalize_boxscore_player_period_rows(
        traditional.player_stats.get_data_frame(),
        season="2026-27",
        season_type="Regular Season",
        period_window=window,
        player_context=player_context,
    )
    rates = importer.normalize_boxscore_player_advanced_rows(advanced.player_stats.get_data_frame())
    players = players.merge(
        rates, on=["game_id", "team_id", "player_id"], how="left", validate="one_to_one"
    )
    missing_rates = players[list(importer.PLAYER_RATE_COLUMNS)].isna().any(axis=1)
    if (missing_rates & players.minutes.gt(0)).any():
        raise ValueError("Missing period Advanced rate row")
    # A literal zero-duration source row has no rate denominator. Never fill a
    # missing played-player rate, and never fabricate an unobserved window.
    players.loc[players.minutes.eq(0), list(importer.PLAYER_RATE_COLUMNS)] = 0.0
    players = add_advanced_pct_columns(players)[list(importer.PLAYER_PERIOD_OUTPUT_COLUMNS)]
    if window.period_family != "overtime":
        players = importer._complete_player_standard_window_keys(
            players,
            player_context,
            period_windows=(window,),
        )
    players = players.reset_index(drop=True)
    teams = importer.normalize_boxscore_team_period_rows(
        traditional.team_stats.get_data_frame(),
        season="2026-27",
        season_type="Regular Season",
        period_window=window,
        team_context=team_context,
    )
    teams = add_advanced_pct_columns(teams)[list(importer.TEAM_PERIOD_OUTPUT_COLUMNS)]
    return (
        validate_player_game_period_stats_df(players),
        validate_team_game_period_stats_df(teams),
    )
