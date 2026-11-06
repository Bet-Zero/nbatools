import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from nbatools.commands.data_utils import score_margin_plus_minus
from nbatools.commands.pipeline import pull_team_game_stats as producer
from nbatools.commands.pipeline.build_schedule_context_features import (
    build_schedule_context_features,
)

OUT = Path(__file__).resolve().parent
BASE = Path(__file__).resolve().parents[4]
E = OUT / "originals"
with zipfile.ZipFile(
    BASE
    / "working/nba-tools-completion-program/source-evidence"
    / "multi-team-absence-20261106/archive-originals.zip"
) as z:
    raw = z.read("teams.json")
    logs = z.read("players.json")
assert (
    hashlib.sha256(raw).hexdigest()
    == "04d3562ca95976278569c70c50dfc521e984300fc6af0f6d5ac21e21d2af9f06"
)
assert (
    hashlib.sha256(logs).hexdigest()
    == "8fe0beda6aaafee1bf39f48b6ffd86a94fef0d3dbe71d8d08fc059609b6c0f47"
)


def table(b, name=None):
    s = json.loads(b)
    ts = s["resultSets"]
    t = next(t for t in ts if name is None or t["name"] == name)
    return pd.DataFrame(t["rowSet"], columns=t["headers"])


t = table(raw)
p = table(logs)
t = t.loc[t.GAME_ID.isin(["0022200138", "0022200749"])].copy()
assert len(t) == 4
vectors = []
source_hashes = {}
for gid, group in t.groupby("GAME_ID"):
    vpath = E / f"boxscoretraditionalv3_{gid}.json"
    spath = E / f"boxscoresummaryv2_{gid}.json"
    vb = vpath.read_bytes()
    sb = spath.read_bytes()
    source_hashes[vpath.name] = hashlib.sha256(vb).hexdigest()
    source_hashes[spath.name] = hashlib.sha256(sb).hexdigest()
    v = json.loads(vb)["boxScoreTraditional"]
    assert v["gameId"] == gid
    summary = table(sb, "LineScore")
    assert len(summary) == 2
    for row in group.to_dict("records"):
        tid = row["TEAM_ID"]
        other = group.loc[group.TEAM_ID.ne(tid)].iloc[0]
        vt = next(v[side] for side in ["homeTeam", "awayTeam"] if v[side]["teamId"] == tid)
        sr = summary.loc[summary.TEAM_ID.eq(tid)].iloc[0]
        ps = p.loc[p.GAME_ID.eq(gid) & p.TEAM_ID.eq(tid)]
        assert len(ps) in [9, 12] and not ps.PLAYER_ID.duplicated().any()
        assert row["PTS"] == vt["statistics"]["points"] == sr.PTS
        qsum = sum(
            sr[c] for c in summary.columns if c.startswith("PTS_QTR") or c.startswith("PTS_OT")
        )
        assert qsum == sr.PTS
        margin = row["PTS"] - int(other.PTS)
        assert vt["statistics"]["plusMinusPoints"] == margin
        rawsum = int(ps.PLUS_MINUS.sum())
        vsum = sum(
            q["statistics"]["plusMinusPoints"] for q in vt["players"] if q["statistics"]["minutes"]
        )
        assert vsum == rawsum and rawsum / 5 == row["PLUS_MINUS"]
        vectors.append(
            dict(
                game_id=gid,
                team_id=tid,
                team=row["TEAM_ABBREVIATION"],
                reported_plus_minus=row["PLUS_MINUS"],
                pts=row["PTS"],
                opponent_pts=int(other.PTS),
                paired_margin=margin,
                v3_team_plus_minus=vt["statistics"]["plusMinusPoints"],
                player_count=len(ps),
                player_plus_minus_sum=rawsum,
                v3_player_plus_minus_sum=vsum,
                minutes_reported=row["MIN"],
                v3_minutes=vt["statistics"]["minutes"],
            )
        )
with tempfile.TemporaryDirectory() as td:
    try:
        os.chdir(td)
        producer.run("2022-23", "Regular Season", raw_frame=t)
        c = pd.read_csv("data/raw/team_game_stats/2022-23_regular_season.csv")
        assert len(c) == 4
        original = producer.add_opponent_info(producer.normalize_columns(t))
        loaded = score_margin_plus_minus(original)
        sp = Path("data/raw/schedule")
        sp.mkdir(parents=True)
        pd.DataFrame({"game_id": c.game_id.unique()}).to_csv(
            sp / "2022-23_regular_season.csv", index=False
        )
        schedule = build_schedule_context_features("2022-23", "Regular Season")
        for r in vectors:
            gid = int(r["game_id"])
            tid = r["team_id"]
            canon = c.loc[c.game_id.eq(gid) & c.team_id.eq(tid)].iloc[0]
            load = loaded.loc[loaded.game_id.eq(r["game_id"]) & loaded.team_id.eq(tid)].iloc[0]
            sched = schedule.loc[schedule.game_id.eq(gid) & schedule.team_id.eq(tid)].iloc[0]
            assert canon.plus_minus == load.plus_minus == r["paired_margin"]
            assert sched.score_margin == abs(r["paired_margin"]) and sched.one_possession == 0
            r.update(
                canonical_team_plus_minus=float(canon.plus_minus),
                loaded_team_plus_minus=float(load.plus_minus),
                schedule_score_margin=float(sched.score_margin),
                schedule_one_possession=int(sched.one_possession),
            )
    finally:
        os.chdir(BASE)
