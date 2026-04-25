# Data Contracts

This document defines the core dataset contracts for `nbatools`.

The goal is to keep query behavior stable as the repo grows. Commands should depend on explicit dataset contracts, not on accidental columns or vague assumptions.

This is a living document. Update it whenever:

- a dataset grain changes
- required columns change
- a new derived dataset becomes a core dependency
- a command starts depending on a new dataset or field

---

## Contract rules

For each dataset, this document should define:

- path pattern
- grain
- key fields
- required columns
- important derived columns
- producer(s)
- consumer(s)

### General rules

- commands should only depend on documented required columns
- optional columns should be treated as optional, never assumed
- sample-aware metrics must document their source dataset
- new derived datasets should be added here before they become widely depended on
- new datasets should be additive, clearly scoped, and placed in the correct lifecycle layer (`raw`, `processed`, or `derived`)
- extending an existing canonical dataset requires explicit rationale and must not silently repurpose the table's contract
- trust and coverage fields are required for partially supported or gated execution paths
- mixed-grain semantics (for example, game-level with stint-level or play-by-play-derived rows) must not be hidden inside legacy tables without an explicit approved contract

---

## 1. `player_game_stats`

### Path pattern

`data/raw/player_game_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/player_game_stats/2025-26_regular_season.csv`
- `data/raw/player_game_stats/2024-25_playoffs.csv`

### Grain

One row per **player-game**.

### Key fields

- `game_id`
- `player_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `player_id`)

### Required columns

These are the baseline fields query behavior should be able to rely on:

- `game_id`
- `game_date`
- `season`
- `season_type`
- `player_id`
- `player_name`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_abbr`
- `matchup`
- `wl`
- `minutes`
- `pts`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `plus_minus`

### Important derived/query fields

Some commands may also rely on these fields if they are present or built during processing/loading:

- `is_home`
- `is_away`
- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`

### Producer(s)

- raw ingestion commands that pull player game logs from the NBA data source
- any cleanup/standardization layer that normalizes the raw pull into the contract above

### Primary consumer(s)

- `player_game_finder`
- `player_game_summary`
- `player_compare`
- `player_split_summary`
- `player_streak_finder`
- natural-query player finder/summary/comparison/split/streak routes
- grouped boolean execution over player game samples

### Notes

This is one of the most important datasets in the repo.

Legacy `start_position` and `starter_flag` columns may appear in the current raw file because the historical `LeagueGameFinder` pull shape exposed a `START_POSITION` column name. They are not authoritative for starter / bench execution and must not be treated as a role contract.

Player sample-aware metrics such as:

- USG%
- AST%
- REB%

ultimately depend on filtered player-game samples built from this contract and season-level supporting context.

---

## 1A. `player_game_starter_roles`

### Path pattern

`data/raw/player_game_starter_roles/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/player_game_starter_roles/2025-26_regular_season.csv`
- `data/raw/player_game_starter_roles/2024-25_playoffs.csv`

### Grain

One row per **player-game role observation**.

### Key fields

- `game_id`
- `player_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `player_id`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `team_id`
- `player_id`
- `starter_position_raw`
- `starter_flag`
- `role_source`
- `role_source_trusted`
- `starter_count_for_team_game`
- `role_validation_reason`

### Important derived/query fields

- `team_abbr`
- `player_name`

These are convenience fields only. Commands should join the role dataset back to `player_game_stats` for the rest of the player/game context.

### Producer(s)

- `src/nbatools/commands/pipeline/pull_player_game_starter_roles.py`, a dedicated backfill command that fans out over `data/raw/games/{season}_{season_type_safe}.csv`
- the upstream NBA per-game box score endpoint `BoxScoreTraditionalV3.PlayerStats.position`
- any future compatibility layer that normalizes an alternate upstream source into this same contract

### Primary consumer(s)

- starter / bench execution for `player_game_summary`
- starter / bench execution for `player_game_finder`
- future role-aware player routes that explicitly opt into the same contract

### Notes

This dataset is the authoritative starter / bench source for player-context natural-query execution.

Contract rules:

- `role_source` should identify the normalized upstream source, currently `boxscore_traditional_v3.position`
- `starter_flag` is derived from non-empty `starter_position_raw`
- rows may only be used for execution when `role_source_trusted=1`
- at minimum, trust requires exactly 5 starter-marked players in the row's `(game_id, team_id)` group
- if trust fails, `role_validation_reason` must explain why, such as `starter_count_not_five`
- if a requested role-filtered slice depends on rows that are missing or untrusted in this dataset, commands must keep the current honest fallback note instead of partially filtering or fabricating bench assignments
- refreshed seasons treat this dataset as part of the required raw pipeline contract alongside `player_game_stats`

