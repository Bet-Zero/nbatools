import pandas as pd

from nbatools.commands.player_advanced_metrics import (
    build_player_team_context,
    compute_grouped_sample_advanced_metrics,
    compute_sample_advanced_metrics,
    compute_sample_ast_pct,
    compute_sample_reb_pct,
    compute_sample_usg_pct,
    compute_season_grouped_sample_advanced_metrics,
)


def test_build_player_team_context_attaches_team_and_opponent_rows():
    player_df = pd.DataFrame(
        [
            {
                "game_id": "G1",
                "season": "2025-26",
                "season_type": "Regular Season",
                "player_id": 1,
                "player_name": "Test Player",
                "team_id": 100,
                "opponent_team_id": 200,
                "minutes": 36,
                "fgm": 10,
                "fga": 20,
                "fta": 6,
                "tov": 4,
                "reb": 12,
                "ast": 8,
            }
        ]
    )

    team_df = pd.DataFrame(
        [
            {
                "game_id": "G1",
                "season": "2025-26",
                "season_type": "Regular Season",
                "team_id": 100,
                "team_abbr": "AAA",
                "team_name": "A Team",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "minutes": 240,
                "fgm": 40,
                "fga": 85,
                "fta": 20,
                "tov": 12,
                "reb": 50,
                "wl": "W",
            },
            {
                "game_id": "G1",
                "season": "2025-26",
                "season_type": "Regular Season",
                "team_id": 200,
                "team_abbr": "BBB",
                "team_name": "B Team",
                "opponent_team_id": 100,
                "opponent_team_abbr": "AAA",
                "minutes": 240,
                "fgm": 38,
                "fga": 82,
                "fta": 18,
                "tov": 14,
                "reb": 44,
                "wl": "L",
            },
        ]
    )

    out = build_player_team_context(player_df, team_df)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["team_minutes"] == 240
    assert row["team_fgm"] == 40
    assert row["team_fga"] == 85
    assert row["team_fta"] == 20
    assert row["team_tov"] == 12
    assert row["team_reb"] == 50
    assert row["opp_minutes"] == 240
    assert row["opp_fgm"] == 38
    assert row["opp_fga"] == 82
    assert row["opp_fta"] == 18
    assert row["opp_tov"] == 14
    assert row["opp_reb"] == 44


def test_compute_sample_usg_pct_matches_formula():
    df = pd.DataFrame(
        [
            {
                "minutes": 36,
                "fga": 20,
                "fta": 6,
                "tov": 4,
                "team_minutes": 240,
                "team_fga": 85,
                "team_fta": 20,
                "team_tov": 12,
            },
            {
                "minutes": 34,
                "fga": 18,
                "fta": 4,
                "tov": 3,
                "team_minutes": 240,
                "team_fga": 82,
                "team_fta": 18,
                "team_tov": 11,
            },
        ]
    )

    player_fga = 38
    player_fta = 10
    player_tov = 7
    player_minutes = 70
    team_fga = 167
    team_fta = 38
    team_tov = 23
    team_minutes = 480

    expected = round(
        100
        * (
            ((player_fga + 0.44 * player_fta + player_tov) * (team_minutes / 5))
            / (player_minutes * (team_fga + 0.44 * team_fta + team_tov))
        ),
        3,
    )

    actual = compute_sample_usg_pct(df)
    assert actual == expected


def test_compute_sample_ast_pct_matches_formula():
    df = pd.DataFrame(
        [
            {
                "ast": 8,
                "fgm": 10,
                "minutes": 36,
                "team_fgm": 40,
                "team_minutes": 240,
            },
            {
                "ast": 7,
                "fgm": 9,
                "minutes": 34,
                "team_fgm": 38,
                "team_minutes": 240,
            },
        ]
    )

    player_ast = 15
    player_fgm = 19
    player_minutes = 70
    team_fgm = 78
    team_minutes = 480

    expected = round(
        100 * (player_ast / (((player_minutes / (team_minutes / 5)) * team_fgm) - player_fgm)),
        3,
    )

    actual = compute_sample_ast_pct(df)
    assert actual == expected


def test_compute_sample_reb_pct_matches_formula():
    df = pd.DataFrame(
        [
            {
                "reb": 12,
                "minutes": 36,
                "team_minutes": 240,
                "team_reb": 50,
                "opp_reb": 44,
            },
            {
                "reb": 10,
                "minutes": 34,
                "team_minutes": 240,
                "team_reb": 48,
                "opp_reb": 42,
            },
        ]
    )

    player_reb = 22
    player_minutes = 70
    team_minutes = 480
    team_reb = 98
    opp_reb = 86

    expected = round(
        100 * ((player_reb * (team_minutes / 5)) / (player_minutes * (team_reb + opp_reb))),
        3,
    )

    actual = compute_sample_reb_pct(df)
    assert actual == expected


