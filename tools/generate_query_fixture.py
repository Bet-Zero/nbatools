"""Generate the committed query-engine fixture dataset.

Why this exists
---------------

1036 of 4413 tests carry `needs_data` and skip wherever the local NBA dataset is
absent — which includes CI, on every trigger. Among them are every smoke test
and the whole of `tests/test_filter_execution_integrity.py`, the suite that
guards the invariant that a displayed filter badge corresponds to filtering that
actually ran. That guard has never executed on CI infrastructure.

This generator writes a small, deterministic, internally consistent dataset that
those behavioural tests can run against anywhere. It is **synthetic**: every
number here is invented. That is deliberate and it bounds what the fixture is
for.

What the fixture is for
-----------------------

Tests whose assertion is *behavioural* — "a filter either changes the answer or
is refused", "this route executes rather than crashing", "a split axis is not
mistaken for an unapplied filter". Those hold regardless of whether Jokić really
averaged what the fixture says.

What the fixture is NOT for
---------------------------

Tests asserting a *specific real value* ("Jokić averaged 26.4 points in
2023-24"). Those need the real pinned generation and must stay `needs_data`.
Pointing them at synthetic data would not make them pass; it would make them
wrong.

The trap this generator must avoid
----------------------------------

`assert_filter_applied_or_refused` returns early when the filtered query is
refused, without consulting the control. So a fixture too thin to answer the
*control* queries makes the whole suite pass vacuously — every query refuses for
want of data, every assertion is satisfied, and the safety net is fake. That
would be worse than the current honest skip.

`tests/test_query_fixture_contract.py` is the guard: it asserts every control
query returns a populated answer on this fixture. Regenerating the fixture
without keeping those populated is a failure, not a smaller pass.

Usage
-----

    python tools/generate_query_fixture.py            # write the fixture
    python tools/generate_query_fixture.py --check     # fail if it would change

Determinism: seeded from `RANDOM_SEED`, so the same input always produces
byte-identical CSVs. `--check` is what CI uses to prove the committed fixture
matches this generator.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "qa/fixtures/query_engine_sample"

RANDOM_SEED = 20260927

# ── The seed: everything below is derived from this ───────────────────

# `_seasons.LATEST_REGULAR_SEASON` / `LATEST_PLAYOFF_SEASON` is 2025-26, and an
# unanchored query ("Lakers vs Celtics record", "Lakers playoff history")
# defaults to it. The fixture therefore has to cover that season or every
# unanchored control refuses for want of data — and a refused control is exactly
# the vacuous pass this fixture exists to prevent. 2023-24 is kept because the
# filter-integrity queries name it explicitly, and 2024-25 because one control
# names it.
SEASONS = ("2023-24", "2024-25", "2025-26")
REGULAR = "Regular Season"
PLAYOFFS = "Playoffs"

# Real team ids, taken from the tracked
# `data/raw/teams/team_conference_membership.csv`, so opponent-conference and
# opponent-division resolution behaves as it does in production. Six teams:
# both conferences, and two in the Pacific division.


@dataclass(frozen=True)
class Team:
    team_id: int
    abbr: str
    name: str
    conference: str
    division: str


TEAMS: tuple[Team, ...] = (
    Team(1610612747, "LAL", "Los Angeles Lakers", "West", "Pacific"),
    Team(1610612744, "GSW", "Golden State Warriors", "West", "Pacific"),
    Team(1610612743, "DEN", "Denver Nuggets", "West", "Northwest"),
    Team(1610612738, "BOS", "Boston Celtics", "East", "Atlantic"),
    Team(1610612752, "NYK", "New York Knicks", "East", "Atlantic"),
    Team(1610612748, "MIA", "Miami Heat", "East", "Southeast"),
)
TEAM_BY_ABBR = {team.abbr: team for team in TEAMS}


@dataclass(frozen=True)
class Player:
    player_id: int
    name: str
    team_abbr: str
    position: str  # roster code: G, G-F, F, F-G, F-C, C, C-F
    experience_years: int
    scoring: int  # mean points, shapes the leaderboards
    rebounding: int
    assisting: int


# Names the targeted tests reference by name must exist here: the filter
# integrity suite asks about Jokić and Jamal Murray, and several controls ask
# about the Lakers and the Celtics. Karl-Anthony Towns and Nikola Jović are
# here on purpose: their names contain another player's alias ("anthony" is
# Carmelo Anthony, "nikola" is Jokić), so the identity tests can prove each
# question reaches its own player's rows. Every position group the position filter
# resolves (guards, centers, forwards) has members, or a position-filtered
# leaderboard could not restrict anything.
PLAYERS: tuple[Player, ...] = (
    # Denver — Jokić is a centre, Murray a guard, so "with Jamal Murray" and
    # "among centers" both have something to bite on.
    Player(203999, "Nikola Jokić", "DEN", "C", 8, 27, 12, 9),
    Player(1627750, "Jamal Murray", "DEN", "G", 7, 21, 4, 6),
    Player(1628420, "Aaron Gordon", "DEN", "F", 9, 14, 7, 3),
    Player(1630166, "Christian Braun", "DEN", "G-F", 1, 8, 3, 2),
    Player(203914, "Kentavious Caldwell-Pope", "DEN", "G", 10, 11, 3, 2),
    Player(1631128, "Peyton Watson", "DEN", "F", 1, 6, 3, 1),
    # Los Angeles
    Player(2544, "LeBron James", "LAL", "F", 20, 25, 8, 8),
    Player(1629029, "Luka Dončić", "LAL", "G", 5, 28, 8, 8),
    Player(203076, "Anthony Davis", "LAL", "C-F", 11, 24, 12, 3),
    Player(1630559, "Austin Reaves", "LAL", "G", 2, 15, 4, 5),
    Player(1626156, "Dalton Knecht", "LAL", "G-F", 0, 9, 3, 1),
    Player(1629020, "Rui Hachimura", "LAL", "F", 4, 12, 4, 1),
    # Boston
    Player(1628369, "Jayson Tatum", "BOS", "F", 6, 27, 8, 5),
    Player(1627759, "Jaylen Brown", "BOS", "G-F", 7, 23, 6, 3),
    Player(201950, "Jrue Holiday", "BOS", "G", 14, 12, 5, 5),
    Player(1628464, "Derrick White", "BOS", "G", 6, 15, 4, 5),
    Player(203935, "Kristaps Porziņģis", "BOS", "C", 7, 20, 7, 2),
    Player(1629057, "Robert Williams", "BOS", "C-F", 5, 8, 8, 1),
    # New York
    Player(1628973, "Jalen Brunson", "NYK", "G", 5, 26, 4, 7),
    Player(1626157, "Karl-Anthony Towns", "NYK", "C", 9, 22, 11, 3),
    Player(1629628, "RJ Barrett", "NYK", "G-F", 4, 18, 6, 3),
    Player(1630193, "Immanuel Quickley", "NYK", "G", 3, 13, 3, 4),
    Player(203944, "Julius Randle", "NYK", "F-C", 9, 21, 9, 4),
    Player(1631216, "Miles McBride", "NYK", "G", 2, 7, 2, 2),
    # Golden State
    Player(201939, "Stephen Curry", "GSW", "G", 14, 28, 5, 6),
    Player(202691, "Klay Thompson", "GSW", "G-F", 12, 17, 4, 2),
    Player(203110, "Draymond Green", "GSW", "F-C", 11, 8, 7, 6),
    Player(1630228, "Jonathan Kuminga", "GSW", "F", 3, 16, 5, 2),
    Player(1626172, "Kevon Looney", "GSW", "C", 8, 6, 9, 2),
    Player(1630541, "Brandin Podziemski", "GSW", "G", 1, 10, 5, 4),
    # Miami
    Player(202710, "Jimmy Butler", "MIA", "F-G", 13, 22, 6, 5),
    Player(1629639, "Tyler Herro", "MIA", "G", 5, 20, 5, 5),
    Player(202355, "Bam Adebayo", "MIA", "C", 7, 19, 10, 4),
    Player(1631170, "Jaime Jaquez", "MIA", "G-F", 1, 12, 4, 3),
    Player(203482, "Kelly Olynyk", "MIA", "C-F", 11, 9, 5, 2),
    Player(1631107, "Nikola Jović", "MIA", "F", 2, 8, 4, 2),
)
PLAYERS_BY_TEAM: dict[str, list[Player]] = {
    team.abbr: [player for player in PLAYERS if player.team_abbr == team.abbr] for team in TEAMS
}

# A season starts here and games step forward, so "in January 2024" and
# "since January 1" land inside the 2023-24 fixture season rather than outside
# it.
SEASON_START = {
    "2023-24": date(2023, 10, 24),
    "2024-25": date(2024, 10, 22),
    "2025-26": date(2025, 10, 21),
}

# Each ordered pair of teams meets this many times, so every team has home and
# away games against every other team and `Lakers vs Celtics record` has a
# populated series.
MEETINGS_PER_ORDERED_PAIR = 6

# The postseason: one series, so `Lakers playoff history` is populated.
PLAYOFF_SERIES = ("LAL", "DEN")
PLAYOFF_GAMES = 6


# ── Derivation ────────────────────────────────────────────────────────


@dataclass
class PlayerLine:
    player: Player
    minutes: float
    pts: int
    fgm: int
    fga: int
    fg3m: int
    fg3a: int
    ftm: int
    fta: int
    oreb: int
    dreb: int
    ast: int
    stl: int
    blk: int
    tov: int
    pf: int
    plus_minus: int

    @property
    def reb(self) -> int:
        return self.oreb + self.dreb


@dataclass
class TeamSide:
    team: Team
    opponent: Team
    is_home: bool
    lines: list[PlayerLine]

    def total(self, field: str) -> int:
        return sum(getattr(line, field) for line in self.lines)

    @property
    def pts(self) -> int:
        return self.total("pts")


@dataclass
class Game:
    game_id: str
    season: str
    season_type: str
    game_date: date
    home: TeamSide
    away: TeamSide

    def side(self, team_abbr: str) -> TeamSide:
        return self.home if self.home.team.abbr == team_abbr else self.away

    @property
    def sides(self) -> tuple[TeamSide, TeamSide]:
        return (self.home, self.away)


def _player_line(rng: random.Random, player: Player, force_triple_double: bool) -> PlayerLine:
    """One plausible box-score line, shaped by the player's seed profile."""
    if force_triple_double:
        pts = rng.randint(max(10, player.scoring - 2), player.scoring + 8)
        reb_total = rng.randint(10, 15)
        ast = rng.randint(10, 14)
    else:
        pts = max(0, int(rng.gauss(player.scoring, 6)))
        reb_total = max(0, int(rng.gauss(player.rebounding, 3)))
        ast = max(0, int(rng.gauss(player.assisting, 2)))

    fg3a = rng.randint(0, 10) if player.position.startswith(("G", "F")) else rng.randint(0, 3)
    fg3m = rng.randint(0, fg3a) if fg3a else 0
    fga = max(fg3a, int(pts / 2) + rng.randint(1, 6))
    fgm = min(fga, max(fg3m, int(pts * 0.4)))
    fta = rng.randint(0, 8)
    ftm = rng.randint(0, fta) if fta else 0
    oreb = min(reb_total, rng.randint(0, 4))

    return PlayerLine(
        player=player,
        minutes=round(rng.uniform(18.0, 38.0), 1),
        pts=pts,
        fgm=fgm,
        fga=fga,
        fg3m=fg3m,
        fg3a=fg3a,
        ftm=ftm,
        fta=fta,
        oreb=oreb,
        dreb=reb_total - oreb,
        ast=ast,
        stl=rng.randint(0, 4),
        blk=rng.randint(0, 3),
        tov=rng.randint(0, 5),
        pf=rng.randint(0, 5),
        plus_minus=rng.randint(-18, 18),
    )


