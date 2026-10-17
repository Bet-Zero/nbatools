"""ESPN source requires exact NBA game + identity matching, not name guesses."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_espn as adapter
from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    normalize_boxscore_availability,
)

pytestmark = pytest.mark.engine


@pytest.fixture
def sources(tmp_path, monkeypatch):
    root = tmp_path / "data"
    for subdir in ("games", "team_game_stats", "player_game_stats"):
        (root / "raw" / subdir).mkdir(parents=True)
    pd.DataFrame([{
        "game_id": "0022500001", "game_date": "2025-10-21", "season": "2025-26",
        "season_type": "Regular Season", "is_final": True,
        "home_team_id": 1610612747, "away_team_id": 1610612744,
    }]).to_csv(root / "raw/games/2025-26_regular_season.csv", index=False)
    pd.DataFrame([
        {"game_id": "0022500001", "team_id": 1610612747, "team_abbr": "LAL", "pts": 109},
        {"game_id": "0022500001", "team_id": 1610612744, "team_abbr": "GSW", "pts": 119},
    ]).to_csv(root / "raw/team_game_stats/2025-26_regular_season.csv", index=False)
    # A source-reported DNP need not appear in this game log; his verified
    # NBA ID is resolved from a different game with the SAME team/season.
    pd.DataFrame([
        {"game_id": "0022500002", "team_id": 1610612747,
         "player_id": 10, "player_name": "LeBron James"},
        {"game_id": "0022500002", "team_id": 1610612747,
         "player_id": 11, "player_name": "Bronny James"},
        {"game_id": "0022500002", "team_id": 1610612744,
         "player_id": 20, "player_name": "Jimmy Butler III"},
    ]).to_csv(root / "raw/player_game_stats/2025-26_regular_season.csv", index=False)

    event = {
        "id": "401809244",
        "competitions": [{"competitors": [
            {"team": {"abbreviation": "LAL"}, "score": "109"},
            {"team": {"abbreviation": "GS"}, "score": "119"},
        ]}],
    }
    boxscore = {"boxscore": {"players": [
        {
            "team": {"abbreviation": "LAL"},
            "statistics": [{"names": ["MIN", "PTS"], "athletes": [
                {"athlete": {"displayName": "LeBron James"}, "didNotPlay": False,
                 "stats": ["30", "18"]},
                {"athlete": {"displayName": "Bronny James"}, "didNotPlay": True,
                 "stats": ["--", "--"], "reason": "COACH'S DECISION"},
            ]}],
        },
        {
            "team": {"abbreviation": "GS"},
            "statistics": [{"names": ["MIN", "PTS"], "athletes": [
                {"athlete": {"displayName": "Jimmy Butler"}, "didNotPlay": False,
                 "stats": ["35", "31"], "reason": "COACH'S DECISION"},
            ]}],
        },
    ]}}
    monkeypatch.setattr(adapter, "_scoreboard", lambda _: {"events": [event]})
    monkeypatch.setattr(adapter, "_get_json", lambda _: boxscore)
    return root, event, boxscore


def test_espn_player_game_is_verified_and_source_reported(sources):
    root, _event, _box = sources
    rows = backfill("2025-26", root=root, source="espn")
    assert len(rows) == 3
    assert dict(zip(rows.player_id, rows.participation_state)) == {
        10: "played", 11: "did_not_play", 20: "played",
    }
    assert rows.source.eq("espn_game_summary:401809244").all()
    dnp = rows.loc[rows.player_id.eq(11)].iloc[0]
    assert dnp.source_comment == "DNP - ESPN confirmed didNotPlay"
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    # Source only lists 3 athletes; no other Lakers are invented as absent.
    assert 42 not in rows.player_id.tolist()


def test_game_score_mismatch_is_not_reconciled_by_team_names(sources):
    root, event, _box = sources
    event["competitions"][0]["competitors"][0]["score"] = "110"
    with pytest.raises(ValueError, match="No unique score/team/date"):
        backfill("2025-26", root=root, source="espn")


def test_espn_unmapped_or_traded_player_is_not_given_someone_elses_id(sources):
    root, _event, box = sources
    box["boxscore"]["players"][0]["statistics"][0]["athletes"][1][
        "athlete"
    ]["displayName"] = "A Random Athlete"
    with pytest.raises(ValueError, match="Unresolved ESPN-to-NBA"):
        backfill("2025-26", root=root, source="espn")
    assert not (root / "raw/player_game_availability/2025-26_regular_season.csv").exists()


def test_nonboolean_dnp_is_untrusted(sources):
    root, _event, box = sources
    box["boxscore"]["players"][0]["statistics"][0]["athletes"][1]["didNotPlay"] = "true"
    with pytest.raises(ValueError, match="didNotPlay"):
        backfill("2025-26", root=root, source="espn")


def test_espn_dnp_flag_not_reinterpreted_as_injury(sources):
    _root, _event, box = sources
    box["boxscore"]["players"][0]["statistics"][0]["athletes"][1]["reason"] = "INJURY"
    raw, event = adapter.espn_boxscore_as_v3(
        game_id=22500001, game_date="2025-10-21", season="2025-26",
        season_type="Regular Season", home_team_id=1610612747,
        away_team_id=1610612744, data_root=_root,
    )
    result = normalize_boxscore_availability(
        raw, game_id=22500001, game_date="2025-10-21", season="2025-26",
        season_type="Regular Season",
        expected_team_ids={1610612747, 1610612744},
        source=f"espn_game_summary:{event}",
    )
    assert "INJURY" not in " ".join(result.source_comment)
    assert result.loc[result.player_id.eq(11), "participation_state"].iloc[0] == "did_not_play"


def test_espn_athlete_identity_conflict_fails_instead_of_guessing(sources):
    root, _event, box = sources
    players = pd.read_csv(root / "raw/player_game_stats/2025-26_regular_season.csv")
    players.loc[len(players)] = {
        "game_id": "0022500002", "team_id": 1610612747,
        "player_id": 90, "player_name": "Bronny James",
    }
    players.to_csv(root / "raw/player_game_stats/2025-26_regular_season.csv", index=False)
    with pytest.raises(ValueError, match="Unresolved ESPN-to-NBA"):
        backfill("2025-26", root=root, source="espn")
