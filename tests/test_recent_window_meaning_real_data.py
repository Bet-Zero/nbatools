"""Raw-row evidence for numbered recent samples; no frozen-comparison rerun."""

import pytest

from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize("kind", ["team", "player"])
@pytest.mark.parametrize("scope", ["window", "qualifying"])
def test_recent_sample_order_actual_rows(kind, scope):
    season = "2023-24"
    teams = data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv")
    if kind == "team":
        rows = teams.loc[teams.team_abbr.eq("DEN")].copy()
        route, n, minimum = "game_summary", 8, 114
        identity = {"team": "DEN"}
        query = (
            "How did Denver fare scoring at least 114 points within its final 8 games of 2023-24?"
            if scope == "window"
            else "Denver averages in its final 8 games scoring at least 114 points in 2023-24"
        )
    else:
        players = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
        rows = players.loc[players.player_id.eq(203999)].copy()
        rows = rows.drop(columns="wl", errors="ignore").merge(
            teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
        )
        route, n, minimum = "player_game_summary", 9, 29
        identity = {"player": "Nikola Jokić"}
        query = (
            "Average Nikola Jokic’s stats for games scoring at least 29 points within his final 9 appearances of 2023-24."
            if scope == "window"
            else "Nikola Jokic’s averages in his final 9 appearances scoring at least 29 points in 2023-24"
        )
    keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
    assert not rows.duplicated(keys).any()
    rows = rows.sort_values(["game_date", "game_id"], ascending=False)
    window = rows.head(n)
    within = window.loc[window.pts.ge(minimum)]
    qualifying = rows.loc[rows.pts.ge(minimum)].head(n)
    assert 0 < len(within) < n == len(qualifying)
    expected = within if scope == "window" else qualifying
    for response in [
        execute_natural_query(query),
        execute_structured_query(
            route,
            season=season,
            stat="pts",
            min_value=minimum,
            last_n=n,
            last_n_scope=scope,
            **identity,
        ),
    ]:
        assert response.result_status == "ok"
        assert response.route == route
        assert response.metadata["last_n"] == n
        assert response.metadata["last_n_scope"] == scope
        assert response.metadata["season"] == season
        assert response.metadata["min_value"] == minimum
        for key, value in identity.items():
            assert response.metadata[key] == value
        sections = response.result.to_dict()["sections"]
        actual = sections["game_log"]
        assert len(actual) == len(expected)
        assert {tuple(int(r[k]) for k in keys) for r in actual} == set(
            map(tuple, expected[keys].astype(int).to_numpy())
        )
        summary = sections["summary"][0]
        assert summary["games"] == len(expected)
        assert summary["wins"] == expected.wl.eq("W").sum()
        assert summary["losses"] == expected.wl.eq("L").sum()
        for stat in ["pts", "reb", "ast"]:
            assert summary[stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)
        labels = {b["label"]: b["value"] for b in response.metadata["applied_filters"]}
        assert labels["Sample selection"] == (
            f"Check conditions within the last {n} games"
            if scope == "window"
            else f"Select the last {n} games matching the conditions"
        )
