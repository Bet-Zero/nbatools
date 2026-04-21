# Phase E Data Inventory: On/Off and Lineup Support

> Role: reconnaissance output for Phase E item 7 in [phase_e_work_queue.md](./phase_e_work_queue.md).

## Bottom line

- Item 8 (on/off intent and routing) can ship parser/routing work now, but real execution is blocked by missing on/off split data.
- Item 9 (lineup intent and routing) can also ship parser/routing work now, but real execution is blocked by missing lineup-unit data.
- The current repo can support honest stub execution for both items, using the same pattern already used for parser-recognized but execution-unavailable filters such as clutch.

## What the current data layer actually contains

### Raw game logs

- [data/raw/player_game_stats](../../data/raw/player_game_stats) stores one row per player per game. Representative header from [data/raw/player_game_stats/2024-25_regular_season.csv](../../data/raw/player_game_stats/2024-25_regular_season.csv): `game_id`, team/opponent metadata, `starter_flag`, `minutes`, box-score stats, `plus_minus`, `comment`.
- [data/raw/team_game_stats](../../data/raw/team_game_stats) stores one row per team per game. Representative header from [data/raw/team_game_stats/2024-25_regular_season.csv](../../data/raw/team_game_stats/2024-25_regular_season.csv): `game_id`, team/opponent metadata, `wl`, `minutes`, box-score totals, `plus_minus`.

These tables are sufficient for whole-game summaries, finders, records, and the existing `without_player` absence filter. They do not contain separate on-court/off-court rows, stint boundaries, lineup identifiers, substitution timestamps, or possession-level context.

### Season-level advanced tables

- [data/raw/player_season_advanced](../../data/raw/player_season_advanced) stores season-level advanced metrics such as `off_rating`, `def_rating`, `net_rating`, `usage_rate`, `ts_pct`, `ast_pct`, and `reb_pct`.
- [data/raw/team_season_advanced](../../data/raw/team_season_advanced) stores season-level team metrics such as `off_rating`, `def_rating`, `net_rating`, and `pace`.

These files can inform season-level opponent-quality definitions, but they do not expose on/off or lineup splits.

### Roster snapshots

- [data/raw/rosters](../../data/raw/rosters) stores roster membership with a `stint` column.
- [src/nbatools/commands/pipeline/pull_rosters.py](../../src/nbatools/commands/pipeline/pull_rosters.py) currently sets `df["stint"] = 1` for every row before writing the raw roster files.
- [src/nbatools/commands/pipeline/validate_raw.py](../../src/nbatools/commands/pipeline/validate_raw.py) validates the presence of `stint`, but the pulled data does not distinguish multiple same-season team stints.

This means the roster layer is only a season/team membership snapshot. It is not enough to reconstruct lineup groups, rotation stints, or same-season team changes for traded players.

### Schedule and standings metadata

- [data/raw/schedule](../../data/raw/schedule) stores game metadata such as `game_id`, home/away teams, arena, city, and `national_tv`.
- [src/nbatools/commands/pipeline/pull_schedule.py](../../src/nbatools/commands/pipeline/pull_schedule.py) currently writes `schedule["national_tv"] = ""` as a schema-stability placeholder.
- [data/raw/standings_snapshots](../../data/raw/standings_snapshots) stores season standings snapshots used by the shipped opponent-quality filters.

This metadata is useful for opponent-quality buckets and schedule-context notes, but it does not provide the possession, substitution, or lineup-granularity data that on/off and lineup features need.

### Processed feature tables

- [data/processed/player_game_features](../../data/processed/player_game_features) and [data/processed/game_features](../../data/processed/game_features) provide rolling-window and schedule-style features built from the raw game logs.

These processed tables still operate at the game level. They do not add on/off, lineup, or stint-level outputs.

### What is missing outright

No raw or processed directory currently exists for:

- play-by-play events
- substitutions / rotation logs
- on/off split tables
- 2-man, 3-man, or 5-man lineup-unit tables
- possession or stint-level aggregations

## Existing code support and its limits

### The shipped `without_player` path is not on/off support

