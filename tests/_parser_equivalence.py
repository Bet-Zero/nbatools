"""Equivalence-group test helpers for parser phrasing parity.

Phase A of the parser/query-surface expansion plan centers on proving that
semantically equivalent surface forms (full question, search phrase,
compressed shorthand) produce identical parse states. This module provides
the reusable assertion primitive used across equivalence-group tests.

Usage pattern (copy into a test module):

    from tests._parser_equivalence import assert_parse_equivalence

    def test_points_leaders_last_10_games():
        assert_parse_equivalence([
            "Who has the most points in the last 10 games?",
            "most points last 10 games",
            "points leaders last 10",
        ])

See ``docs/architecture/parser/examples.md`` §7 for the catalog of
equivalence groups this is designed against, and
``docs/planning/phase_a_work_queue.md`` for the broader Phase A work this
helper supports.
"""

from __future__ import annotations

from collections.abc import Iterable

from nbatools.commands.natural_query import parse_query

# Fields that legitimately differ across surface forms or are not yet part
# of the parse contract. Excluded from equivalence comparison.
#
# - ``normalized_query`` carries the raw input through, so of course it
#   varies per form.
# - ``confidence`` / ``alternates`` / ``intent`` are reserved for Phase D
#   (canonical parse formalization); they are excluded pre-emptively so
#   this helper keeps working once they land.
_DEFAULT_EXCLUDE: frozenset[str] = frozenset(
    {"normalized_query", "confidence", "alternates", "intent"}
)


def _canonical(parse_state: dict, exclude: frozenset[str]) -> dict:
    """Return the parse-state slice that must match across equivalent forms."""
    return {k: v for k, v in parse_state.items() if k not in exclude}


def assert_parse_equivalence(
    surface_forms: Iterable[str],
    *,
    exclude_keys: Iterable[str] | None = None,
) -> dict:
    """Assert every surface form parses to the same canonical parse state.

    "Equivalent" means identical ``route``, ``route_kwargs``, and slot values
    (player, team, stat, thresholds, timeframe, etc.) — everything in the
    parse state except fields in ``_DEFAULT_EXCLUDE`` (plus any extras in
    ``exclude_keys``).

    Returns the reference parse state (from the first surface form) so
    callers can make additional, more targeted assertions on it.
    """
    forms = list(surface_forms)
    if len(forms) < 2:
        raise ValueError("assert_parse_equivalence needs at least two surface forms")

    exclude = _DEFAULT_EXCLUDE | frozenset(exclude_keys or ())

    reference_form = forms[0]
    reference_state = parse_query(reference_form)
    reference_canonical = _canonical(reference_state, exclude)

    for form in forms[1:]:
        state = parse_query(form)
        canonical = _canonical(state, exclude)
        assert canonical == reference_canonical, (
            f"Parse state divergence between equivalent surface forms:\n"
            f"  reference: {reference_form!r}\n"
            f"    -> {reference_canonical}\n"
            f"  diverging: {form!r}\n"
            f"    -> {canonical}\n"
            f"  differing keys: "
            f"{sorted(_diff_keys(reference_canonical, canonical))}"
        )

    return reference_state


def _diff_keys(a: dict, b: dict) -> set[str]:
    """Return the set of keys whose values differ (or that exist in only one)."""
    return {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
