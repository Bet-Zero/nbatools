# Leaderboard Supporting Columns Preflight

Discovery date: 2026-05-10

Scope: product-decision preflight for route-specific supporting columns on
leaderboard-like result tables. This is not an implementation wave, a full UI
redesign, a route registry redesign, or new query support.

## Executive Summary

Routes and families reviewed:

- `season_leaders`
- `season_team_leaders`
- `team_record_leaderboard`
- `player_occurrence_leaders`
- `team_occurrence_leaders`
- `player_stretch_leaderboard`
- `playoff_appearances` league-wide leaderboard variant
- `lineup_leaderboard`
- `record_by_decade_leaderboard`
- `top_player_games`
- `top_team_games`

Biggest finding: generic `LeaderboardResult` currently infers supporting
columns from row keys. That works for small happy-path rows, but it is not a
stable product contract. Route families have different useful context:
season leaders need GP/team/qualifier context, record leaderboards need W-L and
win percentage, appearances need round and season span, occurrences need event
count and games played, and lineups need lineup identity plus rating context.

Highest-risk route: `lineup_leaderboard`. Actual source-backed backend rows use
`lineup_name`, `player_names`, `lineup_id`, `player_ids`, `unit_size`,
`minute_minimum`, and rating fields. Current `LeaderboardResult` recognizes only
synthetic `lineup`, `lineup_members`, or `members` as lineup identity. With
actual backend rows, it can classify the row as a team row via `team_abbr` and
then dynamically expose low-product-value fields such as IDs.

Recommended next implementation: Option C, add route-specific frontend column
configs for leaderboard-like routes that still use generic `LeaderboardResult`,
without backend behavior changes. Keep `TopPerformancesResult`,
`RollingStretchResult`, and `RecordResult` as separate specialized renderers.

Production code should change in the next implementation wave: yes, narrowly in
frontend result rendering and tests. This preflight changes docs only.

## Files Inspected

