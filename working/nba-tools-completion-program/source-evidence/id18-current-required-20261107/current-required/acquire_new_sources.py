import concurrent.futures, hashlib, json, subprocess, sys, time
from datetime import datetime, UTC
from pathlib import Path
from tools.cloud_nba_archive import fetch_capture

REV = "e3aa21ccfbb58f37b403cf8160193c821cb7546d"
OUT = Path("work/source-qualification/captured")
OUT.mkdir(parents=True, exist_ok=False)
ENDPOINTS = [
    "boxscoretraditionalv3",
    "leaguedashplayerstats",
    "leaguedashteamstats",
    "leaguestandingsv3",
    "commonteamroster",
]
metadata = {}
for ep in ENDPOINTS:
    raw = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/sportsdataverse/hoopR-nba-stats-raw/contents/nba_stats/json/{ep}/2027?ref={REV}",
        ]
    )
    (OUT / f"{ep}-directory.json").write_bytes(raw)
    metadata[ep] = {r["name"]: r for r in json.loads(raw)}
    print(ep, len(metadata[ep]), list(metadata[ep])[:5], flush=True)
jobs = []
for n in range(173, 189):
    jobs.append(("boxscoretraditionalv3", f"00226{n:05d}.json"))
for ep in ["leaguedashplayerstats", "leaguedashteamstats"]:
    jobs.append((ep, "regular-season_advanced_pergame.json"))
for name in metadata["leaguestandingsv3"]:
    if "regular" in name:
        jobs.append(("leaguestandingsv3", name))
# Team rosters are a required source family; collect current30 once, but treat
# them as snapshots, never inferred game-day membership.
for name in metadata["commonteamroster"]:
    if name.endswith(".json"):
        jobs.append(("commonteamroster", name))
records = []
for ep, name in jobs:
    info = metadata[ep][name]
    path = f"nba_stats/json/{ep}/2027/{name}"
    destination = OUT / f"{ep}-{name}"
    started = datetime.now(UTC).isoformat()
    record = fetch_capture(path, destination, REV)
    raw = destination.read_bytes()
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    assert blob == info["sha"] and len(raw) == info["size"]
    records.append(
        dict(
            endpoint=ep,
            file=destination.name,
            path=path,
            git_blob_sha=blob,
            metadata_size=info["size"],
            retrieved_at=datetime.now(UTC).isoformat(),
            started_at=started,
            **record,
        )
    )
    (OUT / "sources.json").write_text(
        json.dumps(
            dict(
                repository="sportsdataverse/hoopR-nba-stats-raw",
                revision=REV,
                classification="required123source_delta_not_completeness_acceptance",
                files=records,
                old107body_requests=0,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )
    print(ep, name, len(raw), flush=True)
    time.sleep(0.25)
