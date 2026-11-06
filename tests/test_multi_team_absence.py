"""Controlled transferred-player populations; these are not real NBA tenure facts."""

import hashlib
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
SEASON = "2025-26"
PID = 202710
CLUBS = {1610612748, 1610612747}


@pytest.fixture
def transferred(tmp_path, monkeypatch):
    root = tmp_path / "controlled-transfer"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    suffix = f"{SEASON}_regular_season.csv"
    teams = pd.read_csv(root / "data/raw/team_game_stats" / suffix)
    teams = teams.loc[teams.team_id.isin(CLUBS)].copy()
    boundary = "2025-12-01"
    eligible = (
        teams.loc[
            (teams.team_id.eq(1610612748) & teams.game_date.lt(boundary))
            | (teams.team_id.eq(1610612747) & teams.game_date.ge(boundary))
        ]
        .copy()
        .sort_values(["game_date", "game_id"])
    )
    # Deliberately include DNP on both clubs, including the first new-club game.
    missed = set(eligible.groupby("team_id").head(1).game_id.astype(int))
    path = root / "data/raw/player_game_stats" / suffix
    players = pd.read_csv(path)
    template = players.loc[players.player_id.eq(PID)].iloc[0]
    records = []
    for game in eligible.itertuples():
        row = template.to_dict()
        for key in (
            "game_id",
            "game_date",
            "team_id",
            "team_abbr",
            "team_name",
            "season",
            "season_type",
        ):
            if hasattr(game, key):
                row[key] = getattr(game, key)
        row["minutes"] = 30
        records.append(row)
    appearances = pd.DataFrame(records)
    pd.concat(
        [
            players.loc[~players.player_id.eq(PID)],
            appearances.loc[~appearances.game_id.isin(missed)],
        ]
    ).to_csv(path, index=False)
    observed = appearances.assign(
        participation_state=[
            "did_not_play" if gid in missed else "played" for gid in appearances.game_id
        ],
        coverage_scope="listed_player_rows_only",
        source="nba_official_finalbox:20251201_LALMIA",
        source_sha256="b" * 64,
    )
    path = root / "data/raw/player_game_availability" / suffix
    path.parent.mkdir(parents=True, exist_ok=True)
    observed.to_csv(path, index=False)
    original = b"controlled transfer fixture; not NBA evidence"
    digest = hashlib.sha256(original).hexdigest()
    path = root / "data/raw/player_team_membership_sources" / f"{digest}.source"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(original)
    common = dict(
        season=SEASON,
        player_id=PID,
        player_name="Jimmy Butler",
        membership_state="member",
        coverage_scope="explicit_dated_nba_membership",
        source="https://www.nba.com/controlled-transfer",
        source_sha256=digest,
    )
    intervals = pd.DataFrame(
        [
            dict(**common, team_id=1610612748, start_date="2025-10-01", end_date="2025-11-30"),
            dict(**common, team_id=1610612747, start_date=boundary, end_date="2026-12-31"),
        ]
    )
    path = root / "data/raw/player_team_membership" / f"{SEASON}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    intervals.to_csv(path, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield root, eligible, missed
    reset_data_source_cache()


def test_combined_natural_count_exact_ids_and_team_totals(transferred):
    _, eligible, missed = transferred
    result = execute_natural_query("How many games did Jimmy Butler miss in 2025-26?")
    assert result.result_status == "ok", result.metadata
    body = result.result.to_dict()
    assert body["sections"]["count"] == [{"count": 2}]
    assert {int(r["game_id"]) for r in body["sections"]["finder"]} == missed
    coverage = body["metadata"]["membership_coverage"]
    assert coverage["complete"] and coverage["missed_games"] == 2
    assert sum(r["eligible_games"] for r in coverage["by_team"]) == len(eligible)
    assert {r["team_abbr"]: r["did_not_play"] for r in coverage["by_team"]} == {"LAL": 1, "MIA": 1}
    assert "NBA" in result.metadata["answer_phrase"]
    assert "Miami Heat games" not in result.metadata["answer_phrase"]


