"""Retained source replay and discriminating future-versus-final coverage controls."""

import copy
import hashlib
import json
import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline import pull_games, pull_schedule, pull_team_game_stats
from nbatools.commands.pipeline.official_schedule import (
    normalize_official_schedule,
    official_final_rows,
    validate_schedule_game_coverage,
    validate_schedule_team_coverage,
)
from nbatools.commands.validation_control import DatasetSpec, build_slice_manifest

EVIDENCE = Path(__file__).resolve().parents[1] / (
    "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
)


@lru_cache(1)
def original():
    with zipfile.ZipFile(EVIDENCE / "schedule-capture.zip") as archive:
        raw = archive.read("acquired_data/rollover-2026-27-schedule/scheduleleaguev2-2027.json")
    assert hashlib.sha256(raw).hexdigest() == (
        "edf45e0c7f06ba0f5c842a333d054b617f23244443514fb4aa9771a6b32b75cf"
    )
    return raw


def specimen():
    source = json.loads(original())
    selected = []
    predicates = [
        lambda g: g["gameId"].startswith("00226") and g["gameStatus"] == 3,
        lambda g: (
            g["gameId"].startswith("00226") and g["gameStatus"] == 1 and g["homeTeam"]["teamId"] > 0
        ),
        lambda g: g["gameId"].startswith("00226") and not g["homeTeam"]["teamId"],
        lambda g: g["gameId"].startswith("00226") and g["isNeutral"],
        lambda g: g["gameId"].startswith("00126"),
    ]
    for predicate in predicates:
        day, game = next(
            (d, g)
            for d in source["leagueSchedule"]["gameDates"]
            for g in d["games"]
            if predicate(g)
        )
        selected.append(dict(gameDate=day["gameDate"], games=[copy.deepcopy(game)]))
    return dict(leagueSchedule=dict(seasonYear="2026-27", leagueId="00", gameDates=selected))


def normalized(doc=None):
    return normalize_official_schedule(json.dumps(doc or specimen()).encode(), "2026-27")


def completed(schedule):
    return official_final_rows(schedule).assign(is_final=1)


def test_retained_whole_body_preserves_future_tbd_and_neutral_facts():
    schedule = normalize_official_schedule(original(), "2026-27")
    assert len(schedule) == 1206
    assert schedule.status.value_counts().to_dict() == {"Scheduled": 1125, "Final": 81}
    assert len(official_final_rows(schedule)) == 81
    assert len(schedule.loc[schedule.team_a_id.isna()]) == 6
    assert schedule.neutral_site.sum() == 3
    assert schedule.loc[schedule.neutral_site.eq(1), "home_away_designation_trusted"].eq(0).all()
    assert schedule.loc[schedule.neutral_site.eq(1), "home_team_id"].isna().all()
    assert schedule.game_datetime.str.endswith("+00:00").all()
    assert set(schedule.schedule_source_sha256) == {hashlib.sha256(original()).hexdigest()}


def test_future_schedule_accepts_exact_completed_catalog_without_future_stats():
    schedule = normalized()
    validate_schedule_game_coverage(schedule, completed(schedule))
    assert len(schedule) == 4 and len(completed(schedule)) == 1


@pytest.mark.parametrize(
    "damage",
    ["missing_final", "future_as_final", "unplayed", "wrong_date", "wrong_side", "duplicate_id"],
)
def test_completed_catalog_cannot_hide_or_invent_games(damage):
    schedule = normalized()
    games = completed(schedule)
    if damage == "missing_final":
        games = games.iloc[:0]
    elif damage == "future_as_final":
        games = pd.concat([games, schedule.iloc[1:2].assign(is_final=1)])
    elif damage == "unplayed":
        games = games.assign(is_final=0)
    elif damage == "wrong_date":
        games = games.assign(game_date="2026-10-01")
    elif damage == "wrong_side":
        games = games.assign(home_team_id=games.away_team_id, away_team_id=games.home_team_id)
    else:
        duplicate = games.copy()
        duplicate["game_id"] = duplicate.game_id.astype(str).str.zfill(10)
        games = pd.concat([games, duplicate])
    with pytest.raises(ValueError):
        validate_schedule_game_coverage(schedule, games)


def test_unknown_source_tags_do_not_waive_legacy_exact_equality():
    legacy = pd.DataFrame(dict(game_id=[1, 2]))
    with pytest.raises(ValueError, match="Mismatch"):
        validate_schedule_game_coverage(legacy, pd.DataFrame(dict(game_id=[1])))
    with pytest.raises(ValueError):
        official_final_rows(legacy.assign(schedule_source="unreviewed"))