---

## 1B. `player_game_period_stats`

### Path pattern

`data/raw/player_game_period_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/player_game_period_stats/2025-26_regular_season.csv`
- `data/raw/player_game_period_stats/2024-25_playoffs.csv`

### Grain

One row per **player-game period window** for the supported period semantics.

### Key fields

- `game_id`
- `player_id`
- `period_family`
- `period_value`

Recommended uniqueness expectation:

- unique on (`game_id`, `player_id`, `period_family`, `period_value`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `game_date`
- `period_family`
- `period_value`
- `source_start_period`
- `source_end_period`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `wl`
- `player_id`
- `player_name`
- `minutes`
- `pts`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `oreb`
- `dreb`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `pf`
- `plus_minus`

### Important derived/query fields

- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`
- `usg_pct`
- `ast_pct`
- `reb_pct`
- `tov_pct`
- `comment`

### Producer(s)

- `src/nbatools/commands/pipeline/pull_game_period_stats.py`, which fans out over
  `data/raw/games/{season}_{season_type_safe}.csv`
- `BoxScoreTraditionalV3` period-window requests for the traditional box-score totals
- `BoxScoreAdvancedV3` period-window requests for the player-only rate fields needed by
  `player_game_finder`

### Primary consumer(s)

- quarter / half / overtime execution on `player_game_finder`
- future player-context routes that explicitly opt into the same period-window contract

### Notes

This dataset is the authoritative period-window source for the initial player route boundary.

Contract rules:

- `BoxScoreTraditionalV3` is the source of record for player-grain period windows and owns
  the traditional box-score columns in this table
- `BoxScoreAdvancedV3` is an explicit player-only enrichment path for `usg_pct`, `ast_pct`,
  `reb_pct`, and `tov_pct`; the initial team route boundary does not depend on AdvancedV3
- supported period semantics are represented as explicit `period_family` / `period_value`
  pairs:
  - `quarter` with values `1`, `2`, `3`, `4`
  - `half` with values `first`, `second`
  - `overtime` with value `OT`
- `source_start_period` / `source_end_period` record the exact upstream window used to
  materialize the row:
  - quarters: `1-1`, `2-2`, `3-3`, `4-4`
  - halves: `1-2`, `3-4`
  - overtime: `5-14`, aggregated into one `OT` row only when the returned window shows real
    overtime activity
- this contract is period-only; it does not define `clutch`, and no consumer may treat these
  rows as a clutch-capable substitute
- commands should treat missing or incomplete season files for this dataset as a coverage
  failure and fall back to the current honest unfiltered-results note instead of partially
  mixing whole-game and period-window rows

---

## 1C. `play_by_play_events` and derived clutch stats

The approved source path for clutch execution is official `PlayByPlayV3` event
data plus local score-state derivation. This is documented in
[`docs/planning/clutch_source_boundary.md`](../planning/clutch_source_boundary.md).

The raw `play_by_play_events` dataset path, validation, and loader exist. The
processed `player_game_clutch_stats` and `team_game_clutch_stats` derivation
paths, validation, and loaders also exist. Current clutch queries remain
unfiltered with an explicit note until route execution is implemented.

### Raw path

`data/raw/play_by_play_events/{season}_{season_type_safe}.csv`

### Raw grain

One row per NBA play-by-play event.

### Raw key fields

- `season`
- `season_type`
- `game_id`
- `action_number`

### Raw required columns

- `season`
- `season_type`
- `game_id`
- `action_number`
- `period`
- `clock`
- `clock_seconds_remaining`
- `team_id`
- `team_abbr`
- `player_id`
- `player_name`
- `action_type`
- `sub_type`
- `description`
- `score_home`
- `score_away`
- `pbp_source`
- `pbp_source_trusted`
- `pbp_validation_reason`

### Derived paths

- `data/processed/player_game_clutch_stats/{season}_{season_type_safe}.csv`,
  at one row per player-game clutch sample keyed by `season`, `season_type`,
  `game_id`, `team_id`, and `player_id`
- `data/processed/team_game_clutch_stats/{season}_{season_type_safe}.csv`, at
  one row per team-game clutch sample keyed by `season`, `season_type`,
  `game_id`, and `team_id`

Derived clutch rows include `clutch_window`,
`clutch_time_remaining_start`, `clutch_score_margin_max`, `clutch_events`,
`clutch_seconds`, event-derived `pts`, `clutch_source`,
`clutch_source_trusted`, and `clutch_validation_reason`.

Contract rules:

- clutch means last five minutes of the fourth quarter or overtime with the
  score within five points
- raw play-by-play rows must have parseable clocks, parseable home/away score
  state, unique event keys, and trusted event ordering
- whole-game logs and period-only box-score windows must not be used as clutch
  substitutes
- route execution may only use derived clutch rows when source trust and
  score-state validation pass for the requested slice
- missing or untrusted coverage must keep the current honest
  unfiltered-results note rather than partially filtering results
- rate and efficiency metrics may only ship after their sample denominators are
  validated against the play-by-play derivation

---

## 1D. `team_player_on_off_summary`

The approved future source path for `player_on_off` execution is the upstream
`teamplayeronoffsummary` split table, called through
`nba_api.stats.endpoints.TeamPlayerOnOffSummary`. This is documented in
[`docs/planning/phase_i_on_off_source_boundary.md`](../planning/phase_i_on_off_source_boundary.md).

This section defines the approved raw source dataset for `player_on_off`
execution. The route may only use rows when validation marks the requested
single-player slice trusted; missing or untrusted coverage keeps the explicit
unsupported/no-result response.

### Path pattern

`data/raw/team_player_on_off_summary/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/team_player_on_off_summary/2025-26_regular_season.csv`
- `data/raw/team_player_on_off_summary/2024-25_playoffs.csv`

### Grain

One row per **team / queried player / presence-state season split**.

The upstream source exposes separate on-court and off-court row groups. The
normalized dataset should combine them into one table with explicit
`presence_state` values.

### Key fields

- `season`
- `season_type`
- `team_id`
- `player_id`
- `presence_state`

Recommended uniqueness expectation:

- unique on (`season`, `season_type`, `team_id`, `player_id`, `presence_state`)

### Required columns

- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `team_name`
- `player_id`
- `player_name`
- `presence_state`
- `court_status_raw`
- `gp`
- `minutes`
- `plus_minus`
- `off_rating`
- `def_rating`
- `net_rating`
- `source_endpoint`
- `source_pull_date`
- `source_schema_version`
- `coverage_trusted`
- `coverage_validation_reason`

### Producer(s)

- `src/nbatools/commands/pipeline/pull_team_player_on_off_summary.py`,
  wrapping
  `nba_api.stats.endpoints.TeamPlayerOnOffSummary`
- any future compatibility layer that normalizes an alternate upstream on/off
  split source into this same contract

### Primary consumer(s)

- future `player_on_off` execution

### Notes

Contract rules:

- `PlayersOnCourtTeamPlayerOnOffSummary` rows should normalize to
  `presence_state=on`
- `PlayersOffCourtTeamPlayerOnOffSummary` rows should normalize to
  `presence_state=off`
- source `VS_PLAYER_ID` / `VS_PLAYER_NAME` should normalize to `player_id` /
  `player_name`
- possessions are not exposed by the approved minimum source; route execution
  should use `minutes` and `gp` as the sample-size fields unless a later
  approved source adds possessions
- route execution may only use rows when both `on` and `off` states exist for
  the requested player/team/season slice and `coverage_trusted=1`
- missing or untrusted coverage must keep the existing honest unsupported-data
  response instead of fabricating or partially filtering on/off splits
- whole-game `without_player` absence remains a separate team/game-log filter
  and must not be treated as on/off execution

---

## 1E. `league_lineup_viz`

The approved source path for `lineup_summary` and `lineup_leaderboard`
execution is the upstream `leaguelineupviz` lineup-unit table, called through
`nba_api.stats.endpoints.LeagueLineupViz`. This is documented in
[`docs/planning/phase_j_lineup_source_boundary.md`](../planning/phase_j_lineup_source_boundary.md).

This raw source dataset path, validation, loader, and coverage-gated route
execution exist. Missing or untrusted coverage returns an explicit
unsupported/no-result response.

### Path pattern

`data/raw/league_lineup_viz/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/league_lineup_viz/2025-26_regular_season.csv`
- `data/raw/league_lineup_viz/2024-25_playoffs.csv`

### Grain

One row per **team lineup unit / unit size / minimum-minute threshold season
split**.

### Key fields

- `season`
- `season_type`
- `team_id`
- `unit_size`
- `lineup_id`
- `minute_minimum`

Recommended uniqueness expectation:

- unique on (`season`, `season_type`, `team_id`, `unit_size`, `lineup_id`,
  `minute_minimum`)

### Required columns

- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `unit_size`
- `lineup_id`
- `lineup_name`
- `player_ids`
- `player_names`
- `minute_minimum`
- `minutes`
- `off_rating`
- `def_rating`
- `net_rating`
- `pace`
- `ts_pct`
- `source_endpoint`
- `source_pull_date`
- `source_schema_version`
- `coverage_trusted`
- `coverage_validation_reason`

### Important derived/query fields

- `player_ids` should be a normalized, deterministic membership list parsed
  from source `GROUP_ID`
- `player_names` should be a normalized membership list parsed from source
  `GROUP_NAME`
- `lineup_id` should preserve the stable source membership key so specific
  lineup queries and leaderboard rows agree

### Producer(s)

- `src/nbatools/commands/pipeline/pull_league_lineup_viz.py`, wrapping
  `nba_api.stats.endpoints.LeagueLineupViz`
- any future compatibility layer that normalizes an alternate upstream
  lineup-unit source into this same contract

### Primary consumer(s)

- `lineup_summary` execution
- `lineup_leaderboard` execution

### Notes

Contract rules:

- source `GROUP_ID` / `GROUP_NAME` are the lineup membership source of record
- source `MinutesMin` should normalize to `minute_minimum`
- route execution may only use rows when the parsed membership count matches
  `unit_size` and `coverage_trusted=1`
- possessions and games represented are not exposed by the approved minimum
  source; route execution should use `minutes` as the sample-size field unless a
  later approved enrichment source adds possessions or games
- missing or untrusted coverage must keep the existing honest unsupported-data
  response instead of fabricating or partially filtering lineup-unit results
- roster membership remains an identity/enrichment source only and must not be
  treated as lineup-unit execution

---

## 2. `team_game_stats`

### Path pattern

`data/raw/team_game_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/team_game_stats/2025-26_regular_season.csv`
- `data/raw/team_game_stats/2024-25_playoffs.csv`

### Grain

One row per **team-game**.

### Key fields

- `game_id`
- `team_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `team_id`)

