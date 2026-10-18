"""Manual, bounded qualification of additional official season-input captures.

No refresh timer or publication. Completed-season snapshots and upcoming-season
planning evidence remain separate; archive retrieval is never source freshness.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
from nba_api.stats.static import teams

from nbatools.commands.pipeline import pull_player_season_advanced as player_advanced
from nbatools.commands.pipeline import (
    pull_rosters,
    pull_standings_snapshots,
    pull_team_season_advanced,
)
from tools.cloud_nba_archive import MIRROR, _official_table, fetch_capture

PIN = "9e81bacbd75f882c5194eb70b6900bbdf30bd0fc"
ROOT = Path(__file__).resolve().parents[1]
SEASON = "2025-26"
TYPE = "Regular Season"


def check_parameters(document: dict, expected: dict) -> None:
    parameters = document.get("parameters", {})
    if any(parameters.get(key) != value for key, value in expected.items()):
        raise ValueError("Official response parameters do not match requested statistical scope")


def check_schedule(document: dict, season: str) -> dict:
    schedule = document["leagueSchedule"]
    if schedule["seasonYear"] != season or schedule["leagueId"] != "00":
        raise ValueError("Schedule season/league mismatch")
    games = [game for day in schedule["gameDates"] for game in day["games"]]
    regular = [g for g in games if re.fullmatch("002" + season[2:4] + r"\d{5}", g["gameId"])]
    if not regular or len({g["gameId"] for g in regular}) != len(regular):
        raise ValueError("Empty or duplicate regular-season schedule identities")
    for game in regular:
        home, away = game["homeTeam"]["teamId"], game["awayTeam"]["teamId"]
        if home == away and not (home == 0 and game["gameStatus"] == 1):
            raise ValueError("Schedule self matchup")
        if game["gameStatus"] not in (1, 2, 3):
            raise ValueError("Unknown schedule state")
    return {
        "season": season,
        "regular_games": len(regular),
        "unresolved_matchups": sum(
            not g["homeTeam"]["teamId"] or not g["awayTeam"]["teamId"] for g in regular
        ),
        "final_regular_games": sum(g["gameStatus"] == 3 for g in regular),
        "first_regular_date": min(g["gameDateEst"][:10] for g in regular),
        "scope": "planning only; not the canonical completed-game schedule",
    }


def qualify(destination: Path, *, revision: str = PIN) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Full immutable source revision required")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    sources = destination / "sources"
    sources.mkdir()
    paths = {
        "players.json": "leaguedashplayerstats/2026/regular-season_advanced_pergame.json",
        "teams.json": "leaguedashteamstats/2026/regular-season_advanced_pergame.json",
        "standings.json": "leaguestandings/2026/regular-season.json",
        "upcoming-schedule.json": "scheduleleaguev2/2027.json",
        "upcoming-players.json": "leaguedashplayerstats/2027/regular-season_advanced_pergame.json",
        "upcoming-standings.json": "leaguestandingsv3/2027/regular-season.json",
    }
    team_list = teams.get_teams()
    paths.update(
        {f"roster-{t['id']}.json": f"commonteamroster/2026/{t['id']}.json" for t in team_list}
    )
    captures = {}

    def fetch(item):
        name, path = item
        try:
            return name, fetch_capture("nba_stats/json/" + path, sources / name, revision)
        except requests.HTTPError as exc:
            if name.startswith("roster-") and exc.response.status_code == 404:
                return name, {"status": "missing", "http_status": 404, "path": path}
            raise

    with ThreadPoolExecutor(max_workers=4) as pool:
        captures.update(pool.map(fetch, paths.items()))
    captures["LICENSE.md"] = fetch_capture("LICENSE.md", sources / "LICENSE.md", revision)
    # Reuse the accepted original season Finder capture for independent standings
    # reconciliation and as-of date, without repeating its acquisition audit.
    old = ROOT / "working/nba-tools-completion-program/cloud-operations"
    expected = json.loads((old / "core-archive-receipt.json").read_text())["durable_bundle"]
    bundle = (old / "core-archive-staging.zip").read_bytes()
    if hashlib.sha256(bundle).hexdigest() != expected["sha256"]:
        raise ValueError("Accepted source bundle hash mismatch")
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        original = archive.read("sources/teams.json")
        reference = json.loads(archive.read("receipt.json"))["files"]["sources/teams.json"]
    if hashlib.sha256(original).hexdigest() != reference["sha256"]:
        raise ValueError("Accepted Finder capture hash mismatch")
    (sources / "accepted-games.json").write_bytes(original)
    finder = _official_table(sources / "accepted-games.json", "LeagueGameFinderResults")
    if (
        not finder.SEASON_ID.astype(str).eq("22025").all()
        or finder.duplicated(["GAME_ID", "TEAM_ID"]).any()
    ):
        raise ValueError("Finder season/identity mismatch")
    as_of = pd.to_datetime(finder.GAME_DATE).max().strftime("%Y-%m-%d")
    expected_teams = {t["id"] for t in team_list}
    for name in ("players", "teams"):
        check_parameters(
            json.loads((sources / f"{name}.json").read_text()),
            {
                "Season": SEASON,
                "SeasonType": TYPE,
                "MeasureType": "Advanced",
                "PerMode": "PerGame",
                "TeamID": 0,
                "Period": 0,
                "LastNGames": 0,
                "DateFrom": "",
                "DateTo": "",
            },
        )
    check_parameters(
        json.loads((sources / "standings.json").read_text()),
        {"Season": SEASON, "SeasonType": TYPE},
    )
    p_raw = _official_table(sources / "players.json", "LeagueDashPlayerStats")
    t_raw = _official_table(sources / "teams.json", "LeagueDashTeamStats")
    s_raw = _official_table(sources / "standings.json", "Standings")
    p = player_advanced.normalize(p_raw, SEASON, TYPE, as_of)
    t = pull_team_season_advanced.normalize(t_raw, SEASON, TYPE, as_of)
    s = pull_standings_snapshots.normalize(s_raw, SEASON, TYPE, as_of)
    for frame, key in ((p, "player_id"), (t, "team_id"), (s, "team_id")):
        if frame.empty or frame[key].duplicated().any():
            raise ValueError("Missing/duplicate season snapshot identity")
    if set(t.team_id) != expected_teams or set(s.team_id) != expected_teams:
        raise ValueError("Incomplete team coverage")
    totals = (
        finder.assign(wins=finder.WL.eq("W").astype(int), losses=finder.WL.eq("L").astype(int))
        .groupby("TEAM_ID")[["wins", "losses"]]
        .sum()
    )
    for frame in (t, s):
        checked = frame.set_index("team_id").sort_index()
        if not checked[["wins", "losses"]].eq(totals.sort_index()).all().all():
            raise ValueError("Independent completed-game record mismatch")
    if not (t.games_played == t.wins + t.losses).all():
        raise ValueError("Team game denominator mismatch")
    if not ((t.off_rating - t.def_rating - t.net_rating).abs() < 0.5).all():
        raise ValueError("Net rating mismatch")
    if (
        p[["usage_rate", "ts_pct", "minutes_per_game"]].isna().any().any()
        or not p.usage_rate.between(0, 1).all()
        or not p.ts_pct.between(0, 2).all()
    ):
        raise ValueError("Invalid player advanced rates")
    rosters = []
    for team in team_list:
        path = sources / f"roster-{team['id']}.json"
        if not path.exists():
            continue
        check_parameters(json.loads(path.read_text()), {"TeamID": team["id"], "Season": "2025"})
        raw = _official_table(path, "CommonTeamRoster")
        if (
            raw.empty
            or not raw.TeamID.eq(team["id"]).all()
            or not raw.SEASON.astype(str).eq("2025").all()
        ):
            raise ValueError("Roster season/team mismatch")
        rosters.append(
            pull_rosters.normalize_columns(raw, SEASON, team["id"], team["abbreviation"])
        )
    r = pd.concat(rosters, ignore_index=True)
    r["birth_date"] = pd.to_datetime(r.birth_date, format="%b %d, %Y", errors="raise").dt.strftime(
        "%Y-%m-%d"
    )
    r["experience_years"] = pd.to_numeric(r.experience_years.replace("R", "0"), errors="raise")
    r["weight"] = pd.to_numeric(r.weight, errors="raise")
    if r.duplicated(["season", "team_id", "player_id", "stint"]).any():
        raise ValueError("Duplicate roster identities")
    missing_rosters = sorted(expected_teams - set(r.team_id))
    partial = destination / "partial"
    partial.mkdir()
    r.sort_values(["team_id", "player_id"]).to_csv(partial / "rosters.csv", index=False)
    for name, frame, sort in (
        ("player_season_advanced", p, ["player_id"]),
        ("team_season_advanced", t, ["team_id"]),
        ("standings_snapshots", s, ["team_id"]),
    ):
        directory = destination / "data/raw" / name
        directory.mkdir(parents=True)
        suffix = f"{SEASON}_regular_season"
        frame.sort_values(sort).to_csv(directory / f"{suffix}.csv", index=False)
    schedule = check_schedule(
        json.loads((sources / "upcoming-schedule.json").read_text()), "2026-27"
    )
    check_parameters(
        json.loads((sources / "upcoming-players.json").read_text()),
        {"Season": "2026-27", "SeasonType": TYPE, "MeasureType": "Advanced", "PerMode": "PerGame"},
    )
    upcoming_players = _official_table(sources / "upcoming-players.json", "LeagueDashPlayerStats")
    check_parameters(
        json.loads((sources / "upcoming-standings.json").read_text()),
        {"SeasonYear": "2026-27", "SeasonType": TYPE},
    )
    upcoming_standings = _official_table(sources / "upcoming-standings.json", "Standings")
    # Empty player stats are not fresh statistics or proof of source health. An
    # upcoming season never replaces a known-good completed-season snapshot.
    rollover = {
        **schedule,
        "advanced_player_rows": len(upcoming_players),
        "standings_rows": len(upcoming_standings),
        "promotion": "blocked: new season inputs/period/on-off not qualified",
        "previous_season_preserved": True,
    }
    receipt = {
        "schema_version": 1,
        "mirror": MIRROR,
        "revision": revision,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "original_capture_time": "unknown",
        "scope": "completed-season input snapshots and separate upcoming-season planning",
        "season": SEASON,
        "as_of_completed_game": as_of,
        "roster_snapshot": {
            "state": "partial; not canonical whole-league output",
            "teams": r.team_id.nunique(),
            "rows": len(r),
            "missing_team_ids": missing_rosters,
        },
        "canonical_rows": {
            "player_season_advanced": len(p),
            "team_season_advanced": len(t),
            "standings_snapshots": len(s),
        },
        "sources": captures,
        "accepted_finder_bundle_sha256": expected["sha256"],
        "rollover": rollover,
        "automatic_refresh": False,
        "production_writes": 0,
        "limitations": [
            "No live NBA Stats access or full refresh acceptance",
            "Roster snapshot is not historical membership intervals",
            "Upcoming official schedule retained as planning source, never mislabeled Final",
            "No period/on-off substitution",
            "Mirror commit/retrieval time is not original capture time",
        ],
    }
    receipt["files"] = {
        path.relative_to(destination).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mirror-revision", default=PIN)
    args = parser.parse_args()
    print(json.dumps(qualify(args.output, revision=args.mirror_revision), sort_keys=True))


if __name__ == "__main__":
    main()
