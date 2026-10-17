"""Read-only S1/S2/S3 deployed checks against one pinned raw generation."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
BASE = "https://nbatools.vercel.app"


def _retain(name, payload):
    destination = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
    if destination:
        target = Path(destination) / "deployed" / (name + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2))


def _ready(name):
    with urllib.request.urlopen(BASE + "/readiness", timeout=30) as response:
        value = json.load(response)
    _retain(name, value)
    assert value["ready"] is True and value["immutable_generation"] is True
    assert value["active_generation"] == os.environ["NBATOOLS_DATA_GENERATION"]
    return value


def _query(query, name):
    request = urllib.request.Request(
        BASE + "/query",
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    _retain(name, payload)
    assert payload["ok"] is True and payload["result_status"] == "ok", payload
    return payload


@pytest.mark.parametrize("kind", ["team", "player"])
def test_deployed_nonadjacent_seasons_keep_opponent_and_filter(kind):
    before = _ready("before-" + kind + "-" + str(os.getpid()))
    expected = {}
    for season in ["2023-24", "2025-26"]:
        raw = data_read_csv(f"data/raw/{kind}_game_stats/{season}_regular_season.csv")
        keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
        assert not raw.duplicated(keys).any() and not raw.empty
        if kind == "team":
            selected = raw.loc[
                raw.team_abbr.eq("BOS") & raw.opponent_team_abbr.eq("NYK") & raw.is_home.eq(True)
            ]
        else:
            selected = raw.loc[
                raw.player_id.eq(201939) & raw.opponent_team_abbr.eq("POR") & raw.pts.ge(25)
            ]
        assert not selected.empty
        expected[season] = selected
    query = (
        "Celtics home record vs Knicks in 2023-24 and 2025-26"
        if kind == "team"
        else "Stephen Curry averages with at least 25 points against Portland in 2023-24 and 2025-26"
    )
    payload = _query(query, "season-split-" + kind)
    assert payload["route"] == kind + "_split_summary"
    metadata = payload["metadata"]
    assert metadata["team" if kind == "team" else "player"] == (
        "BOS" if kind == "team" else "Stephen Curry"
    )
    assert metadata["opponent"] == ("NYK" if kind == "team" else "POR")
    assert metadata["season_list"] == list(expected)
    labels = {r["label"]: r["value"] for r in metadata["applied_filters"]}
    assert labels["Opponent"] == metadata["opponent"]
    assert labels["Seasons"] == ", ".join(expected)
    assert labels["Location" if kind == "team" else "pts min"] == (
        "Home" if kind == "team" else "25.0"
    )
    sections = payload["result"]["sections"]
    actual = sections["split_comparison"]
    assert [row["bucket"] for row in actual] == list(expected)
    assert sections["summary"][0]["games_total"] == sum(map(len, expected.values()))
    for row in actual:
        raw = expected[row["bucket"]]
        assert row["games"] == len(raw)
        assert row["pts_avg"] == pytest.approx(raw.pts.mean(), abs=0.001)
        if kind == "player":
            assert row["pts_sum"] == raw.pts.sum()
            for stat in ["reb", "ast"]:
                assert row[stat + "_avg"] == pytest.approx(raw[stat].mean(), abs=0.001)
        if kind == "team":
            assert row["wins"] == raw.wl.eq("W").sum()
            assert row["losses"] == raw.wl.eq("L").sum()
    assert _ready("after-split-" + kind)["active_generation"] == before["active_generation"]


@pytest.mark.parametrize("kind", ["team", "player"])
def test_deployed_own_and_opponent_scoring_have_distinct_owners(kind):
    before = _ready("before-ownership-" + kind)
    season = "2023-24"
    teams = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
    assert not teams.duplicated(["game_id", "team_id"]).any()
    lookup = teams.set_index(["game_id", "team_id"])
    if kind == "team":
        raw = teams.loc[teams.team_abbr.eq("LAL")].copy()
        floor = 110
        question = "Lakers home record when they score at least 110 points and allow under 110 points in 2023-24"
    else:
        players = data_read_csv(f"data/raw/player_game_stats/{season}_regular_season.csv")
        raw = players.loc[players.player_id.eq(2544)].copy()
        floor = 25
        question = "LeBron James averages at home with at least 25 points when opponents score under 110 points in 2023-24"
    selected = []
    outcomes = []
    for row in raw.itertuples():
        own = lookup.loc[(row.game_id, row.team_id)]
        other = lookup.loc[(row.game_id, own.opponent_team_id)]
        assert other.opponent_team_id == row.team_id
        if own.is_home and row.pts >= floor and other.pts < 110:
            selected.append(row.Index)
            outcomes.append(own.wl)
    expected = raw.loc[selected]
    assert len(expected) > 0
    payload = _query(question, "subject-ownership-" + kind)
    assert payload["route"] == ("team_record" if kind == "team" else "player_game_summary")
    metadata = payload["metadata"]
    assert metadata["team" if kind == "team" else "player"] == (
        "LAL" if kind == "team" else "LeBron James"
    )
    assert metadata["season"] == season
    labels = {r["label"]: r["value"] for r in metadata["applied_filters"]}
    assert labels["Location"] == "Home"
    assert labels["pts min"] == f"{floor:.1f}"
    assert labels["OPP PTS max"] == "110 (exclusive)"
    sections = payload["result"]["sections"]
    row = sections["summary"][0]
    assert row["games"] == len(expected)
    assert row["wins"] == outcomes.count("W") and row["losses"] == outcomes.count("L")
    assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
    if kind == "player":
        keys = ["game_id", "team_id", "player_id"]
        assert {tuple(int(r[k]) for k in keys) for r in sections["game_log"]} == set(
            map(tuple, expected[keys].astype(int).to_numpy())
        )
        assert row["pts_sum"] == expected.pts.sum()
    assert _ready("after-ownership-" + kind)["active_generation"] == before["active_generation"]
