"""Official profile identity evidence, independent of game-day membership/status."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline.player_game_availability_espn import _name, _surname

DERIVATION = "derived:official_profile_identities_v1"


def profile_identity(raw: bytes, player_id: int, expected_name: str) -> str:
    matched = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw.decode("utf-8"), re.S
    )
    if matched is None:
        raise ValueError("Official profile lacks structured identity")
    info = json.loads(matched.group(1))["props"]["pageProps"]["player"]["info"]
    name = f"{info['FIRST_NAME']} {info['LAST_NAME']}"
    if (
        type(info["PERSON_ID"]) is not int
        or info["PERSON_ID"] != player_id
        or _name(name) != _name(expected_name)
        or _name(info["DISPLAY_FIRST_LAST"]) != _name(name)
    ):
        raise ValueError("Official profile identity differs from requested NBA identity")
    return info["DISPLAY_FIRST_LAST"]


def _archive(raw: bytes, directory: Path, suffix: str, source_url: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    path = directory / f"{digest}.{suffix}"
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)
    receipt = dict(
        source_url=source_url,
        retrieved_at=datetime.now(UTC).isoformat(),
        sha256=digest,
        size_bytes=len(raw),
        raw_file=path.name,
    )
    temporary = directory / f"{digest}.receipt.tmp"
    temporary.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    temporary.replace(directory / f"{digest}.receipt.json")
    return digest


def fetch_profile_for_name(name: str, team_id: int, surname: bool, directory: Path):
    from nba_api.stats.static import players

    normalized = _name(name)
    candidates = [
        p
        for p in players.get_players()
        if _name(p["full_name"]) == normalized
        or (surname and _surname(p["full_name"]) == normalized)
    ]
    if len(candidates) != 1:
        raise ValueError("Official profile requires a unique NBA identity candidate")
    candidate = candidates[0]
    ident = candidate["id"]
    url = f"https://www.nba.com/player/{ident}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Oversized official profile")
    digest = _archive(raw, directory, "profile.html", url)
    full_name = profile_identity(raw, ident, candidate["full_name"])
    # team_id comes from the game's report, never from this current profile.
    record = dict(player_id=ident, player_name=full_name, team_id=team_id, profile_sha256=digest)
    frame = pd.DataFrame(
        [dict(team_id=team_id, player_id=ident, player_name=full_name, normalized=_name(full_name))]
    )
    return frame, record


def archive_profile_index(records: list[dict], directory: Path) -> str:
    raw = json.dumps(
        dict(source_kind="official_player_profiles", identities=records), sort_keys=True
    ).encode()
    return _archive(raw, directory, "identity.json", DERIVATION)


def validate_profile_index(payload: dict, directory: Path) -> pd.DataFrame:
    records = payload["identities"]
    if not records:
        raise ValueError("Empty official profile identity index")
    rows = []
    for record in records:
        ident, name, digest = record["player_id"], record["player_name"], record["profile_sha256"]
        if type(ident) is not int or ident <= 0 or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
            raise ValueError("Invalid official profile identity index")
        receipt = json.loads((directory / f"{digest}.receipt.json").read_text())
        raw = (directory / f"{digest}.profile.html").read_bytes()
        if (
            receipt.get("source_url") != f"https://www.nba.com/player/{ident}"
            or receipt.get("sha256") != digest
            or receipt.get("raw_file") != f"{digest}.profile.html"
            or receipt.get("size_bytes") != len(raw)
            or hashlib.sha256(raw).hexdigest() != digest
            or datetime.fromisoformat(receipt["retrieved_at"]).tzinfo is None
        ):
            raise ValueError("Official profile receipt/bytes mismatch")
        full_name = profile_identity(raw, ident, name)
        rows.append(
            dict(
                team_id=record["team_id"],
                player_id=ident,
                player_name=full_name,
                normalized=_name(full_name),
            )
        )
    frame = pd.DataFrame(rows)
    if frame.player_id.duplicated().any():
        raise ValueError("Duplicate official profile identity")
    return frame
