# Phase F Execution Gap Inventory

> Role: audit output for item 1 in [phase_f_work_queue.md](./phase_f_work_queue.md).

## Bottom line

Cross-checking the Part 2 scope against the current parser spec, example library,
query catalog, Phase E retrospective, and current execution hooks yields six
execution-partial capability families and no extras:

1. clutch
2. quarter / half / overtime
3. schedule-context filters
4. starter / bench role
5. on/off
6. lineups

These are the only parser-shipped families that still sit in an `unfiltered` or
`placeholder` execution state today. Opponent-quality buckets and stretch queries
are intentionally excluded from this inventory because they already have
execution-backed support on their documented route set.

## Classification legend

- `execution-backed` — real execution exists for the documented supported routes
- `unfiltered` — parser and routing accept the filter, but execution drops or ignores it and appends an explicit note
- `placeholder` — parser and routing reach a dedicated route, but that route returns an honest unsupported-data response instead of real stats
- `explicitly deferred` — intentionally not shipping now, with a documented boundary

## Summary table

| Family                    | Classification | Current parser surface / routes                                                                                                                                                                                                     | Required data source or aggregation layer                                                                                                                   | Primary blocker                                                                                                                                                                          | Authoritative docs                                                                                              |
| ------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Clutch                    | `unfiltered`   | Surface forms: `clutch`, `in the clutch`, `clutch time`, `late-game`. Verified route shapes in smoke: `player_game_summary`, `team_record`, `season_leaders`, `player_game_finder`.                                                 | Play-by-play clutch possessions or an upstream clutch-split table keyed by NBA's official clutch definition.                                                | No play-by-play or clutch split tables exist under `data/`; current implementation only appends a parse-stage note.                                                                      | Part 2 plan §4; Phase E item 1; parser spec §8; parser examples §7.7; query catalog §3.11                       |
| Quarter / half / overtime | `unfiltered`   | Surface forms: `1st/2nd/3rd/4th quarter`, `first/second half`, `overtime`, `OT`. Verified route shapes in smoke: `player_game_finder`, `team_record`.                                                                               | Period-level split tables or play-by-play aggregated to quarter / half / OT slices.                                                                         | Current raw and processed tables are whole-game only; execution strips `quarter` / `half` and appends an unfiltered note.                                                                | Part 2 plan §4; parser spec §8; parser examples §7.8; query catalog §3.11                                       |
| Schedule-context filters  | `unfiltered`   | Surface forms: `back-to-back`, `b2b`, `rest advantage`, `rest disadvantage`, `2 days rest`, `one-possession games`, `nationally televised`, `on national TV`. Verified route shapes in smoke: `team_record`, `player_game_summary`. | Joined schedule/context feature tables keyed by game and season, covering B2B state, rest days, one-possession flags, and trustworthy national-TV flags.    | Schedule/context features are not joined into route execution; `national_tv` is still a placeholder in schedule pulls; no dedicated one-possession execution-grade feature table exists. | Part 2 plan §4; parser spec §8; parser examples §§7.9, 7.12-7.14; query catalog §3.11                           |
| Starter / bench role      | `unfiltered`   | Surface forms: `as a starter`, `starting`, `off the bench`, `bench`, `reserve`. Player-context only; team-only bench phrasing is intentionally ignored. Verified route shape in smoke: `player_game_summary`.                       | Route-level filtering over player game logs using `starter_flag` (or an equivalent role feature) across the player-summary / player-finder execution paths. | The raw player game logs already contain `starter_flag`, but execution currently strips `role` before command execution instead of applying it.                                          | Part 2 plan §4; parser spec §8; parser examples §7.10; query catalog §3.11                                      |
| On/off                    | `placeholder`  | Surface forms: `on/off`, `with X on the floor`, `without X on the floor`, `X on court`, `X off court`, `X sitting`. Dedicated route: `player_on_off`.                                                                               | Play-by-play with substitutions, stint tables, or upstream on/off split tables.                                                                             | No raw or processed on/off split tables exist; current data is whole-game only; `without_player` is a whole-game absence filter, not an on/off mechanism.                                | Part 2 plan §4; parser spec §11; parser examples §7.15; query catalog §2.3 / §3.3; Phase E data inventory       |
| Lineups                   | `placeholder`  | Surface forms: `best 5-man lineups`, `3-man units`, `2-man combos`, `lineup with X and Y`, `with X and Y together`. Dedicated routes: `lineup_summary`, `lineup_leaderboard`.                                                       | Lineup-unit tables or play-by-play plus substitution / rotation data aggregated into 2-man / 3-man / 5-man units with minutes thresholds.                   | No lineup-unit, play-by-play, substitution, or rotation tables exist; roster snapshots are season membership only and cannot reconstruct unit-level stints.                              | Part 2 plan §4; parser spec §11; parser examples §§7.16-7.17; query catalog §2.3 / §3.3; Phase E data inventory |

