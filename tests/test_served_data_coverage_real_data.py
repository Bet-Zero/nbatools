"""What the served data generation actually covers.

The data catalog declares 1996-97 through 2025-26, regular season and playoffs,
for the core game tables. That declaration is documentation; this module checks
it against the pinned generation itself and prints the coverage report into
the run log, so the R2 validation workflow records which seasons and optional
datasets are really served.

Expected regular-season game counts are league facts (82 games per team, with
the lockout and pandemic seasons and the cancelled 2013 Celtics-Pacers game),
not values read from the data under test.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from nbatools.commands.ops.served_coverage import collect_served_coverage, format_report
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data]

FIRST_SEASON = 1996
LAST_SEASON = 2025
CORE_DATASETS = ("raw/games", "raw/team_game_stats", "raw/player_game_stats")

# Teams x 82 / 2, except the shortened seasons.
_REGULAR_SEASON_GAMES = {
    1998: 725,  # 1998-99 lockout, 50 games
    2011: 990,  # 2011-12 lockout, 66 games
    2012: 1229,  # 2012-13 Celtics-Pacers game cancelled, never replayed
    2019: 1059,  # 2019-20 suspended season
    2020: 1080,  # 2020-21, 72 games
}


def _season(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def _expected_regular_games(year: int) -> int:
    if year in _REGULAR_SEASON_GAMES:
        return _REGULAR_SEASON_GAMES[year]
    teams = 29 if year < 2004 else 30
    return teams * 82 // 2


SEASONS = [_season(year) for year in range(FIRST_SEASON, LAST_SEASON + 1)]


@pytest.fixture(scope="module")
def coverage():
    report = collect_served_coverage()
    return report


def test_print_served_coverage_report(coverage):
    # Emitted as a warning because the workflow runs pytest quietly (and in
    # parallel workers), where printed output is dropped from a passing run;
    # the warnings summary always reaches the log.
    warnings.warn(ServedCoverageReport("\n" + format_report(coverage)), stacklevel=1)
    assert coverage.slices


class ServedCoverageReport(UserWarning):
    """Carries the coverage report into the pytest warnings summary."""


@pytest.mark.parametrize("dataset", CORE_DATASETS)
def test_core_dataset_covers_working_scope(coverage, dataset):
    served = set(coverage.dataset_seasons.get(dataset, []))
    missing = [
        f"{season} {season_type}"
        for season in SEASONS
        for season_type in ("Regular Season", "Playoffs")
        if f"{season} {season_type}" not in served
    ]
    assert not missing, f"{dataset} is missing {missing}"


@pytest.mark.parametrize("season_type", ["Regular Season", "Playoffs"])
@pytest.mark.parametrize("season", SEASONS)
def test_core_slice_validated(coverage, season, season_type):
    # A versioned receipt that passed, or a pre-receipt slice the backfill
    # manifest records as complete. The game-count and key checks below are
    # the independent evidence for both kinds.
    item = coverage.slice(season, season_type)
    assert item is not None, f"{season} {season_type} is not served"
    if item.validation_state == "legacy_unverified":
        assert item.legacy_complete, (season, season_type)
    else:
        assert item.validation_state == "passed", (season, season_type, item.errors)


@pytest.mark.parametrize("year", range(FIRST_SEASON, LAST_SEASON + 1))
def test_regular_season_has_every_game(coverage, year):
    item = coverage.slice(_season(year), "Regular Season")
    assert item is not None
    assert item.final_games == _expected_regular_games(year)


@pytest.mark.parametrize("season", SEASONS)
def test_playoffs_have_a_plausible_game_count(coverage, season):
    item = coverage.slice(season, "Playoffs")
    assert item is not None
    # 16 teams: at least 52 games when first rounds were best-of-five, at most
    # 105 if every series went the distance.
    assert item.final_games is not None and 52 <= item.final_games <= 105, item.final_games


def _final_game_ids(season: str, kind: str) -> set[str]:
    games = data_read_csv(f"raw/games/{season}_{kind}.csv", dtype={"game_id": str})
    flags = games["is_final"].astype(str).str.strip().str.lower()
    return set(games.loc[flags.isin({"1", "true", "1.0"}), "game_id"])


@pytest.mark.parametrize("kind", ["regular_season", "playoffs"])
@pytest.mark.parametrize("season", SEASONS)
def test_box_scores_cover_every_final_game(season, kind):
    final_ids = _final_game_ids(season, kind)
    team = data_read_csv(f"raw/team_game_stats/{season}_{kind}.csv", dtype={"game_id": str})
    per_game = team.groupby("game_id").size()
    assert set(per_game.index) == final_ids
    assert (per_game == 2).all(), per_game[per_game != 2].head().to_dict()

    players = data_read_csv(
        f"raw/player_game_stats/{season}_{kind}.csv",
        dtype={"game_id": str},
        usecols=["game_id", "team_id"],
    )
    assert set(players["game_id"]) == final_ids
    teams_with_players = players.drop_duplicates().groupby("game_id").size()
    assert (teams_with_players == 2).all(), teams_with_players[teams_with_players != 2].head()


def test_report_dates_are_inside_their_season(coverage):
    for item in coverage.slices:
        if item.first_game_date is None:
            continue
        start = int(item.season[:4])
        first = pd.Timestamp(item.first_game_date)
        last = pd.Timestamp(item.last_game_date)
        assert first.year in {start, start + 1}, item.to_dict()
        assert last.year in {start, start + 1}, item.to_dict()


def test_latest_served_season_is_read_from_the_generation(coverage):
    from nbatools.commands import _seasons

    _seasons.reset_latest_served_season_cache()
    # The newest season with a final game in this generation, at least 2025-26.
    # It moves to 2026-27 when those games are published, with no code change.
    for season_type in ("Regular Season", "Playoffs"):
        newest = max(
            item.season
            for item in coverage.slices
            if item.season_type == season_type and item.final_games
        )
        assert newest >= _season(LAST_SEASON)
        assert _seasons.latest_served_season(season_type) == newest


class NameSourceReport(UserWarning):
    """Carries the name-source comparison into the warnings summary."""


def test_report_whether_small_files_carry_every_player_name():
    # The player-name index reads all 60 player-game files (about 145 MB) on a
    # cold start just for names. Report whether the much smaller roster and
    # season-advanced files carry exactly the same names, which would let the
    # index read them instead. Informational: this records evidence only.
    game_names: set[str] = set()
    roster_names: set[str] = set()
    advanced_names: set[str] = set()
    advanced_has_names = True
    for year in range(FIRST_SEASON, LAST_SEASON + 1):
        season = _season(year)
        roster = data_read_csv(f"raw/rosters/{season}.csv", dtype=str)
        roster_names.update(roster.get("player_name", pd.Series(dtype=str)).dropna())
        for kind in ("regular_season", "playoffs"):
            game = data_read_csv(
                f"raw/player_game_stats/{season}_{kind}.csv", usecols=["player_name"], dtype=str
            )
            game_names.update(game["player_name"].dropna())
            advanced = data_read_csv(f"raw/player_season_advanced/{season}_{kind}.csv", dtype=str)
            if "player_name" in advanced.columns:
                advanced_names.update(advanced["player_name"].dropna())
            else:
                advanced_has_names = False
    lines = [
        f"player_game_stats names: {len(game_names)}",
        f"roster names: {len(roster_names)}; in games but not rosters: "
        f"{len(game_names - roster_names)} {sorted(game_names - roster_names)[:15]}; "
        f"in rosters but not games: {len(roster_names - game_names)}",
        f"season-advanced has player_name: {advanced_has_names}; names: {len(advanced_names)}; "
        f"in games but not advanced: {len(game_names - advanced_names)} "
        f"{sorted(game_names - advanced_names)[:15]}",
    ]
    warnings.warn(NameSourceReport("\n" + "\n".join(lines)), stacklevel=1)
    assert game_names
