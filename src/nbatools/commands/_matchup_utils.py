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


# ---------------------------------------------------------------------------
# Matchup / head-to-head helpers
# ---------------------------------------------------------------------------

MATCHUP_NOISE_PATTERN = r"\b(?:head\s*[- ]\s*to\s*[- ]\s*head|h2h|matchup|matchups)\b"


def strip_matchup_noise(text: str) -> str:
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
