"""Qualified played-pair original versus qualifying windows through public UI."""

import hashlib
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _table
from tests.test_original_window_played_pair_real_data import ORACLE, ORACLE_PATH, SOURCE_IDENTITIES
from tests.test_qualified_participation_pair_real_data import _qualified_source

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-CJ1uR2hx.js", "original-pair-browser"
ORIGINAL = "Select the last 1 original matchup game before checking both played predicates"
QUALIFYING = "Select the last 1 games matching the conditions"


def _cases():
    assert (
        hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest()
        == "572c17fd53172c1f8dfcc2b53f782a0943dfc06e50bfc58209851d361f4e3f6b"
    )
    assert ORACLE["generation"] == "availability-opening-s4-v1-20261017"
    assert (
        ORACLE["manifest_sha256"]
        == "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
    )
    _qualified_source()  # Retained official PDFs plus qualified AD/LeBron observations and raw identities.
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        return pd.read_csv(data_path(f"raw/{kind}/2023-24_regular_season.csv"))

    teams, players, report, games = [
        raw(k)
        for k in ["team_game_stats", "player_game_stats", "player_game_availability", "games"]
    ]
    assert (
        not teams.duplicated(["game_id", "team_id"]).any() and not games.game_id.duplicated().any()
    )
    candidates = teams[
        teams.team_id.eq(1610612747) & teams.opponent_team_id.eq(1610612738)
    ].sort_values(["game_date", "game_id"], ascending=False)
    assert candidates.game_id.tolist() == [22300684, 22300403]
    played = {}
    for game in candidates.itertuples():
        catalog = games[games.game_id.eq(game.game_id)]
        other = teams[teams.game_id.eq(game.game_id) & teams.team_id.eq(game.opponent_team_id)]
        assert len(catalog) == len(other) == 1
        final = catalog.iloc[0]
        assert str(final.is_final).lower() in {"1", "true"} and final.game_date == game.game_date
        assert {int(final.home_team_id), int(final.away_team_id)} == {
            game.team_id,
            game.opponent_team_id,
        }
        assert (
            other.iloc[0].opponent_team_id == game.team_id
            and other.iloc[0].game_date == game.game_date
        )
        for name in ["Jayson Tatum", "Anthony Davis", "Austin Reaves"]:
            pid, side = SOURCE_IDENTITIES[name]
            fact = report[report.game_id.eq(game.game_id) & report.player_id.eq(pid)]
            assert len(fact) == 1
            fact = fact.iloc[0]
            assert (
                fact.player_name == name
                and fact.team_id == side
                and fact.game_date == game.game_date
            )
            assert (
                side in {game.team_id, game.opponent_team_id}
                and fact.coverage_scope == "listed_player_rows_only"
            )
            pdf = data_path("raw/player_game_availability_sources/" + fact.source_sha256 + ".pdf")
            assert hashlib.sha256(pdf.read_bytes()).hexdigest() == fact.source_sha256
            positive = players[
                players.game_id.eq(game.game_id) & players.player_id.eq(pid) & players.minutes.gt(0)
            ]
            assert len(positive) == int(fact.participation_state == "played")
            if len(positive):
                row = positive.iloc[0]
                assert (
                    row.player_name == name
                    and row.team_id == side
                    and row.game_date == fact.game_date
                )
            else:
                assert (
                    fact.participation_state == "did_not_play"
                    and isinstance(fact.source_comment, str)
                    and fact.source_comment.strip()
                )
            played[(int(game.game_id), name)] = fact.participation_state == "played"
    cases = []
    for ident, which, scope in [
        ("original-pair-empty", 0, "original_window"),
        ("qualifying-pair-positive", 0, "qualifying"),
        ("original-pair-positive", 1, "original_window"),
    ]:
        truth = ORACLE["helper_order_oracles"][which]
        names = truth["names"].split(" and ")
        original = candidates.head(1)
        selected = [
            int(row.game_id)
            for row in (original if scope == "original_window" else candidates).itertuples()
            if all(played[(int(row.game_id), name)] for name in names)
        ][:1]
        expected = truth[
            "qualified_inside_original_window"
            if scope == "original_window"
            else "latest_qualifying"
        ]
        assert selected == expected["game_ids"]
        source = candidates[candidates.game_id.isin(selected)]
        assert len(source) == expected["games"] and int(source.wl.eq("W").sum()) == expected["wins"]
        for stat, total in expected["sums"].items():
            assert source[stat].sum() == total
        keys = [
            "game_id",
            "game_date",
            "team_id",
            "opponent_team_id",
            "team_abbr",
            "opponent_team_abbr",
            "wl",
            "pts",
            "reb",
            "ast",
        ]
        rows = source[keys].to_dict("records")
        for row in rows:
            row["opponent_pts"] = int(
                teams[teams.game_id.eq(row["game_id"]) & teams.team_id.eq(row["opponent_team_id"])]
                .iloc[0]
                .pts
            )
        phrase = (
            "within their last 1 game"
            if scope == "original_window"
            else "in their last 1 qualifying game"
        )
        label = ORIGINAL if scope == "original_window" else QUALIFYING
        text = (
            ["No Matching Results"]
            if not expected["games"]
            else [truth["names"], label, "Los Angeles Lakers"]
        )
        forbidden = ["Unavailable Filter", "Data Not Available", "undefined", "NaN", "Infinity"]
        if expected["games"]:
            forbidden.append("No Matching Results")
        cases.append(
            dict(
                id=ident,
                query=f"Lakers record against Celtics {phrase} with {names[0]} playing while {names[1]} plays in 2023-24",
                scope=scope,
                pair=truth["names"],
                selection=label,
                expected=expected,
                rows=rows,
                text=text,
                forbidden=forbidden,
            )
        )
    return cases


