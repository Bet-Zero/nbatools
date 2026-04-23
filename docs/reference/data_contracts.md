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

- `player_game_finder` -> `player_game_stats`
- `player_game_summary` -> `player_game_stats` + supporting advanced metric context
- `player_compare` -> `player_game_stats` + supporting advanced metric context
- `player_split_summary` -> `player_game_stats` + supporting advanced metric context
- `player_streak_finder` -> `player_game_stats`
- `season_leaders` -> `player_season_advanced` and/or `player_game_stats`, plus `rosters` for enrichment

### Team query surface

- `game_finder` -> `team_game_stats`
- `game_summary` -> `team_game_stats`
- `team_compare` -> `team_game_stats`
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