| File | Why inspected | Key finding |
|---|---|---|
| `docs/planning/raw-product/RAW_QUERY_PRODUCT_MAP.md` | Current route/product map | Identifies the leaderboard routes, renderer families, and shipped examples. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Locked Wave 1/Wave 2 contracts | Documents generic leaderboard supporting columns as inferred and needing product decision. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_1_RETURN_PACKAGE.md` | Prior Wave 1 context | Confirms generic leaderboard only locked rank, entity, and primary metric. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_2_RETURN_PACKAGE.md` | Prior Wave 2 context | Confirms lineup and record leaderboards remain partially inferred or specialized. |
| `return_packages/raw-product/WEAK_CONTRACT_DECISION_PREFLIGHT_RETURN_PACKAGE.md` | Weak-contract decision context | Established that single-team playoff appearances are no longer part of this leaderboard decision. |
| `return_packages/raw-product/WEAK_CONTRACT_CLEANUP_WAVE_1_RETURN_PACKAGE.md` | Latest cleanup context | Confirms lineup summary and single-team playoff appearances were cleaned up, while leaderboard supporting columns remain next. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Generic leaderboard renderer | Columns are `#`, entity, primary metric, then dynamically inferred row keys. No detail drawer or row cap. |
| `frontend/src/components/results/patterns/TopPerformancesResult.tsx` | Single-game leaderboard renderer | Uses a curated table: rank, identity, date, opponent, result, optional score, primary metric, and metric-specific support stats. |
| `frontend/src/components/results/patterns/RollingStretchResult.tsx` | Stretch leaderboard renderer | Already specialized: rank, player, window, stretch metric, start, end, season, plus at most two supported window fields when present. |
| `frontend/src/components/results/patterns/RecordResult.tsx` | Record/decade renderer | `record_by_decade_leaderboard` already has route-specific columns and does not use generic `LeaderboardResult`. |
| `frontend/src/components/results/config/routeToPattern.ts` | Route-to-renderer mapping | Generic `leaderboard` is used by season, occurrence, team-record, appearances, and lineup leaderboards; top/stretch/decade record use specialized patterns. |
| `frontend/src/components/results/resultShapes.ts` | Shape classification | Collapses generic leaderboard routes to `leaderboard_table`; keeps top performances, rolling stretch, and record by decade separate. |
| `frontend/src/components/results/primitives/ResultTable.tsx` | Shared table primitive | Supports highlight columns and optional row caps, but generic leaderboard does not pass a frontend row cap. |
| `frontend/src/components/results/primitives/detailTables.ts` | Detail drawer helper | Generic leaderboard does not use raw/detail drawers, so undisplayed fields are not recoverable in UI. |
| `frontend/src/api/types.ts` | Route typing | Includes all routes reviewed. |
| `src/nbatools/commands/natural_query.py` | Routing and default limits | Natural routes usually set `limit=10`; top/stretch/lineup leaderboards also default to 10. |
| `src/nbatools/commands/_natural_query_execution.py` | Build-result map | Confirms all reviewed backend routes are mapped to production builders. |
| `src/nbatools/commands/season_leaders.py` | Player season leaders | Outputs only identity, GP, primary metric, metric-specific context columns, and season context. |
| `src/nbatools/commands/season_team_leaders.py` | Team season leaders | Outputs only identity, GP, primary metric, metric-specific context columns, and season context. |
| `src/nbatools/commands/team_record.py` | Team record leaderboard | Outputs team identity, games, wins, losses, win percentage, and season context. |
| `src/nbatools/commands/player_occurrence_leaders.py` | Player occurrence leaders | Outputs player, optional team abbreviation, games played, dynamic occurrence-count column, and season context. |
| `src/nbatools/commands/team_occurrence_leaders.py` | Team occurrence leaders | Outputs team abbreviation/name fallback, games played, dynamic occurrence-count column, and season context. |
| `src/nbatools/commands/player_stretch_leaderboard.py` | Rolling stretch rows | Backend rows are window metadata plus `stretch_value`; per-window support averages are not currently emitted. |
| `src/nbatools/commands/playoff_history.py` | Playoff appearances and decade record rows | League-wide appearances rows include team, appearances, round, and season span; decade rows include team, decade, games, W-L, win pct. |
| `src/nbatools/commands/lineup_leaderboard.py` | Lineup leaderboard route | Returns source-backed rows from `_lineup_execution.RESULT_COLUMNS` with rank inserted. |
| `src/nbatools/commands/_lineup_execution.py` | Actual lineup row keys | Actual lineup rows include `lineup_name`, `player_names`, `lineup_id`, `player_ids`, ratings, pace, and TS%. |
| `tests/test_core_result_table_contracts.py` | Backend section contracts | Locks only section names, not route-specific supporting columns. |
| `frontend/src/test/routeToPattern.test.ts` | Route mapping tests | Protects current renderer selection and non-fallback behavior. |
| `frontend/src/test/resultShapes.test.ts` | Shape tests | Protects generic vs specialized leaderboard shape classification. |
| `frontend/src/test/wave1TableContracts.test.tsx` | Wave 1 table tests | Locks only rank/entity/primary metric for generic leaderboards. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Wave 2 table tests | `lineup_leaderboard` fixture uses synthetic `lineup`, not actual backend `lineup_name`/`player_names`. |

## Current Leaderboard Inventory

