"""Team splits with a resolved opponent list ("Lakers home vs away splits
against winning teams") must describe the opponents, not crash on them."""

from __future__ import annotations

import pytest

from nbatools.commands.structured_results import SplitSummaryResult

pytestmark = pytest.mark.fixture_data


def test_opponent_list_names_the_opponents_in_the_caveat():
    from nbatools.commands.team_split_summary import build_result

    result = build_result(
        split="home_away",
        season="2024-25",
        team="LAL",
        opponent=["BOS", "NYK", "DEN", "OKC"],
    )
    assert isinstance(result, SplitSummaryResult)
    assert "filtered to games vs 4 opponents (BOS, DEN, NYK, ...)" in result.caveats
