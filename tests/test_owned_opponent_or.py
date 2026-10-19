"""An OR branch names a condition owner without changing the game subject."""

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
RAW = Path(__file__).resolve().parents[1] / "qa/fixtures/query_engine_sample/data/raw"
QUERY = "Lakers games against Celtics and Wizards when Celtics score at least 110 or Wizards score at least 125 in 2023-24"


@pytest.mark.parametrize(
    "query", [QUERY, QUERY.replace("Celtics", "BOS").replace("Wizards", "WAS")]
)
def test_named_owners_bind_to_each_executed_branch(query):
    teams = pd.read_csv(RAW / "team_game_stats/2023-24_regular_season.csv")
    own = teams.loc[teams.team_abbr.eq("LAL")]
    # Read the other team's same-game rows, independently of engine conditions.
    other = teams.set_index(["game_id", "team_id"])
    expected = []
    for row in own.itertuples():
        if row.opponent_team_abbr not in {"BOS", "WAS"}:
            continue
        score = other.loc[(row.game_id, row.opponent_team_id)].pts
        if score >= {"BOS": 110, "WAS": 125}[row.opponent_team_abbr]:
            expected.append(int(row.game_id))
    assert expected
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    rows = result.result.to_dict()["sections"]["finder"]
    assert sorted(int(row["game_id"]) for row in rows) == sorted(expected)
    assert all(row["team_abbr"] == "LAL" for row in rows)
    meta = result.metadata
    assert meta["team"] == "LAL" and meta["opponents"] == ["BOS", "WAS"]
    assert meta["stat"] is meta["min_value"] is meta["max_value"] is None
    assert not meta["conditions"] and not meta["threshold_conditions"]
    branches = meta["boolean_filter_branches"]
    assert [b["conditions"] for b in branches] == [
        [{"stat": "opponent_pts", "min_value": 110, "max_value": None, "opponent_team": "BOS"}],
        [{"stat": "opponent_pts", "min_value": 125, "max_value": None, "opponent_team": "WAS"}],
    ]
    assert all(b["scope"]["team"] == "LAL" for b in branches)
    assert next(f["value"] for f in meta["applied_filters"] if f["kind"] == "boolean") == (
        "(Opponent: BOS, WAS; 110+ BOS OPP PTS) OR (Opponent: BOS, WAS; 125+ WAS OPP PTS)"
    )


@pytest.mark.parametrize(
    "query",
    [
        QUERY.replace("Wizards score at least 125", "Blorg score at least 125"),
        QUERY.replace("Wizards score at least 125", "Knicks score at least 125"),
        QUERY.replace("Wizards score at least 125", "Wizards games with at least 125 points"),
        QUERY.replace("Wizards score at least 125", "Lakers score at least 125"),
        QUERY.replace(
            "Wizards score at least 125", "Wizards score at least 125 and Blorg score at least 20"
        ),
        QUERY.replace("Lakers games", "Lakers last 3 games"),
        QUERY.replace("Lakers games", "Lakers record"),
        QUERY.replace("Lakers games", "LeBron James games"),
    ],
)
def test_unfinished_extra_scope_never_becomes_a_partial_union(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata
    assert result.result_reason in {"unsupported", "filter_not_supported"}


def test_unavailable_branch_is_not_silently_omitted(monkeypatch):
    from nbatools.commands import _natural_query_execution as execution
    from nbatools.commands.structured_results import NoResult

    build = execution._execute_build_result
    calls = []

    def unavailable_second(*args, **kwargs):
        calls.append(args)
        if len(calls) == 2:
            return NoResult(query_class="finder", result_reason="data_unavailable")
        return build(*args, **kwargs)

    monkeypatch.setattr(execution, "_execute_build_result", unavailable_second)
    result = execute_natural_query(QUERY)
    assert len(calls) == 2
    assert result.result_status == "no_result" and result.result_reason == "data_unavailable"