@pytest.mark.parametrize("team", ["MIA", "LAL"])
def test_per_team_natural_and_structured_api(transferred, team):
    _, eligible, missed = transferred
    expected = missed & set(eligible.loc[eligible.team_abbr.eq(team)].game_id)
    direct = execute_structured_query(
        "game_finder", season=SEASON, team=team, membership_player="Jimmy Butler", limit=1000
    )
    assert direct.result_status == "ok", direct.metadata
    assert {int(r["game_id"]) for r in direct.result.to_dict()["sections"]["finder"]} == expected
    response = TestClient(app).post(
        "/query", json={"query": f"How many games did Jimmy Butler miss for the {team} in 2025-26?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result_status"] == "ok", body
    assert body["result"]["sections"]["count"] == [{"count": 1}]
    assert {int(r["game_id"]) for r in body["result"]["sections"]["finder"]} == expected


def test_unknown_member_game_withholds_total_and_retains_denominator(transferred):
    root, eligible, missed = transferred
    path = root / f"data/raw/player_game_availability/{SEASON}_regular_season.csv"
    rows = pd.read_csv(path)
    gid = min(missed)
    rows.loc[~rows.game_id.eq(gid)].to_csv(path, index=False)
    reset_data_source_cache()
    result = execute_natural_query("How many games did Jimmy Butler miss in 2025-26?")
    assert result.result_status == "no_result" and result.result_reason == "no_data", (
        result.metadata
    )
    coverage = result.result.metadata["membership_coverage"]
    assert coverage["missed_games"] is None and not coverage["complete"]
    assert any(
        r["game_id"] == gid and r["participation_state"] == "unknown" for r in coverage["games"]
    )
    assert sum(r["unknown"] for r in coverage["by_team"]) == 1
    assert sum(r["eligible_games"] for r in coverage["by_team"]) == len(eligible)


def test_unknown_transition_does_not_silently_drop_games(transferred):
    root, _, _ = transferred
    path = root / f"data/raw/player_team_membership/{SEASON}.csv"
    rows = pd.read_csv(path)
    rows.loc[rows.team_id.eq(1610612747), "start_date"] = "2025-12-11"
    rows.to_csv(path, index=False)
    # Remove exact-game rows in the uncertain period, including positive appearances.
    for family in ("player_game_availability", "player_game_stats"):
        path = root / f"data/raw/{family}/{SEASON}_regular_season.csv"
        rows = pd.read_csv(path)
        rows.loc[
            ~(rows.player_id.eq(PID) & rows.game_date.between("2025-12-01", "2025-12-10"))
        ].to_csv(path, index=False)
    reset_data_source_cache()
    result = execute_natural_query("How many games did Jimmy Butler miss in 2025-26?")
    assert result.result_status == "no_result", result.metadata
    coverage = result.result.metadata["membership_coverage"]
    assert coverage["unknown_membership_dates"] and coverage["missed_games"] is None


def test_filtered_selected_ids_and_arithmetic(transferred):
    _, eligible, missed = transferred
    expected = eligible.loc[
        eligible.game_id.isin(missed) & eligible.is_home.eq(1) & eligible.pts.ge(100)
    ]
    result = execute_structured_query(
        "game_finder",
        season=SEASON,
        membership_player="Jimmy Butler",
        home_only=True,
        stat="pts",
        min_value=100,
        limit=1000,
    )
    assert result.result_status == ("ok" if len(expected) else "no_result"), result.metadata
    if len(expected):
        assert {int(r["game_id"]) for r in result.result.to_dict()["sections"]["finder"]} == set(
            expected.game_id
        )


def test_natural_team_stat_condition_counts_absences_and_keeps_team_ownership(transferred):
    _, eligible, missed = transferred
    expected = set(eligible.loc[eligible.game_id.isin(missed) & eligible.pts.ge(100), "game_id"])
    result = execute_natural_query(
        "How many games did Jimmy Butler miss in 2025-26 when his team scored at least 100 points?"
    )
    assert result.result_status == "ok", result.metadata
    assert result.result.to_dict()["sections"]["count"] == [{"count": len(expected)}]
    assert {
        int(r["game_id"]) for r in result.result.to_dict()["sections"].get("finder", [])
    } == expected
    assert any(c["stat"] == "pts" and c["min_value"] == 100 for c in result.metadata["conditions"])
    assert "team points at least 100" in result.metadata["answer_phrase"]


@pytest.mark.parametrize("tail", ["when he scored at least 20 points", "with 80+ team points"])
def test_unread_stat_condition_never_counts_appearances(transferred, tail):
    result = execute_natural_query(f"How many games did Jimmy Butler miss in 2025-26 {tail}?")
    assert result.result_status != "ok", result.metadata
    assert "count" not in result.result.to_dict()["sections"]