| Route/family | Renderer | Sections | Primary metric | Current visible columns | Supporting columns behavior | Row cap | Example queries |
|---|---|---|---|---|---|---|---|
| `season_leaders` | `LeaderboardResult` | `leaderboard` | `metricKey` prop absent, then metadata stat/metric hint, then query hint, then highest-priority numeric row key | `#`, `Player`, primary metric, then inferred fields such as `Season`, `TM`, `GP`, `Type`, and shooting components when present | Dynamic row-key inference sorted by one shared display order | No frontend cap; backend/natural default usually 10 | `top scorers this season`; `best field goal percentage`; `points leaders last 10` |
| `season_team_leaders` | `LeaderboardResult` | `leaderboard` | Same generic logic; team query hints can select `wins`, `win_pct`, ratings, or per-game stats | `#`, `Team`, primary metric, then inferred fields such as `Season`, `GP`, `Losses`, `Type`, or shooting components | Dynamic row-key inference | No frontend cap; backend/natural default usually 10 | `best team offensive rating this season`; `teams with most wins this season` |
| `team_record_leaderboard` | `LeaderboardResult` | `leaderboard` | Generic query hint usually picks `win_pct`, `wins`, or `losses` | `#`, `Team`, primary metric, then inferred `Season`, `GP`, `Wins`, `Losses`, `Win %`, `Type` as available | Dynamic row-key inference | No frontend cap; backend default 10 | `best team record this season`; `worst away record since 2020` |
| `player_occurrence_leaders` | `LeaderboardResult` | `leaderboard` | Dynamic event-count column, e.g. `triple doubles` or `games_pts_40+` | `#`, `Player`, event count, then inferred `Season`, `TM`, `GP`, `Type` | Dynamic row-key inference; event label becomes a row key | No frontend cap; natural leaderboard default 10; distinct-count paths can use `limit=None` | `leaders in triple doubles this season`; structured `player_occurrence_leaders` for 40-point games |
| `team_occurrence_leaders` | `LeaderboardResult` | `leaderboard` | Dynamic event-count column, e.g. `games_pts_120+` | `#`, `Team`, event count, then inferred `Season`, `GP`, `Type` | Dynamic row-key inference; team rows may have only `team_abbr` | No frontend cap; backend/natural default 10 | `teams with most 120 point games this season` |
| `player_stretch_leaderboard` | `RollingStretchResult` | `leaderboard`; optional named-player game-log sections | `stretch_metric` row field/metadata controls `stretch_value` label | League table: `Rank`, `Player`, `Window`, stretch metric, `Start`, `End`, `Season`, plus at most two support fields if backend emits them | Specialized renderer, not generic `LeaderboardResult` | No frontend cap; backend/natural default 10 | `hottest 3-game scoring stretch this year`; `Booker hottest 4-game scoring stretch` |
| `playoff_appearances` league-wide | `LeaderboardResult` when `leaderboard` exists | `leaderboard` | Route config forces `appearances` | `#`, `Team`, `Appearances`, then inferred `Seasons`/`Season` and `Round` | Dynamic row-key inference with a forced metric | No frontend cap; backend default 10 | `most playoff appearances`; `teams with most Finals appearances` |
| `lineup_leaderboard` | `LeaderboardResult` | `leaderboard` | Route config forces `net_rating` unless future stat prop is added | Synthetic fixture: `#`, `Name`, `Net`, `TM`, `Minutes`, `ORtg`, `DRtg`. Actual backend fields can classify as team and expose IDs dynamically. | Dynamic row-key inference; actual lineup identity fields are not currently recognized by `LeaderboardResult` | No frontend cap; backend/natural default 10 | `best 5-man lineups`; `best 3-man units with at least 200 minutes` |
| `record_by_decade_leaderboard` | `RecordResult` mode `record_by_decade_leaderboard` | `leaderboard` | `metadata.stat`/`metric`, then query hint, then `wins`/`win_pct` fallback | `#`, `Team`, `Decade`, primary metric, `W-L`, optional `Games`, optional `Win %`, optional `Seasons`, optional `Season Type` | Specialized route-specific columns already | No frontend cap; backend returns top N per decade, so total rows can exceed N | `most wins by decade since 2010`; `best record by decade` |
| `top_player_games` | `TopPerformancesResult` subject `player` | `leaderboard` | Metadata stat/metric, query hint, or stat-order fallback | `Rank`, `Player`, `Date`, `Opp`, `Result`, optional `Score`, primary metric, and support stats. For points: `REB`, `AST`, `3PM` when present | Specialized renderer with metric-specific support stat rules | No frontend cap; backend/natural default 10 | `highest scoring games this season` |
| `top_team_games` | `TopPerformancesResult` subject `team` | `leaderboard` | Same top-performance logic | `Rank`, `Team`, `Date`, `Opp`, `Result`, optional `Score`, primary metric, and support stats | Specialized renderer with metric-specific support stat rules | No frontend cap; backend/natural default 10 | `biggest team scoring nights` |

