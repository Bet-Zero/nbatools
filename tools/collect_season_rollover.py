"""One pinned 2026-27 schedule-body capture, never refresh or publication.

Retain the whole original and its observed regular-season population before
requesting any final-game statistics. Mirror timestamps do not prove freshness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from tools.cloud_nba_archive import MIRROR, fetch_capture
from tools.cloud_season_sources import check_schedule

REVISION = "7a1ab93e02f7a4d23443d3c6abb14bafe9c94f11"
PATH = "nba_stats/json/scheduleleaguev2/2027.json"
BLOB = "f722a15886ece11915a37e197f4873c34c893284"
BYTES = 4379956
SEASON = "2026-27"


def schedule_population(document):
    """Preserve source status and IDs; no finalized-stat or completeness flags."""
    checked = check_schedule(document, SEASON)
    rows = []
    for day in document["leagueSchedule"]["gameDates"]:
        for game in day["games"]:
            if not str(game["gameId"]).startswith("00226"):
                continue
            date = pd.to_datetime(game["gameDateEst"], errors="raise")
            if pd.isna(date):
                raise ValueError("Missing source schedule date")
            home, away = game["homeTeam"]["teamId"], game["awayTeam"]["teamId"]
            if type(game["gameStatus"]) is not int:
                raise ValueError("Invalid source schedule status type")
            if any(type(value) is not int or value < 0 for value in [home, away]):
                raise ValueError("Invalid source schedule team identity")
            if game["gameStatus"] == 3 and (not home or not away):
                raise ValueError("Final source game has unresolved team identity")
            rows.append(
                dict(
                    game_id=game["gameId"],
                    game_date_est=date.strftime("%Y-%m-%d"),
                    game_status=game["gameStatus"],
                    home_team_id=home,
                    away_team_id=away,
                    game_status_text=game.get("gameStatusText"),
                )
            )
    if len(rows) != checked["regular_games"]:
        raise ValueError("Regular source population differs from scoped schedule")
    return checked, rows


def collect_schedule(output: Path) -> dict:
    """Capture exactly one reviewed immutable public body into a new directory."""
    output.mkdir(parents=True, exist_ok=False)
    source = output / "scheduleleaguev2-2027.json"
    started = datetime.now(UTC).isoformat()
    capture = fetch_capture(PATH, source, REVISION)
    raw = source.read_bytes()
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if len(raw) != BYTES or blob != BLOB or capture["sha256"] != hashlib.sha256(raw).hexdigest():
        raise ValueError("Schedule original differs from reviewed immutable archive metadata")
    document = json.loads(raw)
    checked, population = schedule_population(document)
    final = [row for row in population if row["game_status"] == 3]
    report = dict(
        schema_version=1,
        classification="retained_schedule_source_not_canonical_or_published",
        season=SEASON,
        season_type="Regular Season",
        archive_repository=MIRROR,
        archive_revision=REVISION,
        archive_path=PATH,
        archive_git_blob_sha=blob,
        capture_started_at=started,
        retrieved_at=datetime.now(UTC).isoformat(),
        original_source_capture_time="unverified; retained document metadata is preserved",
        source_document_meta=document.get("meta"),
        source=capture,
        source_file=source.name,
        schedule=checked,
        observed_regular_games=population,
        observed_final_game_ids=[row["game_id"] for row in final],
        final_population_scope="only explicit gameStatus3 in this complete retained body",
        independent_schedule_completeness="not_established",
        required_next_inputs=(
            "exact final-game/team/player/period keys after independent body qualification"
        ),
        acquired_source_bodies=1,
        nba_stats_probes=0,
        production_writes=0,
        automatic_refresh=False,
    )
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    collect_schedule(args.output)