## Detailed inventory

### 1. Clutch

- Classification: `unfiltered`
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
  - Unlike quarter / half / schedule / role filters, the execution sanitizer does not currently receive a `clutch` kwarg
- Required data / aggregation:
  - play-by-play or a clutch split table keyed to the NBA definition: last 5 minutes of the 4th quarter or OT, score within 5
- Current blockers:
  - no play-by-play or clutch split tables in `data/`
  - no execution-stage clutch filtering hook in `_natural_query_execution.py`
- Audit note:
  - Several docs describe clutch as route-propagated. The current code path is slightly narrower: the parser carries the slot and appends the honest note, but `clutch` is not yet preserved in `route_kwargs` the way other context filters are

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
  - `_natural_query_execution._sanitize_unavailable_context_filters()` drops `quarter` / `half`
  - execution appends an explicit unfiltered note and returns full-game results
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
  - `_natural_query_execution._sanitize_unavailable_context_filters()` strips these kwargs
  - execution appends explicit unfiltered notes and returns the underlying unfiltered results
- Required data / aggregation:
  - execution-ready schedule/context features joined into the existing game-log routes
  - at minimum: per-game B2B state, rest day counts / advantage flags, one-possession flags, and reliable national-TV metadata
- Current blockers:
  - schedule/context features are not joined into route execution
  - `pull_schedule.py` still writes `national_tv` as a schema-stability placeholder
  - one-possession support lacks a dedicated execution-grade feature table

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
  - `_natural_query_execution._sanitize_unavailable_context_filters()` strips `role`
  - execution appends an explicit unfiltered note
- Required data / aggregation:
  - player-route filtering over a role field such as `starter_flag`
  - command-level support for the player-summary / player-finder family to honor that filter consistently
- Current blockers:
  - the raw player-game tables already have `starter_flag`, so this is mostly an execution-plumbing gap rather than a brand-new data-ingestion gap
  - team-level role semantics remain intentionally unsupported

### 5. On/off

- Classification: `placeholder`
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
- Required data / aggregation:
  - play-by-play with substitutions
  - derived stint tables, or an upstream on/off split table with on-court and off-court metrics
- Current blockers:
  - no raw or processed on/off split tables exist
  - no play-by-play, substitution, or stint data exists in the repo
  - the existing `without_player` helper excludes whole games and cannot answer possession-level on/off questions

### 6. Lineups

- Classification: `placeholder`
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
- Required data / aggregation:
  - lineup-unit tables, or play-by-play plus substitutions / rotations aggregated into 2-man / 3-man / 5-man groups
  - minute-threshold support tied to the derived unit table
- Current blockers:
  - no lineup-unit tables exist in raw or processed data
  - no play-by-play, substitution, or rotation data exists to derive those units
  - roster snapshots set `stint = 1` and are not a usable substitute for lineup-level execution

## Route and data ownership matrix

### Shared execution path

For the families in this inventory, the route handoff is currently:

1. `parse_query()` / `_finalize_route()` decides the route and builds `route_kwargs`
2. `query_service.execute_structured_query()` mirrors those kwargs into envelope metadata and forwards them to `_execute_build_result()`
3. `_execute_build_result()` resolves opponent-quality filters first, then calls `_sanitize_unavailable_context_filters()` before dispatching to the owning `build_result()` function from `_get_build_result_map()`

The one exception is `clutch`: it currently stays on the parse state and receives its honest fallback note in `_finalize_route()`, rather than flowing through the shared execution sanitizer.