def test_compute_sample_advanced_metrics_returns_all_three():
    df = pd.DataFrame(
        [
            {
                "minutes": 36,
                "fga": 20,
                "fta": 6,
                "tov": 4,
                "reb": 12,
                "ast": 8,
                "fgm": 10,
                "team_minutes": 240,
                "team_fga": 85,
                "team_fta": 20,
                "team_tov": 12,
                "team_fgm": 40,
                "team_reb": 50,
                "opp_reb": 44,
            }
        ]
    )

    metrics = compute_sample_advanced_metrics(df)
    assert set(metrics.keys()) == {"usg_pct_avg", "ast_pct_avg", "reb_pct_avg"}
    assert metrics["usg_pct_avg"] is not None
    assert metrics["ast_pct_avg"] is not None
    assert metrics["reb_pct_avg"] is not None


def test_compute_sample_metrics_returns_none_safely_on_zero_denominators():
    df = pd.DataFrame(
        [
            {
                "minutes": 0,
                "fga": 0,
                "fta": 0,
                "tov": 0,
                "reb": 0,
                "ast": 0,
                "fgm": 0,
                "team_minutes": 0,
                "team_fga": 0,
                "team_fta": 0,
                "team_tov": 0,
                "team_fgm": 0,
                "team_reb": 0,
                "opp_reb": 0,
            }
        ]
    )

    assert compute_sample_usg_pct(df) is None
    assert compute_sample_ast_pct(df) is None
    assert compute_sample_reb_pct(df) is None


def test_compute_grouped_sample_advanced_metrics_returns_different_bucket_values():
    df = pd.DataFrame(
        [
            {
                "bucket": "home",
                "minutes": 36,
                "fga": 22,
                "fta": 8,
                "tov": 5,
                "reb": 11,
                "ast": 9,
                "fgm": 11,
                "team_minutes": 240,
                "team_fga": 86,
                "team_fta": 22,
                "team_tov": 11,
                "team_fgm": 42,
                "team_reb": 48,
                "opp_reb": 40,
            },
            {
                "bucket": "home",
                "minutes": 35,
                "fga": 21,
                "fta": 7,
                "tov": 4,
                "reb": 10,
                "ast": 8,
                "fgm": 10,
                "team_minutes": 240,
                "team_fga": 84,
                "team_fta": 20,
                "team_tov": 10,
                "team_fgm": 41,
                "team_reb": 47,
                "opp_reb": 39,
            },
            {
                "bucket": "away",
                "minutes": 37,
                "fga": 16,
                "fta": 3,
                "tov": 2,
                "reb": 14,
                "ast": 6,
                "fgm": 7,
                "team_minutes": 240,
                "team_fga": 80,
                "team_fta": 14,
                "team_tov": 13,
                "team_fgm": 35,
                "team_reb": 52,
                "opp_reb": 46,
            },
            {
                "bucket": "away",
                "minutes": 38,
                "fga": 15,
                "fta": 2,
                "tov": 2,
                "reb": 15,
                "ast": 5,
                "fgm": 7,
                "team_minutes": 240,
                "team_fga": 79,
                "team_fta": 15,
                "team_tov": 14,
                "team_fgm": 34,
                "team_reb": 53,
                "opp_reb": 45,
            },
        ]
    )

    out = (
        compute_grouped_sample_advanced_metrics(df, "bucket")
        .sort_values("bucket")
        .reset_index(drop=True)
    )

    assert list(out["bucket"]) == ["away", "home"]
    assert out.loc[0, "usg_pct_avg"] != out.loc[1, "usg_pct_avg"]
    assert out.loc[0, "ast_pct_avg"] != out.loc[1, "ast_pct_avg"]
    assert out.loc[0, "reb_pct_avg"] != out.loc[1, "reb_pct_avg"]


def test_compute_season_grouped_sample_advanced_metrics_returns_per_season_values():
    df = pd.DataFrame(
        [
            {
                "season": "2024-25",
                "minutes": 36,
                "fga": 20,
                "fta": 6,
                "tov": 4,
                "reb": 12,
                "ast": 8,
                "fgm": 10,
                "team_minutes": 240,
                "team_fga": 85,
                "team_fta": 20,
                "team_tov": 12,
                "team_fgm": 40,
                "team_reb": 50,
                "opp_reb": 44,
            },
            {
                "season": "2025-26",
                "minutes": 36,
                "fga": 15,
                "fta": 4,
                "tov": 2,
                "reb": 14,
                "ast": 5,
                "fgm": 7,
                "team_minutes": 240,
                "team_fga": 78,
                "team_fta": 16,
                "team_tov": 14,
                "team_fgm": 33,
                "team_reb": 52,
                "opp_reb": 46,
            },
        ]
    )

    out = compute_season_grouped_sample_advanced_metrics(df)
    assert list(out["season"]) == ["2024-25", "2025-26"]
    assert len(out) == 2
    assert out.loc[0, "usg_pct_avg"] != out.loc[1, "usg_pct_avg"]
