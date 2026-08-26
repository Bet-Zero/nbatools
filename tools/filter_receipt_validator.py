"""Hold the receipt migration to what the docs claim it covers.

``tools/filter_execution_sweep.py`` cannot see this class of defect: it buckets
every ``no_result`` as REFUSED before looking at the badges, so a non-ok answer
carrying a false applied-filter claim is invisible to it.

Three claims are checked here, and a case has to satisfy all three:

1. **Completeness.** Every filter a migrated route was asked for has a
   serialized final state on the result. A route that quietly returns without
   its ledger fails, on success as well as on refusal.
2. **No false badge.** Every displayed applied-filter badge has an ``applied``
   receipt behind it.
3. **No lost truth.** Every filter with an ``applied`` receipt that has a badge
   shape still shows its badge. This is the half the first version of this
   validator could not see: dropping every badge whenever receipts were absent
   satisfied "no false claims" while destroying the true ones, and scored as a
   pass.

Claim 1 is what fails on a partially migrated build. ``player_game_summary``
declared fifteen filters and marked one; every summary result it returned
therefore had filters with no serialized state at all.

Usage:
    python tools/filter_receipt_validator.py
    python tools/filter_receipt_validator.py --json outputs/receipts.json

Exit code is 1 when any case fails, so this can gate CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nbatools.query_service import (  # noqa: E402
    execute_natural_query,
    execute_structured_query,
)

try:  # pragma: no cover - exercised by running against an older candidate
    from nbatools.commands._filter_receipts import (
        APPLIED,
        MIGRATED_ROUTE_FILTERS,
        RECEIPT_STATES,
        requested_filter_ids,
    )
    from nbatools.query_service import _badge_filter_id
except ImportError:
    # A build that predates the published migration contract. Keep running
    # rather than crashing, so this validator can demonstrate the defect on the
    # candidate it was written to reject.
    APPLIED = "applied"
    RECEIPT_STATES = frozenset(
        {"applied", "unsupported", "unresolved", "not_evaluated", "coverage_unavailable"}
    )
    MIGRATED_ROUTE_FILTERS = {}

    def requested_filter_ids(route: str, kwargs: dict[str, Any]) -> set[str]:  # noqa: ARG001
        return set()

    def _badge_filter_id(badge: dict[str, Any]) -> str | None:
        if badge.get("kind") == "threshold":
            return "threshold"
        return str(badge.get("label", "")) or None


PASS = "PASS"
FALSE_CLAIM = "FALSE_CLAIM"
MISSING_RECEIPT = "MISSING_RECEIPT"
LOST_BADGE = "LOST_BADGE"
WRONG_ROUTE = "WRONG_ROUTE"
ERROR = "ERROR"

# Filters that always render a badge when they run. Used for claim 3: an
# ``applied`` receipt for one of these with no badge means the truthful context
# was thrown away. Filters whose badge shape depends on other slots (thresholds
# carry the stat name, season/date badges are built from several fields) are
# deliberately absent - their absence is not evidence of loss.
_BADGE_BACKED_FILTERS = frozenset(
    {
        "opponent",
        "home_only",
        "away_only",
        "wins_only",
        "losses_only",
        "clutch",
        "quarter",
        "half",
        "role",
        "position_filter",
        "with_player",
        "without_player",
        "back_to_back",
        "one_possession",
        "nationally_televised",
        "special_event",
    }
)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
#
# One entry per (route, result-path) the migration claims. ``expect`` pins the
# states a case exists to prove; every other requested filter still has to carry
# some legal state, which is claim 1.

NATURAL_CASES: list[dict[str, Any]] = [
    # -- player_game_finder ------------------------------------------------
    {
        "query": "Tatum clutch stats at home on January 1 2024",
        "route": "player_game_finder",
        "why": "finder short-circuit: date/location empty the sample before clutch",
        "expect": {"date_range": APPLIED, "home_only": APPLIED, "clutch": "not_evaluated"},
    },
    {
        "query": "Nikola Jokic games with over 80 points this season",
        "route": "player_game_finder",
        "why": "finder truthful no_match: the threshold really ran",
        "expect": {"threshold": APPLIED},
    },
    {
        "query": "LeBron James games with over 30 points at home this season",
        "route": "player_game_finder",
        "why": "finder success carries receipts",
        "expect": {"threshold": APPLIED, "home_only": APPLIED},
    },
    {
        "query": "Tatum 4th quarter stats on January 1 2024",
        "route": "player_game_finder",
        "why": "finder period path",
    },
    # -- player_game_summary ----------------------------------------------
    {
        "query": "Stephen Curry stats at home in wins this season",
        "route": "player_game_summary",
        "why": "summary success carries receipts",
        "expect": {"home_only": APPLIED, "wins_only": APPLIED},
    },
    {
        "query": "Stephen Curry clutch averages at home on January 1 2024",
        "route": "player_game_summary",
        "why": "summary early empty sample before clutch",
        "expect": {"date_range": APPLIED, "home_only": APPLIED, "clutch": "not_evaluated"},
    },
    {
        "query": "Stephen Curry clutch stats this season",
        "route": "player_game_summary",
        "why": "summary clutch coverage failure",
        "expect": {"clutch": "coverage_unavailable"},
    },
    {
        "query": "Nikola Jokic stats on back to back games this season",
        "route": "player_game_summary",
        "why": "summary schedule-context path",
    },
    # -- season_leaders ----------------------------------------------------
    {
        "query": "top scorers among starters on January 1 2024",
        "route": "season_leaders",
        "why": "leaderboard role coverage failure after the date filter ran",
        "expect": {"date_range": APPLIED, "role": "coverage_unavailable"},
    },
    {
        "query": "top scorers at home this season",
        "route": "season_leaders",
        "why": "leaderboard success carries receipts",
        "expect": {"home_only": APPLIED},
    },
    {
        "query": "top scorers on January 1 1970",
        "route": "season_leaders",
        "why": "leaderboard truthful no_match after the date filter ran",
    },
    {
        "query": "top scorers among guards this season",
        "route": "season_leaders",
        "why": "leaderboard position filter",
        "expect": {"position_filter": APPLIED},
    },
    # -- team_record -------------------------------------------------------
    {
        "query": "Lakers clutch record on January 1 2024",
        "route": "team_record",
        "why": "team record short-circuit: date empties the sample before clutch",
        "expect": {"date_range": APPLIED, "clutch": "not_evaluated"},
    },
    {
        "query": "Lakers record without LeBron James",
        "route": "team_record",
        "why": "team record availability success",
        "expect": {"without_player": APPLIED},
    },
    {
        "query": "Lakers record at home this season",
        "route": "team_record",
        "why": "team record location success",
        "expect": {"home_only": APPLIED},
    },
    {
        "query": "Celtics record in the 4th quarter this season",
        "route": "team_record",
        "why": "team record period path",
        "expect": {"quarter": APPLIED},
    },
    {
        "query": "Lakers record on back to back games this season",
        "route": "team_record",
        "why": "team record schedule-context path",
    },
]

STRUCTURED_CASES: list[dict[str, Any]] = [
    {
        "route": "player_game_finder",
        "kwargs": {
            "player": "Jayson Tatum",
            "season": "2023-24",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "home_only": True,
            "clutch": True,
        },
        "why": "structured finder: same short-circuit as the natural path",
        "expect": {"date_range": APPLIED, "home_only": APPLIED, "clutch": "not_evaluated"},
    },
    {
        "route": "player_game_summary",
        "kwargs": {"player": "Stephen Curry", "season": "2024-25", "home_only": True},
        "why": "structured summary success",
        "expect": {"home_only": APPLIED},
    },
    {
        "route": "player_game_summary",
        "kwargs": {
            "player": "Stephen Curry",
            "season": "2023-24",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "clutch": True,
            "role": "starter",
        },
        "why": "structured summary: clutch and role after a one-day window",
    },
    {
        "route": "season_leaders",
        "kwargs": {"season": "2024-25", "stat": "pts", "home_only": True},
        "why": "structured leaderboard success",
        "expect": {"home_only": APPLIED},
    },
    {
        "route": "team_record",
        "kwargs": {"team": "LAL", "season": "2024-25", "home_only": True},
        "why": "structured team record success",
        "expect": {"home_only": APPLIED},
    },
    {
        "route": "team_record",
        "kwargs": {
            "team": "LAL",
            "season": "2023-24",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "clutch": True,
        },
        "why": "structured team record short-circuit",
        "expect": {"date_range": APPLIED, "clutch": "not_evaluated"},
    },
    {
        "route": "player_game_summary",
        "kwargs": {"player": "LeBron James", "season": "2024-25", "rest_days": 0},
        "why": "structured summary: rest_days=0 is a request, not an absent slot",
        "expect": {"rest_days": APPLIED},
    },
]


def _receipts_of(executed: Any) -> dict[str, Any]:
    metadata = getattr(executed.result, "metadata", None) or {}
    receipts = metadata.get("filter_receipts")
    return receipts if isinstance(receipts, dict) else {}


def _evaluate(
    executed: Any,
    route: str,
    kwargs: dict[str, Any],
    expect: dict[str, Any],
) -> dict[str, Any]:
    metadata = executed.metadata or {}
    badges = metadata.get("applied_filters") or []
    receipts = _receipts_of(executed)
    states = {k: v.get("state") for k, v in receipts.items() if isinstance(v, dict)}

    problems: list[str] = []
    verdict = PASS

    actual_route = executed.route or metadata.get("route")
    if actual_route != route:
        return {
            "verdict": WRONG_ROUTE,
            "route": actual_route,
            "expected_route": route,
            "problems": [f"routed to {actual_route!r}, case is about {route!r}"],
            "status": executed.result_status,
            "receipts": states,
        }

    # Claim 1: every requested tracked filter has a legal serialized state.
    for filter_id in sorted(requested_filter_ids(route, kwargs)):
        state = states.get(filter_id)
        if state is None:
            problems.append(f"{filter_id}: requested but absent from the serialized ledger")
            verdict = MISSING_RECEIPT
        elif state not in RECEIPT_STATES:
            problems.append(f"{filter_id}: illegal receipt state {state!r}")
            verdict = MISSING_RECEIPT

    # Claim 2: no badge without an applied receipt.
    badge_ids: set[str] = set()
    for badge in badges:
        filter_id = _badge_filter_id(badge)
        if filter_id:
            badge_ids.add(filter_id)
        if filter_id not in states:
            # Not a filter this route reports on; the bounded fallback rule in
            # result_contracts.md governs it, not this validator.
            continue
        if states[filter_id] != APPLIED:
            problems.append(
                f"{badge.get('label')}={badge.get('value')} shown with receipt "
                f"{states[filter_id]!r}"
            )
            verdict = FALSE_CLAIM

    # Claim 3: no applied receipt silently loses its badge.
    for filter_id, state in states.items():
        if state != APPLIED or filter_id not in _BADGE_BACKED_FILTERS:
            continue
        if filter_id not in badge_ids:
            problems.append(f"{filter_id}: applied receipt but no badge shown")
            if verdict == PASS:
                verdict = LOST_BADGE

    # Pinned expectations for what this case exists to prove.
    for filter_id, expected_state in expect.items():
        actual = states.get(filter_id)
        if actual != expected_state:
            problems.append(f"{filter_id}: expected receipt {expected_state!r}, got {actual!r}")
            if verdict == PASS:
                verdict = MISSING_RECEIPT

    return {
        "verdict": verdict,
        "route": actual_route,
        "status": executed.result_status,
        "reason": executed.result_reason,
        "badges": [f"{b.get('label')}={b.get('value')}" for b in badges],
        "receipts": states,
        "requested": sorted(requested_filter_ids(route, kwargs)),
        "unevaluated_filters": metadata.get("unevaluated_filters"),
        "unsupported_filters": metadata.get("unsupported_filters"),
        "problems": problems,
    }


def _check_natural(case: dict[str, Any]) -> dict[str, Any]:
    query = case["query"]
    try:
        executed = execute_natural_query(query)
    except Exception as exc:  # noqa: BLE001 - the validator reports, never raises
        return {"path": "natural", "case": query, "verdict": ERROR, "problems": [repr(exc)]}
    kwargs = dict(executed.metadata.get("route_kwargs") or {})
    if not kwargs:
        # query_service does not republish route_kwargs; rebuild the request
        # view from the metadata it does publish.
        kwargs = _request_view(executed.metadata or {})
    row = _evaluate(executed, case["route"], kwargs, case.get("expect") or {})
    row.update({"path": "natural", "case": query, "why": case["why"]})
    return row


def _request_view(metadata: dict[str, Any]) -> dict[str, Any]:
    """Route-kwarg-shaped view of what the parser asked the route for."""
    return {
        "opponent": metadata.get("opponent"),
        "home_only": metadata.get("home_only"),
        "away_only": metadata.get("away_only"),
        "wins_only": metadata.get("wins_only"),
        "losses_only": metadata.get("losses_only"),
        "start_date": metadata.get("start_date"),
        "end_date": metadata.get("end_date"),
        "last_n": metadata.get("last_n"),
        "min_value": metadata.get("min_value"),
        "max_value": metadata.get("max_value"),
        "conditions": metadata.get("conditions"),
        "quarter": metadata.get("quarter"),
        "half": metadata.get("half"),
        "opponent_player": metadata.get("opponent_player"),
        "with_player": metadata.get("with_player"),
        "without_player": metadata.get("without_player"),
        "special_event": metadata.get("special_event"),
        "clutch": metadata.get("clutch"),
        "role": metadata.get("role"),
        "position": metadata.get("position_filter"),
        "back_to_back": metadata.get("back_to_back"),
        "rest_days": metadata.get("rest_days"),
        "one_possession": metadata.get("one_possession"),
        "nationally_televised": metadata.get("nationally_televised"),
    }


def _check_structured(case: dict[str, Any]) -> dict[str, Any]:
    route, kwargs = case["route"], case["kwargs"]
    label = f"{route}({', '.join(f'{k}={v!r}' for k, v in kwargs.items())})"
    try:
        executed = execute_structured_query(route, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return {"path": "structured", "case": label, "verdict": ERROR, "problems": [repr(exc)]}
    row = _evaluate(executed, route, kwargs, case.get("expect") or {})
    row.update({"path": "structured", "case": label, "why": case["why"]})
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write full results here")
    args = parser.parse_args()

    rows = [_check_natural(case) for case in NATURAL_CASES]
    rows += [_check_structured(case) for case in STRUCTURED_CASES]

    covered = {row.get("route") for row in rows if row.get("verdict") != ERROR}
    for row in rows:
        marker = "ok  " if row["verdict"] == PASS else "FAIL"
        print(f"  {marker}  [{row['path']}] {row['case']}")
        for problem in row.get("problems") or []:
            print(f"          {row['verdict']}: {problem}")

    missing_routes = sorted(set(MIGRATED_ROUTE_FILTERS) - covered)
    failures = [row for row in rows if row["verdict"] != PASS]

    print()
    print(f"cases: {len(rows)}  pass: {len(rows) - len(failures)}  fail: {len(failures)}")
    advertised = set(MIGRATED_ROUTE_FILTERS)
    print(f"routes covered: {len(covered & advertised)}/{len(advertised)}")
    if missing_routes:
        print(f"  advertised but unexercised: {', '.join(missing_routes)}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "cases": rows,
                    "routes_advertised": sorted(MIGRATED_ROUTE_FILTERS),
                    "routes_covered": sorted(c for c in covered if c),
                    "failures": len(failures),
                },
                indent=2,
                default=str,
            )
        )
        print(f"full results: {args.json}")

    return 1 if failures or missing_routes else 0


if __name__ == "__main__":
    raise SystemExit(main())