| Family                    | Route names                                                                                                                  | Query-service / execution path                                                                                                                                                                                                      | Command owner(s)                                                                                                                         | Current table inputs                                                                                                                                              | Missing table / join / aggregation                                                                                                                              |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clutch                    | `player_game_summary`, `team_record`, `season_leaders`, `player_game_finder` (verified in Phase E smoke)                     | `_finalize_route()` adds the clutch note directly; `query_service` never receives `clutch` in `route_kwargs`, so `_sanitize_unavailable_context_filters()` never sees it                                                            | `player_game_summary.build_result()`, `build_team_record_result()`, `season_leaders.build_result()`, `player_game_finder.build_result()` | Whole-game `data/raw/player_game_stats/*` and `data/raw/team_game_stats/*`; `season_leaders` reads player game logs directly and merges team W/L data when needed | `clutch` kwarg plumbing into execution, command signatures that can accept it, and a clutch-capable split source such as play-by-play or upstream clutch tables |
| Quarter / half / overtime | `player_game_finder`, `team_record` (verified in Phase E smoke; same modifier pattern applies to the underlying base route)  | `query_service` forwards `quarter` / `half`; `_sanitize_unavailable_context_filters()` `pop()`s them and appends `build_period_filter_note()` before command execution                                                              | `player_game_finder.build_result()`, `build_team_record_result()`                                                                        | Whole-game `data/raw/player_game_stats/*` via `load_player_games_for_seasons()` and `data/raw/team_game_stats/*` via `load_team_games_for_seasons()`              | Period-level split tables or play-by-play aggregates by quarter / half / OT, plus command-level filtering support                                               |
| Schedule-context filters  | `team_record`, `player_game_summary` (verified in Phase E smoke; same modifier pattern applies to the underlying base route) | `query_service` forwards `back_to_back`, `rest_days`, `one_possession`, and `nationally_televised`; `_sanitize_unavailable_context_filters()` removes them and appends `build_game_context_filter_notes()` before command execution | `build_team_record_result()`, `player_game_summary.build_result()`                                                                       | Whole-game `data/raw/team_game_stats/*`, `data/raw/player_game_stats/*`, plus raw schedule metadata that is not yet execution-joined                              | A joined schedule/context feature layer exposing B2B state, rest-day deltas, one-possession flags, and reliable national-TV flags to the command layer          |
| Starter / bench role      | `player_game_summary` (verified in Phase E smoke; current supported scope is player-context only)                            | `query_service` forwards `role`; `_sanitize_unavailable_context_filters()` removes it and appends `build_role_filter_note()` before command execution                                                                               | `player_game_summary.build_result()`                                                                                                     | `data/raw/player_game_stats/*`, which already includes `starter_flag` derived from `start_position` during `pull_player_game_stats.py`                            | No new raw data is required; the gap is execution plumbing: preserve `role`, accept it in command signatures, and filter on `starter_flag` consistently         |
| On/off                    | `player_on_off`                                                                                                              | `query_service` forwards `lineup_members` and `presence_state`; `_execute_build_result()` dispatches straight to the placeholder route without any real filtering step                                                              | `player_on_off.build_result()`                                                                                                           | No usable on/off tables exist; only whole-game player/team logs are present today                                                                                 | On/off split tables or play-by-play plus substitution-derived stints, plus the computation layer to build on-court / off-court metrics                          |
| Lineups                   | `lineup_summary`, `lineup_leaderboard`                                                                                       | `query_service` forwards `lineup_members`, `unit_size`, `minute_minimum`, and `presence_state`; `_execute_build_result()` dispatches straight to placeholder lineup routes                                                          | `lineup_summary.build_result()`, `lineup_leaderboard.build_result()`                                                                     | No lineup-unit or stint tables exist; roster snapshots are season membership only                                                                                 | Lineup-unit tables or play-by-play plus substitution / rotation aggregation, including minutes-threshold support for unit queries                               |

### Route ownership notes by family

- Clutch:
  - Route ownership is fragmented because clutch is a modifier layered onto existing routes instead of a dedicated route family.
  - The owning implementation surfaces are the same command modules that already answer the unfiltered query.
  - `season_leaders` is slightly different from the others because it loads player game logs directly rather than going through `data_utils.load_player_games_for_seasons()`.
- Quarter / half / overtime:
  - The ownership boundary is shared between `query_service`, `_natural_query_execution.py`, and the underlying game-log commands.
  - The sanitizer already centralizes the honest fallback path, so the missing step is to replace that fallback with real period-aware filtering once period data exists.
- Schedule-context filters:
  - The execution gap is shared across four surface filters, which is why they should stay grouped as one family in planning.
  - The raw schedule layer is not enough on its own; the commands need a joined feature table or an equivalent pre-merge step.
- Starter / bench role:
  - This is the only family in the current inventory where the relevant raw data already exists in the main game-log table.
  - Because the parser intentionally ignores team-only bench phrasing today, the execution owner is currently the player-context command family rather than team routes.