@pytest.mark.parametrize(
    "damage",
    [
        "league",
        "year",
        "duplicate",
        "clock",
        "code",
        "status",
        "postponed",
        "neutral",
        "final_tbd",
        "negative_score",
        "wrong_season_date",
    ],
)
def test_source_contradictions_cannot_become_canonical(damage):
    doc = specimen()
    game = doc["leagueSchedule"]["gameDates"][0]["games"][0]
    if damage == "league":
        doc["leagueSchedule"]["leagueId"] = "10"
    elif damage == "year":
        doc["leagueSchedule"]["seasonYear"] = "2025-26"
    elif damage == "duplicate":
        doc["leagueSchedule"]["gameDates"].append(
            copy.deepcopy(doc["leagueSchedule"]["gameDates"][0])
        )
    elif damage == "clock":
        game["gameDateTimeUTC"] = game["gameDateTimeEst"]
    elif damage == "code":
        game["gameCode"] = game["gameCode"][:-6] + "BOSBOS"
    elif damage == "status":
        game["gameStatus"] = True
    elif damage == "postponed":
        game["postponedStatus"] = "unqualified"
    elif damage == "neutral":
        game["isNeutral"] = "false"
    elif damage == "final_tbd":
        game["homeTeam"]["teamId"] = 0
    elif damage == "negative_score":
        game["homeTeam"]["score"] = -1
    else:
        game["gameDateEst"] = "2026-01-20T00:00:00Z"
        game["gameDateTimeEst"] = "2026-01-20T15:00:00Z"
        game["gameDateTimeUTC"] = "2026-01-20T20:00:00Z"
        game["gameCode"] = "20260120/BOSDET"
        doc["leagueSchedule"]["gameDates"][0]["gameDate"] = "01/20/2026 00:00:00"
    with pytest.raises(ValueError):
        normalized(doc)


def test_independent_finder_rows_reconcile_all_retained_schedule_finals(tmp_path, monkeypatch):
    with zipfile.ZipFile(EVIDENCE / "stats-sources.zip") as archive:
        capture = json.loads(archive.read("stats-capture.json"))
        raw = archive.read("stats-sources/finder.json")
    assert hashlib.sha256(raw).hexdigest() == capture["source_files"]["finder"]["sha256"]
    table = json.loads(raw)["resultSets"][0]
    finder = pd.DataFrame(table["rowSet"], columns=table["headers"])
    assert len(finder) == 162 and set(finder.SEASON_ID.astype(str)) == {"22026"}
    monkeypatch.chdir(tmp_path)
    pull_games.run("2026-27", "Regular Season", raw_frame=finder)
    pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=finder)
    pull_schedule.run("2026-27", "Regular Season", official_original=original())
    schedule = pd.read_csv("data/raw/schedule/2026-27_regular_season.csv")
    games = pd.read_csv("data/raw/games/2026-27_regular_season.csv")
    teams = pd.read_csv("data/raw/team_game_stats/2026-27_regular_season.csv")
    validate_schedule_game_coverage(schedule, games)
    validate_schedule_team_coverage(schedule, teams)
    assert (len(schedule), len(games), len(teams), int(teams.pts.sum())) == (1206, 81, 162, 18464)
    specs = tuple(
        DatasetSpec(name, "raw", "test source keys", keys, "test")
        for name, keys in (
            ("games", ("game_id",)),
            ("schedule", ("game_id",)),
            ("team_game_stats", ("game_id", "team_id")),
        )
    )
    # A deliberately narrow three-dataset test is not a publishable slice receipt.
    manifest = build_slice_manifest(
        "2026-27", "Regular Season", data_root=Path("data"), specs=specs
    )
    assert manifest["validation_state"] == "passed"
    coverage = {r["name"]: r["coverage"] for r in manifest["datasets"]}
    assert coverage["schedule"]["scope"] == "explicit_official_final_games"
    assert coverage["schedule"]["future_or_in_progress_games"] == 1125
    assert coverage["schedule"]["expected_keys"] == coverage["schedule"]["observed_keys"] == 81
    for kind in ("omitted_both_teams", "score", "extra_future"):
        damaged = teams.copy()
        if kind == "omitted_both_teams":
            damaged = damaged.loc[damaged.game_id.ne(damaged.game_id.iloc[0])]
        elif kind == "score":
            damaged.loc[0, "pts"] += 1
        else:
            damaged.loc[0, "game_id"] = schedule.loc[schedule.status.ne("Final"), "game_id"].iloc[0]
        with pytest.raises(ValueError):
            validate_schedule_team_coverage(schedule, damaged)
