"""S5 independent raw-row oracle for summary sample selection."""

from functools import wraps

import pytest

from nbatools.commands import team_record
from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query


def check_sample_order(kind, operation, monkeypatch):
    season = "2023-24"
    teams = data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv")
    assert not teams.duplicated(["game_id", "team_id"]).any()
    if kind == "team":
        raw = teams.loc[teams.team_abbr.eq("BOS")].copy()
        subject, identity, route, floor, opponent = (
            "Celtics record",
            {"team": "BOS"},
            "team_record",
            110,
            "NYK",
        )
    else:
        players = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
        raw = players.loc[players.player_id.eq(201939)].copy()
        if "wl" in raw.columns:
            raw = raw.drop(columns="wl")
        raw = raw.merge(
            teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
        )
        subject, identity, route, floor, opponent = (
            "Stephen Curry averages",
            {"player": "Stephen Curry"},
            "player_game_summary",
            30,
            "LAL",
        )
    raw = raw.sort_values(["game_date", "game_id"], ascending=False)
    assert not raw.empty and not raw.duplicated(["game_id", "team_id"]).any()
    kwargs = dict(season=season, **identity)
    if operation == "date":
        start, end = (
            ("2023-11-01", "2024-03-01") if kind == "team" else ("2024-01-01", "2024-03-31")
        )
        dates = raw.game_date.astype(str).str[:10].between(start, end)
        opponents = raw.opponent_team_abbr.eq(opponent)
        expected = raw.loc[dates & opponents]
        assert 0 < len(expected) < int(dates.sum())
        assert len(expected) < int(opponents.sum())
        query = f"{subject} vs {opponent} from {start} to {end}"
        kwargs.update(opponent=opponent, start_date=start, end_date=end)
    else:
        threshold = raw.pts.ge(floor)
        window = raw.head(10)
        within = window.loc[window.pts.ge(floor)]
        qualifying = raw.loc[threshold].head(10)
        assert 0 < len(within) < 10 == len(qualifying)
        assert set(within.game_id) != set(qualifying.game_id)
        expected = within if operation == "window" else qualifying
        owner = "their" if kind == "team" else "his"
        query = (
            f"{subject} scoring at least {floor} points in {owner} last 10 games in {season}"
            if operation == "window"
            else f"{subject} in {owner} last 10 games scoring at least {floor} points in {season}"
        )
        kwargs.update(stat="pts", min_value=floor, last_n=10, last_n_scope=operation)
    captured = []
    compute = team_record._compute_record

    @wraps(compute)
    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    with monkeypatch.context() as scope:
        scope.setattr(team_record, "_compute_record", capture)
        results = [execute_natural_query(query), execute_structured_query(route, **kwargs)]
    if kind == "team":
        assert len(captured) == 2
    keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
    for index, result in enumerate(results):
        assert result.result_status == "ok", (query, result.metadata)
        assert result.route == route
        sections = result.result.to_dict()["sections"]
        rows = captured[index].to_dict("records") if kind == "team" else sections["game_log"]
        assert {tuple(int(r[k]) for k in keys) for r in rows} == set(
            map(tuple, expected[keys].astype(int).to_numpy())
        )
        row = sections["summary"][0]
        assert row["games"] == len(expected)
        assert row["wins"] == expected.wl.eq("W").sum()
        assert row["losses"] == expected.wl.eq("L").sum()
        for stat in ["pts", "reb", "ast"]:
            assert row[stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)
        labels = {r["label"]: r["value"] for r in result.metadata["applied_filters"]}
        if operation == "date":
            assert labels["Opponent"] == opponent
            assert labels["Date range"] == f"{start} – {end}"
        else:
            assert labels["Last N games"] == "10"
            selection = (
                "Check conditions within the last 10 games"
                if operation == "window"
                else "Select the last 10 games matching the conditions"
            )
            assert labels["Sample selection"] == selection
    return expected
