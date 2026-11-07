"""Independent source oracle; standard library only, never app calculations."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[5]
OUTPUT = Path(__file__).resolve().parent
ORIGINALS = OUTPUT.parent / "originals.zip"
TEAM, PLAYER = 1610612760, 201142


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read_table(name):
    with ZipFile(ORIGINALS) as archive:
        raw = archive.read("sources/" + name)
    receipt = next(r for r in receipts if r["url"].endswith("/" + name))
    assert len(raw) == receipt["bytes"] and sha(raw) == receipt["sha256"]
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert blob == receipt["git_blob_sha"]
    doc = json.loads(raw)
    assert doc["resource"] == "leaguegamelog"
    assert doc["parameters"]["SeasonType"] == "Regular Season"
    assert len(doc["resultSets"]) == 1
    table = doc["resultSets"][0]
    assert table["name"] == "LeagueGameLog"
    assert len(table["headers"]) == len(set(table["headers"]))
    rows = [dict(zip(table["headers"], row, strict=True)) for row in table["rowSet"]]
    assert {r["SEASON_ID"] for r in rows} == {"22007"}
    assert all(len(r["GAME_ID"]) == 10 and r["GAME_ID"].startswith("00207") for r in rows)
    return rows


with ZipFile(ORIGINALS) as archive:
    receipts = json.loads(archive.read("log-source-receipts.json"))
teams, players = read_table("regular-season.json"), read_table("regular-season_p.json")
assert len(teams) == 2460
assert len({(r["GAME_ID"], r["TEAM_ID"]) for r in teams}) == 2460
assert len({(r["GAME_ID"], r["TEAM_ID"], r["PLAYER_ID"]) for r in players}) == len(players)
assert len({r["TEAM_ID"] for r in teams}) == 30
assert set(Counter(r["TEAM_ID"] for r in teams).values()) == {82}
fixtures = defaultdict(list)
for row in teams:
    fixtures[row["GAME_ID"]].append(row)
assert len(fixtures) == 1230
for pair in fixtures.values():
    assert len(pair) == 2 and len({r["TEAM_ID"] for r in pair}) == 2
    assert len({r["GAME_DATE"] for r in pair}) == 1
    assert {r["WL"] for r in pair} == {"W", "L"}
    a, b = pair
    assert (a["PTS"] > b["PTS"]) == (a["WL"] == "W")
    assert a["PLUS_MINUS"] == -b["PLUS_MINUS"] == a["PTS"] - b["PTS"]
    assert a["MATCHUP"].split()[-1] == b["TEAM_ABBREVIATION"]
    assert b["MATCHUP"].split()[-1] == a["TEAM_ABBREVIATION"]
    assert {r["MATCHUP"].split()[1] for r in pair} == {"vs.", "@"}
population = sorted((r for r in teams if r["TEAM_ID"] == TEAM), key=lambda r: r["GAME_ID"])
assert len(population) == 82
assert {r["TEAM_ABBREVIATION"] for r in population} == {"SEA"}
assert {r["TEAM_NAME"] for r in population} == {"Seattle SuperSonics"}
durant = [r for r in players if r["PLAYER_ID"] == PLAYER]
assert len(durant) == 80
assert {r["PLAYER_NAME"] for r in durant} == {"Kevin Durant"}
assert {r["TEAM_ID"] for r in durant} == {TEAM}
assert {r["TEAM_ABBREVIATION"] for r in durant} == {"SEA"}
assert all(isinstance(r["MIN"], (int, float)) and r["MIN"] > 0 for r in durant)
by_id = {r["GAME_ID"]: r for r in population}
for p in durant:
    t = by_id[p["GAME_ID"]]
    assert all(
        p[k] == t[k]
        for k in (
            "SEASON_ID",
            "TEAM_ID",
            "TEAM_ABBREVIATION",
            "TEAM_NAME",
            "GAME_DATE",
            "MATCHUP",
            "WL",
        )
    )
played = {r["GAME_ID"] for r in durant}
missing = set(by_id) - played
assert missing == {"0020700456", "0020700788"}
plan = []
for endpoint in ("boxscoretraditionalv3", "boxscoresummaryv2"):
    with ZipFile(ORIGINALS) as archive:
        tree = json.loads(archive.read(f"{endpoint}-2008.json"))
    assert tree.get("truncated") is False
    for gid in sorted(missing):
        row = next(r for r in tree["tree"] if r["path"] == gid + ".json")
        assert row["type"] == "blob" and 0 < row["size"] < 2_000_000
        plan.append(
            {"endpoint": endpoint, "game_id": gid, "git_blob_sha": row["sha"], "bytes": row["size"]}
        )
result = {
    "classification": "independent archived log oracle; unresolved games are unknown, not DNP",
    "source_receipts": receipts,
    "season": "2007-08",
    "season_type": "Regular Season",
    "team_id": TEAM,
    "player_id": PLAYER,
    "qualified_log_population": {
        "games": 82,
        "wins": sum(r["WL"] == "W" for r in population),
        "losses": sum(r["WL"] == "L" for r in population),
        "points": sum(r["PTS"] for r in population),
    },
    "played": {
        "games": len(played),
        "game_ids": sorted(played),
        "wins": sum(by_id[g]["WL"] == "W" for g in played),
        "losses": sum(by_id[g]["WL"] == "L" for g in played),
        "team_points": sum(by_id[g]["PTS"] for g in played),
    },
    "population": [
        {
            "game_id": r["GAME_ID"],
            "game_date": r["GAME_DATE"],
            "team_id": r["TEAM_ID"],
            "team_abbr": r["TEAM_ABBREVIATION"],
            "matchup": r["MATCHUP"],
            "wl": r["WL"],
            "pts": r["PTS"],
            "state": "played" if r["GAME_ID"] in played else "unknown",
        }
        for r in population
    ],
    "unresolved_game_ids": sorted(missing),
    "smallest_remaining_source_plan": plan,
    "remaining_required": (
        "Original explicit same-game nonparticipation and Seattle association for "
        "each unresolved game; compare exact population and source facts with pinned "
        "canonical games/schedule/team/player before acceptance."
    ),
    "absence_result": None,
}
(OUTPUT / "source-log-oracle.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        {
            k: result[k]
            for k in ("qualified_log_population", "played", "unresolved_game_ids", "absence_result")
        },
        indent=2,
    )
)
