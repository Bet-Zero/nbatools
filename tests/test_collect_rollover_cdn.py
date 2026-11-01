"""One public request, strict identity scope, preserved originals and no inferred facts."""

import hashlib
import json

import pytest

from tools import collect_rollover_cdn as collector


class Response:
    def __init__(self, raw, status=200):
        self.raw = raw
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise collector.requests.HTTPError("public fixture rejection")

    def iter_content(self, size):
        yield self.raw


def payload():
    def team(ident, abbr, score, pid):
        return dict(
            teamId=ident,
            teamTricode=abbr,
            score=score,
            players=[dict(personId=pid, firstName="Fixture", familyName=abbr)],
        )

    return dict(
        game=dict(
            gameId="0022600144",
            gameStatus=3,
            gameTimeUTC="2026-10-30T00:00:00Z",
            homeTeam=team(1610612737, "ATL", 114, 1),
            awayTeam=team(1610612739, "CLE", 111, 2),
        )
    )


@pytest.mark.parametrize(
    "damage", [None, "wrong_game", "wrong_score", "oversized", "http403", "timeout"]
)
def test_capture_cannot_cross_fixed_scope_or_infer_statistical_acceptance(
    tmp_path, monkeypatch, damage
):
    body = payload()
    if damage == "wrong_game":
        body["game"]["gameId"] = "0022600001"
    elif damage == "wrong_score":
        body["game"]["homeTeam"]["score"] = 113
    raw = b"x" * 2_000_001 if damage == "oversized" else json.dumps(body).encode()
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        if damage == "timeout":
            raise collector.requests.ReadTimeout("fixture")
        return Response(raw, status=403 if damage == "http403" else 200)

    monkeypatch.setattr(collector.requests, "get", get)
    output = tmp_path / "capture"
    if damage:
        with pytest.raises((ValueError, collector.requests.RequestException)):
            collector.collect_missing_boxscore(output)
        assert not (output / "receipt.json").exists()
        assert not (output / "boxscore_0022600144.json").exists()
    else:
        report = collector.collect_missing_boxscore(output)
        assert (output / report["source_file"]).read_bytes() == raw
        assert report["source_sha256"] == hashlib.sha256(raw).hexdigest()
        assert report["statistical_qualification"] == "pending_independent_original_rows"
        assert report["production_writes"] == 0
        with pytest.raises(FileExistsError):
            collector.collect_missing_boxscore(output)
    assert calls == [(collector.URL, dict(timeout=20, stream=True))]
    attempt = json.loads((output / "capture-attempt.json").read_text())
    assert attempt["attempts"] == 1 and attempt["production_writes"] == 0
    assert attempt["source_url"] == collector.URL and attempt["game_id"] == "0022600144"
    assert attempt["identity_scope_qualified"] is (damage is None)
    if damage:
        assert attempt["error_type"]
        if damage == "timeout":
            assert attempt["http_status"] is None and attempt["response_bytes"] == 0
        else:
            retained = (output / "unqualified-response.bin").read_bytes()
            assert len(retained) <= 2_000_000
            assert attempt["response_sha256"] == hashlib.sha256(retained).hexdigest()
            assert attempt["http_status"] == (403 if damage == "http403" else 200)
