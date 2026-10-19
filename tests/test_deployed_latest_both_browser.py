"""Qualified BOTH checks preserve the latest original game for Yes and No."""

import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _table
from tests.test_original_window_played_pair_real_data import ORACLE, ORACLE_PATH, SOURCE_IDENTITIES
from tests.test_qualified_participation_pair_real_data import _qualified_source

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-ClijrUhz.js", "latest-both-browser"
SELECTION = "Select the latest original matchup game before checking both played predicates"
CAVEAT = (
    "Both played predicates were checked on the selected original game. "
    "A No answer means at least one player did not play; "
    "it does not imply that neither played."
)


def _cases():
    assert hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest() == (
        "572c17fd53172c1f8dfcc2b53f782a0943dfc06e50bfc58209851d361f4e3f6b"
    )
    _qualified_source()  # Existing retained official reports; never query-derived truth.
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        return pd.read_csv(data_path(f"raw/{kind}/2023-24_regular_season.csv"))

    teams, games, players, observations = [
        raw(k)
        for k in ["team_game_stats", "games", "player_game_stats", "player_game_availability"]
    ]
    assert not teams.duplicated(["game_id", "team_id"]).any()
    candidates = teams[teams.team_id.eq(1610612747) & teams.opponent_team_id.eq(1610612738)]
    candidates = candidates.sort_values(["game_date", "game_id"], ascending=False)
    assert candidates.game_id.tolist() == [22300684, 22300403]
    original = candidates.iloc[0]
    assert original.game_id == 22300684 and original.game_date == "2024-02-01"
    schedule = games[games.game_id.eq(original.game_id)]
    reciprocal = teams[teams.game_id.eq(original.game_id) & teams.team_id.eq(1610612738)]
    assert len(schedule) == len(reciprocal) == 1
    scheduled, other = schedule.iloc[0], reciprocal.iloc[0]
    assert str(scheduled.is_final).lower() in {"1", "true"}
    assert scheduled.game_date == other.game_date == original.game_date
    assert {int(scheduled.home_team_id), int(scheduled.away_team_id)} == {1610612747, 1610612738}
    assert other.opponent_team_id == original.team_id
    played = {}
    for name, (pid, side) in SOURCE_IDENTITIES.items():
        if name == "LeBron James":
            continue
        facts = observations[
            observations.game_id.eq(original.game_id) & observations.player_id.eq(pid)
        ]
        assert len(facts) == 1
        fact = facts.iloc[0]
        assert (
            fact.player_name == name
            and fact.team_id == side
            and fact.game_date == original.game_date
        )
        assert fact.coverage_scope == "listed_player_rows_only"
        assert (
            fact.source_sha256 == "98f2dbbf9db7b64a99a19e80721196ec788632c5ba0bae881c70bcd3799cfda4"
        )
        positive = players[
            players.game_id.eq(original.game_id) & players.player_id.eq(pid) & players.minutes.gt(0)
        ]
        assert len(positive) == int(fact.participation_state == "played")
        if len(positive):
            appearance = positive.iloc[0]
            assert (
                appearance.player_name == name
                and appearance.team_id == side
                and appearance.game_date == fact.game_date
            )
        else:
            assert (
                fact.participation_state == "did_not_play"
                and isinstance(fact.source_comment, str)
                and fact.source_comment.strip()
            )
        played[name] = fact.participation_state == "played"
    keys = [
        "game_id",
        "game_date",
        "team_id",
        "opponent_team_id",
        "team_abbr",
        "opponent_team_abbr",
        "pts",
        "reb",
        "ast",
        "wl",
    ]
    row = {
        key: original[key].item() if hasattr(original[key], "item") else original[key]
        for key in keys
    }
    row["opponent_pts"] = int(other.pts)
    assert [row[k] for k in ["pts", "reb", "ast", "opponent_pts"]] == [114, 52, 30, 105]
    cases = []
    for ident, second, expected in [
        ("latest-both-yes", "Austin Reaves", True),
        ("latest-both-no", "Anthony Davis", False),
    ]:
        names = ["Jayson Tatum", second]
        assert all(played[name] for name in names) is expected
        pair = " and ".join(names)
        cases.append(
            dict(
                id=ident,
                names=names,
                pair=pair,
                truth=expected,
                row=row,
                query=f"Of the Lakers last game against Celtics in 2023-24, did BOTH {pair} play?",
                text=[
                    "Yes:" if expected else "No:",
                    pair,
                    "2024-02-01",
                    SELECTION,
                    pair + " both played",
                    CAVEAT,
                ],
                forbidden=[
                    "No Matching Results",
                    "Unavailable Filter",
                    "With player",
                    "Without player",
                    "undefined",
                    "NaN",
                    "Infinity",
                ],
            )
        )
    cases.append(
        dict(
            id="latest-both-unknown-first",
            truth=None,
            query="Of the Lakers last game against Celtics in 2023-24, did BOTH Blorg and Austin Reaves play?",
            text=["Unavailable Filter"],
            forbidden=["Yes:", "No:", "No Matching Results", "undefined", "NaN", "Infinity"],
        )
    )
    return cases