review = dict(
    reviewer="/root/dq005_checker",
    model="Exact model identifier not exposed",
    reviewed_application_baseline="4bd2f799ddeb06544ef2223e56449ec609318dec",
    source_hashes=source_hashes,
    vectors=vectors,
    checks=(
        "Two-game four-team complete vector; paired score/V3 team/Summary period checks; "
        "12/12/9/9 player counts and sums; unchanged canonical producer/load arithmetic "
        "and schedule features"
    ),
    result="blocked_evidence; no source correction qualified",
    findings=[
        "Raw Finder JSON already contains all4anomalies: no local parse origin.",
        (
            "Canonical producer and loader already derive margins from paired scores;"
            " no application correction indicated."
        ),
        (
            "Player-sum/5 equality across endpoint variants is observed; undocumented"
            " upstream algorithm/cause remains unproven."
        ),
        (
            "V3 and Summary share NBA Stats upstream; their agreement is not "
            "independent original scorer corroboration."
        ),
        (
            "No native official scorer PDF bytes retained; extracted web text cannot "
            "substitute exact original-body provenance."
        ),
    ],
    missing=[
        (
            "Retained attributable original scorer final boxes or equivalent "
            "qualified independent original evidence for both complete game/team "
            "vectors."
        ),
    ],
    unknown_mechanism=(
        "Upstream processing, stale-source cause or alternate Finder basis remains unknown. "
        "This need not block a future field correction if independent original scorer totals "
        "and the intended field meaning establish the complete correction."
    ),
    qualified_output_version=None,
)
# Authenticate the author receipts independently, including Git object framing.
receipt = json.loads((OUT / "analysis.json").read_bytes())
assert len(receipt["source_receipts"]) == 4
review["provenance_checks"] = []
for source in receipt["source_receipts"]:
    body = (OUT / source["file"]).read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
    assert len(body) == source["bytes"]
    assert digest == source["sha256"] == source_hashes[Path(source["file"]).name]
    assert blob == source["git_blob_sha1"]
    family, gid = Path(source["file"]).stem.split("_")
    expected_url = (
        "https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/"
        "2e44b7c039f104bc6b41a1de494411e83a03714e/nba_stats/json/"
        + family
        + "/2023/"
        + gid
        + ".json"
    )
    assert source["url"] == expected_url
    review["provenance_checks"].append(
        dict(
            file=source["file"],
            sha256=digest,
            git_blob_sha1=blob,
            bytes=len(body),
            url=expected_url,
        )
    )
review["reviewed_files_sha256"] = {
    str(path.relative_to(BASE)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [
        OUT / "README.md",
        OUT / "replay.py",
        OUT / "analysis.json",
        OUT / "sources-investigated.json",
        BASE / "working/nba-tools-completion-program/data-quality/DQ-005.json",
        BASE / "working/nba-tools-completion-program/data-quality/README.md",
        *sorted(E.glob("*.json")),
    ]
}
review["collector_review"] = dict(
    reviewed_remote_revision="e548f629d038055f84c3b448ed4ec184f2d62ecf",
    reviewed_local_revision="711273320c8d71f9b5648466343941147deb461d",
    path="tests/cloud_dq005_source_capture_real_data.py",
    file_sha256=hashlib.sha256(
        (BASE / "tests/cloud_dq005_source_capture_real_data.py").read_bytes()
    ).hexdigest(),
    approval="Bounded two-original collector only; not statistical or corrected-data approval",
    controlled_checks="Success and two-failure receipt branches passed, zero network calls",
    execution=(
        "No hosted workflow executed; request manifest rejected before write per author receipt"
    ),
)
review["package_review"] = dict(
    approval=(
        "Accurate blocked-evidence investigation only; no correction acceptance or merge approval"
    ),
    native_pdf_claims=(
        "README accurately identifies extracted web text as unretained native-body leads"
    ),
    root_cause_claims="README accurately limits player-sum/5 relationship to observed hypothesis",
    author_script_scope=(
        "Offline hash-bound two-game four-team/42player analysis; no network or app mutation"
    ),
    independent_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
)
(OUT / "independent-review.json").write_text(json.dumps(review, indent=2) + "\n")
print(json.dumps(review, indent=2))
