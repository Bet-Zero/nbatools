"""Required 2023-24 ranked-zero evidence from the configured real snapshot.

No fixture fallback or per-case skip: absent coverage or absent discriminating
rows fails acceptance. Expected membership and ordering use the loaded raw
values, never the query's parser, filters, or ranking helpers.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
SEASON = "2023-24"
SEASON_TYPE = "Regular Season"


def _qualify_rows(frame, keys, values):
    required = {
        *keys,
        *values,
        "season",
        "season_type",
        "game_date",
        "team_abbr",
        "opponent_team_abbr",
    }
    assert not frame.empty, "Required real-data sample is unavailable"
    assert required.issubset(frame.columns), required - set(frame.columns)
    assert frame[list(required)].notna().all().all(), "Required row values are missing"
    assert set(frame.season) == {SEASON}
    assert set(frame.season_type) == {SEASON_TYPE}
    assert not frame.duplicated(keys).any(), "Duplicate game-grain keys"
    for column in values:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        assert numeric.notna().all(), f"Invalid required numeric column: {column}"
    assert pd.to_datetime(frame.game_date, errors="coerce").notna().all()
    return frame.to_dict("records")


# Match the function-scoped needs_data guard: ordinary no-data CI skips before
# loading required rows, while the R2 harness still rejects every required skip.
@pytest.fixture
def teams():
    from nbatools.commands.freshness import manifest_entry
    from nbatools.data_source import data_read_csv

    # The same legacy qualification used by served-coverage acceptance remains
    # explicit; a missing/failed receipt is not treated as a valid empty sample.
    receipt = manifest_entry(SEASON, SEASON_TYPE)
    assert receipt is not None, "Required season receipt/backfill record is missing"
    assert receipt["validation_state"] in {"passed", "legacy_unverified"}, receipt
    assert receipt["raw_complete"] and receipt["processed_complete"], receipt
    frame = data_read_csv(Path(f"data/raw/team_game_stats/{SEASON}_regular_season.csv"))
    assert "team_name" in frame and frame.team_name.notna().all()
    return _qualify_rows(
        frame,
        ["game_id", "team_id"],
        ["pts", "blk", "tov"],
    )


def _team_rows(teams, abbreviation):
    rows = [row for row in teams if row["team_abbr"] == abbreviation]
    assert len(rows) == 82, f"Incomplete {SEASON} regular-season coverage for {abbreviation}"
    assert len({row["game_id"] for row in rows}) == 82
    return rows


def _ranked(rows, limit):
    return sorted(
        rows,
        key=lambda row: (float(row["pts"]), pd.Timestamp(row["game_date"])),
        reverse=True,
    )[:limit]


def _identity_and_values(row, metric, player=False):
    return (
        int(row["game_id"]),
        int(row["player_id"]) if player else row["team_abbr"],
        row["team_abbr"],
        row["opponent_team_abbr"],
        str(row["game_date"])[:10],
        float(row["pts"]),
        float(row[metric]),
    )


def _assert_ranked_answer(query, expected, metric, *, player=False):
    from nbatools.query_service import execute_natural_query

    assert expected, "This required positive case needs a nonempty independent oracle"
    payload = execute_natural_query(query).result.to_dict()
    assert payload["result_status"] == "ok", payload
    assert payload["query_class"] == "finder", payload
    actual = payload["sections"]["finder"]
    assert [_identity_and_values(row, metric, player) for row in actual] == [
        _identity_and_values(row, metric, player) for row in expected
    ]
    assert [row["rank"] for row in actual] == list(range(1, len(expected) + 1))
    assert {row["season"] for row in actual} == {SEASON}
    assert {row["season_type"] for row in actual} == {SEASON_TYPE}


@pytest.fixture
def zero_block_matchup(teams):
    knicks = _team_rows(teams, "NYK")
    # Select a real discriminating matchup, without assuming a particular
    # opponent had a zero-block game. Its absence fails, never skips this case.
    for opponent in sorted({row["opponent_team_abbr"] for row in knicks}):
        own = [row for row in knicks if row["opponent_team_abbr"] == opponent]
        zero = [row for row in own if float(row["blk"]) == 0]
        top_two = _ranked(own, 2)
        if not zero or len(top_two) != 2 or not any(float(r["blk"]) > 0 for r in top_two):
            continue
        other = [row for row in _team_rows(teams, opponent) if row["opponent_team_abbr"] == "NYK"]
        assert {row["game_id"] for row in own} == {row["game_id"] for row in other}
        opposite_zero = {row["game_id"] for row in other if float(row["blk"]) == 0}
        if {row["game_id"] for row in zero} != opposite_zero:
            names = {row["team_name"] for row in other}
            assert len(names) == 1, "Opponent must have one raw team name"
            return own, zero, next(iter(names))
    pytest.fail("No qualified NYK matchup distinguishes own zero blocks from opponent/floor")


@pytest.mark.parametrize("owner_first", [True, False], ids=["owner-first", "opponent-first"])
@pytest.mark.parametrize(
    "condition", ["without any blocks", "with 0+ blocks", "with 0 blocks or more"]
)
def test_team_zero_owner_opponent_and_top_n_2023_24(zero_block_matchup, owner_first, condition):
    own, zero, opponent = zero_block_matchup
    owner = f"by Knicks vs {opponent}" if owner_first else f"vs {opponent} by Knicks"
    expected = _ranked(zero if condition == "without any blocks" else own, 2)
    _assert_ranked_answer(f"top 2 scoring games {owner} {condition} in {SEASON}", expected, "blk")


@pytest.fixture
def bam_games(teams):
    from nbatools.data_source import data_read_csv

    miami = _team_rows(teams, "MIA")
    frame = data_read_csv(Path(f"data/raw/player_game_stats/{SEASON}_regular_season.csv"))
    frame = frame[frame.player_name.eq("Bam Adebayo")]
    assert frame.player_id.nunique() == 1, "Bam Adebayo must resolve to one raw player ID"
    rows = _qualify_rows(frame, ["game_id", "player_id"], ["pts", "plus_minus"])
    assert {row["team_abbr"] for row in rows} == {"MIA"}
    team_dates = {int(row["game_id"]): str(row["game_date"])[:10] for row in miami}
    assert all(team_dates.get(int(row["game_id"])) == str(row["game_date"])[:10] for row in rows)
    assert any(float(row["plus_minus"]) < 0 for row in rows)
    assert any(float(row["plus_minus"]) == 0 for row in rows)
    assert any(float(row["plus_minus"]) > 0 for row in rows)
    return rows


@pytest.mark.parametrize(
    "condition", ["with zero plus-minus", "with 0+ plus minus", "with 0 plus minus or more"]
)
def test_player_signed_zero_and_floor_rank_2023_24(bam_games, condition):
    exact = condition == "with zero plus-minus"
    selected = [
        row
        for row in bam_games
        if (float(row["plus_minus"]) == 0 if exact else float(row["plus_minus"]) >= 0)
    ]
    expected = _ranked(selected, 5)
    if not exact:
        assert len(expected) == 5 and any(float(row["plus_minus"]) > 0 for row in expected)
    _assert_ranked_answer(
        f"Bam Adebayo top 5 scoring games {condition} in {SEASON}",
        expected,
        "plus_minus",
        player=True,
    )


def test_known_zero_turnover_empty_is_no_match_2023_24(teams):
    from nbatools.query_service import execute_natural_query

    nuggets = _team_rows(teams, "DEN")
    warriors = _team_rows(teams, "GSW")
    own = [row for row in nuggets if row["opponent_team_abbr"] == "GSW"]
    other = [row for row in warriors if row["opponent_team_abbr"] == "DEN"]
    assert own and {row["game_id"] for row in own} == {row["game_id"] for row in other}
    assert all(float(row["tov"]) > 0 for row in own), "This required empty case is no longer empty"
    payload = execute_natural_query(
        f"best scoring games by Nuggets vs Warriors without turnovers in {SEASON}"
    ).result.to_dict()
    assert payload["result_status"] == "no_result", payload
    assert payload["result_reason"] == "no_match", payload
    assert not payload["sections"].get("finder")
