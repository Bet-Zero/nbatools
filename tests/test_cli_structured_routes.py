from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import typer
from typer.testing import CliRunner

from nbatools.cli_apps import queries
from nbatools.query_service import VALID_ROUTES

runner = CliRunner()


def _install_fake_route_runner(monkeypatch) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def fake_execute_structured_query(route: str, **kwargs: Any):
        calls["execute"] = {"route": route, "kwargs": kwargs}
        return SimpleNamespace(query=f"structured:{route}")

    def fake_render_query_result(
        qr,
        query: str,
        *,
        pretty: bool,
        export_csv_path: str | None,
        export_txt_path: str | None,
        export_json_path: str | None,
    ) -> None:
        calls["render"] = {
            "qr": qr,
            "query": query,
            "pretty": pretty,
            "export_csv_path": export_csv_path,
            "export_txt_path": export_txt_path,
            "export_json_path": export_json_path,
        }
        typer.echo(f"rendered {query}")

    monkeypatch.setattr(queries, "execute_structured_query", fake_execute_structured_query)
    monkeypatch.setattr(queries, "render_query_result", fake_render_query_result)
    return calls


def test_query_routes_lists_every_valid_route():
    result = runner.invoke(queries.app, ["routes"])

    assert result.exit_code == 0
    listed_routes = [line.strip() for line in result.output.splitlines() if line.strip()]
    assert listed_routes == sorted(VALID_ROUTES)


def test_query_routes_details_lists_route_guidance():
    result = runner.invoke(queries.app, ["routes", "--details"])

    assert result.exit_code == 0
    assert "team_record:" in result.output
    assert "required: team" in result.output


def test_query_route_help_displays_representative_route_metadata():
    result = runner.invoke(queries.app, ["route-help", "team_record"])

    assert result.exit_code == 0
    assert "team_record" in result.output
    assert "Implementation: nbatools.commands.team_record.build_team_record_result" in result.output
    assert "Required kwargs: team" in result.output
    assert "opponent_conference" in result.output
    assert "--kwargs-json" in result.output


def test_query_route_help_rejects_invalid_route():
    result = runner.invoke(queries.app, ["route-help", "not_a_real_route"])

    assert result.exit_code != 0
    assert "Unknown route 'not_a_real_route'" in result.output


def test_query_route_invokes_representative_valid_route(monkeypatch):
    calls = _install_fake_route_runner(monkeypatch)

    result = runner.invoke(
        queries.app,
        [
            "route",
            "player_game_summary",
            "--kwargs-json",
            '{"player":"Nikola Jokic","last_n":10}',
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == "rendered structured:player_game_summary\n"
    assert calls["execute"] == {
        "route": "player_game_summary",
        "kwargs": {"player": "Nikola Jokic", "last_n": 10},
    }
    assert calls["render"]["query"] == "structured:player_game_summary"
    assert calls["render"]["pretty"] is False


def test_query_route_rejects_invalid_route(monkeypatch):
    calls = _install_fake_route_runner(monkeypatch)

    result = runner.invoke(queries.app, ["route", "not_a_real_route"])

    assert result.exit_code != 0
    assert "Unknown route 'not_a_real_route'" in result.output
    assert "execute" not in calls


def test_query_route_rejects_malformed_kwargs_json(monkeypatch):
    calls = _install_fake_route_runner(monkeypatch)

    result = runner.invoke(
        queries.app,
        ["route", "team_record", "--kwargs-json", "{bad"],
    )

    assert result.exit_code != 0
    assert "--kwargs-json must be valid JSON" in result.output
    assert "execute" not in calls


def test_query_route_rejects_non_object_kwargs_json(monkeypatch):
    calls = _install_fake_route_runner(monkeypatch)

    result = runner.invoke(
        queries.app,
        ["route", "team_record", "--kwargs-json", '["not", "an", "object"]'],
    )

    assert result.exit_code != 0
    assert "--kwargs-json must decode to a JSON object" in result.output
    assert "execute" not in calls


def test_query_route_passes_export_options(monkeypatch, tmp_path):
    calls = _install_fake_route_runner(monkeypatch)
    csv_path = tmp_path / "route.csv"
    txt_path = tmp_path / "route.txt"
    json_path = tmp_path / "route.json"

    result = runner.invoke(
        queries.app,
        [
            "route",
            "season_leaders",
            "--kwargs-json",
            '{"season":"2025-26","stat":"pts","limit":5}',
            "--csv",
            str(csv_path),
            "--txt",
            str(txt_path),
            "--json",
            str(json_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls["execute"] == {
        "route": "season_leaders",
        "kwargs": {"season": "2025-26", "stat": "pts", "limit": 5},
    }
    assert calls["render"]["export_csv_path"] == str(csv_path)
    assert calls["render"]["export_txt_path"] == str(txt_path)
    assert calls["render"]["export_json_path"] == str(json_path)
