# Phase F Execution Gap Inventory

> Role: audit output for item 1 in [phase_f_work_queue.md](./phase_f_work_queue.md).

## Bottom line

Cross-checking the Part 2 scope against the parser spec, example library,
query catalog, Phase E retrospective, and execution hooks at the start of Part 2
yielded six execution-partial capability families and no extras:

1. clutch
2. quarter / half / overtime
3. schedule-context filters
4. starter / bench role
5. on/off
6. lineups

This inventory remains the family list of record for Part 2. Individual family
rows are updated as later phases move from `unfiltered` / `placeholder` to
coverage-gated execution or explicit deferral. Opponent-quality buckets and
stretch queries are intentionally excluded because they already had
execution-backed support on their documented route set.

## Classification legend

- `execution-backed` — real execution exists for the documented supported routes
- `unfiltered` — parser and routing accept the filter, but execution drops or ignores it and appends an explicit note
- `placeholder` — parser and routing reach a dedicated route, but that route returns an honest unsupported-data response instead of real stats
- `explicitly deferred` — intentionally not shipping now, with a documented boundary

## Summary table

| Family                    | Classification | Current parser surface / routes                                                                                                                                                                                                     | Required data source or aggregation layer                                                                                                                                              | Primary blocker                                                                                                                                                                                                                                                 | Authoritative docs                                                                                                                     |
| ------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Clutch                    | `unfiltered`   | Surface forms: `clutch`, `in the clutch`, `clutch time`, `late-game`. Verified route shapes in smoke: `player_game_summary`, `team_record`, `season_leaders`, `player_game_finder`.                                                 | Play-by-play clutch possessions or an upstream clutch-split table keyed by NBA's official clutch definition.                                                                           | No play-by-play or clutch split tables exist under `data/`; transport now preserves `clutch` on the initial Phase G routes, but execution still appends the honest unfiltered note.                                                                             | Part 2 plan §4; Phase E item 1; parser spec §8; parser examples §7.7; query catalog §3.11                                              |
| Quarter / half / overtime | `unfiltered`   | Surface forms: `1st/2nd/3rd/4th quarter`, `first/second half`, `overtime`, `OT`. Verified route shapes in smoke: `player_game_finder`, `team_record`.                                                                               | Period-level split tables or play-by-play aggregated to quarter / half / OT slices.                                                                                                    | Current raw and processed tables are whole-game only; transport now preserves `quarter` / `half` on the initial Phase G routes, but execution still appends the explicit unfiltered note.                                                                       | Part 2 plan §4; parser spec §8; parser examples §7.8; query catalog §3.11                                                              |
| Schedule-context filters  | `execution-backed with coverage gate` | Surface forms: `back-to-back`, `b2b`, `rest advantage`, `rest disadvantage`, `2 days rest`, `one-possession games`, `nationally televised`, `on national TV`. Verified route shapes in smoke: `team_record`, `player_game_summary`. | `schedule_context_features` keyed by `game_id` + `team_id`, covering B2B state, normalized rest days, one-possession flags, and trusted national-TV flags.                              | Execution now works on `team_record` / `player_game_summary` when trusted feature coverage exists. Missing feature coverage, unsupported routes, or untrusted national-TV source coverage still produce explicit unfiltered-results notes.                    | Part 2 plan §4; parser spec §8; parser examples §§7.9, 7.12-7.14; query catalog §3.11; data contracts §6A                              |
| Starter / bench role      | `unfiltered`   | Surface forms: `as a starter`, `starting`, `off the bench`, `bench`, `reserve`. Player-context only; team-only bench phrasing is intentionally ignored. Verified route shape in smoke: `player_game_summary`.                       | A dedicated `player_game_starter_roles` backfill sourced by `game_id` from `BoxScoreTraditionalV3.PlayerStats.position`, joined to the player-summary / player-finder execution paths. | The current player-game corpus does not contain trustworthy starter-role data: `start_position` is empty throughout and the derived `starter_flag` stays `0`, while sampled historical box-score position data is not uniformly trustworthy without validation. | Part 2 plan §4; parser spec §8; parser examples §7.10; query catalog §3.11; `src/nbatools/commands/pipeline/pull_player_game_stats.py` |
| On/off                    | `explicitly deferred` | Surface forms: `on/off`, `with X on the floor`, `without X on the floor`, `X on court`, `X off court`, `X sitting`. Dedicated route: `player_on_off`.                                                                               | Play-by-play with substitutions, stint tables, or upstream on/off split tables.                                                                                                        | Phase I confirmed no trustworthy on/off-capable source exists in the repo. `player_on_off` remains an honest placeholder; `without_player` is a whole-game absence filter, not an on/off mechanism.                                                            | Part 2 plan §4; parser spec §11; parser examples §7.15; query catalog §2.3 / §3.3; Phase E data inventory; Phase I source boundary      |
| Lineups                   | `explicitly deferred` | Surface forms: `best 5-man lineups`, `3-man units`, `2-man combos`, `lineup with X and Y`, `with X and Y together`. Dedicated routes: `lineup_summary`, `lineup_leaderboard`.                                                       | Lineup-unit tables or play-by-play plus substitution / rotation data aggregated into 2-man / 3-man / 5-man units with minutes thresholds.                                              | Phase J confirmed no trustworthy lineup-unit source exists in the repo. Placeholder routes remain honest; roster snapshots are season membership only and cannot reconstruct unit-level stints.                                                                 | Part 2 plan §4; parser spec §11; parser examples §§7.16-7.17; query catalog §2.3 / §3.3; Phase E data inventory; Phase J source boundary |

