"""Standalone acquisition keeps evidence and cannot expand beyond one Q1 game."""

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import requests

from tools import collect_rollover_q1_laptop as collector
from tools.collection_bundle import unpack


def documents():
    traditional = dict(gameId=collector.GAME)
    advanced = dict(gameId=collector.GAME)
    for index, (side, (tid, points, _)) in enumerate(collector.ORACLE.items()):
        players = [
            dict(personId=index * 10 + i + 1, statistics=dict(minutes="12:00", points=p))
            for i, p in enumerate([10, points - 20, 4, 4, 2])
        ]
        traditional[side] = dict(
            teamId=tid, statistics=dict(points=points, minutes="60:00"), players=players
        )
        rates = copy.deepcopy(players)
        for p in rates:
            p["statistics"].update(
                usagePercentage=0.2, assistPercentage=0.1, reboundPercentage=0.2, turnoverRatio=10
            )
        advanced[side] = dict(teamId=tid, statistics=dict(minutes="60:00"), players=rates)
    return dict(boxScoreTraditional=traditional), dict(boxScoreAdvanced=advanced)


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "zero",
        "full",
        "rate_zero",
        "bad_rate",
        "identity",
        "fractional_points",
        "clock",
        "team",
        "game",
    ],
)
def test_quarter_qualification_cannot_accept_activity_or_scope_substitutes(damage):
    a, b = documents()
    team = a["boxScoreTraditional"]["homeTeam"]
    rates = b["boxScoreAdvanced"]["homeTeam"]
    if damage == "zero":
        team["statistics"].update(points=0, minutes="0:00")
    elif damage == "full":
        team["statistics"].update(points=121, minutes="240:00")
    elif damage == "rate_zero":
        for player in rates["players"]:
            player["statistics"]["usagePercentage"] = 0
    elif damage == "bad_rate":
        rates["players"][0]["statistics"]["assistPercentage"] = float("nan")
    elif damage == "identity":
        rates["players"][0]["personId"] = 0
    elif damage == "fractional_points":
        team["players"][0]["statistics"]["points"] = 10.5
    elif damage == "clock":
        team["players"][0]["statistics"]["minutes"] = "13:00"
    elif damage == "team":
        team["teamId"] = 0
    elif damage == "game":
        b["boxScoreAdvanced"]["gameId"] = "0022600002"
    if damage:
        with pytest.raises(ValueError):
            collector.qualify(a, b)
    else:
        checked = collector.qualify(a, b)
        assert [row["points"] for row in checked] == [27, 28]


class Response:
    def __init__(self, raw, status=200):
        self.raw, self.status_code = raw, status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def iter_content(self, size):
        yield self.raw

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("fixture")


@pytest.mark.parametrize(
    "damage", [None, "timeout", "second_timeout", "403", "oversized", "invalid_json", "zero"]
)
def test_exact_one_attempt_and_data_only_archive_preserve_success_or_failure(
    tmp_path, monkeypatch, damage
):
    payloads = documents()
    if damage == "zero":
        payloads[0]["boxScoreTraditional"]["homeTeam"]["statistics"]["points"] = 0
    calls = []

    class HTTP:
        base_url = "https://stats.nba.com/stats/{endpoint}"
        headers = {"User-Agent": "unaltered library fixture"}

        def get_session(self):
            return self

        def get(self, **kwargs):
            index = len(calls)
            calls.append(kwargs)
            if damage == "timeout" or damage == "second_timeout" and index == 1:
                raise requests.ReadTimeout("fixture")
            raw = json.dumps(payloads[index]).encode()
            if damage == "403":
                raw = b"original public403body"
            elif damage == "oversized":
                raw = b"x" * 2_000_001
            elif damage == "invalid_json":
                raw = b"original public nonJSON200body"
            return Response(raw, 403 if damage == "403" else 200)

    class Endpoint:
        def __init__(self, name):
            self.endpoint, self.parameters = name, collector.PARAMETERS.copy()

    monkeypatch.setattr(
        collector,
        "_clients",
        lambda: ((Endpoint(name), HTTP()) for name in collector.REQUEST["endpoints"]),
    )
    output = tmp_path / "capture"
    if damage:
        with pytest.raises((ValueError, requests.RequestException)):
            collector.collect(output)
    else:
        assert collector.collect(output)["source_scope_qualified"] is True
        with pytest.raises(FileExistsError):
            collector.collect(output)
    report = json.loads((output / "acquisition.json").read_text())
    assert report["production_writes"] == 0 and report["canonical_period_accepted"] is False
    assert report["source_scope_qualified"] is (damage is None)
    assert len(calls) == (1 if damage in {"timeout", "403", "oversized", "invalid_json"} else 2)
    for row, call in zip(report["attempts"], calls, strict=True):
        assert dict(call["params"]) == collector.PARAMETERS
        assert call["timeout"] == 30 and call["headers"] == HTTP.headers and call["stream"] is True
        assert row["attempts"] == 1 and row["response_bytes"] <= 2_000_000
        assert call["allow_redirects"] is False
        assert set(call) == {"url", "params", "headers", "timeout", "stream", "allow_redirects"}
    if damage:
        assert report["error_type"]
    destination = tmp_path / "unpacked"
    receipt = unpack(output / "collection.zip", collector.REQUEST, destination)
    assert receipt["state"] == "unvalidated_staging_only"
    for file in (output / "sources").glob("*.json"):
        assert (destination / "sources" / file.name).read_bytes() == file.read_bytes()
    assert not list(destination.rglob("*.py"))


def test_standalone_help_does_not_need_development_checkout_or_site_packages(tmp_path):
    source = Path(collector.__file__)
    copied = tmp_path / source.name
    copied.write_bytes(source.read_bytes())
    response = subprocess.run(
        [sys.executable, "-S", str(copied), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert response.returncode == 0 and "--output" in response.stdout
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(ast.parse(copied.read_text()))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not {"tools", "nbatools"}.intersection(imports)


def test_installed_sdk_constructs_exact_parameters_without_request():
    rows = list(collector._clients())
    assert len(rows) == 2
    assert [e.endpoint for e, _ in rows] == collector.REQUEST["endpoints"]
    assert all(e.parameters == collector.PARAMETERS and http.headers for e, http in rows)
    assert all(
        http.get_session().get_adapter("https://").max_retries.total == 0 for _, http in rows
    )
