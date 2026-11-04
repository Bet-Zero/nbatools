"""Field-scoped period/clock evidence from complete retained event originals.

No source event is reordered or dropped. Ambiguous lineups and contradictory
substitutions remain errors; this does not establish general on-court support.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from fractions import Fraction

from tools.season_rollover_core_bridge import _literal_clock_seconds

ACTOR_TYPES = {"Made Shot", "Missed Shot", "Free Throw", "Turnover", "Rebound", "Jump Ball"}


def on_floor_actor(row):
    return row["actionType"] in ACTOR_TYPES or (
        row["actionType"] == "Foul"
        and row.get("subType", "").lower()
        in {"away from play", "loose ball", "offensive", "offensive charge", "personal", "shooting"}
    )


def require(ok, message):
    if not ok:
        raise ValueError(message)


def event_clock(value):
    # Duration normalizers allow blank DNP clocks; an event timestamp never does.
    require(
        isinstance(value, str) and re.fullmatch(r"PT\d+M[0-5]?\d(?:\.\d+)?S", value) is not None,
        "Missing or malformed literal event clock",
    )
    return _literal_clock_seconds(value)


def same_clock_score_evidence(raw, *, game_id, final_teams):
    """Qualify replay scoreboard snapshots without moving an event or its clock.

    Scoring actions retain their literal sequential score assertions. Only a
    non-actor Instant Replay row may report a later, uniquely explained score
    from scoring actions at its identical period/clock. This is an explicit
    metadata interpretation, never an event-order correction.
    """
    rows = json.loads(raw)["game"]["actions"]
    require(json.loads(raw)["game"]["gameId"] == game_id, "Score proof identity differs")
    ids = list(final_teams)
    score = dict.fromkeys(ids, 0)
    states, groups = [], defaultdict(list)
    for row in rows:
        value = 0
        if row["actionType"] == "Made Shot":
            require(row["shotValue"] in [2, 3], "Invalid scoring shot value")
            value = row["shotValue"]
        elif row["actionType"] == "Free Throw" and not row["description"].startswith("MISS "):
            value = 1
        if value:
            require(row["teamId"] in score and row["personId"] > 0, "Scoring actor missing")
            score[row["teamId"]] += value
        states.append(score.copy())
        groups[(row["period"], row["clock"])].append(len(states) - 1)
    require(score == final_teams, "Score proof final total differs")
    observations = []
    for i, row in enumerate(rows):
        literal = {
            tid: int(row[name])
            for tid, name in zip(ids, ["scoreHome", "scoreAway"], strict=True)
            if row[name] not in ["", None]
        }
        if all(states[i][tid] == value for tid, value in literal.items()):
            continue
        require(
            row["actionType"] == "Instant Replay"
            and row["teamId"] == row["personId"] == 0
            and set(literal) == set(ids),
            "Unexplained event score change",
        )
        later = [j for j in groups[(row["period"], row["clock"])] if j > i]
        scorers = [
            j
            for j in later
            if rows[j]["actionType"] == "Made Shot"
            or (
                rows[j]["actionType"] == "Free Throw"
                and not rows[j]["description"].startswith("MISS ")
            )
        ]
        matches = [j for j in scorers if states[j] == literal]
        require(len(matches) == 1, "Replay snapshot lacks unique same-clock scoring explanation")
        target = matches[0]
        require(
            all(
                rows[j]["period"] == row["period"] and rows[j]["clock"] == row["clock"]
                for j in range(i, target + 1)
            ),
            "Replay explanation crosses a clock boundary",
        )
        observations.append(
            dict(
                action_id=row["actionId"],
                period=row["period"],
                clock=row["clock"],
                event_prefix_score=states[i],
                literal_score=literal,
                explaining_scoring_action_ids=[rows[j]["actionId"] for j in scorers if j <= target],
                event_order_changed=False,
                clock_changed=False,
            )
        )
    require(observations, "No same-clock scoreboard metadata requiring qualification")
    return dict(
        source_sha256=hashlib.sha256(raw).hexdigest(),
        observations=observations,
        interpretation="replay_metadata_score_snapshot_at_identical_clock",
    )


def period_facts(raw, *, game_id, final_teams, score_snapshots=None):
    """Check every event, literal period boundary and score transition."""
    qualified_snapshots = {}
    if score_snapshots is not None:
        require(
            score_snapshots
            == same_clock_score_evidence(raw, game_id=game_id, final_teams=final_teams),
            "Score snapshot evidence differs from exact original",
        )
        qualified_snapshots = {item["action_id"]: item for item in score_snapshots["observations"]}
    game = json.loads(raw)["game"]
    require(game["gameId"] == game_id, "Event game identity differs")
    ids = list(final_teams)
    require(len(ids) == 2, "Paired final teams required")
    score = dict.fromkeys(ids, 0)
    ends, starts, periods = {}, set(), set()
    repeated_terminal_markers = []
    previous_period, previous_clock = 1, Fraction(720)
    rows = game["actions"]
    for index, row in enumerate(rows, 1):
        period = row["period"]
        clock = event_clock(row["clock"])
        duration = 720 if period <= 4 else 300
        require(
            type(period) is int
            and 1 <= period <= 14
            and row["actionId"] == index
            and previous_period <= period <= previous_period + 1
            and 0 <= clock <= duration
            and (period > previous_period or clock <= previous_clock),
            "Incomplete or contradictory event chronology",
        )
        periods.add(period)
        if row["actionType"] == "period":
            if row["subType"] == "start":
                require(clock == duration and period not in starts, "Invalid period start")
                starts.add(period)
            elif row["subType"] == "end":
                require(clock == 0, "Invalid period end")
                if period in ends:
                    previous = rows[index - 2]
                    omit = {"actionId", "actionNumber", "videoAvailable"}
                    require(
                        index == len(rows)
                        and index > 1
                        and {k: v for k, v in row.items() if k not in omit}
                        == {k: v for k, v in previous.items() if k not in omit},
                        "Conflicting or nonterminal duplicate period end",
                    )
                    repeated_terminal_markers.append(row["actionId"])
                ends[period] = score.copy()
        value = 0
        if row["actionType"] == "Made Shot":
            require(row["shotValue"] in [2, 3], "Invalid scoring shot value")
            value = row["shotValue"]
        elif row["actionType"] == "Free Throw" and not row["description"].startswith("MISS "):
            value = 1
        if value:
            require(row["teamId"] in score and row["personId"] > 0, "Scoring actor missing")
            score[row["teamId"]] += value
        for tid, name in zip(ids, ["scoreHome", "scoreAway"], strict=True):
            if row[name] not in ["", None]:
                if row["actionId"] in qualified_snapshots:
                    proof = qualified_snapshots[row["actionId"]]
                    require(
                        proof["event_prefix_score"] == score
                        and int(row[name]) == proof["literal_score"][tid],
                        "Score snapshot observation differs",
                    )
                else:
                    require(int(row[name]) == score[tid], "Unexplained event score change")
        previous_period, previous_clock = period, clock
    expected = set(range(1, max(periods) + 1))
    require(
        starts == set(ends) == periods == expected
        and previous_clock == 0
        and rows[-1]["actionType"] == "period"
        and rows[-1]["subType"] == "end"
        and score == final_teams,
        "Incomplete terminal period/score evidence",
    )
    before = dict.fromkeys(ids, 0)
    scores = {}
    for period in sorted(periods):
        scores[period] = {tid: ends[period][tid] - before[tid] for tid in ids}
        before = ends[period]
    return dict(
        game_id=game_id,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        periods=sorted(periods),
        period_count=max(periods),
        period_scores=scores,
        events=len(rows),
        repeated_terminal_markers=repeated_terminal_markers,
        complete_timeline=True,
        canonical_pbp_accepted=False,
        **({"score_snapshot_evidence": score_snapshots} if score_snapshots is not None else {}),
    )


def _alias(value):
    text = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def clock_facts(raw, whole_raw, *, period_report, only_periods=None, trace=None):
    """Infer only uniquely forced five-player lineups; preserve exact source time."""
    game_id = period_report["game_id"]
    whole = json.loads(whole_raw)["boxScoreTraditional"]
    require(whole["gameId"] == game_id, "Whole/event game identity differs")
    checked = period_facts(
        raw,
        game_id=game_id,
        final_teams={
            whole[s]["teamId"]: whole[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
        },
        score_snapshots=period_report.get("score_snapshot_evidence"),
    )
    require(checked == period_report, "Clock evidence does not bind the validated event original")
    teams, aliases, starters = {}, {}, {}
    for side in ["homeTeam", "awayTeam"]:
        team = whole[side]
        tid = team["teamId"]
        teams[tid] = {p["personId"]: p for p in team["players"]}
        require(len(teams[tid]) == len(team["players"]), "Duplicate same-team identity")
        index = defaultdict(set)
        for person in team["players"]:
            families = {
                person["familyName"],
                re.sub(r"\s+(?:Jr\.?|Sr\.?|II|III|IV)$", "", person["familyName"]),
            }
            # A source-provided abbreviated display name can use another
            # family order (e.g. firstName=Hansen/familyName=Yang, Y. Hansen).
            # This is a literal same-player field, never a first-name guess.
            # Keep all identity collisions in the alias set so ambiguity fails.
            display_name = person.get("nameI")
            display = (
                re.fullmatch(r"[^\W\d_]\.\s+(.+)", display_name)
                if isinstance(display_name, str)
                else None
            )
            if display is not None:
                index[_alias(display[1].strip())].add(person["personId"])
                index[_alias(display_name)].add(person["personId"])
            for family in families:
                index[_alias(family)].add(person["personId"])
                # NBA descriptions disambiguate e.g. Jal./Jay. Williams.
                # Every literal prefix is tied to a known same-team identity;
                # collisions stay ambiguous rather than selecting a player.
                for size in range(1, len(person["firstName"]) + 1):
                    index[_alias(person["firstName"][:size] + " " + family)].add(person["personId"])
        aliases[tid] = index
        starters[tid] = {p["personId"] for p in team["players"] if p.get("position", "").strip()}
        require(len(starters[tid]) == 5, "Literal starting positions must supply five players")
    rows = json.loads(raw)["game"]["actions"]
    output = {}
    for period in period_report["periods"]:
        if only_periods is not None and period not in only_periods:
            continue
        subset = [r for r in rows if r["period"] == period]
        substitutions, first, actors = {}, {tid: {} for tid in teams}, {tid: set() for tid in teams}
        for row in subset:
            tid, pid = row["teamId"], row["personId"]
            if row["actionType"] == "Substitution":
                require(tid in teams and pid in teams[tid], "Unknown substitution actor")
                match = re.fullmatch(r"SUB: (.+) FOR (.+)", row["description"])
                require(match is not None, "Unsupported substitution evidence")
                candidates = aliases[tid].get(_alias(match[1]), set())
                require(len(candidates) == 1, "Ambiguous incoming substitution identity")
                incoming = next(iter(candidates))
                require(incoming != pid, "Self substitution")
                substitutions[row["actionId"]] = (tid, pid, incoming)
                first[tid].setdefault(pid, "out")
                first[tid].setdefault(incoming, "in")
            elif on_floor_actor(row) and tid in teams and pid > 0:
                require(pid in teams[tid], "Unknown on-floor event actor")
                actors[tid].add(pid)
        active = {}
        for tid in teams:
            inferred = {p for p, role in first[tid].items() if role == "out"} | (
                actors[tid] - set(first[tid])
            )
            active[tid] = starters[tid].copy() if period == 1 else inferred
            require(len(active[tid]) == 5, "Starting lineup is not uniquely established")
        seconds = {tid: defaultdict(Fraction) for tid in teams}
        previous = Fraction(720 if period <= 4 else 300)
        for row in subset:
            clock = event_clock(row["clock"])
            delta = previous - clock
            require(delta >= 0, "Nonmonotone clock")
            for tid in teams:
                for pid in active[tid]:
                    seconds[tid][pid] += delta
            if row["actionId"] in substitutions:
                tid, outgoing, incoming = substitutions[row["actionId"]]
                require(
                    outgoing in active[tid] and incoming not in active[tid],
                    "Contradictory substitution lineup",
                )
                active[tid].remove(outgoing)
                active[tid].add(incoming)
            elif on_floor_actor(row) and row["teamId"] in teams and row["personId"] > 0:
                require(row["personId"] in active[row["teamId"]], "Event actor absent from lineup")
            if trace is not None and row["actionType"] != "Substitution":
                trace.append(
                    dict(
                        action_id=row["actionId"],
                        period=period,
                        team_id=row["teamId"],
                        player_id=row["personId"],
                        kind=row["actionType"],
                        lineups={tid: sorted(values) for tid, values in active.items()},
                    )
                )
            previous = clock
        duration = 720 if period <= 4 else 300
        require(
            previous == 0 and all(sum(v.values()) == 5 * duration for v in seconds.values()),
            "Incomplete clock denominator",
        )
        output[period] = {tid: dict(values) for tid, values in seconds.items()}
    return output


def usage_event_evidence(raw, whole_raw, traditional_raw, advanced_raw, *, period=1):
    """Independent event ratios, without redefining NBA possession-credit semantics.

    The no-FTA/no-OREB case avoids free-throw trip estimation. End-action plays
    remain a different denominator when NBA credits a partially played possession.
    Mismatches stay unresolved rather than replacing the reported usage value.
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
    traditional = json.loads(traditional_raw)["boxScoreTraditional"]
    advanced = json.loads(advanced_raw)["boxScoreAdvanced"]
    require(
        traditional["gameId"] == advanced["gameId"] == whole["gameId"], "Usage source game differs"
    )
    result = []
    for side in ["homeTeam", "awayTeam"]:
        team = traditional[side]
        tid = team["teamId"]
        require(advanced[side]["teamId"] == tid, "Usage source side differs")
        if team["statistics"]["freeThrowsAttempted"] or team["statistics"]["reboundsOffensive"]:
            continue
        rates = {
            p["personId"]: p["statistics"]["usagePercentage"] for p in advanced[side]["players"]
        }
        for player in team["players"]:
            pid = player["personId"]
            stats = player["statistics"]
            if _literal_clock_seconds(stats["minutes"]) <= 0:
                continue
            actions = [
                r
                for r in trace
                if r["team_id"] == tid and r["kind"] in {"Made Shot", "Missed Shot", "Turnover"}
            ]
            numerator = sum(r["player_id"] == pid for r in actions)
            denominator = sum(pid in r["lineups"][tid] for r in actions)
            require(
                numerator == stats["fieldGoalsAttempted"] + stats["turnovers"],
                "Independent usage numerator differs from direct counts",
            )
            require(
                clocks[period][tid].get(pid, Fraction(0))
                == _literal_clock_seconds(stats["minutes"]),
                "Independent usage sample clock differs",
            )
            require(denominator > 0 and 0 <= rates[pid] <= 1, "Invalid usage observation")
            ratio = Fraction(numerator, denominator)
            result.append(
                dict(
                    game_id=whole["gameId"],
                    period=period,
                    team_id=tid,
                    player_id=pid,
                    independent_numerator=numerator,
                    end_action_denominator=denominator,
                    independent_end_action_ratio=float(ratio),
                    reported_NBA_usage=rates[pid],
                    matches_reported_rounding=abs(ratio - Fraction(str(rates[pid])))
                    <= Fraction(1, 2000),
                )
            )
    require(result, "No independently checkable usage sample; no vacuous pass")
    return dict(
        scope="no_FTA_no_OREB_end_action_sample_not_all_NBA_possession_credits",
        source_event_sha256=facts["source_sha256"],
        cases=result,
        exact_ratio_matches=sum(r["matches_reported_rounding"] for r in result),
        unresolved_credit_semantics=sum(not r["matches_reported_rounding"] for r in result),
        reported_values_rewritten=False,
        full_independent_NBA_usage_accepted=False,
    )
