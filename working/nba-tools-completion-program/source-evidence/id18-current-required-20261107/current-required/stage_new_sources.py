"""One offline123cutoff qualification, using existing producers/validators only."""

import hashlib, io, json, shutil, subprocess, sys, os
from datetime import datetime, UTC
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from fractions import Fraction
import pandas as pd
from nba_api.stats.endpoints import BoxScoreTraditionalV3
from nbatools.commands.pipeline.pull_player_game_starter_roles import (
    normalize_boxscore_player_roles,
    add_trust_validation,
)
from nbatools.commands.pipeline import (
    pull_player_season_advanced,
    pull_team_season_advanced,
    pull_standings_snapshots,
    pull_rosters,
)
from nbatools.commands.validation_control import build_slice_manifest
from tools.stage_rollover_periods import _endpoint
from tools.stage_current_season import project_season_basis

E = Path(__file__).resolve().parent
OLD = E.parent.parent / "core-live-current-20261107"
SUFFIX = "2026-27_regular_season.csv"
WORK = Path(sys.argv[1])
WORK.mkdir(parents=True, exist_ok=False)
S = WORK / "sources"
S.mkdir()
binding = json.loads((E / "source-binding.json").read_bytes())
assert (
    hashlib.sha256((E / binding["archive"]).read_bytes()).hexdigest() == binding["archive_sha256"]
)
with ZipFile(E / binding["archive"]) as z:
    assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in z.namelist())
    z.extractall(S)
for item in json.loads((S / "sources.json").read_bytes())["files"]:
    raw = (S / item["file"]).read_bytes()
    assert len(raw) == item["bytes"] == item["metadata_size"]
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    assert hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == item["git_blob_sha"]
assert (
    hashlib.sha256((OLD / "current123-provisional.zip").read_bytes()).hexdigest()
    == "eb60f64204a089d0d5a9083496aa44e172e3fe511b71d7980a0649e0e3778c17"
)
with ZipFile(OLD / "current123-provisional.zip") as z:
    z.extractall(WORK / "stage")
R = WORK / "stage"
D = R / "data"
for p in (D / "metadata").glob("*"):
    p.unlink()
games = pd.read_csv(D / "raw/games" / SUFFIX)
teams = pd.read_csv(D / "raw/team_game_stats" / SUFFIX)
players = pd.read_csv(D / "raw/player_game_stats" / SUFFIX)


def table(name, table_name):
    d = json.loads((S / name).read_bytes())
    (r,) = [r for r in d["resultSets"] if r["name"] == table_name]
    assert len(r["headers"]) == len(set(r["headers"]))
    return pd.DataFrame(r["rowSet"], columns=r["headers"])


rows = []
role_receipts = []
for n in range(173, 189):
    gid = f"00226{n:05d}"
    path = S / f"boxscoretraditionalv3-{gid}.json"
    raw = path.read_bytes()
    b = json.loads(raw)["boxScoreTraditional"]
    assert b["gameId"] == gid
    canonical = teams.loc[teams.game_id.eq(int(gid))].set_index("team_id")
    assert set(canonical.index) == {b["awayTeamId"], b["homeTeamId"]}
    for side in ["awayTeam", "homeTeam"]:
        t = b[side]
        assert t["statistics"]["points"] == canonical.loc[t["teamId"], "pts"]
    f = normalize_boxscore_player_roles(
        _endpoint(BoxScoreTraditionalV3, raw, gid).player_stats.get_data_frame()
    )
    for k in ["game_id", "team_id", "player_id"]:
        f[k] = pd.to_numeric(f[k])
    expected = players.loc[players.game_id.eq(int(gid)), ["game_id", "team_id", "player_id"]]
    assert set(expected.itertuples(index=False, name=None)) <= set(
        f[["game_id", "team_id", "player_id"]].itertuples(index=False, name=None)
    )
    f = f.merge(expected, on=["game_id", "team_id", "player_id"], validate="one_to_one")
    f["season"] = "2026-27"
    f["season_type"] = "Regular Season"
    f = add_trust_validation(f)
    assert f.role_source_trusted.eq(1).all()
    role_receipts.append(
        dict(
            game_id=gid,
            source_sha256=hashlib.sha256(raw).hexdigest(),
            positive_rows=len(f),
            starter_counts=f.groupby("team_id").starter_flag.sum().to_dict(),
        )
    )
    rows.append(f)
