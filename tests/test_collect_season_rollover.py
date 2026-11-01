"""Fixed source scope, whole-body integrity and schedule-state preservation."""

import copy
import hashlib
import json

import pytest

from tools import collect_season_rollover as collector


def document():
    return dict(
        leagueSchedule=dict(
            seasonYear="2026-27",
            leagueId="00",
            gameDates=[
                dict(
                    games=[
                        dict(
                            gameId="0022600001",
                            gameStatus=3,
                            gameDateEst="2026-10-20T00:00:00Z",
                            homeTeam=dict(teamId=1),
                            awayTeam=dict(teamId=2),
                        ),
                        dict(
                            gameId="0022600002",
                            gameStatus=1,
                            gameDateEst="2027-01-01T00:00:00Z",
                            homeTeam=dict(teamId=0),
                            awayTeam=dict(teamId=0),
                        ),
                    ]
                )
            ],
        )
    )


def test_one_capture_preserves_original_future_and_final_population(tmp_path, monkeypatch):
    raw = json.dumps(document()).encode()
    calls = []

    def fetch(path, destination, revision):
        calls.append((path, revision))
        destination.write_bytes(raw)
        return dict(url="retained fixture", bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    monkeypatch.setattr(collector, "fetch_capture", fetch)
    monkeypatch.setattr(collector, "BYTES", len(raw))
    monkeypatch.setattr(
        collector, "BLOB", hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    )
    output = tmp_path / "capture"
    report = collector.collect_schedule(output)
    assert calls == [(collector.PATH, collector.REVISION)]
    assert (output / report["source_file"]).read_bytes() == raw
    assert report["schedule"]["regular_games"] == 2
    assert report["schedule"]["unresolved_matchups"] == 1
    assert report["observed_final_game_ids"] == ["0022600001"]
    assert [row["game_status"] for row in report["observed_regular_games"]] == [3, 1]
    assert report["independent_schedule_completeness"] == "not_established"
    assert report["production_writes"] == 0
    with pytest.raises(FileExistsError):
        collector.collect_schedule(output)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "damage", ["old_season", "duplicate", "bad_date", "negative_team", "final_tbd", "status_type"]
)
def test_invalid_source_population_cannot_qualify_by_filename(damage):
    doc = document()
    games = doc["leagueSchedule"]["gameDates"][0]["games"]
    if damage == "old_season":
        doc["leagueSchedule"]["seasonYear"] = "2025-26"
    elif damage == "duplicate":
        games.append(copy.deepcopy(games[0]))
    elif damage == "bad_date":
        games[0]["gameDateEst"] = "not-a-date"
    elif damage == "negative_team":
        games[0]["homeTeam"]["teamId"] = -1
    elif damage == "final_tbd":
        games[1]["gameStatus"] = 3
    elif damage == "status_type":
        games[1]["gameStatus"] = True
    with pytest.raises(ValueError):
        collector.schedule_population(doc)


@pytest.mark.parametrize("damage", ["size", "blob", "hash"])
def test_changed_original_is_retained_but_not_qualified(tmp_path, monkeypatch, damage):
    raw = json.dumps(document()).encode()

    def fetch(path, destination, revision):
        destination.write_bytes(raw)
        return dict(sha256="bad" if damage == "hash" else hashlib.sha256(raw).hexdigest())

    monkeypatch.setattr(collector, "fetch_capture", fetch)
    if damage != "size":
        monkeypatch.setattr(collector, "BYTES", len(raw))
    if damage != "blob":
        monkeypatch.setattr(
            collector, "BLOB", hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        )
    output = tmp_path / "capture"
    with pytest.raises(ValueError, match="immutable archive metadata"):
        collector.collect_schedule(output)
    assert (output / "scheduleleaguev2-2027.json").exists()
    assert not (output / "receipt.json").exists()