def _build_side(
    rng: random.Random, team: Team, opponent: Team, is_home: bool, triple_double_for: int | None
) -> TeamSide:
    lines = [
        _player_line(rng, player, force_triple_double=player.player_id == triple_double_for)
        for player in PLAYERS_BY_TEAM[team.abbr]
    ]
    return TeamSide(team=team, opponent=opponent, is_home=is_home, lines=lines)


def build_games(rng: random.Random) -> list[Game]:
    """Every game in the fixture, regular season then postseason."""
    games: list[Game] = []
    counter = 0

    for season in SEASONS:
        day = SEASON_START[season]
        # Deterministic double round robin: every ordered pair, so each team
        # hosts and visits each other team.
        matchups = [
            (home, away) for home in TEAMS for away in TEAMS if home.abbr != away.abbr
        ] * MEETINGS_PER_ORDERED_PAIR

        for index, (home_team, away_team) in enumerate(matchups):
            counter += 1
            # A triple-double every seventh game, always to the home team's
            # highest-usage player, so "most triple doubles" has a real ranking
            # and the leader is stable across regenerations.
            td_player = None
            if index % 7 == 0:
                td_player = max(PLAYERS_BY_TEAM[home_team.abbr], key=lambda p: p.scoring).player_id

            games.append(
                Game(
                    game_id=f"00{counter:08d}",
                    season=season,
                    season_type=REGULAR,
                    game_date=day,
                    home=_build_side(rng, home_team, away_team, True, td_player),
                    away=_build_side(rng, away_team, home_team, False, None),
                )
            )
            _break_tie(games[-1])
            day += timedelta(days=2)

    # One postseason series in the later season.
    playoff_season = SEASONS[-1]
    day = SEASON_START[playoff_season] + timedelta(days=200)
    first, second = (TEAM_BY_ABBR[abbr] for abbr in PLAYOFF_SERIES)
    for game_number in range(PLAYOFF_GAMES):
        counter += 1
        home_team, away_team = (first, second) if game_number % 2 == 0 else (second, first)
        games.append(
            Game(
                game_id=f"00{counter:08d}",
                season=playoff_season,
                season_type=PLAYOFFS,
                game_date=day,
                home=_build_side(rng, home_team, away_team, True, None),
                away=_build_side(rng, away_team, home_team, False, None),
            )
        )
        _break_tie(games[-1])
        day += timedelta(days=2)

    return games