## Actual Row-Field Inventory

Representative query sweep through `nbatools.query_service`:

| Route/family | Example/query/source | Section | First-row keys | Missing fields for desired product columns |
|---|---|---|---|---|
| `season_leaders` | natural `top scorers this season` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `games_played`, `pts_per_game`, `season`, `season_type` | `minutes_per_game` is not present unless it is the primary metric; other box-score support stats are not present. |
| `season_leaders` shooting | structured `season_leaders(stat="fg_pct")` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `games_played`, `fg_pct`, `fgm_total`, `fga_total`, `season`, `season_type` | No MPG or secondary averages; shooting make/attempt context is present. |
| `season_leaders` TS | structured `season_leaders(stat="ts_pct")` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `games_played`, `ts_pct`, `fga_total`, `fta_total`, `season`, `season_type` | No points or minutes context. |
| `season_leaders` advanced | structured `season_leaders(stat="net_rating")` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `games_played`, `net_rating`, `season`, `season_type` | No minutes, usage, ORtg/DRtg support columns unless emitted as the metric. |
| `season_team_leaders` | natural `best team offensive rating this season` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `games_played`, `off_rating`, `season`, `season_type` | PTS, Opp PTS, Net, DRtg, and Pace are not all present unless selected/merged in the row. |
| `season_team_leaders` record | structured `season_team_leaders(stat="wins")` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `games_played`, `wins`, `losses`, `season`, `season_type` | `win_pct` is not present on wins rows from this route; record-specific route has better record context. |
| `season_team_leaders` shooting | structured `season_team_leaders(stat="fg_pct")` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `games_played`, `fg_pct`, `fgm_total`, `fga_total`, `season`, `season_type` | No broad team profile stats. |
| `team_record_leaderboard` | natural `best team record this season` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `games_played`, `wins`, `losses`, `win_pct`, `season`, `season_type` | PPG, Opp PPG, net/margin not present. |
| `player_occurrence_leaders` | natural `leaders in triple doubles this season` | `leaderboard` | `rank`, `player_name`, `team_abbr`, `games_played`, `triple doubles`, `season`, `season_type` | Rate/frequency and threshold decomposition are not row fields; special-event definition is in caveats. |
| `player_occurrence_leaders` | structured `player_occurrence_leaders(stat="pts", min_value=40)` | `leaderboard` | `rank`, `player_name`, `team_abbr`, `games_played`, `games_pts_40+`, `season`, `season_type` | Rate/frequency unavailable. |
| `team_occurrence_leaders` | natural `teams with most 120 point games this season` | `leaderboard` | `rank`, `team_abbr`, `games_played`, `games_pts_120+`, `season`, `season_type` | Team name may be absent; rate/frequency unavailable. |
| `player_stretch_leaderboard` | natural `hottest 3-game scoring stretch this year` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `window_size`, `stretch_metric`, `window_start_date`, `window_end_date`, `window_start_season`, `games_in_window`, `window_end_season`, `stretch_value` | Per-window PTS/REB/AST/FG/TS support columns are not emitted. |
| `playoff_appearances` league-wide | natural `most playoff appearances` | `leaderboard` | `rank`, `team_abbr`, `team_name`, `appearances`, `round`, `seasons` | Last appearance and first appearance are not present. |
| `lineup_leaderboard` | local natural/structured query with current checkout data | none | No rows; trusted `league_lineup_viz` coverage unavailable locally. | Actual row keys inferred from source-backed tests and `_lineup_execution.RESULT_COLUMNS`. |
| `lineup_leaderboard` source-backed contract | `_lineup_execution.RESULT_COLUMNS` plus inserted `rank` | `leaderboard` | `rank`, `season`, `season_type`, `team_abbr`, `unit_size`, `lineup_id`, `lineup_name`, `player_ids`, `player_names`, `minute_minimum`, `minutes`, `off_rating`, `def_rating`, `net_rating`, `pace`, `ts_pct` | Current generic frontend does not recognize `lineup_name`/`player_names` as lineup identity. |
| `record_by_decade_leaderboard` | natural `most wins by decade since 2010` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `decade`, `games_played`, `wins`, `losses`, `win_pct`, `season_type`, `seasons` | Season count per decade is not present; `seasons` is the requested range, not row-specific count. |
| `top_player_games` | natural `highest scoring games this season` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `game_date`, `game_id`, `pts`, `opponent_team_abbr`, `is_home`, `is_away`, `season`, `season_type`, `team_id`, `team_name`, `opponent_team_id`, `opponent_team_name`, `wl`, `minutes`, `reb`, `ast`, `stl`, `blk`, `fgm`, `fga`, `fg3m`, `fg3a`, `ftm`, `fta`, `tov`, `pf`, `plus_minus`, `fg_pct`, `fg3_pct`, `ft_pct` | Player rows do not expose `team_score`/`opponent_score`, so the optional Score column usually cannot render. |
| `top_team_games` | natural `biggest team scoring nights` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `game_date`, `game_id`, `pts`, `opponent_team_abbr`, `is_home`, `is_away`, `wl`, `season`, `season_type`, `opponent_team_id`, `opponent_team_name`, `opponent_pts`, `reb`, `ast`, `stl`, `blk`, `fgm`, `fga`, `fg3m`, `fg3a`, `ftm`, `fta`, `tov`, `oreb`, `dreb`, `minutes`, `plus_minus`, `fg_pct`, `fg3_pct`, `ft_pct` | Score can render for team rows because `pts` and `opponent_pts` are present. |

