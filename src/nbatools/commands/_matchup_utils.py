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
    # First try the original curated alias dict (preserves exact existing behavior)
    for key in sorted(PLAYER_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return PLAYER_ALIASES[key]
    # Fall back to entity resolution (data-driven last-name lookup)
    result = resolve_player_in_query(text)
    if result.is_confident:
        return result.resolved
    return None


def detect_player_resolved(text: str) -> ResolutionResult:
    """Like detect_player but returns full resolution result including ambiguity."""
    # First try the original curated alias dict
    for key in sorted(PLAYER_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return ResolutionResult(
                resolved=PLAYER_ALIASES[key],
                candidates=[PLAYER_ALIASES[key]],
                confidence="confident",
                source="alias",
            )
    # Fall back to entity resolution (data-driven last-name lookup)
    return resolve_player_in_query(text)


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
        player_b = detect_player(phrase_b)
        if player_b:
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
        # `when PLAYER didn't play` / `when PLAYER did not play`
        r"\bwhen\s+([\w .&'\-]+?)\s+(?:didn'?t|did\s+not)\s+play\b",
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
            player = detect_player(phrase)
            if player:
                cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
                # Whitespace cleanup after string surgery.
                cleaned = normalize_text(cleaned)
                return player, cleaned

    return None, cleaned_text
