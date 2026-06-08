import pytest

from nbatools.query_output_snapshot import build_query_ui_snapshot

pytestmark = pytest.mark.output


def _snapshot_payload(
    *,
    route: str,
    query: str,
    metadata: dict,
    row: dict,
) -> dict:
    return {
        "ok": True,
        "query": query,
        "route": route,
        "result_status": "ok",
        "result_reason": None,
        "result": {
            "query_class": "leaderboard",
            "metadata": {"query_text": query, "route": route, **metadata},
            "notes": [],
            "caveats": [],
            "sections": {"leaderboard": [row]},
        },
    }


def test_top_player_performance_snapshot_uses_metric_sentence_and_columns():
    snapshot = build_query_ui_snapshot(
        _snapshot_payload(
            route="top_player_games",
            query="most assists in a game this season",
            metadata={"stat": "ast", "season": "2025-26", "season_type": "Regular Season"},
            row={
                "rank": 1,
                "player_name": "Ryan Nembhard",
                "team_abbr": "DAL",
                "game_date": "2026-04-12",
                "opponent_team_abbr": "CHI",
                "wl": "W",
                "ast": 23,
                "pts": 15,
                "reb": 9,
            },
        )
    )

    rendered = snapshot["rendered_output"]
    assert rendered["answer"]["text"] == (
        "Ryan Nembhard had the top assist game this season with 23 assists "
        "in a win against CHI on Apr 12."
    )
    block = rendered["blocks"][0]
    assert block["table_type"] == "top_performances"
    assert block["subject"] == "Players"
    assert block["mode"] == "single-game player performances"
    assert block["visible_columns"] == [
        "Rank",
        "Player",
        "Team",
        "Date",
        "Opp",
        "W/L",
        "AST",
        "PTS",
        "REB",
    ]


def test_top_team_performance_snapshot_shows_score_and_margin_context():
    snapshot = build_query_ui_snapshot(
        _snapshot_payload(
            route="top_team_games",
            query="top team scoring games this season",
            metadata={"stat": "pts", "season": "2025-26", "season_type": "Regular Season"},
            row={
                "rank": 1,
                "team_name": "Denver Nuggets",
                "team_abbr": "DEN",
                "game_date": "2026-02-20",
                "opponent_team_abbr": "POR",
                "wl": "W",
                "pts": 157,
                "opponent_pts": 103,
                "reb": 60,
                "ast": 41,
            },
        )
    )

    rendered = snapshot["rendered_output"]
    assert rendered["answer"]["text"] == (
        "Denver Nuggets had the top scoring game this season with 157 points "
        "in a 157-103 win against POR on Feb 20."
    )
    block = rendered["blocks"][0]
    assert block["table_type"] == "top_performances"
    assert block["subject"] == "Teams"
    assert block["mode"] == "single-game team performances"
    assert block["visible_columns"] == [
        "Rank",
        "Team",
        "Date",
        "Opp",
        "W/L",
        "Score",
        "PTS",
        "Opp PTS",
        "Margin",
        "REB",
        "AST",
    ]
    assert block["rows"][0][5:9] == ["157-103", "157", "103", "54"]
