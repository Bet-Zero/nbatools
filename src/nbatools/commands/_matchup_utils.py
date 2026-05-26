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
    resolve_player_in_query,
    resolve_team_in_query,
)

# ---------------------------------------------------------------------------
# Entity detection helpers
# ---------------------------------------------------------------------------


def detect_player(text: str) -> str | None:
    result = resolve_player_in_query(text)
    if result.is_confident:
        return result.resolved
    # Fall back to the legacy merged alias map for any compatibility-only alias
    # not covered by the resolver.
    for key in sorted(PLAYER_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return PLAYER_ALIASES[key]
    return None


def detect_player_resolved(text: str) -> ResolutionResult:
    """Like detect_player but returns full resolution result including ambiguity."""
    result = resolve_player_in_query(text)
    if result.is_confident or result.is_ambiguous:
        return result
    # Fall back to the legacy merged alias map for any compatibility-only alias
    # not covered by the resolver.
    for key in sorted(PLAYER_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return ResolutionResult(
                resolved=PLAYER_ALIASES[key],
                candidates=[PLAYER_ALIASES[key]],
                confidence="confident",
                source="alias",
            )
    return result


def detect_team_in_text(text: str) -> str | None:
    for key in sorted(TEAM_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return TEAM_ALIASES[key]
    # Fall back to entity resolution for abbreviations etc.
    result = resolve_team_in_query(text)
    if result.is_confident:
        return result.resolved
    return None


def detect_team_resolved(text: str) -> ResolutionResult:
    """Like detect_team_in_text but returns full ResolutionResult."""
    for key in sorted(TEAM_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
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

    patterns = [
        rf"\bvs\.?\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|$)",
        rf"\bversus\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|$)",
        rf"\bagainst\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|$)",
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
            rf"(?=\s+(?:{stop})\b|$)"
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


def _extract_full_name_comparison(cleaned_text: str) -> tuple[str | None, str | None]:
    compare_and = re.search(
        r"\bcompare\s+([a-z0-9 .&'\-]+?)\s+(?:and|with)\s+([a-z0-9 .&'\-]+)$",
        cleaned_text,
    )
    if compare_and:
        player_a = _resolve_comparison_player_phrase(compare_and.group(1))
        player_b = _resolve_comparison_player_phrase(compare_and.group(2))
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


def extract_team_comparison(text: str) -> tuple[str | None, str | None]:
    cleaned_text = strip_matchup_noise(text)

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


_ADJACENT_TEAM_SEPARATOR_RE = re.compile(r"^[\s/&,+-]+$")


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
        or re.search(
            r"\b(?:nba\s+finals?|the\s+finals|finals?|conference\s+finals?|conf\s+finals?)"
            r"\s+(?:history|series|matchups?|record)\b",
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
        if _ADJACENT_TEAM_SEPARATOR_RE.fullmatch(separator):
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
        # `when PLAYER didn't/doesn't play` / `when PLAYER did/does not play`
        r"\bwhen\s+([\w .&'\-]+?)\s+(?:didn'?t|did\s+not|doesn'?t|does\s+not)\s+play\b",
        # `when PLAYER is/was out`
        r"\bwhen\s+([\w .&'\-]+?)\s+(?:is|was)\s+out\b",
        # `when PLAYER out` (no copula)
        r"\bwhen\s+([\w .&'\-]+?)\s+out\b",
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
            player = detect_player(phrase)
            if player:
                cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
                # Whitespace cleanup after string surgery.
                cleaned = normalize_text(cleaned)
                return player, cleaned

    return None, cleaned_text


def detect_with_player(text: str) -> tuple[str | None, str]:
    """Detect whole-game presence patterns like ``with PLAYER``.

    This is intentionally separate from on/off-court parsing. Callers should
    skip this detector for phrases like ``with Jokic on the floor``.
    """
    cleaned_text = text
    presence_patterns = [
        rf"\bwith\s+([\w .&'\-]+?)(?=\s+(?:without|w/o|{STOP_WORDS})\b|$)",
        r"\bwhen\s+([\w .&'\-]+?)\s+(?:plays?|played)\b",
    ]

    for pattern in presence_patterns:
        m = re.search(pattern, cleaned_text)
        if m:
            phrase = m.group(1).strip()
            if re.search(r"\b(?:didn'?t|doesn'?t|did\s+not|does\s+not)\b", phrase):
                continue
            player = detect_player(phrase)
            if player:
                cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
                cleaned = normalize_text(cleaned)
                return player, cleaned

    return None, cleaned_text


def detect_unresolved_availability_player(text: str, *, mode: str) -> str | None:
    """Return a raw availability name fragment that was requested but unresolved."""
    if mode == "without":
        patterns = [
            rf"\b(?:without|w/o)\s+([\w .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
            r"\bwhen\s+([\w .&'\-]+?)\s+(?:didn'?t|did\s+not|doesn'?t|does\s+not)\s+play\b",
            r"\bwhen\s+([\w .&'\-]+?)\s+(?:is|was)\s+out\b",
            r"\bwhen\s+([\w .&'\-]+?)\s+out\b",
            r"\brecord\s+([\w .&'\-]+?)\s+out\b",
            rf"\b(?:no|sans|minus)\s+([\w .&'\-]+?)(?=\s+(?:{STOP_WORDS})\b|$)",
        ]
    elif mode == "with":
        patterns = [
            rf"\bwith\s+([\w .&'\-]+?)(?=\s+(?:without|w/o|{STOP_WORDS})\b|$)",
            r"\bwhen\s+([\w .&'\-]+?)\s+(?:plays?|played)\b",
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
        if phrase and not detect_player(phrase):
            return phrase
    return None
