"""Bounded retained 0144 foul-credit qualification; no acquisition or publication.

Elapsed lineups, scoring credit, plays and possessions are separate evidence.
Reported Advanced denominators are consulted only after event replay. This is
not a general NBA possession importer or a repair of the original responses.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from tools.period_event_evidence import _alias, clock_facts, event_clock, period_facts, require
from tools.qualify_scoring_basis import SHOOTING, shooting_counts

GAME = "0022600144"
FT = re.compile(r"Free Throw ([123]) of ([123])")


def event_basis(raw, whole_raw):
    """Derive the observed Q1/Q2 credit ledger before reading period statistics."""
    whole = json.loads(whole_raw)["boxScoreTraditional"]
    require(whole["gameId"] == GAME, "Only retained 0144 credit scope is qualified")
    teams = {whole[s]["teamId"]: whole[s] for s in ["homeTeam", "awayTeam"]}
    facts = period_facts(
        raw, game_id=GAME, final_teams={tid: t["statistics"]["points"] for tid, t in teams.items()}
    )
    trace = []
    clocks = clock_facts(raw, whole_raw, period_report=facts, trace=trace)
    lineups = {r["action_id"]: r["lineups"] for r in trace}
    rows = json.loads(raw)["game"]["actions"]
    aliases = {}
    for tid, team in teams.items():
        index = defaultdict(set)
        for p in team["players"]:
            for name in [p["familyName"], re.sub(r"\s+Jr\.?$", "", p["familyName"])]:
                index[_alias(name)].add(p["personId"])
                for n in range(1, len(p["firstName"]) + 1):
                    index[_alias(p["firstName"][:n] + " " + name)].add(p["personId"])
        aliases[tid] = index
    result = {}
    for q in [1, 2]:
        acts = [r for r in rows if r["period"] == q]
        credit, andones, deadball, ft_trips = {}, {}, set(), Counter()
        ft_ledger = []
        for r in acts:
            if r["actionType"] != "Free Throw":
                continue
            aid, tid, pid = r["actionId"], r["teamId"], r["personId"]
            technical = r["subType"] == "Free Throw Technical"
            match = FT.fullmatch(r["subType"])
            require(technical or match is not None, "Unsupported free-throw trip")
            fouls = [
                a
                for a in acts
                if a["actionId"] < aid
                and a["clock"] == r["clock"]
                and a["actionType"] == "Foul"
                and (a["subType"] == "Technical" if technical else a["subType"] == "Shooting")
            ]
            require(len(fouls) == 1, "Free throw lacks unique same-clock foul credit")
            anchor = fouls[0]
            require(
                anchor["teamId"] == 0
                if technical
                else anchor["teamId"] in teams and anchor["teamId"] != tid,
                "Free-throw foul ownership differs",
            )
            credit[aid] = lineups[anchor["actionId"]]
            if match:
                group = [
                    a
                    for a in acts
                    if a["clock"] == r["clock"]
                    and a["teamId"] == tid
                    and a["personId"] == pid
                    and FT.fullmatch(a["subType"])
                ]
                require(
                    [FT.fullmatch(a["subType"])[1] for a in group]
                    == list(map(str, range(1, int(match[2]) + 1)))
                    and all(FT.fullmatch(a["subType"])[2] == match[2] for a in group),
                    "Incomplete or conflicting free-throw trip",
                )
                if match[1] == "1":
                    if match[2] == "1":
                        made = [
                            a
                            for a in acts
                            if a["actionType"] == "Made Shot"
                            and a["clock"] == r["clock"]
                            and a["teamId"] == tid
                            and a["personId"] == pid
                            and a["actionId"] < anchor["actionId"]
                        ]
                        require(len(made) == 1, "And-one lacks unique made-shot link")
                        andones[made[0]["actionId"]] = aid
                    else:
                        ft_trips[pid] += 1
                if match[1] != match[2] and r["description"].startswith("MISS "):
                    following = rows[aid]
                    require(
                        following["actionType"] == "Rebound"
                        and following["teamId"] == 0
                        and following["personId"] == tid
                        and following["clock"] == r["clock"],
                        "Nonfinal missed FT lacks bound dead-ball rebound",
                    )
                    deadball.add(following["actionId"])
            ft_ledger.append(
                dict(
                    action_id=aid,
                    foul_action_id=anchor["actionId"],
                    technical=technical,
                    credit_lineups=credit[aid],
                    elapsed_lineups=lineups[aid],
                )
            )
        counts = Counter()
        teammate_fgm, rebound_chances = Counter(), Counter()
        points_for, points_against = Counter(), Counter()
        plays, possessions = [], []
        first = next(
            a
            for a in acts
            if a["actionType"] in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}
        )

        def begin(owner, aid):
            require(owner in teams, "Unknown play ownership")
            return dict(team_id=owner, start_action=aid, seconds=Counter(), scoring_credit=set())

        def finish(unit, aid, target, incomplete=False):
            require(unit is not None, "Play/possession ending without established owner")
            players = {pid for pid, sec in unit["seconds"].items() if sec > 0} | unit[
                "scoring_credit"
            ]
            require(players, "No independently exposed players")
            target.append(
                dict(
                    team_id=unit["team_id"],
                    start_action=unit["start_action"],
                    end_action=aid,
                    players=sorted(players),
                    incomplete=incomplete,
                    elapsed_seconds={pid: str(v) for pid, v in unit["seconds"].items()},
                    scoring_credit_players=sorted(unit["scoring_credit"]),
                )
            )

        play = begin(first["teamId"], acts[0]["actionId"])
        possession = begin(first["teamId"], acts[0]["actionId"])
        previous = event_clock(acts[0]["clock"])
        pending_miss = None
        for r in acts:
            aid, kind, tid, pid = r["actionId"], r["actionType"], r["teamId"], r["personId"]
            if kind == "Substitution":
                continue
            current = event_clock(r["clock"])
            for unit in [play, possession]:
                if unit is not None:
                    for player in lineups[aid][unit["team_id"]]:
                        unit["seconds"][player] += previous - current
            previous = current
            if kind == "Made Shot":
                for player in lineups[aid][tid]:
                    teammate_fgm[player] += player != pid
                assist = re.search(r"\(([^()]+) \d+ AST\)$", r["description"])
                if assist:
                    candidates = aliases[tid].get(_alias(assist[1]), set())
                    require(len(candidates) == 1, "Ambiguous event assist identity")
                    assistant = next(iter(candidates))
                    require(
                        assistant in lineups[aid][tid] and assistant != pid, "Assist actor absent"
                    )
                    counts[assistant, "assists"] += 1
            if kind == "Rebound" and aid not in deadball:
                owner = tid if tid in teams else pid
                require(owner in teams, "Unknown rebound ownership")
                for values in lineups[aid].values():
                    rebound_chances.update(values)
                if tid in teams:
                    require(pending_miss is not None, "Player rebound lacks a live miss")
                    counts[
                        pid, "reboundsOffensive" if owner == pending_miss else "reboundsDefensive"
                    ] += 1
                    counts[pid, "reboundsTotal"] += 1
            if kind == "Turnover":
                counts[pid, "turnovers"] += 1
            if kind == "Foul" and r["subType"] != "Technical":
                require(
                    r["subType"] in {"Personal", "Shooting", "Offensive", "Personal Take"},
                    "Unsupported personal foul",
                )
                counts[pid, "foulsPersonal"] += 1
            if kind == "" and re.search(r"\b(?:STEAL|BLOCK) \(", r["description"]):
                require(tid in teams and pid in lineups[aid][tid], "Unknown steal/block actor")
                counts[pid, "steals" if " STEAL " in r["description"] else "blocks"] += 1
            made = (
                kind == "Made Shot"
                or kind == "Free Throw"
                and not r["description"].startswith("MISS ")
            )
            if made:
                value = r["shotValue"] if kind == "Made Shot" else 1
                credited = credit.get(aid, lineups[aid])
                for owner, players in credited.items():
                    for player in players:
                        (points_for if owner == tid else points_against)[player] += value
                for unit in [play, possession]:
                    if unit is not None and unit["team_id"] == tid:
                        unit["scoring_credit"].update(credited[tid])
            if kind == "Free Throw" and r["subType"] == "Free Throw Technical":
                require(
                    play is not None and play["team_id"] == tid,
                    "Unqualified technical FT possession state",
                )
                continue
            if kind in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}:
                require(play is not None and play["team_id"] == tid, "Event contradicts play owner")
            if kind == "Made Shot" and aid in andones:
                continue
            match = FT.fullmatch(r["subType"]) if kind == "Free Throw" else None
            terminal = (
                kind in {"Made Shot", "Missed Shot", "Turnover", "Heave"}
                or match
                and match[1] == match[2]
            )
            if terminal:
                require(play is not None and possession is not None, "Unestablished terminal play")
                owner = play["team_id"]
                if kind == "Heave":
                    require(
                        tid == pid == 0 and r["subType"] == "Team Field Goal Attempt",
                        "Unsupported heave",
                    )
                finish(play, aid, plays)
                play = None
                if kind in {"Made Shot", "Turnover"} or kind == "Free Throw" and made:
                    finish(possession, aid, possessions)
                    other = next(t for t in teams if t != owner)
                    play, possession = begin(other, aid), begin(other, aid)
                    pending_miss = None
                else:
                    pending_miss = owner
            elif kind == "Rebound" and aid not in deadball:
                require(
                    play is None and possession is not None and pending_miss is not None,
                    "Rebound lacks unclosed live miss",
                )
                owner = tid if tid in teams else pid
                play = begin(owner, aid)
                if possession["team_id"] != owner:
                    finish(possession, aid, possessions)
                    possession = begin(owner, aid)
                pending_miss = None
            elif kind == "Jump Ball":
                require(play is not None, "Jump ball has no established ownership")
                winner = re.search(r": Tip to (.+)$", r["description"])
                require(winner is not None, "Missing jump-ball winner")
                owners = [owner for owner, index in aliases.items() if index.get(_alias(winner[1]))]
                require(owners == [play["team_id"]], "Jump ball contradicts play ownership")
            elif kind == "period" and r["subType"] == "end":
                if play:
                    finish(play, aid, plays, incomplete=True)
                finish(possession, aid, possessions, incomplete=True)
                play = possession = None
        require(play is possession is None, "Unclosed period evidence")
        result[q] = dict(
            plays=plays,
            possessions=possessions,
            counts=counts,
            ft_trips=ft_trips,
            teammate_fgm=teammate_fgm,
            rebound_chances=rebound_chances,
            points_for=points_for,
            points_against=points_against,
            ft_credit=ft_ledger,
            deadball_rebound_ids=sorted(deadball),
        )
    return dict(
        source_sha256=hashlib.sha256(raw).hexdigest(),
        whole_sha256=hashlib.sha256(whole_raw).hexdigest(),
        facts=facts,
        clocks=clocks,
        periods=result,
    )


def qualify_pair(raw, whole_raw, traditional_raw, advanced_raw, *, start, end):
    """Produce field-scoped copies only after all consumed rates independently agree."""
    require((start, end) in {(1, 1), (2, 2), (1, 2)}, "Unqualified credit window")
    basis = event_basis(raw, whole_raw)
    traditional = json.loads(traditional_raw)
    advanced = json.loads(advanced_raw)
    require(
        traditional["boxScoreTraditional"]["gameId"]
        == advanced["boxScoreAdvanced"]["gameId"]
        == GAME,
        "Credit source identity differs",
    )
    periods = [basis["periods"][q] for q in range(start, end + 1)]
    shooting, _ = shooting_counts(raw, start=start, end=end)
    candidate = copy.deepcopy(traditional)
    changes, cases = [], []

    def total(name, pid):
        return sum(p[name][pid] for p in periods)

    for side in ["homeTeam", "awayTeam"]:
        team = candidate["boxScoreTraditional"][side]
        rates = advanced["boxScoreAdvanced"][side]
        tid = team["teamId"]
        require(
            rates["teamId"] == tid and tid in basis["clocks"][start], "Credit source side differs"
        )
        rate_rows = {p["personId"]: p["statistics"] for p in rates["players"]}
        expected_players = {
            pid
            for q in range(start, end + 1)
            for pid, sec in basis["clocks"][q][tid].items()
            if sec > 0
        }
        from tools.season_rollover_core_bridge import _literal_clock_seconds

        positive = {
            p["personId"]
            for p in team["players"]
            if _literal_clock_seconds(p["statistics"]["minutes"]) > 0
        }
        positive_rates = {
            pid for pid, stats in rate_rows.items() if _literal_clock_seconds(stats["minutes"]) > 0
        }
        require(
            positive == positive_rates == expected_players,
            "Complete credit player population differs",
        )
        for person in team["players"]:
            pid, stats = person["personId"], person["statistics"]
            if pid not in expected_players:
                require(
                    not any(stats[f] for f in SHOOTING), "Zero-duration player has shooting counts"
                )
                continue
            for field in [
                "reboundsOffensive",
                "reboundsDefensive",
                "reboundsTotal",
                "assists",
                "steals",
                "blocks",
                "turnovers",
                "foulsPersonal",
            ]:
                require(
                    stats[field] == sum(p["counts"][pid, field] for p in periods),
                    "Independent event count differs: " + field,
                )
            require(
                stats["plusMinusPoints"] == total("points_for", pid) - total("points_against", pid),
                "Foul-credit margin differs",
            )
            plays = sum(
                pid in play["players"]
                for p in periods
                for play in p["plays"]
                if play["team_id"] == tid
            )
            possessions = sum(
                pid in possession["players"]
                for p in periods
                for possession in p["possessions"]
                if possession["team_id"] == tid
            )
            counts = shooting.get((tid, pid), dict.fromkeys(SHOOTING.values(), 0))
            trips = total("ft_trips", pid)
            numerator = counts["fga"] + stats["turnovers"] + trips
            denominators = {
                "usagePercentage": (numerator, plays),
                "assistPercentage": (stats["assists"], total("teammate_fgm", pid)),
                "reboundPercentage": (stats["reboundsTotal"], total("rebound_chances", pid)),
                "turnoverRatio": (100 * stats["turnovers"], numerator + stats["assists"]),
            }
            require(plays > 0 and possessions > 0, "Missing independent positive exposure")
            offensive_rating = Fraction(100 * total("points_for", pid), possessions)
            require(
                abs(offensive_rating - Fraction(str(rate_rows[pid]["offensiveRating"])))
                <= Fraction(1, 20),
                "Independent offensive rating differs",
            )
            ratios = {}
            for field, (n, d) in denominators.items():
                require(d > 0 or n == 0, "Invalid event rate denominator")
                value = Fraction(n, d) if d else Fraction(0)
                limit = Fraction(1, 20) if field == "turnoverRatio" else Fraction(1, 2000)
                require(
                    abs(value - Fraction(str(rate_rows[pid][field]))) <= limit,
                    "Independent event rate differs: " + field,
                )
                ratios[field] = dict(
                    numerator=n, denominator=d, exact=str(value), reported=rate_rows[pid][field]
                )
            cases.append(
                dict(
                    team_id=tid,
                    player_id=pid,
                    rates=ratios,
                    independent_possessions=possessions,
                    reported_possessions_corroborate=rate_rows[pid]["possessions"] == possessions,
                    credited_points_for=total("points_for", pid),
                    credited_points_against=total("points_against", pid),
                    independent_offensive_rating=str(offensive_rating),
                    original_ts=rate_rows[pid]["trueShootingPercentage"],
                )
            )
        for pid, stats in [
            (0, team["statistics"]),
            *[(p["personId"], p["statistics"]) for p in team["players"]],
        ]:
            counts = shooting.get((tid, pid), dict.fromkeys(SHOOTING.values(), 0))
            for field, col in SHOOTING.items():
                if stats[field] != counts[col]:
                    changes.append(
                        dict(
                            team_id=tid,
                            player_id=pid,
                            field=field,
                            before=stats[field],
                            after=counts[col],
                        )
                    )
                    stats[field] = counts[col]
            for field, numerator, denominator in [
                ("fieldGoalsPercentage", "fgm", "fga"),
                ("threePointersPercentage", "fg3m", "fg3a"),
                ("freeThrowsPercentage", "ftm", "fta"),
            ]:
                value = round(
                    float(Fraction(counts[numerator], counts[denominator]))
                    if counts[denominator]
                    else 0,
                    3,
                )
                if stats[field] != value:
                    changes.append(
                        dict(
                            team_id=tid,
                            player_id=pid,
                            field=field,
                            before=stats[field],
                            after=value,
                        )
                    )
                    stats[field] = value
    # Clock refinement remains the existing independent entire-vector path.
    from tools.qualify_incremental_return import event_clock_copy

    copies, clock_ledger = event_clock_copy(
        {
            "boxscoretraditionalv3": json.dumps(candidate).encode(),
            "boxscoreadvancedv3": advanced_raw,
        },
        raw,
        whole_raw,
        start=start,
        end=end,
    )
    # Restore all deliberately copied fields and clocks to authenticate that no
    # unqualified source value changed. Originals themselves are never written.
    restored = json.loads(copies["boxscoretraditionalv3"])
    for row in changes:
        team = next(
            restored["boxScoreTraditional"][s]
            for s in ["homeTeam", "awayTeam"]
            if restored["boxScoreTraditional"][s]["teamId"] == row["team_id"]
        )
        stats = (
            team["statistics"]
            if row["player_id"] == 0
            else next(p["statistics"] for p in team["players"] if p["personId"] == row["player_id"])
        )
        stats[row["field"]] = row["before"]
    for row in clock_ledger:
        if row["endpoint"] != "boxscoretraditionalv3":
            continue
        team = next(
            restored["boxScoreTraditional"][s]
            for s in ["homeTeam", "awayTeam"]
            if restored["boxScoreTraditional"][s]["teamId"] == row["team_id"]
        )
        next(p["statistics"] for p in team["players"] if p["personId"] == row["player_id"])[
            "minutes"
        ] = row["original_literal"]
    require(restored == traditional, "Unqualified Traditional cell changed")
    # Counters with tuple keys are internal only; emit exact event interval and
    # source-rate proof, never guessed/canonicalized Advanced statistics.
    report = dict(
        game_id=GAME,
        start=start,
        end=end,
        changes=changes,
        clock_ledger=clock_ledger,
        cases=cases,
        periods={
            q: {
                k: v
                for k, v in basis["periods"][q].items()
                if k in {"plays", "possessions", "ft_credit", "deadball_rebound_ids"}
            }
            for q in range(start, end + 1)
        },
        source_sha256={
            name: hashlib.sha256(body).hexdigest()
            for name, body in [
                ("events", raw),
                ("whole", whole_raw),
                ("traditional", traditional_raw),
                ("advanced", advanced_raw),
            ]
        },
        reported_possessions_used_as_oracle=False,
        advanced_rates_rewritten=False,
        full_general_credit_model_accepted=False,
        full_snapshot_accepted=False,
        production_writes=0,
    )
    return copies, report


def retained_inputs(cache):
    """Select one exact retained standard-window request, never another range."""
    from tools.season_rollover_core_bridge import _additional_sources
    from tools.stage_current_season import CURRENT

    sources = _additional_sources(CURRENT.parent)

    def read(endpoint, start, end, range_type):
        matches = [
            r
            for r in cache.data["direct"].values()
            if r["job"]["endpoint"] == endpoint
            and r["job"]["parameters"].get("GameID") == GAME
            and int(r["job"]["parameters"].get("StartPeriod", 0)) == start
            and int(r["job"]["parameters"].get("EndPeriod", 0)) == end
            and int(r["job"]["parameters"].get("RangeType", 0)) == range_type
            and (
                range_type == 0
                or (
                    r["job"]["parameters"].get("StartRange") == 0
                    and r["job"]["parameters"].get("EndRange") == 28800
                )
            )
        ]
        require(len(matches) == 1, "Missing or ambiguous retained request identity")
        return cache.read(matches[0])

    return (
        sources["pbp.json"].raw,
        sources["summary.json"].document,
        read("boxscoretraditionalv3", 0, 0, 0),
        read,
    )


def stage(cache_path: Path, output: Path):
    """Append only the two newly qualified windows through the real importer."""
    from datetime import UTC, datetime

    import pandas as pd

    from nbatools.commands.pipeline import (
        build_game_features,
        build_league_season_stats,
        build_player_game_features,
        build_schedule_context_features,
        build_team_game_features,
        validate_raw,
    )
    from nbatools.commands.pipeline.pull_game_period_stats import PERIOD_WINDOWS
    from nbatools.commands.validation_control import build_slice_manifest
    from tools.assess_readiness_recovery import due_population
    from tools.qualify_incremental_return import bound_zip
    from tools.qualify_rollover_q1 import _local_stage
    from tools.readiness_refresh import SourceCache
    from tools.stage_current_season import CURRENT, SUFFIX, _append_rows
    from tools.stage_rollover_periods import import_window

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = output / "stage"
    previous = {}
    archive = CURRENT.parent / "retained-qualification-20261104/qualification-evidence.zip"
    with bound_zip(
        archive, "8e177a33ee0c8f91e7f6d93c0030d8ef5575f379b09574bb3d71d7f19b3686e4"
    ) as z:
        for name in z.namelist():
            if name.startswith("period-qualification/stage/data/") and name.endswith(".csv"):
                relative = name.removeprefix("period-qualification/stage/")
                raw = z.read(name)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                previous[relative] = raw
    cache = SourceCache(cache_path)
    events, summary, whole, read = retained_inputs(cache)
    players = pd.read_csv(root / f"data/raw/player_game_stats/{SUFFIX}")
    teams = pd.read_csv(root / f"data/raw/team_game_stats/{SUFFIX}")
    context = players.merge(
        teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
    )
    admissions = []
    for start, end in [(2, 2), (1, 2)]:
        pair = {
            ep: read(ep, start, end, 1) for ep in ["boxscoretraditionalv3", "boxscoreadvancedv3"]
        }
        window = next(w for w in PERIOD_WINDOWS if (w.start_period, w.end_period) == (start, end))
        try:
            import_window(
                pair["boxscoretraditionalv3"],
                pair["boxscoreadvancedv3"],
                game_id=GAME,
                window=window,
                summary=summary,
                player_context=context,
                team_context=teams,
            )
        except ValueError as exc:
            require(
                str(exc) == "Period score differs from Summary",
                "Original window failed for unexpected reason",
            )
            original_failure = str(exc)
        else:
            raise ValueError("Uncorrected technical FT original unexpectedly admitted")
        copies, proof = qualify_pair(
            events,
            whole,
            pair["boxscoretraditionalv3"],
            pair["boxscoreadvancedv3"],
            start=start,
            end=end,
        )
        frames = import_window(
            copies["boxscoretraditionalv3"],
            copies["boxscoreadvancedv3"],
            game_id=GAME,
            window=window,
            summary=summary,
            player_context=context,
            team_context=teams,
        )
        for grain, frame in zip(["player", "team"], frames, strict=True):
            path = root / f"data/raw/{grain}_game_period_stats/{SUFFIX}"
            before = pd.read_csv(path)
            require(
                not (
                    before.game_id.eq(int(GAME))
                    & before.period_family.eq(window.period_family)
                    & before.period_value.astype(str).eq(str(window.period_value))
                ).any(),
                "Existing window replacement forbidden",
            )
            _append_rows(path, frame)
        folder = output / f"qualified-copies/{start}-{end}"
        folder.mkdir(parents=True)
        for endpoint, raw in copies.items():
            (folder / (endpoint + ".json")).write_bytes(raw)
        proof["original_import_failure"] = original_failure
        admissions.append(proof)
    stages = []
    with _local_stage(root):
        for fn in [
            validate_raw.run,
            build_team_game_features.run,
            build_game_features.run,
            build_schedule_context_features.run,
            build_player_game_features.run,
            build_league_season_stats.run,
        ]:
            try:
                fn("2026-27", "Regular Season")
            except Exception as exc:
                stages.append(dict(stage=fn.__module__, state="failed", error=str(exc)))
            else:
                stages.append(dict(stage=fn.__module__, state="passed"))
        assessment = build_slice_manifest(
            "2026-27",
            "Regular Season",
            data_root=root / "data",
            generation_id="unpublished-technical-ft-0144",
        )
        due = due_population(root, datetime.now(UTC))
        from nbatools.commands.player_game_finder import build_result

        consumers = []
        for scope in [{"quarter": "2"}, {"half": "first"}]:
            answer = build_result(
                player="Jalen Johnson",
                season="2026-27",
                start_date=str(context.loc[context.game_id.eq(int(GAME)), "game_date"].iloc[0]),
                end_date=str(context.loc[context.game_id.eq(int(GAME)), "game_date"].iloc[0]),
                **scope,
            )
            require(
                answer.result_status == "ok" and set(answer.games.game_id) == {int(GAME)},
                "Qualified technical FT consumer unavailable",
            )
            consumers.append(dict(scope=scope, rows=answer.games.to_dict("records")))
    for name, raw in previous.items():
        observed = (root / name).read_bytes()
        if "/raw/" in name:
            require(
                observed.startswith(raw) if "game_period_stats/" in name else observed == raw,
                "Previously accepted raw bytes changed",
            )
    period = pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}")
    report = dict(
        classification="qualified_0144_credit_not_full_readiness",
        admissions=admissions,
        consumers=consumers,
        admitted_windows=len(
            period[["game_id", "period_family", "period_value"]].drop_duplicates()
        ),
        known_required_windows=647,
        remaining_period_windows=[["0022600142", "quarter", "3"], ["0022600142", "half", "second"]],
        required_raw=11,
        required_processed=5,
        executed_stages=stages,
        dataset_assessment=assessment,
        due_population=due,
        raw_bytes_preserved=True,
        prior_period_prefixes_preserved=True,
        retained_direct_successes=len(cache.data["direct"]),
        full_snapshot_accepted=False,
        production_writes=0,
    )
    (output / "assessment.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    stage(args.cache, args.output)
