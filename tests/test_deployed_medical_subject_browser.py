"""Unavailable status preserves request ownership beside qualified statistics."""

import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _identity, _summary, _table

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-vEjeGbzQ.js", "medical-subject-browser"
FIXTURES = Path(__file__).parent / "fixtures/medical_subject_scope"
GENERATION = "availability-opening-s4-v1-20261017"


def _cases():
    path = FIXTURES / "source_facts.json"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "a96da8646a6d5323f9d14b455c0ad89fdc1eb4285f0b9d47f41939c400e6e615"
    )
    contract = FIXTURES / "route_consumer_contract.json"
    assert (
        hashlib.sha256(contract.read_bytes()).hexdigest()
        == "d1f6aa6ff8fc53becf6601cdba908fe6c1f7bfe363b24d1a591a7f7a27324189"
    )
    source = json.loads(path.read_text())
    assert source["generation"] == GENERATION
    for name, digest in source["source_hashes"].items():
        assert hashlib.sha256(data_path(name).read_bytes()).hexdigest() == digest

    def raw(kind, season):
        with data_path(f"raw/{kind}/{season}_regular_season.csv").open() as stream:
            return list(csv.DictReader(stream))

    def exact_rows(frozen, kind, season, keys):
        rows = raw(kind, season)
        for expected in frozen:
            assert [r for r in rows if all(r[k] == expected[k] for k in keys)] == [expected]

    white = source["qualified_played_control"]
    for key, kind, keys in [
        ("team_rows", "team_game_stats", ["game_id", "team_id"]),
        ("reciprocal_rows", "team_game_stats", ["game_id", "team_id"]),
        ("catalog_rows", "games", ["game_id"]),
        ("player_rows", "player_game_stats", ["game_id", "player_id"]),
        ("report_rows", "player_game_availability", ["game_id", "player_id"]),
    ]:
        exact_rows(white[key], kind, "2025-26", keys)
    teams = raw("team_game_stats", "2025-26")
    candidate = [
        r
        for r in teams
        if r["team_id"] == white["subject_team_id"]
        and r["opponent_team_id"] == white["opponent_team_id"]
    ]
    assert sorted(candidate, key=lambda r: r["game_id"]) == sorted(
        white["team_rows"], key=lambda r: r["game_id"]
    )
    assert {r["game_id"] for r in candidate} == {"0022500338", "0022500823"}
    for row in candidate:
        report = [r for r in white["report_rows"] if r["game_id"] == row["game_id"]]
        player = [r for r in white["player_rows"] if r["game_id"] == row["game_id"]]
        other = [
            r
            for r in white["reciprocal_rows"]
            if r["game_id"] == row["game_id"] and r["team_id"] == row["opponent_team_id"]
        ]
        game = [r for r in white["catalog_rows"] if r["game_id"] == row["game_id"]]
        assert len(report) == len(player) == len(other) == len(game) == 1
        assert report[0]["player_id"] == player[0]["player_id"] == white["condition_player_id"]
        assert report[0]["team_id"] == player[0]["team_id"] == row["team_id"]
        assert (
            report[0]["game_date"]
            == player[0]["game_date"]
            == row["game_date"]
            == other[0]["game_date"]
            == game[0]["game_date"]
        )
        assert (
            report[0]["participation_state"] == "played"
            and report[0]["coverage_scope"] == "listed_player_rows_only"
            and float(player[0]["minutes"]) > 0
        )
        assert game[0]["is_final"] == "1" and {
            game[0]["home_team_id"],
            game[0]["away_team_id"],
        } == {row["team_id"], row["opponent_team_id"]}
        assert other[0]["opponent_team_id"] == row["team_id"]
        assert (row["wl"] == "W") == (int(row["pts"]) > int(other[0]["pts"]))
    assert len(candidate) == white["games"] == 2 and white["wins"] == 2 and white["losses"] == 0
    assert white["totals"] == {
        stat: sum(int(r[stat]) for r in candidate) for stat in ("pts", "reb", "ast")
    }
    comparison = source["unfiltered_comparison_control"]
    exact_rows(comparison["team_rows"], "team_game_stats", "2023-24", ["game_id", "team_id"])
    exact_rows(comparison["catalog_rows"], "games", "2023-24", ["game_id"])
    players = raw("player_game_stats", "2023-24")
    assert len({(r["game_id"], r["player_id"]) for r in players}) == len(players)
    for sample in comparison["samples"]:
        selected = [
            r
            for r in players
            if r["player_id"] == sample["player_id"]
            and r["opponent_team_abbr"] == "NYK"
            and float(r["minutes"]) > 0
        ]
        selected.sort(key=lambda r: (r["game_date"], r["game_id"]))
        assert selected == sample["selected_rows"] and len(selected) == sample["games"]
        assert sample["totals"] == {
            stat: sum(int(r[stat]) for r in selected) for stat in ("pts", "reb", "ast")
        }
    unavailable = [
        (
            "medical-team-primary",
            "Boston record against Lakers in 2025-26 when Derrick White is medically cleared.",
            "team_record",
            "BOS",
            ["LAL"],
            "2025-26",
            "medical clearance",
            "derrick white",
        ),
        (
            "medical-prefix-owner",
            "While Al Horford is healthy, what was Lakers record against Celtics in 2023-24?",
            "team_record",
            "LAL",
            ["BOS"],
            "2023-24",
            "health status",
            "al horford",
        ),
        (
            "medical-opponent-union",
            "Boston record against Lakers and Knicks in 2025-26 when Derrick White is medically cleared.",
            "team_record",
            "BOS",
            ["LAL", "NYK"],
            "2025-26",
            "medical clearance",
            "derrick white",
        ),
        (
            "medical-comparison-owner",
            "Show Embiid and Jokic side by side against Knicks in 2023-24 when Tyrese Maxey is healthy.",
            "player_compare",
            None,
            ["NYK"],
            "2023-24",
            "health status",
            "tyrese maxey",
        ),
        (
            "medical-adjective-owner",
            "Boston record against Lakers in 2025-26 with a medically cleared Derrick White and a healthy Jaylen Brown.",
            "team_record",
            "BOS",
            ["LAL"],
            "2025-26",
            "medical clearance",
            "derrick white",
        ),
        (
            "medical-status-played-chain",
            "Boston record against Lakers in 2025-26 when Derrick White is cleared for contact and Jaylen Brown played.",
            "team_record",
            "BOS",
            ["LAL"],
            "2025-26",
            "medical clearance",
            "derrick white",
        ),
    ]
    cases = []
    for ident, query, route, team, opponents, season, condition, owner in unavailable:
        cases.append(
            dict(
                id=ident,
                kind="unavailable",
                query=query,
                route=route,
                team=team,
                opponents=opponents,
                season=season,
                condition=condition,
                owner=owner,
                text=[
                    "Unavailable Filter",
                    "The requested filter or metric is not available in the current dataset.",
                ],
                forbidden=[
                    "No Matching Results",
                    "Can't answer that one yet",
                    "0 games",
                    "2-0",
                    "118.5",
                    "NaN",
                    "undefined",
                    "Infinity",
                ],
            )
        )
    cases.append(
        dict(
            id="medical-played-positive",
            kind="record",
            query="Boston record against Lakers in 2025-26 when Derrick White played.",
            route="team_record",
            team="BOS",
            opponents=["LAL"],
            season="2025-26",
            expected=white,
            text=["Boston Celtics", "2-0", "2025-26", "Derrick White", "118.5"],
            forbidden=[
                "Unavailable Filter",
                "No Matching Results",
                "Can't answer that one yet",
                "NaN",
                "undefined",
                "Infinity",
            ],
        )
    )
    cases.append(
        dict(
            id="medical-unfiltered-comparison",
            kind="comparison",
            query="Show Embiid and Jokic side by side against Knicks in 2023-24.",
            route="player_compare",
            team=None,
            opponents=["NYK"],
            season="2023-24",
            expected=comparison["samples"],
            text=["Joel Embiid", "Nikola Jokić", "2023-24", "NYK"],
            forbidden=[
                "Unavailable Filter",
                "No Matching Results",
                "Can't answer that one yet",
                "NaN",
                "undefined",
                "Infinity",
            ],
        )
    )
    return cases


