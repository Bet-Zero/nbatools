"""Original matchup time/count checks preserve both target-owned predicates."""

import csv
import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _identity, _table

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-ClijrUhz.js", "original-stat-pair-browser"
SOURCE_PATH = (
    Path(__file__).parent / "fixtures/qualified_original_stat_pair/checker_revealed_controls.json"
)
SOURCE = json.loads(SOURCE_PATH.read_text())
SELECTION = "Select the latest original team matchup before checking player minutes and count"
CAVEAT = (
    "The minutes check uses official report time in MM:SS on the selected original game. "
    "The table shows team-game totals, not the checked player's statistics. "
    "An explicit DNP is nonparticipation, not a zero-stat appearance."
)


def _cases():
    assert (
        hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
        == "c617ed72b97afa56815d22ddb61d3794156c05987075f94482588779c6d9d184"
    )
    assert SOURCE["generation"] == "availability-opening-s4-v1-20261017"
    for path, digest in SOURCE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        with data_path(f"raw/{kind}/2023-24_regular_season.csv").open() as stream:
            return list(csv.DictReader(stream))

    games, teams, players, reports = [
        raw(k)
        for k in ["games", "team_game_stats", "player_game_stats", "player_game_availability"]
    ]
    assert len({(r["game_id"], r["team_id"]) for r in teams}) == len(teams)
    cases = []
    specs = [
        ("stat-pair-exact-yes", 0, "LAL", "BOS", "REB", "> 16.0666 minutes", "> 6.99999 REB"),
        ("stat-pair-count-no-reversed", 4, "BOS", "LAL", "AST", ">= 22.65 minutes", ">= 1 AST"),
        ("stat-pair-real-zero", 3, "BOS", "LAL", "AST", ">= 22.65 minutes", "<= 0 AST"),
        ("stat-pair-dnp-no", 5, "LAL", "BOS", "AST", "< 30 minutes", "<= 0 AST"),
        ("stat-pair-time-unavailable", 6, "LAL", "NOP", "AST", ">= 30 minutes", ">= 10 AST"),
    ]
    for ident, index, team, opponent, stat, minutes_description, count_description in specs:
        frozen = SOURCE["cases"][index]
        name, gid, truth = frozen["target"], frozen["original_game_id"], frozen["desired_boolean"]
        candidates = [
            r for r in teams if r["team_abbr"] == team and r["opponent_team_abbr"] == opponent
        ]
        candidates.sort(key=lambda r: (r["game_date"], int(r["game_id"])), reverse=True)
        row = candidates[0]
        assert int(row["game_id"]) == gid
        catalog = [r for r in games if int(r["game_id"]) == gid]
        other = [
            r for r in teams if int(r["game_id"]) == gid and r["team_id"] == row["opponent_team_id"]
        ]
        assert len(catalog) == len(other) == 1 and catalog[0]["is_final"] == "1"
        assert catalog[0]["game_date"] == row["game_date"] == other[0]["game_date"]
        assert {catalog[0]["home_team_id"], catalog[0]["away_team_id"]} == {
            row["team_id"],
            row["opponent_team_id"],
        }
        assert other[0]["opponent_team_id"] == row["team_id"]
        time, actual_count = None, None
        if name in SOURCE["source"]:
            qualified = SOURCE["source"][name]
            report, positive = qualified["report"], qualified["positive"]
            identity = dict(player_id=int(report["player_id"]), player_name=name)
            assert [
                r
                for r in reports
                if int(r["game_id"]) == gid and int(r["player_id"]) == identity["player_id"]
            ] == [report]
            assert [
                r
                for r in players
                if int(r["game_id"]) == gid and int(r["player_id"]) == identity["player_id"]
            ] == [positive]
            assert (
                report["team_id"] == positive["team_id"] == row["team_id"]
                and report["game_date"] == positive["game_date"] == row["game_date"]
            )
            assert (
                report["participation_state"] == "played"
                and report["coverage_scope"] == "listed_player_rows_only"
            )
            assert float(positive["minutes"]) > 0
            time, actual_count = qualified["time"], int(positive[stat.lower()])
            mm, ss = map(int, time.split(":"))
            assert (
                qualified["seconds"] == mm * 60 + ss
                and abs(float(report["source_minutes"]) * 60 - qualified["seconds"]) < 1e-8
            )
        elif name == "Anthony Davis":
            report = SOURCE["explicit_dnp"]
            identity = dict(player_id=int(report["player_id"]), player_name=name)
            assert [
                r
                for r in reports
                if int(r["game_id"]) == gid and int(r["player_id"]) == identity["player_id"]
            ] == [report]
            assert report["team_id"] == row["team_id"] and report["game_date"] == row["game_date"]
            assert (
                report["participation_state"] == "did_not_play"
                and not report["source_minutes"]
                and report["source_comment"]
            )
            assert not [
                r
                for r in players
                if int(r["game_id"]) == gid
                and int(r["player_id"]) == identity["player_id"]
                and float(r["minutes"]) > 0
            ]
        else:
            positive = SOURCE["precise_time_unknown_positive"]
            identity = dict(player_id=int(positive["player_id"]), player_name=name)
            assert [
                r
                for r in players
                if int(r["game_id"]) == gid and int(r["player_id"]) == identity["player_id"]
            ] == [positive]
            assert (
                positive["team_id"] == row["team_id"] and positive["game_date"] == row["game_date"]
            )
            assert positive["minutes"] == "38" and positive["ast"] == "17" and truth is None
            assert not [
                r
                for r in reports
                if int(r["game_id"]) == gid and int(r["player_id"]) == identity["player_id"]
            ]
        if truth is None:
            text = [
                "Unavailable Filter",
                "The requested filter or metric is not available in the current dataset.",
            ]
            forbidden = [
                "Yes:",
                "No:",
                "No Matching Results",
                "MINUTES CHECK",
                "COUNT CHECK",
                "Can't answer that one yet",
            ]
        else:
            text = [
                "Yes:" if truth else "No:",
                name,
                row["game_date"],
                SELECTION,
                CAVEAT,
                name + " played " + minutes_description,
                name + " " + count_description,
            ]
            text.append(f"played {time} with {actual_count} {stat}" if time else "did not play")
            forbidden = [
                "Unavailable Filter",
                "No Matching Results",
                "With player",
                "Without player",
                "Played check",
                "played 0:00",
            ]
        cases.append(
            dict(
                id=ident,
                query=frozen["query"],
                identity=identity,
                team=team,
                opponent=opponent,
                stat=stat,
                truth=truth,
                time=time,
                actual_count=actual_count,
                minutes_description=minutes_description,
                count_description=count_description,
                row=row,
                opponent_pts=int(other[0]["pts"]),
                team_context=_identity(team, ["2023-24"], int(row["team_id"])),
                opponent_context=_identity(opponent, ["2023-24"], int(row["opponent_team_id"])),
                text=text,
                forbidden=forbidden + ["undefined", "NaN", "Infinity"],
            )
        )
    return cases


