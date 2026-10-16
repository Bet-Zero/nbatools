"""Synthetic counterexamples for the required shooting oracle, not NBA evidence."""

import pandas as pd
import pytest

from tests.shooting_rate_oracle import assert_shooting_rows


@pytest.mark.parametrize("made,attempts,rate", [(1, 12, 0.083), (19, 21, 0.905)])
def test_source_precision_and_exact_counts(made, attempts, rate):
    row = dict(
        season="2023-24",
        game_id=1,
        player_id=2,
        team_abbr="LAL",
        opponent_team_abbr="BOS",
        game_date="2024-01-01",
        fgm=made,
        fga=attempts,
        fg_pct=rate,
        rank=1,
    )
    source = pd.DataFrame([row])
    assert_shooting_rows(source, [row], percentage="fg_pct", made="fgm", attempts="fga")
    for column, bad in [
        ("fgm", made + 1),
        ("fga", attempts + 1),
        ("fg_pct", made / attempts),
        ("rank", 2),
        ("opponent_team_abbr", "NYK"),
        ("game_id", 99),
    ]:
        with pytest.raises((AssertionError, KeyError)):
            assert_shooting_rows(
                source, [{**row, column: bad}], percentage="fg_pct", made="fgm", attempts="fga"
            )


def test_tied_cutoff_preserves_attempts_and_date_order():
    base = dict(season="2023-24", team_abbr="LAL", opponent_team_abbr="BOS", fg_pct=0.5)
    rows = [
        dict(base, game_id=1, player_id=1, game_date="2024-01-02", fgm=6, fga=12),
        dict(base, game_id=1, player_id=2, game_date="2024-01-02", fgm=6, fga=12),
        dict(base, game_id=2, player_id=1, game_date="2024-01-01", fgm=5, fga=10),
    ]
    source = pd.DataFrame(rows)
    for tied in rows[:2]:
        assert_shooting_rows(
            source, [{**tied, "rank": 1}], percentage="fg_pct", made="fgm", attempts="fga", limit=1
        )
    with pytest.raises(AssertionError):
        assert_shooting_rows(
            source,
            [{**rows[2], "rank": 1}],
            percentage="fg_pct",
            made="fgm",
            attempts="fga",
            limit=1,
        )


@pytest.mark.parametrize(
    "made,attempts,allowed", [(1, 16, (0.062, 0.063)), (15, 16, (0.937, 0.938))]
)
def test_exact_halfway_source_precision_without_assuming_a_tie_rule(made, attempts, allowed):
    row = dict(
        season="2023-24",
        game_id=1,
        player_id=2,
        team_abbr="LAL",
        opponent_team_abbr="BOS",
        game_date="2024-01-01",
        fgm=made,
        fga=attempts,
        rank=1,
    )
    for rate in allowed:
        original = {**row, "fg_pct": rate}
        assert_shooting_rows(
            pd.DataFrame([original]), [original], percentage="fg_pct", made="fgm", attempts="fga"
        )
    for bad in (made / attempts, allowed[0] - 0.001, allowed[1] + 0.001):
        original = {**row, "fg_pct": bad}
        with pytest.raises(AssertionError):
            assert_shooting_rows(
                pd.DataFrame([original]),
                [original],
                percentage="fg_pct",
                made="fgm",
                attempts="fga",
            )