def _validate_answers(receipt, cases, output):
    by_id, seen = {c["id"]: c for c in cases}, set()
    assert not receipt["failures"]
    ids = {"BOS": 1610612738, "LAL": 1610612747, "NYK": 1610612752}
    actors = [
        dict(player_id=203954, player_name="Joel Embiid"),
        dict(player_id=203999, player_name="Nikola Jokić"),
    ]
    for item in receipt["receipts"]:
        key = item["viewport"], item["id"]
        assert key not in seen
        seen.add(key)
        case = by_id[item["id"]]
        payload = item["payload"]
        assert item["query"] == payload["query"] == case["query"] and item["http"] == 200
        assert not any(item[k] for k in ("errors", "missing", "forbidden", "grainErrors"))
        assert all(t in item["text"] for t in case["text"]) and not any(
            t in item["text"] for t in case["forbidden"]
        )
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        for ready in (item["readinessBefore"], item["readinessAfter"]):
            assert (
                ready["ready"] is True
                and ready["status"] == "ready"
                and ready["immutable_generation"] is True
            )
            assert ready["active_generation"] == GENERATION and not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        assert payload["route"] == case["route"]
        meta, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert (
            meta["query_text"] == case["query"]
            and meta["season"] == case["season"]
            and meta["season_type"] == "Regular Season"
        )
        assert meta["team"] == case["team"] and not meta.get("without_player")
        if case["team"]:
            assert meta["team_context"] == _identity(
                case["team"], [case["season"]], ids[case["team"]]
            )
            assert (
                meta.get("player") is None
                and not meta.get("player_context")
                and not meta.get("players_context")
            )
        else:
            assert (
                meta["player"] == "Joel Embiid, Nikola Jokić" and meta["players_context"] == actors
            )
        if len(case["opponents"]) == 1:
            opponent = case["opponents"][0]
            assert meta["opponent"] == opponent and meta["opponent_context"] == _identity(
                opponent, [case["season"]], ids[opponent]
            )
        else:
            assert meta["opponents"] == case["opponents"] and meta["opponent"] == ", ".join(
                case["opponents"]
            )
            assert not meta.get("opponent_context")
        if case["kind"] == "unavailable":
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "filter_not_supported"
            )
            assert (
                not sections
                and not item["tables"]
                and not meta.get("answer_phrase")
                and not meta.get("applied_filters")
            )
            assert not meta.get("with_player")
            assert (
                "availability_status" in meta["unsupported_filters"]
                and meta["unsupported_availability"]["condition"] == case["condition"]
            )
            assert any(
                "requested_availability_condition:" in n and case["owner"] in n.lower()
                for n in meta["notes"]
            )
            if case["id"] == "medical-adjective-owner":
                assert any(
                    "with a medically cleared derrick white and a healthy jaylen brown" in n.lower()
                    for n in meta["notes"]
                )
            continue
        assert (
            payload["result_status"] == "ok"
            and payload["result_reason"] is None
            and not meta.get("unsupported_filters")
            and not meta.get("unsupported_availability")
        )
        assert not any("unsupported_boundary" in str(n) for n in meta.get("notes", []))
        if case["kind"] == "record":
            expected = case["expected"]
            assert meta["with_player"] == "Derrick White"
            assert (
                dict(label="With player", kind="player", value="Derrick White")
                in meta["applied_filters"]
            )
            assert "WITH PLAYER\nDerrick White" in item["text"]
            summary = dict(games=2, wins=2, losses=0, sums=expected["totals"])
            assert len(sections["summary"]) == len(sections["by_season"]) == 1
            for row in (sections["summary"][0], sections["by_season"][0]):
                _summary(row, summary)
            rows = sections["game_log"]
            assert len(rows) == 2
            truth = {int(r["game_id"]): r for r in expected["team_rows"]}
            assert {r["game_id"] for r in rows} == set(truth)
            matching = [t for t in item["tables"] if t.get("sectionLabel") == "Game Detail"]
            assert len(matching) == 1
            table = matching[0]
            assert len(table["rows"]) == 2 and not table["footers"]
            for row in rows:
                source = truth[row["game_id"]]
                for field in ("team_id", "opponent_team_id", "pts", "reb", "ast"):
                    assert row[field] == int(source[field])
                assert (
                    datetime.fromisoformat(str(row["game_date"]).replace("Z", "+00:00"))
                    .date()
                    .isoformat()
                    == source["game_date"]
                )
                assert (
                    row["team_abbr"] == source["team_abbr"]
                    and row["opponent_team_abbr"] == source["opponent_team_abbr"]
                    and row["wl"] == source["wl"]
                )
            displayed = [dict(zip(table["headers"], row)) for row in table["rows"]]
            displayed_by_id = {int(r["Game Id"].replace(",", "")): r for r in displayed}
            assert set(displayed_by_id) == set(truth)
            for game_id, shown in displayed_by_id.items():
                source = truth[game_id]
                assert shown["Team Name"] == source["team_name"]
                assert shown["Opponent Team Name"] == source["opponent_team_name"]
                assert shown["Game Date"] == datetime.fromisoformat(source["game_date"]).strftime(
                    "%b %-d"
                )
                assert shown["Wl"] == source["wl"]
                for stat in ("pts", "reb", "ast"):
                    assert float(shown[stat.title()]) == int(source[stat])
                other = next(
                    r for r in expected["reciprocal_rows"] if r["game_id"] == source["game_id"]
                )
                assert float(shown["Opponent Pts"]) == int(other["pts"])
            for stat in ("pts", "reb", "ast"):
                assert sum(float(r[stat.title()]) for r in displayed) == expected["totals"][stat]
        else:
            assert not meta.get("with_player") and not meta.get("head_to_head_used")
            expected = case["expected"]
            rows = sections["summary"]
            assert len(rows) == 2 and [r["player_name"] for r in rows] == [
                s["canonical_name"] for s in expected
            ]
            table = _table(item, "Comparison metrics")
            assert (
                table["headers"][1:3] == [s["canonical_name"] for s in expected]
                and not table["footers"]
            )
            displayed = {r[0]: r for r in table["rows"]}
            for col, (row, sample) in enumerate(zip(rows, expected), 1):
                assert (
                    row["games"] == sample["games"]
                    and int(displayed["Games"][col]) == sample["games"]
                )
                for stat in ("pts", "reb", "ast"):
                    assert row[stat + "_sum"] == sample["totals"][stat] and row[
                        stat + "_avg"
                    ] == round(sample["totals"][stat] / sample["games"], 3)
                    assert float(displayed[stat.upper() + " Avg"][col]) == pytest.approx(
                        row[stat + "_avg"], abs=0.051
                    )
    assert seen == {(view, ident) for view in ("desktop", "mobile") for ident in by_id}


def test_deployed_medical_subject_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
