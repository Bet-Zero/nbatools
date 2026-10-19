"""Exact report-time and optional player-count checks on one original matchup."""

from __future__ import annotations

import re
from decimal import Decimal, localcontext


def read_request(text: str, out: dict) -> dict | None:
    from nbatools.commands._latest_original_both import _read_scalar_request
    from nbatools.commands._parse_helpers import extract_stat_predicate_spans
    from nbatools.commands.natural_query import _YES_NO_STATS

    bounds = extract_stat_predicate_spans(
        text, exact_stat=_YES_NO_STATS, preserve_numeric_text=True
    )
    if len(bounds) not in (1, 2) or len({b["stat"] for b in bounds}) != len(bounds):
        return None
    minutes = [b for b in bounds if b["stat"] == "minutes"]
    if len(minutes) != 1 or not re.fullmatch(r"play(?:ed|s)?", minutes[0].get("verb") or ""):
        return None
    if any(
        b["stat"] not in _YES_NO_STATS or re.search(r"%|\bpercent\b", b["text"]) for b in bounds
    ):
        return None
    if len(bounds) == 2:
        # A range's inner AND is already inside its bound span. The one
        # remaining connector must join the same actor's two predicates.
        if not re.fullmatch(r"\s*,?\s+and\s+", text[bounds[0]["end"] : bounds[1]["start"]]):
            return None
        count = next(b for b in bounds if b["stat"] != "minutes")
        if (count.get("verb") or "").startswith("play"):
            return None
    # Reuse the scalar full identity/scope reader after removing only the
    # two complete governed predicates and their validated connector.
    remaining = re.sub(
        r"\s+", " ", text[: bounds[0]["start"]] + "play" + text[bounds[-1]["end"] :]
    ).strip()
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
            for bound in sorted(bounds, key=lambda b: b["stat"] != "minutes")
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
            value = Decimal(str(check[edge]))
            number = int(value) if value == value.to_integral_value() else check[edge]
            parts.append(f"{sign} {number}")
    unit = "minutes" if check["stat"] == "minutes" else check["stat"].upper()
    return " and ".join(parts) + " " + unit


def passes(seconds: int, check: dict) -> bool:
    value = Decimal(seconds)
    low, high = check.get("min_value"), check.get("max_value")

    def cutoff(bound):
        number = Decimal(str(bound))
        if check["stat"] != "minutes":
            return number
        # Multiplication must not round a long original decimal literal back
        # across the exact report-second boundary under Decimal's default28.
        with localcontext() as context:
            context.prec = max(context.prec, len(number.as_tuple().digits) + 2)
            return number * 60

    if low is not None:
        bound = cutoff(low)
        if value < bound or (value == bound and not check["min_inclusive"]):
            return False
    if high is not None:
        bound = cutoff(high)
        if value > bound or (value == bound and not check["max_inclusive"]):
            return False
    return True


def answer_phrase(
    row,
    player: str,
    check: dict,
    seconds: int | None,
    *,
    count_check: dict | None = None,
    count: int | None = None,
) -> str:
    import pandas as pd

    truth = seconds is not None and passes(seconds, check)
    if count_check is not None:
        truth = truth and count is not None and passes(count, count_check)
    fact = "did not play" if seconds is None else f"played {seconds // 60}:{seconds % 60:02d}"
    if count_check and seconds is not None:
        fact += f" with {count} {count_check['stat'].upper()}"
    day = str(pd.Timestamp(row.game_date).date())
    return (
        f"{'Yes' if truth else 'No'}: {player} {fact} in the {row.team_name}' latest original "
        f"game against the {row.opponent_team_name} ({day}); the check was played "
        f"{check_description(check)}"
        + (f" and {check_description(count_check)}" if count_check else "")
        + "."
    )


def same_game_count(row, player: str, seasons: list[str], season_type: str, stat: str) -> int:
    """A real count on the exact qualified positive appearance, never DNPzero."""
    import math

    import pandas as pd

    from nbatools.commands._participation_observations import qualified_report_observation
    from nbatools.commands.data_utils import load_player_games_for_seasons

    report = qualified_report_observation(row, player, seasons, season_type)
    if report.participation_state != "played":
        raise ValueError(f"No qualified same-game {stat.upper()} for {player}")
    frame = load_player_games_for_seasons(seasons, season_type)
    required = {"game_id", "game_date", "player_id", "player_name", "team_id", stat}
    if not required.issubset(frame.columns):
        raise ValueError(f"No qualified same-game {stat.upper()} for {player}")
    rows = frame.loc[pd.to_numeric(frame.player_id, errors="coerce").eq(int(report.player_id))]
    rows = rows.loc[
        rows.game_id.astype(int).eq(int(row.game_id))
        & pd.to_datetime(rows.game_date).dt.date.eq(pd.Timestamp(row.game_date).date())
        & pd.to_numeric(rows.team_id, errors="coerce").eq(int(report.team_id))
    ]
    if len(rows) != 1 or stat not in rows:
        raise ValueError(f"No qualified same-game {stat.upper()} for {player}")
    try:
        value = float(rows.iloc[0][stat])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"No qualified same-game {stat.upper()} for {player}") from exc
    if not math.isfinite(value) or value < 0 or not value.is_integer():
        raise ValueError(f"No qualified same-game {stat.upper()} for {player}")
    return int(value)
