"""Questions that name two or more seasons answer each one.

"Lakers record this season vs last season" answered 2024-25 alone, "Lakers
record 2025-26 vs 2024-25" the current season alone, and "Lakers record in
2016 and 2020" the current season. Named seasons are now a season split:
one row per season, the seasons between them left out. Routes with no
season split (comparisons, leaderboards) refuse instead of answering one.

Expected values are counted with pandas from the fixture's raw rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

_RAW = Path(__file__).resolve().parents[1] / "qa/fixtures/query_engine_sample/data/raw"


def _rows(kind: str, season: str) -> pd.DataFrame:
    return pd.read_csv(_RAW / f"{kind}/{season}_regular_season.csv")


def _split(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.route in ("team_split_summary", "player_split_summary")
    sections = result.result.to_dict()["sections"]
    return result, {row["bucket"]: row for row in sections["split_comparison"]}


@pytest.mark.parametrize(
    ("query", "seasons"),
    [
        ("Lakers record this season vs last season", ["2024-25", "2025-26"]),
        ("Lakers record this season compared to last season", ["2024-25", "2025-26"]),
        ("Lakers record last season vs this season", ["2024-25", "2025-26"]),
        ("Lakers record 2025-26 vs 2024-25", ["2024-25", "2025-26"]),
        ("Lakers record in 2023-24 and 2025-26", ["2023-24", "2025-26"]),
        ("Lakers record in 2024 vs 2026", ["2023-24", "2025-26"]),
        ("Lakers record in 2023-24, 2024-25 and 2025-26", ["2023-24", "2024-25", "2025-26"]),
    ],
)
def test_team_record_per_named_season(query, seasons):
    result, rows = _split(query)
    assert sorted(rows) == seasons
    for season in seasons:
        team = _rows("team_game_stats", season)
        team = team[team["team_abbr"] == "LAL"]
        row = rows[season]
        assert (row["games"], row["wins"], row["losses"]) == (
            len(team),
            int((team["wl"] == "W").sum()),
            int((team["wl"] == "L").sum()),
        )
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["games_total"] == sum(rows[s]["games"] for s in seasons)
    badges = {f["label"]: f["value"] for f in result.metadata["applied_filters"]}
    assert badges["Seasons"] == ", ".join(seasons)


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James stats this season vs last season",
        "LeBron James points this season compared to last season",
        "LeBron James scored more this season than last season",
    ],
)
def test_player_per_named_season(query):
    _, rows = _split(query)
    assert sorted(rows) == ["2024-25", "2025-26"]
    for season, row in rows.items():
        games = _rows("player_game_stats", season)
        games = games[games["player_name"] == "LeBron James"]
        assert row["games"] == len(games)
        assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)


def test_player_count_per_named_season():
    _, rows = _split("how many 30 point games did LeBron James have this season vs last season")
    for season, row in rows.items():
        games = _rows("player_game_stats", season)
        games = games[(games["player_name"] == "LeBron James") & (games["pts"] >= 30)]
        assert row["games"] == len(games)


def test_skipped_season_stays_out():
    _, rows = _split("LeBron James 2023-24 vs 2025-26")
    assert sorted(rows) == ["2023-24", "2025-26"]


@pytest.mark.parametrize(
    "query",
    [
        # One answer would pool the seasons, or answer one of them.
        "LeBron vs Curry this season vs last season",
        "top scorers 2024 vs 2025",
        "Lakers home vs away this season vs last season",
        "Lakers last 10 games this season vs last season",
        # Filters the one-season reading refuses or the split does not run.
        "LeBron James stats when Reaves scores 20 this season vs last season",
        "LeBron James and Curry stats this season vs last season",
        "LeBron James stats when Davis sits this season vs last season",
        "LeBron James stats against Curry this season vs last season",
        # The team summary reads the team's own points for these (on main).
        "Lakers points allowed per game this season vs last season",
        "Lakers opponent field goal percentage this season vs last season",
        "Lakers record vs opponents over 500 this season vs last season",
        "LeBron James stats by opponent 2023-24 vs 2024-25",
    ],
)
def test_routes_without_a_season_split_refuse(query):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "no_result", (query, result.route, result.metadata)


def test_player_season_split_applies_the_team_owned_scoring_bound():
    # Deliberately promotes the former unsupported case: use the team's raw
    # box score to qualify LeBron's games, then aggregate his own stat line.
    result, buckets = _split("LeBron James when the Lakers score 120 2024-25 vs 2025-26")
    assert result.metadata["conditions"] == [
        {"stat": "team_pts", "min_value": 120, "max_value": None}
    ]
    for season in ("2024-25", "2025-26"):
        teams = _rows("team_game_stats", season)
        games = _rows("player_game_stats", season)
        qualifying = teams[(teams.team_abbr == "LAL") & (teams.pts >= 120)]
        expected = games[
            (games.player_name == "LeBron James") & games.game_id.isin(qualifying.game_id)
        ]
        assert buckets[season]["games"] == len(expected)
        for stat in ("pts", "reb", "ast"):
            assert buckets[season][stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Lakers record last season", None),
        ("Lakers record in 2024 and 2025", None),
        ("Lakers record from 2023-24 to 2025-26", None),
        ("LeBron points between 2000 and 2010 points", None),
        ("Lakers record this year vs last", ["2024-25", "2025-26"]),
    ],
)
def test_season_list_reading(query, expected):
    from nbatools.commands.natural_query import parse_query

    assert parse_query(query).get("season_list") == expected


def test_filters_the_split_runs_apply_per_season():
    _, rows = _split("Lakers home record vs the Celtics this season vs last season")
    for season, row in rows.items():
        team = _rows("team_game_stats", season)
        team = team[
            (team["team_abbr"] == "LAL")
            & (team["opponent_team_abbr"] == "BOS")
            & (team["is_home"] == 1)
        ]
        assert (row["games"], row["wins"]) == (len(team), int((team["wl"] == "W").sum()))


def test_a_named_season_without_games_is_named():
    result, rows = _split("Lakers record 2016 vs 2025")
    assert sorted(rows) == ["2024-25"]
    assert "no games in 2015-16" in result.result.caveats


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record this season vs last season vs the season before",
        "Lakers record 2023-24 and the season before",
    ],
)
def test_seasons_named_from_another_are_not_a_list(query):
    from nbatools.commands.natural_query import parse_query

    assert parse_query(query).get("season_list") is None


def test_one_possession_games_per_named_season():
    _, rows = _split("Lakers record in one possession games this season vs last season")
    for season, row in rows.items():
        team = _rows("team_game_stats", season)
        opp = team[["game_id", "team_abbr", "pts"]].rename(
            columns={"team_abbr": "opp_abbr", "pts": "opp_pts"}
        )
        games = team.merge(opp, on="game_id")
        games = games[(games["team_abbr"] == "LAL") & (games["opp_abbr"] != "LAL")]
        margin = games["pts"] - games["opp_pts"]
        close = margin[margin.abs() <= 3]
        assert (row["games"], row["wins"], row["losses"]) == (
            len(close),
            int((close > 0).sum()),
            int((close < 0).sum()),
        )


@pytest.mark.parametrize(
    ("query", "team", "column", "stat"),
    [
        ("Lakers points per game this season vs last season", "LAL", "pts_avg", "pts"),
        ("Lakers turnovers per game this season vs last season", "LAL", "tov_avg", "tov"),
        ("Celtics threes per game this season vs last season", "BOS", "fg3m_avg", "fg3m"),
    ],
)
def test_team_per_game_stats_per_named_season(query, team, column, stat):
    _, rows = _split(query)
    assert sorted(rows) == ["2024-25", "2025-26"]
    for season, row in rows.items():
        games = _rows("team_game_stats", season)
        games = games[games["team_abbr"] == team]
        assert row[column] == pytest.approx(games[stat].mean(), abs=1e-3)


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        (
            "Lakers record when allowing 100 this season vs last season",
            lambda o: o["opp_pts"] >= 100,
        ),
        (
            "Lakers record when they held opponents under 100 this season vs last season",
            lambda o: o["opp_pts"] < 100,
        ),
        (
            "Lakers record when they forced 15 turnovers this season vs last season",
            lambda o: o["opp_tov"] >= 15,
        ),
    ],
)
def test_opponent_bounds_per_named_season(query, keep):
    _, rows = _split(query)
    for season, row in rows.items():
        team = _rows("team_game_stats", season)
        opp = team[["game_id", "team_abbr", "pts", "tov"]].rename(
            columns={"team_abbr": "opp_abbr", "pts": "opp_pts", "tov": "opp_tov"}
        )
        games = team.merge(opp, on="game_id")
        games = games[(games["team_abbr"] == "LAL") & (games["opp_abbr"] != "LAL")]
        games = games[keep(games)]
        assert (row["games"], row["wins"]) == (len(games), int((games["wl"] == "W").sum()))


def test_two_opponents_per_named_season():
    _, rows = _split("Lakers record vs Celtics and Knicks this season vs last season")
    for season, row in rows.items():
        team = _rows("team_game_stats", season)
        team = team[(team["team_abbr"] == "LAL") & team["opponent_team_abbr"].isin(["BOS", "NYK"])]
        assert (row["games"], row["wins"]) == (len(team), int((team["wl"] == "W").sum()))


def test_player_points_opponent_nonadjacent_seasons_and_controls(monkeypatch):
    """S2: an own-points bound and opponent select the same raw player games."""
    from nbatools.commands import player_split_summary
    from nbatools.query_service import execute_natural_query

    seasons = ["2023-24", "2025-26"]
    expected = {}
    for season in seasons:
        raw = _rows("player_game_stats", season)
        player = raw[raw.player_name.eq("LeBron James")]
        opponent = player[player.opponent_team_abbr.eq("BOS")]
        expected[season] = opponent[opponent.pts.ge(25)]
        assert 0 < len(expected[season]) < len(opponent)
        assert len(player[player.pts.ge(25)]) > len(expected[season])
    assert any(frame.pts.eq(25).any() for frame in expected.values())
    # At least one requested sample discriminates inclusive from strict bounds.
    middle = _rows("player_game_stats", "2024-25")
    assert (
        middle.player_name.eq("LeBron James")
        & middle.opponent_team_abbr.eq("BOS")
        & middle.pts.ge(25)
    ).any()

    def keys(frame):
        return set(zip(frame.season, frame.game_id, frame.team_id, frame.player_id))

    def assert_values(row, frame):
        assert row["games"] == len(frame)
        for metric in ("pts", "reb", "ast"):
            assert row[f"{metric}_avg"] == pytest.approx(frame[metric].mean(), abs=0.001)
        assert row["pts_sum"] == frame.pts.sum()

    def assert_labels(result):
        assert result.result_status == "ok", result.metadata
        assert result.metadata["player"] == "LeBron James"
        assert result.metadata["opponent"] == "BOS"
        assert result.metadata["season_type"] == "Regular Season"
        assert result.metadata["min_value"] == 25
        filters = result.metadata["applied_filters"]
        assert {"kind": "team", "label": "Opponent", "value": "BOS"} in filters
        assert {"kind": "threshold", "label": "pts min", "value": "25.0"} in filters

    captured = []
    summarize = player_split_summary._summarize_bucket

    def capture(frame, bucket):
        captured.append((bucket, frame.copy()))
        return summarize(frame, bucket)

    monkeypatch.setattr(player_split_summary, "_summarize_bucket", capture)
    question = "LeBron James averages with at least 25 points against Celtics in "
    combined = execute_natural_query(question + "2023-24 and 2025-26")
    assert_labels(combined)
    assert combined.route == "player_split_summary"
    assert combined.metadata["season_list"] == seasons
    assert [season for season, _ in captured] == seasons
    sections = combined.result.to_dict()["sections"]
    assert [row["bucket"] for row in sections["split_comparison"]] == seasons
    assert sections["summary"][0]["games_total"] == sum(map(len, expected.values()))
    for row, (season, frame) in zip(sections["split_comparison"], captured):
        assert len(frame) == len(expected[season])
        assert keys(frame) == keys(expected[season])
        assert_values(row, expected[season])
    for season in seasons:
        single = execute_natural_query(question + season)
        assert_labels(single)
        assert single.route == "player_game_summary"
        assert single.metadata["season"] == season
        sections = single.result.to_dict()["sections"]
        log = pd.DataFrame(sections["game_log"])
        assert len(log) == len(expected[season])
        assert keys(log) == keys(expected[season])
        assert_values(sections["summary"][0], expected[season])


@pytest.mark.parametrize("home,away", [(1, 0), (0, 1), (0, 0)])
def test_s1_source_venue_contract_accepts_home_away_and_neutral(home, away):
    from tests.test_c1_season_lists_real_data import _assert_venue_flags

    _assert_venue_flags(pd.DataFrame({"is_home": [home], "is_away": [away]}))


@pytest.mark.parametrize("home,away", [(1, 1), (2, 0), (0, -1), (None, 0), (0, None)])
def test_s1_source_venue_contract_rejects_invalid_flags(home, away):
    from tests.test_c1_season_lists_real_data import _assert_venue_flags

    with pytest.raises(AssertionError):
        _assert_venue_flags(pd.DataFrame({"is_home": [home], "is_away": [away]}))
