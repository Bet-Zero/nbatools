# Leaderboard Supporting Columns Preflight Return Package

## 1. Executive summary

- Routes/families reviewed: `season_leaders`, `season_team_leaders`,
  `team_record_leaderboard`, `player_occurrence_leaders`,
  `team_occurrence_leaders`, `player_stretch_leaderboard`,
  `playoff_appearances` league-wide leaderboard variant,
  `lineup_leaderboard`, `record_by_decade_leaderboard`,
  `top_player_games`, and `top_team_games`.
- Biggest finding: generic `LeaderboardResult` infers supporting columns from
  row keys; route families need different stable defaults.
- Recommended next implementation: Option C, add route-specific frontend column
  configs for generic leaderboard routes without backend behavior changes.
- Highest-impact leaderboard family: player/team season leaderboards, because
  they are common entry points and currently depend on generic dynamic context.
- Highest-risk route: `lineup_leaderboard`, because actual backend row keys are
  not the synthetic lineup identity keys used by the current frontend fixture.
- Should production code change now? yes in the next implementation wave;
  this preflight itself changed docs only.

## 2. Files inspected

| File | Why inspected | Key finding |
|---|---|---|
| `docs/planning/raw-product/RAW_QUERY_PRODUCT_MAP.md` | Current product map | Lists leaderboard routes and renderer families. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Locked contracts | Calls generic leaderboard supporting columns inferred and undecided. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_1_RETURN_PACKAGE.md` | Wave 1 context | Generic leaderboard only locked rank/entity/metric. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_2_RETURN_PACKAGE.md` | Wave 2 context | Confirms lineup/decade/playoff current behavior and deferred decisions. |
| `return_packages/raw-product/WEAK_CONTRACT_DECISION_PREFLIGHT_RETURN_PACKAGE.md` | Weak-contract decision context | Established single-team playoff appearances as a separate, already-cleaned-up concern. |
| `return_packages/raw-product/WEAK_CONTRACT_CLEANUP_WAVE_1_RETURN_PACKAGE.md` | Latest cleanup context | Confirms route-specific leaderboard columns are the next recommended phase. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Generic leaderboard behavior | Columns are rank, entity, primary metric, then dynamically inferred fields. |
| `frontend/src/components/results/patterns/TopPerformancesResult.tsx` | Top Performances behavior | Already uses curated single-game columns and metric-specific support stats. |
| `frontend/src/components/results/patterns/RollingStretchResult.tsx` | Stretch behavior | Already uses a specialized rolling-window table. |
| `frontend/src/components/results/patterns/RecordResult.tsx` | Record by decade behavior | `record_by_decade_leaderboard` already has specialized columns. |
| `frontend/src/components/results/config/routeToPattern.ts` | Renderer mapping | Shows which routes still use generic leaderboard rendering. |
| `frontend/src/components/results/resultShapes.ts` | Shape classification | Generic leaderboards collapse to `leaderboard_table`; specialized top/stretch/record shapes remain separate. |
| `frontend/src/components/results/primitives/ResultTable.tsx` | Shared table primitive | Supports highlight and row caps; generic leaderboard passes no frontend cap. |
| `frontend/src/components/results/primitives/detailTables.ts` | Detail drawer helper | Generic leaderboard does not use raw/detail drawers. |
| `frontend/src/api/types.ts` | Route union | Includes all reviewed routes. |
| `src/nbatools/commands/natural_query.py` | Routing/default limits | Natural leaderboard routes generally default to top 10. |
| `src/nbatools/commands/_natural_query_execution.py` | Builder map | All reviewed routes are production-mapped. |
| `src/nbatools/commands/season_leaders.py` | Player season row fields | Emits identity, GP, primary metric, optional metric context, and season context. |
| `src/nbatools/commands/season_team_leaders.py` | Team season row fields | Emits team identity, GP, primary metric, optional metric context, and season context. |
| `src/nbatools/commands/team_record.py` | Record leaderboard fields | Emits games, wins, losses, win percentage, and season context. |
| `src/nbatools/commands/player_occurrence_leaders.py` | Player occurrence fields | Emits a dynamic occurrence-count field plus GP and season context. |
| `src/nbatools/commands/team_occurrence_leaders.py` | Team occurrence fields | Emits team key, dynamic count, GP, and season context. |
| `src/nbatools/commands/player_stretch_leaderboard.py` | Stretch fields | Emits window metadata and `stretch_value`; no per-window support averages. |
| `src/nbatools/commands/playoff_history.py` | Playoff/decade fields | Emits appearances rows and decade record leaderboard rows. |
| `src/nbatools/commands/lineup_leaderboard.py` | Lineup route | Returns source-backed lineup rows with rank inserted. |
| `src/nbatools/commands/_lineup_execution.py` | Actual lineup contract | Actual rows use `lineup_name`, `player_names`, IDs, minutes, ratings, pace, and TS%. |
| `tests/test_core_result_table_contracts.py` | Backend section tests | Locks section names but not supporting column choices. |
| `frontend/src/test/routeToPattern.test.ts` | Route tests | Protects current renderer mapping. |
| `frontend/src/test/resultShapes.test.ts` | Shape tests | Protects generic/specialized shape classification. |
| `frontend/src/test/wave1TableContracts.test.tsx` | Wave 1 table tests | Generic leaderboard test does not lock route-specific supports. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Wave 2 table tests | `lineup_leaderboard` uses synthetic `lineup`, not actual backend keys. |

