"""Official player-game availability observations are not absence complements."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import (
    COVERAGE,
    SOURCE,
    _minutes,
    backfill,
    normalize_boxscore_availability,
    validate_availability,
)

pytestmark = pytest.mark.engine


def boxscore(game=22500001):
    return pd.DataFrame(
        [
            dict(
                gameId=game,
                teamId=1,
                teamTricode="BOS",
                personId=10,
                firstName="A",
                familyName="Played",
                minutes="PT25M30S",
                comment="",
            ),
            dict(
                gameId=game,
                teamId=1,
                teamTricode="BOS",
                personId=11,
                firstName="B",
                familyName="CoachDNP",
                minutes=None,
                comment="DNP - Coach's Decision",
            ),
            dict(
                gameId=game,
                teamId=1,
                teamTricode="BOS",
                personId=12,
                firstName="C",
                familyName="Unavailable",
                minutes=None,
                comment="DND - Injury/Illness",
            ),
            dict(
                gameId=game,
                teamId=2,
                teamTricode="NYK",
                personId=20,
                firstName="D",
                familyName="Unknown",
                minutes="0:00",
                comment="",
            ),
            dict(
                gameId=game,
                teamId=2,
                teamTricode="NYK",
                personId=21,
                firstName="E",
                familyName="Inactive",
                minutes=None,
                comment="INACTIVE",
            ),
        ]
    )


def normalized(raw=None, game=22500001):
    return normalize_boxscore_availability(
        boxscore(game) if raw is None else raw,
        game_id=game,
        game_date="2025-10-22",
        season="2025-26",
        season_type="Regular Season",
        expected_team_ids={1, 2},
    )


def test_source_preserves_explicit_nonplayers_and_unknown_without_inventing_rows():
    rows = normalized()
    assert list(rows["participation_state"]) == [
        "played",
        "did_not_play",
        "did_not_play",
        "unknown",
        "did_not_play",
    ]
    assert len(rows) == 5
    assert rows["coverage_scope"].eq(COVERAGE).all()
    assert rows["source"].eq(SOURCE).all()
    assert rows.loc[rows.player_id.eq(12), "source_comment"].iloc[0] == "DND - Injury/Illness"
    assert rows.loc[rows.player_id.eq(20), "participation_state"].iloc[0] == "unknown"
    assert 99 not in rows.player_id.tolist()
    validate_availability(rows)


@pytest.mark.parametrize(
    "value,expected",
    [("PT30M05S", 30 + 5 / 60), ("15:45", 15.75), ("0:00", 0.0), (0, 0.0), (None, None)],
)
def test_minutes(value, expected):
    assert (
        _minutes(value) == pytest.approx(expected)
        if expected is not None
        else _minutes(value) is None
    )


@pytest.mark.parametrize("value", ["PT", "9:61", "-1", "NaN", "abc", "3:04:12"])
def test_malformed_minutes_fail_closed(value):
    with pytest.raises(ValueError, match="duration"):
        _minutes(value)


def test_duplicate_or_cross_game_team_data_rejected():
    raw = boxscore()
    with pytest.raises(ValueError, match="Duplicate"):
        normalized(pd.concat([raw, raw.iloc[[1]]]))
    with pytest.raises(ValueError, match="teams"):
        normalized(raw[raw.teamId.eq(1)])
    with pytest.raises(ValueError, match="game ID"):
        normalized(raw.assign(gameId=12345))


def test_conflicting_explicit_dnp_and_played_minutes_is_invalid():
    raw = boxscore()
    raw.loc[raw.personId.eq(11), "minutes"] = "PT04M10S"
    with pytest.raises(ValueError, match="Contradictory"):
        normalized(raw)


def test_reject_unsupported_reason_and_invalid_false_completeness():
    raw = boxscore()
    raw.loc[raw.personId.eq(11), "comment"] = "check with trainer"
    rows = normalized(raw)
    assert rows.loc[rows.player_id.eq(11), "participation_state"].iloc[0] == "unknown"
    rows.loc[rows.player_id.eq(11), "participation_state"] = "did_not_play"
    with pytest.raises(ValueError, match="explicit"):
        validate_availability(rows)
    rows = normalized()
    rows.loc[0, "coverage_scope"] = "entire_roster"
    with pytest.raises(ValueError, match="completeness"):
        validate_availability(rows)


def test_cached_backfill_acquires_dnp_with_atomic_rerun(tmp_path):
    root = tmp_path / "data"
    games_dir = root / "raw" / "games"
    games_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            dict(
                game_id="0022500001",
                game_date="2025-10-22",
                season="2025-26",
                season_type="Regular Season",
                is_final=True,
                home_team_id=1,
                away_team_id=2,
            )
        ]
    ).to_csv(games_dir / "2025-26_regular_season.csv", index=False)
    archive = tmp_path / "archived"
    archive.mkdir()
    records = boxscore().to_dict("records")
    (archive / "boxscore_0022500001.json").write_text(
        json.dumps({"boxScoreTraditional": {"playerStats": records}}), encoding="utf-8"
    )
    one = backfill("2025-26", root=root, cached_boxscores=archive)
    two = backfill("2025-26", root=root, cached_boxscores=archive)
    assert len(one) == len(two) == 5
    assert int(one.participation_state.eq("did_not_play").sum()) == 3
    assert one.game_id.tolist() == ["0022500001"] * 5
    assert not (root / "raw/player_game_availability/2025-26_regular_season.partial.csv").exists()


def test_missing_archived_game_does_not_publish_partial_sample(tmp_path):
    root = tmp_path / "data"
    games_dir = root / "raw" / "games"
    games_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            dict(
                game_id="0022500002",
                game_date="2025-10-22",
                season="2025-26",
                season_type="Regular Season",
                is_final=True,
                home_team_id=1,
                away_team_id=2,
            )
        ]
    ).to_csv(games_dir / "2025-26_regular_season.csv", index=False)
    with pytest.raises(FileNotFoundError, match="archive missing"):
        backfill("2025-26", root=root, cached_boxscores=tmp_path)
    assert not (root / "raw/player_game_availability/2025-26_regular_season.csv").exists()


def test_selected_unknown_game_refused(tmp_path):
    root = tmp_path / "data"
    p = root / "raw" / "games"
    p.mkdir(parents=True)
    pd.DataFrame(
        [
            dict(
                game_id="0022500001",
                game_date="2025-10-22",
                season="2025-26",
                season_type="Regular Season",
                is_final=True,
                home_team_id=1,
                away_team_id=2,
            )
        ]
    ).to_csv(p / "2025-26_regular_season.csv", index=False)
    with pytest.raises(ValueError, match="not in finalized"):
        backfill("2025-26", root=root, game_ids=[22500002])
