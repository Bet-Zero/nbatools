"""Qualify the two unresolved source games independently of the application."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUTPUT = Path(__file__).resolve().parent
SOURCE = OUTPUT.parent / "pair-sources"
TEAM, PLAYER = 1610612760, 201142
oracle = json.loads((OUTPUT / "source-log-oracle.json").read_text())
receipts = json.loads((SOURCE / "sources.json").read_text())
assert receipts["revision"] == "2e44b7c039f104bc6b41a1de494411e83a03714e"
population = {r["game_id"]: r for r in oracle["population"]}


def read(endpoint, gid):
    name = f"{endpoint}_{gid}.json"
    raw = (SOURCE / "sources" / name).read_bytes()
    r = receipts["files"][name]
    assert len(raw) == r["size_bytes"]
    assert hashlib.sha256(raw).hexdigest() == r["sha256"]
    assert (
        hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        == r["git_blob_sha"]
    )
    assert r["url"].endswith(f"/{endpoint}/2008/{gid}.json")
    return json.loads(raw)


def table(doc, name):
    matches = [t for t in doc["resultSets"] if t["name"] == name]
    assert len(matches) == 1
    t = matches[0]
    assert len(t["headers"]) == len(set(t["headers"]))
    return [dict(zip(t["headers"], r, strict=True)) for r in t["rowSet"]]


qualified = []
for gid in oracle["unresolved_game_ids"]:
    traditional = read("boxscoretraditionalv3", gid)["boxScoreTraditional"]
    summary = read("boxscoresummaryv2", gid)
    gs = table(summary, "GameSummary")
    assert len(gs) == 1
    gs = gs[0]
    assert gs["GAME_ID"] == traditional["gameId"] == gid
    assert gs["GAME_DATE_EST"][:10] == population[gid]["game_date"]
    assert gs["GAME_STATUS_ID"] == 3 and gs["GAME_STATUS_TEXT"] == "Final"
    assert int(gs["SEASON"]) == 2007
    assert (gs["HOME_TEAM_ID"], gs["VISITOR_TEAM_ID"]) == (
        traditional["homeTeamId"],
        traditional["awayTeamId"],
    )
    lines = table(summary, "LineScore")
    assert len(lines) == 2
    by_team = {r["TEAM_ID"]: r for r in lines}
    assert set(by_team) == {gs["HOME_TEAM_ID"], gs["VISITOR_TEAM_ID"]}
    participants, target = [], []
    for side in ("homeTeam", "awayTeam"):
        team = traditional[side]
        line = by_team[team["teamId"]]
        assert line["GAME_ID"] == gid and line["GAME_DATE_EST"][:10] == population[gid]["game_date"]
        assert line["TEAM_ABBREVIATION"] == team["teamTricode"]
        assert line["PTS"] == team["statistics"]["points"]
        assert team["statistics"]["minutes"] == "240:00"
        assert sum(p["statistics"]["points"] for p in team["players"]) == line["PTS"]
        ids = [p["personId"] for p in team["players"]]
        assert len(ids) == len(set(ids))
        for p in team["players"]:
            m = p["statistics"]["minutes"]
            if m:
                assert re.fullmatch(r"\d+:\d{2}", m) and int(m.split(":")[1]) < 60
                assert (
                    sum(int(x) * scale for x, scale in zip(m.split(":"), (60, 1), strict=True)) > 0
                )
                participants.append((team["teamId"], p["personId"]))
            if p["personId"] == PLAYER:
                target.append((team["teamId"], p))
    own = by_team[TEAM]
    assert (
        own["TEAM_ABBREVIATION"] == "SEA"
        and own["TEAM_CITY_NAME"] == "Seattle"
        and own["TEAM_NICKNAME"] == "SuperSonics"
    )
    assert own["PTS"] == population[gid]["pts"]
    opposite = next(row for row in lines if row["TEAM_ID"] != TEAM)
    assert (own["PTS"] > opposite["PTS"]) == (population[gid]["wl"] == "W")
    assert (TEAM, PLAYER) not in participants
    inactive = [r for r in table(summary, "InactivePlayers") if r["PLAYER_ID"] == PLAYER]
    if gid == "0020700456":
        assert len(target) == 1 and target[0][0] == TEAM
        p = target[0][1]
        assert p["firstName"] == "Kevin" and p["familyName"] == "Durant"
        assert p["statistics"]["minutes"] == ""
        assert p["comment"] == "DND - Sprained left index finger"
        assert not inactive
        basis = {
            "source": "TraditionalV3 explicit DND row under Seattle homeTeam",
            "literal_comment": p["comment"],
        }
    else:
        assert gid == "0020700788" and not target and len(inactive) == 1
        p = inactive[0]
        assert p["TEAM_ID"] == TEAM and p["TEAM_ABBREVIATION"] == "SEA"
        assert p["FIRST_NAME"] == "Kevin" and p["LAST_NAME"] == "Durant"
        assert p["TEAM_CITY"] == "Seattle" and p["TEAM_NAME"] == "SuperSonics"
        basis = {"source": "SummaryV2 explicit InactivePlayers row with Seattle team identity"}
    population[gid]["state"] = "did_not_play"
    population[gid]["state_basis"] = basis
    qualified.append(
        {
            "game_id": gid,
            "game_date": population[gid]["game_date"],
            "home_team_id": gs["HOME_TEAM_ID"],
            "away_team_id": gs["VISITOR_TEAM_ID"],
            "scores": {str(r["TEAM_ID"]): r["PTS"] for r in lines},
            "player_id": PLAYER,
            "team_id": TEAM,
            "state": "did_not_play",
            "membership_basis": basis,
            "qualified_played_rows": len(participants),
        }
    )

assert len(population) == 82
assert len([r for r in population.values() if r["state"] == "played"]) == 80
assert len([r for r in population.values() if r["state"] == "did_not_play"]) == 2
assert not any(r["state"] == "unknown" for r in population.values())
groups = {}
for label, state in (("with", "played"), ("without", "did_not_play")):
    selected = [r for r in population.values() if r["state"] == state]
    groups[label] = {
        "game_ids": sorted(r["game_id"] for r in selected),
        "games": len(selected),
        "wins": sum(r["wl"] == "W" for r in selected),
        "losses": sum(r["wl"] == "L" for r in selected),
        "points": sum(r["pts"] for r in selected),
        "ppg": sum(r["pts"] for r in selected) / len(selected),
    }
result = {
    "classification": (
        "independent original-source full82 Durant/Seattle participation oracle; "
        "canonical pinned comparison and app execution pending"
    ),
    "season": "2007-08",
    "season_type": "Regular Season",
    "team_id": TEAM,
    "historical_team": "Seattle SuperSonics",
    "team_abbr": "SEA",
    "player_id": PLAYER,
    "source_log_sha256": hashlib.sha256(
        (OUTPUT / "source-log-oracle.json").read_bytes()
    ).hexdigest(),
    "pair_receipts": receipts,
    "explicit_nonparticipants": qualified,
    "coverage": {"eligible": 82, "played": 80, "did_not_play": 2, "nonmember": 0, "unknown": 0},
    "expected": groups,
    "population": sorted(population.values(), key=lambda r: r["game_id"]),
    "limits": [
        (
            "Historical archive capture; original NBA capture time unknown; no freshness "
            "or current-season claim"
        ),
        (
            "Source medical wording retained literally but only generic whole-game "
            "nonparticipation is accepted"
        ),
        (
            "Same-game Seattle association supplied directly for both nonparticipants, "
            "without roster-snapshot or tenure-gap inference"
        ),
        (
            "No independent upstream origin asserted; independent checker arithmetic is "
            "separate from capture provenance"
        ),
        (
            "Canonical pinned manifest/game/schedule/team/player comparisons and "
            "exact-candidate required execution remain pending"
        ),
        (
            "Traditional0456 team turnovers13 versus season log14 is outside requested "
            "record/PTS/participation qualification; neither source is silently "
            "corrected; no full-stat or exact-clock acceptance"
        ),
    ],
}
(OUTPUT / "source-qualified-oracle.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"coverage": result["coverage"], "expected": result["expected"]}, indent=2))
