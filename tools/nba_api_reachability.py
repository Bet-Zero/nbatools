"""Check whether this machine can reach the NBA stats endpoints the refresh uses.

A nightly refresh can only run in GitHub Actions if stats.nba.com answers
requests from GitHub's runners; it is known to refuse some cloud networks.
This makes one small request per endpoint (no retries, no credentials, no
writes) and prints a JSON receipt with each endpoint's outcome and timing.

    python tools/nba_api_reachability.py --season 2025-26 --output receipt.json

Exits 1 when any endpoint the current-season refresh depends on fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Any

REQUEST_TIMEOUT = 30


def _game_finder(season: str, kind: str) -> Any:
    from nba_api.stats.endpoints import LeagueGameFinder

    return LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Regular Season",
        player_or_team_abbreviation=kind,
        timeout=REQUEST_TIMEOUT,
    )


_CDN = "https://cdn.nba.com/static/json"


class _CdnJson:
    """Fetch one CDN JSON document and expose it like an nba_api endpoint."""

    def __init__(self, url: str, key: str):
        import pandas as pd
        import requests

        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        if key not in response.json():
            raise ValueError(f"CDN document has no {key!r}")
        self.document = response.json()
        self._frame = pd.DataFrame([{"bytes": len(response.content)}])

    def get_data_frames(self) -> list[Any]:
        return [self._frame]


class Skipped(Exception):
    """A check that could not be attempted because an earlier one failed."""


def _checks(season: str) -> list[Check]:
    """(name, needed by the current-season refresh, request) for each endpoint."""
    from nba_api.stats.endpoints import (
        BoxScoreTraditionalV3,
        CommonTeamRoster,
        LeagueDashPlayerStats,
        LeagueLineupViz,
        LeagueStandings,
        PlayByPlayV3,
        TeamPlayerOnOffSummary,
    )

    celtics = 1610612738
    game_ids: list[str] = []

    def team_game_log() -> Any:
        endpoint = _game_finder(season, "T")
        frame = endpoint.get_data_frames()[0]
        if not frame.empty:
            game_ids.append(str(frame["GAME_ID"].iloc[0]))
        return endpoint

    def game() -> str:
        if not game_ids:
            raise Skipped("no game id: the team game log failed or returned no games")
        return game_ids[0]

    cdn_game_ids: list[str] = []

    def cdn_schedule() -> Any:
        endpoint = _CdnJson(f"{_CDN}/staticData/scheduleLeagueV2.json", "leagueSchedule")
        for day in endpoint.document["leagueSchedule"].get("gameDates") or []:
            for item in day.get("games") or []:
                if item.get("gameStatus") == 3 and not cdn_game_ids:
                    cdn_game_ids.append(str(item["gameId"]))
        return endpoint

    def cdn_box_score() -> Any:
        game_id = (cdn_game_ids or game_ids or [None])[0]
        if game_id is None:
            raise Skipped("no game id from the CDN schedule or the team game log")
        return _CdnJson(f"{_CDN}/liveData/boxscore/boxscore_{game_id}.json", "game")

    return [
        ("team_game_log", True, team_game_log),
        ("player_game_log", True, lambda: _game_finder(season, "P")),
        (
            "player_season_advanced",
            True,
            lambda: LeagueDashPlayerStats(
                season=season,
                season_type_all_star="Regular Season",
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                timeout=REQUEST_TIMEOUT,
            ),
        ),
        (
            "standings",
            True,
            lambda: LeagueStandings(season=season, timeout=REQUEST_TIMEOUT),
        ),
        (
            "team_roster",
            True,
            lambda: CommonTeamRoster(team_id=celtics, season=season, timeout=REQUEST_TIMEOUT),
        ),
        (
            "box_score",
            True,
            lambda: BoxScoreTraditionalV3(game_id=game(), timeout=REQUEST_TIMEOUT),
        ),
        # Sources for data the site does not have yet (play-by-play, from
        # which clutch stats are built; lineups; on/off).
        (
            "play_by_play",
            False,
            lambda: PlayByPlayV3(game_id=game(), timeout=REQUEST_TIMEOUT),
        ),
        (
            "lineups",
            False,
            lambda: LeagueLineupViz(
                minutes_min=10,
                group_quantity="5",
                season=season,
                season_type_all_star="Regular Season",
                timeout=REQUEST_TIMEOUT,
            ),
        ),
        (
            "on_off",
            False,
            lambda: TeamPlayerOnOffSummary(
                team_id=celtics,
                season=season,
                season_type_all_star="Regular Season",
                timeout=REQUEST_TIMEOUT,
            ),
        ),
        # The public NBA CDN, a possible alternative source when stats.nba.com
        # refuses this network. Not used by the pipeline yet.
        ("cdn_schedule", False, cdn_schedule),
        ("cdn_box_score", False, cdn_box_score),
    ]


def _run_check(request: Callable[[], Any]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        frames = request().get_data_frames()
    except Skipped as exc:
        return {"ok": None, "skipped": str(exc)}
    except Exception as exc:  # the receipt records any failure; nothing is retried
        return {
            "ok": False,
            "seconds": round(time.monotonic() - started, 2),
            "error": type(exc).__name__,
            "detail": str(exc)[:200],
        }
    return {
        "ok": True,
        "seconds": round(time.monotonic() - started, 2),
        "rows": int(frames[0].shape[0]) if frames else 0,
    }


Check = tuple[str, bool, Callable[[], Any]]


def probe(season: str, checks: list[Check] | None = None) -> dict[str, Any]:
    results = {}
    for name, required, request in checks if checks is not None else _checks(season):
        results[name] = {"required_for_refresh": required, **_run_check(request)}
    return {
        "season": season,
        "nba_api_version": _nba_api_version(),
        "refresh_endpoints_reachable": all(
            r["ok"] is True for r in results.values() if r["required_for_refresh"]
        ),
        "endpoints": results,
    }


def _nba_api_version() -> str | None:
    try:
        return metadata.version("nba_api")
    except metadata.PackageNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--season", required=True, help="Season to request, e.g. 2025-26")
    parser.add_argument("--output", help="Optional JSON receipt path")
    args = parser.parse_args()

    receipt = probe(args.season)
    text = json.dumps(receipt, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0 if receipt["refresh_endpoints_reachable"] else 1


if __name__ == "__main__":
    sys.exit(main())
