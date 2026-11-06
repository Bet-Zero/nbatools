"""Independent end-to-end fixture controls: Miami/Butler, no NBA-fact claim."""

import hashlib
import json
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
TEAM = 1610612748
PLAYER = 202710


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / "controlled-miami"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    suffix = SEASON + "_regular_season.csv"
    path = root / "data/raw/player_game_stats" / suffix
    players = pd.read_csv(path)
    own = players[players.player_id.eq(PLAYER)].sort_values("game_date")
    assert len(own) > 20
    dnp = own[own.game_id.isin([386, 389, 395])].copy()
    assert len(dnp) == 3
    prejoin = own[own.game_id.eq(365)].copy()
    availability = dnp.assign(
        participation_state="did_not_play",
        coverage_scope="listed_player_rows_only",
        source="nba_official_finalbox:20251210_LALMIA",
        source_sha256="c" * 64,
    )
    target = root / "data/raw/player_game_availability" / suffix
    target.parent.mkdir(parents=True, exist_ok=True)
    availability.to_csv(target, index=False)
    players[~(players.player_id.eq(PLAYER) & players.game_id.isin([365, 386, 389, 395]))].to_csv(
        path, index=False
    )
    raw = json.dumps(
        {
            "classification": "controlled fixture, no NBA evidence",
            "not_member": ["2025-10-29", "2025-10-29"],
            "member": ["2025-11-08", own.iloc[-1].game_date],
        }
    ).encode()
    digest = hashlib.sha256(raw).hexdigest()
    original = root / "data/raw/player_team_membership_sources" / f"{digest}.source"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(raw)
    common = dict(
        season=SEASON,
        player_id=PLAYER,
        player_name="Jimmy Butler",
        team_id=TEAM,
        coverage_scope="explicit_dated_nba_membership",
        source="https://www.nba.com/controlled-independent-review-fixture",
        source_sha256=digest,
    )
    intervals = pd.DataFrame(
        [
            dict(
                **common,
                start_date="2025-10-29",
                end_date="2025-10-29",
                membership_state="not_member",
            ),
            dict(
                **common,
                start_date="2025-11-08",
                end_date=own.iloc[-1].game_date,
                membership_state="member",
            ),
        ]
    )
    target = root / "data/raw/player_team_membership" / f"{SEASON}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    intervals.to_csv(target, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    try:
        yield root, dnp, prejoin, own
    finally:
        reset_data_source_cache()


def ids(result, section="finder"):
    assert result.result_status == "ok", result.metadata
    return {int(r["game_id"]) for r in result.to_dict()["sections"][section]}


def test_natural_absence_excludes_verified_prejoin_game_and_preserves_home_scope(source):
    result = execute_natural_query("How many home games did Jimmy Butler miss in 2025-26?")
    assert ids(result) == {386, 389}
    assert result.to_dict()["sections"]["count"] == [{"count": 2}]


def test_away_scope_and_exact_date_preserved(source):
    result = execute_natural_query("How many away games did Jimmy Butler miss in 2025-26?")
    assert ids(result) == {395}
    result = execute_natural_query("Which games did Jimmy Butler miss on 2025-12-10 in 2025-26?")
    assert ids(result) == {386}


def test_natural_team_record_keeps_original_team_and_opponent(source):
    result = execute_natural_query("Lakers record vs Miami without Jimmy Butler in 2025-26")
    assert ids(result, "game_log") == {386, 395}
    raw = pd.read_csv(source[0] / "data/raw/team_game_stats/2025-26_regular_season.csv")
    chosen = raw[raw.team_abbr.eq("LAL") & raw.game_id.isin([386, 395])]
    actual = result.to_dict()["sections"]["summary"][0]
    assert actual["games"] == 2
    wins = int(chosen.win.sum()) if "win" in chosen else int(chosen.wl.eq("W").sum())
    assert actual["wins"] == wins
    assert actual["pts_avg"] == pytest.approx(chosen.pts.mean(), abs=0.001)


@pytest.mark.api
def test_http_natural_and_structured_membership_are_real_consumers(source):
    client = TestClient(app)
    response = client.post(
        "/query", json={"query": "Which games did Jimmy Butler miss in 2025-26?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result_status"] == "ok"
    assert {int(r["game_id"]) for r in body["result"]["sections"]["finder"]} == {386, 389, 395}
    for day, gid, wanted_member, wanted_part in [
        ("2025-10-29", 365, "not_member", "not_member"),
        ("2025-12-10", 386, "member", "did_not_play"),
        ("2025-11-08", 370, "member", "played"),
    ]:
        response = client.post(
            "/structured-query",
            json={
                "route": "player_membership",
                "kwargs": dict(
                    player_id=PLAYER, team_id=TEAM, date=day, season=SEASON, game_id=gid
                ),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_status"] == "ok", body
        row = body["result"]["sections"]["summary"][0]
        assert (row["membership_state"], row["participation_state"]) == (wanted_member, wanted_part)


def test_date_only_does_not_promote_game_row_to_tenure(source):
    result = execute_structured_query(
        "player_membership", player_id=PLAYER, team_id=TEAM, date="2025-10-30", season=SEASON
    )
    row = result.to_dict()["sections"]["summary"][0]
    assert row["membership_state"] == "unknown" and row["participation_state"] == "unknown"


def test_missing_member_participation_stays_unknown_and_blocks_missed_count(source):
    root, _, _, _ = source
    path = root / "data/raw/player_game_availability/2025-26_regular_season.csv"
    frame = pd.read_csv(path)
    frame[~frame.game_id.eq(389)].to_csv(path, index=False)
    reset_data_source_cache()
    result = execute_structured_query(
        "player_membership",
        player_id=PLAYER,
        team_id=TEAM,
        date="2025-12-16",
        season=SEASON,
        game_id=389,
    )
    row = result.to_dict()["sections"]["summary"][0]
    assert (row["membership_state"], row["participation_state"]) == ("member", "unknown")
    result = execute_natural_query("Which games did Jimmy Butler miss in 2025-26?")
    assert result.result_status == "no_result" and result.result_reason != "no_match"


def test_player_statistical_and_teammate_filters_keep_subject(source):
    result = execute_structured_query(
        "player_game_summary",
        season=SEASON,
        player="Bam Adebayo",
        without_player="Jimmy Butler",
        with_player="Tyler Herro",
        home_only=True,
        stat="pts",
        min_value=24,
        start_date="2025-12-01",
        end_date="2025-12-31",
    )
    assert ids(result, "game_log") == {389}
    row = result.to_dict()["sections"]["summary"][0]
    assert row["games"] == 1 and row["pts_avg"] == 27


def test_unfamiliar_natural_player_summary_keeps_same_team_sample(source):
    result = execute_natural_query(
        "Bam Adebayo average points without Jimmy Butler in home games in 2025-26"
    )
    assert ids(result, "game_log") == {386, 389}
    row = result.to_dict()["sections"]["summary"][0]
    assert row["games"] == 2 and row["pts_avg"] == 24