### Required columns

- `game_id`
- `game_date`
- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_abbr`
- `matchup`
- `wl`
- `pts`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `plus_minus`

### Important derived/query fields

- `is_home`
- `is_away`
- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`

### Producer(s)

- raw ingestion commands that pull team game logs from the NBA data source
- any cleanup/standardization layer that normalizes the raw pull into this contract

### Primary consumer(s)

- `game_finder`
- `game_summary`
- `team_compare`
- `team_split_summary`
- `team_streak_finder`
- natural-query team finder/summary/comparison/split/streak routes
- grouped boolean execution over team game samples

### Notes

This is the core team query dataset. Team summary, split, and streak behaviors should be designed around this contract.

---

## 2A. `team_game_period_stats`

### Path pattern

`data/raw/team_game_period_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/team_game_period_stats/2025-26_regular_season.csv`
- `data/raw/team_game_period_stats/2024-25_playoffs.csv`

### Grain

One row per **team-game period window** for the supported period semantics.

### Key fields

- `game_id`
- `team_id`
- `period_family`
- `period_value`

Recommended uniqueness expectation:

- unique on (`game_id`, `team_id`, `period_family`, `period_value`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `game_date`
- `period_family`
- `period_value`
- `source_start_period`
- `source_end_period`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `wl`
- `minutes`
- `pts`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `oreb`
- `dreb`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `pf`
- `plus_minus`

### Important derived/query fields

- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`

### Producer(s)

- `src/nbatools/commands/pipeline/pull_game_period_stats.py`, which fans out over
  `data/raw/games/{season}_{season_type_safe}.csv`
- `BoxScoreTraditionalV3` period-window requests for the team-grain period totals

### Primary consumer(s)

- quarter / half / overtime execution on `team_record`
- future team-context routes that explicitly opt into the same period-window contract

### Notes

This dataset is the authoritative period-window source for the initial team route boundary.

Contract rules:

- `BoxScoreTraditionalV3` is the source of record for team-grain period windows
- supported period semantics are represented with the same `period_family` / `period_value`
  vocabulary as `player_game_period_stats`
- `wl` is a period-window outcome derived from the period point differential:
  `W` when `plus_minus > 0`, `L` when `plus_minus < 0`, and `T` when the selected period
  ends tied
- `team_record` owns the downstream handling of `T`; the raw dataset must preserve that state
  instead of collapsing tied period windows into whole-game semantics
- this contract is period-only; it does not power `clutch`
- commands should treat missing or incomplete season files for this dataset as a coverage
  failure and fall back to the current honest unfiltered-results note instead of partially
  mixing whole-game and period-window rows

---

## 3. `player_season_advanced`

### Path pattern

`data/raw/player_season_advanced/{season}_{season_type_safe}.csv`

### Grain

One row per **player-season**.

### Key fields

- `season`
- `season_type`
- `player_id`
- `team_id`

### Required columns

At minimum, commands depending on this table should expect:

- `player_id`
- `player_name`
- `team_id`
- `games_played`

### Common advanced columns

Depending on source availability, this dataset may include:

- `minutes_per_game`
- `pts_per_game`
- `reb_per_game`
- `ast_per_game`
- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `usage_rate`
- `ts_pct`
- `pie`
- `off_rating`
- `def_rating`
- `net_rating`

### Producer(s)

- raw player season advanced pull commands

### Primary consumer(s)

- `season_leaders`
- any future player season leaderboard or leaderboard-adjacent queries

### Notes

If a requested season leaderboard stat is not directly present here, the command may fall back to building it from `player_game_stats`. That fallback behavior should stay explicit and tested.

---

## 4. `team_season_advanced`

### Path pattern

`data/raw/team_season_advanced/{season}_{season_type_safe}.csv`

### Grain

One row per **team-season**.

### Key fields

- `season`
- `season_type`
- `team_id`

### Required columns

At minimum, commands depending on this table should expect:

- `team_id`
- `team_abbr`
- `team_name`
- `games_played`

### Common advanced columns

Depending on source availability, this dataset may include:

- `pts_per_game`
- `reb_per_game`
- `ast_per_game`
- `fg3m_per_game`
- `efg_pct`
- `ts_pct`
- `off_rating`
- `def_rating`
- `net_rating`
- `pace`

### Producer(s)

- raw team season advanced pull commands

### Primary consumer(s)

- `season_team_leaders`
- natural team leaderboard queries
- future team season ranking features

### Notes

If date-windowed leaderboard behavior needs per-window recomputation, the command may need to derive results from `team_game_stats` instead of directly trusting full-season advanced rows.

---

## 5. `rosters`

### Path pattern

`data/raw/rosters/{season}.csv`

### Grain

Typically one row per **player-team-season roster entry**.

### Key fields

- `season`
- `player_id`
- `team_id`

### Required columns

- `player_id`
- `player_name`
- `team_id`
- `team_abbr`

### Producer(s)

- raw roster pull commands

### Primary consumer(s)

- season leaderboard enrichment when `team_abbr` is missing from season advanced datasets
- future roster-aware filters or normalization flows

### Notes

This dataset is primarily used as an enrichment table, not a primary query surface.

---

## 6. Processed feature tables

The repo now includes processing/build command groups. As processed feature tables become required dependencies for query behavior, each one should be documented here with the same structure as above.

Likely candidates include:

- player game feature tables
- team game feature tables
- game-level combined feature tables
- league season stats tables
- standings snapshot derivatives

### Current rule

A processed table should be added to this document once either of the following becomes true:

- a query command depends on it directly
- multiple commands depend on it indirectly and a contract is needed to stabilize future work

---

## 6A. `schedule_context_features`

### Path pattern

`data/processed/schedule_context_features/{season}_{season_type_safe}.csv`

Examples:

- `data/processed/schedule_context_features/2025-26_regular_season.csv`
- `data/processed/schedule_context_features/2024-25_playoffs.csv`

### Grain

One row per **team-game**.

### Key fields

- `game_id`
- `team_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `team_id`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `game_date`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `rest_days`
- `opponent_rest_days`
- `back_to_back`
- `rest_advantage`
- `score_margin`
- `one_possession`
- `nationally_televised`
- `national_tv_source`
- `national_tv_source_trusted`
- `schedule_context_source`
- `schedule_context_source_trusted`

### Important derived/query fields

- `rest_days` is normalized to full off days since the team's previous game;
  the second game of a back-to-back has `rest_days=0`.
- `back_to_back` is `1` only when the previous team game was the previous
  calendar day.
- `rest_advantage` is one of `advantage`, `disadvantage`, `even`, or `unknown`
  relative to the opponent's normalized rest for the same game.
- `one_possession` is `1` when the final absolute scoring margin is `<= 3`.
- `nationally_televised` is `1` only when the schedule source carries a
  non-empty national-TV marker.

### Producer(s)

- `src/nbatools/commands/pipeline/build_schedule_context_features.py`
- inputs: `team_game_stats` plus `schedule`

### Primary consumer(s)

- schedule-context execution on `team_record`
- schedule-context execution on `player_game_summary`

### Notes

This is the execution-grade owner for whole-game schedule-context filters in the
initial Phase H route boundary.

Contract rules:

- command owners must join by (`game_id`, `team_id`) so team-relative rest and
  back-to-back state is not confused with game-level state
- `schedule_context_source_trusted=0` means commands must fall back with an
  explicit unfiltered-results note instead of partially filtering
- `national_tv_source_trusted=0` means the raw schedule source is still acting
  as the historical placeholder; commands may execute other schedule-context
  filters but must fall back for `nationally_televised`
- current raw `pull_schedule` output can still produce blank `national_tv`
  values; a season file is considered national-TV trusted only when at least
  one non-empty national-TV marker is present

---

## 7. Sample-aware metric contract

Player sample-aware advanced metrics currently include:

- `usg_pct`
- `ast_pct`
- `reb_pct`

### Contract expectation

These metrics are not generic season lookups. They must be computed from the filtered player-game sample plus the required supporting season/team context used by the implementation.

### Where they should appear

These metrics may appear in:

- player summaries
- player comparisons
- player split summaries
- pretty output
- raw structured output

### Rule

If the sample changes, these metrics must reflect the sample.

Do not silently substitute season-average values for filtered-sample outputs.

---

## 8. Command-to-dataset mapping summary

### Player query surface

- `player_game_finder` -> `player_game_stats`, or `player_game_period_stats` when a supported quarter / half / OT filter is execution-backed for the requested slice
- `player_game_summary` -> `player_game_stats` + supporting advanced metric context, plus `schedule_context_features` for supported schedule-context filters
- `player_compare` -> `player_game_stats` + supporting advanced metric context
- `player_split_summary` -> `player_game_stats` + supporting advanced metric context
- `player_streak_finder` -> `player_game_stats`
- `season_leaders` -> `player_season_advanced` and/or `player_game_stats`, plus `rosters` for enrichment

### Team query surface

- `game_finder` -> `team_game_stats`
- `game_summary` -> `team_game_stats`
- `team_compare` -> `team_game_stats`
- `team_record` -> `team_game_stats`, or `team_game_period_stats` when a supported quarter / half / OT filter is execution-backed for the requested slice, plus `schedule_context_features` for supported schedule-context filters
- `team_split_summary` -> `team_game_stats`
- `team_streak_finder` -> `team_game_stats`
- `season_team_leaders` -> `team_season_advanced` and/or `team_game_stats`

---

## 9. Future expectations

As the repo evolves toward a UI-based search app, these data contracts should help preserve:

- stable engine behavior
- predictable query semantics
- cleaner agent contributions
- easier refactors
- clearer migration paths if storage evolves beyond CSV

When adding a new core dataset, add it here before making it an implicit dependency.

### Explicitly deferred source boundaries

- `clutch` now has an approved future source path: official `PlayByPlayV3`
  plus local score-state derivation. The raw `play_by_play_events` dataset
  path and processed `player_game_clutch_stats` / `team_game_clutch_stats`
  derivations exist with validation and loaders. Until route execution is wired,
  clutch queries must keep the explicit unfiltered-results note. Whole-game logs
  and period-only box-score windows remain rejected as clutch substitutes.
- `player_on_off` now has an approved future source path: upstream
  `teamplayeronoffsummary` via
  `nba_api.stats.endpoints.TeamPlayerOnOffSummary`. The source dataset path,
  validation, loader, and coverage-gated `player_on_off` execution exist.
  Missing or untrusted coverage keeps the explicit unsupported-data response.
  Whole-game `without_player` absence remains rejected as an on/off substitute
  because it has no on-court/off-court sample boundary.
- `lineup_summary` and `lineup_leaderboard` now have an approved future source
  path: upstream `leaguelineupviz` via
  `nba_api.stats.endpoints.LeagueLineupViz`. The raw source dataset path,
  validation, loader, and coverage-gated route execution exist. Missing or
  untrusted coverage keeps the explicit unsupported-data response. Roster
  membership remains rejected as a lineup-unit substitute because it has no
  shared-court, possession, or unit-level sample boundary.
