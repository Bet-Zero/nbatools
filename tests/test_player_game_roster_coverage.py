"""Roster classification coverage, using controlled rows and synthetic games."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.player_game_finder import _apply_roster_filter, build_result
from nbatools.query_service import execute_natural_query


def _games():
    return pd.DataFrame(
        {
            "season": ["2023-24"] * 3,
            "player_id": [41, 42, 43],
            "game_id": ["known-match", "unknown-leader", "known-nonmatch"],
            "pts": [33, 55, 60],
        }
    )


def _roster():
    return pd.DataFrame(
        {
            "season": ["2023-24"] * 3,
            "player_id": [41, 42, 43],
            "position": ["C", "C", "G"],
            "experience_years": [0, 0, 4],
        }
    )


def _filter(monkeypatch, games, rosters, position="centers", rookies=False):
    monkeypatch.setattr("nbatools.data_source.data_exists", lambda path: path.stem in rosters)
    monkeypatch.setattr(
        "nbatools.data_source.data_read_csv", lambda path: rosters[path.stem].copy()
    )
    caveats = []
    kept, note = _apply_roster_filter(games, position, rookies, caveats)
    return kept, note, caveats


@pytest.mark.parametrize(
    ("column", "value", "position", "rookies"),
    [
        ("position", None, "centers", False),
        ("position", "", "centers", False),
        ("position", "unknown", "centers", False),
        ("experience_years", None, None, True),
        ("experience_years", None, "centers", True),
        ("experience_years", "unknown", None, True),
        ("experience_years", -1, None, True),
        ("experience_years", 0.5, None, True),
    ],
)
def test_unknown_requested_values_disclose_incomplete_ranked_population(
    monkeypatch, column, value, position, rookies
):
    roster = _roster().astype({column: "object"})
    roster.loc[roster.player_id == 42, column] = value
    kept, note, caveats = _filter(monkeypatch, _games(), {"2023-24": roster}, position, rookies)
    assert note is None
    assert kept.game_id.tolist() == ["known-match"]
    assert kept.pts.tolist() == [33]
    assert len(caveats) == 1
    assert "Incomplete population" in caveats[0]
    assert "1 games" in caveats[0]


@pytest.mark.parametrize(("position", "rookies"), [("centers", False), (None, True)])
@pytest.mark.parametrize("missing", ["empty", "column", "wrong-season", "file"])
def test_each_season_requires_its_own_requested_schema_and_rows(
    monkeypatch, position, rookies, missing
):
    games = _games().iloc[:2].copy()
    games.loc[games.player_id == 42, "season"] = "1998-99"
    old = _roster().iloc[[1]].copy()
    old["season"] = "1998-99"
    if missing == "empty":
        old = old.iloc[:0]
    elif missing == "column":
        old = old.drop(columns=["position" if position else "experience_years"])
    elif missing == "wrong-season":
        old["season"] = "2023-24"
    rosters = {"2023-24": _roster()}
    if missing != "file":
        rosters["1998-99"] = old
    _, note, caveats = _filter(monkeypatch, games, rosters, position, rookies)
    assert "unavailable for 1998-99" in note
    assert not caveats


def test_zero_byte_roster_is_unavailable(monkeypatch):
    monkeypatch.setattr("nbatools.data_source.data_exists", lambda path: True)

    def empty(path):
        raise pd.errors.EmptyDataError("No columns to parse from file")

    monkeypatch.setattr("nbatools.data_source.data_read_csv", empty)
    _, note = _apply_roster_filter(_games(), "centers", False, [])
    assert "unavailable for 2023-24" in note


def test_unknowns_cannot_establish_no_match(monkeypatch):
    roster = _roster()
    roster.loc[roster.position == "C", "position"] = None
    _, note, caveats = _filter(monkeypatch, _games(), {"2023-24": roster})
    assert "2 candidate games have unknown position classification" in note
    assert "no matching games can be verified" in note
    assert not caveats


def test_fully_classified_nonmatches_can_establish_empty_result(monkeypatch):
    roster = _roster()
    roster["position"] = "G"
    kept, note, caveats = _filter(monkeypatch, _games(), {"2023-24": roster})
    assert kept.empty
    assert note is None
    assert not caveats


@pytest.mark.parametrize(
    ("position", "rookies", "unused"),
    [("centers", False, "experience_years"), (None, True, "position")],
)
def test_unknown_unrequested_attributes_do_not_block_valid_answers(
    monkeypatch, position, rookies, unused
):
    roster = _roster().drop(columns=[unused])
    kept, note, caveats = _filter(monkeypatch, _games(), {"2023-24": roster}, position, rookies)
    assert kept.game_id.tolist() == ["known-match", "unknown-leader"]
    assert kept.pts.tolist() == [33, 55]
    assert note is None
    assert not caveats


def test_duplicate_snapshot_unknown_is_not_negative_evidence(monkeypatch):
    roster = _roster()
    roster.loc[roster.player_id == 42, "position"] = "G"
    duplicate = roster[roster.player_id.isin([41, 42])].copy()
    duplicate["position"] = None
    roster = pd.concat([roster, duplicate], ignore_index=True)
    kept, note, caveats = _filter(monkeypatch, _games(), {"2023-24": roster})
    assert kept.game_id.tolist() == ["known-match"]  # Positive listing remains valid.
    assert note is None
    assert "1 games" in caveats[0]  # Known nonmatch + unknown is still unknown.


def _patch_fixture_roster(monkeypatch, change):
    from nbatools.data_source import data_read_csv

    roster = data_read_csv(Path("data/raw/rosters/2025-26.csv")).copy()
    change(roster)

    def read(path, *args, **kwargs):
        if str(path).endswith("rosters/2025-26.csv"):
            return roster.copy()
        return data_read_csv(path, *args, **kwargs)

    monkeypatch.setattr("nbatools.data_source.data_read_csv", read)
    return roster


@pytest.mark.fixture_data
def test_unknown_center_population_is_unavailable_through_natural_and_structured_paths(monkeypatch):
    def remove_centers(roster):
        roster.loc[roster.position.isin(["C", "C-F"]), "position"] = None

    _patch_fixture_roster(monkeypatch, remove_centers)
    natural = execute_natural_query("top 5 rebounding games by centers in 2025-26").result
    structured = build_result(
        season="2025-26", position="centers", stat="reb", sort_by="stat", limit=5
    )
    for result in (natural, structured):
        payload = result.to_dict()
        assert payload["result_reason"] == "filter_not_supported"
        assert any("classification unavailable" in note for note in payload["notes"])


@pytest.mark.fixture_data
def test_partial_population_still_answers_with_exact_ids_values_and_visible_caveat(monkeypatch):
    from nbatools.data_source import data_read_csv

    raw = data_read_csv(Path("data/raw/player_game_stats/2025-26_regular_season.csv"))
    roster = data_read_csv(Path("data/raw/rosters/2025-26.csv"))
    centers = set(roster.loc[roster.position.isin(["C", "C-F"]), "player_id"])
    leader = raw[raw.player_id.isin(centers)].sort_values("reb", ascending=False).iloc[0].player_id

    def remove_one(roster):
        roster.loc[roster.player_id == leader, "position"] = None

    _patch_fixture_roster(monkeypatch, remove_one)
    expected = sorted(
        (r for r in raw.to_dict("records") if r["player_id"] in centers - {leader}),
        key=lambda r: (r["reb"], r["game_date"]),
        reverse=True,
    )[:5]
    assert expected
    natural = execute_natural_query("top 5 rebounding games by centers in 2025-26").result
    structured = build_result(
        season="2025-26", position="centers", stat="reb", sort_by="stat", limit=5
    )
    for result in (natural, structured):
        payload = result.to_dict()
        actual = payload["sections"]["finder"]
        assert [(r["game_id"], r["player_id"], r["reb"]) for r in actual] == [
            (r["game_id"], r["player_id"], r["reb"]) for r in expected
        ]
        assert [r["rank"] for r in actual] == [1, 2, 3, 4, 5]
        assert {r["population_scope"] for r in actual} == {
            "Incomplete population: known roster classifications only"
        }
        assert any("Incomplete population" in caveat for caveat in payload["caveats"])
        assert "Incomplete population" in result.to_labeled_text()