## 3. Current leaderboard inventory

| Route/family | Renderer | Sections | Primary metric | Current visible columns | Supporting columns behavior | Row cap | Example queries |
|---|---|---|---|---|---|---|---|
| `season_leaders` | `LeaderboardResult` | `leaderboard` | prop metric, metadata hint, query hint, then numeric priority | `#`, `Player`, primary metric, dynamic `Season`/`TM`/`GP`/`Type` and metric context | Dynamic | No frontend cap; backend default 10 | `top scorers this season` |
| `season_team_leaders` | `LeaderboardResult` | `leaderboard` | same generic logic | `#`, `Team`, primary metric, dynamic `Season`/`GP`/`Type` and metric context | Dynamic | No frontend cap; backend default 10 | `best team offensive rating this season` |
| `team_record_leaderboard` | `LeaderboardResult` | `leaderboard` | generic hint usually `win_pct`, `wins`, or `losses` | `#`, `Team`, primary metric, inferred games/wins/losses/win pct/season context | Dynamic | No frontend cap; backend default 10 | `best team record this season` |
| `player_occurrence_leaders` | `LeaderboardResult` | `leaderboard` | dynamic event-count field | `#`, `Player`, event count, inferred team/GP/season context | Dynamic | No frontend cap; usually 10, but count paths can use all rows | `leaders in triple doubles this season` |
| `team_occurrence_leaders` | `LeaderboardResult` | `leaderboard` | dynamic event-count field | `#`, `Team`, event count, inferred GP/season context | Dynamic | No frontend cap; backend default 10 | `teams with most 120 point games this season` |
| `player_stretch_leaderboard` | `RollingStretchResult` | `leaderboard` | `stretch_metric` labels `stretch_value` | `Rank`, `Player`, `Window`, metric, `Start`, `End`, `Season` | Specialized | No frontend cap; backend default 10 | `hottest 3-game scoring stretch this year` |
| `playoff_appearances` league-wide | `LeaderboardResult` | `leaderboard` | forced `appearances` | `#`, `Team`, `Appearances`, inferred `Round`/`Seasons` | Dynamic with forced metric | No frontend cap; backend default 10 | `most playoff appearances` |
| `lineup_leaderboard` | `LeaderboardResult` | `leaderboard` | forced `net_rating` | Synthetic fixture shows `#`, `Name`, `Net`, `TM`, `Minutes`, `ORtg`, `DRtg`; actual rows can differ | Dynamic; actual backend lineup keys are not recognized as identity | No frontend cap; backend default 10 | `best 5-man lineups` |
| `record_by_decade_leaderboard` | `RecordResult` | `leaderboard` | record-specific metric resolver | `#`, `Team`, `Decade`, metric, `W-L`, `Games`, `Win %`, `Seasons`, `Season Type` | Specialized | No frontend cap; top N per decade | `most wins by decade since 2010` |
| `top_player_games` | `TopPerformancesResult` | `leaderboard` | metadata/query/stat-order metric | `Rank`, `Player`, `Date`, `Opp`, `Result`, optional `Score`, metric, support stats | Specialized | No frontend cap; backend default 10 | `highest scoring games this season` |
| `top_team_games` | `TopPerformancesResult` | `leaderboard` | metadata/query/stat-order metric | `Rank`, `Team`, `Date`, `Opp`, `Result`, `Score`, metric, support stats | Specialized | No frontend cap; backend default 10 | `biggest team scoring nights` |

