"""Standalone acquisition only: one NBA game/Q1, two public source requests.

Run with Python and the existing nba_api client; no NBA Tools checkout/imports.
This does not write production, retry, collect a season, or accept a dataset.
Failed attempts also retain a data-only ZIP for cloud diagnosis. No credentials
or request/response headers are written into the collection.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import zipfile
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

GAME = "0022600001"
PARAMETERS = dict(
    GameID=GAME, StartPeriod=1, EndPeriod=1, RangeType=1, StartRange=0, EndRange=28800
)
ORACLE = {"homeTeam": (1610612765, 27, 121), "awayTeam": (1610612738, 28, 113)}
SUMMARY_SHA = "7e61162d1ec001d5235a8dd2125a654dfad30887db90e0d0c58621859383cf5a"
REQUEST = dict(
    schema_version=1,
    status="collection_requirement_not_publication_approval",
    base_generation="availability-lebron-season-v1-20261031",
    base_manifest_sha256="3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3",
    authorization="standing bounded public NBA collection/staging; no publication",
    season="2026-27",
    season_type="Regular Season",
    game_id=GAME,
    period="Q1",
    endpoints=["boxscoretraditionalv3", "boxscoreadvancedv3"],
    parameters=PARAMETERS,
    oracle_summary_sha256=SUMMARY_SHA,
    maximum_requests=2,
    attempts_per_endpoint=1,
    timeout_seconds=30,
    response_limit_bytes=2_000_000,
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _minutes(value):
    if value is None or value == "":
        return 0.0
    match = re.fullmatch(r"(\d+):(\d+(?:\.\d+)?)", str(value))
    if match:
        if float(match[2]) >= 60:
            raise ValueError("Invalid source seconds")
        result = int(match[1]) + float(match[2]) / 60
    else:
        result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Invalid source minutes")
    return result


def qualify(traditional, advanced):
    """The oracle was independently bound to Summary, Finder and Schedule."""
    boxes = [traditional["boxScoreTraditional"], advanced["boxScoreAdvanced"]]
    if any(box["gameId"] != GAME for box in boxes):
        raise ValueError("Wrong source game")
    for box in boxes:
        identities = [p["personId"] for side in ORACLE for p in box[side]["players"]]
        if len(identities) != len(set(identities)) or any(
            type(pid) is not int or pid <= 0 for pid in identities
        ):
            raise ValueError("Invalid/duplicate same-game NBA player identity")
    checked = []
    for side, (team_id, points, _) in ORACLE.items():
        team, rates = [box[side] for box in boxes]
        if (
            team["teamId"] != team_id
            or rates["teamId"] != team_id
            or team["statistics"]["points"] != points
            or any(
                not math.isclose(_minutes(t["statistics"]["minutes"]), 60, abs_tol=1e-6)
                for t in [team, rates]
            )
        ):
            raise ValueError("Zero/full-game/wrong-side response or wrong Q1 score/clock")
        rows = []
        for source_team in [team, rates]:
            listed = source_team["players"]
            if len({p["personId"] for p in listed}) != len(listed):
                raise ValueError("Duplicate player source identity")
            rows.append(
                {
                    p["personId"]: p["statistics"]
                    for p in listed
                    if _minutes(p["statistics"]["minutes"]) > 0
                }
            )
        players, advanced_players = rows
        if not players or players.keys() != advanced_players.keys():
            raise ValueError("Played player identities differ between sources")
        if (
            any(
                type(p["points"]) is not int or not 0 <= p["points"] <= points
                for p in players.values()
            )
            or sum(p["points"] for p in players.values()) != points
            or not math.isclose(
                sum(_minutes(p["minutes"]) for p in players.values()), 60, abs_tol=1 / 60
            )
        ):
            raise ValueError("Player Q1 scores/clock do not reconcile")
        for pid, player in players.items():
            minutes = _minutes(player["minutes"])
            stats = advanced_players[pid]
            if not 0 < minutes <= 12 or not math.isclose(
                _minutes(stats["minutes"]), minutes, abs_tol=1 / 60
            ):
                raise ValueError("Wrong Q1 player clock")
            for field, ceiling in [
                ("usagePercentage", 1),
                ("assistPercentage", 1),
                ("reboundPercentage", 1),
                ("turnoverRatio", 100),
            ]:
                value = float(stats[field])
                if not math.isfinite(value) or not 0 <= value <= ceiling:
                    raise ValueError("Invalid or missing quarter advanced rate")
        if not math.isclose(
            sum(_minutes(p["minutes"]) for p in advanced_players.values()), 60, abs_tol=1 / 60
        ):
            raise ValueError("Advanced quarter player clock denominator differs")
        if not any(float(p["usagePercentage"]) > 0 for p in advanced_players.values()):
            raise ValueError("All-zero advanced usage contradicts nonzero quarter scoring")
        checked.append(
            dict(team_id=team_id, points=points, team_minutes=60, player_ids=sorted(players))
        )
    return checked


def _clients():
    # get_request=False prevents constructor requests; use the installed
    # library's standard session and headers without alternate hosts/overrides.
    from nba_api.stats.endpoints import BoxScoreAdvancedV3, BoxScoreTraditionalV3
    from nba_api.stats.library.http import NBAStatsHTTP

    for cls in [BoxScoreTraditionalV3, BoxScoreAdvancedV3]:
        yield (
            cls(
                game_id=GAME,
                start_period=1,
                end_period=1,
                start_range=0,
                end_range=28800,
                range_type=1,
                get_request=False,
            ),
            NBAStatsHTTP(),
        )


def _bundle(output):
    """The existing collection_bundle data-only protocol and20MB/100MB/2000 bounds."""
    files = {}
    total = 0
    for path in sorted([output / "acquisition.json", *(output / "sources").glob("*.json")]):
        raw = path.read_bytes()
        total += len(raw)
        files[path.relative_to(output).as_posix()] = dict(bytes=len(raw), sha256=_sha(raw))
    if total > 100_000_000 or len(files) > 2000:
        raise ValueError("Collection exceeds reviewed data-only limits")
    manifest = dict(
        schema_version=1,
        classification="unvalidated_development_collection",
        request_sha256=_sha(json.dumps(REQUEST, sort_keys=True, separators=(",", ":")).encode()),
        request=REQUEST,
        files=files,
        production_writes=0,
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(output / name, name)
        archive.writestr("collection-manifest.json", json.dumps(manifest, indent=2) + "\n")
    raw = buffer.getvalue()
    if len(raw) > 20_000_000:
        raise ValueError("Collection exceeds20MB upload bound")
    with (output / "collection.zip").open("xb") as handle:
        handle.write(raw)


def collect(output: Path):
    output.mkdir(parents=True, exist_ok=False)
    (output / "sources").mkdir()
    report = dict(
        classification="unvalidated_laptop_source_capture_not_publication",
        source="NBA Stats V3",
        captured_at=datetime.now(UTC).isoformat(),
        parameters=PARAMETERS,
        request=REQUEST,
        oracle=ORACLE,
        original_oracle_sha256=SUMMARY_SHA,
        production_writes=0,
        canonical_period_accepted=False,
        source_scope_qualified=False,
        attempts=[],
    )
    try:
        report["nba_api_version"] = version("nba_api")
        documents = []
        for endpoint, http in _clients():
            if endpoint.parameters != PARAMETERS or endpoint.endpoint not in REQUEST["endpoints"]:
                raise ValueError("Installed NBA API request differs from fixed reviewed parameters")
            url = http.base_url.format(endpoint=endpoint.endpoint)
            if url != f"https://stats.nba.com/stats/{endpoint.endpoint}":
                raise ValueError("Unexpected source host")
            attempt = dict(
                endpoint=endpoint.endpoint,
                url=url,
                parameters=endpoint.parameters,
                started_at=datetime.now(UTC).isoformat(),
                attempts=1,
                timeout_seconds=30,
                http_status=None,
                response_complete=False,
                response_bytes=0,
            )
            report["attempts"].append(attempt)
            raw = bytearray()
            try:
                with http.get_session().get(
                    url=url,
                    params=sorted(endpoint.parameters.items()),
                    headers=http.headers,
                    timeout=30,
                    stream=True,
                    allow_redirects=False,
                ) as response:
                    attempt["http_status"] = response.status_code
                    for chunk in response.iter_content(65536):
                        remaining = 2_000_000 - len(raw)
                        raw.extend(chunk[:remaining])
                        if len(chunk) > remaining:
                            attempt["response_truncated"] = True
                            raise ValueError("Response exceeds2MB retained bound")
                    attempt["response_complete"] = True
                    response.raise_for_status()
                documents.append(json.loads(raw))
            except Exception as exc:
                attempt["error_type"] = type(exc).__name__
                raise
            finally:
                path = output / "sources" / f"{endpoint.endpoint}_{GAME}_q1.json"
                if raw:
                    # Original bytes even on HTTP/JSON failure; suffix is the
                    # container's source slot, never proof of JSON/scope validity.
                    path.write_bytes(raw)
                attempt.update(
                    finished_at=datetime.now(UTC).isoformat(),
                    response_bytes=len(raw),
                    response_sha256=_sha(raw),
                    source_file=path.relative_to(output).as_posix() if raw else None,
                )
        report["checked_teams"] = qualify(*documents)
        report["source_scope_qualified"] = True
        return report
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        raise
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        payload = json.dumps(report, indent=2) + "\n"
        (output / "acquisition.json").write_text(payload)
        (output / "sources/capture-attempt.json").write_text(payload)
        _bundle(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New acquisition directory; never reused"
    )
    args = parser.parse_args()
    collect(args.output)
    print(
        f"Source capture retained at {args.output / 'collection.zip'}; "
        "cloud qualification required."
    )