## Detailed inventory

### 1. Clutch

- Classification: `execution-backed with coverage gate`
- Parser surface:
  - `clutch`
  - `in the clutch`
  - `clutch time`
  - `late-game`
- Current route behavior:
  - Verified in Phase E smoke on `player_game_summary`, `team_record`, `season_leaders`, and `player_game_finder`
  - The base route is whatever the same query would use without the clutch phrase; `clutch` is a modifier, not a dedicated route family
- Current execution behavior:
  - `parse_query(...)` sets `clutch=True`
  - `_finalize_route()` appends a note explaining that clutch results are currently unfiltered
  - `query_service` forwards `clutch`, and `_route_context_filters_for_execution()` preserves it on the initial Phase G routes while keeping the explicit unfiltered-results note in place
- Required data / aggregation:
  - play-by-play or a clutch split table keyed to the NBA definition: last 5 minutes of the 4th quarter or OT, score within 5
- Current blockers:
  - no play-by-play or clutch split tables in `data/`
  - no command-level clutch filtering hook exists yet in the owning build-result functions

### 2. Quarter / half / overtime

- Classification: `unfiltered`
- Parser surface:
  - `1st quarter`, `2nd quarter`, `3rd quarter`, `4th quarter`
  - `first half`, `second half`
  - `overtime`, `OT`
- Current route behavior:
  - Verified in Phase E smoke on `player_game_finder` and `team_record`
  - `quarter` / `half` are preserved in `route_kwargs`
- Current execution behavior:
  - `query_service` forwards `quarter` / `half`, and `_route_context_filters_for_execution()` preserves them on the initial Phase G routes before appending the explicit unfiltered note
  - execution still returns full-game results because no period-aware filtering layer exists yet
- Required data / aggregation:
  - period-level split tables, or play-by-play aggregated by quarter / half / OT before query execution
- Current blockers:
  - raw player/team logs are whole-game tables
  - processed feature tables are also game-level only

### 3. Schedule-context filters

- Classification: `unfiltered`
- Parser surface:
  - back-to-back: `back-to-back`, `b2b`, `second of a back-to-back`
  - rest: `rest advantage`, `rest disadvantage`, `on 2 days rest`
  - one-possession: `one-possession games`
  - national TV: `nationally televised`, `on national TV`