## 4. Actual row-field inventory

| Route/family | Example/query/source | Section | First-row keys | Missing fields |
|---|---|---|---|---|
| `season_leaders` | `top scorers this season` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `games_played`, `pts_per_game`, `season`, `season_type` | MPG and secondary stats absent. |
| `season_leaders` shooting | structured `stat=fg_pct` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `games_played`, `fg_pct`, `fgm_total`, `fga_total`, `season`, `season_type` | MPG and secondary averages absent. |
| `season_team_leaders` | `best team offensive rating this season` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `games_played`, `off_rating`, `season`, `season_type` | PTS/Opp PTS/Net/Pace not universally present. |
| `team_record_leaderboard` | `best team record this season` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `games_played`, `wins`, `losses`, `win_pct`, `season`, `season_type` | PPG, Opp PPG, margin/net absent. |
| `player_occurrence_leaders` | `leaders in triple doubles this season` | `leaderboard` | `rank`, `player_name`, `team_abbr`, `games_played`, `triple doubles`, `season`, `season_type` | Rate/frequency absent; special-event definition is caveat only. |
| `player_occurrence_leaders` | structured 40-point games | `leaderboard` | `rank`, `player_name`, `team_abbr`, `games_played`, `games_pts_40+`, `season`, `season_type` | Rate/frequency absent. |
| `team_occurrence_leaders` | `teams with most 120 point games this season` | `leaderboard` | `rank`, `team_abbr`, `games_played`, `games_pts_120+`, `season`, `season_type` | Team name and rate/frequency can be absent. |
| `player_stretch_leaderboard` | `hottest 3-game scoring stretch this year` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `window_size`, `stretch_metric`, `window_start_date`, `window_end_date`, `window_start_season`, `games_in_window`, `window_end_season`, `stretch_value` | Per-window PTS/REB/AST/efficiency support columns absent. |
| `playoff_appearances` league-wide | `most playoff appearances` | `leaderboard` | `rank`, `team_abbr`, `team_name`, `appearances`, `round`, `seasons` | First/last appearance absent. |
| `lineup_leaderboard` | `_lineup_execution.RESULT_COLUMNS` plus rank | `leaderboard` | `rank`, `season`, `season_type`, `team_abbr`, `unit_size`, `lineup_id`, `lineup_name`, `player_ids`, `player_names`, `minute_minimum`, `minutes`, `off_rating`, `def_rating`, `net_rating`, `pace`, `ts_pct` | Local trusted coverage unavailable; current frontend identity does not read `lineup_name`/`player_names`. |
| `record_by_decade_leaderboard` | `most wins by decade since 2010` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `decade`, `games_played`, `wins`, `losses`, `win_pct`, `season_type`, `seasons` | Row-specific season count absent. |
| `top_player_games` | `highest scoring games this season` | `leaderboard` | `rank`, `player_name`, `player_id`, `team_abbr`, `game_date`, `game_id`, `pts`, `opponent_team_abbr`, `is_home`, `is_away`, `season`, `season_type`, `team_id`, `team_name`, `opponent_team_id`, `opponent_team_name`, `wl`, `minutes`, `reb`, `ast`, `stl`, `blk`, `fgm`, `fga`, `fg3m`, `fg3a`, `ftm`, `fta`, `tov`, `pf`, `plus_minus`, `fg_pct`, `fg3_pct`, `ft_pct` | Score fields absent for player rows. |
| `top_team_games` | `biggest team scoring nights` | `leaderboard` | `rank`, `team_name`, `team_abbr`, `team_id`, `game_date`, `game_id`, `pts`, `opponent_team_abbr`, `is_home`, `is_away`, `wl`, `season`, `season_type`, `opponent_team_id`, `opponent_team_name`, `opponent_pts`, `reb`, `ast`, `stl`, `blk`, `fgm`, `fga`, `fg3m`, `fg3a`, `ftm`, `fta`, `tov`, `oreb`, `dreb`, `minutes`, `plus_minus`, `fg_pct`, `fg3_pct`, `ft_pct` | None for current top-team score display. |

