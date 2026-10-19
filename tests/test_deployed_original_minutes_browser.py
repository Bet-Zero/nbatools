"""Exact report-time checks remain distinct from original team-game evidence."""

import csv
import hashlib
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _identity, _table

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-ClijrUhz.js", "original-minutes-browser"
FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_PATH = FIXTURES / "qualified_scalar_played/source_and_baseline.json"
PRIVATE_PATH = FIXTURES / "qualified_original_minutes/checker_close_decimal_controls.json"
SOURCE = json.loads(SOURCE_PATH.read_text())
SELECTION = "Select the latest original team matchup before checking player minutes"
CAVEAT = (
    "The minutes check uses official report time in MM:SS on the selected original game. "
    "The table shows team-game totals, not the checked player's statistics. "
    "An explicit DNP is nonparticipation, not a zero-stat appearance."
)


def _cases():
    assert (
        hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
        == "1d55567df1bd2cd8ea400b1d24ac0da1e5de22fe7c917c566c4c0984fbb3ddd1"
    )
    assert (
        hashlib.sha256(PRIVATE_PATH.read_bytes()).hexdigest()
        == "c3fdc1110f3ec41d4861c9660b89e181e3b6d828489da2fb36d421d905699fb7"
    )
    private = json.loads(PRIVATE_PATH.read_text())
    for path, digest in SOURCE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        with data_path(f"raw/{kind}/2023-24_regular_season.csv").open() as stream:
            return list(csv.DictReader(stream))

    teams, appearances, ledger = [
        raw(k) for k in ["team_game_stats", "player_game_stats", "player_game_availability"]
    ]
    assert len({(r["game_id"], r["team_id"]) for r in teams}) == len(teams)
    specs = [
        (
            "minutes-exact-yes",
            private["cases"][0],
            dict(player_id=1630202, player_name="Payton Pritchard"),
            "BOS",
            "LAL",
            22300684,
            True,
            "21:18",
            "> 21.29995 minutes",
        ),
        (
            "minutes-exact-no",
            private["cases"][2],
            dict(player_id=1630202, player_name="Payton Pritchard"),
            "BOS",
            "LAL",
            22300684,
            False,
            "21:18",
            ">= 21.30005 minutes",
        ),
        (
            "minutes-dnp-no",
            None,
            SOURCE["cases"][1]["canonical_player"],
            "LAL",
            "BOS",
            22300684,
            False,
            None,
            "< 30 minutes",
        ),
        (
            "minutes-time-unknown",
            None,
            SOURCE["cases"][6]["canonical_player"],
            "LAL",
            "NOP",
            22301195,
            None,
            None,
            ">= 30 minutes",
        ),
    ]
    cases = []
    for ident, heldout, identity, team, opponent, gid, truth, time, description in specs:
        candidates = [
            r for r in teams if r["team_abbr"] == team and r["opponent_team_abbr"] == opponent
        ]
        candidates.sort(key=lambda r: (r["game_date"], int(r["game_id"])), reverse=True)
        row = candidates[0]
        assert int(row["game_id"]) == gid
        other = [
            r for r in teams if int(r["game_id"]) == gid and r["team_id"] == row["opponent_team_id"]
        ]
        assert (
            len(other) == 1
            and other[0]["opponent_team_id"] == row["team_id"]
            and other[0]["game_date"] == row["game_date"]
        )
        facts = [
            r
            for r in ledger
            if int(r["game_id"]) == gid and int(r["player_id"]) == identity["player_id"]
        ]
        positive = [
            r
            for r in appearances
            if int(r["game_id"]) == gid
            and int(r["player_id"]) == identity["player_id"]
            and float(r["minutes"]) > 0
        ]
        if heldout:
            assert facts == [private["canonical_report_fact"]] and positive == [
                private["canonical_positive_appearance"]
            ]
            assert facts[0]["team_id"] == positive[0]["team_id"] == row["team_id"]
            assert (
                facts[0]["game_date"]
                == positive[0]["game_date"]
                == row["game_date"]
                == "2024-02-01"
            )
            assert (
                facts[0]["participation_state"] == "played"
                and facts[0]["coverage_scope"] == "listed_player_rows_only"
            )
            assert (
                private["pdf_time"] == time
                and Decimal(facts[0]["source_minutes"]) * 60
                == heldout["exact_report_seconds"]
                == 1278
            )
            query = heldout["query"]
            assert truth is heldout["expected_boolean"]
        elif truth is False:
            frozen = SOURCE["cases"][1]
            assert (
                row == frozen["selected_original_team_row"]
                and facts == frozen["report_observation_rows"]
            )
            assert (
                not positive
                and facts[0]["participation_state"] == "did_not_play"
                and facts[0]["source_minutes"] == ""
                and facts[0]["source_comment"]
            )
            query = "Did Anthony Davis play fewer than 30 minutes in the Lakers last game against Celtics in 2023-24?"
        else:
            frozen = SOURCE["cases"][6]
            assert (
                row == frozen["selected_original_team_row"]
                and positive == frozen["positive_appearance_rows"]
                and not facts
            )
            assert (
                positive[0]["team_id"] == row["team_id"]
                and positive[0]["game_date"] == row["game_date"]
            )
            assert (
                positive[0]["minutes"] == "38"
            )  # A positive rounded row is not qualified report seconds.
            query = "Did LeBron James play at least 30 minutes in the Lakers last game against Pelicans in 2023-24?"
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
                "Can't answer that one yet",
            ]
        else:
            text = [
                "Yes:" if truth else "No:",
                identity["player_name"],
                row["game_date"],
                SELECTION,
                CAVEAT,
                identity["player_name"] + " played " + description,
            ]
            text.append("played " + time if time else "did not play")
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
                query=query,
                identity=identity,
                team=team,
                opponent=opponent,
                truth=truth,
                time=time,
                description=description,
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
            assert not any(f["label"] == "Minutes check" for f in m.get("applied_filters", []))
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
            assert "played " + case["time"] in phrase
        else:
            assert "did not play" in phrase and not any(
                t in phrase for t in ["played 0:", "0 points", "0 rebounds", "0 assists", "38:50"]
            )
        check = dict(
            label="Minutes check",
            kind="player",
            value=case["identity"]["player_name"] + " played " + case["description"],
        )
        assert check in m["applied_filters"] and f"MINUTES CHECK\n{check['value']}" in item["text"]
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


def test_deployed_original_minutes_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
