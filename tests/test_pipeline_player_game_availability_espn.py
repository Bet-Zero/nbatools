"""ESPN source requires exact NBA game + identity matching, not name guesses."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_espn as adapter
from nbatools.commands.pipeline import pull_player_game_availability as importer
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
    pd.DataFrame(
        [
            {
                "game_id": "0022500001",
                "game_date": "2025-10-21",
                "season": "2025-26",
                "season_type": "Regular Season",
                "is_final": True,
                "home_team_id": 1610612747,
                "away_team_id": 1610612744,
            }
        ]
    ).to_csv(root / "raw/games/2025-26_regular_season.csv", index=False)
    pd.DataFrame(
        [
            {"game_id": "0022500001", "team_id": 1610612747, "team_abbr": "LAL", "pts": 109},
            {"game_id": "0022500001", "team_id": 1610612744, "team_abbr": "GSW", "pts": 119},
        ]
    ).to_csv(root / "raw/team_game_stats/2025-26_regular_season.csv", index=False)
    # A source-reported DNP need not appear in this game log; his verified
    # NBA ID is resolved from a different game with the SAME team/season.
    pd.DataFrame(
        [
            {
                "game_id": "0022500002",
                "team_id": 1610612747,
                "player_id": 10,
                "player_name": "LeBron James",
            },
            {
                "game_id": "0022500002",
                "team_id": 1610612747,
                "player_id": 11,
                "player_name": "Bronny James",
            },
            {
                "game_id": "0022500002",
                "team_id": 1610612744,
                "player_id": 20,
                "player_name": "Jimmy Butler III",
            },
        ]
    ).to_csv(root / "raw/player_game_stats/2025-26_regular_season.csv", index=False)

    event = {
        "id": "401809244",
        "competitions": [
            {
                "date": "2025-10-22T02:00:00Z",
                "status": {"type": {"completed": True}},
                "competitors": [
                    {"team": {"abbreviation": "LAL"}, "score": "109", "homeAway": "home"},
                    {"team": {"abbreviation": "GS"}, "score": "119", "homeAway": "away"},
                ],
            }
        ],
    }
    boxscore = {
        "header": deepcopy(event),
        "boxscore": {
            "players": [
                {
                    "team": {"abbreviation": "LAL"},
                    "statistics": [
                        {
                            "names": ["MIN", "PTS"],
                            "athletes": [
                                {
                                    "athlete": {"displayName": "LeBron James"},
                                    "didNotPlay": False,
                                    "stats": ["30", "18"],
                                },
                                {
                                    "athlete": {"displayName": "Bronny James"},
                                    "didNotPlay": True,
                                    "stats": ["--", "--"],
                                    "reason": "COACH'S DECISION",
                                },
                            ],
                        }
                    ],
                },
                {
                    "team": {"abbreviation": "GS"},
                    "statistics": [
                        {
                            "names": ["MIN", "PTS"],
                            "athletes": [
                                {
                                    "athlete": {"displayName": "Jimmy Butler"},
                                    "didNotPlay": False,
                                    "stats": ["35", "31"],
                                    "reason": "COACH'S DECISION",
                                },
                            ],
                        }
                    ],
                },
            ]
        },
    }
    monkeypatch.setattr(adapter, "_scoreboard", lambda _: {"events": [event]})
    monkeypatch.setattr(adapter, "_get_json", lambda _: boxscore)
    return root, event, boxscore


def test_espn_player_game_is_verified_and_source_reported(sources):
    root, _event, _box = sources
    rows = backfill("2025-26", root=root, source="espn")
    assert len(rows) == 3
    assert dict(zip(rows.player_id, rows.participation_state)) == {
        10: "played",
        11: "did_not_play",
        20: "played",
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
    box["boxscore"]["players"][0]["statistics"][0]["athletes"][1]["athlete"]["displayName"] = (
        "A Random Athlete"
    )
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
        game_id=22500001,
        game_date="2025-10-21",
        season="2025-26",
        season_type="Regular Season",
        home_team_id=1610612747,
        away_team_id=1610612744,
        data_root=_root,
    )
    result = normalize_boxscore_availability(
        raw,
        game_id=22500001,
        game_date="2025-10-21",
        season="2025-26",
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
        "game_id": "0022500002",
        "team_id": 1610612747,
        "player_id": 90,
        "player_name": "Bronny James",
    }
    players.to_csv(root / "raw/player_game_stats/2025-26_regular_season.csv", index=False)
    with pytest.raises(ValueError, match="Unresolved ESPN-to-NBA"):
        backfill("2025-26", root=root, source="espn")


@pytest.mark.parametrize("location", ["scoreboard", "summary"])
@pytest.mark.parametrize("defect", ["date", "naive_date", "home_away", "unfinished", "score"])
def test_source_game_identity_must_match(sources, location, defect):
    root, event, box = sources
    candidate = event if location == "scoreboard" else box["header"]
    competition = candidate["competitions"][0]
    if defect == "date":
        competition["date"] = "2000-01-01T02:00:00Z"
    elif defect == "naive_date":
        competition["date"] = "2025-10-21T22:00:00"
    elif defect == "home_away":
        competition["competitors"][0]["homeAway"] = "away"
    elif defect == "unfinished":
        competition["status"]["type"]["completed"] = False
    else:
        competition["competitors"][0]["score"] = "108"
    with pytest.raises(ValueError, match="match|summary identity"):
        backfill("2025-26", root=root, source="espn")
    assert not (root / "raw/player_game_availability/2025-26_regular_season.csv").exists()


def test_summary_event_id_must_match_scoreboard(sources):
    root, _, box = sources
    box["header"]["id"] = "999"
    with pytest.raises(ValueError, match="summary identity"):
        backfill("2025-26", root=root, source="espn")


def test_source_dnp_must_not_discard_positive_minutes(sources):
    root, _, box = sources
    box["boxscore"]["players"][0]["statistics"][0]["athletes"][1]["stats"][0] = "20"
    with pytest.raises(ValueError, match="Contradictory"):
        backfill("2025-26", root=root, source="espn")


@pytest.mark.parametrize("damage", ["truncated", "missing_receipt", "changed_minutes"])
def test_resume_reacquires_unverified_game(sources, monkeypatch, damage):
    root, _, box = sources
    backfill("2025-26", root=root, source="espn")
    target = root / "raw/player_game_availability/2025-26_regular_season.csv"
    rows = pd.read_csv(target)
    if damage == "truncated":
        rows.iloc[:1].to_csv(target, index=False)
    elif damage == "changed_minutes":
        rows.loc[rows.player_id.eq(10), "source_minutes"] = 99
        rows.to_csv(target, index=False)
    else:
        target.with_suffix(".imports.json").unlink()
    calls = []
    monkeypatch.setattr(adapter, "_get_json", lambda endpoint: calls.append(endpoint) or box)
    repaired = backfill("2025-26", root=root, source="espn")
    assert calls == ["summary?event=401809244"]
    assert len(repaired) == 3
    assert repaired.loc[repaired.player_id.eq(10), "source_minutes"].iloc[0] == 30
    calls.clear()
    backfill("2025-26", root=root, source="espn")
    assert not calls, "verified complete import should resume without refetch"


def test_source_switch_reacquires_instead_of_relabeling(sources, monkeypatch):
    root, _, _ = sources
    raw, _ = adapter.espn_boxscore_as_v3(
        game_id=22500001,
        game_date="2025-10-21",
        season="2025-26",
        season_type="Regular Season",
        home_team_id=1610612747,
        away_team_id=1610612744,
        data_root=root,
    )
    backfill("2025-26", root=root, source="espn")
    calls = []
    monkeypatch.setattr(
        importer, "fetch_starter_role_rows_for_game", lambda ident: calls.append(ident) or raw
    )
    changed = backfill("2025-26", root=root, source="stats")
    assert calls == [22500001]
    assert changed.source.eq(importer.SOURCE).all()
    assert len(changed) == 3


def test_failed_source_switch_preserves_last_good(sources, monkeypatch):
    root, _, _ = sources
    backfill("2025-26", root=root, source="espn")
    target = root / "raw/player_game_availability/2025-26_regular_season.csv"
    original = target.read_bytes()

    def fail(_):
        raise ConnectionError("source unavailable")

    monkeypatch.setattr(importer, "fetch_starter_role_rows_for_game", fail)
    with pytest.raises(ConnectionError):
        backfill("2025-26", root=root, source="stats")
    assert target.read_bytes() == original