- [src/nbatools/commands/data_utils.py](../../src/nbatools/commands/data_utils.py) provides `filter_without_player(...)`.
- That helper loads player game logs, finds `game_id` values where the named player appeared, and excludes those full games from the downstream dataset.
- The same helper is consumed by existing summary/finder/record commands such as [src/nbatools/commands/player_game_summary.py](../../src/nbatools/commands/player_game_summary.py), [src/nbatools/commands/player_game_finder.py](../../src/nbatools/commands/player_game_finder.py), [src/nbatools/commands/game_summary.py](../../src/nbatools/commands/game_summary.py), [src/nbatools/commands/game_finder.py](../../src/nbatools/commands/game_finder.py), and [src/nbatools/commands/team_record.py](../../src/nbatools/commands/team_record.py).

This is a whole-game absence filter. It answers questions like "record when Giannis did not play." It does not answer on/off questions like "net rating with Giannis on the floor versus off the floor."

### There is no dedicated on/off or lineup subsystem yet

- No command modules exist matching `player_on_off`, `team_with_without_player`, `lineup_summary`, or `lineup_leaderboard`.
- No files under [src/nbatools/commands](../../src/nbatools/commands) are dedicated to on/off or lineup execution.
- [src/nbatools/commands/_constants.py](../../src/nbatools/commands/_constants.py) currently defines broad `QueryIntent` buckets for shipped routes only; there is no on/off or lineup intent label yet.

### The current honest-stub pattern already exists

- [docs/architecture/parser/specification.md](../architecture/parser/specification.md#11-onoff-and-lineup-support) still marks on/off and lineup support as not yet shipped.
- The current parser already uses honest execution notes for recognized-but-unavailable filters such as clutch, period splits, and schedule-context filters.
- [src/nbatools/commands/natural_query.py](../../src/nbatools/commands/natural_query.py) appends a note when `clutch` is detected because play-by-play clutch splits are not available.

That pattern is the cleanest model for items 8 and 9 until a real data source exists.

## What item 8 can ship with current data

Item 8 can ship these pieces immediately:

- parser detection for `on/off`, `with X on the floor`, `without X on the floor`, `X on court`, and related surface forms
- new parse slots such as `lineup_members` and `presence_state`
- route selection for dedicated on/off routes
- tests proving the parser and router classify those queries correctly
- execution stubs that return an honest note explaining that on/off splits are not yet available in the data layer

Item 8 cannot ship real split calculations with the current data because the repo has no source table containing on-court and off-court possessions, minutes, or split metrics.

## What item 9 can ship with current data

Item 9 can ship these pieces immediately:

- parser detection for lineup/unit phrasing such as `best 5-man lineups`, `3-man units`, and `with Tatum and Brown together`
- new parse slots such as `unit_size` and `minute_minimum`
- route selection for dedicated lineup routes
- tests proving lineup phrasing is detected and routed correctly
- execution stubs that return an honest note explaining that lineup-unit stats are not yet available in the data layer

Item 9 cannot ship real lineup results with the current data because the repo has no lineup-unit tables, no rotation/stint logs, and no play-by-play source from which to derive them.

## Recommended implementation order

### Recommendation for item 8

Proceed as parser/routing-first with stub execution.

Why:

- the slot model in [docs/architecture/parser/specification.md](../architecture/parser/specification.md#112-new-slots-required) is already defined
- the repo already has a proven honest-stub pattern for unavailable execution filters
- no current table can answer true on/off split questions

### Recommendation for item 9

Proceed as parser/routing-first with stub execution.

Why:

- lineup phrasing can be parsed and routed independently of the future data source
- no current raw or processed table captures lineup-unit aggregates
- waiting for a lineup dataset would block parser surface work with no technical benefit

## Suggested acquisition strategies for real execution later

If the project wants real on/off and lineup execution later, it will need a new ingestion path. The most plausible options are:

1. Pull dedicated on/off and lineup split tables from a stable upstream endpoint and store them as new raw tables under `data/raw/` with clear schemas.
2. Pull play-by-play plus substitution/rotation data and aggregate on/off and lineup stints locally in the pipeline.
3. Treat on/off and lineup as a separate data subsystem with its own validation rules, because the grain, defaults, and metric semantics differ from the existing game-log model.

Until one of those exists, items 8 and 9 should stop at parser/routing plus explicit execution notes rather than pretending the current game-log tables can answer the queries.