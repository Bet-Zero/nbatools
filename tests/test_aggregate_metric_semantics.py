"""Formula and cross-command tests for game-sample aggregation."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.aggregate_metrics import (
    METRIC_DESCRIPTORS,
    AggregationKind,
    add_aggregate_metric_fields,
    compute_grouped_rate_metrics,
)
from nbatools.commands.analysis.advanced_metrics import summarize_usage_rate
from nbatools.commands.pipeline.build_league_season_stats import run as build_league_season_stats
from nbatools.commands.player_advanced_metrics import (
    add_sample_advanced_metrics_to_summary_row,
)
from nbatools.commands.player_compare import summarize_player
from nbatools.commands.player_split_summary import _summarize_bucket as summarize_player_bucket
from nbatools.commands.team_compare import summarize_team
from nbatools.commands.team_record import _stat_averages
from nbatools.commands.team_split_summary import _summarize_bucket as summarize_team_bucket
from nbatools.query_service import execute_structured_query

pytestmark = pytest.mark.engine


@pytest.fixture
def unequal_attempt_games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": 1,
                "season": "2024-25",
                "wl": "W",
                "minutes": 30,
                "pts": 5,
                "fgm": 1,
                "fga": 1,
                "fg_pct": 1.0,
                "fg3m": 1,
                "fg3a": 1,
                "fg3_pct": 1.0,
                "ftm": 2,
                "fta": 2,
                "ft_pct": 1.0,
                "reb": 2,
                "ast": 3,
                "stl": 1,
                "blk": 0,
                "tov": 1,
                "plus_minus": 4,
                "efg_pct": 1.5,
                "ts_pct": 0.90,
            },
            {
                "game_id": 2,
                "season": "2024-25",
                "wl": "L",
                "minutes": 30,
                "pts": 0,
                "fgm": 0,
                "fga": 9,
                "fg_pct": 0.0,
                "fg3m": 0,
                "fg3a": 9,
                "fg3_pct": 0.0,
                "ftm": 0,
                "fta": 9,
                "ft_pct": 0.0,
                "reb": 4,
                "ast": 1,
                "stl": 0,
                "blk": 1,
                "tov": 2,
                "plus_minus": -4,
                "efg_pct": 0.0,
                "ts_pct": 0.0,
            },
        ]
    )


def test_metric_descriptors_distinguish_all_aggregation_kinds() -> None:
    assert METRIC_DESCRIPTORS["pts"].kind == AggregationKind.ADDITIVE
    assert METRIC_DESCRIPTORS["usg_pct"].kind == AggregationKind.AVERAGE_ONLY
    assert METRIC_DESCRIPTORS["ts_pct"].kind == AggregationKind.RATE_OF_TOTALS


def test_unequal_attempt_rates_use_totals_and_never_emit_sums(
    unequal_attempt_games: pd.DataFrame,
) -> None:
    row = add_aggregate_metric_fields(
        {},
        unequal_attempt_games,
        ["pts", "fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"],
        sum_metrics=["pts"],
    )

    assert row["pts_avg"] == 2.5
    assert row["pts_sum"] == 5.0
    assert row["fg_pct_avg"] == 0.1
    assert row["fg3_pct_avg"] == 0.1
    assert row["ft_pct_avg"] == 0.182
    assert row["efg_pct_avg"] == 0.15
    assert row["ts_pct_avg"] == 0.168
    assert not any(key.endswith("_pct_sum") for key in row)


def test_rate_metrics_cannot_be_requested_as_sums(
    unequal_attempt_games: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="cannot be summed: ts_pct"):
        add_aggregate_metric_fields(
            {},
            unequal_attempt_games,
            ["ts_pct"],
            sum_metrics=["ts_pct"],
        )


def test_grouped_rate_metrics_use_each_groups_totals(
    unequal_attempt_games: pd.DataFrame,
) -> None:
    source = pd.concat(
        [
            unequal_attempt_games,
            unequal_attempt_games.assign(season="2025-26", pts=[0, 5]),
        ],
        ignore_index=True,
    )

    grouped = compute_grouped_rate_metrics(source, "season", ["efg_pct", "ts_pct"])
    first = grouped.set_index("season").loc["2024-25"]

    assert first["efg_pct_avg"] == 0.15
    assert first["ts_pct_avg"] == 0.168


def test_summary_compare_split_and_record_helpers_share_rate_formulas(
    unequal_attempt_games: pd.DataFrame,
) -> None:
    rows = [
        summarize_player(unequal_attempt_games, unequal_attempt_games, "Test Player"),
        summarize_team(unequal_attempt_games, "Test Team"),
        summarize_player_bucket(unequal_attempt_games, "Home"),
        summarize_team_bucket(unequal_attempt_games, "Home"),
        _stat_averages(unequal_attempt_games),
    ]

    assert {row["efg_pct_avg"] for row in rows} == {0.15}
    assert {row["ts_pct_avg"] for row in rows} == {0.168}


def test_advanced_rate_helpers_do_not_create_sum_aliases(
    unequal_attempt_games: pd.DataFrame,
) -> None:
    summary = add_sample_advanced_metrics_to_summary_row(unequal_attempt_games, {})
    usage = summarize_usage_rate(pd.DataFrame({"usg_pct": [20.0, 30.0]}))

    assert not any(key.endswith("_pct_sum") for key in summary)
    assert usage == {"usg_pct_avg": 25.0}


@pytest.mark.needs_data
def test_structured_summary_recomputes_real_sample_rates_without_rate_sums() -> None:
    result = execute_structured_query(
        "player_game_summary",
        player="Nikola Jokic",
        season="2025-26",
    ).to_dict()
    summary = result["sections"]["summary"][0]
    games = pd.DataFrame(result["sections"]["game_log"])

    expected_efg = (games["fgm"].sum() + 0.5 * games["fg3m"].sum()) / games["fga"].sum()
    expected_ts = games["pts"].sum() / (2.0 * (games["fga"].sum() + 0.44 * games["fta"].sum()))

    assert summary["efg_pct_avg"] == round(expected_efg, 3)
    assert summary["ts_pct_avg"] == round(expected_ts, 3)
    assert not any(key.endswith("_pct_sum") for key in summary)


def test_league_season_pipeline_uses_total_makes_and_attempts(
    tmp_path,
    monkeypatch,
    unequal_attempt_games: pd.DataFrame,
) -> None:
    input_path = tmp_path / "data/raw/team_game_stats/2024-25_regular_season.csv"
    input_path.parent.mkdir(parents=True)
    unequal_attempt_games.to_csv(input_path, index=False)
    monkeypatch.chdir(tmp_path)

    build_league_season_stats("2024-25", "Regular Season")

    output = pd.read_csv(
        tmp_path / "data/processed/league_season_stats/2024-25_regular_season.csv"
    ).iloc[0]
    assert output["avg_fg3_pct"] == pytest.approx(0.1)