## Recommended Supporting Columns

Recommendations below are locked/default display decisions only. They do not
claim unavailable backend fields exist.

| Route/family | Recommended default columns | Metric-specific columns | Hidden/detail fields | Why |
|---|---|---|---|---|
| `season_leaders` | `Rank`, `Player`, primary metric, `Team`, `GP`, `Season`, `Season Type` | Shooting percentage metrics: show makes/attempts available in row (`FGM/FGA`, `3PM/3PA`, `FTM/FTA`, `FGA/FTA` for TS). Count metrics: show `GP`. Advanced ratings: show `GP` only unless backend emits more. | Hide `player_id`; no raw drawer in next wave. | Uses fields consistently present today and avoids pretending MPG/secondary stats are available. |
| `season_team_leaders` | `Rank`, `Team`, primary metric, `GP`, `Season`, `Season Type` | Record-ish stats from this route: show `Wins`/`Losses` when present. Shooting metrics: show makes/attempts. Advanced ratings: show `GP`. | Hide `team_id`; no raw drawer. | Keeps team rows compact and stable; richer PTS/Opp PTS/Net profile would require backend support. |
| `team_record_leaderboard` | `Rank`, `Team`, `W-L`, `Win %`, `Games`, `Season`, `Season Type` | If primary metric is `wins` or `losses`, keep W-L and Win % visible; if primary metric is `win_pct`, still show W-L and Games. | Hide `team_id`; no raw drawer. | Record semantics are clearer as W-L plus win percentage than as a generic metric row. |
| `player_occurrence_leaders` | `Rank`, `Player`, event count, `Team`, `GP`, `Season`, `Season Type` | Special-event caveat remains in caveats; compound-event text remains backend caveat until a row-level event descriptor exists. | Hide `player_id`; no raw drawer. | The count and denominator are the trustworthy fields currently available. |
| `team_occurrence_leaders` | `Rank`, `Team`, event count, `GP`, `Season`, `Season Type` | If backend later adds rate/frequency, add it after count and GP. | Hide IDs; no raw drawer. | Avoids unstable event-key ordering and keeps denominator visible. |
| `player_stretch_leaderboard` | Keep current specialized columns: `Rank`, `Player`, `Window`, stretch metric, `Start`, `End`, `Season` | If backend later emits per-window support averages, allow at most two support columns, metric-family-specific. | Existing renderer has no raw drawer. | Already a separate table pattern; generic leaderboard config should not absorb it. |
| `playoff_appearances` league-wide | `Rank`, `Team`, `Appearances`, `Round`, `Seasons` or `Season` | None until backend exposes first/last appearance. | Hide IDs; no raw drawer. | These fields answer the ranking and context without inventing history fields. |
| `lineup_leaderboard` | `Rank`, `Lineup`, `Team`, primary metric defaulting to `Net`, `Minutes`, `ORtg`, `DRtg`, `Pace`, `TS%` | If primary metric is `minutes`, still show `Net`, `ORtg`, `DRtg`; if primary is an efficiency/rating field, show `Minutes` first. Show `Min` or `Minute Min` if `minute_minimum` is present and product space allows. | Hide `lineup_id`, `player_ids`, raw `player_names`, and `unit_size`; no drawer in first pass. | Highest-risk route because actual backend identity keys differ from synthetic frontend tests. |
| `record_by_decade_leaderboard` | Keep current specialized columns: `Rank`, `Team`, `Decade`, primary metric, `W-L`, `Games`, `Win %`, `Seasons`, `Season Type` | If primary is `win_pct`, W-L and Games stay visible; if primary is `wins`/`losses`, Win % stays visible. | No raw drawer currently. | Already route-specific and generally aligned with product need. |
| `top_player_games` | Keep current specialized columns: `Rank`, `Player`, `Date`, `Opp`, `Result`, primary metric, support stats | Points: `REB`, `AST`, `3PM`; assists: `PTS`, `REB`, `TOV`; rebounds: `PTS`, `AST`; threes: `PTS`, `3PA`. Add `Score` only when backend exposes scores. | Hide IDs, game IDs, location booleans; no raw drawer. | Top performances are already curated and should remain visually distinct from season leaderboards. |
| `top_team_games` | Keep current specialized columns: `Rank`, `Team`, `Date`, `Opp`, `Result`, `Score`, primary metric, support stats | Same support-stat policy as current renderer; team scoring rows can show `Score` from `pts` and `opponent_pts`. | Hide IDs, game IDs, location booleans; no raw drawer. | Current renderer has the right table shape; only query routing quirks are outside this preflight. |

