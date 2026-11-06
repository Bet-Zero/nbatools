"""Controlled date/transfer semantics, independent of real NBA tenure qualification."""

import hashlib
from datetime import timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands._dated_membership import (
    COLUMNS,
    calendar_date,
    load_membership,
    membership_on_date,
    validate_intervals,
)
from nbatools.commands._participation_observations import filter_absent, game_participation
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_qualified_participation_pair import SEASON
from tests.test_qualified_participation_pair import qualified_pair as _qualified_pair

qualified_pair = _qualified_pair

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
LAL, BOS, AD = 1610612747, 1610612738, 203076


def interval(start="2023-10-01", end="2023-10-31", team=LAL, state="member", **extra):
    return dict(
        season=SEASON,
        player_id=AD,
        player_name="Anthony Davis",
        team_id=team,
        start_date=start,
        end_date=end,
        membership_state=state,
        coverage_scope="explicit_dated_nba_membership",
        source="https://www.nba.com/controlled-test-evidence",
        source_sha256="a" * 64,
        **extra,
    )


def install(rows):
    from nbatools.data_source import data_path

    original = b'{"classification":"controlled fixture, NOT NBA tenure evidence"}'
    digest = hashlib.sha256(original).hexdigest()
    table = pd.DataFrame(rows, columns=COLUMNS)
    table["source_sha256"] = digest
    path = data_path(f"data/raw/player_team_membership/{SEASON}.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    source = data_path(f"data/raw/player_team_membership_sources/{digest}.source")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(original)
    reset_data_source_cache()
    return path, source


def test_inclusive_boundaries_gaps_and_explicit_negatives():
    rows = validate_intervals(pd.DataFrame([interval()]), SEASON)
    for day in ("2023-10-01", "2023-10-31"):
        own = membership_on_date(rows, AD, calendar_date(day), LAL)
        assert own.state == "member" and own.team_id == LAL
        assert membership_on_date(rows, AD, calendar_date(day), BOS).state == "not_member"
    for day in ("2023-09-30", "2023-11-01"):
        assert membership_on_date(rows, AD, calendar_date(day), LAL).state == "unknown"
    negative = validate_intervals(pd.DataFrame([interval(state="not_member")]), SEASON)
    day = calendar_date("2023-10-01")
    assert membership_on_date(negative, AD, day, LAL).state == "not_member"
    assert membership_on_date(negative, AD, day, BOS).state == "unknown"
    assert membership_on_date(negative, AD, day).team_id is None
    assert membership_on_date(negative, AD, day).state == "unknown"


@pytest.mark.parametrize("damage", ["overlap", "negative", "date", "scope", "hash", "identity"])
def test_unqualified_or_contradictory_intervals_reject(damage):
    rows = [interval()]
    if damage == "overlap":
        rows.append(interval(team=BOS, start="2023-10-31"))
    elif damage == "negative":
        rows.append(interval(state="not_member"))
    elif damage == "date":
        rows[0]["start_date"] = "2023-10-01T00:00:00"
    elif damage == "scope":
        rows[0]["coverage_scope"] = "roster_snapshot"
    elif damage == "hash":
        rows[0]["source_sha256"] = "not a hash"
    else:
        rows[0]["player_id"] = 1.5
    with pytest.raises(ValueError):
        validate_intervals(pd.DataFrame(rows), SEASON)


def test_membership_never_substitutes_for_participation_or_other_game(qualified_pair):
    day = calendar_date("2023-10-01")
    intervals = validate_intervals(pd.DataFrame([interval()]), SEASON)
    rows = qualified_pair["ledger"].copy()
    rows["game_date"] = "2023-10-01"
    state, membership = game_participation(rows, intervals, AD, 999999, LAL, day)
    assert state == "unknown" and membership.state == "member"
    state, membership = game_participation(rows, intervals, AD, 999999, BOS, day)
    assert state == "not_member" and membership.team_id == LAL
    with pytest.raises(ValueError, match="Contradictory"):
        membership_on_date(intervals, AD, day, exact_team_id=BOS)


def test_prejoining_is_excluded_but_unknown_member_game_blocks(qualified_pair):
    a, b, c, d = qualified_pair["ids"]
    teams = qualified_pair["teams"].sort_values("game_date")
    first, last = str(teams.game_date.iloc[0])[:10], str(teams.game_date.iloc[-1])[:10]
    # Explicitly stipulate another NBA club on the first game's date; a
    # separate controlled interval certifies LAL only after that date.
    install(
        [
            interval(first, first, team=BOS),
            interval((calendar_date(first) + timedelta(days=1)).isoformat(), last),
        ]
    )
    ledger = qualified_pair["ledger"]
    ledger.drop(ledger.index[ledger.game_id.eq(a) & ledger.player_id.eq(AD)], inplace=True)
    selected = filter_absent(teams, "Anthony Davis", [SEASON], "Regular Season")
    assert set(selected.game_id) == {c}
    result = execute_natural_query(f"Lakers record without Anthony Davis in {SEASON}")
    assert result.result_status == "ok", result.metadata
    summary = result.result.to_dict()["sections"]["summary"][0]
    expected = teams.loc[teams.game_id.eq(c)].iloc[0]
    assert summary["games"] == 1 and summary["pts_avg"] == expected.pts
    # Remove the actual DNP evidence while retaining interval membership.
    ledger.drop(ledger.index[ledger.game_id.eq(c) & ledger.player_id.eq(AD)], inplace=True)
    unknown = execute_natural_query(f"Lakers record without Anthony Davis in {SEASON}")
    assert unknown.result_status == "no_result" and unknown.result_reason != "no_match"


def test_structured_and_http_date_membership_and_exact_game(qualified_pair):
    game = qualified_pair["teams"].iloc[0]
    day = str(game.game_date)[:10]
    install([interval(day, day)])
    kwargs = dict(player_id=AD, date=day, season=SEASON)
    direct = execute_structured_query("player_membership", **kwargs)
    row = direct.result.to_dict()["sections"]["summary"][0]
    assert row["member_team_id"] == LAL and row["membership_state"] == "member"
    assert row["participation_state"] == "unknown"
    client = TestClient(app)
    response = client.post(
        "/structured-query",
        json=dict(
            route="player_membership",
            kwargs={
                **kwargs,
                "team_id": LAL,
                "game_id": int(game.game_id),
            },
        ),
    )
    assert response.status_code == 200, response.text
    row = response.json()["result"]["sections"]["summary"][0]
    assert row["membership_state"] == "member" and row["participation_state"] == "did_not_play"
    # An unqualified date is returned explicitly as unknown, with no club/DNP.
    kwargs["date"] = (calendar_date(day) - timedelta(days=1)).isoformat()
    unknown = execute_structured_query("player_membership", **kwargs)
    row = unknown.result.to_dict()["sections"]["summary"][0]
    assert row["membership_state"] == row["participation_state"] == "unknown"
    assert row["member_team_id"] is None


def test_source_bytes_and_generation_cache_boundaries(qualified_pair):
    path, source = install([interval()])
    assert len(load_membership([SEASON])) == 1
    source.write_bytes(b"changed bytes")
    reset_data_source_cache()
    from nbatools.dataframe_cache import FRAME_CACHE

    FRAME_CACHE.clear()  # Explicitly invalidate the deliberately mutated test version.
    with pytest.raises(ValueError, match="source hash"):
        load_membership([SEASON])
    assert path.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("player_id", True),
        ("player_id", 1.5),
        ("team_id", False),
        ("game_id", 0),
        ("game_id", 1.5),
        ("season", "2023-99"),
        ("date", "2023-02-30"),
        ("date", "20231001"),
        ("season_type", "Preseason"),
    ],
)
def test_bad_structured_identity_and_calendar_never_answer(qualified_pair, field, value):
    kwargs = dict(player_id=AD, date="2023-10-01", season=SEASON)
    kwargs[field] = value
    result = execute_structured_query("player_membership", **kwargs)
    assert result.result_status != "ok" and not result.result.to_dict()["sections"]
