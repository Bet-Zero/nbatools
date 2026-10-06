"""Matchup, comparison, and entity-detection parsing helpers.

Pure functions for:
- detecting head-to-head / matchup phrasing
- extracting player and team comparisons (A vs B)
- extracting opponent references
- detecting player and team entities in free text
"""

from __future__ import annotations

import re

from nbatools.commands._constants import STOP_WORDS, normalize_text
from nbatools.commands.entity_resolution import (
    PLAYER_ALIASES,
    TEAM_ALIASES,
    ResolutionResult,
    mask_copula_team_lookalikes,
    phrase_has_partial_nickname_player_typo,
    resolve_player_in_query,
    resolve_team_in_query,
)

# ---------------------------------------------------------------------------
# Entity detection helpers
# ---------------------------------------------------------------------------


def detect_player(text: str) -> str | None:
    result = resolve_player_in_query(text)
    return result.resolved if result.is_confident else None


def detect_player_resolved(text: str) -> ResolutionResult:
    """Like detect_player but returns full resolution result including ambiguity.

    The resolver already scans every curated alias (normalized), so there is
    no second raw-alias scan: that fallback could only bypass full-name
    precedence or turn an ambiguous last name into one arbitrary player.
    """
    return resolve_player_in_query(text)


def detect_team_in_text(text: str) -> str | None:
    scan_text = mask_copula_team_lookalikes(text)
    for key in sorted(TEAM_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", scan_text):
            return TEAM_ALIASES[key]
    # Fall back to entity resolution for abbreviations etc.
    result = resolve_team_in_query(text)
    if result.is_confident:
        return result.resolved
    return None


def detect_team_resolved(text: str) -> ResolutionResult:
    """Like detect_team_in_text but returns full ResolutionResult."""
    scan_text = mask_copula_team_lookalikes(text)
    for key in sorted(TEAM_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", scan_text):
            return ResolutionResult(
                resolved=TEAM_ALIASES[key],
                candidates=[TEAM_ALIASES[key]],
                confidence="confident",
                source="team_alias",
            )
    return resolve_team_in_query(text)


# ---------------------------------------------------------------------------
# Matchup / head-to-head helpers
# ---------------------------------------------------------------------------

MATCHUP_NOISE_PATTERN = r"\b(?:head\s*[- ]\s*to\s*[- ]\s*head|h2h|matchup|matchups)\b"


def strip_matchup_noise(text: str) -> str:
    # normalize_text here is for whitespace cleanup after regex substitution,
    # not primary normalization (text is already normalized at pipeline entry).
    return normalize_text(re.sub(MATCHUP_NOISE_PATTERN, " ", text))


def detect_head_to_head(text: str) -> bool:
    return bool(re.search(MATCHUP_NOISE_PATTERN, text))


# ---------------------------------------------------------------------------
# Comparison / opponent extraction
# ---------------------------------------------------------------------------


def detect_opponent(text: str) -> tuple[str | None, str]:
    cleaned_text = strip_matchup_noise(text)

    # A count after the team ("vs Celtics 15+ threes") also ends the phrase;
    # "+" is outside the phrase characters, so the match failed and the
    # opponent was read as the subject team.
    count = r"\s+\d+(?:\.\d+)?(?:\+|\s)"
    patterns = [
        rf"\bvs\.?\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|{count}|$)",
        rf"\bversus\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|{count}|$)",
        rf"\bagainst\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|{count}|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        phrase = m.group(1).strip()
        detected = detect_team_in_text(phrase)
        if detected:
            cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
            # Whitespace cleanup after string surgery.
            cleaned = normalize_text(cleaned)
            return detected, cleaned

    return None, cleaned_text


def extract_player_comparison(text: str) -> tuple[str | None, str | None]:
    cleaned_text = strip_matchup_noise(text)

    for alias_a, player_a in sorted(PLAYER_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        stop = STOP_WORDS
        pattern = (  # noqa: E501
            rf"\b{re.escape(alias_a)}\b\s+(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+?)"
            rf"(?=\s+(?:{stop}|against|vs\.?|versus)\b|$)"
        )
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        phrase_b = m.group(1).strip()
        if detect_team_in_text(phrase_b):
            continue
        player_b = detect_player(phrase_b)
        if player_b:
            return player_a, player_b

    explicit = _extract_full_name_comparison(cleaned_text)
    if explicit != (None, None):
        return explicit

    question_form = _extract_question_form_player_comparison(cleaned_text)
    if question_form != (None, None):
        return question_form

    return None, None


_PLAYER_AS_OPPONENT_CONTEXT_RE = re.compile(
    r"\b(?:show|list|stats?|games?|game\s+log|logs?|box\s+score|finder|"
    r"summary|averages?|record|numbers?|performance|scoring)\b"
)


def _clean_comparison_player_phrase(phrase: str) -> str:
    cleaned = normalize_text(phrase)
    cleaned = re.sub(r"^(?:compare|comparing)\s+", "", cleaned)
    cleaned = re.sub(r"\bcomparison\b.*$", "", cleaned)
    return normalize_text(cleaned.strip(" ."))


def _resolve_comparison_player_phrase(phrase: str) -> str | None:
    cleaned = _clean_comparison_player_phrase(phrase)
    if not cleaned:
        return None
    if detect_team_in_text(cleaned):
        return None
    result = resolve_player_in_query(cleaned)
    if result.is_confident:
        return result.resolved
    return detect_player(cleaned)


def _is_exact_player_reference_phrase(phrase: str, player: str) -> bool:
    cleaned = normalize_text(phrase).strip(" .?!,;:")
    if not cleaned:
        return False
    if PLAYER_ALIASES.get(cleaned) == player:
        return True
    return cleaned == normalize_text(player).strip(" .?!,;:")


def detect_bare_player_vs_player_query(text: str) -> tuple[str | None, str | None]:
    """Detect exact ``PLAYER vs PLAYER`` fragments that need clarification.

    This intentionally requires each side of ``vs`` to be only a player
    reference. Qualified comparison phrasing such as ``Jokic vs Embiid recent
    form`` or explicit opponent-player phrasing such as ``LeBron stats vs KD``
    remains outside this boundary.
    """
    cleaned_text = normalize_text(text).strip(" .?!,;:")
    if detect_head_to_head(cleaned_text):
        return None, None

    vs_match = re.match(
        r"^([a-z0-9 .&'\-]+?)\s+(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+?)$",
        cleaned_text,
    )
    if not vs_match:
        return None, None

    left_phrase = vs_match.group(1).strip()
    right_phrase = vs_match.group(2).strip()
    if _PLAYER_AS_OPPONENT_CONTEXT_RE.search(left_phrase) or _PLAYER_AS_OPPONENT_CONTEXT_RE.search(
        right_phrase
    ):
        return None, None
    if detect_team_in_text(left_phrase) or detect_team_in_text(right_phrase):
        return None, None

    player_a = _resolve_comparison_player_phrase(left_phrase)
    player_b = _resolve_comparison_player_phrase(right_phrase)
    if (
        player_a
        and player_b
        and player_a != player_b
        and _is_exact_player_reference_phrase(left_phrase, player_a)
        and _is_exact_player_reference_phrase(right_phrase, player_b)
    ):
        return player_a, player_b

    return None, None


def _extract_full_name_comparison(cleaned_text: str) -> tuple[str | None, str | None]:
    compare_and = re.search(
        # The second phrase runs to the end and may carry filters such as
        # "with 8+ rebounds"; the player resolver reads the name off its front.
        r"\bcompare\s+([a-z0-9 .&'\-]+?)\s+(?:and|with)\s+(.+)$",
        cleaned_text,
    )
    if compare_and:
        player_a = _resolve_comparison_player_phrase(compare_and.group(1))
        # "compare lebron and curry vs the celtics": the opponent is a filter.
        second = re.sub(r"\s+(?:against|vs\.?|versus)\s+.*$", "", compare_and.group(2))
        player_b = _resolve_comparison_player_phrase(second)
        if player_a and player_b and player_a != player_b:
            return player_a, player_b

    vs_match = re.search(
        r"^(?:compare\s+)?([a-z0-9 .&'\-]+?)\s+(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+)$",
        cleaned_text,
    )
    if not vs_match:
        return None, None

    left_phrase = _clean_comparison_player_phrase(vs_match.group(1))
    if _PLAYER_AS_OPPONENT_CONTEXT_RE.search(left_phrase):
        return None, None

    player_a = _resolve_comparison_player_phrase(left_phrase)
    player_b = _resolve_comparison_player_phrase(vs_match.group(2))
    if player_a and player_b and player_a != player_b:
        return player_a, player_b

    return None, None


def _extract_question_form_player_comparison(
    cleaned_text: str,
) -> tuple[str | None, str | None]:
    compare_question = re.search(
        r"\bhow\s+(?:do|did)\s+([a-z0-9 .&'\-]+?)\s+and\s+"
        r"([a-z0-9 .&'\-]+?)\s+compare\b",
        cleaned_text,
    )
    if not compare_question:
        return None, None

    player_a = _resolve_comparison_player_phrase(compare_question.group(1))
    player_b = _resolve_comparison_player_phrase(compare_question.group(2))
    if player_a and player_b and player_a != player_b:
        return player_a, player_b

    return None, None


def extract_team_comparison(text: str) -> tuple[str | None, str | None]:
    cleaned_text = strip_matchup_noise(text)
    # "compare the Lakers and Warriors vs the Celtics": the joined pair is
    # the subject and the "vs" team their opponent.
    team_a, team_b = _extract_compare_and_teams(cleaned_text)
    if team_a and team_b:
        if not _COMPARE_LEAD_RE.search(cleaned_text) and _LEADING_PAIR_OTHER_INTENT_RE.search(
            cleaned_text
        ):
            # "Lakers and Celtics leading scorers", "... series history": the
            # pair is not asking for a side-by-side team summary.
            return None, None
        return team_a, team_b

    team_keys = sorted(TEAM_ALIASES.keys(), key=len, reverse=True)
    for alias_a in team_keys:
        stop = STOP_WORDS
        pattern = (
            rf"\b{re.escape(alias_a)}\b\s+(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+?)"
            rf"(?=\s+(?:{stop})\b|$)"
        )
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        team_a = TEAM_ALIASES[alias_a]
        phrase_b = m.group(1).strip()
        team_b = detect_team_in_text(phrase_b)
        if team_b and team_b != team_a:
            return team_a, team_b

    return None, None


_COMPARE_LEAD_RE = re.compile(r"\bcompar(?:e|ing)\s+(?:the\s+)?")
_COMPARE_JOIN_RE = re.compile(r"\s+(?:and|with|to)\s+(?:the\s+)?")


_LEADING_TEAM_RE = re.compile(r"^\s*(?:the\s+)?")
_LEADING_AND_RE = re.compile(r"\s+and\s+(?:the\s+)?")
_LEADING_PAIR_OTHER_INTENT_RE = re.compile(
    r"\b(?:leading|leaders?|scorers?|players?|most|fewest|highest|lowest|"
    r"streaks?|stretch(?:es)?|roster|standings|history|finals|rank(?:ed|ings?)?|who)\b"
)


def _extract_compare_and_teams(text: str) -> tuple[str | None, str | None]:
    """Two teams joined by "and" that the question is about.

    "compare the Lakers and Celtics when scoring 120", and also a question
    that opens with the pair: "Lakers and Warriors last 10 games".
    """
    lead = _COMPARE_LEAD_RE.search(text)
    if lead:
        start, join = lead.end(), _COMPARE_JOIN_RE
    else:
        start, join = _LEADING_TEAM_RE.match(text).end(), _LEADING_AND_RE
    mentions = _non_overlapping_team_mentions(text)
    for (start_a, end_a, team_a), (start_b, _end_b, team_b) in zip(
        mentions, mentions[1:], strict=False
    ):
        if start_a != start or team_a == team_b:
            continue
        if join.fullmatch(text[end_a:start_b]):
            return team_a, team_b
    return None, None


_ADJACENT_TEAM_SEPARATOR_RE = re.compile(r"^[\s/&,+-]+$")
# "Lakers and Nuggets playoff history", "Heat vs. Knicks series history"
_PLAYOFF_PAIR_JOIN_RE = re.compile(r"\s+(?:and|vs\.?|versus)\s+(?:the\s+)?")


def _non_overlapping_team_mentions(text: str) -> list[tuple[int, int, str]]:
    """Return longest non-overlapping team mentions in text order."""
    mentions: list[tuple[int, int, str]] = []

    for alias, team in sorted(TEAM_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        for match in re.finditer(rf"\b{re.escape(alias)}\b", text):
            span = match.span()
            if any(not (span[1] <= start or span[0] >= end) for start, end, _ in mentions):
                continue
            mentions.append((span[0], span[1], team))

    return sorted(mentions, key=lambda item: item[0])


def extract_adjacent_playoff_team_comparison(text: str) -> tuple[str | None, str | None]:
    """Detect adjacent team-team phrasing in playoff series/history contexts.

    This intentionally does not generalize adjacency parsing to ordinary
    comparisons. It only promotes phrases like "Heat Knicks playoff history"
    or "Warriors Cavaliers Finals history" where a playoff series/history
    context is explicit and the two team mentions are directly adjacent.
    """
    cleaned_text = strip_matchup_noise(text)
    has_playoff_context = bool(
        re.search(r"\b(?:playoff|postseason)\s+(?:history|series|matchups?|record)\b", cleaned_text)
        or re.search(r"\bseries\s+(?:history|results)\b", cleaned_text)
        or re.search(
            r"\b(?:nba\s+finals?|the\s+finals|finals?|conference\s+finals?|conf\s+finals?)"
            r"\s+(?:history|series|matchups?|record)\b",
            cleaned_text,
        )
        # "Lakers and Celtics record in the 2010 finals", as "finals record" reads.
        or re.search(
            r"\brecord\s+in\s+(?:the\s+)?(?:(?:19|20)\d{2}\s+)?(?:nba\s+)?"
            r"(?:(?:eastern|western|east|west)\s+)?(?:conference\s+|conf\s+)?"
            r"(?:finals?|semifinals|semis|(?:first|second)\s+round)\b",
            cleaned_text,
        )
    )
    if not has_playoff_context:
        return None, None

    mentions = _non_overlapping_team_mentions(cleaned_text)
    for first, second in zip(mentions, mentions[1:]):
        _, first_end, team_a = first
        second_start, _, team_b = second
        if team_a == team_b:
            continue
        separator = cleaned_text[first_end:second_start]
        if _ADJACENT_TEAM_SEPARATOR_RE.fullmatch(separator) or _PLAYOFF_PAIR_JOIN_RE.fullmatch(
            separator
        ):
            return team_a, team_b

    return None, None


# ---------------------------------------------------------------------------
# Player-vs-player-as-opponent detection
# ---------------------------------------------------------------------------


def extract_player_vs_player_as_opponent(text: str) -> tuple[str | None, str | None]:
    """Detect 'PLAYER stats/... vs PLAYER' where the second player is an opponent filter.

    Unlike extract_player_comparison (which requires 'PLAYER vs PLAYER' adjacently),
    this catches patterns where words like 'stats', 'record', 'averages' appear between
    the first player and 'vs', indicating the user wants one player's stats filtered
    to games against the second player, not a head-to-head comparison.

    Returns (player_a, opponent_player) or (None, None) if no match.
    """
    cleaned_text = strip_matchup_noise(text)

    # Pattern: PLAYER [context words] vs/against PLAYER
    context_words = (
        r"(?:stats?|averages?|record|numbers?|performance|scoring|games?|season|this season|last)"  # noqa: E501
    )

    for alias_a, player_a in sorted(PLAYER_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        stop = STOP_WORDS
        pattern = (
            rf"\b{re.escape(alias_a)}\b\s+"
            rf"(?:[\w\s]*?{context_words}[\w\s]*?\s+)?"
            rf"(?:vs\.?|versus|against)\s+"
            rf"([a-z0-9 .&'\-]+?)"
            rf"(?=\s+(?:{stop})\b|$)"
        )
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        full_match = m.group(0)
        vs_pos = re.search(r"\b(?:vs\.?|versus|against)\b", full_match)
        if vs_pos:
            between = full_match[len(alias_a) : vs_pos.start()].strip()
            if between and re.search(context_words, between):
                phrase_b = m.group(1).strip()
                player_b = detect_player(phrase_b)
                if player_b and player_b != player_a:
                    return player_a, player_b

    return None, None


def detect_opponent_player(text: str) -> tuple[str | None, str]:
    """Detect 'vs/against PLAYER_NAME' where the opponent is a player, not a team.

    This runs after detect_opponent (team-level) fails. It catches cases like
    'Jokic stats vs Embiid' where the 'vs' target is a player name.

    Returns (opponent_player_name, cleaned_text) or (None, original_text).
    """
    cleaned_text = strip_matchup_noise(text)

    patterns = [
        rf"\bvs\.?\s+([a-z0-9 .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
        rf"\bversus\s+([a-z0-9 .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
        rf"\bagainst\s+([a-z0-9 .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, cleaned_text)
        if not m:
            continue
        phrase = m.group(1).strip()
        player = detect_player(phrase)
        if player:
            cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
            # Whitespace cleanup after string surgery.
            cleaned = normalize_text(cleaned)
            return player, cleaned

    return None, cleaned_text


# ---------------------------------------------------------------------------
# Without-player detection
# ---------------------------------------------------------------------------


def _phrase_names_multiple_players(phrase: str) -> bool:
    """True if a presence/absence phrase names two distinct players.

    ``detect_player`` falls back to a substring alias scan, which will match a
    single known name embedded anywhere in the phrase even when the phrase
    actually names two players (e.g. "both Bane and Franz"). Without this
    check, presence/absence detectors silently collapse a two-player request
    down to whichever one name happens to match first, instead of surfacing
    it as unresolved.
    """
    for sep in (" and ", " & "):
        if sep not in phrase:
            continue
        left, right = phrase.split(sep, 1)
        left_player = detect_player(left.strip(" ."))
        right_player = detect_player(right.strip(" ."))
        if left_player and right_player and left_player != right_player:
            return True
    return False


# "while LeBron was out" states exactly the same availability condition as
# "when LeBron was out". Reading only one of them dropped the clause and
# answered the unfiltered question.
_ABSENCE_CONJUNCTIONS = r"when|while"


def detect_without_player(text: str) -> tuple[str | None, str]:
    """Detect absence patterns like 'without PLAYER', 'w/o PLAYER',
    'when PLAYER out', 'when PLAYER didn't play', 'no PLAYER',
    'sans PLAYER', 'minus PLAYER'.

    Returns (excluded_player_name, cleaned_text) or (None, original_text).
    Used for queries like 'Warriors record without Steph Curry'.
    """
    # Receives pre-normalized text from _build_parse_state; no per-detector
    # normalization needed.
    cleaned_text = text

    # Ordered most-specific first to avoid partial matches.
    absence_patterns = [
        # `without PLAYER` / `w/o PLAYER`
        rf"\b(?:without|w/o)\s+([\w .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
        # `when/while PLAYER didn't/doesn't play` / `... did/does not play`
        rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)"
        r"\s+(?:didn'?t|did\s+not|doesn'?t|does\s+not)\s+play\b",
        # `when/while/and PLAYER sits/rests`: "Lakers record when Luka sits"
        # read no absence and answered with the whole record.
        r"\b(?:when|while|and)\s+((?:(?!\b(?:and|when|while)\b)[\w .&'\-])+?)"
        r"\s+(?:sits?|sat|rests?|rested|is\s+resting|was\s+resting)(?:\s+out)?\b",
        # `when/while PLAYER is/was out`
        rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)\s+(?:is|was|were|are)\s+out\b",
        # `when/while PLAYER out` (no copula)
        rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)\s+out\b",
        # `record PLAYER out`
        r"\brecord\s+([\w .&'\-]+?)\s+out\b",
        # `no PLAYER` / `sans PLAYER` / `minus PLAYER`
        rf"\b(?:no|sans|minus)\s+([\w .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
    ]

    for pattern in absence_patterns:
        m = re.search(pattern, cleaned_text)
        if m:
            phrase = m.group(1).strip()
            if re.search(r"\b(?:didn'?t|doesn'?t|did\s+not|does\s+not)\b", phrase):
                continue
            if _phrase_names_multiple_players(phrase):
                continue
            player = detect_player(phrase)
            if player:
                cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
                # Whitespace cleanup after string surgery.
                cleaned = normalize_text(cleaned)
                return player, cleaned

    return None, cleaned_text


# "35 minutes", "at least 35 minutes", "30 minutes or less", "35+ mins": a
# minutes condition, not a word that can follow bare presence.
_MINUTES_BOUND_TAIL = (
    # Any operator words ("at least", "no fewer than", "a max of") before the
    # number; the threshold reader decides which bound they state.
    r"\s+(?:[a-z]+\s+){0,3}"
    r"\d+(?:\.\d+)?\+?(?:\s+or\s+(?:more|fewer|less))?\s*"
    r"(?:minutes?|mins?)\b"
)


# "and Luka sits", "while Davis is out": another player's availability clause.
_AVAILABILITY_CLAUSE = re.compile(
    r"\b(?:and|while|when|but)\s+((?:(?!\b(?:and|while|when|but)\b)[\w .'\-])+?)"
    r"\s+(?:plays?|played|playing|sits?|sat|rests?|rested|(?:is|was)\s+resting"
    r"|(?:is|was)\s+out|out|(?:does|did)(?:n'?t|\s+not)\s+play)\b"
)

# "plays and scores 30", "played and had 10 assists": the player's own stat
# condition, not bare presence.
_OWN_STAT_CLAUSE = (
    r"\s+and\s+(?:scores?|scored|scoring|grabs?|grabbed|dishes|dished|has|had"
    r"|records?|recorded|puts?\s+up|makes?|made|hits?)\b"
)


def names_other_player_availability(text: str, player: str | None) -> bool:
    """True when ``text`` states availability for a player other than ``player``.

    A pronoun or a team ("and he plays well", "and the Lakers play at home")
    is not another player. Any other subject counts, including a name the
    resolver can't match ("and Davis sits"): dropping that clause would
    answer about the first player alone.
    """
    own_words = set(player.lower().split()) if player else set()
    for m in _AVAILABILITY_CLAUSE.finditer(text):
        subject = re.sub(r"^(?:the|his|their)\s+", "", m.group(1).strip())
        if not subject or subject in _NON_PLAYER_SUBJECTS or subject in TEAM_ALIASES:
            continue
        other = detect_player(subject)
        if other is None and set(subject.split()) <= own_words:
            continue
        if other is None or player is None or other.upper() != player.upper():
            return True
    return False


_NON_PLAYER_SUBJECTS = {"he", "she", "they", "we", "it", "team", "teams", "squad", "game"}


def detect_with_player(text: str) -> tuple[str | None, str]:
    """Detect whole-game presence patterns like ``with PLAYER`` / ``w/ PLAYER``.

    This is intentionally separate from on/off-court parsing. Callers should
    skip this detector for phrases like ``with Jokic on the floor``.
    """
    cleaned_text = text
    with_player_pattern = (
        rf"\b(?:with|w/)\s+([\w .&'\-]+?)"
        rf"(?=\s+(?:available|without|w/o|{STOP_WORDS})\b|[?.!,;:]|$)"
    )
    presence_patterns = [
        with_player_pattern,
        rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)\s+(?:plays?|played)\b",
    ]

    for index, pattern in enumerate(presence_patterns):
        m = re.search(pattern, cleaned_text)
        if m:
            phrase = m.group(1).strip()
            if re.search(r"\b(?:didn'?t|doesn'?t|did\s+not|does\s+not)\b", phrase):
                continue
            if _phrase_names_multiple_players(phrase):
                continue
            player = detect_player(phrase)
            tail = cleaned_text[m.end() :]
            if (
                player
                and index == 1
                and (re.match(_MINUTES_BOUND_TAIL, tail) or re.match(_OWN_STAT_CLAUSE, tail))
                and not names_other_player_availability(tail, player)
            ):
                # "when PLAYER plays 35 minutes" / "plays and scores 30" state a
                # condition on that player. Read as presence the bound was
                # dropped (or checked against team rows) and the team's whole
                # record came back. With another player's clause after it the
                # player route would drop that clause, so it stays presence and
                # the team route refuses.
                continue
            if player:
                cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
                cleaned = normalize_text(cleaned)
                return player, cleaned

    return None, cleaned_text


_STAT_COUNT_QUALIFIER = (
    r"(?:at\s+(?:least|most)\s+|(?:no(?:t)?\s+)?(?:over|above|under|below)\s+"
    r"|(?:no(?:t)?\s+)?(?:more|fewer|less|greater)\s+than\s+)?"
)
# Only nouns the threshold reader turns into a stat; "3-pointers", "rebs" or
# "minutes" would skip the refusal and then apply no filter.
_STAT_COUNT_NOUN = (
    r"(?:made\s+)?(?:points?|pts|rebounds?|boards?|assists?|dimes"
    r"|threes?|3s|3pm|three[- ]pointers?|steals?|blocks?|turnovers?|fouls?)"
)
_STAT_COUNT_CLAUSE = (
    rf"{_STAT_COUNT_QUALIFIER}\d+\+?(?:\s+or\s+(?:more|fewer|less))?\s+{_STAT_COUNT_NOUN}"
    r"(?:\s+or\s+(?:more|fewer|less|better))?"
)
# "120 points", "15+ threes and 30 assists": every clause is a count of a
# box-score stat. "1 day of rest", "2 players scoring 30" and "23" are not.
_STAT_COUNT_PHRASE = re.compile(
    rf"{_STAT_COUNT_CLAUSE}(?:\s*(?:,|and|,\s*and)\s+{_STAT_COUNT_CLAUSE})*(?![\w-])"
)
_MONTH = (
    r"(?:january|february|march|april|may|june|july|august|september|october"
    r"|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
)
_SEASON = r"(?:(?:19|20)\d{2}(?:-\d{2}(?:\d{2})?)?)"
# Scope the parser applies after a stat-count bound. The whole tail must be
# made of these, so nothing after the bound ("in games where Davis sits",
# "before the all-star break", ", 2 days rest") is silently dropped.
_READ_SCOPE_UNIT = (
    r"(?:(?:in|during|for)\s+(?:the\s+)?)?" + _SEASON + r"(?:\s+(?:season|regular\s+season))?"
    r"|(?:this|last)\s+(?:season|year)"
    r"|since\s+(?:" + _SEASON + r"|" + _MONTH + r"(?:\s+" + _SEASON + r")?)"
    r"|(?:in\s+)?" + _MONTH + r"(?:\s+" + _SEASON + r")?"
    r"|(?:vs\.?|versus|against)\s+(?:teams\s+(?:over|under|above|below)\s+\.500"
    r"|(?:good|bad|winning|losing)\s+teams"
    r"|(?:the\s+)?(?P<opp>[a-z]+))"
    r"|at\s+home|on\s+the\s+road|home|road|away"
    r"|(?:in\s+the\s+)?(?:playoffs|postseason|regular\s+season)"
    r"|in\s+(?:a\s+)?(?:win|loss|wins|losses)"
    r"|in\s+(?:the|their|his)\s+last\s+\d+\s+games?"
    r"|after\s+the\s+all[- ]star\s+break"
    r"|if\s+(?P<plr>[a-z][\w.'\-]*(?:\s+[a-z][\w.'\-]*)?)\s+plays?"
)
_READ_SCOPE_STEP = re.compile(rf"\s+(?:{_READ_SCOPE_UNIT})(?![\w.-])")
_READ_TAIL_END = re.compile(r"\s*[?.!]?\s*$")
_CONFERENCE_OPPONENTS = {"east", "west", "eastern conference", "western conference"}


def _opponent_quality_end(text: str, pos: int) -> int | None:
    # _parse_helpers imports this module, so load it lazily.
    from nbatools.commands._parse_helpers import opponent_quality_span_end

    return opponent_quality_span_end(text, pos)


def _tail_is_read_scope(text: str, pos: int) -> bool:
    """Whether everything from ``pos`` on is scope the parser applies.

    Opponents must resolve to a team or conference and "if X plays" to a
    player, so "vs playoff teams" or "if anyone plays" is never dropped.
    """
    while not _READ_TAIL_END.match(text, pos):
        gap = re.compile(r"\s+").match(text, pos)
        quality_end = _opponent_quality_end(text, gap.end()) if gap else None
        if quality_end is not None:
            # "vs playoff teams", "against top-10 defenses": glossary terms
            # the opponent-quality filter applies.
            pos = quality_end
            continue
        step = _READ_SCOPE_STEP.match(text, pos)
        if not step:
            return False
        pos = step.end()
        if step.group("opp") is not None:
            # The longest run of up to three words that names a team or
            # conference: "the boston celtics", "golden state", "the east".
            words = re.match(r"[a-z]+(?:\s+[a-z]+){0,2}", text[step.start("opp") :])
            names = words.group(0).split() if words else []
            for n in range(len(names), 0, -1):
                name = " ".join(names[:n])
                if name in TEAM_ALIASES or name in _CONFERENCE_OPPONENTS:
                    pos = step.start("opp") + len(name)
                    break
            else:
                return False
        if step.group("plr") is not None and not detect_player(step.group("plr")):
            return False
    return True


_CONDITIONAL_CLAUSE = re.compile(r"\b(?:when|if|while|whenever)\b")


def _names_conditional_player(text: str) -> bool:
    cond = _CONDITIONAL_CLAUSE.search(text)
    return bool(cond and detect_player(text[cond.end() :]))


_PEOPLE_WORDS = re.compile(
    r"\b(?:teammates?|guards?|forwards?|centers?|bench|players?|starters?|lineups?|"
    r"coach(?:es)?|rookies?|scorers?|shooters?|defenders?|roster|duo|trio|big\s+men)\b"
)


def _superlative_names_a_stat(phrase: str, text: str) -> bool:
    """ "the best record", "the most turnovers": a stat, not a person or group."""
    sup = r"(?:the\s+)?(?:most|fewest|least|highest|lowest|best|worst)"
    rest = re.sub(rf"^{sup}\b\s*", "", phrase).strip()
    if not rest:
        # The phrase stopped at a word the player pattern drops ("record").
        m = re.search(
            rf"\bwith\s+{sup}\s+(.+?)(?=\s+(?:in|this|since|over|from|during|of|for|with|"
            r"without|by|vs|against)\b|[,?.]|$)",
            text,
        )
        rest = m.group(1).strip() if m else ""
    if not rest or _PEOPLE_WORDS.search(rest):
        return False
    if re.search(r"\b(?:home|road|away)\b", rest):
        # No home/road season board yet: keep the refusal.
        return False
    if re.fullmatch(r"(?:(?:regular[\s-]season|playoff)\s+)?(?:record|wins|losses)", rest):
        return True
    from nbatools.commands._parse_helpers import detect_stat

    return detect_stat(rest) is not None


_NEGATED_BOUND = r"(?:(?:more|fewer|less|greater)\s+than|over|above|under|below)\s+\d"


def detect_unresolved_availability_player(text: str, *, mode: str) -> str | None:
    """Return a raw availability name fragment that was requested but unresolved."""
    if mode == "without":
        patterns = [
            rf"\b(?:without|w/o)\s+([\w .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
            rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)"
            r"\s+(?:didn'?t|did\s+not|doesn'?t|does\s+not)\s+play\b",
            rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)\s+(?:is|was|were|are)\s+out\b",
            rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)\s+out\b",
            r"\brecord\s+([\w .&'\-]+?)\s+out\b",
            # "when Davis sits"; not "when they sit atop the standings".
            r"\b(?:when|while|and)\s+(?!(?:they|he|she|we|it|the)\b)"
            r"((?:(?!\b(?:and|when|while)\b)[\w .&'\-])+?)"
            r"\s+(?:sits?|sat|rests?|rested|is\s+resting|was\s+resting)(?:\s+out)?\b"
            r"(?!\s+(?:atop|at|in|on|near|behind|ahead)\b)",
            # "no more than 10 turnovers" is a bound, not a missing player.
            rf"\b(?:no|sans|minus)\s+(?!{_NEGATED_BOUND})([\w .&'\-]+?)"
            rf"(?=\s+(?:{STOP_WORDS})\b|$)",
        ]
    elif mode == "with":
        with_player_pattern = (
            rf"\b(?:with|w/)\s+([\w .&'\-]+?)"
            rf"(?=\s+(?:available|without|w/o|{STOP_WORDS})\b|[?.!,;:]|$)"
        )
        patterns = [
            with_player_pattern,
            rf"\b(?:{_ABSENCE_CONJUNCTIONS})\s+([\w .&'\-]+?)\s+(?:plays?|played)\b",
        ]
    else:
        raise ValueError(f"Unsupported availability mode: {mode}")

    for pattern in patterns:
        m = re.search(pattern, text)
        if not m:
            continue
        phrase = m.group(1).strip()
        if mode == "with" and re.search(r"\b(?:didn'?t|doesn'?t|did\s+not|does\s+not)\b", phrase):
            continue
        stat_bound = _STAT_COUNT_PHRASE.match(text, m.start(1)) if mode == "with" else None
        if (
            stat_bound
            # Only scope the parser already reads may follow the bound, so
            # nothing ("and 2 days rest", "from Davis") is silently dropped.
            and _tail_is_read_scope(text, stat_bound.end())
            and not detect_player(text[stat_bound.end() :])
            and not _names_conditional_player(text)
        ):
            # "record in games with 120 points": a stat bound, not a teammate.
            # A player named later ("... with 15 threes and LeBron") or in a
            # "when LeBron scores 30" clause still needs the availability
            # reading, which this path cannot combine with the team bound.
            continue
        if (
            mode == "with"
            and re.match(r"(?:the\s+)?(?:most|fewest|least|highest|lowest|best|worst)\b", phrase)
            and (
                re.search(r"\bseasons?\b.*\bwith\s+the\s+(?:most|fewest)\s+(?:wins|losses)\b", text)
                or (
                    re.search(
                        r"\bseasons?\s+with\s+the\s+(?:most|fewest|least|highest|lowest|best|worst)\b",
                        text,
                    )
                    and _superlative_names_a_stat(phrase, text)
                )
            )
        ):
            # "season with the most wins / best record" ranks seasons, it
            # names no player.
            continue
        if phrase and _phrase_names_multiple_players(phrase):
            return phrase
        if phrase and not detect_player(phrase):
            return phrase
    return None