## Decision Matrix

| Route/family | Current behavior | Available fields | Product issue | Options | Recommendation | Implementation size | Test impact |
|---|---|---|---|---|---|---|---|
| `season_leaders` | Generic dynamic supporting columns | Identity, team, GP, primary metric, metric-specific attempts, season context | Common route but columns vary by row key order and do not make qualifier context explicit | Keep dynamic; universal columns; route-specific config; backend metadata | Route-specific frontend config using current fields | Small-medium | Update Wave 1 table tests for player season leaders and metric-specific shooting rows |
| `season_team_leaders` | Generic dynamic supporting columns | Team identity, GP, primary metric, some record/shooting context, season context | Team rows can look too thin and record semantics differ from stat semantics | Keep dynamic; route-specific config; backend metadata | Route-specific frontend config using current fields | Small-medium | Add team metric family fixtures: rating, wins, shooting |
| `team_record_leaderboard` | Generic dynamic supporting columns | Team, games, wins, losses, win_pct, season context | W-L should be a locked record display, not inferred separate fields | Keep generic; route-specific config; reuse record renderer | Route-specific config in generic leaderboard or move later to record-style helper | Small | Add rendered table test for W-L, Win %, Games |
| `player_occurrence_leaders` | Generic dynamic event-count column | Player, team, games_played, dynamic event count, season context | Event-count key labels are unstable and denominator must be visible | Keep dynamic; route-specific occurrence config; backend event metadata | Route-specific config that detects event count and locks GP/Team context | Small-medium | Add player occurrence fixture with `triple doubles` and `games_pts_40+` |
| `team_occurrence_leaders` | Generic dynamic event-count column | Team abbreviation/name, games_played, dynamic event count, season context | Team name may be absent; rate unavailable; event key order is unstable | Keep dynamic; route-specific occurrence config; backend event metadata | Route-specific config that detects event count and locks GP context | Small-medium | Add team occurrence fixture with only `team_abbr` |
| `player_stretch_leaderboard` | Specialized `RollingStretchResult` | Window fields and `stretch_value`; optional game-log sections for named player | Backend does not expose per-window support averages; current table is already curated | Leave current; add backend support later; fold into generic config | Leave current specialized renderer | None now | No new tests required in this wave |
| `playoff_appearances` league-wide | Generic dynamic with forced `appearances` metric | Team, appearances, round, season/seasons | Last/first appearance unavailable; dynamic order can still vary | Keep dynamic; route-specific appearances config; backend adds first/last season | Route-specific frontend config using current fields | Small | Add ranked appearances table fixture |
| `lineup_leaderboard` | Generic dynamic with forced `net_rating`; fixture uses synthetic `lineup` | Actual rows: lineup_name, player_names, IDs, team, minutes, ORtg, DRtg, Net, Pace, TS%, minute_minimum | Highest risk: actual identity keys are not recognized and ID fields can leak as visible columns | Keep dynamic; route-specific frontend config; backend alias fields; dedicated lineup renderer | Route-specific frontend config and actual-backend-key tests | Medium | Update Wave 2 table/shape fixtures to use actual source-backed row keys |
| `record_by_decade_leaderboard` | Specialized `RecordResult` | Team, decade, games, wins, losses, win_pct, season context | Already mostly correct; row count can exceed default limit because limit is per decade | Leave current; tweak labels; backend adds seasons_appeared | Leave current specialized renderer | None-small | No generic leaderboard tests; optional explicit top-N-per-decade fixture |
| `top_player_games` | Specialized `TopPerformancesResult` | Game row fields, opponent, W/L, primary stat, support stats; no player score fields | Player Score column usually cannot render because scores are absent | Leave current; backend score enrichment; route-specific top config | Leave current; consider backend score enrichment later | None now | No generic leaderboard tests; optional future score fixture |
| `top_team_games` | Specialized `TopPerformancesResult` | Game row fields, opponent score, primary stat, support stats | Current table is consistent; natural query phrasing can route to season team leaders unless top-game phrase is clear | Leave current; parser/routing work later | Leave current | None now | No new tests for this wave |

