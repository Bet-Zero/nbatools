"""Delivered identity and record-basis controls for K12's confirmed gaps."""

import pandas as pd
import pytest

from nbatools import query_service as service
from nbatools.commands._parse_helpers import detect_wins_losses
from nbatools.commands.structured_results import SummaryResult


@pytest.mark.parametrize("structured", [False, True])
def test_summary_context_matches_selected_same_name_player(monkeypatch, structured):
    monkeypatch.setattr(
        service,
        "_resolve_player_context",
        lambda value: {"player_id": 201607, "player_name": "Patrick Ewing"},
    )
    result = SummaryResult(
        summary=pd.DataFrame([{"player_name": "Patrick Ewing", "games": 2, "pts_avg": 20}]),
        game_log=pd.DataFrame(
            [
                {"player_id": 121, "player_name": "Patrick Ewing", "pts": 19},
                {"player_id": 121, "player_name": "Patrick Ewing", "pts": 21},
            ]
        ),
    )
    if structured:
        monkeypatch.setattr(service, "_execute_build_result", lambda *args, **kwargs: result)
        answer = service.execute_structured_query(
            "player_game_summary", player="Patrick Ewing", season="1996-97"
        )
    else:
        answer = service._finalize_natural_query_result(
            result,
            {
                "route": "player_game_summary",
                "player": "Patrick Ewing",
                "season": "1996-97",
                "route_kwargs": {"player": "Patrick Ewing", "season": "1996-97"},
            },
            "Patrick Ewing stats in 1996-97",
            grouped_boolean_used=False,
        )
    assert answer.metadata["player_context"] == {"player_id": 121, "player_name": "Patrick Ewing"}
    assert answer.result is result and result.summary.pts_avg.iloc[0] == 20


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Celtics win-loss record against Knicks in 2023-24", (False, False)),
        ("Celtics win loss record in games they won", (True, False)),
        ("Celtics win-loss record in games they lost", (False, True)),
        ("Celtics games they win and lose", (True, False)),
        ("Celtics wins and losses against Knicks", (True, True)),
    ],
)
def test_record_basis_is_distinct_from_outcome_filter(query, expected):
    assert detect_wins_losses(query.lower()) == expected
