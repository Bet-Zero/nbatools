"""Bounded public opposing-player played, qualified empty and unfinished clause."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from nbatools.data_source import data_path, data_read_csv
from tests.test_core_identity_find_count_browser import ROOT, _capture_browser
from tests.test_deployed_union_pair_browser import _summary, _table
from tests.test_opponent_played_real_data import ORACLE

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
FIXTURES = ROOT / "tests/fixtures/opponent_played"
OBLIGATION = json.loads((FIXTURES / "additional_clause_obligation.json").read_text())
ASSET = "index-CE3ZKqeM.js"
LAL, BOS, TATUM = 1610612747, 1610612738, 1628369


def _cases():
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    cases = []
    for frozen in ORACLE["primary_cases"]:
        season = frozen["query"].split()[-1]
        suffix = f"{season}_regular_season.csv"
        games = data_read_csv(f"raw/games/{suffix}")
        teams = data_read_csv(f"raw/team_game_stats/{suffix}")
        players = data_read_csv(f"raw/player_game_stats/{suffix}")
        report = data_read_csv(f"raw/player_game_availability/{suffix}")
        candidates = teams.loc[teams.team_id.eq(LAL) & teams.opponent_team_id.eq(BOS)]
        assert sorted(candidates.game_id.astype(int)) == frozen["candidate_game_ids"]
        selected_ids = []
        for fact in frozen["observations"]:
            listed = report.loc[report.game_id.eq(fact["game_id"]) & report.player_id.eq(TATUM)]
            game = games.loc[games.game_id.eq(fact["game_id"])]
            assert len(listed) == len(game) == 1
            listed, game = listed.iloc[0], game.iloc[0]
            assert str(game.is_final).lower() in {"true", "1"}
            assert game.season == season and game.season_type == "Regular Season"
            assert {int(game.home_team_id), int(game.away_team_id)} == {LAL, BOS}
            assert str(game.game_date) == fact["game_date"]
            for key, value in fact.items():
                assert listed[key] == value
            assert listed.coverage_scope == "listed_player_rows_only"
            # The same historical source is retained in the pinned generation;
            # reading its bytes is not a new NBA fetch or a publication action.
            day = fact["game_date"].replace("-", "")
            reference = f"{day}_{game.away_team_abbr}{game.home_team_abbr}"
            directory = "raw/player_game_availability_sources/"
            receipt = json.loads(data_path(directory + reference + ".json").read_text())
            assert receipt["source_url"] == f"https://statsdmz.nba.com/pdfs/{day}/{reference}.pdf"
            assert receipt["sha256"] == fact["source_sha256"]
            assert receipt["raw_file"] == fact["source_sha256"] + ".pdf"
            assert datetime.fromisoformat(receipt["retrieved_at"]).tzinfo is not None
            raw = data_path(directory + receipt["raw_file"]).read_bytes()
            assert raw.startswith(b"%PDF") and len(raw) == receipt["size_bytes"]
            assert hashlib.sha256(raw).hexdigest() == receipt["sha256"]
            positive = players.loc[
                players.game_id.eq(fact["game_id"])
                & players.player_id.eq(TATUM)
                & players.minutes.gt(0)
            ]
            if fact["participation_state"] == "played":
                assert len(positive) == 1
                assert positive.iloc[0].team_id == BOS
                assert str(positive.iloc[0].game_date) == fact["game_date"]
                assert listed.source_minutes > 0
                selected_ids.append(fact["game_id"])
            else:
                assert fact["participation_state"] == "did_not_play" and positive.empty
                assert listed.source_comment and not listed.source_minutes > 0
        assert sorted(selected_ids) == frozen["expected"]["game_ids"]
        chosen = candidates.loc[candidates.game_id.isin(selected_ids)]
        expected = frozen["expected"]
        assert len(chosen) == expected["games"]
        assert int(chosen.wl.eq("W").sum()) == expected["wins"]
        assert int(chosen.wl.eq("L").sum()) == expected["losses"]
        for stat, total in expected["sums"].items():
            assert int(chosen[stat].sum()) == total
        positive_case = bool(expected["games"])
        cases.append(
            dict(
                id="opponent-played-positive" if positive_case else "opponent-played-empty",
                kind="positive" if positive_case else "empty",
                query=frozen["query"],
                season=season,
                expected=expected,
                rows=chosen.to_dict("records"),
                text=["Los Angeles Lakers", "1-1", "Jayson Tatum", "50% win rate", "2023-24"]
                if positive_case
                else ["No Matching Results", "No games or records matched the query filters."],
                forbidden=["Unavailable Filter", "Data Not Available"]
                + (["No Matching Results"] if positive_case else ["1-1"]),
            )
        )
    report = data_read_csv("raw/player_game_availability/2023-24_regular_season.csv")
    for fact in OBLIGATION["independent_source_rows"]:
        rows = report.loc[
            report.game_id.eq(fact["game_id"]) & report.player_id.eq(fact["player_id"])
        ]
        assert len(rows) == 1
        for key, value in fact.items():
            assert rows.iloc[0][key] == value
    cases.append(
        dict(
            id="opponent-played-extra-clause",
            kind="guard",
            query=OBLIGATION["query"],
            season="2023-24",
            text=[
                "Unavailable Filter",
                "These player participation conditions are not supported together yet. Try one condition at a time.",
            ],
            forbidden=["No Matching Results", "1-1", "114.5", "with-player and without-player"],
        )
    )
    assert len(cases) == 3
    return cases


def _validate_answers(receipt, cases, output):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
        assert item["http"] == 200 and not item["errors"]
        assert not item["missing"] and not item["forbidden"] and not item["grainErrors"]
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert f"{receipt['base']}/assets/{ASSET}" in item["assets"]
        assert all(text in item["text"] for text in case["text"])
        assert not any(text in item["text"] for text in case["forbidden"])
        for ready in [item["readinessBefore"], item["readinessAfter"]]:
            assert ready["ready"] is True and ready["status"] == "ready"
            assert ready["immutable_generation"] is True
            assert ready["active_generation"] == ORACLE["generation"]
            assert not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        payload = item["payload"]
        assert payload["route"] == "team_record"
        meta, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert meta["team"] == "LAL" and meta["team_context"]["team_id"] == LAL
        assert meta["opponent"] == "BOS" and meta["opponent_context"]["team_id"] == BOS
        assert meta["player"] is None and not meta.get("player_context")
        assert meta["with_player"] == "Jayson Tatum" and not meta["without_player"]
        assert meta["season"] == case["season"] and meta["season_type"] == "Regular Season"
        if case["kind"] != "positive":
            assert payload["result_status"] == "no_result" and not sections
            assert payload["result_reason"] == (
                "no_match" if case["kind"] == "empty" else "filter_not_supported"
            )
            assert not any(table["rows"] for table in item["tables"])
            if case["kind"] == "guard":
                assert "multi_player_availability" in meta["unsupported_filters"]
            else:
                assert not meta.get("unsupported_filters")
            continue
        assert payload["result_status"] == "ok" and not meta.get("unsupported_filters")
        assert {"label": "With player", "value": "Jayson Tatum", "kind": "player"} in meta[
            "applied_filters"
        ]
        assert len(sections["summary"]) == len(sections["by_season"]) == 1
        for summary in (sections["summary"][0], sections["by_season"][0]):
            _summary(summary, case["expected"])
        rows = sections["game_log"]
        truth = {int(row["game_id"]): row for row in case["rows"]}
        assert len(rows) == len(truth) == 2
        assert {int(row["game_id"]) for row in rows} == set(truth)
        for row in rows:
            source = truth[int(row["game_id"])]
            for key in (
                "game_id",
                "team_id",
                "opponent_team_id",
                "team_abbr",
                "opponent_team_abbr",
                "season",
                "pts",
                "reb",
                "ast",
                "wl",
            ):
                assert row[key] == source[key]
            when = datetime.fromisoformat(str(row["game_date"]).replace("Z", "+00:00"))
            assert when.date().isoformat() == source["game_date"]
        for stat, total in case["expected"]["sums"].items():
            assert sum(row[stat] for row in rows) == total
        table = _table(item, "Team record")
        assert len(table["rows"]) == 1
        cells = dict(zip(table["headers"], table["rows"][0]))
        assert "LAL" in cells["Team"] and "Celtics" in cells["Opponent"]
        assert cells["W-L"] == "1-1" and int(cells["Games"]) == 2
        assert float(cells["Win %"].rstrip("%")) == 50
        assert float(cells["PPG"]) == 114.5
        if item["viewport"] == "desktop":
            assert "114.5" in item["text"]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in by_id}


def test_deployed_opponent_played_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, "opponent-played-browser")
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path)))
    _validate_answers(receipt, cases, output / "opponent-played-browser")
