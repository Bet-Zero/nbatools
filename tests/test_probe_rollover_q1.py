"""The bounded quarter experiment must reject zero/full-game and retain failures."""

import copy
import hashlib
import json

import pytest
import requests

from tools import probe_rollover_q1 as collector


def sample():
    oracle = dict(game_id=collector.GAME, teams={})
    traditional = dict(gameId=collector.GAME)
    advanced = dict(gameId=collector.GAME)
    for index, side in enumerate(["homeTeam", "awayTeam"]):
        ident = index + 1
        points = [10, 7 + index, 4, 4, 2]
        oracle["teams"][side] = dict(team_id=ident, points=sum(points), full_points=121 - index * 8)
        players = [
            dict(personId=ident * 100 + i, statistics=dict(minutes="12:00", points=p))
            for i, p in enumerate(points)
        ]
        traditional[side] = dict(
            teamId=ident, statistics=dict(minutes="60:00", points=sum(points)), players=players
        )
        rate_players = copy.deepcopy(players)
        for player in rate_players:
            player["statistics"].update(
                usagePercentage=0.2, assistPercentage=0.1, reboundPercentage=0.2, turnoverRatio=10
            )
        advanced[side] = dict(teamId=ident, statistics=dict(minutes="60:00"), players=rate_players)
    return {"boxScoreTraditional": traditional}, {"boxScoreAdvanced": advanced}, oracle


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "zero",
        "full",
        "wrong_game",
        "wrong_side",
        "clock",
        "missing",
        "duplicate",
        "bad_rate",
        "rate_clock",
        "player_points",
    ],
)
def test_qualifies_only_independently_scoped_quarter(damage):
    traditional, advanced, oracle = sample()
    team = traditional["boxScoreTraditional"]["homeTeam"]
    rates = advanced["boxScoreAdvanced"]["homeTeam"]
    if damage == "zero":
        team["statistics"].update(minutes="0:00", points=0)
    elif damage == "full":
        team["statistics"].update(minutes="240:00", points=121)
    elif damage == "wrong_game":
        advanced["boxScoreAdvanced"]["gameId"] = "0022600002"
    elif damage == "wrong_side":
        rates["teamId"] = 2
    elif damage == "clock":
        team["players"][0]["statistics"]["minutes"] = "13:00"
    elif damage == "missing":
        rates["players"].pop()
    elif damage == "duplicate":
        team["players"].append(copy.deepcopy(team["players"][0]))
    elif damage == "bad_rate":
        rates["players"][0]["statistics"]["usagePercentage"] = float("nan")
    elif damage == "rate_clock":
        rates["players"][0]["statistics"]["minutes"] = "11:00"
    elif damage == "player_points":
        team["players"][0]["statistics"]["points"] += 1
    if damage:
        with pytest.raises(ValueError):
            collector.qualify_quarter(traditional, advanced, oracle)
    else:
        result = collector.qualify_quarter(traditional, advanced, oracle)
        assert [row["q1_points"] for row in result] == [27, 28]
        assert all(
            row["team_minutes"] == 60 and len(row["played_player_ids"]) == 5 for row in result
        )


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


@pytest.mark.parametrize("damage", [None, "timeout", "403", "oversized", "second_timeout", "zero"])
def test_one_attempt_exact_parameters_and_preserved_failure(tmp_path, monkeypatch, damage):
    traditional, advanced, oracle = sample()
    if damage == "zero":
        traditional["boxScoreTraditional"]["homeTeam"]["statistics"]["points"] = 0
    documents = [traditional, advanced]
    calls = []
    headers = {"User-Agent": "unchanged library fixture"}

    class HTTP:
        base_url = "https://stats.nba.com/stats/{endpoint}"

        def get_session(self):
            return self

        def get(self, **kwargs):
            index = len(calls)
            calls.append(kwargs)
            if damage == "timeout" or damage == "second_timeout" and index == 1:
                raise requests.ReadTimeout("fixture")
            raw = json.dumps(documents[index]).encode()
            if damage == "403":
                raw = b"public forbidden fixture"
            if damage == "oversized":
                raw = b"x" * 2_000_001
            return Response(raw, 403 if damage == "403" else 200)

    HTTP.headers = headers
    monkeypatch.setattr(collector, "NBAStatsHTTP", HTTP)
    monkeypatch.setattr(collector, "load_oracle", lambda evidence: oracle)
    output = tmp_path / "probe"
    if damage:
        with pytest.raises((ValueError, requests.RequestException)):
            collector.probe(output, tmp_path)
    else:
        report = collector.probe(output, tmp_path)
        assert report["source_scope_qualified"] is True
        with pytest.raises(FileExistsError):
            collector.probe(output, tmp_path)
    report = json.loads((output / "capture-attempt.json").read_text())
    assert report["production_writes"] == 0 and report["canonical_period_accepted"] is False
    assert report["source_scope_qualified"] is (damage is None)
    assert len(calls) == (1 if damage in {"timeout", "403", "oversized"} else 2)
    for call, attempt in zip(calls, report["captures"], strict=True):
        assert dict(call["params"]) == dict(
            GameID=collector.GAME,
            StartPeriod=1,
            EndPeriod=1,
            RangeType=1,
            StartRange=0,
            EndRange=28800,
        )
        assert call["timeout"] == 30 and call["stream"] is True and call["headers"] == headers
        assert set(call) == {"url", "params", "headers", "timeout", "stream"}
        assert attempt["attempts"] == 1
        if attempt["response_file"]:
            raw = (output / attempt["response_file"]).read_bytes()
            assert len(raw) <= 2_000_000 and len(raw) == attempt["response_bytes"]
            assert hashlib.sha256(raw).hexdigest() == attempt["response_sha256"]
    if damage:
        assert report["error_type"]
    if damage in {"timeout", "second_timeout"}:
        assert report["captures"][-1]["http_status"] is None
        assert report["captures"][-1]["error_type"] == "ReadTimeout"
    if damage == "403":
        assert report["captures"][0]["http_status"] == 403
    if damage == "oversized":
        assert report["captures"][0]["response_truncated"] is True
