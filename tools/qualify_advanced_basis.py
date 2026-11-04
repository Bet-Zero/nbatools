"""Retained-source Advanced basis and independent bounded possession qualification.

Reported NBA values and accepted canonical data are never rewritten. The source
basis ledger distinguishes raw NBA game-log arithmetic from corrected canonical
counts. Usage qualification is limited to an observed no-FTA/no-OREB team period;
no estimated free-throw multiplier or Advanced.POSS oracle is used.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pandas as pd

from tools.assess_readiness_recovery import minute_mean_interval
from tools.period_event_evidence import clock_facts, period_facts, require
from tools.qualify_incremental_return import CLOCK_SHA, bound_zip
from tools.season_rollover_core_bridge import _literal_clock_seconds
from tools.stage_current_season import CURRENT, PARTIAL, RECOVERY, SUFFIX, _whole_original

RETURNED = CURRENT.parent / "incremental-return-20261104"
COLLECTION_SHA = "d98ddb5f8b5f3ac7c288abed786b92c6ff3474b7fd97cdc0dead58b87c7736ab"
SOURCE_SHA = "0dfd1bb7dcd9cff467fb110cf888c006266f00c7f02073fa6956e4a0c965ae13"
STAGE_SHA = "04151f5ed20aedf27ee2a5c279ee75babc9084170a01b64ab79104ec8eaa4486"


def true_shooting(points, fga, fta):
    values = [Fraction(str(v)) for v in (points, fga, fta)]
    require(all(v.denominator == 1 and v >= 0 for v in values), "Invalid TS count basis")
    denominator = 2 * (values[1] + Fraction(11, 25) * values[2])
    require(denominator > 0 or values[0] == 0, "Invalid TS count basis: points without attempts")
    return values[0] / denominator if denominator else Fraction(0)


def table(raw, name):
    doc = json.loads(raw)
    records = [r for r in doc["resultSets"] if r["name"] == name]
    require(len(records) == 1, "Advanced source table identity differs")
    return pd.DataFrame(records[0]["rowSet"], columns=records[0]["headers"])


def possession_exposure(raw, whole_raw, traditional_raw, advanced_raw, *, team_id, period):
    """Count observed own-possession exposure, including an unfinished terminal one.

    This restricted oracle requires no own FTA or OREB and verifies every missed
    attempt is followed by an opponent defensive rebound before the next scoring
    attempt/turnover. It accepts neither a team possession scalar nor reported
    Advanced denominators as input to the count. Every original action is retained.
    """
    whole = json.loads(whole_raw)["boxScoreTraditional"]
    facts = period_facts(
        raw,
        game_id=whole["gameId"],
        final_teams={
            whole[s]["teamId"]: whole[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
        },
    )
    trace = []
    clocks = clock_facts(raw, whole_raw, period_report=facts, only_periods={period}, trace=trace)
    trad = json.loads(traditional_raw)["boxScoreTraditional"]
    advanced = json.loads(advanced_raw)["boxScoreAdvanced"]
    require(trad["gameId"] == advanced["gameId"] == whole["gameId"], "Usage identity differs")
    sides = [s for s in ["homeTeam", "awayTeam"] if trad[s]["teamId"] == team_id]
    require(len(sides) == 1, "Usage team identity missing")
    side = sides[0]
    require(advanced[side]["teamId"] == team_id, "Usage Advanced team identity differs")
    paired_teams = {whole[s]["teamId"] for s in ["homeTeam", "awayTeam"]}
    require(
        team_id in paired_teams and len(paired_teams) == 2, "Usage paired team identity differs"
    )
    opponent = next(tid for tid in paired_teams if tid != team_id)
    statistics = trad[side]["statistics"]
    require(
        statistics["freeThrowsAttempted"] == statistics["reboundsOffensive"] == 0,
        "Restricted usage oracle requires no own FTA or OREB",
    )
    lineups = {t["action_id"]: set(t["lineups"][team_id]) for t in trace}
    actions = [a for a in json.loads(raw)["game"]["actions"] if a["period"] == period]
    require(
        not any(a["actionType"] in {"Jump Ball"} for a in actions[2:]),
        "Midperiod possession jump requires another oracle",
    )
    for action in actions:
        owner = action["teamId"]
        if action["actionType"] in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}:
            require(owner in paired_teams, "Possession-changing actor has unknown team ownership")
        elif action["actionType"] == "Rebound":
            rebound_owner = owner if owner else action["personId"]
            require(rebound_owner in paired_teams, "Rebound has unknown team ownership")
    # The observed opening opponent turnover establishes initial possession.
    first = next(
        a
        for a in actions
        if a["actionType"] in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}
    )
    require(
        first["teamId"] == opponent and first["actionType"] == "Turnover",
        "Initial opponent possession is not established by this oracle",
    )
    active, pending_miss, possessions = None, None, []
    terminal_ft = re.compile(r"Free Throw ([123]) of ([123])")
    for action in actions:
        kind, aid, owner = action["actionType"], action["actionId"], action["teamId"]
        if kind == "Substitution":
            continue
        if active is not None:
            active["players"].update(lineups[aid])
        if pending_miss is not None:
            if kind == "Rebound":
                rebound_owner = owner if owner else action["personId"]
                require(rebound_owner == opponent, "Own missed attempt lacks defensive rebound")
                pending_miss = None
            elif kind in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}:
                raise ValueError("Own missed attempt lacks intervening defensive rebound")
        begins = owner == opponent and kind in {"Made Shot", "Turnover"}
        if (
            owner != team_id
            and kind == "Free Throw"
            and not action["description"].startswith("MISS ")
        ):
            match = terminal_ft.fullmatch(action.get("subType", ""))
            require(match is not None, "Unhandled opponent free-throw credit semantics")
            begins = match[1] == match[2]
        if kind == "Rebound":
            begins = (owner if owner else action["personId"]) == team_id
        if begins:
            require(active is None, "Overlapping own possession intervals")
            active = dict(start_action=aid, players=set(lineups[aid]))
        if owner == team_id and kind in {"Made Shot", "Missed Shot", "Turnover"}:
            require(active is not None, "Own ending action has no established possession")
            active.update(end_action=aid, incomplete=False)
            possessions.append(active)
            active = None
            if kind == "Missed Shot":
                pending_miss = aid
        if kind == "period" and action["subType"] == "end" and active is not None:
            active.update(end_action=aid, incomplete=True)
            possessions.append(active)
            active = None
    require(pending_miss is None and active is None, "Unclosed possession evidence")
    denominators = Counter(pid for p in possessions for pid in p["players"])
    rates = {p["personId"]: p["statistics"] for p in advanced[side]["players"]}
    require(
        not any(a["actionType"] == "Free Throw" and a["teamId"] == team_id for a in actions),
        "Own free-throw events contradict restricted source scope",
    )
    observed_players = {
        p["personId"]
        for p in trad[side]["players"]
        if _literal_clock_seconds(p["statistics"]["minutes"]) > 0
    }
    expected_players = {pid for pid, seconds in clocks[period][team_id].items() if seconds > 0}
    require(observed_players == expected_players, "Independent usage player population differs")
    cases = []
    for player in trad[side]["players"]:
        pid, stats = player["personId"], player["statistics"]
        if clocks[period][team_id].get(pid, Fraction(0)) <= 0:
            continue
        require(
            clocks[period][team_id][pid]
            == _literal_clock_seconds(stats["minutes"])
            == _literal_clock_seconds(rates[pid]["minutes"]),
            "Independent usage sample clock differs",
        )
        # Numerators come from literal actions, with direct counts as cross-check.
        numerator = sum(
            a["personId"] == pid
            and a["teamId"] == team_id
            and a["actionType"] in {"Made Shot", "Missed Shot", "Turnover"}
            for a in actions
        )
        require(
            numerator == stats["fieldGoalsAttempted"] + stats["turnovers"],
            "Independent usage numerator differs from source counts",
        )
        denominator = denominators[pid]
        require(denominator > 0 and numerator <= denominator, "Invalid usage exposure denominator")
        exact = Fraction(numerator, denominator)
        reported = Fraction(str(rates[pid]["usagePercentage"]))
        cases.append(
            dict(
                player_id=pid,
                numerator=numerator,
                exposure_denominator=denominator,
                exact_ratio=str(exact),
                reported_rate=str(reported),
                matches=abs(exact - reported) <= Fraction(1, 2000),
                reported_possessions_corroborates=denominator == rates[pid]["possessions"],
            )
        )
    require(
        cases and all(c["matches"] for c in cases), "Event exposure does not qualify reported usage"
    )
    for possession in possessions:
        possession["players"] = sorted(possession["players"])
    return dict(
        game_id=whole["gameId"],
        team_id=team_id,
        period=period,
        scope="no_own_FTA_no_own_OREB_with_complete_event_lineups",
        cases=cases,
        possessions=possessions,
        sample_usage_accepted=True,
        reported_possessions_used_as_oracle=False,
        full_independent_NBA_usage_accepted=False,
        source_sha256={
            name: hashlib.sha256(value).hexdigest()
            for name, value in [
                ("events", raw),
                ("whole", whole_raw),
                ("traditional", traditional_raw),
                ("advanced", advanced_raw),
            ]
        },
    )


def qualify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with bound_zip(CURRENT / "current-sources.zip", SOURCE_SHA) as z:
        primary_raw = z.read("playergamelogs-regular-season_base_totals.json")
        pbp = z.read("playbyplayv3-0022600116.json")
        whole163 = z.read("boxscoretraditionalv3-0022600163.json")
        event_sources = {}
        for name in z.namelist():
            if name.startswith("playbyplayv3-"):
                body = z.read(name)
                gid = json.loads(body)["game"]["gameId"]
                event_sources[gid] = dict(
                    archive="current-refresh-20261104/current-sources.zip",
                    file=name,
                    sha256=hashlib.sha256(body).hexdigest(),
                    classification="retained_original_not_timing_acceptance",
                )
    with bound_zip(RETURNED / "clock-source-originals.zip", CLOCK_SHA) as z:
        events163 = z.read("0022600163.json")
        for name in z.namelist():
            if name != "sources.json":
                body = z.read(name)
                gid = json.loads(body)["game"]["gameId"]
                event_sources[gid] = dict(
                    archive="incremental-return-20261104/clock-source-originals.zip",
                    file=name,
                    sha256=hashlib.sha256(body).hexdigest(),
                    classification="retained_original_not_timing_acceptance",
                )
    primary = table(primary_raw, "PlayerGameLogs")
    require(not primary.duplicated(["GAME_ID", "PLAYER_ID"]).any(), "Duplicate primary count keys")
    with bound_zip(RETURNED / "collection.zip", COLLECTION_SHA) as z:
        p_raw = z.read("sources/leaguedashplayerstats_advanced_through_20261102.json")
        t_raw = z.read("sources/leaguedashteamstats_advanced_through_20261102.json")
    snapshots = {
        "player": table(p_raw, "LeagueDashPlayerStats"),
        "team": table(t_raw, "LeagueDashTeamStats"),
    }
    with bound_zip(RETURNED / "qualification-evidence.zip", STAGE_SHA) as z:
        core = {
            g: pd.read_csv(
                io.BytesIO(z.read(f"stage/data/raw/{g}_game_stats/{SUFFIX}")),
                dtype={"minutes": str},
            )
            for g in ["player", "team"]
        }
        accepted_player_adv = z.read(f"stage/data/raw/player_season_advanced/{SUFFIX}")
    require(
        set(primary.GAME_ID.astype(int)) == set(core["player"].game_id), "Source game scope differs"
    )
    ts_ledgers = {}
    for grain, identity in [("player", "PLAYER_ID"), ("team", "TEAM_ID")]:
        original = primary.groupby(identity)[["PTS", "FGA", "FTA"]].sum()
        canonical = core[grain].groupby(identity.lower())[["pts", "fga", "fta"]].sum()
        snapshot = snapshots[grain].set_index(identity)
        require(
            set(original.index) == set(canonical.index) == set(snapshot.index),
            "TS identity scope differs",
        )
        expected_gp = (
            primary.groupby(identity).size()
            if grain == "player"
            else primary.groupby(identity).GAME_ID.nunique()
        )
        require(snapshot.GP.eq(expected_gp).all(), "Advanced GP differs from raw count basis")
        rows = []
        for ident in original.index:
            counts = [int(original.loc[ident, c]) for c in ["PTS", "FGA", "FTA"]]
            correct = [int(canonical.loc[ident, c]) for c in ["pts", "fga", "fta"]]
            source_ratio, canonical_ratio = true_shooting(*counts), true_shooting(*correct)
            literal = Fraction(str(snapshot.loc[ident, "TS_PCT"]))
            require(
                abs(source_ratio - literal) <= Fraction(1, 2000),
                "Reported TS lacks established raw count basis",
            )
            rows.append(
                dict(
                    identity=int(ident),
                    original_counts=counts,
                    canonical_counts=correct,
                    original_exact_ts=str(source_ratio),
                    canonical_exact_ts=str(canonical_ratio),
                    literal_reported_ts=str(literal),
                    reported_matches_original_basis=True,
                    reported_differs_canonical_basis=abs(canonical_ratio - literal)
                    > Fraction(1, 2000),
                )
            )
        ts_ledgers[grain] = rows
    minute_ledger = []
    reported = snapshots["player"].set_index("PLAYER_ID")
    for pid, rows in primary.groupby("PLAYER_ID"):
        lo, hi = minute_mean_interval(rows.MIN.astype(str))
        mean = sum((Fraction(str(v)) for v in rows.MIN), Fraction(0)) / len(rows)
        value = Fraction(str(reported.loc[pid, "MIN"]))
        lower, upper = value - Fraction(1, 20), value + Fraction(1, 20)
        require(
            hi >= lower and lo <= upper, "Reported minute basis differs from retained raw game logs"
        )
        boundary = lo <= lower <= hi or lo <= upper <= hi
        minute_ledger.append(
            dict(
                player_id=int(pid),
                game_ids=sorted(set(rows.GAME_ID.astype(str))),
                retained_event_game_ids=sorted(set(rows.GAME_ID.astype(str)) & set(event_sources)),
                missing_event_game_ids=sorted(set(rows.GAME_ID.astype(str)) - set(event_sources)),
                precise_clock_requirement=(
                    "Unique exact full-player clock vectors over every listed game, with "
                    "qualified whole identity/period evidence, or independent official precise "
                    "timing and an established rounding policy. Retained PBP presence is not "
                    "proof of unique timing; no reacquisition of listed retained originals."
                )
                if boundary
                else None,
                reported_minutes=str(value),
                raw_mean=str(mean),
                raw_mean_interval=[str(lo), str(hi)],
                state="real_clock_boundary_unknown" if boundary else "raw_basis_rounding_matches",
            )
        )
    # GP1 exposes an entire independent timing population, not an inferred
    # nearest-grid clock. Existing inclusive0.05minute comparison is unchanged.
    pid, gid = 1641712, "0022600163"
    sample = primary.loc[primary.PLAYER_ID.eq(pid)]
    require(
        len(sample) == 1
        and sample.GAME_ID.astype(str).tolist() == [gid]
        and reported.loc[pid, "GP"] == 1,
        "Exact clock boundary qualification requires the sole GP1 game",
    )
    canonical_sample = core["player"].loc[core["player"].player_id.eq(pid)]
    require(
        len(canonical_sample) == 1 and canonical_sample.game_id.tolist() == [int(gid)],
        "Canonical exact clock sample differs",
    )
    whole = json.loads(whole163)["boxScoreTraditional"]
    facts = period_facts(
        events163,
        game_id=gid,
        final_teams={
            whole[side]["teamId"]: whole[side]["statistics"]["points"]
            for side in ["homeTeam", "awayTeam"]
        },
    )
    clocks = clock_facts(events163, whole163, period_report=facts)
    tid = int(sample.TEAM_ID.iloc[0])
    exact_seconds = sum(
        (clocks[q][tid].get(pid, Fraction(0)) for q in facts["periods"]), Fraction(0)
    )
    require(exact_seconds == 123, "Retained complete event vector changed")
    reported_minutes = Fraction(str(reported.loc[pid, "MIN"]))
    residual = abs(reported_minutes - exact_seconds / 60)
    require(residual <= Fraction(1, 20), "Exact clock exceeds existing inclusive minute comparison")
    exact_clock_qualification = dict(
        player_id=pid,
        game_ids=[gid],
        games=1,
        exact_seconds=str(exact_seconds),
        exact_mean_minutes=str(exact_seconds / 60),
        reported_minutes=str(reported_minutes),
        absolute_residual_minutes=str(residual),
        unchanged_inclusive_limit_minutes="1/20",
        state="qualified_exact_clock_boundary",
        source_sha256=dict(
            events=hashlib.sha256(events163).hexdigest(), whole=hashlib.sha256(whole163).hexdigest()
        ),
        source_events=len(json.loads(events163)["game"]["actions"]),
        original_event_order_preserved=True,
        rounding_policy_invented=False,
    )
    for row in minute_ledger:
        row["independent_timing_state"] = (
            "qualified_exact_clock_boundary"
            if row["player_id"] == pid
            else "real_clock_boundary_unknown"
            if row["state"] == "real_clock_boundary_unknown"
            else "raw_basis_interior_no_boundary_qualification_needed"
        )
    with bound_zip(
        PARTIAL / "collection.zip",
        "03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3",
    ) as z:
        traditional = z.read("sources/boxscoretraditionalv3_0022600116_q1.json")
    with bound_zip(
        RECOVERY / "collection.zip",
        "7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17",
    ) as z:
        advanced = z.read("sources/boxscoreadvancedv3_0022600116_q1.json")
    usage = possession_exposure(
        pbp, _whole_original("0022600116"), traditional, advanced, team_id=1610612746, period=1
    )
    report = dict(
        classification="field_scoped_dual_basis_and_usage_qualification_not_full_acceptance",
        source_hashes={
            name: hashlib.sha256(raw).hexdigest()
            for name, raw in [
                ("primary_player_game_logs", primary_raw),
                ("reported_player_advanced", p_raw),
                ("reported_team_advanced", t_raw),
                ("preserved_accepted_player_advanced", accepted_player_adv),
            ]
        },
        true_shooting=ts_ledgers,
        retained_event_sources=event_sources,
        minute_basis=minute_ledger,
        independent_real_clock_qualifications=[exact_clock_qualification],
        independent_real_clock_qualified_count=1,
        remaining_real_clock_boundary_unknown_player_ids=[
            r["player_id"]
            for r in minute_ledger
            if r["independent_timing_state"] == "real_clock_boundary_unknown"
        ],
        minute_states_scope="raw serialized arithmetic before independent timing qualification",
        independent_usage=usage,
        raw_basis_player_ts_qualified=len(ts_ledgers["player"]),
        raw_basis_team_ts_qualified=len(ts_ledgers["team"]),
        canonical_player_ts_differences=sum(
            r["reported_differs_canonical_basis"] for r in ts_ledgers["player"]
        ),
        canonical_team_ts_differences=sum(
            r["reported_differs_canonical_basis"] for r in ts_ledgers["team"]
        ),
        minute_states=dict(Counter(r["state"] for r in minute_ledger)),
        accepted_values_rewritten=False,
        production_writes=0,
        full_snapshot_accepted=False,
    )
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = qualify(args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "raw_basis_player_ts_qualified",
                    "raw_basis_team_ts_qualified",
                    "canonical_player_ts_differences",
                    "canonical_team_ts_differences",
                    "minute_states",
                ]
            },
            indent=2,
        )
    )