- Current route behavior:
  - Verified in Phase E smoke on `team_record` and `player_game_summary`
  - `back_to_back`, `rest_days`, `one_possession`, and `nationally_televised` are preserved in `route_kwargs`
- Current execution behavior:
  - `_route_context_filters_for_execution()` preserves these kwargs on `team_record` and `player_game_summary`
  - `build_team_record_result()` and `player_game_summary.build_result()` apply the filters through `schedule_context_features` when trusted coverage exists
  - unsupported routes or missing feature coverage append explicit unfiltered-results notes and return the underlying unfiltered result
  - `nationally_televised` additionally requires `national_tv_source_trusted=1`; placeholder schedule pulls still fall back honestly for that filter
- Required data / aggregation:
  - `data/processed/schedule_context_features/{season}_{season_type_safe}.csv`
  - one row per team-game keyed by `game_id` + `team_id`
  - fields for `back_to_back`, normalized `rest_days`, `rest_advantage`, `one_possession`, and national-TV trust/source flags
- Current blockers:
  - no remaining blocker for the documented initial route boundary
  - national-TV execution remains coverage-gated because current raw schedule pulls may still contain placeholder blank `national_tv` values

### 4. Starter / bench role

- Classification: `unfiltered`
- Parser surface:
  - `as a starter`
  - `starting`
  - `off the bench`
  - `bench`
  - `reserve`
- Current route behavior:
  - Player-context only; team-only phrases such as `Celtics bench scoring` are intentionally ignored
  - Verified in Phase E smoke on `player_game_summary`
  - `role` is preserved in `route_kwargs`
- Current execution behavior:
  - `_route_context_filters_for_execution()` preserves `role` on the initial Phase G player routes and appends the explicit unfiltered note
  - no command-level role filtering is enabled yet because the current starter-role field is not trustworthy enough to ship against
- Required data / aggregation:
  - a dedicated `player_game_starter_roles` dataset keyed to the player game logs used by `player_game_summary` and `player_game_finder`
  - the dataset should be backfilled by `game_id` from `data/raw/games/*` using `BoxScoreTraditionalV3.PlayerStats.position`, normalized into a starter-role contract instead of overloading the current `player_game_stats` pull
  - command-level support for the player-summary / player-finder family to honor that trusted signal consistently once it exists
- Current blockers:
  - `pull_player_game_stats.py` maps `START_POSITION` to `start_position`, fills missing `start_position` with `""`, and derives `starter_flag` from whether `start_position` is non-empty
  - corpus audit of `data/raw/player_game_stats/*.csv` found `start_position` empty throughout and `starter_flag=0` throughout the current raw player-game dataset
  - direct upstream audit showed that `LeagueGameFinder` still does not expose starter-role fields, so the existing player-game pull cannot be repaired by a small rename or loader tweak
  - direct upstream audit also identified the viable source path: `BoxScoreTraditionalV3.PlayerStats.position` returns clean 5-starter-per-team data on sampled 2024-25 and 2025-26 games, but a sampled 1996-97 game over-labeled starters, so trust validation is required before execution can use the source
  - the dedicated backfill dataset and trust-gating layer have not been implemented yet
  - an exploratory role-filter execution attempt was correctly reverted after smoke validation showed that starter queries would collapse into false `no_match` results
  - team-level role semantics remain intentionally unsupported

### 5. On/off

- Classification: `explicitly deferred`
- Parser surface:
  - `on/off`
  - `with X on the floor`
  - `without X on the floor`
  - `X on court`
  - `X off court`
  - `X sitting`
- Current route behavior:
  - Dedicated route: `player_on_off`
  - Verified in Phase E smoke on `Jokic on/off` and `Nuggets without Jokic on the floor`
