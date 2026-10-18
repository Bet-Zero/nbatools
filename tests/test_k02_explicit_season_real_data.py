"""The two explicit-season anchors in the finite K02 acceptance binding."""

import hashlib
import json
from functools import wraps
from pathlib import Path

import pytest

from nbatools.commands import team_record
from nbatools.data_source import data_path, data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "working/nba-tools-completion-program/k02-raw-oracle.json"
    ).read_text()
)
CASES = [c for c in ORACLE["cases"] if c["operation"] == "season"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_k02_explicit_season_summary(case, monkeypatch):
    for source, expected_hash in ORACLE["sources"].items():
        assert (
            hashlib.sha256(data_path("data/raw/" + source).read_bytes()).hexdigest()
            == expected_hash
        )
    teams = data_read_csv("data/raw/team_game_stats/2023-24_regular_season.csv")
    if case["kind"] == "team":
        raw = teams.loc[teams.team_abbr.eq("BOS")]
        route, identity, label = "team_record", {"team": "BOS"}, ("team_name", "Boston Celtics")
    else:
        players = data_read_csv("data/raw/player_game_stats/2023-24_regular_season.csv")
        raw = (
            players.loc[players.player_id.eq(201939)]
            .drop(columns="wl", errors="ignore")
            .merge(
                teams[["game_id", "team_id", "wl"]],
                on=["game_id", "team_id"],
                validate="many_to_one",
            )
        )
        route, identity, label = (
            "player_game_summary",
            {"player": "Stephen Curry"},
            ("player_name", "Stephen Curry"),
        )
    expected_keys = {tuple(row) for row in case["expected_keys"]}
    assert len(raw) == case["games"] == len(expected_keys)
    assert set(map(tuple, raw[case["keys"]].astype(int).values)) == expected_keys
    assert raw.season.eq("2023-24").all()
    assert raw.season_type.eq("Regular Season").all()
    for stat, value in case["sums"].items():
        assert raw[stat].sum() == value
    assert int(raw.wl.eq("W").sum()) == case["wins"]
    assert int(raw.wl.eq("L").sum()) == case["losses"]
    captured = []
    compute = team_record._compute_record

    @wraps(compute)
    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    with monkeypatch.context() as scope:
        scope.setattr(team_record, "_compute_record", capture)
        results = [
            execute_natural_query(case["query"]),
            execute_structured_query(route, season="2023-24", **identity),
        ]
    if case["kind"] == "team":
        assert len(captured) == 2
    for index, result in enumerate(results):
        assert result.result_status == "ok", result.result_reason
        assert result.route == route
        assert result.metadata["season"] == "2023-24"
        for key, value in identity.items():
            assert result.metadata[key] == value
        sections = result.result.to_dict()["sections"]
        actual = (
            captured[index].to_dict("records") if case["kind"] == "team" else sections["game_log"]
        )
        assert len(actual) == len(expected_keys)
        assert {tuple(int(row[k]) for k in case["keys"]) for row in actual} == expected_keys
        assert len(sections["summary"]) == 1
        summary = sections["summary"][0]
        assert summary[label[0]] == label[1]
        assert summary["season_start"] == summary["season_end"] == "2023-24"
        for field in ("games", "wins", "losses"):
            assert summary[field] == case[field]
        for stat, value in case["means"].items():
            assert summary[stat + "_avg"] == pytest.approx(value, abs=0.001)


def test_k02_fresh_booker_possessive_summary():
    """The independently frozen Give/possessive wording remains a desired positive."""
    baseline = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "working/nba-tools-completion-program/k02-language-baseline.json"
        ).read_text()
    )
    frozen = next(row for row in baseline["results"] if row["case"]["id"] == "h2")
    for source, expected_hash in ORACLE["sources"].items():
        assert (
            hashlib.sha256(data_path("data/raw/" + source).read_bytes()).hexdigest()
            == expected_hash
        )
    teams = data_read_csv("data/raw/team_game_stats/2023-24_regular_season.csv")
    players = data_read_csv("data/raw/player_game_stats/2023-24_regular_season.csv")
    raw = (
        players.loc[players.player_id.eq(1626164)]
        .drop(columns="wl", errors="ignore")
        .merge(
            teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
        )
    )
    truth = frozen["truth"]
    assert len(raw) == truth["games"] == 68
    assert int(raw.wl.eq("W").sum()) == truth["wins"] == 43
    assert int(raw.wl.eq("L").sum()) == truth["losses"] == 25
    for stat in ("pts", "reb", "ast"):
        assert raw[stat].mean() == pytest.approx(truth[stat + "_avg"])
    expected_keys = set(map(tuple, raw[["game_id", "team_id", "player_id"]].astype(int).values))
    response = execute_natural_query(frozen["case"]["query"])
    assert response.result_status == "ok", (response.result_reason, response.metadata)
    assert response.route == "player_game_summary"
    assert response.metadata["season"] == "2023-24"
    sections = response.result.to_dict()["sections"]
    rows = sections["game_log"]
    assert len(rows) == len(expected_keys) == 68
    assert {
        tuple(int(row[k]) for k in ("game_id", "team_id", "player_id")) for row in rows
    } == expected_keys
    assert len(sections["summary"]) == 1
    summary = sections["summary"][0]
    assert summary["player_name"] == "Devin Booker"
    assert summary["season_start"] == summary["season_end"] == "2023-24"
    for key, value in truth.items():
        assert summary[key] == pytest.approx(value, abs=0.001)