## Risks And Constraints

- Dynamic row keys produce unpredictable supporting column order when a new backend
  field appears.
- Generic leaderboard has no raw detail drawer, so hidden fields are not
  recoverable in the UI.
- Several desired columns are not backend row fields today: player MPG on most
  season leader rows, broad support stats on season leader rows, team PPG/Opp
  PPG/Net on record rows, occurrence rate/frequency, and first/last playoff
  appearance.
- `lineup_leaderboard` can misidentify actual backend lineup rows because
  `LeaderboardResult` does not read `lineup_name` or `player_names`.
- `lineup_leaderboard` can expose implementation fields (`lineup_id`,
  `player_ids`, `unit_size`) as visible support columns if actual source-backed
  rows reach the generic dynamic renderer.
- Team occurrence rows may contain only `team_abbr`; the display must still
  render a clean team identity.
- Supporting columns can clutter mobile if all available fields are shown.
- Primary metric labels for dynamic event keys such as `games_pts_120+` are
  mechanically formatted and may be less clear than route-specific labels.
- Record and stat leaderboards should not be forced into one universal column
  set; W-L semantics are product-specific.
- Top performances and generic leaderboards already diverge visually. That is
  acceptable, but their rank/date/opponent/result conventions should remain
  internally consistent.

## Recommended Implementation Wave