role_path = D / "raw/player_game_starter_roles" / SUFFIX
base_role = role_path.read_bytes()
extra = pd.concat(rows, ignore_index=True)
assert len(extra) == 368
with role_path.open("ab") as f:
    f.write(extra.to_csv(index=False, header=False).encode())
assert role_path.read_bytes().startswith(base_role)
window_doc = json.loads((OLD / "new16-window-denominator.json").read_bytes())
with ZipFile(OLD / "new16-summary-originals.zip") as z:
    for item in window_doc["new16"]:
        names = [x for x in z.namelist() if x.endswith(item["game_id"] + ".json")]
        assert len(names) == 1
        raw = z.read(names[0])
        assert hashlib.sha256(raw).hexdigest() == item["source_sha256"]
        b = json.loads(raw)["boxScoreSummary"]
        assert b["period"] == item["periods"]
        gid = int(item["game_id"])
        games.loc[games.game_id.eq(gid), "overtime_periods"] = item["ot"]
        for side in ["awayTeam", "homeTeam"]:
            t = b[side]
            assert sum(p["score"] for p in t["periods"]) == t["score"]
            assert len(t["periods"]) == item["periods"]
games.to_csv(D / "raw/games" / SUFFIX, index=False)
# Original Advanced documents are qualified for same scope by everyGP/W/L key,
# not by their filename or retrieval clock. Dependent rate truth remains separate.
raw_player = table(
    "leaguedashplayerstats-regular-season_advanced_pergame.json", "LeagueDashPlayerStats"
)
raw_team = table("leaguedashteamstats-regular-season_advanced_pergame.json", "LeagueDashTeamStats")
for raw in [raw_player, raw_team]:
    assert raw.GP.eq(raw.W + raw.L).all()
pc = players.merge(
    teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
)
pop = (
    pc.assign(W=pc.wl.eq("W").astype(int), L=pc.wl.eq("L").astype(int))
    .groupby("player_id")
    .agg(GP=("game_id", "size"), W=("W", "sum"), L=("L", "sum"))
)
assert set(pop.index) == set(raw_player.PLAYER_ID)
pd.testing.assert_frame_equal(
    pop.sort_index(),
    raw_player.set_index("PLAYER_ID")[["GP", "W", "L"]].sort_index(),
    check_names=False,
    check_dtype=False,
)
tpop = (
    teams.assign(W=teams.wl.eq("W").astype(int), L=teams.wl.eq("L").astype(int))
    .groupby("team_id")
    .agg(GP=("game_id", "size"), W=("W", "sum"), L=("L", "sum"))
)
pd.testing.assert_frame_equal(
    tpop.sort_index(),
    raw_team.set_index("TEAM_ID")[["GP", "W", "L"]].sort_index(),
    check_names=False,
    check_dtype=False,
)
asof = games.game_date.max()
reported = pull_player_season_advanced.normalize(raw_player, "2026-27", "Regular Season", asof)
literal_core = pd.read_csv(D / "raw/player_game_stats" / SUFFIX, dtype={"minutes": str})
projected, ledger = project_season_basis(literal_core, reported)
projected.to_csv(D / "raw/player_season_advanced" / SUFFIX, index=False)
pull_team_season_advanced.normalize(raw_team, "2026-27", "Regular Season", asof).to_csv(
    D / "raw/team_season_advanced" / SUFFIX, index=False
)
standing = table("leaguestandingsv3-regular-season.json", "Standings")
pd.testing.assert_frame_equal(
    tpop[["W", "L"]].sort_index(),
    standing.set_index("TeamID")[["WINS", "LOSSES"]]
    .sort_index()
    .rename(columns={"WINS": "W", "LOSSES": "L"}),
    check_names=False,
    check_dtype=False,
)
pull_standings_snapshots.normalize(standing, "2026-27", "Regular Season", asof).to_csv(
    D / "raw/standings_snapshots" / SUFFIX, index=False
)
rosters = []
for p in sorted(S.glob("commonteamroster-*.json")):
    if not p.stem.split("-")[1].isdigit():
        continue
    tid = int(p.stem.split("-")[1])
    raw = table(p.name, "CommonTeamRoster")
    assert raw.TeamID.eq(tid).all() and raw.SEASON.astype(str).eq("2026").all()
    abbr = teams.loc[teams.team_id.eq(tid), "team_abbr"].unique()
    assert len(abbr) == 1
    rosters.append(pull_rosters.normalize_columns(raw, "2026-27", tid, abbr[0]))
