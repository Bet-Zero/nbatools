"""Placeholder route for lineup summary queries.

The parser can recognize lineup phrasing, but the current data layer does not
expose lineup-unit aggregates or stint-level data. This route exists so natural
and structured queries can return an honest placeholder result until that data
ingestion path is available.
"""

from __future__ import annotations

from nbatools.commands._parse_helpers import build_lineup_note
from nbatools.commands.structured_results import NoResult


def build_result(
    *,
    lineup_members: list[str] | None = None,
    unit_size: int | None = None,
    minute_minimum: int | None = None,
    **_: object,
) -> NoResult:
    """Return an explicit placeholder until real lineup data is available."""
    if not lineup_members:
        raise ValueError("lineup_summary requires lineup_members")

    notes: list[str] = []
    if lineup_note := build_lineup_note(
        lineup_members=lineup_members,
        unit_size=unit_size,
        minute_minimum=minute_minimum,
    ):
        notes.append(lineup_note)

    return NoResult(
        query_class="summary",
        reason="unsupported",
        notes=notes,
    )
