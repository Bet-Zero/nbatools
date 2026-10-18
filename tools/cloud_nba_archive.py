"""Bounded development staging of retained NBA Stats captures.

This is archival recovery, not direct/live Stats access or production publication.
Only public fixed-revision source reads and a new staging directory are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
from nba_api.stats.endpoints import BoxScoreTraditionalV3, PlayByPlayV3
from nba_api.stats.library.http import NBAStatsResponse

from nbatools.commands.pipeline.pull_play_by_play_events import normalize_play_by_play_events
from nbatools.commands.pipeline.pull_player_game_starter_roles import (
    add_trust_validation,
    normalize_boxscore_player_roles,
)
from nbatools.commands.pipeline.validate_raw import (
    validate_play_by_play_events_df,
    validate_team_game_stats_df,
)
from nbatools.commands.source_invariants import (
    apply_play_by_play_trust_decisions,
    expected_game_terminal_states,
)

MIRROR = "sportsdataverse/hoopR-nba-stats-raw"
PIN = "2e44b7c039f104bc6b41a1de494411e83a03714e"
SUFFIX = "2025-26_regular_season.csv"


def fetch_capture(path: str, destination: Path, revision: str) -> dict:
    url = f"https://raw.githubusercontent.com/{MIRROR}/{revision}/{path}"
    with requests.get(url, timeout=30, stream=True) as response:
        response.raise_for_status()
        payload = bytearray()
        for chunk in response.iter_content(65536):
            payload.extend(chunk)
            if len(payload) > 8_000_000:
                raise ValueError("Capture exceeds bounded 8MB limit")
    destination.write_bytes(payload)
    return {"url": url, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _official_table(path: Path, name: str) -> pd.DataFrame:
    source = json.loads(path.read_bytes())
    tables = [item for item in source["resultSets"] if item["name"] == name]
    if len(tables) != 1:
        raise ValueError(f"Expected exactly one official {name} table")
    table = tables[0]
    if len(table["headers"]) != len(set(table["headers"])):
        raise ValueError("Duplicate official source columns")
    return pd.DataFrame(table["rowSet"], columns=table["headers"])


def _endpoint(cls, path):
    endpoint = cls(game_id="0022500003", get_request=False)
    endpoint.nba_response = NBAStatsResponse(
        response=path.read_text(),
        status_code=200,
        url=f"https://stats.nba.com/stats/{endpoint.endpoint}",
    )
    endpoint.load_response()
    return endpoint


def prepare(destination: Path, *, revision: str = PIN) -> dict:
    """Qualify one fixed game through existing canonical producers and validators.

    Fixed scope prevents silent season completion claims. Changing this to wider
    acquisition requires another source-coverage/numeric acceptance, not a flag.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("An immutable full Git revision is required")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    sources = destination / "sources"
    sources.mkdir()
    captures = {}
    for name, path in {
        "teams.json": "leaguegamefinder/2026/regular-season.json",
        "players.json": "leaguegamelog/2026/regular-season_p.json",
        "boxscore.json": "boxscoretraditionalv3/2026/0022500003.json",
        "pbp.json": "playbyplayv3/2026/0022500003.json",
    }.items():
        captures[name] = fetch_capture("nba_stats/json/" + path, sources / name, revision)
    captures["LICENSE.md"] = fetch_capture("LICENSE.md", sources / "LICENSE.md", revision)

    teams = _official_table(sources / "teams.json", "LeagueGameFinderResults")
    players = _official_table(sources / "players.json", "LeagueGameLog")
    season_counts = {"team_rows": len(teams), "player_rows": len(players)}
    for name, frame in (("teams", teams), ("players", players)):
        if not frame.SEASON_ID.astype(str).eq("22025").all():
            raise ValueError(f"{name}: unexpected season/type")
        if not frame.GAME_ID.astype(str).str.fullmatch(r"00225\d{5}").all():
            raise ValueError(f"{name}: unexpected game type")
    teams = teams[teams.GAME_ID.eq("0022500003")].copy()
    players = players[players.GAME_ID.eq("0022500003")].copy()
    if len(teams) != 2 or len(players) != 21 or players.PLAYER_ID.duplicated().any():
        raise ValueError("Missing or duplicate bounded game/player coverage")
    for name, frame in (("teams", teams), ("players", players)):
        frame.to_json(sources / f"selected-{name}.json", orient="table", index=False)

    # Execute the SAME producers/feature builders in an isolated cwd. Child
    # processes receive no cloud credential; source frames are explicit inputs.
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(word in key.upper() for word in ("TOKEN", "SECRET", "R2_", "AWS_"))
    }
    env["DATA_SOURCE"] = "local"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    script = """
import pandas as pd
from nbatools.commands.pipeline import pull_games, pull_team_game_stats, pull_player_game_stats
from nbatools.commands.pipeline import build_player_game_features, build_team_game_features
from nbatools.commands.pipeline import build_game_features
t = pd.read_json('sources/selected-teams.json', orient='table')
p = pd.read_json('sources/selected-players.json', orient='table')
for module, frame in [(pull_games,t), (pull_team_game_stats,t), (pull_player_game_stats,p)]:
    module.run('2025-26','Regular Season',raw_frame=frame)
for module in [build_player_game_features, build_team_game_features, build_game_features]:
    module.run('2025-26','Regular Season')
"""
    subprocess.run([sys.executable, "-c", script], cwd=destination, env=env, check=True, timeout=60)
    raw = destination / "data/raw"
    games = pd.read_csv(raw / "games" / SUFFIX)
    team = pd.read_csv(raw / "team_game_stats" / SUFFIX)
    player = pd.read_csv(raw / "player_game_stats" / SUFFIX)
    validate_team_game_stats_df(team, games=games)
    # Finder minutes are rounded player sums (239/241 here), not the exact
    # 240:00 team boxscore clock. Preserve them, as the existing pipeline does.
    if sorted(team.pts.tolist()) != [111, 119] or team.minutes.mean() != 240:
        raise ValueError("Source disagrees with independently qualified game totals")

    box = _endpoint(BoxScoreTraditionalV3, sources / "boxscore.json").player_stats.get_data_frame()
    if not box.gameId.eq("0022500003").all():
        raise ValueError("Boxscore game identity mismatch")
    played = box[box.minutes.fillna("").ne("")].copy()
    expected_keys = set(zip(player.team_id, player.player_id))
    if set(zip(played.teamId, played.personId)) != expected_keys:
        raise ValueError("Boxscore/player-log played identities disagree")
    joined = player.merge(
        played,
        left_on=["team_id", "player_id"],
        right_on=["teamId", "personId"],
        validate="one_to_one",
    )
    for canonical, official in {
        "pts": "points",
        "reb": "reboundsTotal",
        "ast": "assists",
        "fgm": "fieldGoalsMade",
        "fga": "fieldGoalsAttempted",
    }.items():
        if not joined[canonical].eq(joined[official]).all():
            raise ValueError(f"Independent Stats captures disagree: {canonical}")

    roles = normalize_boxscore_player_roles(box)
    roles = roles[[key in expected_keys for key in zip(roles.team_id, roles.player_id)]].copy()
    roles["season"], roles["season_type"] = "2025-26", "Regular Season"
    roles = add_trust_validation(roles)
    if not roles.role_source_trusted.eq(1).all():
        raise ValueError("Untrusted starter roles")
    pbp_frame = _endpoint(PlayByPlayV3, sources / "pbp.json").play_by_play.get_data_frame()
    pbp_status = {
        "raw_actions": len(pbp_frame),
        "canonical_rows": 0,
        "duplicate_action_numbers": int(pbp_frame.actionNumber.duplicated().sum()),
        "blank_score_actions": int(pbp_frame.scoreHome.eq("").sum()),
    }
    try:
        pbp = normalize_play_by_play_events(
            pbp_frame, season="2025-26", season_type="Regular Season"
        )
        pbp, decisions = apply_play_by_play_trust_decisions(
            pbp, expected_game_terminal_states(team)
        )
        if any(decisions.values()):
            raise ValueError(f"Whole-game trust failed: {decisions}")
        validate_play_by_play_events_df(pbp)
        directory = raw / "play_by_play_events"
        directory.mkdir()
        pbp.to_csv(directory / SUFFIX, index=False)
        pbp_status.update(status="canonical-validated", canonical_rows=len(pbp))
    except ValueError as exc:
        # Raw payload availability is separate from canonical compatibility.
        # Do not delete supplemental steals/blocks or renumber official actions.
        pbp_status.update(status="canonical-rejected", reason=str(exc))
    directory = raw / "player_game_starter_roles"
    directory.mkdir()
    roles.to_csv(directory / SUFFIX, index=False)
    receipt = {
        "schema_version": 1,
        "classification": "qualified archival development slice",
        "collected_at": datetime.now(UTC).isoformat(),
        "mirror": MIRROR,
        "mirror_revision": revision,
        "attribution": (
            "SportsDataverse hoopR NBA Stats raw captures, CC BY 4.0; original source stats.nba.com"
        ),
        "sources": captures,
        "season_archive_inventory_only": season_counts,
        "game_id": "0022500003",
        "season": "2025-26",
        "season_type": "Regular Season",
        "canonical_rows": {
            "games": len(games),
            "team_game_stats": len(team),
            "player_game_stats": len(player),
            "player_game_starter_roles": len(roles),
            "play_by_play_events": pbp_status["canonical_rows"],
        },
        "team_scores": dict(zip(team.team_abbr, team.pts)),
        "play_by_play": pbp_status,
        "limitations": [
            "one game qualified; not season-wide acceptance",
            "archive retrieval time is not original capture time",
            "no fresh/live Stats acceptance",
            "periods/on-off not supplied",
            "no production publication acceptance",
        ],
        "r2_writes": 0,
    }
    receipt["files"] = {
        str(p.relative_to(destination)): {
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mirror-revision", default=PIN)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, revision=args.mirror_revision), indent=2))


if __name__ == "__main__":
    main()
