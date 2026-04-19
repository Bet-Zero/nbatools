"""Centralized glossary of fuzzy-term definitions and product-policy defaults.

This module is the single source of truth for how the parser interprets
fuzzy, subjective, and shorthand terms.  Downstream code should read from
these data structures rather than hardcoding values.

Each entry records:
  - ``expansion``: what the term resolves to at parse time
  - ``shipped``: whether the term is currently supported in the parser

Spec mirror: docs/architecture/parser/specification.md §18
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Time terms (spec §18.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FuzzyTimeTerm:
    """Definition of a fuzzy time word and its deterministic expansion."""

    expansion: str
    shipped: bool = True


# --- last_n expansions (resolve to ``extract_last_n`` returning an int) ---
FUZZY_LAST_N_TERMS: dict[str, int] = {
    "recently": 10,
    "lately": 10,
}

# --- date-range expansions (resolve to ``extract_date_range``) ---


@dataclass(frozen=True, slots=True)
class DateRangeTerm:
    """A fuzzy time phrase that maps to a rolling date window."""

    regex: str
    days_back: int | None = None
    same_day: bool = False
    yesterday: bool = False
    shipped: bool = True


FUZZY_DATE_TERMS: list[DateRangeTerm] = [
    # `last night` / `yesterday` → yesterday's date
    DateRangeTerm(regex=r"\b(?:last\s+night|yesterday)\b", yesterday=True),
    # `today` / `tonight` → today's date
    DateRangeTerm(regex=r"\b(?:today|tonight)\b", same_day=True),
    # `past month` / `last month` → rolling 30 days
    DateRangeTerm(regex=r"\b(?:past|last)\s+month\b", days_back=30),
    # `last couple weeks` / `past 2 weeks` / `past few weeks` → rolling 14 days
    DateRangeTerm(regex=r"\b(?:past|last)\s+(?:couple|couple\s+of|few|2)\s+weeks?\b", days_back=14),
]


# ---------------------------------------------------------------------------
# Opponent-quality definitions (spec §18.2) — reserved, not yet shipped
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpponentQualityTerm:
    """A fuzzy opponent-quality bucket — reserved for Phase E."""

    definition: str
    shipped: bool = False


OPPONENT_QUALITY_TERMS: dict[str, OpponentQualityTerm] = {
    "good teams": OpponentQualityTerm("Teams with win % >= .500"),
    "winning teams": OpponentQualityTerm("Teams with win % >= .500"),
    "top teams": OpponentQualityTerm("Top 8 by net rating"),
    "contenders": OpponentQualityTerm("Top 6 by net rating"),
    "playoff teams": OpponentQualityTerm("Teams currently in top 10 of conference"),
    "top-10 defenses": OpponentQualityTerm("Top 10 by defensive rating"),
    "top-10 offenses": OpponentQualityTerm("Top 10 by offensive rating"),
    "elite defenses": OpponentQualityTerm("Top 5 by defensive rating"),
    "bad teams": OpponentQualityTerm("Teams with win % < .400"),
}


# ---------------------------------------------------------------------------
# Subjective / skill terms (spec §18.3) — reserved, not yet shipped
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubjectiveTerm:
    """A fuzzy skill or quality term — reserved for future phases."""

    definition: str
    shipped: bool = False


SUBJECTIVE_TERMS: dict[str, SubjectiveTerm] = {
    "best games": SubjectiveTerm("Ranked by Game Score (default); by points if specified"),
    "biggest games": SubjectiveTerm("Ranked by points scored"),
    "hottest": SubjectiveTerm("Rolling average over last 5 games, ranked"),
    "efficient": SubjectiveTerm("Ranked by True Shooting %"),
    "clutch": SubjectiveTerm("Last 5 min of 4th quarter or OT, score within 5", shipped=True),
    "all-around games": SubjectiveTerm("Undefined — not yet shipped"),
    "catch-and-shoot": SubjectiveTerm("Undefined — not yet shipped"),
    "transition scorer": SubjectiveTerm("Undefined — not yet shipped"),
}
