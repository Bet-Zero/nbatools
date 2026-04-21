"""Placeholder route for on/off queries.

The parser can recognize on/off phrasing, but the current data layer does not
expose possession- or lineup-stint-level splits. This route exists so natural
and structured queries can return an honest placeholder result until that data
ingestion path is available.
"""

from __future__ import annotations

from nbatools.commands._parse_helpers import build_on_off_note
from nbatools.commands.structured_results import NoResult


def build_result(
    *,
    lineup_members: list[str] | None = None,
    presence_state: str | None = None,
    **_: object,
) -> NoResult:
    """Return an explicit placeholder until real on/off data is available."""
    if not lineup_members or presence_state is None:
        raise ValueError("player_on_off requires lineup_members and presence_state")

    notes: list[str] = []
    if on_off_note := build_on_off_note(
        lineup_members=lineup_members,
        presence_state=presence_state,
    ):
        notes.append(on_off_note)

    return NoResult(
        query_class="summary",
        reason="unsupported",
        notes=notes,
    )
