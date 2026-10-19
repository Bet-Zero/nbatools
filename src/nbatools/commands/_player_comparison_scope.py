"""Complete player operands and a common historical playing-for sample."""

from __future__ import annotations

import re
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from nbatools.commands._constants import STOP_WORDS
from nbatools.commands._matchup_utils import (
    _is_exact_player_reference_phrase,
    detect_player,
)
from nbatools.commands.entity_resolution import (
    TEAM_ALIASES,
    canonical_player_names_by_id,
    player_ids_for_name,
)

_TEAM = "|".join(re.escape(a) for a in sorted(TEAM_ALIASES, key=len, reverse=True))
_SHARED_TEAM = re.compile(
    r"\b(?:(?:(?:while|when)\s+)?(?:each\s+)?(?:playing|played)\s+for"
    r"|(?:only\s+)?(?:in\s+)?their\s+games?\s+for|(?:while\s+)?on|for|as)\s+"
    rf"(?:the\s+)?(?P<team>{_TEAM})(?![\w'-])"
)
_INTENT = re.compile(r"\bcompar(?:e|ing|ison)\b|\bside[ -]by[ -]side\b")
_NAME_END = rf"(?=\s+(?:{STOP_WORDS}|against|stats?|statistics|numbers?|per|games?)\b|[?!,;:]|$)"
_OPERANDS = (
    re.compile(
        r"\b(?:compare|comparing)\s+(?P<a>.+?)\s+(?:and|with|to|vs\.?|versus)\s+"
        rf"(?P<b>.+?){_NAME_END}"
    ),
    re.compile(r"\bhow\s+(?:do|did|does)\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)\s+compare\b"),
    re.compile(
        r"\b(?:put|show)\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)"
        r"\s+(?:averages?\s+)?side[ -]by[ -]side\b"
    ),
)


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + " " * (end - start) + text[end:]
    return text


def _sample_remainder(text: str) -> str:
    """Consume only complete common context already read by existing consumers."""
    from nbatools.commands._date_utils import _date_token_pattern, extract_date_range
    from nbatools.commands._parse_helpers import (
        extract_season,
        extract_threshold_conditions,
        opponent_lists,
    )

    # This promotion has one scalar opponent. Keep existing no-team unions
    # unchanged, and retain new team+union questions as unfinished positives.
    if opponent_lists(text):
        return "unpromoted opponent union"
    opponents = list(
        re.finditer(rf"\b(?:against|vs\.?|versus)\s+(?:the\s+)?(?:{_TEAM})(?![\w'-])", text)
    )
    if len(opponents) > 1:
        return "multiple opponent clauses"
    spans = [m.span() for m in opponents]
    spans += [(b["start"], b["end"]) for b in extract_threshold_conditions(text)]
    season = extract_season(text)
    # Use the shared date tokens and resolver; unrecognized/invalid dates are
    # left unread, rather than silently claiming an applied date restriction.
    token = _date_token_pattern()
    date_matches = list(
        re.finditer(
            rf"\b(?:(?:from|since|after)\s+{token}\s+(?:to|through)\s+{token}"
            rf"|between\s+{token}\s+and\s+{token}"
            rf"|(?:since|after|before|until|through|on)\s+{token})",
            text,
        )
    )
    # The native range reader represents one complete range, not an arbitrary
    # intersection of individually recognized fragments.
    if len(date_matches) > 1:
        return "multiple date scopes"
    for m in date_matches:
        if any(extract_date_range(m[0], season=season)):
            spans.append(m.span())
    venue_pattern = (
        r"\b(?:at\s+home|home\s+games?|on\s+the\s+road|on\s+road|away\s+games?"
        r"|road\s+games?|at\s+away|home|away)\b"
    )
    windows = list(re.finditer(r"\b(?:last|past|most\s+recent)\s+\d+\s+games?\b", text))
    if len(re.findall(venue_pattern, text)) > 1 or len(windows) > 1:
        return "multiple static sample scopes"
    rest = _mask(text, spans)
    rest = re.sub(
        r"\b(?:(?:in|during|over|for)\s+(?:the\s+)?)?(?:19|20)\d{2}-\d{2}(?:\s+(?:regular\s+)?season)?\b",
        " ",
        rest,
    )
    rest = re.sub(
        r"\b(?:at\s+home|home\s+games?|on\s+the\s+road|on\s+road|away\s+games?|road\s+games?|at\s+away|home|away)\b",
        " ",
        rest,
    )
    rest = re.sub(r"\b(?:last|past|most\s+recent)\s+\d+\s+games?\b", " ", rest)
    # These are connective/basis words around spans, not an escape for an
    # unresolved person, owner, status, clock or a second logical operation.
    rest = re.sub(
        r"\b(?:stats?|statistics|averages?|numbers?|per[ -]game|side[ -]by[ -]side)\b", " ", rest
    )
    if spans:
        rest = re.sub(r"\b(?:with|and|only|in|their|games?)\b", " ", rest)
    return rest.strip(" ,;:.?!")