_COMPARISON_TRAILING_CONTEXT = (
    rf"(?:{STOP_WORDS}|since|before|after|when|where|who|what|which|how|why"
    r"|this|current|season|year|regular|career|all"
    # Stat / metric words that follow the second player in a stat comparison
    # ("curry vs dame 3 point shooting") and must not be read as a name typo.
    r"|\d|points?|pts|rebounds?|reb|rebs|assists?|ast|asts|scoring|shooting"
    r"|threes?|3pt|blocks?|steals?|turnovers?|efficiency|better|head"
    # Opponent filters after the pair: "lebron vs curry against winning teams".
    r"|against|vs\.?|versus)"
)
_VS_COMPARISON_PHRASE_RE = re.compile(
    r"(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+?)"
    rf"(?=\s+{_COMPARISON_TRAILING_CONTEXT}\b|$)"
)
_SPLIT_VS_CONTEXT_RE = re.compile(
    r"\b(?:home|away|road|wins?|losses?)\s+(?:vs\.?|versus)\s+"
    r"(?:home|away|road|wins?|losses?)\b"
)
_ON_OFF_VS_CONTEXT_RE = re.compile(
    r"\b(?:on\s+(?:the\s+)?floor|on\s+court|off\s+(?:the\s+)?floor|off\s+court)\b"
)
_SUMMARY_TYPO_PREFIX_RE = re.compile(r"^([a-z][a-z .&'\-]+?)\s+(?:averages?|average|stats?|stat)\b")
_SUMMARY_TYPO_BLOCKED_NAME_WORDS = frozenset(
    {
        "clutch",
        "game",
        "log",
        "logs",
        "recent",
        "form",
        "playoff",
        "playoffs",
        "postseason",
        "career",
        "season",
        "home",
        "away",
        "road",
        "last",
        "past",
        "on",
        "off",
        "court",
        "floor",
        # Playoff rounds: "LeBron Finals stats" names a round, not a typo.
        "finals",
        "conference",
        "semifinals",
        "semis",
        "round",
        "first-round",
        "second-round",
        "third-round",
    }
)