- Current execution behavior:
  - dedicated route returns an honest unsupported-data / no-result placeholder path
  - the parser preserves `lineup_members` and `presence_state`, but no real split calculation exists
  - Phase I explicitly defers real execution until a trustworthy on/off split,
    play-by-play + substitution, or stint source is approved
- Required data / aggregation:
  - play-by-play with substitutions
  - derived stint tables, or an upstream on/off split table with on-court and off-court metrics
- Current blockers / deferral boundary:
  - no raw or processed on/off split tables exist
  - no play-by-play, substitution, or stint data exists in the repo
  - the existing `without_player` helper excludes whole games and cannot answer possession-level on/off questions
  - see [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md)
    for the exact future source requirements

### 6. Lineups

- Classification: `explicitly deferred`
- Parser surface:
  - `best 5-man lineups`
  - `3-man units`
  - `2-man combos`
  - `lineup with X and Y`
  - `with X and Y together`
- Current route behavior:
  - Dedicated routes: `lineup_summary`, `lineup_leaderboard`
  - Verified in Phase E smoke on `best 5-man lineups this season` and `lineup with Tatum and Jaylen Brown`
- Current execution behavior:
  - dedicated routes return honest unsupported-data / no-result placeholder paths
  - the parser preserves `lineup_members`, `unit_size`, and `minute_minimum`, but execution cannot compute real lineup-unit stats
  - Phase J explicitly defers real execution until a trustworthy lineup-unit,
    play-by-play + substitution, or stint source is approved
- Required data / aggregation:
  - lineup-unit tables, or play-by-play plus substitutions / rotations aggregated into 2-man / 3-man / 5-man groups
  - minute-threshold support tied to the derived unit table
- Current blockers / deferral boundary:
  - no lineup-unit tables exist in raw or processed data
  - no play-by-play, substitution, or rotation data exists to derive those units
  - roster snapshots set `stint = 1` and are not a usable substitute for lineup-level execution
  - see [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md)
    for the exact future source requirements

## Route and data ownership matrix

### Shared execution path

For the families in this inventory, the route handoff is currently:

1. `parse_query()` / `_finalize_route()` decides the route and builds `route_kwargs`
2. `query_service.execute_structured_query()` mirrors those kwargs into envelope metadata and forwards them to `_execute_build_result()`
3. `_execute_build_result()` resolves opponent-quality filters first, then calls `_route_context_filters_for_execution()` before dispatching to the owning `build_result()` function from `_get_build_result_map()`

