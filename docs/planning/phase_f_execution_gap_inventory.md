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

| Family | Classification | Current parser surface / routes | Required data source or aggregation layer | Primary blocker | Authoritative docs |
| --- | --- | --- | --- | --- | --- |
| Clutch | `unfiltered` | Surface forms: `clutch`, `in the clutch`, `clutch time`, `late-game`. Verified route shapes in smoke: `player_game_summary`, `team_record`, `season_leaders`, `player_game_finder`. | Play-by-play clutch possessions or an upstream clutch-split table keyed by NBA's official clutch definition. | No play-by-play or clutch split tables exist under `data/`; current implementation only appends a parse-stage note. | Part 2 plan §4; Phase E item 1; parser spec §8; parser examples §7.7; query catalog §3.11 |
| Quarter / half / overtime | `unfiltered` | Surface forms: `1st/2nd/3rd/4th quarter`, `first/second half`, `overtime`, `OT`. Verified route shapes in smoke: `player_game_finder`, `team_record`. | Period-level split tables or play-by-play aggregated to quarter / half / OT slices. | Current raw and processed tables are whole-game only; execution strips `quarter` / `half` and appends an unfiltered note. | Part 2 plan §4; parser spec §8; parser examples §7.8; query catalog §3.11 |
| Schedule-context filters | `unfiltered` | Surface forms: `back-to-back`, `b2b`, `rest advantage`, `rest disadvantage`, `2 days rest`, `one-possession games`, `nationally televised`, `on national TV`. Verified route shapes in smoke: `team_record`, `player_game_summary`. | Joined schedule/context feature tables keyed by game and season, covering B2B state, rest days, one-possession flags, and trustworthy national-TV flags. | Schedule/context features are not joined into route execution; `national_tv` is still a placeholder in schedule pulls; no dedicated one-possession execution-grade feature table exists. | Part 2 plan §4; parser spec §8; parser examples §§7.9, 7.12-7.14; query catalog §3.11 |
| Starter / bench role | `unfiltered` | Surface forms: `as a starter`, `starting`, `off the bench`, `bench`, `reserve`. Player-context only; team-only bench phrasing is intentionally ignored. Verified route shape in smoke: `player_game_summary`. | Route-level filtering over player game logs using `starter_flag` (or an equivalent role feature) across the player-summary / player-finder execution paths. | The raw player game logs already contain `starter_flag`, but execution currently strips `role` before command execution instead of applying it. | Part 2 plan §4; parser spec §8; parser examples §7.10; query catalog §3.11 |
| On/off | `placeholder` | Surface forms: `on/off`, `with X on the floor`, `without X on the floor`, `X on court`, `X off court`, `X sitting`. Dedicated route: `player_on_off`. | Play-by-play with substitutions, stint tables, or upstream on/off split tables. | No raw or processed on/off split tables exist; current data is whole-game only; `without_player` is a whole-game absence filter, not an on/off mechanism. | Part 2 plan §4; parser spec §11; parser examples §7.15; query catalog §2.3 / §3.3; Phase E data inventory |
| Lineups | `placeholder` | Surface forms: `best 5-man lineups`, `3-man units`, `2-man combos`, `lineup with X and Y`, `with X and Y together`. Dedicated routes: `lineup_summary`, `lineup_leaderboard`. | Lineup-unit tables or play-by-play plus substitution / rotation data aggregated into 2-man / 3-man / 5-man units with minutes thresholds. | No lineup-unit, play-by-play, substitution, or rotation tables exist; roster snapshots are season membership only and cannot reconstruct unit-level stints. | Part 2 plan §4; parser spec §11; parser examples §§7.16-7.17; query catalog §2.3 / §3.3; Phase E data inventory |

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
