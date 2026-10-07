"""C2 franchise identity: a relocated or renamed team keeps its earlier seasons.

Team rows carry the abbreviation the team had that season (SEA, NJN, VAN,
CHH, NOH, NOK). Filters matched only that abbreviation or name, so "Thunder
playoff appearances since 2000" dropped the Seattle seasons and "Nets record
in 2002-03" found no games. Matching now also uses the franchise ``team_id``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._franchise import franchise_caveat, franchise_team_id, team_value_mask
from nbatools.commands.data_utils import build_opponent_mask

pytestmark = [pytest.mark.query]

OKC, BKN, MEM = 1610612760, 1610612751, 1610612763


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # team, name, id, opponent, opponent id
            ("SEA", "Seattle SuperSonics", OKC, "NJN", BKN),
            ("OKC", "Oklahoma City Thunder", OKC, "BKN", BKN),
            ("NJN", "New Jersey Nets", BKN, "SEA", OKC),
            ("VAN", "Vancouver Grizzlies", MEM, "SEA", OKC),
            ("MEM", "Memphis Grizzlies", MEM, "OKC", OKC),
        ],
        columns=["team_abbr", "team_name", "team_id", "opponent_team_abbr", "opponent_team_id"],
    ).assign(opponent_team_name="")


def test_current_abbreviation_names_the_franchise_id():
    assert franchise_team_id("OKC") == OKC
    assert franchise_team_id("bkn") == BKN
    # A historical abbreviation names only its own era.
    assert franchise_team_id("SEA") is None
    assert franchise_team_id("Oklahoma City Thunder") is None


def test_team_mask_keeps_earlier_names_of_the_franchise():
    rows = _rows()
    assert rows[team_value_mask(rows, "OKC")]["team_abbr"].tolist() == ["SEA", "OKC"]
    assert rows[team_value_mask(rows, "MEM")]["team_abbr"].tolist() == ["VAN", "MEM"]
    # "SEA" alone stays the Seattle era.
    assert rows[team_value_mask(rows, "SEA")]["team_abbr"].tolist() == ["SEA"]


def test_opponent_masks_keep_earlier_names():
    rows = _rows()
    by_prefix = rows[team_value_mask(rows, "OKC", prefix="opponent_")]
    assert by_prefix["team_abbr"].tolist() == ["NJN", "VAN", "MEM"]
    shared = rows[build_opponent_mask(rows, "OKC")]
    assert shared["team_abbr"].tolist() == ["NJN", "VAN", "MEM"]
    assert rows[build_opponent_mask(rows, ["BKN"])]["team_abbr"].tolist() == ["SEA", "OKC"]


def test_caveat_names_the_earlier_seasons():
    rows = _rows()
    assert franchise_caveat(rows[team_value_mask(rows, "OKC")], "OKC") == (
        "includes the franchise's seasons as the Seattle SuperSonics"
    )
    assert franchise_caveat(rows[team_value_mask(rows, "SEA")], "SEA") is None
