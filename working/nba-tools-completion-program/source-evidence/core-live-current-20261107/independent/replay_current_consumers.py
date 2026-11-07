"""Independent local replay of frozen current scope; no public network access."""

import asyncio
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import httpx

from nbatools.api_handlers import natural_query_payload
from nbatools.development_data import development_snapshot
from tools.development_query import create_app

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
ARCHIVE_SHA = "eb60f64204a089d0d5a9083496aa44e172e3fe511b71d7980a0649e0e3778c17"
MANIFEST_SHA = "373e0b5c1e53f7e60dbfdb2c2799bf7b661f439fbd5e6662f9d6dcedadf5fe95"
QUESTIONS = [
    "How many games has LeBron James missed this season?",
    "How many home games has LeBron James missed this season?",
    "Lakers win-loss record when Luka Doncic did not play this season",
    "Lakers record with Austin Reaves not playing this season",
    "Lakers record against either Celtics or Knicks without Tatum this season",
    "How many games did LeBron James miss?",
    "Lakers record with Luka Doncic",
    "Lakers record when Luka Doncic rests",
    "Lakers record without Anthony Davis",
]


def verify(payload, index):
    assert payload["query"] == QUESTIONS[index]
    result = payload["result"]
    metadata, sections = result["metadata"], result["sections"]
    assert metadata["season"] == "2026-27"
    quality = metadata["data_quality"]
    assert quality["state"] == "provisional" and quality["manifest_sha256"] == MANIFEST_SHA
    assert not quality["numerical_acceptance"] and not quality["production_accepted"]
    if index in (0, 1, 5):
        ids = [int(row["game_id"]) for row in sections["finder"]]
        expected = [22600106] if index == 1 else [22600106, 22600148]
        assert len(ids) == len(set(ids)) == sections["count"][0]["count"] == len(expected)
        assert set(ids) == set(expected) and metadata["team"] == "PHI"
        assert metadata["without_player"] == "LeBron James"
    elif index in (2, 6):
        freeze = json.loads((HERE / "current-population-freeze.json").read_bytes())
        expected = freeze["populations"]["Luka_LAL"]["expected_observed_scope"][
            "without" if index == 2 else "with"
        ]
        rows = sections["game_log"]
        ids = [int(row["game_id"]) for row in rows]
        assert len(ids) == len(set(ids)) == expected["games"]
        assert set(ids) == {int(gid) for gid in expected["game_ids"]}
        summary = sections["summary"][0]
        assert [summary[k] for k in ("games", "wins", "losses", "pts_avg")] == [
            expected[k] for k in ("games", "wins", "losses", "ppg")
        ]
        assert all(row["team_abbr"] == "LAL" for row in rows)
        assert metadata["without_player" if index == 2 else "with_player"] == "Luka Doncic"
    else:
        assert not sections
        reasons = {3: "no_match", 4: "no_match", 7: "no_data", 8: "unsupported"}
        assert payload["result_reason"] == reasons[index]
        if index == 4:
            assert metadata["opponent"] == "BOS, NYK"
            assert metadata["without_player"] == "Jayson Tatum"


async def replay(root):
    with development_snapshot(root, MANIFEST_SHA):
        direct = [natural_query_payload(query) for query in QUESTIONS]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(root, MANIFEST_SHA)),
        base_url="http://127.0.0.1",
    ) as client:
        records = []
        for index, query in enumerate(QUESTIONS):
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            payload = response.json()
            verify(direct[index], index)
            verify(payload, index)
            records.append(dict(query=query, structured=direct[index], http=payload))
    return records


archive = EVIDENCE / "current123-provisional.zip"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
with TemporaryDirectory(prefix="nbatools-independent-current-consumers-") as temporary:
    root = Path(temporary)
    with ZipFile(archive) as zipped:
        for member in zipped.namelist():
            path = Path(member)
            assert not path.is_absolute() and ".." not in path.parts and "\\" not in member
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(member))
    records = asyncio.run(replay(root))
(HERE / "current-consumer-independent.json").write_text(
    json.dumps(
        dict(
            classification=(
                "local targeted source-qualified facts; "
                "whole snapshot and deployed acceptance false"
            ),
            snapshot_archive_sha256=ARCHIVE_SHA,
            manifest_sha256=MANIFEST_SHA,
            records=records,
        ),
        indent=2,
        default=str,
    ) + "\n"
)
print(f"Verified {len(records)} structured and {len(records)} loopback HTTP cases")
