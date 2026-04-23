from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from nbatools.api import app as api_app
from nbatools.cli import app as cli_app

AlternateExpectation = Literal["optional", "empty", "nonempty"]


@dataclass(frozen=True, slots=True)
class QuerySmokeCase:
    query: str
    expected_routes: tuple[str, ...]
    expected_query_class: str
    expected_statuses: tuple[str, ...] = ("ok",)
    expected_intents: tuple[str, ...] | None = None
    expected_note_substrings: tuple[str, ...] = ()
    alternates: AlternateExpectation = "optional"


CLUTCH_NOTE_SUBSTRINGS = ("clutch", "unfiltered")
QUARTER_NOTE_SUBSTRINGS = ("quarter", "unfiltered")
HALF_NOTE_SUBSTRINGS = ("half", "unfiltered")
BACK_TO_BACK_NOTE_SUBSTRINGS = ("back_to_back", "unfiltered")
REST_NOTE_SUBSTRINGS = ("rest", "unfiltered")
ONE_POSSESSION_NOTE_SUBSTRINGS = ("one_possession", "unfiltered")
NATIONAL_TV_NOTE_SUBSTRINGS = ("national_tv", "unfiltered")
STARTER_NOTE_SUBSTRINGS = ("starter", "unfiltered")
BENCH_NOTE_SUBSTRINGS = ("bench", "unfiltered")
OPPONENT_QUALITY_NOTE_SUBSTRINGS = ("opponent_quality",)
ON_OFF_NOTE_SUBSTRINGS = ("on_off", "placeholder")
LINEUP_NOTE_SUBSTRINGS = ("lineup", "placeholder")

