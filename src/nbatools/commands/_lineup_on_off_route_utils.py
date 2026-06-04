"""Lineup and on/off route helpers for natural query finalization."""

from __future__ import annotations


def try_lineup_on_off_route(parsed: dict) -> tuple[str, dict] | None:
    """Return a lineup/on-off route match, preserving natural-query branch order."""
    season = parsed["season"]
    start_season = parsed["start_season"]
    end_season = parsed["end_season"]
    start_date = parsed.get("start_date")
    end_date = parsed.get("end_date")
    season_type = parsed["season_type"]
    stat = parsed["stat"]
    player = parsed["player"]
    team = parsed["team"]
    opponent = parsed["opponent"]
    last_n = parsed["last_n"]
    top_n = parsed.get("top_n")
    lineup_members = parsed.get("lineup_members") or []
    presence_state = parsed.get("presence_state")
    unit_size = parsed.get("unit_size")
    minute_minimum = parsed.get("minute_minimum")
    lineup_query_mode = parsed.get("lineup_query_mode")

    if lineup_members and presence_state is not None:
        return "player_on_off", {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "player": player or lineup_members[0],
            "team": team,
            "opponent": opponent,
            "lineup_members": lineup_members,
            "presence_state": presence_state,
            "last_n": last_n,
        }
    if lineup_query_mode == "lineup_summary":
        return "lineup_summary", {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "lineup_members": lineup_members,
            "unit_size": unit_size,
            "minute_minimum": minute_minimum,
            "stat": stat,
            "last_n": last_n,
        }
    if lineup_query_mode == "lineup_leaderboard":
        return "lineup_leaderboard", {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "lineup_members": lineup_members,
            "unit_size": unit_size,
            "minute_minimum": minute_minimum,
            "stat": stat,
            "limit": top_n or 10,
            "last_n": last_n,
        }
    return None
