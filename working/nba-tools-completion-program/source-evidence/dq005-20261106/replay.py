"""Offline DQ-005 diagnosis, not a correction producer or qualification gate.

Run from the repository root with .venv/bin/python <this file>.
Original bytes are authenticated before parsing. No network or application edits.
"""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from nbatools.commands.pipeline.pull_team_game_stats import add_opponent_info, normalize_columns
from nbatools.commands.source_invariants import canonicalize_team_game_pairs

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / "multi-team-absence-20261106/archive-originals.zip"
ZIP_SHA = "6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1"
PIN = "2e44b7c039f104bc6b41a1de494411e83a03714e"
HASHES = {
    "boxscoresummaryv2_0022200138.json": (
        "5ba9d933148301cce2399f821f4daf7a8980e32a86cdc0bb2619fd2befe4da21"
    ),
    "boxscoresummaryv2_0022200749.json": (
        "2665610b604f2effb2906b447cb9bee9acd4380c90f05469ade258170afe024b"
    ),
    "boxscoretraditionalv3_0022200138.json": (
        "b936d05d2f2ba83aa11da3f48e60748f544f9659d0e88a8bba5f6b4fd6a29958"
    ),
    "boxscoretraditionalv3_0022200749.json": (
        "d6fb2ea57a230e41379684f7ce3947039ffeeb0ac577048369d0b82e189f8b2f"
    ),
}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def table(doc, name):
    matches = [t for t in doc["resultSets"] if t["name"] == name]
    assert len(matches) == 1
    item = matches[0]
    assert len(item["headers"]) == len(set(item["headers"]))
    assert all(len(row) == len(item["headers"]) for row in item["rowSet"])
    return [dict(zip(item["headers"], row, strict=True)) for row in item["rowSet"]]


