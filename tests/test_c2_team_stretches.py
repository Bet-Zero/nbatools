"""C2 team rolling stretches: "Celtics best 10 game stretch".

"best 10 game stretch for the Celtics" listed games and "which team had the
best 10 game stretch" was refused. Expected windows are counted from the
fixture's team game CSV with a plain loop, never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")
SEASON = "2025-26"


def _team_games() -> pd.DataFrame:
    frame = pd.read_csv(RAW / f"{SEASON}_regular_season.csv", dtype={"game_id": str})
    return frame.sort_values(["game_date", "game_id"])


def _windows(games: pd.DataFrame, size: int, value) -> list[tuple]:
    """(value, net per game, start date, end date) of every N-game window."""
    rows = list(games.itertuples())
    out = []
    for start in range(len(rows) - size + 1):
        chunk = rows[start : start + size]
        net = sum(r.plus_minus for r in chunk) / size
        out.append((value(chunk), round(net, 2), chunk[0].game_date, chunk[-1].game_date))
    return out


def _wins(chunk) -> int:
    return sum(r.wl == "W" for r in chunk)


def _rows(query: str) -> tuple[list[dict], dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.metadata["route"] == "team_stretch_leaderboard"
    return result.result.to_dict()["sections"]["leaderboard"], result.metadata


def test_named_team_best_stretch_is_its_best_record_window():
    celtics = _team_games().query("team_abbr == 'BOS'")
    best = max(_windows(celtics, 10, _wins), key=lambda w: (w[0], w[1]))

    rows, metadata = _rows(f"best 10 game stretch for the Celtics in {SEASON}")
    top = rows[0]
    assert (top["wins"], top["losses"]) == (best[0], 10 - best[0])
    assert top["net_per_game"] == best[1]
    assert (top["window_start_date"], top["window_end_date"]) == (best[2], best[3])
    assert metadata["answer_phrase"].startswith(f"The Boston Celtics went {best[0]}-")
    assert {row["team_name"] for row in rows} == {"Boston Celtics"}


def test_named_team_windows_never_overlap():
    rows, _ = _rows(f"Celtics best 5 game stretch in {SEASON}")
    spans = sorted((row["window_start_date"], row["window_end_date"]) for row in rows)
    for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
        assert start > end


def test_league_ranking_keeps_each_teams_best_window():
    games = _team_games()
    best = {
        name: max(_windows(team, 10, _wins), key=lambda w: (w[0], w[1]))
        for name, team in games.groupby("team_name")
        if len(team) >= 10
    }
    expected = sorted(best.items(), key=lambda item: (item[1][0], item[1][1]), reverse=True)

    rows, metadata = _rows(f"which team had the best 10 game stretch in {SEASON}")
    assert [row["team_name"] for row in rows] == [name for name, _ in expected][:10]
    assert [row["wins"] for row in rows] == [w[0] for _, w in expected][:10]
    assert "the league's best 10-game stretch" in metadata["answer_phrase"]


def test_worst_stretch_ranks_from_the_bottom():
    lakers = _team_games().query("team_abbr == 'LAL'")
    worst = min(_windows(lakers, 5, _wins), key=lambda w: (w[0], w[1]))

    rows, metadata = _rows(f"Lakers worst 5 game stretch in {SEASON}")
    assert (rows[0]["wins"], rows[0]["net_per_game"]) == (worst[0], worst[1])
    assert "their worst 5-game stretch" in metadata["answer_phrase"]


@pytest.mark.parametrize(
    ("query", "metric", "value", "lowest_first"),
    [
        (
            f"best 10 game defensive stretch by a team in {SEASON}",
            "opp_pts",
            lambda chunk: sum(r.pts - r.plus_minus for r in chunk) / 10,
            True,
        ),
        (
            f"best 10 game scoring stretch by a team in {SEASON}",
            "pts",
            lambda chunk: sum(r.pts for r in chunk) / 10,
            False,
        ),
        (
            f"best 10 game three point shooting stretch by a team in {SEASON}",
            "fg3_pct",
            lambda chunk: sum(r.fg3m for r in chunk) / sum(r.fg3a for r in chunk),
            False,
        ),
    ],
)
def test_stat_stretches_match_raw_rows(query, metric, value, lowest_first):
    games = _team_games()
    per_team = [
        max(_windows(team, 10, value), key=lambda w: -w[0] if lowest_first else w[0])[0]
        for _, team in games.groupby("team_name")
        if len(team) >= 10
    ]
    leader = min(per_team) if lowest_first else max(per_team)

    rows, _ = _rows(query)
    assert rows[0]["stretch_metric"] == metric
    assert rows[0]["stretch_value"] == pytest.approx(leader, abs=1e-3)


def test_player_wording_on_a_team_stays_a_player_stretch():
    result = execute_natural_query(
        f"which Lakers player had the best 5 game scoring stretch in {SEASON}"
    )
    assert result.metadata["route"] == "player_stretch_leaderboard"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["team_abbr"] for row in rows} == {"LAL"}


@pytest.mark.parametrize(
    ("query", "value", "lowest"),
    [
        (
            f"Lakers 5 game stretch with the lowest points allowed in {SEASON}",
            lambda chunk: sum(r.pts - r.plus_minus for r in chunk) / 5,
            True,
        ),
        (
            f"Lakers 5 game stretch with the most points allowed in {SEASON}",
            lambda chunk: sum(r.pts - r.plus_minus for r in chunk) / 5,
            False,
        ),
        (
            f"Lakers 5 game stretch with most turnovers in {SEASON}",
            lambda chunk: sum(r.tov for r in chunk) / 5,
            False,
        ),
        (
            f"Lakers lowest scoring 5 game stretch in {SEASON}",
            lambda chunk: sum(r.pts for r in chunk) / 5,
            True,
        ),
    ],
)
def test_lowest_and_most_mean_the_raw_number(query, value, lowest):
    lakers = _team_games().query("team_abbr == 'LAL'")
    values = [w[0] for w in _windows(lakers, 5, value)]
    rows, _ = _rows(query)
    assert rows[0]["stretch_value"] == pytest.approx(
        min(values) if lowest else max(values), abs=1e-3
    )


def test_two_named_teams_are_both_ranked():
    games = _team_games()
    best = {
        abbr: max(_windows(games.query("team_abbr == @abbr"), 5, _wins), key=lambda w: (w[0], w[1]))
        for abbr in ("LAL", "BOS")
    }
    rows, metadata = _rows(f"Lakers and Celtics best 5 game stretch in {SEASON}")
    assert {row["team_abbr"]: (row["wins"], row["net_per_game"]) for row in rows} == {
        abbr: (w[0], w[1]) for abbr, w in best.items()
    }
    assert "by either team in" in metadata["answer_phrase"]


@pytest.mark.parametrize(
    "query",
    [
        f"what was the Lakers best 10 game stretch in {SEASON}",
        f"Lakers best 5 game stretch with min points allowed in {SEASON}",
    ],
)
def test_alias_words_do_not_add_teams(query):
    rows, metadata = _rows(query)
    assert {row["team_abbr"] for row in rows} == {"LAL"}
    assert "their" in metadata["answer_phrase"]


def test_two_opponents_stay_opponents():
    games = _team_games().query("team_abbr == 'BOS' and opponent_team_abbr in ['LAL', 'NYK']")
    best = max(_windows(games, 5, _wins), key=lambda w: (w[0], w[1]))
    rows, _ = _rows(f"Celtics best 5 game stretch vs Lakers and Knicks in {SEASON}")
    assert {row["team_abbr"] for row in rows} == {"BOS"}
    assert (rows[0]["wins"], rows[0]["net_per_game"]) == (best[0], best[1])


@pytest.mark.parametrize(
    ("query", "lowest"),
    [
        (f"top 5 team 5 game stretches with the most points allowed in {SEASON}", False),
        (f"Lakers most defensive 5 game stretch in {SEASON}", True),
    ],
)
def test_count_and_quality_words_keep_direction(query, lowest):
    games = _team_games()
    if query.startswith("Lakers"):
        games = games.query("team_abbr == 'LAL'")
    values = [
        w[0]
        for _, team in games.groupby("team_abbr")
        for w in _windows(team, 5, lambda chunk: sum(r.pts - r.plus_minus for r in chunk) / 5)
    ]
    rows, _ = _rows(query)
    assert rows[0]["stretch_value"] == pytest.approx(
        min(values) if lowest else max(values), abs=1e-3
    )


def test_most_wins_over_a_stretch_is_the_record_ranking():
    rows, metadata = _rows(f"which team had the most wins over a 10 game stretch in {SEASON}")
    assert rows[0]["stretch_metric"] == "wins"
    assert not metadata.get("unsupported_filters")


@pytest.mark.parametrize(
    ("query", "abbrs"),
    [
        (f"compare Lakers and Celtics best 5 game stretch in {SEASON}", ("LAL", "BOS")),
        (f"compare the Lakers and Celtics 5 game stretches in {SEASON}", ("LAL", "BOS")),
        (f"Lakers, Celtics and Knicks best 5 game stretch in {SEASON}", ("LAL", "BOS", "NYK")),
        (f"LAL and BOS best 5 game stretch in {SEASON}", ("LAL", "BOS")),
    ],
)
def test_every_listed_team_is_ranked_on_its_stretch(query, abbrs):
    games = _team_games()
    best = {
        abbr: max(_windows(games.query("team_abbr == @abbr"), 5, _wins), key=lambda w: (w[0], w[1]))
        for abbr in abbrs
    }
    rows, _ = _rows(query)
    assert {row["team_abbr"]: (row["wins"], row["net_per_game"]) for row in rows} == {
        abbr: (w[0], w[1]) for abbr, w in best.items()
    }


def test_multi_season_pair_headline_names_the_season_range():
    rows, metadata = _rows("Warriors and Nuggets best 5 game stretch from 2023-24 to 2025-26")
    # Each team's best window falls in a different season in the fixture.
    assert sorted(row["season"] for row in rows) == ["2023-24", "2025-26"]
    assert metadata["answer_phrase"].endswith("from 2023-24 to 2025-26.")
