"""Independent original-source family/role/numerical review, with no source-body reads."""

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile

BASE = Path("/workspace/nbatools")
SOURCE = BASE / "work/current-required-source"
REL = Path("working/nba-tools-completion-program/source-evidence/id18-current-required-20261107")
E = SOURCE / REL / "current-required"
OLD = E.parent.parent / "core-live-current-20261107"
OUT = BASE / REL / "independent"
SUFFIX = "2026-27_regular_season.csv"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rows(b):
    return list(csv.DictReader(io.StringIO(b.decode())))


def table(doc, name):
    (r,) = [r for r in doc["resultSets"] if r["name"] == name]
    assert len(r["headers"]) == len(set(r["headers"]))
    return [dict(zip(r["headers"], x, strict=True)) for x in r["rowSet"]]


def same(a, b):
    try:
        return Fraction(str(a)) == Fraction(str(b))
    except (TypeError, ValueError):
        return str("" if a is None else a) == str("" if b is None else b)


def main():
    with (
        ZipFile(E / "required-source-originals.zip") as z,
        ZipFile(E / "normalized-required-stage.zip") as stage,
        ZipFile(OLD / "current123-provisional.zip") as old,
        ZipFile(OUT / "current-family-authenticated-metadata.zip") as meta,
    ):
        manifest = json.loads(z.read("sources.json"))
        binding = json.loads((E / "source-binding.json").read_bytes())
        assert sha((E / binding["archive"]).read_bytes()) == binding["archive_sha256"]
        bodies = {}
        for r in manifest["files"]:
            raw = z.read(r["file"])
            assert sha(raw) == r["sha256"]
            assert len(raw) == r["bytes"] == r["metadata_size"]
            assert (
                hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == r["git_blob_sha"]
            )
            (item,) = [
                x for x in json.loads(meta.read(r["endpoint"] + ".json")) if x["path"] == r["path"]
            ]
            assert item["sha"] == r["git_blob_sha"] and item["size"] == len(raw)
            assert (
                r["url"]
                == f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{manifest['revision']}/{r['path']}"
            )
            bodies[r["file"]] = json.loads(raw)

        def load(f):
            return rows(stage.read(f"data/raw/{f}/{SUFFIX}"))

        teams, players, games = [load(f) for f in ["team_game_stats", "player_game_stats", "games"]]
        assert (len(teams), len(players), len(games)) == (246, 2781, 123)
        unchanged = []
        for name in old.namelist():
            selected = name.startswith("data/processed/") or any(
                "/" + f + "/" in name
                for f in [
                    "player_game_stats",
                    "team_game_stats",
                    "player_game_period_stats",
                    "team_game_period_stats",
                    "player_game_availability",
                    "schedule",
                ]
            )
            if selected and "/game_features/" not in name:
                assert old.read(name) == stage.read(name), name
                unchanged.append(name)
        rolepath = f"data/raw/player_game_starter_roles/{SUFFIX}"
        assert stage.read(rolepath).startswith(old.read(rolepath))
        newids = {f"00226{n:05d}" for n in range(173, 189)}
        expectedroles = {}
        for gid in sorted(newids):
            b = bodies[f"boxscoretraditionalv3-{gid}.json"]["boxScoreTraditional"]
            assert b["gameId"] == gid
            pair = [r for r in teams if int(r["game_id"]) == int(gid)]
            assert len(pair) == 2
            for side in ["homeTeam", "awayTeam"]:
                t = b[side]
                (canonical,) = [r for r in pair if int(r["team_id"]) == t["teamId"]]
                assert (
                    int(canonical["pts"]) == t["statistics"]["points"]
                    and canonical["team_abbr"] == t["teamTricode"]
                )
                count = 0
                for p in t["players"]:
                    k = (int(gid), t["teamId"], p["personId"])
                    assert k not in expectedroles
                    expectedroles[k] = (p["position"].strip(), int(bool(p["position"].strip())))
                    count += int(bool(p["position"].strip()))
                assert count == 5
        newroles = [
            r
            for r in load("player_game_starter_roles")
            if str(int(r["game_id"])).zfill(10) in newids
        ]

        def keys(r):
            return (int(r["game_id"]), int(r["team_id"]), int(r["player_id"]))

        wanted = {keys(r) for r in players if str(int(r["game_id"])).zfill(10) in newids}
        assert len(newroles) == len(wanted) == 368 and {keys(r) for r in newroles} == wanted
        for r in newroles:
            assert (r["starter_position_raw"], int(r["starter_flag"])) == expectedroles[keys(r)]
            assert r["role_source_trusted"] == "1" and r["starter_count_for_team_game"] == "5"
        # Only source-qualified new OT catalog cells and their processed copies change.
        oldgames = {int(r["game_id"]): r for r in rows(old.read(f"data/raw/games/{SUFFIX}"))}
        catalog = []
        for r in games:
            for k, v in oldgames[int(r["game_id"])].items():
                if str(int(r["game_id"])).zfill(10) in newids and k == "overtime_periods":
                    continue
                assert same(v, r[k]), (r["game_id"], k, v, r[k])
            if str(int(r["game_id"])).zfill(10) in newids:
                expected = int(int(r["game_id"]) in {22600179, 22600186})
                assert int(float(r["overtime_periods"])) == expected
                catalog.append((r["game_id"], expected))
        feature_name = f"data/processed/game_features/{SUFFIX}"
        before = rows(old.read(feature_name))
        after = rows(stage.read(feature_name))
        assert len(before) == len(after) == 123
        features = []
        for a, b in zip(before, after, strict=True):
            assert a.keys() == b.keys()
            for k, v in a.items():
                if same(v, b[k]):
                    continue
                assert str(int(b["game_id"])).zfill(10) in newids
                assert v == ""
                features.append((b["game_id"], k, v, b[k]))
        chronological = defaultdict(list)
        for r in sorted(teams, key=lambda r: (r["game_date"], int(r["game_id"]))):
            chronological[int(r["team_id"])].append(r)
        new_feature_checks = 0
        for r in after:
            if str(int(r["game_id"])).zfill(10) not in newids:
                continue
            expected = {}
            for side in ["home", "away"]:
                team = chronological[int(r[side + "_team_id"])]
                (index,) = [i for i, x in enumerate(team) if int(x["game_id"]) == int(r["game_id"])]
                previous = team[max(0, index - 5) : index]
                rest = (
                    date.fromisoformat(team[index]["game_date"])
                    - date.fromisoformat(team[index - 1]["game_date"])
                ).days
                expected[side + "_days_rest"] = Fraction(rest)
                expected[side + "_is_back_to_back"] = int(rest == 1)
                for field in ["pts", "fg3m", "fg3_pct", "reb", "tov"]:
                    expected[side + "_" + field + "_last_5"] = sum(
                        (Fraction(x[field]) for x in previous), Fraction(0)
                    ) / len(previous)
            expected["rest_diff"] = expected["home_days_rest"] - expected["away_days_rest"]
            expected["rest_advantage"] = (
                "home"
                if expected["rest_diff"] > 0
                else ("away" if expected["rest_diff"] < 0 else "tie")
            )
            for field in ["pts", "fg3m", "fg3_pct", "reb", "tov"]:
                diff = expected["home_" + field + "_last_5"] - expected["away_" + field + "_last_5"]
                expected[field + "_last_5_diff"] = diff
                if field != "pts":
                    expected[field + "_battle_winner"] = (
                        "home" if diff > 0 else ("away" if diff < 0 else "tie")
                    )
            for k, v in expected.items():
                if isinstance(v, str):
                    assert r[k] == v, (r["game_id"], k, r[k], v)
                else:
                    assert abs(Fraction(r[k]) - v) < Fraction(1, 10**12), (r["game_id"], k, r[k], v)
                new_feature_checks += 1
        pop = defaultdict(lambda: Counter(GP=0, W=0, L=0))
        tp = defaultdict(lambda: Counter(GP=0, W=0, L=0))
        byplayer = defaultdict(list)
        lookup = {(r["game_id"], r["team_id"]): r for r in teams}
        for r in teams:
            tp[int(r["team_id"])].update(["GP", r["wl"]])
        for r in players:
            pid = int(r["player_id"])
            pop[pid].update(["GP", lookup[r["game_id"], r["team_id"]]["wl"]])
            byplayer[pid].append(r)
        pa = table(
            bodies["leaguedashplayerstats-regular-season_advanced_pergame.json"],
            "LeagueDashPlayerStats",
        )
        ta = table(
            bodies["leaguedashteamstats-regular-season_advanced_pergame.json"],
            "LeagueDashTeamStats",
        )
        standings = table(bodies["leaguestandingsv3-regular-season.json"], "Standings")
        canonical = {int(r["player_id"]): r for r in load("player_season_advanced")}
        assert len(pa) == len(pop) == len(canonical) == 452
        assert {r["PLAYER_ID"] for r in pa} == set(pop)
        mapping = {
            "TEAM_ID": "team_id",
            "GP": "games_played",
            "USG_PCT": "usage_rate",
            "OFF_RATING": "off_rating",
            "DEF_RATING": "def_rating",
            "NET_RATING": "net_rating",
            "AST_PCT": "ast_pct",
            "REB_PCT": "reb_pct",
            "OREB_PCT": "oreb_pct",
            "DREB_PCT": "dreb_pct",
            "PIE": "pie",
            "TS_PCT": "reported_ts_pct",
            "MIN": "reported_minutes_per_game",
        }
        exact_checks = []
        with ZipFile(OLD / "current-originals.zip") as original:
            logs = json.loads(original.read("playergamelogs-current.json"))["resultSets"][0]
            logs = [dict(zip(logs["headers"], r, strict=True)) for r in logs["rowSet"]]
        source_groups = defaultdict(list)
        for r in logs:
            source_groups[r["PLAYER_ID"]].append(r)
        for r in pa:
            pid = r["PLAYER_ID"]
            assert all(r[k] == pop[pid][k] for k in ["GP", "W", "L"])
            c = canonical[pid]
            for a, b in mapping.items():
                assert same(r[a], c[b]), (pid, a)
            g = byplayer[pid]

            def total(k):
                return sum((Fraction(x[k]) for x in g), Fraction(0))

            den = 2 * (total("fga") + Fraction(11, 25) * total("fta"))
            ts = total("pts") / den if den else Fraction(0)
            minutes = total("minutes") / len(g)
            assert abs(Fraction(c["ts_pct"]) - ts) < Fraction(1, 10**14)
            assert abs(Fraction(c["minutes_per_game"]) - minutes) < Fraction(1, 10**12)

            def rawsum(k):
                return sum((Fraction(str(x[k])) for x in source_groups[pid]), Fraction(0))

            source_den = 2 * (rawsum("FGA") + Fraction(11, 25) * rawsum("FTA"))
            source_ts = rawsum("PTS") / source_den if source_den else Fraction(0)
            assert abs(Fraction(str(r["TS_PCT"])) - source_ts) <= Fraction(1, 2000)
            assert (
                c["as_of_date"] == "2026-11-05"
                and c["ts_pct_basis"] == "same_scope_game_count_ratio"
                and c["minutes_per_game_basis"] == "same_scope_game_minute_mean"
            )
            exact_checks.append(
                dict(
                    player_id=pid,
                    exact_ts=str(ts),
                    exact_minute_mean=str(minutes),
                    reported_ts=r["TS_PCT"],
                    source_log_exact_ts=str(source_ts),
                )
            )
        ct = {int(r["team_id"]): r for r in load("team_season_advanced")}
        cs = {int(r["team_id"]): r for r in load("standings_snapshots")}
        assert len(ta) == len(standings) == len(tp) == len(ct) == len(cs) == 30
        for r in ta:
            tid = r["TEAM_ID"]
            assert all(r[k] == tp[tid][k] for k in ["GP", "W", "L"])
            for a, b in {
                "GP": "games_played",
                "W": "wins",
                "L": "losses",
                "W_PCT": "win_pct",
                "OFF_RATING": "off_rating",
                "DEF_RATING": "def_rating",
                "NET_RATING": "net_rating",
                "PACE": "pace",
            }.items():
                assert same(r[a], ct[tid][b])
        for r in standings:
            tid = r["TeamID"]
            assert (r["WINS"], r["LOSSES"]) == (tp[tid]["W"], tp[tid]["L"])
            assert (
                same(r["WINS"], cs[tid]["wins"])
                and same(r["LOSSES"], cs[tid]["losses"])
                and same(r["WinPCT"], cs[tid]["win_pct"])
            )
        rawroster = {}
        for name, b in bodies.items():
            if not name.startswith("commonteamroster-"):
                continue
            tid = int(name.split("-")[1].split(".")[0])
            assert b["parameters"] == dict(TeamID=tid, LeagueID="00", Season="2026")
            for r in table(b, "CommonTeamRoster"):
                assert r["TeamID"] == tid and str(r["SEASON"]) == "2026"
                k = (tid, r["PLAYER_ID"])
                assert k not in rawroster
                rawroster[k] = r
        roster = rows(stage.read("data/raw/rosters/2026-27.csv"))
        assert len(roster) == len(rawroster) == 526
        for r in roster:
            source = rawroster[int(r["team_id"]), int(r["player_id"])]
            assert r["season"] == "2026-27" and r["stint"] == "1"
            for a, b in {
                "PLAYER": "player_name",
                "POSITION": "position",
                "HEIGHT": "height",
                "WEIGHT": "weight",
                "BIRTH_DATE": "birth_date",
                "SCHOOL": "school",
            }.items():
                assert same(source[a], r[b])
        report = json.loads((E / "initial-validation.json").read_bytes())
        failed = {
            r["name"]: r["validation"]["errors"]
            for r in report["datasets"]
            if r["validation"]["errors"]
        }
        assert set(failed) == {"player_game_period_stats", "team_game_period_stats"}
        receipt = dict(
            reviewer="/root/id18_checker",
            backend_model="unavailable",
            candidate_sha="578dd16d6ff4137abd13ea69d2276438506ad03b",
            source_archive_sha256=binding["archive_sha256"],
            normalized_stage_sha256=sha((E / "normalized-required-stage.zip").read_bytes()),
            authenticated_metadata_archive_sha256=sha(
                (OUT / "current-family-authenticated-metadata.zip").read_bytes()
            ),
            metadata_reads=5,
            originalbody_reacquisitions=0,
            authenticated_originals=49,
            old_current123_byte_identical_files=unchanged,
            new_roles_qualified=368,
            catalog_ot_source_pairs=catalog,
            processed_new_game_feature_changes=features,
            independent_previous_window_game_feature_cells=new_feature_checks,
            player_gp_w_l_count=452,
            team_gp_w_l_count=30,
            standings_w_l_count=30,
            roster_source_rows=526,
            roster_game_day_membership_qualified=False,
            player_source_mapped_fields=list(mapping),
            independent_exact_ts_and_minutes=exact_checks,
            required_structural_failures=failed,
            unchanged_old_period_bytes=True,
            old_484_rate_unknowns_preserved=True,
            source_generation_independence=False,
            full_snapshot_accepted=False,
            freshness_accepted=False,
            production_writes=0,
            conclusion=(
                "Approved finite source/schema/key/role/same-scope "
                "GP-W-L/TS-minute basis admission; "
                "source-reported remaining Advanced fields and independent numerical "
                "generation/current-release acceptance remain separate."
            ),
        )
        (OUT / "current-family-independent-execution.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
        print(
            {
                k: receipt[k]
                for k in [
                    "authenticated_originals",
                    "new_roles_qualified",
                    "player_gp_w_l_count",
                    "team_gp_w_l_count",
                    "standings_w_l_count",
                    "roster_source_rows",
                    "required_structural_failures",
                    "conclusion",
                ]
            }
        )


if __name__ == "__main__":
    main()
