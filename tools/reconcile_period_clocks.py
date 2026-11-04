"""Explicit derived clock observations from already qualified disjoint periods.

Malformed original bytes remain quarantined. Only a copied input's affected
minute field may use sum/difference of two independently admitted windows; every
original count/rate cell survives, and the unchanged importer must still pass.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from tools.season_rollover_core_bridge import FIELDS, _literal_clock_seconds

COMPLEMENTS = {
    (1, 1): (((1, 2), 1), ((2, 2), -1)),
    (2, 2): (((1, 2), 1), ((1, 1), -1)),
    (3, 3): (((3, 4), 1), ((4, 4), -1)),
    (4, 4): (((3, 4), 1), ((3, 3), -1)),
    (1, 2): (((1, 1), 1), ((2, 2), 1)),
    (3, 4): (((3, 3), 1), ((4, 4), 1)),
}
KEYS = {"boxscoretraditionalv3": "boxScoreTraditional", "boxscoreadvancedv3": "boxScoreAdvanced"}


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _person(box, side, pid, tid):
    team = box[side]
    found = [p for p in team["players"] if p["personId"] == pid]
    _require(team["teamId"] == tid and len(found) == 1, "Complement player/team identity differs")
    return found[0]["statistics"]


def derive_clocks(key, jobs, independently_admitted):
    gid, start, end = key
    _require((start, end) in COMPLEMENTS, "Unsupported complementary clock window")
    terms = [
        (tuple([gid, *bounds]), coefficient) for bounds, coefficient in COMPLEMENTS[start, end]
    ]
    _require(
        all(k in independently_admitted for k, _ in terms),
        "Clock terms require prior independent importer admission; cycles forbidden",
    )
    originals = jobs[key]
    documents = {name: json.loads(body) for name, body in originals.items()}
    copies = deepcopy(documents)
    ledger = []
    for endpoint, root in KEYS.items():
        box = copies[endpoint][root]
        _require(box["gameId"] == gid, "Target game identity differs")
        for side in ["homeTeam", "awayTeam"]:
            tid = box[side]["teamId"]
            for person in box[side]["players"]:
                literal = person["statistics"]["minutes"]
                try:
                    _literal_clock_seconds(literal)
                except ValueError:
                    pid = person["personId"]
                    observed, seconds = [], 0
                    count_fields = [*FIELDS, "plusMinusPoints"]
                    counts = {f: 0 for f in count_fields}
                    for term, coefficient in terms:
                        source = jobs[term][endpoint]
                        source_box = json.loads(source)[root]
                        _require(source_box["gameId"] == gid, "Complement game identity differs")
                        stats = _person(source_box, side, pid, tid)
                        clock = _literal_clock_seconds(stats["minutes"])
                        seconds += coefficient * clock
                        observed.append(
                            dict(
                                window=list(term),
                                coefficient=coefficient,
                                source_sha256=hashlib.sha256(source).hexdigest(),
                                literal=stats["minutes"],
                                seconds=float(clock),
                            )
                        )
                        # Advanced omits count cells; bind the same exact player's
                        # unchanged target counts to complementary Traditional sources.
                        traditional = json.loads(jobs[term]["boxscoretraditionalv3"])[
                            "boxScoreTraditional"
                        ]
                        traditional_stats = _person(traditional, side, pid, tid)
                        for field in count_fields:
                            counts[field] += coefficient * traditional_stats[field]
                    target_stats = _person(
                        documents["boxscoretraditionalv3"]["boxScoreTraditional"], side, pid, tid
                    )
                    _require(
                        all(counts[f] == target_stats[f] for f in count_fields),
                        "Complementary count basis differs from target player",
                    )
                    _require(
                        seconds.denominator == 1 and 0 < seconds <= (end - start + 1) * 720,
                        "Derived player clock is nonintegral or outside target window",
                    )
                    total = int(seconds)
                    replacement = f"{total // 60}:{total % 60:02d}"
                    person["statistics"]["minutes"] = replacement
                    ledger.append(
                        dict(
                            endpoint=endpoint,
                            game_id=gid,
                            team_id=tid,
                            player_id=pid,
                            original_literal=literal,
                            derived_literal=replacement,
                            derived_seconds=total,
                            terms=observed,
                            original_sha256=hashlib.sha256(originals[endpoint]).hexdigest(),
                        )
                    )
    _require(ledger, "No malformed literal to reconcile; valid residual clocks are never adjusted")
    identities = {(r["team_id"], r["player_id"]) for r in ledger}
    for tid, pid in identities:
        pair = [r for r in ledger if (r["team_id"], r["player_id"]) == (tid, pid)]
        _require(
            len(pair) == 2 and pair[0]["derived_seconds"] == pair[1]["derived_seconds"],
            "Traditional/Advanced derived player clocks differ",
        )
    derived = {
        name: json.dumps(doc, separators=(",", ":")).encode() for name, doc in copies.items()
    }
    for name in derived:
        # Independently compare parsed cells after undoing only explicit changes.
        restored = deepcopy(copies[name])
        for row in ledger:
            if row["endpoint"] == name:
                for side in ["homeTeam", "awayTeam"]:
                    if restored[KEYS[name]][side]["teamId"] == row["team_id"]:
                        _person(restored[KEYS[name]], side, row["player_id"], row["team_id"])[
                            "minutes"
                        ] = row["original_literal"]
        _require(restored == documents[name], "Non-clock target cells changed")
    return derived, ledger