def _wl(side: TeamSide, other: TeamSide) -> str:
    return "W" if side.pts > other.pts else "L"


def _break_tie(game: Game) -> None:
    """No game may end level: `_wl` would record both sides as losses.

    Deterministic and minimal - one point to the home side's leading scorer.
    Team totals are summed from the player lines, so the box score stays
    internally consistent without a second edit.
    """
    if game.home.pts != game.away.pts:
        return
    leader = max(game.home.lines, key=lambda line: (line.pts, -line.player.player_id))
    leader.pts += 1


# ── Emission ──────────────────────────────────────────────────────────


def _tenths(value: float) -> int:
    """A one-decimal value as an exact integer count of tenths."""
    return round(value * 10)


def _mean_one_dp(tenths: list[int]) -> str:
    """Mean of integer tenths, to one decimal place, as an exact string.

    Deliberately integer-only. Python 3.12 gave `sum()` compensated summation
    for floats (gh-100425), so summing float minutes produces a very slightly
    different result on 3.11 than on 3.12+. One rolling average in this fixture
    landed exactly on a rounding boundary and `round(..., 1)` flipped 23.3 to
    23.4, making the committed fixture fail its own `--check` on half the CI
    matrix.

    Summing integers and rounding half-up by hand has no such freedom: the
    output is identical on every interpreter.
    """
    total = sum(tenths)
    count = len(tenths)
    rounded = (total * 10 + count // 2) // count  # hundredths, half-up
    whole, remainder = divmod((rounded + 5) // 10, 10)
    return f"{whole}.{remainder}"


def _write(files: dict[str, str], relative: str, header: list[str], rows: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    files[relative] = buffer.getvalue()


def _season_groups(games: list[Game]) -> dict[tuple[str, str], list[Game]]:
    groups: dict[tuple[str, str], list[Game]] = {}
    for game in games:
        groups.setdefault((game.season, game.season_type), []).append(game)
    return groups


def _suffix(season_type: str) -> str:
    return "regular_season" if season_type == REGULAR else "playoffs"


def emit(games: list[Game]) -> dict[str, str]:
    """Render every dataset as CSV text, keyed by path relative to the root."""
    files: dict[str, str] = {}

    for (season, season_type), season_games in _season_groups(games).items():
        tag = f"{season}_{_suffix(season_type)}"

        # raw/games and raw/schedule share a shape.
        game_rows = [
            {
                "game_id": game.game_id,
                "season": game.season,
                "season_type": game.season_type,
                "game_date": game.game_date.isoformat(),
                "is_final": "True",
                "home_team_id": game.home.team.team_id,
                "away_team_id": game.away.team.team_id,
                "site_type": "home_away",
                "neutral_site": "False",
                "home_away_designation_trusted": "True",
                "home_away_source": "fixture",
            }
            for game in season_games
        ]
        games_header = list(game_rows[0])
        _write(files, f"raw/games/{tag}.csv", games_header, game_rows)
        _write(
            files,
            f"raw/schedule/{tag}.csv",
            [column for column in games_header if column != "is_final"],
            [{k: v for k, v in row.items() if k != "is_final"} for row in game_rows],
        )
        _write(
            files,
            f"processed/game_features/{tag}.csv",
            ["game_id", "season", "season_type", "game_date", "home_team_id", "away_team_id"],
            [
                {
                    key: row[key]
                    for key in (
                        "game_id",
                        "season",
                        "season_type",
                        "game_date",
                        "home_team_id",
                        "away_team_id",
                    )
                }
                for row in game_rows
            ],
        )

        # raw/team_game_stats — totals are summed from the player lines, so the
        # two datasets can never disagree.
        team_rows: list[dict] = []
        for game in season_games:
            for side, other in ((game.home, game.away), (game.away, game.home)):
                team_rows.append(
                    {
                        "game_id": game.game_id,
                        "team_id": side.team.team_id,
                        "team_abbr": side.team.abbr,
                        "team_name": side.team.name,
                        "season": game.season,
                        "season_type": game.season_type,
                        "game_date": game.game_date.isoformat(),
                        "opponent_team_id": other.team.team_id,
                        "opponent_team_abbr": other.team.abbr,
                        "opponent_team_name": other.team.name,
                        "is_home": str(side.is_home),
                        "is_away": str(not side.is_home),
                        "wl": _wl(side, other),
                        "minutes": 240.0,
                        "pts": side.pts,
                        "fgm": side.total("fgm"),
                        "fga": side.total("fga"),
                        "fg3m": side.total("fg3m"),
                        "fg3a": side.total("fg3a"),
                        "ftm": side.total("ftm"),
                        "fta": side.total("fta"),
                        "oreb": side.total("oreb"),
                        "dreb": side.total("dreb"),
                        "reb": side.total("reb"),
                        "ast": side.total("ast"),
                        "stl": side.total("stl"),
                        "blk": side.total("blk"),
                        "tov": side.total("tov"),
                        "pf": side.total("pf"),
                        "plus_minus": side.pts - other.pts,
                    }
                )
        _write(files, f"raw/team_game_stats/{tag}.csv", list(team_rows[0]), team_rows)

        # raw/player_game_stats
        player_rows: list[dict] = []
        for game in season_games:
            for side, other in ((game.home, game.away), (game.away, game.home)):
                for line in side.lines:
                    player_rows.append(
                        {
                            "game_id": game.game_id,
                            "team_id": side.team.team_id,
                            "team_abbr": side.team.abbr,
                            "team_name": side.team.name,
                            "player_id": line.player.player_id,
                            "player_name": line.player.name,
                            "season": game.season,
                            "season_type": game.season_type,
                            "game_date": game.game_date.isoformat(),
                            "opponent_team_id": other.team.team_id,
                            "opponent_team_abbr": other.team.abbr,
                            "opponent_team_name": other.team.name,
                            "is_home": str(side.is_home),
                            "is_away": str(not side.is_home),
                            "wl": _wl(side, other),
                            "minutes": line.minutes,
                            "pts": line.pts,
                            "fgm": line.fgm,
                            "fga": line.fga,
                            "fg3m": line.fg3m,
                            "fg3a": line.fg3a,
                            "ftm": line.ftm,
                            "fta": line.fta,
                            "oreb": line.oreb,
                            "dreb": line.dreb,
                            "reb": line.reb,
                            "ast": line.ast,
                            "stl": line.stl,
                            "blk": line.blk,
                            "tov": line.tov,
                            "pf": line.pf,
                            "plus_minus": line.plus_minus,
                        }
                    )
        _write(files, f"raw/player_game_stats/{tag}.csv", list(player_rows[0]), player_rows)

        # raw/player_game_starter_roles — the five highest scorers by seed
        # profile start, so starter/bench filters have trusted coverage for
        # every player-game rather than a partial leaderboard.
        role_rows: list[dict] = []
        for game in season_games:
            for side in game.sides:
                ranked = sorted(side.lines, key=lambda ln: -ln.player.scoring)
                starters = {line.player.player_id for line in ranked[:5]}
                for line in side.lines:
                    role_rows.append(
                        {
                            "game_id": game.game_id,
                            "season": game.season,
                            "season_type": game.season_type,
                            "team_id": side.team.team_id,
                            "player_id": line.player.player_id,
                            "starter_position_raw": line.player.position,
                            "starter_flag": str(line.player.player_id in starters),
                            "role_source": "fixture",
                            "role_source_trusted": "True",
                            "starter_count_for_team_game": 5,
                            "role_validation_reason": "",
                        }
                    )
        _write(files, f"raw/player_game_starter_roles/{tag}.csv", list(role_rows[0]), role_rows)

        # processed/team_game_features and schedule_context_features — rest and
        # schedule context derived from each team's own ordered game dates.
        by_team: dict[int, list[tuple[date, Game, TeamSide, TeamSide]]] = {}
        for game in season_games:
            for side, other in ((game.home, game.away), (game.away, game.home)):
                by_team.setdefault(side.team.team_id, []).append(
                    (game.game_date, game, side, other)
                )

        feature_rows: list[dict] = []
        context_rows: list[dict] = []
        for entries in by_team.values():
            entries.sort(key=lambda item: item[0])
            previous: date | None = None
            for game_date, game, side, other in entries:
                rest = 3 if previous is None else (game_date - previous).days - 1
                back_to_back = rest == 0
                margin = side.pts - other.pts
                feature_rows.append(
                    {
                        "game_id": game.game_id,
                        "team_id": side.team.team_id,
                        "season": game.season,
                        "season_type": game.season_type,
                        "game_date": game_date.isoformat(),
                        "days_rest": rest,
                        "is_back_to_back": str(back_to_back),
                    }
                )
                context_rows.append(
                    {
                        "game_id": game.game_id,
                        "season": game.season,
                        "season_type": game.season_type,
                        "game_date": game_date.isoformat(),
                        "team_id": side.team.team_id,
                        "team_abbr": side.team.abbr,
                        "team_name": side.team.name,
                        "opponent_team_id": other.team.team_id,
                        "opponent_team_abbr": other.team.abbr,
                        "opponent_team_name": other.team.name,
                        "is_home": str(side.is_home),
                        "is_away": str(not side.is_home),
                        "rest_days": rest,
                        "opponent_rest_days": rest,
                        "back_to_back": str(back_to_back),
                        "rest_advantage": 0,
                        "score_margin": margin,
                        "one_possession": str(abs(margin) <= 3),
                        "nationally_televised": str(game.game_date.day % 5 == 0),
                        "national_tv_source": "fixture",
                        "national_tv_source_trusted": "True",
                        "schedule_context_source": "fixture",
                        "schedule_context_source_trusted": "True",
                    }
                )
        _write(
            files, f"processed/team_game_features/{tag}.csv", list(feature_rows[0]), feature_rows
        )
        _write(
            files,
            f"processed/schedule_context_features/{tag}.csv",
            list(context_rows[0]),
            context_rows,
        )

        # processed/player_game_features — trailing five-game form.
        by_player: dict[int, list[tuple[date, Game, TeamSide, PlayerLine]]] = {}
        for game in season_games:
            for side in game.sides:
                for line in side.lines:
                    by_player.setdefault(line.player.player_id, []).append(
                        (game.game_date, game, side, line)
                    )
        pgf_rows: list[dict] = []
        for entries in by_player.values():
            entries.sort(key=lambda item: item[0])
            for index, (game_date, game, side, line) in enumerate(entries):
                window = entries[max(0, index - 4) : index + 1]
                pgf_rows.append(
                    {
                        "game_id": game.game_id,
                        "team_id": side.team.team_id,
                        "player_id": line.player.player_id,
                        "season": game.season,
                        "season_type": game.season_type,
                        "game_date": game_date.isoformat(),
                        "minutes_last_5": _mean_one_dp(
                            [_tenths(item[3].minutes) for item in window]
                        ),
                        "pts_last_5": _mean_one_dp([item[3].pts * 10 for item in window]),
                    }
                )
        _write(files, f"processed/player_game_features/{tag}.csv", list(pgf_rows[0]), pgf_rows)

        # raw/standings_snapshots — one end-of-span snapshot per team.
        snapshot_day = max(game.game_date for game in season_games)
        standings_rows = []
        for team in TEAMS:
            entries = by_team.get(team.team_id, [])
            wins = sum(1 for _d, _g, side, other in entries if _wl(side, other) == "W")
            played = len(entries)
            standings_rows.append(
                {
                    "team_id": team.team_id,
                    "snapshot_date": snapshot_day.isoformat(),
                    "season": season,
                    "season_type": season_type,
                    "wins": wins,
                    "losses": played - wins,
                    "win_pct": round(wins / played, 3) if played else 0.0,
                }
            )
        _write(files, f"raw/standings_snapshots/{tag}.csv", list(standings_rows[0]), standings_rows)

        # raw/team_season_advanced
        adv_rows = []
        for team in TEAMS:
            entries = by_team.get(team.team_id, [])
            scored = sum(side.pts for _d, _g, side, _o in entries)
            allowed = sum(other.pts for _d, _g, _s, other in entries)
            possessions = max(1, len(entries)) * 100
            off = round(scored / possessions * 100, 1)
            dfn = round(allowed / possessions * 100, 1)
            adv_rows.append(
                {
                    "team_id": team.team_id,
                    "as_of_date": snapshot_day.isoformat(),
                    "season": season,
                    "season_type": season_type,
                    "off_rating": off,
                    "def_rating": dfn,
                    "net_rating": round(off - dfn, 1),
                    "pace": 100.0,
                }
            )
        _write(files, f"raw/team_season_advanced/{tag}.csv", list(adv_rows[0]), adv_rows)

        # raw/player_season_advanced
        padv_rows = []
        for player_id, entries in sorted(by_player.items()):
            points = sum(item[3].pts for item in entries)
            attempts = sum(item[3].fga for item in entries)
            throws = sum(item[3].fta for item in entries)
            denominator = 2 * (attempts + 0.44 * throws) or 1
            padv_rows.append(
                {
                    "player_id": player_id,
                    "as_of_date": snapshot_day.isoformat(),
                    "season": season,
                    "season_type": season_type,
                    "usage_rate": round(min(45.0, attempts / max(1, len(entries)) * 2.2), 1),
                    "ts_pct": round(points / denominator, 3),
                }
            )
        _write(files, f"raw/player_season_advanced/{tag}.csv", list(padv_rows[0]), padv_rows)

        # processed/league_season_stats
        total_games = len(team_rows)
        _write(
            files,
            f"processed/league_season_stats/{tag}.csv",
            [
                "season",
                "season_type",
                "games",
                "avg_pts",
                "avg_fg3m",
                "avg_fg3a",
                "avg_fg3_pct",
                "avg_reb",
                "avg_tov",
            ],
            [
                {
                    "season": season,
                    "season_type": season_type,
                    "games": len(season_games),
                    "avg_pts": round(sum(r["pts"] for r in team_rows) / total_games, 1),
                    "avg_fg3m": round(sum(r["fg3m"] for r in team_rows) / total_games, 1),
                    "avg_fg3a": round(sum(r["fg3a"] for r in team_rows) / total_games, 1),
                    "avg_fg3_pct": round(
                        sum(r["fg3m"] for r in team_rows)
                        / max(1, sum(r["fg3a"] for r in team_rows)),
                        3,
                    ),
                    "avg_reb": round(sum(r["reb"] for r in team_rows) / total_games, 1),
                    "avg_tov": round(sum(r["tov"] for r in team_rows) / total_games, 1),
                }
            ],
        )

    # raw/rosters — one file per season, no season_type.
    for season in SEASONS:
        roster_rows = [
            {
                "player_id": player.player_id,
                "team_id": TEAM_BY_ABBR[player.team_abbr].team_id,
                "season": season,
                "stint": 1,
                "player_name": player.name,
                "jersey_number": 10 + index,
                "position": player.position,
                "height": "6-7",
                "weight": 220,
                "birth_date": "1995-01-01",
                "experience_years": player.experience_years,
                "school": "Fixture University",
            }
            for index, player in enumerate(PLAYERS)
        ]
        _write(files, f"raw/rosters/{season}.csv", list(roster_rows[0]), roster_rows)

    # The tracked conference membership table, copied in so opponent-conference
    # and opponent-division resolution behaves as it does in production.
    source = REPO_ROOT / "data/raw/teams/team_conference_membership.csv"
    files["raw/teams/team_conference_membership.csv"] = source.read_text(encoding="utf-8")

    return files


# ── Entry point ───────────────────────────────────────────────────────


def build() -> dict[str, str]:
    """Render the whole fixture. Standard library only, by design.

    `--check` runs inside the docs-governance CI job, which installs no project
    dependencies. Importing the engine here to validate seed names broke that
    job outright, so the seed-name guard lives in
    `tests/test_query_fixture_contract.py` instead, where pandas is present and
    it runs on every Python in the test matrix.
    """
    return emit(build_games(random.Random(RANDOM_SEED)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed fixture differs from what this generator produces",
    )
    args = parser.parse_args()

    files = build()
    data_root = FIXTURE_ROOT / "data"

    if args.check:
        problems: list[str] = []
        for relative, content in sorted(files.items()):
            path = data_root / relative
            if not path.exists():
                problems.append(f"missing: {path.relative_to(REPO_ROOT)}")
            elif path.read_text(encoding="utf-8") != content:
                problems.append(f"differs: {path.relative_to(REPO_ROOT)}")
        expected = {(data_root / relative).resolve() for relative in files}
        for path in sorted(data_root.rglob("*.csv")):
            if path.resolve() not in expected:
                problems.append(f"unexpected: {path.relative_to(REPO_ROOT)}")
        if problems:
            print("committed fixture does not match tools/generate_query_fixture.py:")
            for problem in problems:
                print(f"  {problem}")
            print("\nregenerate with: python tools/generate_query_fixture.py")
            return 1
        print(f"fixture check passed ({len(files)} files)")
        return 0

    expected = {(data_root / relative).resolve() for relative in files}
    removed = 0
    if data_root.exists():
        for path in sorted(data_root.rglob("*.csv")):
            if path.resolve() not in expected:
                path.unlink()
                removed += 1

    for relative, content in sorted(files.items()):
        path = data_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    for directory in sorted(data_root.rglob("*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    total = sum(len(content.encode("utf-8")) for content in files.values())
    suffix = f", removed {removed} stale" if removed else ""
    print(
        f"wrote {len(files)} files ({total / 1024:.0f} KiB){suffix} to "
        f"{FIXTURE_ROOT.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
