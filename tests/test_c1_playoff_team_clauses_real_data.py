"""Playoff-team opponent clauses against the real game rows.

"when playing teams that made the playoffs" must filter the same opponents as
"vs teams that made the playoffs" (it switched to playoff games).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    "variant",
    [
        "Lakers record when playing teams that made the playoffs in 2023-24",
        "Lakers record facing teams that made the playoffs in 2023-24",
    ],
)
def test_playing_clause_matches_the_vs_clause(variant):
    from nbatools.query_service import execute_natural_query

    base = execute_natural_query("Lakers record vs teams that made the playoffs in 2023-24")
    other = execute_natural_query(variant)
    assert base.result_status == other.result_status == "ok"
    first = base.result.to_dict()["sections"]["summary"][0]
    second = other.result.to_dict()["sections"]["summary"][0]
    assert (second["wins"], second["losses"]) == (first["wins"], first["losses"])
    assert first["wins"] + first["losses"] < 82