| Family                    | Route names                                                                                                                   | Query-service / execution path                                                                                                                                                                                                           | Command owner(s)                                                                                                                         | Current table inputs                                                                                                                                                                                          | Missing table / join / aggregation                                                                                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clutch                    | `player_game_summary`, `team_record`, `season_leaders`, `player_game_finder` (verified in Phase E and Phase G smoke)          | `query_service` now forwards `clutch`; `_route_context_filters_for_execution()` preserves it on the initial Phase G routes and appends the current honest unfiltered note before command execution                                       | `player_game_summary.build_result()`, `build_team_record_result()`, `season_leaders.build_result()`, `player_game_finder.build_result()` | Whole-game `data/raw/player_game_stats/*` and `data/raw/team_game_stats/*`; `season_leaders` reads player game logs directly and merges team W/L data when needed                                             | A clutch-capable split source such as play-by-play or upstream clutch tables, plus command-level filtering support                                                         |
| Quarter / half / overtime | `player_game_finder`, `team_record` (verified in Phase E and Phase G smoke; same modifier pattern applies to the base route)  | `query_service` forwards `quarter` / `half`; `_route_context_filters_for_execution()` preserves them on the initial Phase G routes and appends `build_period_filter_note()` before command execution                                     | `player_game_finder.build_result()`, `build_team_record_result()`                                                                        | Whole-game `data/raw/player_game_stats/*` via `load_player_games_for_seasons()` and `data/raw/team_game_stats/*` via `load_team_games_for_seasons()`                                                          | Period-level split tables or play-by-play aggregates by quarter / half / OT, plus command-level filtering support                                                          |
| Schedule-context filters  | `team_record`, `player_game_summary` (verified in Phase E / G / H smoke; same modifier pattern applies to the base route) | `query_service` forwards `back_to_back`, `rest_days`, `one_possession`, and `nationally_televised`; `_route_context_filters_for_execution()` preserves them on the Phase H routes and leaves unsupported routes on the explicit-note fallback path | `build_team_record_result()`, `player_game_summary.build_result()`                                                                       | Whole-game `data/raw/team_game_stats/*`, `data/raw/player_game_stats/*`, plus `data/processed/schedule_context_features/*`                                                                                   | Future route expansion beyond `team_record` / `player_game_summary`, plus national-TV source improvement where raw schedule coverage remains placeholder-only              |
| Starter / bench role      | `player_game_summary`, `player_game_finder` (player-context only; natural-query smoke currently verifies the summary path)    | `query_service` forwards `role`; `_route_context_filters_for_execution()` preserves it on the initial Phase G player routes and appends `build_role_filter_note()` before command execution                                              | `player_game_summary.build_result()`, `player_game_finder.build_result()`                                                                | `data/raw/player_game_stats/*` for the base sample plus `data/raw/games/*` as the backfill key inventory; the legacy `player_game_stats.start_position` / `starter_flag` fields remain unusable for execution | A dedicated `player_game_starter_roles` backfill sourced from `BoxScoreTraditionalV3.PlayerStats.position`, normalized with trust validation and joined into player routes |
| On/off                    | `player_on_off`                                                                                                               | `query_service` forwards `lineup_members` and `presence_state`; `_execute_build_result()` dispatches straight to the placeholder route because Phase I explicitly deferred real execution until a trustworthy source exists              | `player_on_off.build_result()`                                                                                                           | No usable on/off tables exist; only whole-game player/team logs are present today                                                                                                                             | On/off split tables or play-by-play plus substitution-derived stints, plus the computation layer to build on-court / off-court metrics                                     |
| Lineups                   | `lineup_summary`, `lineup_leaderboard`                                                                                        | `query_service` forwards `lineup_members`, `unit_size`, `minute_minimum`, and `presence_state`; `_execute_build_result()` dispatches straight to placeholder lineup routes because Phase J explicitly deferred real execution until a trustworthy source exists | `lineup_summary.build_result()`, `lineup_leaderboard.build_result()`                                                                     | No lineup-unit or stint tables exist; roster snapshots are season membership only                                                                                                                             | Lineup-unit tables or play-by-play plus substitution / rotation aggregation, including minutes-threshold support for unit queries                                          |

### Route ownership notes by family

- Clutch:
  - Route ownership is fragmented because clutch is a modifier layered onto existing routes instead of a dedicated route family.
  - The owning implementation surfaces are the same command modules that already answer the unfiltered query.
  - `season_leaders` is slightly different from the others because it loads player game logs directly rather than going through `data_utils.load_player_games_for_seasons()`.
- Quarter / half / overtime:
  - The ownership boundary is shared between `query_service`, `_natural_query_execution.py`, and the underlying game-log commands.
  - The sanitizer already centralizes the honest fallback path, so the missing step is to replace that fallback with real period-aware filtering once period data exists.
- Schedule-context filters:
  - The execution-backed path is shared across four surface filters, which is why they stay grouped as one family in planning.
  - The raw schedule layer is not enough on its own; command execution depends on the processed team-game `schedule_context_features` contract.
  - National-TV remains source-quality gated separately from the rest/B2B/one-possession fields.