- On/off:
  - The dedicated route isolates the unsupported state cleanly, but it also means the eventual owner will need a separate data subsystem rather than a small extension to current whole-game filters.
- Lineups:
  - Both dedicated lineup routes are placeholder-only, so the eventual execution owner needs a new lineup data path rather than a filter added to existing player/team logs.

## Shared prerequisites for context and schedule filters

The partial context families should not turn into six separate implementation tracks.
The audit above reduces them to four shared prerequisites.

### 1. Shared execution-plumbing contract

Applies to: clutch, quarter / half / overtime, schedule-context filters, and role.

Minimal contract:

- parser-owned context slots must reach `route_kwargs` on every route that claims support
- `query_service.execute_structured_query()` must expose those kwargs in metadata and forward them unchanged into `_execute_build_result()`
- `_natural_query_execution.py` must stop using one global drop-on-sight sanitizer for supported routes; either route capability gating or route-specific adapters must decide whether a filter is supported
- owning `build_result()` functions must accept the filter explicitly instead of relying on `**kwargs` swallowing or pre-execution sanitizing
- smoke coverage must exercise at least one supported route per family end-to-end

Why this is shared:

- it removes the current split behavior where `clutch` is parse-note-only while the other context filters are kwarg-preserved-but-sanitized
- it gives Phase G and Phase H one reusable execution contract instead of separate plumbing fixes for each filter

### 2. Segment-split data contract

Applies to: clutch, quarter / half / overtime.

Phase owner: Phase G.

Minimal contract:

- a player-grain segment table and a team-grain segment table, or an equivalent joinable representation
- keys sufficient to join back to existing routes: `season`, `season_type`, `game_id`, and entity identifiers (`player_id` / `team_id`, plus stable names or abbreviations already used by the command layer)
- segment descriptors that can encode both period and clutch contexts, for example a `segment_family` / `segment_value` pair such as `quarter=4`, `half=first`, `period=OT`, `clutch=true`
- the box-score columns already consumed by current summary / finder / leaderboard routes, so the command layer can reuse existing aggregations rather than inventing a separate result shape

Why this is shared:

- clutch and period filters both need intra-game slices; they differ in the slice definition, not in the execution pattern
- one segment contract is cleaner than separate ad hoc clutch tables and quarter tables

Phase-G implication:

- if the segment tables do not exist yet, Phase G can still finish the role filter and must explicitly defer clutch / period execution rather than mixing those blockers into Phase H

### 3. Role execution contract over existing player game logs

Applies to: starter / bench role.

Phase owner: Phase G.

Minimal contract:

- treat `starter_flag` in `data/raw/player_game_stats/*` as the authoritative whole-game starter / bench signal for currently supported player-context routes
- preserve `role` through execution instead of sanitizing it away
- add explicit role filtering to the player-route owners that currently answer the unfiltered query shape

Why this stands alone:

- no new ingestion is required
- this is the one context family that is blocked by execution plumbing, not by missing raw data

Phase-G implication:

- role filtering is the best data-ready Phase G slice and should not wait on the new segment tables needed by clutch / period execution

### 4. Schedule-context feature-join contract

Applies to: back-to-back, rest advantage / disadvantage / day-count filters, one-possession, nationally televised.

Phase owner: Phase H.

Minimal contract:

- one execution-grade game-context feature table, or equivalent derived join, keyed by at least `season`, `season_type`, `game_id`, and the team identity used by the command layer
- fields for `back_to_back`, normalized `rest_days`, and a reliable `nationally_televised` flag
- a stable one-possession indicator so commands do not derive game-margin semantics independently at query time
- a documented join path into both player-game and team-game command execution

Why this is shared:

- the schedule filters all operate at the whole-game level and should ride on the same per-game feature join rather than bespoke logic in each command
- the current blockers are data-contract and join issues, not parser issues

Phase-H implication:

- national-TV ingestion quality and one-possession semantics belong here, not in Phase G
- once the shared game-context feature table exists, the schedule filters can be enabled route-by-route without reopening parser work

## Phase boundary for later queues

- Phase G should target the shared execution-plumbing contract, the role execution contract, and the segment-split contract for clutch / period filters.
- Phase H should target the schedule-context feature-join contract and reuse the same execution-plumbing pattern instead of inventing a second transport path.
- Later queues should schedule work by prerequisite, not by individual filter phrase. For example: "wire role filtering through player summary and finder" is a queue item; "support `as a starter`" is just the surface expression that rides on that prerequisite.

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