STABLE_QUERY_SMOKE_CASES = (
    QuerySmokeCase(
        query="Jokic last 10",
        expected_routes=("player_game_summary",),
        expected_query_class="summary",
        expected_intents=("summary",),
    ),
    QuerySmokeCase(
        query="top scorers this season",
        expected_routes=("season_leaders",),
        expected_query_class="leaderboard",
        expected_intents=("leaderboard",),
    ),
    QuerySmokeCase(
        query="Lakers vs Celtics all-time record",
        expected_routes=("team_matchup_record",),
        expected_query_class="comparison",
        expected_intents=("comparison",),
    ),
    QuerySmokeCase(
        query="how many Jokic games with 30+ points and 10+ rebounds since 2021",
        expected_routes=("player_occurrence_leaders",),
        expected_query_class="count",
        expected_intents=("leaderboard",),
    ),
    QuerySmokeCase(
        query="Curry 5+ threes this season",
        expected_routes=("player_game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
    ),
)

PHASE_D_QUERY_SMOKE_CASES = (
    QuerySmokeCase(
        query="Celtics recently",
        expected_routes=("game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
    ),
    QuerySmokeCase(
        query="Tatum vs Knicks",
        expected_routes=("player_game_finder",),
        expected_query_class="finder",
        expected_statuses=("no_result",),
        expected_intents=("finder",),
        alternates="nonempty",
    ),
    QuerySmokeCase(
        query="Jokic triple doubles",
        expected_routes=("player_game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
    ),
    QuerySmokeCase(
        query="best games Booker",
        expected_routes=("player_game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
    ),
    QuerySmokeCase(
        query="Lakers this season",
        expected_routes=("game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
    ),
)

PHASE_E_QUERY_SMOKE_CASES = (
    QuerySmokeCase(
        query="Tatum clutch stats",
        expected_routes=("player_game_summary",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=CLUTCH_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Lakers clutch record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=CLUTCH_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="best clutch scorers",
        expected_routes=("season_leaders",),
        expected_query_class="leaderboard",
        expected_intents=("leaderboard",),
        expected_note_substrings=CLUTCH_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="late-game Brunson scoring",
        expected_routes=("player_game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
        expected_note_substrings=CLUTCH_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Lakers on back-to-backs record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
    ),
    QuerySmokeCase(
        query="Jokic summary with rest advantage",
        expected_routes=("player_game_summary",),
        expected_query_class="summary",
        expected_intents=("summary",),
    ),
    QuerySmokeCase(
        query="Celtics one-possession record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
    ),
    QuerySmokeCase(
        query="Knicks on national TV record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
    ),
    QuerySmokeCase(
        query="Jokic against contenders 2024-25",
        expected_routes=("player_game_summary",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=OPPONENT_QUALITY_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Lakers record against top-10 defenses 2024-25",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=OPPONENT_QUALITY_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Jokic on/off",
        expected_routes=("player_on_off",),
        expected_query_class="summary",
        expected_statuses=("no_result",),
        expected_intents=("on_off",),
        expected_note_substrings=ON_OFF_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Nuggets without Jokic on the floor",
        expected_routes=("player_on_off",),
        expected_query_class="summary",
        expected_statuses=("no_result",),
        expected_intents=("on_off",),
        expected_note_substrings=ON_OFF_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="best 5-man lineups this season",
        expected_routes=("lineup_leaderboard",),
        expected_query_class="leaderboard",
        expected_statuses=("no_result",),
        expected_intents=("lineup",),
        expected_note_substrings=LINEUP_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="lineup with Tatum and Jaylen Brown",
        expected_routes=("lineup_summary",),
        expected_query_class="summary",
        expected_statuses=("no_result",),
        expected_intents=("lineup",),
        expected_note_substrings=LINEUP_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="hottest 3-game scoring stretch this year",
        expected_routes=("player_stretch_leaderboard",),
        expected_query_class="leaderboard",
        expected_intents=("leaderboard",),
    ),
    QuerySmokeCase(
        query="best 5-game stretch by Game Score",
        expected_routes=("player_stretch_leaderboard",),
        expected_query_class="leaderboard",
        expected_intents=("leaderboard",),
    ),
)

PHASE_G_QUERY_SMOKE_CASES = (
    QuerySmokeCase(
        query="Jokic in the clutch this season",
        expected_routes=("player_game_summary",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=CLUTCH_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="LeBron 4th quarter scoring",
        expected_routes=("player_game_finder",),
        expected_query_class="finder",
        expected_intents=("finder",),
        expected_note_substrings=QUARTER_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Celtics first half record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=HALF_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Knicks OT record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
        expected_note_substrings=QUARTER_NOTE_SUBSTRINGS,
    ),
    QuerySmokeCase(
        query="Lakers on back-to-backs record",
        expected_routes=("team_record",),
        expected_query_class="summary",
        expected_intents=("summary",),
    ),
)

PHASE_QUERY_SMOKE_CASES = (
    PHASE_D_QUERY_SMOKE_CASES + PHASE_E_QUERY_SMOKE_CASES + PHASE_G_QUERY_SMOKE_CASES
)

CLI_RUNNER = CliRunner()
API_CLIENT = TestClient(api_app)


def case_id(case: QuerySmokeCase) -> str:
    return re.sub(r"[^a-z0-9]+", "-", case.query.lower()).strip("-")


def run_cli_query_smoke(case: QuerySmokeCase, tmp_path: Path) -> tuple[str, dict]:
    json_path = tmp_path / f"{case_id(case)}.json"
    result = CLI_RUNNER.invoke(cli_app, ["ask", case.query, "--json", str(json_path)])

    assert result.exit_code == 0, result.output
    assert json_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return result.stdout, payload


def assert_cli_query_smoke(case: QuerySmokeCase, stdout: str, payload: dict) -> None:
    assert stdout.strip()
    assert isinstance(payload, dict)

    metadata = payload.get("metadata")
    assert isinstance(metadata, dict)
    assert metadata.get("query_text") == case.query
    assert metadata.get("route") in case.expected_routes
    assert metadata.get("query_class") == case.expected_query_class

    result_status = metadata.get("result_status", "ok")
    assert result_status in case.expected_statuses

    if result_status == "ok":
        section_keys = [key for key in payload if key != "metadata"]
        assert section_keys
    elif result_status == "error":
        assert metadata.get("result_reason")
        assert "error" in payload
    else:
        assert metadata.get("result_reason")
        assert "no_result" in payload

    if case.expected_note_substrings:
        note_text = " ".join(metadata.get("notes") or []).lower()
        for fragment in case.expected_note_substrings:
            assert fragment.lower() in note_text


def run_api_query_smoke(case: QuerySmokeCase) -> dict:
    response = API_CLIENT.post("/query", json={"query": case.query})

    assert response.status_code == 200, response.text
    return response.json()


def assert_api_query_smoke(case: QuerySmokeCase, body: dict) -> None:
    assert isinstance(body, dict)
    for key in (
        "ok",
        "query",
        "route",
        "result_status",
        "result",
        "confidence",
        "intent",
        "alternates",
    ):
        assert key in body

    assert body["query"] == case.query
    assert body["route"] in case.expected_routes
    assert body["result_status"] in case.expected_statuses
    assert isinstance(body["result"], dict)
    assert body["result"].get("query_class") == case.expected_query_class

    sections = body["result"].get("sections")
    assert isinstance(sections, dict)
    if body["result_status"] == "ok":
        assert body["ok"] is True
        assert sections
    else:
        assert body["ok"] is False
        assert body.get("result_reason")

    assert isinstance(body["confidence"], (int, float))
    assert 0.0 <= float(body["confidence"]) <= 1.0

    if case.expected_intents is None:
        assert body["intent"] is not None
    else:
        assert body["intent"] in case.expected_intents

    alternates = body["alternates"]
    assert isinstance(alternates, list)
    if case.alternates == "empty":
        assert alternates == []
    elif case.alternates == "nonempty":
        assert alternates

    for alternate in alternates:
        assert alternate.get("intent")
        assert alternate.get("route")
        assert alternate.get("description")
        confidence = alternate.get("confidence")
        assert isinstance(confidence, (int, float))
        assert 0.0 <= float(confidence) <= 1.0
