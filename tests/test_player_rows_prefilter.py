"""Loading one player's seasons keeps exactly the rows his selection uses.

A career query used to concatenate every league-wide season frame (about
700 MB across 30 seasons) and only then pick one player's rows. The loader
now cuts each season to that player's candidate ids first; the selected rows
and any shared-name note must not change.
"""

from __future__ import annotations

import pandas as pd
import pytest

pytestmark = [pytest.mark.fixture_data]

SEASONS = ["2023-24", "2024-25", "2025-26"]


@pytest.mark.parametrize(
    "player",
    ["LeBron James", "lebron james", "Nikola Jokic", "Stephen Curry", "Not A Player"],
)
def test_prefiltered_load_selects_the_same_rows(player):
    from nbatools.commands._player_identity import select_player_rows
    from nbatools.commands.data_utils import load_player_games_for_seasons

    full = load_player_games_for_seasons(SEASONS, "Regular Season")
    cut = load_player_games_for_seasons(SEASONS, "Regular Season", player=player)
    full_notes: list[str] = []
    cut_notes: list[str] = []

    expected = select_player_rows(full, player, notes=full_notes)
    actual = select_player_rows(cut, player, notes=cut_notes)

    assert len(cut) < len(full)
    pd.testing.assert_frame_equal(
        actual.sort_values(["game_id", "player_id"]).reset_index(drop=True),
        expected.sort_values(["game_id", "player_id"]).reset_index(drop=True),
    )
    assert cut_notes == full_notes


def test_prefilter_keeps_every_id_stored_under_the_name_in_any_season():
    from nbatools.commands._player_identity import player_rows_prefilter

    a = pd.DataFrame({"player_id": [1, 2], "player_name": ["Sam Doe", "Other"]})
    # Same player id stored under a second spelling in a later season.
    b = pd.DataFrame({"player_id": [1, 3], "player_name": ["Sam Doe Jr.", "Other"]})

    cut_a, cut_b = player_rows_prefilter([a, b], "Sam Doe")

    assert cut_a["player_id"].tolist() == [1]
    assert cut_b["player_id"].tolist() == [1]
