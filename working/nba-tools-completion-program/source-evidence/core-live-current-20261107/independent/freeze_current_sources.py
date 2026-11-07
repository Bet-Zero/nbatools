"""Independent source-only cutoff/participation oracle; no application imports."""

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[5]
WORK = ROOT / "work/core-live-current"
OLD = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
OUTPUT = Path(__file__).resolve().parent


def bound(raw, record):
    capture = record.get("capture", record)
    assert hashlib.sha256(raw).hexdigest() == capture["sha256"]
    assert len(raw) == capture.get("bytes", record.get("size_bytes", record.get("bytes")))
    assert (
        hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        == record["git_blob_sha"]
    )


receipts = json.loads((WORK / "fresh-core-source-receipts.json").read_bytes())
tables = {}
for key in ("playergamelogs", "leaguegamefinder"):
    raw = (WORK / f"{key}-current.json").read_bytes()
    bound(raw, receipts[key])
    doc = json.loads(raw)
    assert doc["parameters"]["SeasonType"] == "Regular Season"
    table = doc["resultSets"][0]
    assert len(table["headers"]) == len(set(table["headers"]))
    tables[key] = [dict(zip(table["headers"], r, strict=True)) for r in table["rowSet"]]
players, teams = tables["playergamelogs"], tables["leaguegamefinder"]
assert {p["SEASON_YEAR"] for p in players} == {"2026-27"}
assert {t["SEASON_ID"] for t in teams} == {"22026"}
assert len(players) == len({(p["GAME_ID"], p["TEAM_ID"], p["PLAYER_ID"]) for p in players}) == 2781
assert len(teams) == len({(p["GAME_ID"], p["TEAM_ID"]) for p in teams}) == 246
fixtures = defaultdict(list)
for team in teams:
    fixtures[team["GAME_ID"]].append(team)
schedule_receipt = json.loads((WORK / "schedule-current-receipt.json").read_bytes())
raw = (WORK / "schedule-current.json").read_bytes()
bound(raw, {**schedule_receipt["source"], "git_blob_sha": schedule_receipt["git_blob_sha"]})
schedule_doc = json.loads(raw)
schedule = {
    game["gameId"]: game
    for day in schedule_doc["leagueSchedule"]["gameDates"]
    for game in day["games"]
    if re.fullmatch(r"00226\d{5}", game["gameId"])
}
assert len(schedule) == 1206
cutoff = datetime.fromisoformat(schedule_receipt["checked_at"]) - timedelta(hours=24)
due = {
    gid
    for gid, game in schedule.items()
    if datetime.fromisoformat(game["gameDateTimeUTC"].replace("Z", "+00:00")) <= cutoff
}
assert due == set(fixtures) == set(schedule_receipt["due_population"]["due_game_ids"])
assert len(due) == 123
for gid, pair in fixtures.items():
    assert len(pair) == 2 and len({p["TEAM_ID"] for p in pair}) == 2
    assert {p["WL"] for p in pair} == {"W", "L"}
    game = schedule[gid]
    assert game["gameStatus"] == 3 and game["gameStatusText"].startswith("Final")
    for row in pair:
        side = "homeTeam" if row["TEAM_ID"] == game["homeTeam"]["teamId"] else "awayTeam"
        assert (row["TEAM_ID"], row["TEAM_ABBREVIATION"], row["PTS"], row["GAME_DATE"]) == (
            game[side]["teamId"],
            game[side]["teamTricode"],
            game[side]["score"],
            game["gameDateEst"][:10],
        )
        other = next(p for p in pair if p["TEAM_ID"] != row["TEAM_ID"])
        assert row["MATCHUP"].split()[-1] == other["TEAM_ABBREVIATION"]
        assert (row["PTS"] > other["PTS"]) == (row["WL"] == "W")
for row in players:
    team = next(t for t in fixtures[row["GAME_ID"]] if t["TEAM_ID"] == row["TEAM_ID"])
    assert (row["GAME_DATE"][:10], row["TEAM_ABBREVIATION"], row["WL"]) == (
        team["GAME_DATE"],
        team["TEAM_ABBREVIATION"],
        team["WL"],
    )
