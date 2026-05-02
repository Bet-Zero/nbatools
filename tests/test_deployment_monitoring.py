from __future__ import annotations

from collections.abc import Mapping

from nbatools.deployment_monitoring import (
    default_smoke_cases,
    normalize_base_url,
    run_deployment_smoke,
)


def test_normalize_base_url_trims_whitespace_and_slash() -> None:
    assert normalize_base_url(" https://example.com/path/ ") == "https://example.com/path"


def test_default_smoke_cases_cover_expected_routes() -> None:
    cases = default_smoke_cases()

    assert [case.slug for case in cases] == [
        "root",
        "health",
        "freshness",
        "query_jokic_last_10",
        "query_top_10_scorers_2025_26",
        "query_jokic_multi_filter",
    ]
    assert cases[3].expected_json_fields["route"] == "player_game_summary"
    assert cases[4].expected_json_fields["route"] == "season_leaders"


def test_run_deployment_smoke_reports_successful_cases() -> None:
    responses = {
        ("GET", "https://deploy.example/"): (
            200,
            {"content-type": "text/html; charset=utf-8", "x-vercel-cache": "HIT"},
            b"<html><head><title>nbatools</title></head><body><div id='root'></div></body></html>",
        ),
        ("GET", "https://deploy.example/health"): (
            200,
            {"content-type": "application/json", "x-vercel-cache": "MISS"},
            b'{"status":"ok","version":"0.7.0"}',
        ),
        ("GET", "https://deploy.example/freshness"): (
            200,
            {"content-type": "application/json", "x-vercel-cache": "MISS"},
            b'{"status":"stale","current_through":"2026-04-04","seasons":[{"season":"2025-26"}]}',
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
    assert report.case_count == 6
    assert report.cases[0].summary["title"] == "nbatools"
    assert report.cases[2].summary["season_count"] == 1


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
    assert report.cases[3].error == "route='wrong_route' (expected 'player_game_summary')"
