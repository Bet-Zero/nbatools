"""Raw-row checks for the existing source-percentage shooting-game contract."""

import pandas as pd


def assert_shooting_rows(raw, listed, *, percentage, made, attempts, limit=10):
    """Check identities, counts, source precision and ranking, including tied cutoffs."""
    assert len(listed) == min(limit, len(raw)) > 0
    identity = ["season", "game_id", "player_id", "team_abbr"]
    assert not raw[identity].isna().any().any()
    assert not raw.duplicated(identity).any()

    def key(row):
        return row["season"], int(row["game_id"]), int(row["player_id"]), row["team_abbr"]

    def ranking(row):
        return float(row[percentage]), -int(row[attempts]), pd.Timestamp(row["game_date"])

    source = {key(row): row for row in raw.to_dict("records")}
    assert len({key(row) for row in listed}) == len(listed)
    for rank, row in enumerate(listed, start=1):
        original = source[key(row)]
        assert row["rank"] == rank
        assert row[made] == original[made]
        assert row[attempts] == original[attempts]
        assert row["opponent_team_abbr"] == original["opponent_team_abbr"]
        assert pd.Timestamp(row["game_date"]) == pd.Timestamp(original["game_date"])
        # Stored NBA percentages have three decimals. The serializer preserves
        # them; it does not turn a missing-column computed ratio into 3 decimals.
        assert row[percentage] == original[percentage]
        numerator, denominator = int(original[made]), int(original[attempts])
        assert numerator == original[made] and denominator == original[attempts] > 0
        thousandths, remainder = divmod(numerator * 1000, denominator)
        # Exact nearest-thousandth arithmetic. At an exact halfway value the
        # source's tie rule is unspecified, so either nearest value is valid.
        allowed = set()
        if 2 * remainder <= denominator:
            allowed.add(thousandths / 1000)
        if 2 * remainder >= denominator:
            allowed.add((thousandths + 1) / 1000)
        assert original[percentage] in allowed
    # Exact source-row membership plus the complete ranking-key sequence allows
    # only legitimate equal-key ties at the limit, not arbitrary reordered IDs.
    assert [ranking(row) for row in listed] == sorted(ranking(row) for row in source.values())[
        :limit
    ]