def _validate_answers(receipt, cases, output):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        key = item["viewport"], item["id"]
        assert key not in seen
        seen.add(key)
        case = by_id[item["id"]]
        payload = item["payload"]
        assert item["query"] == payload["query"] == case["query"]
        assert item["http"] == 200 and not item["errors"] and not item["missing"]
        assert not item["forbidden"] and not item["grainErrors"]
        assert all(t in item["text"] for t in case["text"])
        assert not any(t in item["text"] for t in case["forbidden"])
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
        result = payload["result"]
        m, sections = result["metadata"], result["sections"]
        assert m["team"] == "LAL" and m["opponent"] == "BOS" and m["season"] == "2023-24"
        assert m["team_context"] == dict(team_id=1610612747, team_abbr="LAL", team_name="Lakers")
        assert m["opponent_context"] == dict(
            team_id=1610612738, team_abbr="BOS", team_name="Celtics"
        )
        assert m["player"] is None and not m.get("player_context") and not m.get("players_context")
        assert not m["with_player"] and not m["without_player"]
        if case["truth"] is None:
            assert not any(m.get(k) for k in ["player_a", "player_b", "opponent_player"])
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "filter_not_supported"
            )
            assert not sections and not item["tables"] and not m.get("answer_phrase")
            assert (
                not m.get("applied_filters")
                and "multi_player_availability" in m["unsupported_filters"]
            )
            continue
        assert (
            payload["route"] == "game_finder"
            and payload["result_status"] == "ok"
            and payload["result_reason"] is None
        )
        assert not m.get("unsupported_filters") and m["season_type"] == "Regular Season"
        assert m.get("intent") != "unsupported"
        assert not any("unsupported_boundary" in str(note) for note in m.get("notes", []))
        assert "played check" in item["text"].lower()
        assert (
            "with player" not in item["text"].lower()
            and "without player" not in item["text"].lower()
        )
        assert m["last_n"] == 1 and m["last_n_scope"] == "window"
        assert m["answer_phrase"].startswith("Yes:" if case["truth"] else "No:")
        assert case["pair"] in m["answer_phrase"] and "2024-02-01" in m["answer_phrase"]
        assert ("both played" if case["truth"] else "did not both play") in m["answer_phrase"]
        request = next(
            json.loads(n.split(":", 1)[1]) for n in m["notes"] if n.startswith("yes_no_last_game:")
        )
        assert request["event"] == "played_pair" and request["players"] == case["names"]
        assert (
            request["team"] == "LAL"
            and request["opponent"] == "BOS"
            and request["season"] == "2023-24"
        )
        assert (
            dict(label="Played check", kind="player", value=case["pair"] + " both played")
            in m["applied_filters"]
        )
        assert (
            dict(label="Sample selection", kind="window", value=SELECTION) in m["applied_filters"]
        )
        assert not any(
            f["label"] in ["With player", "Without player"] for f in m["applied_filters"]
        )
        assert CAVEAT in result["caveats"]
        assert set(sections) == {"finder"} and len(sections["finder"]) == 1
        row, truth = sections["finder"][0], case["row"]
        for field, value in truth.items():
            if field == "opponent_pts":
                continue  # This finder supplies plus_minus; its renderer derives the other score.
            if field == "game_date":
                assert (
                    datetime.fromisoformat(str(row[field]).replace("Z", "+00:00"))
                    .date()
                    .isoformat()
                    == value
                )
            else:
                assert row[field] == value
        assert row["plus_minus"] == truth["pts"] - truth["opponent_pts"]
        table = _table(item, "Game log")
        assert len(table["rows"]) == 1
        cells = dict(zip(table["headers"], table["rows"][0]))
        day = date.fromisoformat(truth["game_date"])
        assert cells["Date"] == f"{day:%b} {day.day}"
        assert cells["Team"] == "LALLos Angeles Lakers" and cells["Opp"] == "BOSBoston Celtics"
        assert cells["Score"] == "114-105" and cells["W/L"] == "W"
        assert float(cells["Opp PTS"]) == truth["opponent_pts"]
        assert float(cells["Margin"]) == row["plus_minus"] == 9
        for stat in ["pts", "reb", "ast"]:
            assert float(cells[stat.upper()]) == truth[stat]
    assert seen == {(view, ident) for view in ["desktop", "mobile"] for ident in by_id}


def test_deployed_latest_both_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