def main():
    old_bytes = OLD.read_bytes()
    assert sha(old_bytes) == ZIP_SHA
    with ZipFile(OLD) as archive:
        team_bytes, player_bytes = archive.read("teams.json"), archive.read("players.json")
    assert sha(team_bytes) == "04d3562ca95976278569c70c50dfc521e984300fc6af0f6d5ac21e21d2af9f06"
    assert sha(player_bytes) == "8fe0beda6aaafee1bf39f48b6ffd86a94fef0d3dbe71d8d08fc059609b6c0f47"
    teams = table(json.loads(team_bytes), "LeagueGameFinderResults")
    players = table(json.loads(player_bytes), "LeagueGameLog")
    season = [r for r in teams if r["SEASON_ID"] == "22022" and r["GAME_ID"].startswith("002")]
    assert len(season) == 2460
    assert len({(r["GAME_ID"], r["TEAM_ID"]) for r in season}) == 2460
    canonical = canonicalize_team_game_pairs(
        add_opponent_info(normalize_columns(pd.DataFrame(season)))
    )
    sources, vectors = [], []
    for name, digest in sorted(HASHES.items()):
        body = (ROOT / "originals" / name).read_bytes()
        assert sha(body) == digest
        family, gid = name.removesuffix(".json").split("_")
        sources.append(
            dict(
                file="originals/" + name,
                sha256=digest,
                bytes=len(body),
                git_blob_sha1=hashlib.sha1(
                    b"blob " + str(len(body)).encode() + b"\0" + body
                ).hexdigest(),
                url=f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{PIN}/nba_stats/json/{family}/2023/{gid}.json",
                retrieved_on="2026-11-06",
                retrieval_route="Connected GitHub read-only file tool",
                exact_retrieval_timestamp="Not supplied by connector; not invented",
                original_source_capture_time="Unverified; body metadata retained verbatim",
            )
        )
    for gid in ("0022200138", "0022200749"):
        final = json.loads((ROOT / "originals" / f"boxscoresummaryv2_{gid}.json").read_bytes())
        summary = table(final, "GameSummary")
        assert len(summary) == 1 and summary[0]["GAME_ID"] == gid
        assert summary[0]["GAME_STATUS_ID"] == 3
        scores = table(final, "LineScore")
        box = json.loads((ROOT / "originals" / f"boxscoretraditionalv3_{gid}.json").read_bytes())[
            "boxScoreTraditional"
        ]
        assert box["gameId"] == gid
        reported = [r for r in season if r["GAME_ID"] == gid]
        assert len(reported) == len(scores) == 2
        assert {r["TEAM_ID"] for r in reported} == {s["TEAM_ID"] for s in scores}
        for side in ("homeTeam", "awayTeam"):
            team = box[side]
            tid = team["teamId"]
            (r,) = [r for r in reported if r["TEAM_ID"] == tid]
            (opponent,) = [s for s in scores if s["TEAM_ID"] != tid]
            (line,) = [s for s in scores if s["TEAM_ID"] == tid]
            stats = team["statistics"]
            periods = [line[f"PTS_QTR{i}"] for i in range(1, 5)] + [
                line[f"PTS_OT{i}"] for i in range(1, 11)
            ]
            assert sum(periods) == line["PTS"] == stats["points"] == r["PTS"]
            margin = line["PTS"] - opponent["PTS"]
            assert stats["plusMinusPoints"] == margin
            played = [p for p in team["players"] if p["statistics"]["minutes"]]
            logs = [p for p in players if p["GAME_ID"] == gid and p["TEAM_ID"] == tid]
            assert len(logs) == len(played) and len({p["PLAYER_ID"] for p in logs}) == len(logs)
            assert {p["PLAYER_ID"] for p in logs} == {p["personId"] for p in played}
            player_vector = []
            for p in sorted(logs, key=lambda p: p["PLAYER_ID"]):
                (original,) = [b for b in played if b["personId"] == p["PLAYER_ID"]]
                assert p["PLUS_MINUS"] == original["statistics"]["plusMinusPoints"]
                player_vector.append(
                    dict(
                        player_id=p["PLAYER_ID"],
                        name=p["PLAYER_NAME"],
                        reported_plus_minus=p["PLUS_MINUS"],
                    )
                )
            total = sum(p["PLUS_MINUS"] for p in logs)
            assert total / 5 == r["PLUS_MINUS"]
            c = canonical.loc[canonical.game_id.astype(str).eq(gid) & canonical.team_id.eq(tid)]
            assert len(c) == 1 and c.plus_minus.item() == margin
            vectors.append(
                dict(
                    game_id=gid,
                    team_id=tid,
                    team=r["TEAM_ABBREVIATION"],
                    reported_gamefinder_plus_minus=r["PLUS_MINUS"],
                    traditional_team_plus_minus=stats["plusMinusPoints"],
                    pts=r["PTS"],
                    opponent_pts=opponent["PTS"],
                    period_points=periods,
                    score_margin=margin,
                    existing_canonical_output=c.plus_minus.item(),
                    reported_player_sum=total,
                    reported_player_sum_divided_by_five=total / 5,
                    complete_reported_player_vector=player_vector,
                    reported_gamefinder_minutes=r["MIN"],
                    traditional_team_minutes=stats["minutes"],
                )
            )
    result = dict(
        version="dq005-investigation-v1-20261106",
        kind="unqualified_source_investigation",
        baseline_commit="4bd2f799ddeb06544ef2223e56449ec609318dec",
        original_zip_sha256=ZIP_SHA,
        source_receipts=sources,
        affected_team_vectors=vectors,
        checks=dict(
            authenticated_new_bodies=4, complete_team_values=4, complete_played_player_values=42
        ),
        qualification=dict(
            independent_upstream_origin_proven=False,
            native_scorer_pdf_bodies_retained=0,
            source_mechanism_proven=False,
            corrected_output_version=None,
            data_qualified=False,
            production_accepted=False,
        ),
        conclusion=(
            "Raw GameFinder contradictions precede local parsing. Player-sum/5 relationship "
            "is observed, not a proven implementation. Separate team endpoints support "
            "literal margins but share NBA upstream. Existing canonical producer already "
            "derives score margins. No original or dataset changed; further independent "
            "native evidence required."
        ),
    )
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["checks"], sort_keys=True))


if __name__ == "__main__":
    main()