## 5. Recommended supporting columns

| Route/family | Recommended default columns | Metric-specific columns | Hidden/detail fields | Why |
|---|---|---|---|---|
| `season_leaders` | `Rank`, `Player`, metric, `Team`, `GP`, `Season`, `Season Type` | Shooting: makes/attempts; count/advanced: GP only unless row emits more | Hide IDs; no drawer in next wave | Stable on current fields. |
| `season_team_leaders` | `Rank`, `Team`, metric, `GP`, `Season`, `Season Type` | Record-ish: wins/losses when present; shooting: makes/attempts | Hide IDs | Avoids unavailable broad team profile columns. |
| `team_record_leaderboard` | `Rank`, `Team`, `W-L`, `Win %`, `Games`, `Season`, `Season Type` | Keep W-L and Win % visible for wins/losses/win_pct metrics | Hide IDs | Record leaderboards need record semantics. |
| `player_occurrence_leaders` | `Rank`, `Player`, event count, `Team`, `GP`, `Season`, `Season Type` | None until event descriptor/rate exists | Hide IDs | Count plus denominator is the useful current context. |
| `team_occurrence_leaders` | `Rank`, `Team`, event count, `GP`, `Season`, `Season Type` | Future rate/frequency if backend emits it | Hide IDs | Keeps team occurrence rows predictable. |
| `player_stretch_leaderboard` | Keep `Rank`, `Player`, `Window`, metric, `Start`, `End`, `Season` | Future per-window support averages, max two | No current drawer | Already specialized. |
| `playoff_appearances` league-wide | `Rank`, `Team`, `Appearances`, `Round`, `Seasons`/`Season` | None currently | Hide IDs | Current row fields answer the product question. |
| `lineup_leaderboard` | `Rank`, `Lineup`, `Team`, metric/`Net`, `Minutes`, `ORtg`, `DRtg`, `Pace`, `TS%` | If metric is `minutes`, still show ratings; if metric is rating, show minutes first | Hide `lineup_id`, `player_ids`, raw `player_names`, `unit_size`; no drawer first | Fixes the highest-risk actual row-key mismatch. |
| `record_by_decade_leaderboard` | Keep `Rank`, `Team`, `Decade`, metric, `W-L`, `Games`, `Win %`, `Seasons`, `Season Type` | Keep Win % visible for wins/losses metrics | No current drawer | Already specialized and aligned. |
| `top_player_games` | Keep `Rank`, `Player`, `Date`, `Opp`, `Result`, metric, support stats | Points: REB/AST/3PM; assists: PTS/REB/TOV; rebounds: PTS/AST; threes: PTS/3PA | Hide IDs/game IDs/location flags | Already curated; Score needs backend fields. |
| `top_team_games` | Keep `Rank`, `Team`, `Date`, `Opp`, `Result`, `Score`, metric, support stats | Current metric-specific support policy | Hide IDs/game IDs/location flags | Already curated. |

## 6. Decision matrix

