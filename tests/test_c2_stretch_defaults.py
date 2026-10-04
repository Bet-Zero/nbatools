"""C2 stretches with no length named, and player stretch answers.

"Celtics best stretch" fell to a game list and "LeBron best stretch" to a
season summary. Player stretch lists repeated the same hot run as several
overlapping windows and had no headline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")
SEASON = "2025-26"


def _board(query: str) -> tuple[list[dict], dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]["leaderboard"], result.metadata


@pytest.mark.parametrize(
    ("unsized", "sized", "route"),
    [
        ("Celtics best stretch", "Celtics best 10 game stretch", "team_stretch_leaderboard"),
        ("Celtics worst stretch", "Celtics worst 10 game stretch", "team_stretch_leaderboard"),
        (
            "which team had the best stretch",
            "which team had the best 10 game stretch",
            "team_stretch_leaderboard",
        ),
        ("LeBron best stretch", "LeBron best 10 game stretch", "player_stretch_leaderboard"),
        (
            "Jokic best scoring stretch",
            "Jokic best 10 game scoring stretch",
            "player_stretch_leaderboard",
        ),
    ],
)
def test_unsized_stretch_ranks_ten_game_windows(unsized, sized, route):
    rows, metadata = _board(f"{unsized} in {SEASON}")
    expected, _ = _board(f"{sized} in {SEASON}")
    assert metadata["route"] == route
    assert rows == expected
    assert "default: no stretch length named; ranked 10-game windows" in metadata["notes"]


def test_named_length_has_no_default_note():
    _, metadata = _board(f"Celtics best 5 game stretch in {SEASON}")
    assert not any("no stretch length" in note for note in metadata.get("notes") or [])


@pytest.mark.parametrize(
    "query",
    [
        f"Celtics played well down the stretch in {SEASON}",
        f"Celtics stretch run record in {SEASON}",
    ],
)
def test_late_game_and_season_end_wording_is_not_a_rolling_stretch(query):
    result = execute_natural_query(query)
    assert result.metadata["route"] not in {
        "team_stretch_leaderboard",
        "player_stretch_leaderboard",
    }


def test_any_team_wording_ranks_teams():
    _, metadata = _board(f"best 5 game stretches by any team in {SEASON}")
    assert metadata["route"] == "team_stretch_leaderboard"


def _player_points(name: str) -> list[tuple]:
    frame = pd.read_csv(RAW / f"{SEASON}_regular_season.csv", dtype={"game_id": str})
    games = frame[frame["player_name"] == name].sort_values(["game_date", "game_id"])
    return list(zip(games["game_date"], games["pts"], strict=True))


def test_named_player_windows_never_overlap_and_lead_the_headline():
    games = _player_points("Nikola Jokić")
    windows = [
        (round(sum(p for _, p in games[i : i + 5]) / 5, 3), games[i][0], games[i + 4][0])
        for i in range(len(games) - 4)
    ]
    best = max(windows, key=lambda w: (w[0], w[2]))

    rows, metadata = _board(f"Jokic best 5 game scoring stretch in {SEASON}")
    top = rows[0]
    assert top["stretch_value"] == pytest.approx(best[0])
    assert str(top["window_start_date"])[:10] == best[1]
    spans = sorted((str(r["window_start_date"])[:10], str(r["window_end_date"])[:10]) for r in rows)
    for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
        assert start > end
    assert metadata["answer_phrase"] == (
        f"Nikola Jokić's best 5-game stretch of {SEASON} was "
        f"{best[0]:.1f} points per game from {best[1]} to {best[2]}."
    )


def test_league_player_stretch_headline_names_the_leader():
    rows, metadata = _board(f"best 5 game scoring stretch in {SEASON}")
    assert metadata["answer_phrase"].startswith(
        f"{rows[0]['player_name']} had the best 5-game stretch of {SEASON} by any player: "
    )


@pytest.mark.parametrize(
    ("query", "metric"),
    [
        ("Curry best 5 game 3 point shooting stretch", "fg3_pct"),
        ("Curry best 5 game three point shooting stretch", "fg3_pct"),
        ("Curry best 5 game shooting stretch", "fg_pct"),
        ("Curry best 5 game free throw shooting stretch", "ft_pct"),
        ("Curry best 5 game true shooting stretch", "ts_pct"),
    ],
)
def test_shooting_wording_ranks_the_shooting_rate(query, metric):
    rows, _ = _board(f"{query} in {SEASON}")
    assert rows[0]["stretch_metric"] == metric


def test_league_three_point_stretch_needs_a_made_three_per_game():
    frame = pd.read_csv(RAW / f"{SEASON}_regular_season.csv", dtype={"game_id": str})
    best = None
    for name, games in frame.sort_values(["game_date", "game_id"]).groupby("player_name"):
        rows = list(zip(games["fg3m"], games["fg3a"], strict=True))
        for i in range(len(rows) - 4):
            made = sum(m for m, _ in rows[i : i + 5])
            tried = sum(a for _, a in rows[i : i + 5])
            if made >= 5 and tried:
                best = max(best or 0.0, round(made / tried, 3))

    rows, metadata = _board(f"best 5 game 3 point shooting stretch in {SEASON}")
    assert rows[0]["stretch_value"] == pytest.approx(best)
    assert any(
        note.startswith("qualifier: windows need 1+ made threes") for note in metadata["notes"]
    )


def test_named_player_worst_stretch_ranks_from_the_bottom():
    games = _player_points("LeBron James")
    windows = [
        (round(sum(p for _, p in games[i : i + 5]) / 5, 3), games[i][0], games[i + 4][0])
        for i in range(len(games) - 4)
    ]
    worst = min(windows, key=lambda w: w[0])

    rows, metadata = _board(f"LeBron worst 5 game scoring stretch in {SEASON}")
    assert rows[0]["stretch_value"] == pytest.approx(worst[0])
    assert metadata["answer_phrase"].startswith("LeBron James's worst 5-game stretch")


@pytest.mark.parametrize(
    "query",
    [
        f"LeBron coldest stretch in {SEASON}",
        f"worst 5 game scoring stretch in {SEASON}",
    ],
)
def test_worst_wording_says_worst(query):
    _, metadata = _board(query)
    assert "worst" in metadata["answer_phrase"]


@pytest.mark.parametrize(
    ("query", "metric"),
    [
        ("best 5 game scoring stretch by a Lakers player", "pts"),
        ("LeBron best 5 game scoring stretch while shooting 50 percent", "pts"),
        ("Curry best 3 point shooting 5 game stretch", "fg3_pct"),
    ],
)
def test_shooting_only_counts_when_it_names_the_stretch(query, metric):
    rows, _ = _board(f"{query} in {SEASON}")
    assert rows[0]["stretch_metric"] == metric


@pytest.mark.parametrize(
    "query",
    [
        f"best stretch for a rookie in {SEASON}",
        f"best stretch by a shooting guard in {SEASON}",
        f"best 5 game scoring stretch by a shooting guard in {SEASON}",
        f"best shooting stretch by a guard in {SEASON}",
    ],
)
def test_player_group_stretches_refuse_instead_of_ranking_everyone(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    "query", [f"best stretch four in {SEASON}", f"top stretch bigs in {SEASON}"]
)
def test_stretch_positions_are_not_rolling_stretches(query):
    result = execute_natural_query(query)
    assert result.metadata.get("route") not in {
        "team_stretch_leaderboard",
        "player_stretch_leaderboard",
    }


def test_team_shooting_stretch_ranks_teams():
    _, metadata = _board(f"best team shooting stretch in {SEASON}")
    assert metadata["route"] == "team_stretch_leaderboard"


@pytest.mark.parametrize(
    "query",
    [
        f"LeBron best 5 game scoring stretch against the worst teams in {SEASON}",
        f"best 5 game scoring stretch against the worst defenses in {SEASON}",
        f"Celtics best 5 game stretch against the worst teams in {SEASON}",
    ],
)
def test_unread_opponent_descriptions_refuse_and_never_flip_to_worst(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    "query",
    [
        f"best 5 game scoring stretch going forward in {SEASON}",
        f"best 5 game stretch at the Barclays Center in {SEASON}",
    ],
)
def test_group_words_outside_the_subject_do_not_refuse(query):
    rows, _ = _board(query)
    assert rows


def test_league_worst_three_point_stretch_qualifies_on_attempts():
    frame = pd.read_csv(RAW / f"{SEASON}_regular_season.csv", dtype={"game_id": str})
    worst = None
    for _, games in frame.sort_values(["game_date", "game_id"]).groupby("player_name"):
        rows = list(zip(games["fg3m"], games["fg3a"], strict=True))
        for i in range(len(rows) - 9):
            made = sum(m for m, _ in rows[i : i + 10])
            tried = sum(a for _, a in rows[i : i + 10])
            if tried >= 30:
                value = round(made / tried, 3)
                worst = value if worst is None else min(worst, value)

    rows, metadata = _board(f"coldest 3 point shooting stretch in {SEASON}")
    assert rows[0]["stretch_value"] == pytest.approx(worst)
    assert "qualifier: windows need 3+ three-point attempts per game" in metadata["notes"]


@pytest.mark.parametrize(
    "query",
    [
        f"Celtics worst 5 game 3 point shooting stretch in {SEASON}",
        f"Celtics worst rolling 10 game net rating in {SEASON}",
        f"which team had the worst rolling 10 game net rating in {SEASON}",
        f"Lakers coldest rolling 5 game 3 point percentage in {SEASON}",
        f"worst 5 game 3 point shooting stretch in {SEASON}",
        f"LeBron worst 10 game free throw shooting stretch in {SEASON}",
        f"LeBron worst rolling 5 game scoring average in {SEASON}",
    ],
)
def test_long_worst_wordings_rank_from_the_bottom(query):
    _, metadata = _board(query)
    assert "worst" in metadata["answer_phrase"]
    assert "best" not in metadata["answer_phrase"]


def test_team_rolling_three_point_percentage_is_the_rate():
    rows, _ = _board(f"Lakers coldest rolling 5 game 3 point percentage in {SEASON}")
    assert rows[0]["stretch_metric"] == "fg3_pct"


@pytest.mark.parametrize(
    "query",
    [
        f"LeBron best 5 game stretch with the worst teammates in {SEASON}",
        f"best 5 game stretch by a player on the worst team in {SEASON}",
    ],
)
def test_grade_nearest_the_stretch_decides(query):
    _, metadata = _board(query)
    assert "best" in metadata["answer_phrase"]
    assert "worst" not in metadata["answer_phrase"]