def read_shared_comparison(text: str) -> dict | None:
    """Return a complete common-team comparison or a contained attempted one.

    Resolving a player from the front of an operand is insufficient: every
    operand must be exactly that identity. Common sample words are separate
    spans, so a team after the second name cannot erase that name or turn
    an unconsumed comparison into a single-player finder.
    """
    if not _INTENT.search(text):
        return None
    teams = list(_SHARED_TEAM.finditer(text))
    if not teams:
        return None
    request = {"players": [], "team": None, "unsupported": "player_comparison_scope"}
    # This promotion is one explicit regular season. In particular, two
    # seasons joined by AND cannot disappear with connective sample words.
    seasons = re.findall(r"\b(?:19|20)\d{2}-\d{2}\b(?!-\d)", text)
    if len(seasons) != 1:
        return request
    if len(teams) != 1:
        return request  # Distinct per-player team owners remain unfinished.
    team = teams[0]
    masked = _mask(text, [team.span()])
    accepted = []
    for pattern in _OPERANDS:
        for match in pattern.finditer(masked):
            players = []
            for key in ("a", "b"):
                phrase = match[key].strip()
                player = detect_player(phrase)
                if not player or not _is_exact_player_reference_phrase(phrase, player):
                    break
                ids = player_ids_for_name(player)
                if len(ids) != 1:
                    break
                players.append(canonical_player_names_by_id()[next(iter(ids))])
            if len(players) != 2 or players[0] == players[1]:
                continue
            last_name_end = match.start("b") + len(match["b"].rstrip())
            if match.start() < team.start() < last_name_end:
                continue
            if _sample_remainder(_mask(text, [team.span(), match.span()])):
                continue
            accepted.append((match, players))
    if not accepted:
        return request
    # Choose complete operands, never the first incidental syntactic match
    # inside another intent (e.g. 'How did A and B compare ... versus TEAM').
    if len({tuple(players) for _, players in accepted}) != 1:
        return request
    match, players = accepted[0]
    request["players"] = players
    rest = _mask(text, [team.span(), match.span()])
    from nbatools.commands._parse_helpers import extract_threshold_conditions
    from nbatools.commands.natural_query import _YES_NO_STATS

    count_stats = _YES_NO_STATS - {"minutes"}
    checks = extract_threshold_conditions(text, exact_stat=count_stats, preserve_numeric_text=True)
    if any(c["stat"] not in count_stats or re.search(r"%|\bpercent\b", c["text"]) for c in checks):
        return request
    lowered = []
    for check in checks:
        condition = dict(check, min_inclusive=True, max_inclusive=True)
        for edge in ("min", "max"):
            bound = check[edge + "_value"]
            if bound is None:
                continue
            value = Decimal(str(bound))
            if not value.is_finite():
                return request
            inclusive = check[edge + "_inclusive"]
            rounding = ROUND_CEILING if (edge == "min") == inclusive else ROUND_FLOOR
            number = int(value.to_integral_value(rounding=rounding))
            if not inclusive:
                number += 1 if edge == "min" else -1
            condition[edge + "_value"] = number
        lowered.append(condition)
    from nbatools.commands._parse_helpers import detect_home_away, extract_last_n

    opponent = re.search(
        rf"\b(?:against|vs\.?|versus)\s+(?:the\s+)?(?P<team>{_TEAM})(?![\w'-])", rest
    )
    home, away = detect_home_away(rest)
    request.update(
        sample={
            "team": TEAM_ALIASES[team["team"]],
            "opponent": TEAM_ALIASES[opponent["team"]] if opponent else None,
            "season": seasons[0],
            "home_only": home,
            "away_only": away,
            "last_n": extract_last_n(rest),
        },
        sample_text=rest,
        team=TEAM_ALIASES[team["team"]],
        unsupported=None,
        subject_span=match.span(),
        count_checks=checks,
        conditions=lowered,
    )
    return request


def count_filter_descriptions(request: dict) -> list[str]:
    """Original predicates remain visible beside equivalent integer execution."""

    def check_description(check):
        parts = []
        for edge, symbol in (("min", ">"), ("max", "<")):
            value = check[edge + "_value"]
            if value is not None:
                sign = symbol + ("=" if check[edge + "_inclusive"] else "")
                parts.append(f"{sign} {value}")
        return " and ".join(parts) + " " + check["stat"].upper()

    descriptions = []
    for original, executed in zip(request["count_checks"], request["conditions"]):
        label = check_description(original)
        normalized = check_description(executed)
        if label != normalized:
            label += f" (integer execution: {normalized})"
        descriptions.append(label)
    return descriptions


def comparison_contract_matches(request: dict, route: str, kwargs: dict) -> bool:
    """Every admitted subject and static sample must survive family routing."""
    if route != "player_compare":
        return False
    if [kwargs.get("player_a"), kwargs.get("player_b")] != request["players"]:
        return False
    if request.get("conditions"):
        from nbatools.commands._condition_utils import normalize_stat_conditions

        if normalize_stat_conditions(kwargs.get("conditions")) != normalize_stat_conditions(
            request["conditions"]
        ):
            return False
    return all(kwargs.get(key) == value for key, value in request["sample"].items())


def has_mixed_comparison_operands(text: str) -> bool:
    """An opponent modifier cannot turn player/team operands into one player."""
    for pattern in _OPERANDS:
        for match in pattern.finditer(text):
            a, b = match["a"].strip(), match["b"].strip()
            for player_phrase, team_phrase in ((a, b), (b, a)):
                team_phrase = re.sub(r"^the\s+", "", team_phrase)
                player = detect_player(player_phrase)
                if (
                    team_phrase in TEAM_ALIASES
                    and player
                    and _is_exact_player_reference_phrase(player_phrase, player)
                ):
                    return True
    return False