with ZipFile(OLD / "official-gamebooks-20261105/normalized-snapshot.zip") as archive:
    old_games = list(
        csv.DictReader(
            io.StringIO(archive.read("data/raw/games/2026-27_regular_season.csv").decode())
        )
    )
old_ids = {str(int(g["game_id"])).zfill(10) for g in old_games}
assert len(old_ids) == 107 and old_ids <= due

pair_docs, source_bindings = {}, []
metadata = json.loads((OLD / "readiness-reassessment/sources.json").read_bytes())
for gid in ("0022600106", "0022600143"):
    name = f"boxscoretraditionalv3_{gid}.json"
    raw = (OLD / "readiness-reassessment/sources" / name).read_bytes()
    record = metadata["files"][name]
    bound(raw, record)
    pair_docs[gid, "traditional"] = json.loads(raw)["boxScoreTraditional"]
    source_bindings.append(
        {**record, "game_id": gid, "kind": "traditional", "revision": metadata["revision"]}
    )
archive_inputs = [
    (
        "partial-capture-20261103/summary-oracles.zip",
        "sources.json",
        [
            ("0022600106", "summary", "0022600106.json"),
        ],
    ),
    (
        "recovery-capture-20261104/supplementary-sources.zip",
        "summaries/sources.json",
        [
            ("0022600143", "summary", "summaries/0022600143.json"),
        ],
    ),
    (
        "period-milestone/archive-refresh.zip",
        "new-games-metadata.json",
        [
            ("0022600148", "summary", "boxscoresummaryv3_0022600148.json"),
            ("0022600148", "traditional", "boxscoretraditionalv3_0022600148.json"),
        ],
    ),
]
for path, metadata_name, entries in archive_inputs:
    with ZipFile(OLD / path) as archive:
        metadata = json.loads(archive.read(metadata_name))
        for gid, kind, member in entries:
            raw = archive.read(member)
            record = next(r for r in metadata["files"] if r.get("file") == member.split("/")[-1])
            bound(raw, record)
            pair_docs[gid, kind] = json.loads(raw)[
                "boxScoreSummary" if kind == "summary" else "boxScoreTraditional"
            ]
            source_bindings.append(
                dict(
                    game_id=gid,
                    kind=kind,
                    revision=metadata["revision"],
                    location=str((OLD / path).relative_to(ROOT)) + "!" + member,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    git_blob_sha=record["git_blob_sha"],
                )
            )
explicit = {}
for gid, pid, tid in [
    ("0022600106", 2544, 1610612755),
    ("0022600148", 2544, 1610612755),
    ("0022600143", 1629029, 1610612747),
]:
    traditional, summary = pair_docs[gid, "traditional"], pair_docs[gid, "summary"]
    game = schedule[gid]
    assert traditional["gameId"] == summary["gameId"] == gid
    assert summary["gameStatus"] == 3 and summary["gameEt"][:10] == game["gameDateEst"][:10]
    for side in ("homeTeam", "awayTeam"):
        assert traditional[side]["teamId"] == summary[side]["teamId"] == game[side]["teamId"]
        assert (
            traditional[side]["statistics"]["points"]
            == summary[side]["score"]
            == game[side]["score"]
        )
        for player in traditional[side]["players"]:
            minutes = player["statistics"]["minutes"]
            assert not minutes or (
                re.fullmatch(r"\d+:\d\d", minutes) and int(minutes.split(":")[1]) < 60
            )
    side = "homeTeam" if summary["homeTeamId"] == tid else "awayTeam"
    trad = [p for p in traditional[side]["players"] if p["personId"] == pid]
    inactive = [p for p in summary[side]["inactives"] if p["personId"] == pid]
    assert not any(p["MIN"] > 0 for p in players if p["GAME_ID"] == gid and p["PLAYER_ID"] == pid)
    if gid == "0022600106":
        assert len(trad) == 1 and trad[0]["comment"] == "Inactive - Injury/Illness"
        assert trad[0]["statistics"]["minutes"] == ""
        basis = "Traditional explicit Inactive - Injury/Illness under PHI"
    else:
        assert len(inactive) == 1 and not trad
        basis = "Summary explicit inactive under " + game[side]["teamTricode"]
    explicit[gid, pid, tid] = basis

