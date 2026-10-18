"""Finite K04 queries checked against the independently frozen raw-row oracle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path, data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/k04-independent-oracle.json"
)
ORACLE = json.loads(ORACLE_PATH.read_text())
CASES = ORACLE["cases"]
KEYS = ["game_id", "team_id", "player_id"]


def verify_answer(case, response):
    assert response.result_status == "ok", (case["id"], response.result_reason, response.metadata)
    result = response.result.to_dict()
    sections = result["sections"]
    expected_routes = (
        {"season_leaders", "player_occurrence_leaders"}
        if case["id"] == "K04-D1"
        else {"player_occurrence_leaders"}
        if case["id"] == "K04-D2"
        else {"season_leaders"}
        if case["kind"] == "player_board"
        else {"player_game_finder"}
        if case["kind"] == "ranked_games"
        else {"player_game_summary"}
    )
    assert response.route in expected_routes
    if case["kind"] == "player_board":
        rows = sections["leaderboard"]
        expected = case["expected"]
        assert len(rows) == len(expected) == 5
        assert [r["player_name"] for r in rows] == [r["player_name"] for r in expected]
        assert [r["rank"] for r in rows] == list(range(1, 6))
        assert [r["games_played"] for r in rows] == [r["games"] for r in expected]
        columns = {
            "pts": "pts_total",
            "ppg": "pts_per_game",
            "fg3_pct_ratio": "fg3_pct",
            "ft_pct_ratio": "ft_pct",
        }
        metric = columns.get(case["metric"])
        if metric is None:
            metric = (
                ("games_40p" if response.route == "season_leaders" else "games_pts_40+")
                if case["id"] == "K04-D1"
                else "games_ast_10+_tov_0"
            )
        assert [r[metric] for r in rows] == pytest.approx([r["metric"] for r in expected])
        for actual, truth in zip(rows, expected):
            if "player_id" in actual:
                assert actual["player_id"] == truth["player_id"]
        for column in ("fg3a", "fta"):
            minimum = case["qualifiers"].get("min_" + column)
            if minimum is not None:
                assert [r[column + "_total"] for r in rows] == [r[column] for r in expected]
                assert f"at least {minimum}" in " ".join(result["caveats"])
        assert all("2023-24" in str(r) for r in rows)
    else:
        rows = sections["finder" if case["kind"] == "ranked_games" else "game_log"]
        assert len(rows) == case["limit"]
        # Named finder omits team_id; reconstruct it only from the exact
        # source-qualified abbreviation, never from an arbitrary display label.
        team_by_abbr = {"GSW": 1610612744, "NYK": 1610612752}
        identities = []
        for row in rows:
            team_id = team_by_abbr[row["team_abbr"]]
            assert (
                row["player_name"]
                == {201939: "Stephen Curry", 1628973: "Jalen Brunson"}[case["player_id"]]
            )
            if "team_id" in row:
                assert int(row["team_id"]) == team_id
            identities.append([int(row["game_id"]), team_id, int(row["player_id"])])
            assert row["season"] == "2023-24"
            assert row["season_type"] == "Regular Season"
        assert len({tuple(key) for key in identities}) == len(rows)
        if case["kind"] == "ranked_games":
            assert identities == case["expected_ordered_ids"]
            assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))
        else:
            assert sorted(identities) == sorted(case["expected_ordered_ids"])
            dates = [(str(row["game_date"]), int(row["game_id"])) for row in rows]
            assert dates == sorted(dates)
        expected_by_id = {row["game_id"]: row for row in case["expected_rows"]}
        for row in rows:
            expected = expected_by_id[int(row["game_id"])]
            for stat in ("pts", "reb", "ast"):
                assert row[stat] == expected[stat]
        if case["kind"] == "last_games_summary":
            summary = sections["summary"][0]
            assert summary["games"] == case["limit"]
            for stat, value in case["averages"].items():
                assert summary[stat + "_avg"] == pytest.approx(value, abs=0.001)
                assert summary[stat + "_sum"] == case["sums"][stat]


def verify_source(case, source):
    """Confirm each frozen source-key set and arithmetic before testing consumers."""
    if case["kind"] == "player_board":
        for expected in case["expected"]:
            player = source.loc[source.player_id.eq(expected["player_id"])]
            assert (
                sorted(map(list, player[KEYS].astype(int).to_numpy()))
                == expected["source_game_ids"]
            )
            assert player.game_id.nunique() == expected["games"]
            assert player.pts.sum() == expected["pts_total"]
            for column in ("fg3m", "fg3a", "ftm", "fta"):
                assert player[column].sum() == expected[column]
            if case["metric"] == "event_count":
                mask = (
                    player.pts.ge(40)
                    if case["id"] == "K04-D1"
                    else player.ast.ge(10) & player.tov.eq(0)
                )
                assert (
                    sorted(map(list, player.loc[mask, KEYS].astype(int).to_numpy()))
                    == expected["matching_game_ids"]
                )
    else:
        player = source.loc[source.player_id.eq(case["player_id"])]
        if case["kind"] == "ranked_games":
            sample = player.sort_values(["pts", "game_date"], ascending=[False, False]).head(
                case["limit"]
            )
        else:
            sample = player.sort_values(["game_date", "game_id"], ascending=[False, False]).head(
                case["limit"]
            )
        assert sample[KEYS].astype(int).values.tolist() == case["expected_ordered_ids"]
        for stat, value in case["sums"].items():
            assert sample[stat].sum() == value


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
@pytest.mark.parametrize("wording", ["query", "heldout_query"], ids=["primary", "heldout"])
def test_k04_rankings_match_frozen_raw_oracle(case, wording):
    path = "data/raw/player_game_stats/2023-24_regular_season.csv"
    assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == ORACLE["source_sha256"]
    source = data_read_csv(path)
    verify_source(case, source)
    verify_answer(case, execute_natural_query(case[wording]))