| Route/family | Current behavior | Available fields | Product issue | Options | Recommendation | Implementation size | Test impact |
|---|---|---|---|---|---|---|---|
| `season_leaders` | Dynamic generic columns | Player, team, GP, metric, season, metric context | Common route lacks explicit context contract | Keep dynamic; universal columns; route config; backend metadata | Route-specific frontend config | Small-medium | Add player season and shooting fixtures |
| `season_team_leaders` | Dynamic generic columns | Team, GP, metric, season, metric context | Team rows can be too thin and inconsistent | Keep dynamic; route config; backend metadata | Route-specific frontend config | Small-medium | Add rating/wins/shooting fixtures |
| `team_record_leaderboard` | Dynamic generic columns | Team, games, wins, losses, win_pct, season | W-L semantics should be explicit | Keep generic; route config; record renderer | Route-specific config | Small | Add W-L table fixture |
| `player_occurrence_leaders` | Dynamic event key | Player, team, GP, event count, season | Event labels and denominator should be stable | Keep dynamic; route config; backend event metadata | Route-specific occurrence config | Small-medium | Add special-event and threshold fixtures |
| `team_occurrence_leaders` | Dynamic event key | Team, GP, event count, season | Team name/rate may be absent; event key ordering unstable | Keep dynamic; route config; backend event metadata | Route-specific occurrence config | Small-medium | Add team-abbr-only fixture |
| `player_stretch_leaderboard` | Specialized stretch renderer | Window fields and stretch value | No per-window supports emitted | Leave; backend support later | Leave current | None | None |
| `playoff_appearances` league-wide | Generic forced metric | Team, appearances, round, seasons | Dynamic order; no first/last appearance | Keep dynamic; route config; backend enrichment | Route-specific config | Small | Add appearances fixture |
| `lineup_leaderboard` | Generic forced metric with synthetic test keys | Actual lineup keys, ratings, IDs | Actual identity keys can be missed and IDs can leak | Keep; route config; backend aliases; dedicated renderer | Route-specific config using actual keys | Medium | Update fixture to backend-like row |
| `record_by_decade_leaderboard` | Specialized record renderer | Team, decade, games, W-L, win_pct, season context | Mostly solved; limit is per decade | Leave; minor label tweaks | Leave current | None-small | Optional per-decade fixture |
| `top_player_games` | Specialized top renderer | Game row stats; no player score fields | Score optional often absent for players | Leave; backend score enrichment later | Leave current | None | Optional future score test |
| `top_team_games` | Specialized top renderer | Game row stats plus opponent points | Current table is consistent | Leave; parser work later if needed | Leave current | None | None |

## 7. Risks and constraints

- Inconsistent columns by row availability.
- Primary metric can be unclear for dynamic event fields.
- Minimum qualifier or denominator can be hidden if GP is not locked.
- Some leaderboards look too thin because backend rows are intentionally sparse.
- Supporting columns can clutter mobile if every row key is shown.
- Dynamic row keys can produce unpredictable order when backend fields are added.
- Backend does not expose several desired fields: MPG on most player season rows,
  team PPG/Opp PPG on record rows, occurrence rate/frequency, first/last playoff
  appearance, and player top-game scores.
- Frontend labels for event keys such as `games_pts_120+` are mechanical.
- `lineup_leaderboard` actual backend keys can diverge from synthetic frontend
  test keys.
- Top performances and generic leaderboards intentionally diverge visually;
  keep that distinction rather than forcing a universal leaderboard shape.

## 8. Recommended implementation wave

Choose Option C: add route-specific frontend column configs for generic
leaderboard routes.

Exact next scope:

- Add a small route/family column-selection layer for generic
  `LeaderboardResult`.
- Keep `routeToPattern` as a switch; do not convert it to a registry.
- Do not change backend result shapes.
- Do not touch `TopPerformancesResult`, `RollingStretchResult`, or
  `RecordResult` except tests if needed for comparison.
- Prioritize actual backend row keys for `lineup_leaderboard`.
- Add frontend tests for season, record, occurrence, appearances, and lineup
  leaderboard fixtures.

Why: route-specific frontend configs solve the current product issue with the
least architecture churn. Backend metadata is a good later refinement but is not
needed to stop dynamic column leakage now.

## 9. Validation / confidence

- Commands run: read-only inspection with `rg`/`sed`; representative query
  sweeps with `.venv/bin/python -c` using `execute_natural_query` and
  `execute_structured_query`.
- Representative queries executed:
  `top scorers this season`, `best team offensive rating this season`,
  `best team record this season`, `leaders in triple doubles this season`,
  structured `player_occurrence_leaders(stat="pts", min_value=40)`,
  `teams with most 120 point games this season`,
  `hottest 3-game scoring stretch this year`, `most playoff appearances`,
  `best 5-man lineups`, `most wins by decade since 2010`,
  `highest scoring games this season`, and `biggest team scoring nights`.
- Limitations: local trusted lineup coverage was unavailable, so lineup
  leaderboard rows were verified from backend contracts/tests rather than a
  successful local query.
- Uncertain behavior needing manual confirmation: visual mobile density after
  route-specific columns, especially lineup and season leaderboards.
