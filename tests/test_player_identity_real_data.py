"""Name collisions against the real 1996-97+ player data.

Companion to ``test_player_identity_collisions.py``, which proves the same
behaviour on controlled names and the synthetic fixture. Here the expected
values come from the raw ``player_game_stats`` rows of the pinned generation,
selected by exact player name and aggregated with plain pandas, never through
the summary code under test. Each name must also map to exactly one
``player_id`` in that season, so a shared-name merge cannot pass silently.
"""

from __future__ import annotations

import pytest

from nbatools.commands import entity_resolution
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _expected(name: str, season: str, last_n: int | None = None) -> dict[str, float]:
    frame = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
    rows = frame[frame["player_name"] == name].sort_values(["game_date", "game_id"])
    assert not rows.empty, f"{name} has no {season} rows in this generation"
    assert rows["player_id"].nunique() == 1, f"{name!r} is several players in {season}"
    if last_n is not None:
        rows = rows.tail(last_n)
    return {
        "games": len(rows),
        "pts_sum": float(rows["pts"].sum()),
        "reb_sum": float(rows["reb"].sum()),
    }


def _summaries(query: str) -> dict[str, dict]:
    from nbatools.query_service import execute_natural_query

    entity_resolution.reset_player_index()
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    rows = result.result.to_dict()["sections"]["summary"]
    return {row["player_name"]: row for row in rows}


def _assert_matches(row: dict, expected: dict[str, float]) -> None:
    assert row["games"] == expected["games"]
    assert row["pts_sum"] == pytest.approx(expected["pts_sum"])
    assert row["reb_sum"] == pytest.approx(expected["reb_sum"])


@pytest.mark.parametrize(
    ("query", "name", "season"),
    [
        ("karl anthony towns stats 2023-24", "Karl-Anthony Towns", "2023-24"),
        ("Karl-Anthony Towns stats 2018-19", "Karl-Anthony Towns", "2018-19"),
        ("Carmelo Anthony stats 2012-13", "Carmelo Anthony", "2012-13"),
        ("Nikola Jovic stats 2024-25", "Nikola Jović", "2024-25"),
        ("Tim Hardaway Jr stats 2015-16", "Tim Hardaway Jr.", "2015-16"),
        ("Tim Hardaway stats 1996-97", "Tim Hardaway", "1996-97"),
        ("jaren jackson jr stats 2022-23", "Jaren Jackson Jr.", "2022-23"),
    ],
)
def test_named_season_summary_matches_raw_rows(query, name, season):
    summaries = _summaries(query)
    assert set(summaries) == {name}
    _assert_matches(summaries[name], _expected(name, season))


@pytest.mark.parametrize(
    ("query", "names", "season"),
    [
        ("Luka Dončić vs Nikola Jokić 2023-24", ("Luka Dončić", "Nikola Jokić"), "2023-24"),
        ("nikola jovic vs nikola jokic 2024-25", ("Nikola Jović", "Nikola Jokić"), "2024-25"),
    ],
)
def test_comparison_matches_raw_rows_for_each_player(query, names, season):
    summaries = _summaries(query)
    assert set(summaries) == set(names)
    for name in names:
        _assert_matches(summaries[name], _expected(name, season))


# ---------------------------------------------------------------------------
# Identity by player_id: shared names and renamed players (A1b)
#
# Facts of the pinned generation (raw player_game_stats, all season types):
# "Mike James" is player 2229 (2001-02..2013-14, 628 games) and player
# 1628455 (2017-18..2020-21, 58 games); "Marcus Williams" is 200766 (NJN, ...)
# and 201173 (LAC, SAS), both in 2007-08; "Patrick Ewing" is 121 (1996-97..
# 2001-02) and 201607 (2010-11). Player 1626171 is stored as "Bobby Portis"
# through some 2024-25 rows and "Bobby Portis Jr." in every 2024-25
# regular-season row; 202685 is "Jonas
# Valančiūnas" until 2023-24 and "Jonas Valanciunas" after.
# Expected values are selected from raw rows by player_id here.
# ---------------------------------------------------------------------------

_SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(1996, 2026)]


def _raw_regular_rows(player_id: int, seasons: list[str]):
    import pandas as pd

    from nbatools.data_source import data_exists

    frames = []
    for season in seasons:
        path = f"raw/player_game_stats/{season}_regular_season.csv"
        if not data_exists(path):
            continue
        frame = data_read_csv(path)
        frames.append(frame[frame["player_id"] == player_id])
    rows = pd.concat(frames, ignore_index=True)
    assert not rows.empty, f"player {player_id} has no rows in {seasons[0]}..{seasons[-1]}"
    return rows


def _single_summary(query: str):
    from nbatools.query_service import execute_natural_query

    entity_resolution.reset_player_index()
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    payload = result.result.to_dict()
    rows = payload["sections"]["summary"]
    assert len(rows) == 1, rows
    return rows[0], payload.get("notes") or []


def _assert_row_is(row: dict, raw) -> None:
    assert row["games"] == len(raw)
    assert row["pts_sum"] == pytest.approx(float(raw["pts"].sum()))
    assert row["reb_sum"] == pytest.approx(float(raw["reb"].sum()))


def test_shared_name_career_is_one_player_not_two_careers_added():
    row, notes = _single_summary("mike james career stats")
    raw = _raw_regular_rows(2229, _SEASONS)
    _assert_row_is(row, raw)
    assert any("More than one player is named Mike James" in note for note in notes), notes


def test_shared_name_season_of_one_player_answers_about_him():
    row, notes = _single_summary("mike james stats 2017-18")
    _assert_row_is(row, _raw_regular_rows(1628455, ["2017-18"]))
    assert not any("More than one player" in note for note in notes)


def test_shared_name_with_a_team_picks_that_teams_player():
    row, _ = _single_summary("marcus williams spurs stats 2007-08")
    raw = _raw_regular_rows(201173, ["2007-08"])
    _assert_row_is(row, raw[raw["team_abbr"] == "SAS"])


def test_hall_of_famer_is_the_default_for_his_shared_name():
    row, _ = _single_summary("patrick ewing career stats")
    _assert_row_is(row, _raw_regular_rows(121, _SEASONS))


def test_renamed_player_keeps_every_game_of_the_season():
    row, notes = _single_summary("bobby portis stats 2024-25")
    raw = _raw_regular_rows(1626171, ["2024-25"])
    # The typed spelling is the old one; every 2024-25 regular-season row is
    # stored as "Bobby Portis Jr.", so a name filter found none of them.
    assert set(raw["player_name"]) == {"Bobby Portis Jr."}
    _assert_row_is(row, raw)
    assert not any("More than one player" in note for note in notes)


def test_accent_dropping_rename_keeps_the_whole_career():
    row, _ = _single_summary("jonas valanciunas career stats")
    raw = _raw_regular_rows(202685, _SEASONS)
    assert raw["player_name"].nunique() == 2
    _assert_row_is(row, raw)


def test_season_leaderboard_lists_a_renamed_player_once():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.commands.season_leaders import _build_from_game_logs

    entity_resolution.reset_player_index()
    seasons = ["2023-24", "2024-25"]
    basic = load_player_games_for_seasons(seasons, "Regular Season")
    grouped = _build_from_game_logs(basic)
    portis = grouped[grouped["player_id"] == 1626171]
    raw = _raw_regular_rows(1626171, seasons)
    assert raw["player_name"].nunique() == 2, "the spelling changes across these seasons"
    assert len(portis) == 1
    assert portis.iloc[0]["player_name"] == "Bobby Portis Jr."
    assert portis.iloc[0]["pts_total"] == pytest.approx(float(raw["pts"].sum()))
