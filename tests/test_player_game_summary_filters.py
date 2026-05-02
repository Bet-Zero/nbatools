from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.player_game_summary import _apply_filters

pytestmark = pytest.mark.engine


def test_player_filter_normalizes_accents_spacing_case_and_dash_variants():
    df = pd.DataFrame(
        [
            {
                "game_date": "2026-01-01",
                "player_name": "  NIKOLA JOKIC ",
                "pts": 30,
            },
            {
                "game_date": "2026-01-02",
                "player_name": "Shai Gilgeous\u2011Alexander",
                "pts": 31,
            },
            {
                "game_date": "2026-01-03",
                "player_name": "Stephen Curry",
                "pts": 32,
            },
        ]
    )

    jokic = _apply_filters(df, player="Nikola Jokić")
    sga = _apply_filters(df, player="Shai Gilgeous-Alexander")

    assert jokic["pts"].tolist() == [30]
    assert sga["pts"].tolist() == [31]