- Starter / bench role:
  - The player routes and transport path are already identified, but the current raw role signal in `player_game_stats` is not trustworthy enough to execute against.
  - The viable upstream path is a game-level fan-out over `BoxScoreTraditionalV3.PlayerStats.position`, backed by trust validation because sampled historical coverage is not uniformly clean.
  - Because the parser intentionally ignores team-only bench phrasing today, the execution owner is currently the player-context command family rather than team routes.
- On/off:
  - The dedicated route isolates the unsupported state cleanly, but it also means the eventual owner will need a separate data subsystem rather than a small extension to current whole-game filters.
- Lineups:
  - Both dedicated lineup routes are placeholder-only by explicit Phase J deferral, so the eventual execution owner needs a new lineup data path rather than a filter added to existing player/team logs.

## Shared prerequisites for context and schedule filters

The partial context families should not turn into six separate implementation tracks.
The audit above reduces them to four shared prerequisites.

### 1. Shared execution-plumbing contract

Applies to: clutch, quarter / half / overtime, schedule-context filters, and role.

Minimal contract:

- parser-owned context slots must reach `route_kwargs` on every route that claims support
- `query_service.execute_structured_query()` must expose those kwargs in metadata and forward them unchanged into `_execute_build_result()`
- `_natural_query_execution.py` must use route capability gating instead of one global drop-on-sight sanitizer for supported routes
- owning `build_result()` functions must accept the filter explicitly instead of relying on `**kwargs` swallowing or pre-execution sanitizing
- smoke coverage must exercise at least one supported route per family end-to-end

Why this is shared:

- it keeps `clutch`, `quarter`, `half`, `role`, and schedule-context filters on explicit transport paths while leaving unsupported routes honestly noted
- it gives Phase G and Phase H one reusable execution contract instead of separate plumbing fixes for each filter

### 2. Period-window data contract

Applies to: quarter / half / overtime.

Phase owner: the period-only continuation of Phase G.

Locked contract:

- create dedicated `player_game_period_stats` and `team_game_period_stats` datasets
  instead of trying to keep `clutch` and period execution on one shared unfinished
  segment table
- use `BoxScoreTraditionalV3` as the period-window source of record for both datasets
  and for the period window boundaries themselves
- enrich only `player_game_period_stats` with `BoxScoreAdvancedV3` rate fields needed by
  the current `player_game_finder` stat surface (`usg_pct`, `ast_pct`, `reb_pct`,
  `tov_pct`)
- use join keys at least as strong as `season`, `season_type`, `game_id`, and the route
  owner identity (`player_id` or `team_id`), plus the team/opponent/name context already
  used by the current command layer
- represent the supported period semantics with explicit `period_family` /
  `period_value` pairs:
  - `quarter` with `1`, `2`, `3`, `4`
  - `half` with `first`, `second`
  - `overtime` with `OT`
- record the exact upstream window on each row via `source_start_period` /
  `source_end_period`:
  - quarters: `1-1`, `2-2`, `3-3`, `4-4`
  - halves: `1-2`, `3-4`
  - overtime: `5-14`, aggregated into one `OT` row only when real overtime activity is
    returned
- keep the initial route boundary explicit:
  - `player_game_period_stats` owns period execution for `player_game_finder`
  - `team_game_period_stats` owns period execution for `team_record`

Why this is now period-only:

- the segment-source review found no trustworthy clutch-capable game-grain source under
  current repo constraints
- period-only window execution still looks feasible from the `BoxScore*V3` window
  endpoints and should not stay blocked behind the unresolved clutch prerequisite

Phase-G implication:

- the exact next implementation target is to materialize `player_game_period_stats` and
  `team_game_period_stats`, validate them, and wire them into `player_game_finder` and
  `team_record`
- `clutch` stays explicitly deferred and is out of scope for this contract

### 3. Starter-role source and data contract

Applies to: starter / bench role.

Phase owner: Phase G.

Minimal contract:

