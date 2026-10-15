"""A season split groups the same qualified played sample as a summary."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import player_split_summary, team_split_summary
from nbatools.commands.data_utils import filter_with_player
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]
SEASONS = ["2023-24", "2025-26"]


@pytest.fixture
def played_sample(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    expected = {}
    for season in SEASONS:
        path = root / f"data/raw/player_game_stats/{season}_regular_season.csv"
        players = pd.read_csv(path)
        ids = sorted(players.loc[players.team_abbr.eq("BOS"), "game_id"].unique())
        players = players.loc[
            ~(players.player_name.eq("Jayson Tatum") & players.game_id.isin(ids[::3]))
        ]
        gsw_ids = sorted(players.loc[players.team_abbr.eq("GSW"), "game_id"].unique())
        players = players.loc[
            ~(
                (players.player_name.eq("Klay Thompson") & players.game_id.isin(gsw_ids[::4]))
                | (players.player_name.eq("Draymond Green") & players.game_id.isin(gsw_ids[1::5]))
            )
        ]
        lal_ids = sorted(players.loc[players.team_abbr.eq("LAL"), "game_id"].unique())
        players = players.loc[
            ~(players.player_name.eq("LeBron James") & players.game_id.isin(lal_ids[::4]))
        ]
        players.to_csv(path, index=False)
        present = set(players.loc[players.player_name.eq("Jayson Tatum"), "game_id"])
        teams = pd.read_csv(root / f"data/raw/team_game_stats/{season}_regular_season.csv")
        expected[season] = {
            "team": teams.loc[
                teams.team_abbr.eq("BOS")
                & teams.opponent_team_abbr.eq("LAL")
                & teams.game_id.isin(present)
            ],
            "player": players.loc[
                players.player_name.eq("Jaylen Brown")
                & players.opponent_team_abbr.eq("LAL")
                & players.game_id.isin(present)
            ],
        }
        lebron = set(players.loc[players.player_name.eq("LeBron James"), "game_id"])
        expected[season]["lakers_bound"] = teams.loc[
            teams.team_abbr.eq("LAL") & teams.pts.ge(120) & teams.game_id.isin(lebron)
        ]
        klay = set(players.loc[players.player_name.eq("Klay Thompson"), "game_id"])
        green = set(players.loc[players.player_name.eq("Draymond Green"), "game_id"])
        expected[season]["curry_bound"] = players.loc[
            players.player_name.eq("Stephen Curry")
            & players.opponent_team_abbr.eq("NYK")
            & players.pts.ge(24)
            & players.game_id.isin(klay)
        ]
        expected[season]["warriors_pair"] = teams.loc[
            teams.team_abbr.eq("GSW")
            & teams.opponent_team_abbr.eq("NYK")
            & teams.game_id.isin(klay & green)
        ]
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield expected
    reset_data_source_cache()


@pytest.mark.parametrize("kind", ["team", "player"])
@pytest.mark.parametrize("entry", ["natural", "structured"])
def test_played_condition_keeps_sample_ids_and_split_values(
    played_sample, monkeypatch, kind, entry
):
    module = team_split_summary if kind == "team" else player_split_summary
    original = module._summarize_bucket
    seen = {}

    def capture(frame, bucket):
        seen[bucket] = set(frame.game_id)
        return original(frame, bucket)

    monkeypatch.setattr(module, "_summarize_bucket", capture)
    if entry == "natural":
        subject = "Celtics record" if kind == "team" else "Jaylen Brown stats"
        result = execute_natural_query(
            f"{subject} against Lakers with Tatum playing in 2023-24 and 2025-26"
        )
    else:
        identity = {"team": "BOS"} if kind == "team" else {"player": "Jaylen Brown"}
        result = execute_structured_query(
            f"{kind}_split_summary",
            split="season",
            start_season="2023-24",
            end_season="2025-26",
            split_seasons=SEASONS,
            opponent="LAL",
            with_player="Jayson Tatum",
            **identity,
        )
    assert result.result_status == "ok"
    rows = result.to_dict()["sections"]["split_comparison"]
    assert [row["bucket"] for row in rows] == SEASONS
    for row in rows:
        expected = played_sample[row["bucket"]][kind]
        assert seen[row["bucket"]] == set(expected.game_id)
        assert row["games"] == len(expected) == 8
        assert row["wins"] == expected.wl.eq("W").sum() == 7
        assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)


@pytest.mark.parametrize("status", ["injured", "healthy", "available", "resting", "inactive"])
def test_status_stays_separate_from_played_splits(played_sample, status):
    result = execute_natural_query(
        f"Celtics record against Lakers with Tatum {status} in 2023-24 and 2025-26"
    )
    assert result.result_status == "no_result"
    assert "availability_status" in result.metadata["unsupported_filters"]
    assert not result.to_dict()["sections"]


def test_empty_played_identity_cannot_drop_condition(monkeypatch):
    frame = pd.DataFrame(
        {
            "game_id": [1],
            "team_id": [2],
            "team_abbr": ["BOS"],
            "player_id": [3],
            "player_name": ["Jayson Tatum"],
        }
    )
    monkeypatch.setattr(
        "nbatools.commands.data_utils.load_player_games_for_seasons", lambda *_: frame.iloc[:0]
    )
    assert filter_with_player(frame, "Jayson Tatum", SEASONS, "Regular Season").empty


def test_team_summary_uses_played_ids(played_sample):
    result = execute_structured_query(
        "game_summary", team="BOS", season="2025-26", opponent="LAL", with_player="Jayson Tatum"
    )
    assert result.result_status == "ok"
    assert {row["game_id"] for row in result.to_dict()["sections"]["game_log"]} == set(
        played_sample["2025-26"]["team"].game_id
    )


@pytest.mark.parametrize("axis", ["by month", "in 2023-24 and 2025-26"])
def test_teammate_minutes_do_not_become_team_minutes(played_sample, axis):
    result = execute_natural_query(f"Celtics record with Tatum playing 30 minutes {axis}")
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


@pytest.mark.parametrize("period", ["in 2025-26", "in 2023-24 and 2025-26"])
@pytest.mark.parametrize(
    "clause",
    [
        "with at least 24 points against Knicks with Thompson playing",
        "against Knicks with Thompson playing and at least 24 points",
        "with Thompson and at least 24 points against Knicks",
    ],
)
def test_stat_clause_does_not_hide_later_teammate(played_sample, period, clause):
    result = execute_natural_query(f"Stephen Curry averages {clause} {period}")
    assert result.result_status == "ok"
    assert result.metadata["with_player"] == "Klay Thompson"
    if "and" in period:
        rows = result.to_dict()["sections"]["split_comparison"]
        assert [r["bucket"] for r in rows] == SEASONS
    else:
        rows = [{**result.to_dict()["sections"]["summary"][0], "bucket": "2025-26"}]
    for row in rows:
        expected = played_sample[row["bucket"]]["curry_bound"]
        assert len(expected) > 0
        assert row["games"] == len(expected)
        assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)


@pytest.mark.parametrize(
    "clause",
    [
        "against Knicks with Thompson and Green playing",
        "with Thompson and Green playing against Knicks",
    ],
)
def test_team_pair_transfers_both_names_and_rows(played_sample, monkeypatch, clause):
    original = team_split_summary._summarize_bucket
    seen = {}

    def capture(frame, bucket):
        seen[bucket] = set(frame.game_id)
        return original(frame, bucket)

    monkeypatch.setattr(team_split_summary, "_summarize_bucket", capture)
    result = execute_natural_query(f"Warriors record {clause} in 2023-24 and 2025-26")
    assert result.result_status == "ok"
    assert result.metadata["with_player"] == "Klay Thompson and Draymond Green"
    for row in result.to_dict()["sections"]["split_comparison"]:
        expected = played_sample[row["bucket"]]["warriors_pair"]
        assert len(expected) > 0
        assert seen[row["bucket"]] == set(expected.game_id)
        assert row["games"] == len(expected)
        assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)


@pytest.mark.parametrize("presence", ["on the court", "off the court", "on court", "on the floor"])
@pytest.mark.parametrize("period", ["in 2025-26", "in 2023-24 and 2025-26"])
def test_on_court_is_never_whole_game_participation(played_sample, presence, period):
    result = execute_natural_query(f"Celtics record with Tatum {presence} {period}")
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]
    assert result.metadata.get("with_player") is None


def test_separate_team_bound_and_named_presence_are_both_applied(played_sample):
    result = execute_natural_query("Lakers record in games with 120 points with LeBron in 2025-26")
    assert result.result_status == "ok"
    expected = played_sample["2025-26"]["lakers_bound"]
    sections = result.to_dict()["sections"]
    assert {r["game_id"] for r in sections["game_log"]} == set(expected.game_id)
    assert 0 < len(expected) < 19  # The unfiltered 120+ sample has 19 games.
    row = sections["summary"][0]
    assert row["games"] == len(expected)
    assert row["wins"] == expected.wl.eq("W").sum()
    assert row["losses"] == expected.wl.eq("L").sum()
    assert result.metadata["with_player"] == "LeBron James"
