from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from nbatools.deployment_monitoring import (
    MAX_SMOKE_RESPONSE_BYTES,
    ResponseTooLargeError,
    default_smoke_cases,
    fetch_http,
    normalize_base_url,
    run_deployment_smoke,
)


def test_fetch_http_rejects_response_over_safe_limit(monkeypatch) -> None:
    class OversizedResponse:
        status = 200
        headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            del exc_type, exc, traceback

        def read(self, amount: int) -> bytes:
            assert amount == MAX_SMOKE_RESPONSE_BYTES + 1
            return b"x" * amount

    monkeypatch.setattr(
        "nbatools.deployment_monitoring.request.urlopen",
        lambda request, timeout: OversizedResponse(),
    )

    with pytest.raises(ResponseTooLargeError, match="safe smoke-monitoring limit"):
        fetch_http("https://deploy.example/health", "GET", None, 2.0)


def test_normalize_base_url_trims_whitespace_and_slash() -> None:
    assert normalize_base_url(" https://example.com/path/ ") == "https://example.com/path"


def test_default_smoke_cases_cover_expected_routes() -> None:
    cases = default_smoke_cases()

    assert [case.slug for case in cases] == [
        "root",
        "health",
        "freshness",
        "readiness",
        "query_jokic_last_10",
        "query_top_10_scorers_2025_26",
        "query_jokic_multi_filter",
        "query_celtics_record_against_east_current",
    ]
    assert cases[3].expected_json_fields == {"ready": True, "status": "ready"}
    assert cases[4].expected_json_fields["route"] == "player_game_summary"
    assert cases[5].expected_json_fields["route"] == "season_leaders"
    assert cases[7].expected_json_fields["result.metadata.opponent_conference"] == "East"
    assert cases[7].expected_json_fields["result.metadata.opponent_team_abbrs.__len__"] == 15


def test_run_deployment_smoke_reports_successful_cases() -> None:
    responses = {
        ("GET", "https://deploy.example/"): (
            200,
            {"content-type": "text/html; charset=utf-8", "x-vercel-cache": "HIT"},
            b"<html><head><title>nbatools</title></head><body><div id='root'></div></body></html>",
        ),
        ("GET", "https://deploy.example/health"): (
            200,
            {
                "content-type": "application/json",
                "x-vercel-cache": "MISS",
                "x-request-id": "req_health",
            },
            b'{"status":"ok","version":"0.7.0"}',
        ),
        ("GET", "https://deploy.example/freshness"): (
            200,
            {"content-type": "application/json", "x-vercel-cache": "MISS"},
            b'{"status":"stale","current_through":"2026-04-04","seasons":[{"season":"2025-26"}]}',
        ),
        ("GET", "https://deploy.example/readiness"): (
            200,
            {"content-type": "application/json", "x-vercel-cache": "MISS"},
            b'{"ready":true,"status":"ready","season_state":"offseason","active_generation":"release-1","immutable_generation":true,"blockers":[]}',
        ),
        ("POST", "https://deploy.example/query", "Jokic last 10"): (
            200,
            {"content-type": "application/json"},
            b'{"ok":true,"route":"player_game_summary","result_status":"ok","query_class":"summary"}',
        ),
        ("POST", "https://deploy.example/query", "top 10 scorers 2025-26"): (
            200,
            {"content-type": "application/json"},
            b'{"ok":true,"route":"season_leaders","result_status":"ok","query_class":"leaderboard"}',
        ),
        (
            "POST",
            "https://deploy.example/query",
            "Jokic summary (over 25 points and over 10 rebounds) 2025-26",
        ): (
            200,
            {"content-type": "application/json"},
            b'{"ok":true,"route":"player_game_summary","result_status":"ok","query_class":"summary"}',
        ),
        ("POST", "https://deploy.example/query", "Celtics record against the East this season"): (
            200,
            {"content-type": "application/json"},
            json.dumps(
                {
                    "ok": True,
                    "route": "team_record",
                    "result_status": "ok",
                    "query_class": "summary",
                    "result": {
                        "metadata": {
                            "opponent_conference": "East",
                            "opponent_team_abbrs": [
                                "ATL",
                                "BKN",
                                "BOS",
                                "CHA",
                                "CHI",
                                "CLE",
                                "DET",
                                "IND",
                                "MIA",
                                "MIL",
                                "NYK",
                                "ORL",
                                "PHI",
                                "TOR",
                                "WAS",
                            ],
                        }
                    },
                }
            ).encode(),
        ),
    }

    def fake_fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        del timeout
        if method == "POST":
            return responses[(method, url, str(body["query"]))]
        return responses[(method, url)]

    report = run_deployment_smoke("https://deploy.example/", fetcher=fake_fetcher)

    assert report.ok is True
    assert report.failure_count == 0
    assert report.failures == []
    assert report.case_count == 8
    assert report.cases[0].summary["title"] == "nbatools"
    assert report.cases[1].headers["x-request-id"] == "req_health"
    assert report.cases[2].summary["season_count"] == 1
    assert report.cases[3].summary["blocker_count"] == 0
    assert report.cases[7].summary["opponent_conference"] == "East"
    assert report.cases[7].summary["opponent_team_abbrs_count"] == 15