def _positive(item, case, sections):
    assert item["payload"]["result_status"] == "ok" and item["payload"]["result_reason"] is None
    assert set(sections) == {"summary", "by_season", "game_log"}
    expected = case["expected"]
    truth = case["rows"][0]
    assert len(sections["summary"]) == len(sections["by_season"]) == 1
    assert sections["summary"][0]["team_name"] == "Los Angeles Lakers"
    assert sections["by_season"][0]["season"] == "2023-24"
    for row in [sections["summary"][0], sections["by_season"][0]]:
        for key in ["games", "wins", "losses"]:
            assert row[key] == expected[key]
        for stat, total in expected["sums"].items():
            assert row[stat + "_avg"] == total
    rows = sections["game_log"]
    assert len(rows) == 1
    for key, value in truth.items():
        if key == "game_date":
            assert (
                datetime.fromisoformat(str(rows[0][key]).replace("Z", "+00:00")).date().isoformat()
                == value
            )
        else:
            assert rows[0][key] == value
    record = _table(item, "Team record")
    assert len(record["rows"]) == 1
    cells = dict(zip(record["headers"], record["rows"][0]))
    assert (
        cells["Team"] == "LALLos Angeles Lakers"
        and cells["W-L"] == f"{expected['wins']}-{expected['losses']}"
    )
    assert int(cells["Games"]) == 1 and float(cells["PPG"]) == truth["pts"]
    assert cells["Opponent"] == "BOSCeltics"
    assert float(cells["Win %"].rstrip("%")) == expected["wins"] * 100
    margin = truth["pts"] - truth["opponent_pts"]
    assert float(cells["+/-"]) == rows[0]["plus_minus"] == margin
    assert sections["summary"][0]["plus_minus_avg"] == margin


def _validate_answers(receipt, cases, output):
    by_id, seen = {c["id"]: c for c in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
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
            assert ready["active_generation"] == ORACLE["generation"] and not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        payload = item["payload"]
        assert payload["route"] == "team_record"
        m, s = payload["result"]["metadata"], payload["result"]["sections"]
        assert m["team"] == "LAL" and m["team_context"] == dict(
            team_id=1610612747, team_abbr="LAL", team_name="Lakers"
        )
        assert m["opponent"] == "BOS" and m["opponent_context"] == dict(
            team_id=1610612738, team_abbr="BOS", team_name="Celtics"
        )
        assert m["player"] is None and not m.get("player_context")
        assert m["season"] == "2023-24" and m["season_type"] == "Regular Season"
        assert m["last_n"] == 1 and m["last_n_scope"] == case["scope"]
        assert (
            m["with_player"] == case["pair"]
            and not m["without_player"]
            and not m.get("unsupported_filters")
        )
        assert dict(label="With player", kind="player", value=case["pair"]) in m["applied_filters"]
        assert (
            dict(label="Sample selection", kind="window", value=case["selection"])
            in m["applied_filters"]
        )
        if not case["expected"]["games"]:
            # This renderer shows a generic empty card, with scope in collapsed notes.
            # Pair and selection labels above are API assertions, not visible-label claims.
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "no_match"
                and not s
                and not item["tables"]
            )
            assert (
                "Original window selected 1 game(s) before testing both played predicates"
                in payload["result"]["notes"]
            )
        else:
            _positive(item, case, s)
    assert seen == {(view, ident) for view in ["desktop", "mobile"] for ident in by_id}


def test_deployed_original_pair_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