roster = pd.concat(rosters, ignore_index=True)
roster.to_csv(D / "raw/rosters/2026-27.csv", index=False)
env = dict(
    os.environ,
    DATA_SOURCE="local",
    NBATOOLS_DATA_ROOT=str(R.resolve()),
    PYTHONPATH=str(Path("src").resolve()),
)
stages = []
for name in [
    "build_game_features",
    "build_team_game_features",
    "build_player_game_features",
    "build_league_season_stats",
    "build_schedule_context_features",
]:
    run = subprocess.run(
        [
            sys.executable,
            "-c",
            f'from nbatools.commands.pipeline.{name} import run;run("2026-27","Regular Season")',
        ],
        cwd=R,
        env=env,
        capture_output=True,
        text=True,
    )
    stages.append(dict(stage=name, returncode=run.returncode, stdout=run.stdout, stderr=run.stderr))
    assert run.returncode == 0, (name, run.stderr)
report = build_slice_manifest(
    "2026-27", "Regular Season", data_root=D, generation_id="current123-required-source-stage-v1"
)
(E / "initial-validation.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
with ZipFile(OLD / "current-originals.zip") as z:
    source_player = json.loads(z.read("playergamelogs-current.json"))["resultSets"][0]
source_player = pd.DataFrame(source_player["rowSet"], columns=source_player["headers"])
ts_checks = []
for pid, raw in raw_player.set_index("PLAYER_ID").iterrows():
    g = source_player.loc[source_player.PLAYER_ID.eq(pid)]
    den = 2 * (Fraction(str(g.FGA.sum())) + Fraction(11, 25) * Fraction(str(g.FTA.sum())))
    exact = Fraction(str(g.PTS.sum())) / den if den else Fraction(0)
    ts_checks.append(
        dict(
            player_id=int(pid),
            reported=float(raw.TS_PCT),
            raw_source_ratio=str(exact),
            difference=float(abs(Fraction(str(raw.TS_PCT)) - exact)),
            within_source3decimal=abs(Fraction(str(raw.TS_PCT)) - exact) <= Fraction(1, 2000),
        )
    )
missing = [r for r in report["datasets"] if r["validation"]["errors"]]
receipt = dict(
    classification="required123source_delta_qualified_scopes_not_full_snapshot_acceptance",
    game_count=len(games),
    player_rows=len(players),
    team_rows=len(teams),
    new_roles=len(extra),
    old_role_bytes_preserved=True,
    source_window_denominator=745,
    new_window_denominator=98,
    new_ot_games=["0022600179", "0022600186"],
    advanced_player_gp_w_l_keys=len(pop),
    advanced_team_gp_w_l_keys=len(tpop),
    standings_w_l_keys=len(tpop),
    roster_rows=len(roster),
    roster_membership_inference=False,
    source_player_ts_checks=ts_checks,
    derived_player_advanced_ledger=ledger,
    role_source_checks=role_receipts,
    executed_builders=stages,
    structural_failures={r["name"]: r["validation"]["errors"] for r in missing},
    old_period_rate_unknowns=pd.read_csv(D / "raw/player_game_period_stats" / SUFFIX)[
        ["tov_pct", "usg_pct"]
    ]
    .isna()
    .sum()
    .to_dict(),
    production_writes=0,
    full_snapshot_accepted=False,
    source_generation_independence="unestablished",
    freshness_accepted=False,
)
(E / "qualification.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n")
with ZipFile(E / "normalized-required-stage.zip", "w", ZIP_DEFLATED) as z:
    for f in sorted(D.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(R))
print(
    {
        k: v
        for k, v in receipt.items()
        if k
        not in [
            "source_player_ts_checks",
            "derived_player_advanced_ledger",
            "role_source_checks",
            "executed_builders",
        ]
    }
)
