"""One exact report-time check on the original named team matchup."""

from __future__ import annotations

import re
from decimal import Decimal


def read_request(text: str, out: dict) -> dict | None:
    from nbatools.commands._latest_original_both import _read_scalar_request
    from nbatools.commands._parse_helpers import extract_threshold_conditions

    bounds = extract_threshold_conditions(text, exact_stat="minutes")
    if len(bounds) != 1 or bounds[0]["stat"] != "minutes":
        return None
    bound = bounds[0]
    if re.search(r"%|\bpercent\b", bound["text"]):
        return None
    # Play directly governs this bound. Removing only its fully read span
    # leaves the same complete scalar identity/static original-game scope.
    if not re.search(r"\bplay(?:ed|s)?\s*$", text[: bound["start"]]):
        return None
    remaining = re.sub(r"\s+", " ", text[: bound["start"]] + text[bound["end"] :]).strip()
    request = _read_scalar_request(remaining, out)
    if not request or not request["team"] or not request["opponent"]:
        return None
    return {
        **request,
        "checks": [
            {
                k: bound[k]
                for k in ("stat", "min_value", "max_value", "min_inclusive", "max_inclusive")
            }
        ],
    }


def check_description(check: dict) -> str:
    parts = []
    for edge, inclusive, symbol in (
        ("min_value", "min_inclusive", ">"),
        ("max_value", "max_inclusive", "<"),
    ):
        if check.get(edge) is not None:
            sign = symbol + ("=" if check[inclusive] else "")
            number = int(check[edge]) if float(check[edge]).is_integer() else check[edge]
            parts.append(f"{sign} {number}")
    return " and ".join(parts) + " minutes"


def passes(seconds: int, check: dict) -> bool:
    value = Decimal(seconds)
    low, high = check.get("min_value"), check.get("max_value")
    if low is not None:
        cutoff = Decimal(str(low)) * 60
        if value < cutoff or (value == cutoff and not check["min_inclusive"]):
            return False
    if high is not None:
        cutoff = Decimal(str(high)) * 60
        if value > cutoff or (value == cutoff and not check["max_inclusive"]):
            return False
    return True


def answer_phrase(row, player: str, check: dict, seconds: int | None) -> str:
    import pandas as pd

    truth = seconds is not None and passes(seconds, check)
    fact = "did not play" if seconds is None else f"played {seconds // 60}:{seconds % 60:02d}"
    day = str(pd.Timestamp(row.game_date).date())
    return (
        f"{'Yes' if truth else 'No'}: {player} {fact} in the {row.team_name}' latest original "
        f"game against the {row.opponent_team_name} ({day}); the check was played "
        f"{check_description(check)}."
    )
