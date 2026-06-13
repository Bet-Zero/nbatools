"""Descriptive input metadata for structured query routes.

This module is intentionally not a validation layer.  The query service still
owns execution behavior; this registry is for CLI help, docs, and drift checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OneOfGroup:
    """A descriptive set of alternative kwargs accepted by a route."""

    description: str
    options: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class RouteInputMetadata:
    """User-facing metadata for one structured route."""

    route: str
    implementation_module: str
    implementation_function: str
    description: str
    required_kwargs: tuple[str, ...] = ()
    optional_kwargs: tuple[str, ...] = ()
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    one_of_groups: tuple[OneOfGroup, ...] = ()
    allowed_values: dict[str, tuple[str, ...]] = field(default_factory=dict)
    examples: tuple[dict[str, Any], ...] = ()
    notes: tuple[str, ...] = ()
    dispatch_only_kwargs: tuple[str, ...] = ()

    @property
    def implementation_path(self) -> str:
        return f"{self.implementation_module}.{self.implementation_function}"

    @property
    def documented_kwargs(self) -> set[str]:
        names = set(self.required_kwargs)
        names.update(self.optional_kwargs)
        for group in self.one_of_groups:
            for option in group.options:
                names.update(option)
        return names


COMMON_SAMPLE_FILTERS = (
    "season",
    "start_season",
    "end_season",
    "season_type",
    "start_date",
    "end_date",
    "home_only",
    "away_only",
    "wins_only",
    "losses_only",
    "last_n",
)

PLAYER_SAMPLE_FILTERS = COMMON_SAMPLE_FILTERS + (
    "player",
    "team",
    "opponent",
    "opponent_player",
    "without_player",
)

TEAM_SAMPLE_FILTERS = COMMON_SAMPLE_FILTERS + (
    "team",
    "opponent",
    "without_player",
)

SEASON_TYPE_VALUES = ("Regular Season", "Playoffs")
SPLIT_VALUES = ("home_away", "wins_losses")
SORT_BY_VALUES = ("game_date", "stat")
RECORD_STAT_VALUES = ("wins", "losses", "win_pct")
PRESENCE_STATE_VALUES = ("on", "off", "both")
SPECIAL_EVENT_VALUES = ("double_double", "triple_double")
STRETCH_METRIC_VALUES = ("game_score", "pts", "reb", "ast", "ts_pct")
SEASON_LEADER_STAT_VALUES = (
    "pts",
    "reb",
    "oreb",
    "dreb",
    "ast",
    "stl",
    "blk",
    "tov",
    "fg3m",
    "pf",
    "minutes",
    "fgm",
    "fga",
    "fg3a",
    "ftm",
    "fta",
    "fg_pct",
    "fg3_pct",
    "ft_pct",
    "efg_pct",
    "ts_pct",
    "plus_minus",
    "games_played",
    "games_20p",
    "games_30p",
    "games_40p",
    "games_10r",
    "games_10a",
    "usg_pct",
    "ast_pct",
    "reb_pct",
    "tov_pct",
    "net_rating",
    "off_rating",
    "def_rating",
)


ROUTE_INPUT_METADATA: dict[str, RouteInputMetadata] = {
    "top_player_games": RouteInputMetadata(
        route="top_player_games",
        implementation_module="nbatools.commands.top_player_games",
        implementation_function="build_result",
        description="Rank individual player game performances for one stat.",
        required_kwargs=("season", "stat"),
        optional_kwargs=(
            "limit",
            "season_type",
            "ascending",
            "start_date",
            "end_date",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "last_n",
            "opponent",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=(
            {"season": "2005-06", "stat": "pts", "limit": 10},
            {"season": "2025-26", "stat": "ast", "limit": 5},
        ),
        notes=("Requires a single season label; use season_leaders for season averages.",),
    ),
    "top_team_games": RouteInputMetadata(
        route="top_team_games",
        implementation_module="nbatools.commands.top_team_games",
        implementation_function="build_result",
        description="Rank team single-game performances for one stat.",
        required_kwargs=("season", "stat"),
        optional_kwargs=(
            "limit",
            "season_type",
            "ascending",
            "start_date",
            "end_date",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "last_n",
            "opponent",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"season": "2015-16", "stat": "fg3m", "limit": 10},),
    ),
    "season_leaders": RouteInputMetadata(
        route="season_leaders",
        implementation_module="nbatools.commands.season_leaders",
        implementation_function="build_result",
        description="Rank players by season, multi-season, or filtered-window stats.",
        optional_kwargs=(
            "season",
            "stat",
            "limit",
            "season_type",
            "min_games",
            "ascending",
            "start_date",
            "end_date",
            "start_season",
            "end_season",
            "opponent",
            "position",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "last_n",
            "clutch",
            "rookies_only",
            "role",
        ),
        aliases={"limit": ("top_n is a natural-parser slot; direct route calls use limit",)},
        allowed_values={"season_type": SEASON_TYPE_VALUES, "stat": SEASON_LEADER_STAT_VALUES},
        examples=(
            {"season": "2025-26", "stat": "pts", "limit": 10},
            {"season": "2025-26", "stat": "pf", "limit": 10},
            {"start_season": "2020-21", "end_season": "2024-25", "stat": "ast"},
            {"season": "2025-26", "stat": "pts", "rookies_only": True},
        ),
        notes=("Default stat is pts when omitted.",),
    ),
    "season_team_leaders": RouteInputMetadata(
        route="season_team_leaders",
        implementation_module="nbatools.commands.season_team_leaders",
        implementation_function="build_result",
        description="Rank teams by season, multi-season, or filtered-window stats.",
        optional_kwargs=(
            "season",
            "stat",
            "limit",
            "season_type",
            "min_games",
            "ascending",
            "start_date",
            "end_date",
            "start_season",
            "end_season",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "last_n",
        ),
        aliases={"limit": ("top_n is a natural-parser slot; direct route calls use limit",)},
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=(
            {"season": "2025-26", "stat": "pts", "limit": 10},
            {"season": "2025-26", "stat": "net_rating", "ascending": False},
        ),
        notes=("Default stat is pts when omitted.",),
    ),
    "player_game_summary": RouteInputMetadata(
        route="player_game_summary",
        implementation_module="nbatools.commands.player_game_summary",
        implementation_function="build_result",
        description="Summarize a filtered player game sample.",
        optional_kwargs=PLAYER_SAMPLE_FILTERS
        + (
            "special_event",
            "stat",
            "min_value",
            "max_value",
            "clutch",
            "role",
            "back_to_back",
            "rest_days",
            "one_possession",
            "nationally_televised",
            "career_intent",
            "opponent_quality",
        ),
        dispatch_only_kwargs=("opponent_quality",),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "role": ("starter", "bench")},
        examples=(
            {"player": "Nikola Jokic", "season": "2025-26", "last_n": 10},
            {"player": "LeBron James", "season_type": "Playoffs", "stat": "pts"},
        ),
        notes=("Use player for an exact player name or accepted resolver alias.",),
    ),
    "game_summary": RouteInputMetadata(
        route="game_summary",
        implementation_module="nbatools.commands.game_summary",
        implementation_function="build_result",
        description="Summarize a filtered team game sample.",
        optional_kwargs=TEAM_SAMPLE_FILTERS
        + ("stat", "min_value", "max_value", "opponent_quality"),
        dispatch_only_kwargs=("opponent_quality",),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=(
            {"team": "BOS", "season": "2025-26", "home_only": True},
            {"team": "LAL", "start_season": "2021-22", "end_season": "2023-24"},
        ),
    ),
    "player_game_finder": RouteInputMetadata(
        route="player_game_finder",
        implementation_module="nbatools.commands.player_game_finder",
        implementation_function="build_result",
        description="Return player game rows matching stat and context filters.",
        optional_kwargs=PLAYER_SAMPLE_FILTERS
        + (
            "special_event",
            "stat",
            "min_value",
            "max_value",
            "conditions",
            "limit",
            "sort_by",
            "ascending",
            "clutch",
            "quarter",
            "half",
            "role",
            "opponent_quality",
        ),
        dispatch_only_kwargs=("opponent_quality",),
        allowed_values={
            "season_type": SEASON_TYPE_VALUES,
            "sort_by": SORT_BY_VALUES,
            "role": ("starter", "bench"),
        },
        examples=(
            {"player": "Kobe Bryant", "season": "2005-06", "stat": "pts", "min_value": 40},
            {"player": "Nikola Jokic", "conditions": [{"stat": "pts", "min_value": 30}]},
        ),
        notes=("sort_by='stat' requires stat.",),
    ),
    "game_finder": RouteInputMetadata(
        route="game_finder",
        implementation_module="nbatools.commands.game_finder",
        implementation_function="build_result",
        description="Return team game rows matching stat and context filters.",
        optional_kwargs=TEAM_SAMPLE_FILTERS
        + ("stat", "min_value", "max_value", "conditions", "limit", "sort_by", "ascending"),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "sort_by": SORT_BY_VALUES},
        examples=(
            {"team": "BOS", "season": "2025-26", "home_only": True, "wins_only": True},
            {"team": "LAL", "stat": "pts", "min_value": 120, "sort_by": "stat"},
        ),
    ),
    "player_compare": RouteInputMetadata(
        route="player_compare",
        implementation_module="nbatools.commands.player_compare",
        implementation_function="build_result",
        description="Compare two players over the same filtered sample.",
        required_kwargs=("player_a", "player_b"),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "start_date",
            "end_date",
            "season_type",
            "team",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "last_n",
            "head_to_head",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"player_a": "Nikola Jokic", "player_b": "Joel Embiid", "season": "2024-25"},),
    ),
    "team_compare": RouteInputMetadata(
        route="team_compare",
        implementation_module="nbatools.commands.team_compare",
        implementation_function="build_result",
        description="Compare two teams over the same filtered sample.",
        required_kwargs=("team_a", "team_b"),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "start_date",
            "end_date",
            "season_type",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "last_n",
            "head_to_head",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"team_a": "BOS", "team_b": "MIL", "start_season": "2021-22"},),
    ),
    "team_record": RouteInputMetadata(
        route="team_record",
        implementation_module="nbatools.commands.team_record",
        implementation_function="build_team_record_result",
        description="Summarize a team's win/loss record for a filtered sample.",
        required_kwargs=("team",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "opponent",
            "with_player",
            "without_player",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "stat",
            "min_value",
            "max_value",
            "start_date",
            "end_date",
            "clutch",
            "quarter",
            "half",
            "back_to_back",
            "rest_days",
            "one_possession",
            "nationally_televised",
            "opponent_quality",
            "opponent_conference",
            "opponent_division",
        ),
        dispatch_only_kwargs=("opponent_quality", "opponent_conference", "opponent_division"),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=(
            {"team": "LAL", "season": "2025-26"},
            {"team": "BOS", "season": "2025-26", "opponent_conference": "East"},
            {"team": "BOS", "season": "2025-26", "opponent_division": "Atlantic"},
        ),
        notes=("opponent may be a team value or a resolved list of team abbreviations.",),
    ),
    "team_matchup_record": RouteInputMetadata(
        route="team_matchup_record",
        implementation_module="nbatools.commands.team_record",
        implementation_function="build_matchup_record_result",
        description="Summarize head-to-head record for two teams.",
        required_kwargs=("team_a", "team_b"),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "stat",
            "min_value",
            "max_value",
            "start_date",
            "end_date",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"team_a": "LAL", "team_b": "BOS", "season": "2025-26"},),
    ),
    "team_record_leaderboard": RouteInputMetadata(
        route="team_record_leaderboard",
        implementation_module="nbatools.commands.team_record",
        implementation_function="build_record_leaderboard_result",
        description="Rank teams by record-oriented metrics.",
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "stat",
            "opponent",
            "opponent_division",
            "without_player",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "limit",
            "ascending",
            "start_date",
            "end_date",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "stat": RECORD_STAT_VALUES},
        examples=(
            {"season": "2025-26", "stat": "win_pct", "limit": 10},
            {"season": "2025-26", "stat": "win_pct", "opponent_division": "Atlantic"},
        ),
        notes=(
            "Unsupported stat values currently fall back to win_pct in execution.",
            "opponent_division is a dispatch-only natural query filter resolved to opponent teams.",
        ),
        dispatch_only_kwargs=("opponent_division",),
    ),
    "player_split_summary": RouteInputMetadata(
        route="player_split_summary",
        implementation_module="nbatools.commands.player_split_summary",
        implementation_function="build_result",
        description="Summarize a player sample by home/away or wins/losses buckets.",
        required_kwargs=("split",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "player",
            "team",
            "opponent",
            "stat",
            "min_value",
            "max_value",
            "last_n",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "split": SPLIT_VALUES},
        examples=({"split": "home_away", "player": "Nikola Jokic", "season": "2025-26"},),
    ),
    "team_split_summary": RouteInputMetadata(
        route="team_split_summary",
        implementation_module="nbatools.commands.team_split_summary",
        implementation_function="build_result",
        description="Summarize a team sample by home/away or wins/losses buckets.",
        required_kwargs=("split",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "team",
            "opponent",
            "stat",
            "min_value",
            "max_value",
            "last_n",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "split": SPLIT_VALUES},
        examples=({"split": "wins_losses", "team": "BOS", "season": "2025-26"},),
    ),
    "player_streak_finder": RouteInputMetadata(
        route="player_streak_finder",
        implementation_module="nbatools.commands.player_streak_finder",
        implementation_function="build_result",
        description="Find player streaks for stat thresholds or special streak conditions.",
        required_kwargs=("player",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "team",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "stat",
            "min_value",
            "max_value",
            "special_condition",
            "min_streak_length",
            "longest",
            "start_date",
            "end_date",
            "last_n",
            "limit",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=(
            {"player": "Nikola Jokic", "stat": "pts", "min_value": 20, "min_streak_length": 5},
        ),
        notes=("Generic stat streaks require stat; special_condition handles named streaks.",),
    ),
    "team_streak_finder": RouteInputMetadata(
        route="team_streak_finder",
        implementation_module="nbatools.commands.team_streak_finder",
        implementation_function="build_result",
        description="Find team streaks for wins/losses or stat thresholds.",
        required_kwargs=("team",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "stat",
            "min_value",
            "max_value",
            "special_condition",
            "min_streak_length",
            "longest",
            "start_date",
            "end_date",
            "last_n",
            "limit",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"team": "LAL", "special_condition": "win", "longest": True},),
    ),
    "player_occurrence_leaders": RouteInputMetadata(
        route="player_occurrence_leaders",
        implementation_module="nbatools.commands.player_occurrence_leaders",
        implementation_function="build_result",
        description="Rank players by counts of games matching an occurrence definition.",
        one_of_groups=(
            OneOfGroup(
                description="Choose one occurrence mode.",
                options=(
                    ("stat", "min_value"),
                    ("stat", "max_value"),
                    ("special_event",),
                    ("conditions",),
                ),
            ),
        ),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "start_date",
            "end_date",
            "limit",
            "min_games",
            "player",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "special_event": SPECIAL_EVENT_VALUES},
        examples=(
            {"stat": "pts", "min_value": 30, "season": "2024-25", "limit": 5},
            {"conditions": [{"stat": "pts", "min_value": 30}, {"stat": "reb", "min_value": 10}]},
        ),
    ),
    "team_occurrence_leaders": RouteInputMetadata(
        route="team_occurrence_leaders",
        implementation_module="nbatools.commands.team_occurrence_leaders",
        implementation_function="build_result",
        description="Rank teams by counts of games matching an occurrence definition.",
        one_of_groups=(
            OneOfGroup(
                description="Choose one occurrence mode.",
                options=(("stat", "min_value"), ("stat", "max_value"), ("conditions",)),
            ),
        ),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "opponent",
            "home_only",
            "away_only",
            "wins_only",
            "losses_only",
            "start_date",
            "end_date",
            "limit",
            "min_games",
            "team",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=(
            {"stat": "pts", "min_value": 120, "season": "2024-25", "limit": 5},
            {"conditions": [{"stat": "pts", "min_value": 120}, {"stat": "fg3m", "min_value": 15}]},
        ),
    ),
    "player_on_off": RouteInputMetadata(
        route="player_on_off",
        implementation_module="nbatools.commands.player_on_off",
        implementation_function="build_result",
        description="Return trusted on/off splits for a player presence state.",
        required_kwargs=("lineup_members", "presence_state"),
        optional_kwargs=("season", "start_season", "end_season", "season_type", "player", "team"),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "presence_state": PRESENCE_STATE_VALUES},
        examples=(
            {"lineup_members": ["Nikola Jokic"], "presence_state": "both", "season": "2025-26"},
        ),
        notes=(
            "Requires trusted on/off coverage; multi-player on/off is outside "
            "the current contract.",
        ),
    ),
    "lineup_summary": RouteInputMetadata(
        route="lineup_summary",
        implementation_module="nbatools.commands.lineup_summary",
        implementation_function="build_result",
        description="Return trusted summary rows for a requested lineup unit.",
        required_kwargs=("lineup_members",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "team",
            "unit_size",
            "minute_minimum",
            "stat",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"lineup_members": ["Jayson Tatum", "Jaylen Brown"], "unit_size": 2},),
        notes=("Requires trusted lineup coverage.",),
    ),
    "lineup_leaderboard": RouteInputMetadata(
        route="lineup_leaderboard",
        implementation_module="nbatools.commands.lineup_leaderboard",
        implementation_function="build_result",
        description="Rank trusted lineup units.",
        one_of_groups=(
            OneOfGroup(
                description="Identify the lineup scope.",
                options=(("unit_size",), ("lineup_members",)),
            ),
        ),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "team",
            "lineup_members",
            "unit_size",
            "minute_minimum",
            "stat",
            "limit",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"unit_size": 5, "minute_minimum": 200, "limit": 10},),
        notes=("Requires trusted lineup coverage.",),
    ),
    "player_stretch_leaderboard": RouteInputMetadata(
        route="player_stretch_leaderboard",
        implementation_module="nbatools.commands.player_stretch_leaderboard",
        implementation_function="build_result",
        description="Rank rolling player stretches over a requested window size.",
        required_kwargs=("window_size",),
        optional_kwargs=PLAYER_SAMPLE_FILTERS
        + ("stretch_metric", "limit", "dedupe_players", "opponent_quality"),
        dispatch_only_kwargs=("opponent_quality",),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "stretch_metric": STRETCH_METRIC_VALUES},
        examples=(
            {"window_size": 3, "stretch_metric": "pts", "season": "2025-26"},
            {"player": "Devin Booker", "window_size": 4, "stretch_metric": "pts"},
        ),
    ),
    "playoff_history": RouteInputMetadata(
        route="playoff_history",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_playoff_history_result",
        description="Summarize one team's playoff history.",
        required_kwargs=("team",),
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "playoff_round",
            "by_decade",
            "opponent",
        ),
        examples=(
            {"team": "LAL"},
            {"team": "BOS", "start_season": "1980-81", "playoff_round": "Finals"},
        ),
        notes=("playoff_round accepts resolver-supported labels such as Finals or second round.",),
    ),
    "playoff_appearances": RouteInputMetadata(
        route="playoff_appearances",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_playoff_appearances_result",
        description="Show playoff appearance history for a team or rank appearance leaders.",
        optional_kwargs=(
            "team",
            "season",
            "start_season",
            "end_season",
            "playoff_round",
            "limit",
            "ascending",
        ),
        examples=(
            {"team": "LAL", "playoff_round": "Finals"},
            {"playoff_round": "Finals", "start_season": "1980-81", "limit": 10},
        ),
        notes=(
            "Supplying team returns a team history shape; omitting team returns a leaderboard.",
        ),
    ),
    "playoff_matchup_history": RouteInputMetadata(
        route="playoff_matchup_history",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_playoff_matchup_history_result",
        description="Summarize playoff series history between two teams.",
        required_kwargs=("team_a", "team_b"),
        optional_kwargs=("season", "start_season", "end_season", "playoff_round", "by_round"),
        examples=(
            {"team_a": "LAL", "team_b": "BOS"},
            {"team_a": "MIA", "team_b": "NYK", "playoff_round": "Conference Semifinals"},
        ),
    ),
    "playoff_round_record": RouteInputMetadata(
        route="playoff_round_record",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_playoff_round_record_result",
        description="Rank teams by record in a playoff round.",
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "playoff_round",
            "stat",
            "limit",
            "ascending",
        ),
        allowed_values={"stat": RECORD_STAT_VALUES},
        examples=({"playoff_round": "Finals", "start_season": "1980-81", "stat": "win_pct"},),
        notes=("Default stat is win_pct.",),
    ),
    "record_by_decade": RouteInputMetadata(
        route="record_by_decade",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_record_by_decade_result",
        description="Summarize one team's record grouped by decade.",
        required_kwargs=("team",),
        optional_kwargs=("season", "start_season", "end_season", "season_type", "opponent"),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"team": "GSW", "season_type": "Regular Season"},),
    ),
    "record_by_decade_leaderboard": RouteInputMetadata(
        route="record_by_decade_leaderboard",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_record_by_decade_leaderboard_result",
        description="Rank team records within each decade.",
        optional_kwargs=(
            "season",
            "start_season",
            "end_season",
            "season_type",
            "stat",
            "limit",
            "ascending",
            "playoff_round",
        ),
        allowed_values={"season_type": SEASON_TYPE_VALUES, "stat": RECORD_STAT_VALUES},
        examples=({"start_season": "1980-81", "stat": "wins", "limit": 10},),
        notes=("Unsupported stat values currently fall back to wins in execution.",),
    ),
    "matchup_by_decade": RouteInputMetadata(
        route="matchup_by_decade",
        implementation_module="nbatools.commands.playoff_history",
        implementation_function="build_matchup_by_decade_result",
        description="Summarize team-vs-team record grouped by decade.",
        required_kwargs=("team_a", "team_b"),
        optional_kwargs=("season", "start_season", "end_season", "season_type"),
        allowed_values={"season_type": SEASON_TYPE_VALUES},
        examples=({"team_a": "LAL", "team_b": "BOS", "season_type": "Regular Season"},),
    ),
}


def get_route_input_metadata(route: str) -> RouteInputMetadata:
    """Return metadata for a structured route."""

    return ROUTE_INPUT_METADATA[route]


def iter_route_input_metadata() -> tuple[RouteInputMetadata, ...]:
    """Return all route metadata entries sorted by route name."""

    return tuple(ROUTE_INPUT_METADATA[route] for route in sorted(ROUTE_INPUT_METADATA))