def detect_unresolved_player_typo_comparison(text: str) -> str | None:
    """Return typoed opponent phrase from player-vs-player comparison wording."""
    cleaned = strip_matchup_noise(text)
    if _SPLIT_VS_CONTEXT_RE.search(cleaned) or _ON_OFF_VS_CONTEXT_RE.search(cleaned):
        return None
    if _PLAYER_AS_OPPONENT_CONTEXT_RE.search(cleaned):
        return None

    m = _VS_COMPARISON_PHRASE_RE.search(cleaned)
    if not m:
        return None

    phrase = _clean_comparison_player_phrase(m.group(1))
    phrase = re.sub(
        rf"\s+{_COMPARISON_TRAILING_CONTEXT}\b.*$",
        "",
        phrase,
    )
    phrase = normalize_text(phrase.strip(" ."))
    if phrase and phrase_has_partial_nickname_player_typo(phrase):
        return phrase
    return None


def detect_unresolved_player_summary_typo(text: str) -> str | None:
    """Return typoed leading player phrase from summary/averages shorthand."""
    cleaned = strip_matchup_noise(text)
    m = _SUMMARY_TYPO_PREFIX_RE.match(cleaned)
    if not m:
        return None

    phrase = m.group(1).strip()
    if len(phrase.split()) > 3:
        return None
    if any(word in _SUMMARY_TYPO_BLOCKED_NAME_WORDS for word in phrase.split()):
        return None
    if phrase_has_partial_nickname_player_typo(phrase):
        return phrase
    return None


def detect_unresolved_player_typo(
    text: str,
    *,
    comparison: bool = False,
    summary: bool = False,
) -> str | None:
    """Return a player fragment that must not silently resolve via nickname-only match."""
    if comparison:
        if fragment := detect_unresolved_player_typo_comparison(text):
            return fragment
    if summary:
        if fragment := detect_unresolved_player_summary_typo(text):
            return fragment
    return None