Choose Option C: add route-specific frontend column configs for leaderboard
routes that still render through generic `LeaderboardResult`.

Exact next scope:

1. Add a small route/family column-selection layer inside or next to
   `LeaderboardResult`.
2. Do not refactor `routeToPattern` into a registry.
3. Do not change backend result shapes.
4. Keep `TopPerformancesResult`, `RollingStretchResult`, and `RecordResult` as
   specialized renderers.
5. Lock current-source fields only:
   - season leaderboards: identity, primary metric, team/GP/season context,
     plus metric-specific shooting context when present
   - record leaderboards: W-L, Win %, games, season context
   - occurrence leaderboards: event count, GP, team/season context
   - playoff appearances: appearances, round, seasons
   - lineup leaderboard: lineup identity from `lineup_name`/`player_names`,
     team, primary metric, minutes, ORtg, DRtg, Pace, TS%
6. Add frontend contract tests using actual backend-like row keys, especially
   for `lineup_leaderboard`.

Why Option C instead of the other choices:

- Option A leaves a known display-risk route (`lineup_leaderboard`) unresolved.
- Option B would force unrelated leaderboard families into one universal table.
- Option D is directionally attractive but heavier than needed; the frontend
  already knows the route and current row keys are stable enough for display
  defaults.
- Option E is defensible, but the route-specific config layer is small enough
  to cover all generic leaderboard families in one PR-sized unit without
  touching backend behavior.

## Validation And Confidence

Commands run:

- Read-only source and doc inspection with `sed` and `rg`.
- Representative query sweeps through `.venv/bin/python -c` using
  `nbatools.query_service.execute_natural_query`.
- Targeted structured query sweeps through `.venv/bin/python -c` using
  `nbatools.query_service.execute_structured_query`.

Representative queries executed:

| Query/source | Route | Result status | Sections |
|---|---|---|---|
| `top scorers this season` | `season_leaders` | `ok` | `leaderboard` |
| `best team offensive rating this season` | `season_team_leaders` | `ok` | `leaderboard` |
| `best team record this season` | `team_record_leaderboard` | `ok` | `leaderboard` |
| `leaders in triple doubles this season` | `player_occurrence_leaders` | `ok` | `leaderboard` |
| structured `player_occurrence_leaders(stat="pts", min_value=40)` | `player_occurrence_leaders` | `ok` | `leaderboard` |
| `teams with most 120 point games this season` | `team_occurrence_leaders` | `ok` | `leaderboard` |
| `hottest 3-game scoring stretch this year` | `player_stretch_leaderboard` | `ok` | `leaderboard` |
| `most playoff appearances` | `playoff_appearances` | `ok` | `leaderboard` |
| `best 5-man lineups` | `lineup_leaderboard` | `no_result` / `unsupported` | none |
| `most wins by decade since 2010` | `record_by_decade_leaderboard` | `ok` | `leaderboard` |
| `highest scoring games this season` | `top_player_games` | `ok` | `leaderboard` |
| `biggest team scoring nights` | `top_team_games` | `ok` | `leaderboard` |

Limitations:

- Local trusted lineup coverage was unavailable, so `lineup_leaderboard` row
  keys are based on backend source contracts and source-backed tests rather
  than a successful local production query.
- No production code was changed.
- No frontend browser render was executed.
- This preflight does not decide backend metadata design beyond noting that it
  is a future option.