def test_run_deployment_smoke_flags_route_mismatches() -> None:
    responses = {
        ("GET", "https://deploy.example/"): (
            200,
            {"content-type": "text/html; charset=utf-8"},
            b"<html><head><title>nbatools</title></head><body></body></html>",
        ),
        ("GET", "https://deploy.example/health"): (
            200,
            {"content-type": "application/json"},
            b'{"status":"ok"}',
        ),
        ("GET", "https://deploy.example/freshness"): (
            200,
            {"content-type": "application/json"},
            b'{"status":"stale","current_through":"2026-04-04","seasons":[]}',
        ),
        ("GET", "https://deploy.example/readiness"): (
            200,
            {"content-type": "application/json"},
            b'{"ready":true,"status":"ready","blockers":[]}',
        ),
        ("POST", "https://deploy.example/query", "Jokic last 10"): (
            200,
            {"content-type": "application/json"},
            b'{"ok":true,"route":"wrong_route"}',
        ),
        ("POST", "https://deploy.example/query", "top 10 scorers 2025-26"): (
            200,
            {"content-type": "application/json"},
            b'{"ok":true,"route":"season_leaders"}',
        ),
        (
            "POST",
            "https://deploy.example/query",
            "Jokic summary (over 25 points and over 10 rebounds) 2025-26",
        ): (
            200,
            {"content-type": "application/json"},
            b'{"ok":true,"route":"player_game_summary"}',
        ),
        ("POST", "https://deploy.example/query", "Celtics record against the East this season"): (
            200,
            {"content-type": "application/json"},
            json.dumps(
                {
                    "ok": True,
                    "route": "team_record",
                    "result_status": "ok",
                    "result": {
                        "metadata": {
                            "opponent_conference": "East",
                            "opponent_team_abbrs": [
                                "ATL",
                                "BKN",
                                "BOS",
                                "CHA",
                                "CHI",
                                "CLE",
                                "DET",
                                "IND",
                                "MIA",
                                "MIL",
                                "NYK",
                                "ORL",
                                "PHI",
                                "TOR",
                                "WAS",
                            ],
                        }
                    },
                }
            ).encode(),
        ),
    }

    def fake_fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        del timeout
        if method == "POST":
            return responses[(method, url, str(body["query"]))]
        return responses[(method, url)]

    report = run_deployment_smoke("https://deploy.example", fetcher=fake_fetcher)

    assert report.ok is False
    assert report.failure_count == 1
    assert report.failures == ["query_jokic_last_10"]
    assert report.cases[4].error == "route='wrong_route' (expected 'player_game_summary')"