def _validate_answers(receipt, cases, output):
    by_id, seen = {c["id"]: c for c in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        key = item["viewport"], item["id"]
        assert key not in seen
        seen.add(key)
        case, payload = by_id[item["id"]], item["payload"]
        assert item["query"] == payload["query"] == case["query"]
        assert (
            item["http"] == 200
            and not item["errors"]
            and not item["missing"]
            and not item["forbidden"]
            and not item["grainErrors"]
        )
        assert all(t in item["text"] for t in case["text"]) and not any(
            t in item["text"] for t in case["forbidden"]
        )
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        for ready in [item["readinessBefore"], item["readinessAfter"]]:
            assert (
                ready["ready"] is True
                and ready["status"] == "ready"
                and ready["immutable_generation"] is True
            )
            assert ready["active_generation"] == SOURCE["generation"] and not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        result = payload["result"]
        m, sections = result["metadata"], result["sections"]
        assert payload["route"] == "game_finder"
        assert (
            m["player"] == case["identity"]["player_name"]
            and m["player_context"] == case["identity"]
        )
        assert (
            m["team"] == case["team"]
            and m["opponent"] == case["opponent"]
            and m["season"] == "2023-24"
            and m["season_type"] == "Regular Season"
        )
        assert (
            m["team_context"] == case["team_context"]
            and m["opponent_context"] == case["opponent_context"]
        )
        assert (
            m["stat"] is None
            and m["min_value"] is None
            and m["max_value"] is None
            and not m["threshold_conditions"]
        )
        assert (
            not m["with_player"]
            and not m["without_player"]
            and m["last_n"] == 1
            and m["last_n_scope"] == "window"
        )
        if case["truth"] is None:
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "filter_not_supported"
            )
            assert not sections and not item["tables"] and not m.get("answer_phrase")
            assert not any(
                f["label"] in ["Minutes check", "Count check"] for f in m.get("applied_filters", [])
            )
            assert any("precise" in n and "LeBron James" in n for n in result["notes"])
            continue
        assert (
            payload["result_status"] == "ok"
            and payload["result_reason"] is None
            and not m.get("unsupported_filters")
        )
        assert m.get("intent") != "unsupported" and not any(
            "unsupported_boundary" in str(n) for n in m.get("notes", [])
        )
        phrase = m["answer_phrase"]
        assert (
            phrase.startswith("Yes:" if case["truth"] else "No:")
            and case["identity"]["player_name"] in phrase
            and case["row"]["game_date"] in phrase
        )
        if case["time"]:
            assert f"played {case['time']} with {case['actual_count']} {case['stat']}" in phrase
        else:
            assert "did not play" in phrase and not any(
                t in phrase
                for t in ["played 0:", "with 0", "0 points", "0 rebounds", "0 assists", "38:50"]
            )
        minutes = dict(
            label="Minutes check",
            kind="player",
            value=case["identity"]["player_name"] + " played " + case["minutes_description"],
        )
        count = dict(
            label="Count check",
            kind="player",
            value=case["identity"]["player_name"] + " " + case["count_description"],
        )
        assert minutes in m["applied_filters"] and count in m["applied_filters"]
        assert (
            f"MINUTES CHECK\n{minutes['value']}" in item["text"]
            and f"COUNT CHECK\n{count['value']}" in item["text"]
        )
        assert (
            dict(label="Sample selection", kind="window", value=SELECTION) in m["applied_filters"]
        )
        assert not any(
            f["label"] in ["Played check", "With player", "Without player"]
            for f in m["applied_filters"]
        )
        assert CAVEAT in result["caveats"] and CAVEAT in item["text"]
        assert set(sections) == {"finder"} and len(sections["finder"]) == 1
        actual, truth = sections["finder"][0], case["row"]
        assert not any(k in actual for k in ["player", "player_id", "player_name"])
        for field in ["game_id", "team_id", "opponent_team_id", "pts", "reb", "ast"]:
            assert actual[field] == int(truth[field])
        for field in ["team_abbr", "team_name", "opponent_team_abbr", "opponent_team_name", "wl"]:
            assert actual[field] == truth[field]
        assert (
            datetime.fromisoformat(str(actual["game_date"]).replace("Z", "+00:00"))
            .date()
            .isoformat()
            == truth["game_date"]
        )
        assert actual["plus_minus"] == int(truth["pts"]) - case["opponent_pts"]
        table = _table(item, "Game log")
        assert len(table["rows"]) == 1 and "Player" not in table["headers"]
        cells = dict(zip(table["headers"], table["rows"][0]))
        day = date.fromisoformat(truth["game_date"])
        assert cells["Date"] == f"{day:%b} {day.day}"
        assert (
            cells["Team"] == truth["team_abbr"] + truth["team_name"]
            and cells["Opp"] == truth["opponent_team_abbr"] + truth["opponent_team_name"]
        )
        assert (
            cells["Score"] == f"{truth['pts']}-{case['opponent_pts']}"
            and cells["W/L"] == truth["wl"]
        )
        for stat in ["pts", "reb", "ast"]:
            assert float(cells[stat.upper()]) == int(truth[stat])
    assert seen == {(view, ident) for view in ["desktop", "mobile"] for ident in by_id}


def test_deployed_original_stat_pair_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
