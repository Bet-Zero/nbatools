"""K09 source-bound acceptance; independent expectations predate engine execution."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = (
    Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program/k09-raw-oracle.json"
)
ORACLE_SHA = "35a679ea564698c1fca4669d10d28f89da44a87d6692303b643c59e26718d414"
PRIMARY = ("K09-T1", "K09-P1", "K09-R1", "K09-R2", "K09-W1", "K09-W2", "K09-C1", "K09-C2")
SELECTION = [(i, "query") for i in PRIMARY] + [
    ("K09-R2", "synonym_control_query"),
    ("K09-W1", "last_n_control_query"),
    ("K09-W2", "last_n_control_query"),
    ("K09-C2", "single_season_control_query"),
]


def _qualified_sources():
    raw = ORACLE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORACLE_SHA
    oracle, sources = json.loads(raw), {}
    for name, digest in oracle["source_hashes"].items():
        path = data_path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        with path.open() as stream:
            rows = list(csv.DictReader(stream))
        keys = [(r["game_id"], r.get("player_id", r["team_id"])) for r in rows]
        assert len(set(keys)) == len(keys), name
        sources[name] = rows
    team_rows = [
        row for name, rows in sources.items() if "/team_game_stats/" in name for row in rows
    ]

    def key(row):
        return (row["season"], row["season_type"], row["game_id"], row["team_id"])

    outcomes = {key(row): row["wl"] for row in team_rows}
    assert len(outcomes) == len(team_rows)
    assert set(outcomes.values()) <= {"W", "L"}
    for name, rows in sources.items():
        if "/player_game_stats/" in name:
            sources[name] = [dict(row, wl=outcomes[key(row)]) for row in rows]
    return oracle, sources


@pytest.fixture(scope="module")
def qualified_oracle():
    return _qualified_sources()


def _sample(case, sources, seasons=None):
    subject = case["subject"]
    entity = "player_id" if "player_id" in subject else "team_id"
    kind = "player_game_stats" if entity == "player_id" else "team_game_stats"
    rows = [
        r
        for season in (seasons or case["seasons"])
        for r in sources[f"raw/{kind}/{season}_regular_season.csv"]
        if int(r[entity]) == subject[entity] and (entity == "team_id" or float(r["minutes"]) > 0)
    ]
    return sorted(rows, key=lambda r: (r["game_date"], r["game_id"]))


def _runs(rows, predicate):
    result, active = [], []
    for row in rows:
        ok = all(
            row[key[:-4]] != "" and float(row[key[:-4]]) >= bound
            if key.endswith("_min")
            else row[key] == bound
            for key, bound in predicate.items()
            if key != "minimum_run_length"
        )
        if ok:
            active.append(row)
        elif active:
            result.append(active)
            active = []
    return result + ([active] if active else [])


def _assert_run(actual, expected, selected):
    assert [r["game_id"] for r in selected] == expected["game_ids"]
    assert actual["streak_length"] == actual["games"] == expected["games"]
    assert str(actual["start_date"])[:10] == expected["start_date"]
    assert str(actual["end_date"])[:10] == expected["end_date"]
    assert int(actual["start_game_id"]) == int(expected["game_ids"][0])
    assert int(actual["end_game_id"]) == int(expected["game_ids"][-1])
    for stat in ("pts", "reb", "ast", "fg3m"):
        assert actual[stat + "_avg"] == pytest.approx(
            sum(float(r[stat]) for r in selected) / len(selected), abs=0.00051
        )
    assert actual["wins"] == sum(r["wl"] == "W" for r in selected)
    assert actual["losses"] == sum(r["wl"] == "L" for r in selected)


def _assert_case(result, case, sources, field="query"):
    assert result.result_status == "ok", (case["id"], result.result_reason, result.metadata)
    sections = result.result.to_dict()["sections"]
    expected = case.get(field.replace("_query", "_expected"), case["expected"])
    if field in ("query", "synonym_control_query"):
        expected = case["expected"]
    sample = _sample(case, sources, ["2015-16"] if field == "single_season_control_query" else None)
    if case["id"] == "K09-C1":
        sample = [
            r for r in sample if expected["start_date"] <= r["game_date"] <= expected["end_date"]
        ]
    if "predicate" in case:
        runs = _runs(sample, case["predicate"])
        condition = (
            "wins"
            if "wl" in case["predicate"]
            else "made_three"
            if "fg3m_min" in case["predicate"]
            else "pts>=20"
        )
        assert all(row["condition"] == condition for row in sections["streak"])
        if "count" in expected:
            runs = [r for r in runs if len(r) >= case["predicate"]["minimum_run_length"]]
            assert len(runs) == expected["count"]
            assert sorted(tuple(r["game_id"] for r in run) for run in runs) == sorted(
                tuple(run["game_ids"]) for run in expected["runs"]
            )
            assert sections["count"][0]["count"] == expected["count"]
            assert len(sections["streak"]) == len(runs)
            by_start = {int(r["start_game_id"]): r for r in sections["streak"]}
            for frozen in expected["runs"]:
                selected = next(r for r in runs if r[0]["game_id"] == frozen["game_ids"][0])
                _assert_run(by_start[int(frozen["game_ids"][0])], frozen, selected)
        else:
            selected = max(runs, key=lambda r: (len(r), r[-1]["game_date"]))
            assert len(sections["streak"]) == 1
            _assert_run(sections["streak"][0], expected, selected)
        return
    selected = [
        r for r in sample if expected["start_date"] <= r["game_date"] <= expected["end_date"]
    ]
    assert [r["game_id"] for r in selected] == expected["game_ids"]
    assert len(selected) == expected["games"]
    # Every displayed window has a qualified source sample, not only rank one.
    for row in sections.get("leaderboard", []):
        window = [
            r
            for r in sample
            if str(row["window_start_date"])[:10]
            <= r["game_date"]
            <= str(row["window_end_date"])[:10]
        ]
        assert len(window) == row["window_size"] == expected["games"]
        if case["id"] == "K09-W2":
            assert row["stretch_value"] == pytest.approx(
                sum(int(r["fg3m"]) for r in window) / sum(int(r["fg3a"]) for r in window),
                abs=0.00051,
            )
    if case["id"] == "K09-W1":
        pairs = {
            (r["game_id"], r["team_id"]): r
            for r in sources["raw/team_game_stats/2023-24_regular_season.csv"]
        }
        margin = sum(
            int(r["pts"]) - int(pairs[(r["game_id"], r["opponent_team_id"])]["pts"])
            for r in selected
        )
        assert margin == expected["reciprocal_score_margin_sum"]
        assert sum(r["wl"] == "W" for r in selected) == expected["wins"]
        for row in sections.get("leaderboard", []):
            window = [
                r
                for r in sample
                if str(row["window_start_date"])[:10]
                <= r["game_date"]
                <= str(row["window_end_date"])[:10]
            ]
            assert row["wins"] == sum(r["wl"] == "W" for r in window)
            assert row["losses"] == len(window) - row["wins"]
            assert row["net_per_game"] == pytest.approx(
                sum(
                    int(r["pts"]) - int(pairs[(r["game_id"], r["opponent_team_id"])]["pts"])
                    for r in window
                )
                / len(window),
                abs=0.0051,
            )
        if field == "last_n_control_query":
            assert [r["game_id"] for r in sample[-10:]] == expected["game_ids"]
            assert {int(r["game_id"]) for r in sections["game_log"]} == {
                int(r["game_id"]) for r in selected
            }
            actual = sections["summary"][0]
            for stat in ("pts", "reb", "ast"):
                assert actual[stat + "_avg"] == pytest.approx(
                    sum(float(r[stat]) for r in selected) / len(selected), abs=0.00051
                )
            assert actual["plus_minus_avg"] == expected["net_per_game"]
        else:
            actual = sections["leaderboard"][0]
            assert str(actual["window_start_date"])[:10] == expected["start_date"]
            assert str(actual["window_end_date"])[:10] == expected["end_date"]
            assert actual["net_per_game"] == expected["net_per_game"]
        assert actual["wins"] == expected["wins"] and actual["losses"] == expected["losses"]
    else:
        made = sum(int(r["fg3m"]) for r in selected)
        attempts = sum(int(r["fg3a"]) for r in selected)
        assert (made, attempts) == (expected["made_threes"], expected["three_point_attempts"])
        if field == "last_n_control_query":
            assert [r["game_id"] for r in sample[-5:]] == expected["game_ids"]
        actual = sections["leaderboard"][0]
        assert actual["stretch_metric"] == "fg3_pct"
        assert actual["stretch_value"] == pytest.approx(made / attempts, abs=0.00051)
        assert str(actual["window_start_date"])[:10] == expected["start_date"]
        assert str(actual["window_end_date"])[:10] == expected["end_date"]


@pytest.mark.parametrize("ident,field", SELECTION, ids=[f"{i}-{f}" for i, f in SELECTION])
def test_k09_bound_sequences(qualified_oracle, ident, field):
    oracle, sources = qualified_oracle
    case = next(c for c in oracle["cases"] if c["id"] == ident)
    result = execute_natural_query(case[field])
    route = (
        "team_record" if ident == "K09-W1" and field == "last_n_control_query" else case["route"]
    )
    assert result.metadata["route"] == route
    meta = result.metadata
    assert meta["query_text"] == case[field]
    if "player_id" in case["subject"]:
        assert meta["player"] == "Stephen Curry" and not meta.get("team")
    else:
        assert meta["team"] == case["subject"].get("team_abbr", "MIA")
    _assert_case(result, case, sources, field)
