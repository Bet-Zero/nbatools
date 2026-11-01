"""One justified official CDN capture for the missing 2026-27 ATL/CLE source.

The archive lacks this Traditional body and retained player totals disagree by
one Atlanta free throw. Capture evidence; never impute a player or publish data.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import requests

from nbatools.commands.pipeline.player_game_availability_report import live_identity_rows

GAME_ID = 22600144
URL = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600144.json"
SCOPE = dict(
    game_id=GAME_ID,
    game_date="2026-10-29",
    home_team_id=1610612737,
    away_team_id=1610612739,
    by_id={1610612737: ("ATL", 114), 1610612739: ("CLE", 111)},
)


def collect_missing_boxscore(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat()
    raw = bytearray()
    attempt = dict(
        source_url=URL,
        game_id="0022600144",
        started_at=started,
        attempts=1,
        production_writes=0,
        http_status=None,
        response_complete=False,
        identity_scope_qualified=False,
        classification="unqualified_capture_attempt",
    )
    try:
        with requests.get(URL, timeout=20, stream=True) as response:
            attempt["http_status"] = response.status_code
            for chunk in response.iter_content(65536):
                remaining = 2_000_000 - len(raw)
                raw.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    attempt["response_truncated"] = True
                    raise ValueError("One-game CDN capture exceeds 2MB bound")
            attempt["response_complete"] = True
            response.raise_for_status()
        payload = json.loads(raw)
        identities = live_identity_rows(payload, **SCOPE)
        source = output / "boxscore_0022600144.json"
        source.write_bytes(raw)
        report = dict(
            classification="retained_official_identity_scope_not_statistical_or_participation_acceptance",
            season="2026-27",
            season_type="Regular Season",
            game_id="0022600144",
            source_url=URL,
            capture_started_at=started,
            retrieved_at=datetime.now(UTC).isoformat(),
            source_sha256=hashlib.sha256(raw).hexdigest(),
            source_bytes=len(raw),
            source_file=source.name,
            source_meta=payload.get("meta"),
            source_identity_rows=len(identities),
            attempts=1,
            original_source_capture_time="unverified; original response preserved",
            nba_stats_probes=0,
            production_writes=0,
            statistical_qualification="pending_independent_original_rows",
        )
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        attempt["identity_scope_qualified"] = True
        return report
    except Exception as exc:
        attempt["error_type"] = type(exc).__name__
        if raw:
            (output / "unqualified-response.bin").write_bytes(raw)
        raise
    finally:
        attempt.update(
            finished_at=datetime.now(UTC).isoformat(),
            response_bytes=len(raw),
            response_sha256=hashlib.sha256(raw).hexdigest(),
        )
        (output / "capture-attempt.json").write_text(json.dumps(attempt, indent=2) + "\n")