populations = {}
for label, pid, tid in [
    ("LeBron_PHI", 2544, 1610612755),
    ("Luka_LAL", 1629029, 1610612747),
    ("Reaves_LAL", 1630559, 1610612747),
    ("Davis_observed_WAS", 203076, 1610612764),
    ("Tatum_observed_BOS", 1628369, 1610612738),
]:
    own = sorted((t for t in teams if t["TEAM_ID"] == tid), key=lambda t: t["GAME_ID"])
    positive = {
        p["GAME_ID"]
        for p in players
        if p["PLAYER_ID"] == pid and p["TEAM_ID"] == tid and p["MIN"] > 0
    }
    states = []
    for game in own:
        gid, key = game["GAME_ID"], (game["GAME_ID"], pid, tid)
        state = "played" if gid in positive else "did_not_play" if key in explicit else "unknown"
        states.append(
            dict(
                game_id=gid,
                game_date=game["GAME_DATE"],
                team_id=tid,
                team_abbr=game["TEAM_ABBREVIATION"],
                opponent=game["MATCHUP"].split()[-1],
                is_home=" vs. " in game["MATCHUP"],
                wl=game["WL"],
                pts=game["PTS"],
                state=state,
                basis="positive source MIN" if state == "played" else explicit.get(key),
            )
        )
    groups = {}
    for polarity, state in (("with", "played"), ("without", "did_not_play")):
        selected = [g for g in states if g["state"] == state]
        groups[polarity] = dict(
            game_ids=[g["game_id"] for g in selected],
            games=len(selected),
            wins=sum(g["wl"] == "W" for g in selected),
            losses=sum(g["wl"] == "L" for g in selected),
            team_points=sum(g["pts"] for g in selected),
            ppg=sum(g["pts"] for g in selected) / len(selected) if selected else None,
        )
    populations[label] = dict(
        player_id=pid,
        team_id=tid,
        games=states,
        expected_observed_scope=groups,
        coverage={
            state: sum(g["state"] == state for g in states)
            for state in ("played", "did_not_play", "unknown")
        },
    )
assert populations["LeBron_PHI"]["coverage"] == dict(played=7, did_not_play=2, unknown=0)
assert populations["Luka_LAL"]["coverage"] == dict(played=8, did_not_play=1, unknown=0)
assert populations["Reaves_LAL"]["coverage"] == dict(played=9, did_not_play=0, unknown=0)
result = dict(
    classification=(
        "Independent source-only current cutoff oracle; importer/canonical "
        "preservation/consumer qualification pending"
    ),
    revision=schedule_receipt["revision"],
    checked_at=schedule_receipt["checked_at"],
    source_document_time=schedule_doc["meta"]["time"],
    source_receipts=receipts,
    schedule_sha256=schedule_receipt["source"]["sha256"],
    exact_due_game_ids=sorted(due),
    new_due_ids_beyond_retained107=sorted(due - old_ids),
    source_pair_bindings=source_bindings,
    populations=populations,
    LAL_vs_BOS_or_NYK_parent_game_ids=[
        t["GAME_ID"]
        for t in teams
        if t["TEAM_ABBREVIATION"] == "LAL" and t["MATCHUP"].split()[-1] in ("BOS", "NYK")
    ],
    reported_Rest=dict(
        player_id=1629029,
        unresolved_game_ids=["0022600143"],
        reason=(
            "Explicit inactive state lacks source-reported Rest cause; "
            "no Rest zero/positive accepted"
        ),
    ),
    membership_limits=(
        "Observed LeBronPHI/DavisWAS rows do not establish dated nonmembership "
        "for explicit LAL/PHI cross-club conditions."
    ),
    preservation_limits=(
        "Do not overwrite accepted prior107canonical corrections. "
        "Full11raw/5processed/currentfreshness/release acceptance is separate; "
        "preserve484known old-scope unknown rates, with new16period "
        "universe/unassessed fields unknown."
    ),
)
(OUTPUT / "current-population-freeze.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({label: value["coverage"] for label, value in populations.items()}, indent=2))
