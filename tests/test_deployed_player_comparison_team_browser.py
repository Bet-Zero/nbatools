"""Historical shared-team comparisons and lossless source checks through the UI."""

import copy
import csv
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_original_stat_pair_browser import _cases as _stat_cases
from tests.test_deployed_original_stat_pair_browser import _validate_answers as _validate_stat
from tests.test_deployed_union_pair_browser import _identity, _table

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-ClijrUhz.js", "player-comparison-team-browser"
FIXTURES = Path(__file__).parent / "fixtures/player_comparison_team_scope"
GENERATION = "availability-opening-s4-v1-20261017"


def _load(name, digest):
    path = FIXTURES / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    return json.loads(path.read_text())


def _cases():
    primary = _load(
        "source_and_baseline.json",
        "4d77fb2982004cf073dbdc2865db2437cfc82f9a8f57d478b14f6ae19c460205",
    )
    held = _load(
        "revealed_checker_controls.json",
        "dccd27e2d12ae93b6c4f2b37e957a3dd07c82dd142c2c98c6e7b3308fe1ee867",
    )
    fresh = _load(
        "browser_checker_suffix_controls.json",
        "b040130168b3d4596b378c8a8400adbdb41f7865b116445e4f530dfeb48ebb91",
    )
    for document in (primary, held, fresh):
        assert document["generation"] == GENERATION
        for path, digest in document["source_hashes"].items():
            assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        with data_path(f"raw/{kind}/2024-25_regular_season.csv").open() as stream:
            return list(csv.DictReader(stream))

    players, games, teams = [raw(k) for k in ("player_game_stats", "games", "team_game_stats")]
    assert len({(r["player_id"], r["game_id"]) for r in players}) == len(players)
    assert len({(r["game_id"], r["team_id"]) for r in teams}) == len(teams)

    def sample(frozen, team, opponent, bounds=None, *, frozen_is_filtered=False):
        pid = frozen["player_id"]
        selected = [
            r
            for r in players
            if int(r["player_id"]) == pid
            and r["team_abbr"] == team
            and r["opponent_team_abbr"] == opponent
            and float(r["minutes"]) > 0
        ]
        selected.sort(key=lambda r: (r["game_date"], int(r["game_id"])))
        # The complete independently frozen sample must equal physical rows,
        # before applying a newly displayed exact count predicate.
        frozen_rows = sorted(
            frozen["selected_rows"], key=lambda r: (r["game_date"], int(r["game_id"]))
        )
        qualified = selected
        if bounds:
            low, high, low_inclusive, high_inclusive = bounds
            qualified = [
                r
                for r in selected
                if (
                    low is None
                    or (
                        Decimal(r["pts"]) >= Decimal(low)
                        if low_inclusive
                        else Decimal(r["pts"]) > Decimal(low)
                    )
                )
                and (
                    high is None
                    or (
                        Decimal(r["pts"]) <= Decimal(high)
                        if high_inclusive
                        else Decimal(r["pts"]) < Decimal(high)
                    )
                )
            ]
        # Fresh suffix-II facts were themselves frozen under this exact bound.
        if frozen_is_filtered:
            assert qualified == frozen_rows
        else:
            assert selected == frozen_rows
        wins = 0
        for row in selected:
            catalog = [r for r in games if r["game_id"] == row["game_id"]]
            own = [
                r
                for r in teams
                if r["game_id"] == row["game_id"] and r["team_id"] == row["team_id"]
            ]
            other = [
                r
                for r in teams
                if r["game_id"] == row["game_id"] and r["team_id"] == row["opponent_team_id"]
            ]
            assert len(catalog) == len(own) == len(other) == 1
            assert catalog[0]["is_final"] == "1"
            assert (
                catalog[0]["game_date"]
                == own[0]["game_date"]
                == other[0]["game_date"]
                == row["game_date"]
            )
            assert {catalog[0]["home_team_id"], catalog[0]["away_team_id"]} == {
                row["team_id"],
                row["opponent_team_id"],
            }
            assert (
                own[0]["opponent_team_id"] == other[0]["team_id"]
                and other[0]["opponent_team_id"] == own[0]["team_id"]
            )
            assert (own[0]["wl"] == "W") == (int(own[0]["pts"]) > int(other[0]["pts"]))
            if row in qualified:
                wins += own[0]["wl"] == "W"
        return dict(
            player_name=frozen["player_name"],
            player_id=pid,
            games=len(qualified),
            game_ids=[int(r["game_id"]) for r in qualified],
            wins=wins,
            losses=len(qualified) - wins,
            totals={s: sum(int(r[s]) for r in qualified) for s in ("pts", "reb", "ast")},
        )

    independent = held["positive_controls"]
    wiggins_dennis = [independent[2]["source_samples"][0], independent[0]["source_samples"][1]]
    specs = [
        (
            "comparison-shared-primary",
            primary["primary_query"],
            "LAL",
            "GSW",
            primary["source_samples"],
            None,
            None,
        ),
        (
            "comparison-canonical-alias",
            independent[0]["query"],
            "GSW",
            "LAL",
            independent[0]["source_samples"],
            None,
            None,
        ),
        (
            "comparison-omitted-suffix",
            fresh["positive_controls"][0]["query"],
            "ORL",
            "BOS",
            fresh["positive_controls"][0]["source_samples"],
            None,
            None,
        ),
        (
            "comparison-exact-partial-empty",
            "Compare Andrew Wiggins and Dennis Schroder for Warriors against Lakers in 2024-25 with at most 19.999999999999999 points",
            "GSW",
            "LAL",
            wiggins_dennis,
            (None, "19.999999999999999", True, True),
            "<= 19.999999999999999 PTS (integer execution: <= 19 PTS)",
        ),
        (
            "comparison-count-empty",
            "Compare Andrew Wiggins and Dennis Schroder for Warriors against Lakers in 2024-25 with between 0.1 and 0.9 points",
            "GSW",
            "LAL",
            wiggins_dennis,
            ("0.1", "0.9", True, True),
            ">= 0.1 and <= 0.9 PTS (integer execution: >= 1 and <= 0 PTS)",
        ),
        (
            "comparison-suffix-exact-count",
            fresh["positive_controls"][1]["query"],
            "DAL",
            "HOU",
            fresh["positive_controls"][1]["source_samples"],
            ("6.0000000000000001", None, False, True),
            "> 6.0000000000000001 PTS (integer execution: >= 7 PTS)",
        ),
    ]
    cases = []
    for ident, query, team, opponent, frozen, bounds, label in specs:
        expected = [
            sample(
                s,
                team,
                opponent,
                bounds,
                frozen_is_filtered=ident == "comparison-suffix-exact-count",
            )
            for s in frozen
        ]
        base = frozen[0]["selected_rows"][0]
        team_context = _identity(team, ["2024-25"], int(base["team_id"]))
        opponent_context = _identity(opponent, ["2024-25"], int(base["opponent_team_id"]))
        text = (
            ["No Matching Results"]
            if not any(s["games"] for s in expected)
            else [s["player_name"] for s in expected]
        )
        text += [f"PLAYING FOR\n{team}", f"OPPONENT\n{opponent}", "2024-25"]
        if label:
            text.append("COUNT FILTER\n" + label)
        cases.append(
            dict(
                id=ident,
                query=query,
                kind="comparison",
                team=team,
                opponent=opponent,
                team_context=team_context,
                opponent_context=opponent_context,
                expected=expected,
                count_label=label,
                text=text,
                forbidden=[
                    "Unavailable Filter",
                    "Can't answer that one yet",
                    "With player",
                    "Without player",
                    "WITH PLAYER",
                    "WITHOUT PLAYER",
                    "undefined",
                    "NaN",
                    "Infinity",
                ],
            )
        )
    cases.append(
        dict(
            id="comparison-unread-split",
            kind="unsupported",
            query="Compare Andrew Wiggins and Dennis Schroder for Warriors against Lakers in 2024-25 at home and on the road",
            text=["Can't answer that one yet"],
            forbidden=[
                "Unavailable Filter",
                "No Matching Results",
                "PLAYING FOR",
                "OPPONENT",
                "Team split",
                "undefined",
                "NaN",
                "Infinity",
            ],
        )
    )
    hauser = copy.deepcopy(_stat_cases()[2])
    hauser["id"] = "comparison-hauser-precision"
    hauser["kind"] = "original-stat-pair"
    hauser["query"] = (
        "Did Sam Hauser play fewer than 22.6500000000000001 minutes and record at most 0 assists in the Celtics last game against Lakers in 2023-24?"
    )
    previous = hauser["minutes_description"]
    hauser["minutes_description"] = "< 22.6500000000000001 minutes"
    hauser["text"] = [t.replace(previous, hauser["minutes_description"]) for t in hauser["text"]]
    cases.append(hauser)
    assert len(cases) == 8
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
        assert item["http"] == 200 and not any(
            item[k] for k in ("errors", "missing", "forbidden", "grainErrors")
        )
        assert all(t in item["text"] for t in case["text"]) and not any(
            t in item["text"] for t in case["forbidden"]
        )
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
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
        if case["kind"] == "original-stat-pair":
            phrase = payload["result"]["metadata"]["answer_phrase"]
            assert case["minutes_description"] in phrase and case["count_description"] in phrase
            assert phrase in item["text"]
            continue
        assert payload["route"] == "player_compare"
        m, sections = payload["result"]["metadata"], payload["result"]["sections"]
        if case["kind"] == "unsupported":
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "unsupported"
            )
            assert (
                not sections
                and not item["tables"]
                and not m.get("answer_phrase")
                and not m.get("applied_filters")
            )
            continue
        names = [s["player_name"] for s in case["expected"]]
        assert m["player"] == ", ".join(names)
        assert m["players_context"] == [
            dict(player_id=s["player_id"], player_name=s["player_name"]) for s in case["expected"]
        ]
        assert m["team"] == case["team"] and m["opponent"] == case["opponent"]
        assert (
            m["team_context"] == case["team_context"]
            and m["opponent_context"] == case["opponent_context"]
        )
        assert m["season"] == "2024-25" and m["season_type"] == "Regular Season"
        assert not m["with_player"] and not m["without_player"] and not m["head_to_head_used"]
        assert not m.get("opponents") and not m.get("opponent_team_abbrs")
        assert m["last_n"] is None and m["start_date"] is None and m["end_date"] is None
        assert dict(label="Playing for", kind="team", value=case["team"]) in m["applied_filters"]
        assert dict(label="Opponent", kind="team", value=case["opponent"]) in m["applied_filters"]
        labels = [f["value"] for f in m["applied_filters"] if f["label"] == "Count filter"]
        assert labels == ([case["count_label"]] if case["count_label"] else [])
        if case["count_label"]:
            minimum, maximum = {
                "comparison-exact-partial-empty": (None, 19),
                "comparison-count-empty": (1, 0),
                "comparison-suffix-exact-count": (7, None),
            }[case["id"]]
            condition = dict(
                stat="pts",
                min_value=minimum,
                max_value=maximum,
                text=case["query"].rsplit(" with ", 1)[1],
            )
            assert m["stat"] == "pts" and m["min_value"] == minimum and m["max_value"] == maximum
            assert m["threshold_conditions"] == [condition] and m["conditions"] == [condition]
        else:
            assert m["stat"] is None and m["min_value"] is None and m["max_value"] is None
            assert not m["threshold_conditions"] and not m.get("conditions")
        if not any(s["games"] for s in case["expected"]):
            assert (
                payload["result_status"] == "no_result" and payload["result_reason"] == "no_match"
            )
            assert not sections and not item["tables"] and not m.get("answer_phrase")
            continue
        assert payload["result_status"] == "ok" and payload["result_reason"] is None
        assert not m.get("unsupported_filters") and m.get("intent") != "unsupported"
        assert not any("unsupported_boundary" in str(n) for n in m.get("notes", []))
        assert set(sections) == {"summary", "comparison"} and len(sections["summary"]) == 2
        table = _table(item, "Comparison metrics")
        assert table["headers"][1:3] == names and not table["footers"]
        displayed = {r[0]: r for r in table["rows"]}
        metrics = {r["metric"]: r for r in sections["comparison"]}
        assert len(metrics) == len(sections["comparison"])
        for col, (actual, expected) in enumerate(zip(sections["summary"], case["expected"]), 1):
            assert actual["player_name"] == expected["player_name"]
            for metric in ("games", "wins", "losses"):
                assert (
                    actual[metric] == expected[metric]
                    and metrics[metric][expected["player_name"]] == expected[metric]
                )
            assert int(displayed["Games"][col]) == expected["games"]
            assert displayed["Record"][col] == f"{expected['wins']}-{expected['losses']}"
            for stat in ("pts", "reb", "ast"):
                assert actual[stat + "_sum"] == expected["totals"][stat]
                assert metrics[stat + "_sum"][expected["player_name"]] == expected["totals"][stat]
                avg = (
                    round(expected["totals"][stat] / expected["games"], 3)
                    if expected["games"]
                    else None
                )
                assert (
                    actual[stat + "_avg"] == avg
                    and metrics[stat + "_avg"][expected["player_name"]] == avg
                )
                if avg is None:
                    assert displayed[stat.upper() + " Avg"][col] == "-"
                else:
                    assert float(displayed[stat.upper() + " Avg"][col]) == pytest.approx(
                        avg, abs=0.051
                    )
            if not expected["games"]:
                assert all(
                    value is None
                    for metric, value in actual.items()
                    if metric.endswith("_avg") or metric == "win_pct"
                )
    assert seen == {(view, ident) for view in ("desktop", "mobile") for ident in by_id}
    stat_case = next(c for c in cases if c["kind"] == "original-stat-pair")
    subset = dict(receipt, receipts=[r for r in receipt["receipts"] if r["id"] == stat_case["id"]])
    _validate_stat(subset, [stat_case], output)


def test_deployed_player_comparison_team_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