- create a dedicated `player_game_starter_roles` dataset at player-game grain instead of reusing the legacy `player_game_stats.start_position` / `starter_flag` fields
- source the dataset by fan-out over `data/raw/games/*`, using `BoxScoreTraditionalV3.PlayerStats.position` as the raw upstream starter marker and normalizing it into `starter_position_raw` plus derived `starter_flag`
- provide join keys at least as strong as `season`, `season_type`, `game_id`, `team_id`, and `player_id` so the role signal can ride on the existing player-game routes without ambiguity
- mark trust explicitly; at minimum, rows may only be execution-eligible when their `(game_id, team_id)` group validates to exactly 5 starter-marked players, and the dataset must record why rows/games are untrusted when validation fails
- define the supported semantics explicitly: whole-game `starter` vs `bench` for player-context summary / finder routes only
- document coverage / backfill expectations and the failure mode when the role source is absent or incomplete

Why this stands alone:

- the current derived `starter_flag` is not trustworthy enough to support honest route-level role filtering
- the chosen upstream path exists, but sampled historical data shows that raw starter markers still need validation before they can become an execution contract
- starter / bench execution is now a dedicated-source + validation problem first and an execution-plumbing problem second

Phase-G implication:

- item 2A completes the source audit by choosing the `BoxScoreTraditionalV3` backfill path and defining this contract
- the next role item has to materialize the dataset, enforce trust gating, and then wire role filtering through player summary / finder without guessing at the data source

### 4. Schedule-context feature-join contract

Applies to: back-to-back, rest advantage / disadvantage / day-count filters, one-possession, nationally televised.

Phase owner: Phase H.

Locked contract:

- one execution-grade `schedule_context_features` table keyed by `game_id` and `team_id`, with `season` / `season_type` carried on each row
- fields for `back_to_back`, normalized `rest_days`, `rest_advantage`, `one_possession`, `nationally_televised`, `national_tv_source`, `national_tv_source_trusted`, and `schedule_context_source_trusted`
- `rest_days` means full off days since the team's previous game; the second game of a back-to-back has `rest_days=0`
- `one_possession` is a stable final-margin flag (`abs(score_margin) <= 3`) so commands do not derive game-margin semantics independently at query time
- `team_record` and `player_game_summary` join the table by `game_id` + `team_id`

Why this is shared:

- the schedule filters all operate at the whole-game level and should ride on the same per-game feature join rather than bespoke logic in each command
- the current blockers are data-contract and join issues, not parser issues

Phase-H outcome:

- national-TV ingestion quality and one-possession semantics live here, not in Phase G
- the initial route boundary is enabled for `team_record` and `player_game_summary`
- later route expansion can reuse the same feature table without reopening parser work

## Phase boundary for later queues

- Phase G should target the shared execution-plumbing contract, the starter-role source / data contract, and the segment-split contract for clutch / period filters.
- Phase H should target the schedule-context feature-join contract and reuse the same execution-plumbing pattern instead of inventing a second transport path.
- Later queues should schedule work by prerequisite, not by individual filter phrase. For example: "build the validated starter-role dataset and wire role filtering through player summary and finder" is a queue item; "support `as a starter`" is just the surface expression that rides on that prerequisite.

## Families reviewed and intentionally excluded from the gap inventory

- Opponent-quality filters:
  - execution-backed on the documented single-entity summary / finder / record routes and stretch leaderboards
  - unsupported routes still append notes, but the capability family itself is no longer execution-partial at the plan level
- Stretch / rolling-window leaderboards:
  - fully execution-backed on whole-game player logs
- Whole-game absence (`without_player`):
  - execution-backed for the current whole-game absence use case

## Recommendation for Phase F item 2

Use this inventory as the family list of record. The next audit step should trace,
for each family above:

1. the exact query-service route ownership
2. which kwargs survive from `parse_query()` into `_execute_build_result()`
3. which command modules would need new inputs or new data joins
4. whether the gap is primarily missing data, missing execution plumbing, or both
