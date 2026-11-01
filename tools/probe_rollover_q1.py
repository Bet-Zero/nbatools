"""One fixed, correctly parameterized Q1 V3 source probe; no retries or backfill.

The retained quarter archive returned zeros without demonstrated range parameters.
This separate bounded probe preserves failures and does not change pipeline policy.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from nba_api.stats.endpoints import BoxScoreAdvancedV3, BoxScoreTraditionalV3
from nba_api.stats.library.http import NBAStatsHTTP

from nbatools.commands.pipeline.pull_game_period_stats import (
    PERIOD_END_RANGE,
    PERIOD_RANGE_TYPE,
    _parse_minutes_value,
)
from nbatools.commands.pipeline.structured_participation import _table
from tools.collect_season_rollover import BLOB, BYTES, REVISION
from tools.season_rollover_source_stats import retained_stats_documents

GAME = "0022600001"
SUMMARY_SHA = "7e61162d1ec001d5235a8dd2125a654dfad30887db90e0d0c58621859383cf5a"


def load_oracle(evidence):
    directory = evidence / "period-q1-0022600001"
    raw = (directory / "summary.json").read_bytes()
    capture = json.loads((directory / "summary-capture.json").read_text())
    if (
        hashlib.sha256(raw).hexdigest() != SUMMARY_SHA
        or capture["sha256"] != SUMMARY_SHA
        or capture["archive_revision"] != REVISION
        or hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != capture["git_blob_sha"]
    ):
        raise ValueError("Independent quarter oracle original differs")
    summary = json.loads(raw)["boxScoreSummary"]
    proof = json.loads((evidence / "schedule-qualification.json").read_text())
    bundle = (evidence / proof["retained_bundle"]).read_bytes()
    if hashlib.sha256(bundle).hexdigest() != proof["bundle_sha256"]:
        raise ValueError("Retained schedule archive differs")
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        raw_schedule = archive.read(proof["original_member"])
    if (
        len(raw_schedule) != BYTES
        or hashlib.sha1(f"blob {len(raw_schedule)}\0".encode() + raw_schedule).hexdigest() != BLOB
    ):
        raise ValueError("Retained schedule original differs")
    schedule = json.loads(raw_schedule)
    games = [
        g
        for day in schedule["leagueSchedule"]["gameDates"]
        for g in day["games"]
        if g["gameId"] == GAME
    ]
    documents, _, _ = retained_stats_documents(evidence)
    finder = _table(documents["finder"], "LeagueGameFinderResults")
    finder = finder.loc[finder.GAME_ID.eq(GAME)].set_index("TEAM_ID")
    if (
        len(games) != 1
        or games[0]["gameStatus"] != 3
        or summary["gameId"] != GAME
        or summary["gameStatus"] != 3
    ):
        raise ValueError("Independent oracle lacks unique final game")
    result = dict(game_id=GAME, summary_sha256=SUMMARY_SHA, teams={})
    for side in ["homeTeam", "awayTeam"]:
        team = summary[side]
        q1 = [p for p in team["periods"] if p["period"] == 1 and p["periodType"] == "REGULAR"]
        if (
            len(q1) != 1
            or team["score"] != finder.loc[team["teamId"], "PTS"]
            or team["score"] != games[0][side]["score"]
            or team["teamId"] != games[0][side]["teamId"]
        ):
            raise ValueError("Independent Q1/full-game score or team oracle contradicts")
        result["teams"][side] = dict(
            team_id=team["teamId"], points=q1[0]["score"], full_points=team["score"]
        )
    return result


def qualify_quarter(traditional, advanced, oracle):
    """Reject zero/full-game responses using independent Q1 scores and clocks."""
    traditional = traditional["boxScoreTraditional"]
    advanced = advanced["boxScoreAdvanced"]
    if traditional["gameId"] != GAME or advanced["gameId"] != GAME:
        raise ValueError("Quarter source game identity mismatch")
    checked = []
    for side in ["homeTeam", "awayTeam"]:
        team, rates, expected = traditional[side], advanced[side], oracle["teams"][side]
        if (
            team["teamId"] != expected["team_id"]
            or rates["teamId"] != expected["team_id"]
            or team["statistics"]["points"] != expected["points"]
            or not math.isclose(
                _parse_minutes_value(team["statistics"]["minutes"]), 60, abs_tol=1e-6
            )
            or not math.isclose(
                _parse_minutes_value(rates["statistics"]["minutes"]), 60, abs_tol=1e-6
            )
        ):
            raise ValueError("Quarter source is zero/full-game/wrong-side or has wrong Q1 clock")
        positive = {
            p["personId"]: p
            for p in team["players"]
            if _parse_minutes_value(p["statistics"]["minutes"]) > 0
        }
        rate_rows = {
            p["personId"]: p
            for p in rates["players"]
            if _parse_minutes_value(p["statistics"]["minutes"]) > 0
        }
        if (
            not positive
            or len({p["personId"] for p in team["players"]}) != len(team["players"])
            or len({p["personId"] for p in rates["players"]}) != len(rates["players"])
            or positive.keys() != rate_rows.keys()
        ):
            raise ValueError("Quarter played identities are missing/duplicate/conflicting")
        if sum(p["statistics"]["points"] for p in positive.values()) != expected[
            "points"
        ] or not math.isclose(
            sum(_parse_minutes_value(p["statistics"]["minutes"]) for p in positive.values()),
            60,
            abs_tol=1 / 60,
        ):
            raise ValueError("Quarter player scores or clock denominator differ")
        for pid, person in positive.items():
            minutes = _parse_minutes_value(person["statistics"]["minutes"])
            stats = rate_rows[pid]["statistics"]
            if not 0 < minutes <= 12 or not math.isclose(
                _parse_minutes_value(stats["minutes"]), minutes, abs_tol=1 / 60
            ):
                raise ValueError("Player clock does not match Q1 sample")
            for field, maximum in [
                ("usagePercentage", 1),
                ("assistPercentage", 1),
                ("reboundPercentage", 1),
                ("turnoverRatio", 100),
            ]:
                value = float(stats[field])
                if not math.isfinite(value) or not 0 <= value <= maximum:
                    raise ValueError("Unqualified quarter advanced rate")
        checked.append(
            dict(
                team_id=expected["team_id"],
                q1_points=expected["points"],
                team_minutes=60,
                played_player_ids=sorted(positive),
            )
        )
    return checked


def probe(output: Path, evidence: Path):
    output.mkdir(parents=True, exist_ok=False)
    report = dict(
        classification="bounded_period_source_probe_not_canonical_or_published",
        game_id=GAME,
        season="2026-27",
        season_type="Regular Season",
        period="Q1",
        production_writes=0,
        source_scope_qualified=False,
        canonical_period_accepted=False,
        captures=[],
    )
    try:
        oracle = load_oracle(evidence)
        report["oracle"] = oracle
        documents = []
        for cls, name in [(BoxScoreTraditionalV3, "traditional"), (BoxScoreAdvancedV3, "advanced")]:
            endpoint = cls(
                game_id=GAME,
                start_period=1,
                end_period=1,
                start_range=0,
                end_range=PERIOD_END_RANGE,
                range_type=PERIOD_RANGE_TYPE,
                get_request=False,
            )
            http = NBAStatsHTTP()
            url = http.base_url.format(endpoint=endpoint.endpoint)
            attempt = dict(
                endpoint=endpoint.endpoint,
                request_url=url,
                parameters=endpoint.parameters,
                started_at=datetime.now(UTC).isoformat(),
                attempts=1,
                http_status=None,
                response_complete=False,
            )
            report["captures"].append(attempt)
            raw = bytearray()
            try:
                with http.get_session().get(
                    url=url,
                    params=sorted(endpoint.parameters.items()),
                    headers=http.headers,
                    timeout=30,
                    stream=True,
                ) as response:
                    attempt["http_status"] = response.status_code
                    for chunk in response.iter_content(65536):
                        remaining = 2_000_000 - len(raw)
                        raw.extend(chunk[:remaining])
                        if len(chunk) > remaining:
                            attempt["response_truncated"] = True
                            raise ValueError("Bounded quarter response exceeds 2MB")
                    attempt["response_complete"] = True
                    response.raise_for_status()
                documents.append(json.loads(raw))
            except Exception as exc:
                attempt["error_type"] = type(exc).__name__
                raise
            finally:
                filename = f"{name}.response.bin"
                if raw:
                    (output / filename).write_bytes(raw)
                attempt.update(
                    finished_at=datetime.now(UTC).isoformat(),
                    response_file=filename if raw else None,
                    response_sha256=hashlib.sha256(raw).hexdigest(),
                    response_bytes=len(raw),
                )
        report["checked_teams"] = qualify_quarter(*documents, oracle)
        report["source_scope_qualified"] = True
        return report
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        raise
    finally:
        (output / "capture-attempt.json").write_text(json.dumps(report, indent=2) + "\n")
