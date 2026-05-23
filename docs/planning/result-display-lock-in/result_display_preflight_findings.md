# Result Display Lock-In Preflight Findings

This planning note is the durable preflight findings record. The result-display
return package remains a handoff receipt under `return_packages/result_display/`,
not the source of truth for these findings.

## 1. Executive summary

- Overall readiness: Ready to start implementation. The current UI already has a single result-rendering entry point, a route-to-pattern mapper, shared answer-table primitives, and dedicated pattern components for all reviewed display families. No implementation blocker was found.
- Biggest implementation risk: Several requested lock-in changes cross pattern boundaries but are not centralized today: context vs caveat separation, raw/detail toggle suppression, row caps/show-all, metric direction metadata, and rolling-stretch intent/deduping.
- Best first implementation wave: A small shared-display wave: update `ResultEnvelope`, `RawDetailToggle`, and `ResultTable` APIs first, then apply the new behavior to the high-duplication patterns (`GameLogResult`, `RecordResult`, `ComparisonResult`, `PlayoffHistoryResult`, `StreakResult`).
- Any blockers: No blocker for shared frontend work. Product/contract decisions are still needed for product-vs-review row caps, rolling-stretch dedupe semantics, and playoff game-record vs series-record priority.

## 2. Files inspected

| Area | Files inspected | Notes |
|---|---|---|
| Source specs | `docs/planning/result-display-lock-in/result_display_lock_in_implementation_spec.md`, `docs/planning/result_display_family_review_lock_in.md`, `docs/planning/result_display_family_review_lock_in_batch_6_addendum.md` | Spec defines 19 reviewed families, global lock-in rules, waves, and targeted fixture IDs. |
| Renderer/routing | `frontend/src/components/results/ResultRenderer.tsx`, `frontend/src/components/results/config/routeToPattern.ts`, `frontend/src/components/results/resultShapes.ts` | Main renderer and route/pattern classification are current. `frontend/src/components/ResultSections.tsx` was not found. |
| Pattern components | `EntitySummaryResult.tsx`, `GameLogResult.tsx`, `LeaderboardResult.tsx`, `TopPerformancesResult.tsx`, `RollingStretchResult.tsx`, `StreakResult.tsx`, `ComparisonResult.tsx`, `RecordResult.tsx`, `PlayoffHistoryResult.tsx`, `FallbackTableResult.tsx`, `SplitResult.tsx` | All reviewed families route to shared pattern components or no-result state. Some components remain family-specific, but they are under the pattern system. |
| Shared primitives | `ResultHero.tsx`, `ResultShell.tsx`, `ResultTable.tsx`, `ResultTable.module.css`, `RawDetailToggle.tsx`, `frontend/src/components/DataTable.tsx`, `frontend/src/design-system/DataTable.tsx` | Answer tables and raw/detail tables are separate systems. |
| Envelope/no-result | `frontend/src/components/ResultEnvelope.tsx`, `frontend/src/components/NoResultDisplay.tsx`, `frontend/src/api/types.ts`, `src/nbatools/api_handlers.py` | Response envelope exposes `notes`, `caveats`, and `metadata.applied_filters`, but no first-class `context` or `interpreted_as` field. |
| Review/fixtures | `docs/architecture/parser/examples.md`, `src/nbatools/parser_examples.py`, `src/nbatools/api.py`, `src/nbatools/api_handlers.py`, `frontend/src/ReviewPage.tsx`, `frontend/src/lib/reviewScreenshots.ts`, `tools/parser_examples_full_sweep.py`, `Makefile`, `frontend/package.json` | Fixture IDs are parser-example indexes. All minimum targeted IDs from the spec are present in the current 402-case extracted set. |
| Rolling stretch backend | `src/nbatools/commands/player_stretch_leaderboard.py`, `src/nbatools/commands/natural_query.py`, `src/nbatools/query_service.py`, `tests/test_player_stretch_leaderboard.py`, `tests/test_query_service.py` | Current backend ranks windows and returns top windows. It does not dedupe to one row per player. Metadata includes window size and stretch metric, but not a display mode such as "which players" vs "best windows". |

## 3. Current architecture map

The current result-display architecture is pattern-based.

- `frontend/src/components/results/ResultRenderer.tsx`
  - `ResultRenderer` is the main result renderer entry point.
  - Evidence: lines 21-29 describe it as "The single entry point"; lines 32-83 route empty/no-result responses to `NoResultDisplay`; line 85 calls `routeToPattern(data)`; lines 87-93 stack pattern blocks inside `ResultShell`; lines 101-175 switch pattern config types to pattern components.
- `frontend/src/components/results/config/routeToPattern.ts`
  - `routeToPattern` maps routes to ordered pattern configs.
  - Evidence: `PatternConfig` is defined at lines 15-65; `routeToPattern` switch starts at lines 67-68; route cases cover the reviewed families at lines 69-207; default fallback is lines 208-210.
- `frontend/src/components/results/resultShapes.ts`
  - Review-page display shapes are derived from `routeToPattern`.
  - Evidence: shape keys include all reviewed family categories at lines 4-27; definitions at lines 61-179; `classifyResultShape` calls `routeToPattern` at line 188 and maps patterns to shapes at lines 201-254; no-result shape classification is lines 271-282.
- `frontend/src/App.tsx`
  - Product UI renders `ResultEnvelope`, `ResultRenderer`, and `RawJsonToggle`.
  - Evidence: lines 564-578.
- `frontend/src/ReviewPage.tsx`
  - Internal review UI uses the same `ResultEnvelope` and `ResultRenderer`.
  - Evidence: visible examples render at lines 544-551; screenshot capture stage renders at lines 593-600.
- Legacy route-specific component check:
  - `frontend/src/components/ResultSections.tsx` was not found by `find frontend/src/components -maxdepth 2 -name 'ResultSections.tsx'`.
  - Legacy-style route-specific logic still exists inside pattern components as mode/route branches, especially `GameLogResult`, `RecordResult`, `PlayoffHistoryResult`, and `ComparisonResult`, but those are currently reached through the pattern renderer rather than a legacy dispatcher.

## 4. Family-to-code map

| Family # | Family name | Current route/pattern | Current component(s) | Implementation notes | Risk |
|---:|---|---|---|---|---|
| 1 | Entity Summary | `player_game_summary` -> `entity_summary` unless recent/opponent game-log context is detected | `EntitySummaryResult`, `ResultHero`, optional `ResultTable` | Route mapping evidence: `routeToPattern.ts` lines 69-80. Renderer evidence: `EntitySummaryResult` lines 18-47. Hero copy evidence: `summarySentence` lines 212-226 and `summaryContext` lines 250-280. Copy is generic and has row/metadata/query access, but does not consume `metadata.applied_filters` or opponent-quality context. | Medium |
| 2 | Message No Result | No displayable rows, non-recoverable reason -> message no-result shape | `ResultRenderer`, `NoResultDisplay` | No-result routing evidence: `ResultRenderer.tsx` lines 32-83. Message/guided classification evidence: `resultShapes.ts` lines 271-282. Copy profile evidence: `NoResultDisplay.tsx` lines 42-124. | Medium |
| 3 | Guided No Result | No displayable rows, `no_match`/`no_data`/empty reason -> guided no-result shape | `NoResultDisplay` | Static suggestions evidence: `NoResultDisplay.tsx` lines 29-40 and 192-203. Backend/query suggestions are rendered if `metadata.suggested_queries` exists, lines 169-180 and helper lines 226-230. | Medium |
| 4 | Entity Summary + Recent Games | `player_game_summary` with last-N or opponent context -> `entity_summary` + `game_log` | `EntitySummaryResult`, `GameLogResult` | Mapping evidence: `routeToPattern.ts` lines 69-80, with `isLastNPlayerSummary` lines 213-221 and `isOpponentPlayerSummary` lines 223-238. Game log evidence: `GameLogResult.tsx` lines 91-167. | Medium |
| 5 | Player Game Log | `player_game_finder` -> `game_log` mode `player` | `GameLogResult`, `RawDetailToggle` | Mapping evidence: `routeToPattern.ts` lines 81-89. Table/render evidence: `GameLogResult.tsx` lines 140-152. Player/team column branching evidence: lines 184-273. Raw detail title is route-configured as "Player Game Detail". | High |
| 6 | Team Game Log | `game_finder` -> `game_log` mode `team` | `GameLogResult`, `RawDetailToggle` | Mapping evidence: `routeToPattern.ts` lines 90-98. Metric highlight detection evidence: `GameLogResult.tsx` lines 425-437. Table column branching evidence: lines 184-273. Raw detail title is route-configured as "Game Detail". | High |
| 7 | Game Summary Log | `game_summary` -> `game_log` mode `team`, with top-performers detail | `GameLogResult`, `RawDetailToggle` | Mapping evidence: `routeToPattern.ts` lines 115-125. Summary strip evidence: `GameLogResult.tsx` lines 112-122 and `summaryItems` lines 364-378. Detail toggles evidence: lines 153-164. | Medium |
| 8 | Streak Table | `player_streak_finder`, `team_streak_finder` -> `streak` | `StreakResult`, `RawDetailToggle` | Mapping evidence: `routeToPattern.ts` lines 143-145. Renderer evidence: `StreakResult.tsx` lines 51-75. Columns evidence: lines 82-173. Hero/copy evidence: lines 176-194 and condition helpers lines 203-267. | Medium |
| 9 | Playoff History | `playoff_history` -> `playoff_history` mode `history` | `PlayoffHistoryResult` / `PlayoffTeamHistoryResult` | Mapping evidence: `routeToPattern.ts` lines 146-147. Renderer evidence: `PlayoffHistoryResult.tsx` lines 55-82. Hero copy evidence: lines 149-193. History columns evidence: lines 240-271. Detail toggles evidence: lines 418-432. | High |
| 10 | Playoff Round Records | `playoff_round_record` -> `playoff_history` mode `round_record` | `PlayoffHistoryResult` / `PlayoffRoundRecordResult` | Mapping evidence: `routeToPattern.ts` lines 148-149. Renderer evidence: `PlayoffHistoryResult.tsx` lines 85-118. Hero copy evidence: lines 195-218. Columns/metric evidence: lines 273-308 and 566-570. | Medium |
| 11 | Playoff Matchup History | `playoff_matchup_history` -> `playoff_history` mode `matchup` | `PlayoffHistoryResult` / `PlayoffMatchupResult` | Mapping evidence: `routeToPattern.ts` lines 150-151. Renderer evidence: `PlayoffHistoryResult.tsx` lines 120-147. Hero copy evidence: lines 220-238. Winner/result columns evidence: lines 310-383. Winner is read from explicit winner fields, not derived; evidence: lines 581-604. | Medium-High |
| 12 | Comparison Panels | `player_compare`, `team_compare`, `team_matchup_record` -> `comparison` | `ComparisonResult`, `RawDetailToggle` | Mapping evidence: `routeToPattern.ts` lines 152-169. Renderer evidence: `ComparisonResult.tsx` lines 108-157. Hero/edge copy evidence: lines 213-350. Metric table evidence: lines 435-467. Raw details evidence: lines 469-500. | High |
| 13 | Team Record | `team_record` -> `record` mode `team_record` | `RecordResult` / `TeamRecordResult`, `RawDetailToggle` | Mapping evidence: `routeToPattern.ts` lines 170-171. Renderer evidence: `RecordResult.tsx` lines 114-158. Hero/context evidence: lines 453-470 and 584-622. Context does not include opponent-quality filters such as "against playoff teams" unless represented as a direct opponent. | High |
| 14 | Record By Decade | `record_by_decade` -> `record` mode `record_by_decade` | `RecordResult` / `RecordByDecadeResult` | Mapping evidence: `routeToPattern.ts` lines 172-173. Renderer evidence: `RecordResult.tsx` lines 160-188. Columns evidence: lines 324-342. Hero/context evidence: lines 472-489 and 624-644. | Medium |
| 15 | Record By Decade Leaderboard | `record_by_decade_leaderboard` -> `record` mode `record_by_decade_leaderboard` | `RecordResult` / `RecordByDecadeLeaderboardResult` | Mapping evidence: `routeToPattern.ts` lines 174-175. Renderer evidence: `RecordResult.tsx` lines 191-223. Metric selection evidence: lines 546-582. Columns evidence: lines 344-384. | Low-Medium |
| 16 | Matchup By Decade | `matchup_by_decade` -> `record` mode `matchup_by_decade` | `RecordResult` / `MatchupByDecadeResult` | Mapping evidence: `routeToPattern.ts` lines 176-177. Renderer evidence: `RecordResult.tsx` lines 225-250. Columns evidence: lines 386-412. Hero/context evidence: lines 519-544 and 646-649. | Medium |
| 17 | Leaderboard Table | `season_leaders`, `season_team_leaders`, `team_record_leaderboard`, `player_occurrence_leaders`, `team_occurrence_leaders`, `lineup_leaderboard`, `playoff_appearances` -> `leaderboard` | `LeaderboardResult` | Mapping evidence: `routeToPattern.ts` lines 178-207. Renderer evidence: `LeaderboardResult.tsx` lines 184-228. Metric selection evidence: lines 332-388. Hero/context evidence: lines 401-512. | Medium |
| 18 | Top Performances | `top_player_games`, `top_team_games` -> `top_performances` | `TopPerformancesResult` | Mapping evidence: `routeToPattern.ts` lines 99-114. Renderer evidence: `TopPerformancesResult.tsx` lines 97-129. Table columns evidence: lines 132-186. Hero/scope evidence: lines 356-411. | Medium |
| 19 | Rolling Stretch | `player_stretch_leaderboard` -> `rolling_stretch` | `RollingStretchResult` plus backend `player_stretch_leaderboard.build_result` | Mapping evidence: `routeToPattern.ts` lines 184-190. Renderer evidence: `RollingStretchResult.tsx` lines 106-138. League/named-player bodies evidence: lines 140-203. Hero/mode detection evidence: lines 395-458. Backend ranking returns top windows without per-player dedupe; evidence: `player_stretch_leaderboard.py` lines 222-260. | High |

## 5. Cross-cutting implementation map

### Context vs caveats

- Current location(s):
  - API envelope conversion: `src/nbatools/api_handlers.py`.
  - Frontend types: `frontend/src/api/types.ts`.
  - Context chip and caveat rendering: `frontend/src/components/ResultEnvelope.tsx`.
  - No-result notes/caveats display: `frontend/src/components/NoResultDisplay.tsx`.
- Proposed implementation location(s):
  - Frontend-only first pass: split visible sections in `ResultEnvelope` into `Context`, `Interpreted as`, `Notes`, and `Caveats` based on current metadata and top-level arrays.
  - Contract follow-up: add first-class response fields or metadata keys for interpreted context if backend currently sends normal context in `caveats`.
- Evidence:
  - `api_handlers.query_result_to_payload` exposes top-level `notes` and `caveats` directly from result fields, lines 19-39.
  - `types.ts` defines `metadata.applied_filters`, `metadata.notes`, top-level `notes`, and top-level/result `caveats`, but no `context` or `interpreted_as`, lines 95-128 and 136-170.
  - `ResultEnvelope` builds context chips from metadata and `applied_filters`, lines 74-153 and 191-239.
  - `ResultEnvelope` renders `Notes` and `Caveats` in `notices`, lines 240-267.
  - Applied-filter labels already handle opponent quality and thresholds, lines 291-417.
  - `NoResultDisplay` merges notes and caveats into generic Details, lines 138-143 and 181-190.
- Risk:
  - Medium. The frontend can improve display using current metadata, but cannot reliably know whether a caveat string is true caveat or normal context if backend put it in `caveats`.

### Raw/detail toggles

- Current location(s):
  - Primitive: `frontend/src/components/results/primitives/RawDetailToggle.tsx`.
  - Pattern usage: `GameLogResult`, `StreakResult`, `ComparisonResult`, `RecordResult`, `PlayoffHistoryResult`.
- Proposed implementation location(s):
  - Add a label prop and optional duplicate-suppression helper to `RawDetailToggle` or to pattern-level wrappers.
  - Suppress toggles at the pattern level first because pattern components know which columns are already visible in the answer table.
  - Use "Show additional columns" when the rows duplicate the visible answer but include hidden/raw columns.
- Evidence:
  - `RawDetailToggle` props do not include custom labels or duplicate metadata, lines 7-13.
  - Button text is hardcoded to `Show raw table` / `Hide raw table`, line 44.
  - `GameLogResult` renders raw detail for the same `rows` when `rawDetailTitle` exists, lines 150-152.
  - `GameLogResult` renders configured detail sections by key, lines 153-164.
  - `StreakResult` always renders `Full Streak Detail`, line 73.
  - `ComparisonResult` renders one `RawDetailToggle` for every populated section, lines 469-500.
  - `RecordResult` raw toggles are visible for record summary/by-season/matchup summary, lines 151-155, 186, and 248.
  - `PlayoffHistoryResult` maps all populated sections to detail toggles, lines 418-432.
- Risk:
  - Medium-High. Raw toggle changes touch many families and need targeted tests to avoid hiding useful detail tables.

### Shared table sizing

- Current location(s):
  - Answer table primitive: `frontend/src/components/results/primitives/ResultTable.tsx` and `ResultTable.module.css`.
  - Raw table primitive: `frontend/src/components/DataTable.tsx` and `frontend/src/design-system/DataTable.tsx`.
  - Column configs are local in each pattern component.
- Proposed implementation location(s):
  - Add optional column width/min-width metadata to `ResultTableColumn`.
  - Add shared column presets/labels for common stat/date/entity/record columns in a result-display config module.
  - Keep raw `DataTable` generic; prioritize answer-table sizing in `ResultTable`.
- Evidence:
  - `ResultTableColumn` has key/header/alignment/numeric/class/render, but no width/min-width, lines 6-17.
  - `ResultTable` applies highlight and footer rows but no row cap or width metadata, lines 69-144.
  - `ResultTable.module.css` handles horizontal scroll with `overflow-x: auto`, `width: max-content`, `min-width: 100%`, and nowrap cells, lines 1-44.
  - `DataTable` selects visible raw columns and sticky identity columns, lines 71-130, then renders the design-system table at lines 243-274.
  - Pattern-local columns: `GameLogResult` lines 184-273; `LeaderboardResult` lines 236-388; `TopPerformancesResult` lines 132-186; `RollingStretchResult` lines 205-334; `RecordResult` lines 253-412; `PlayoffHistoryResult` lines 240-383; `ComparisonResult` lines 435-467.
- Risk:
  - Medium. Width controls can be centralized, but column choice is intentionally pattern-local today.

### Metric highlighting

- Current location(s):
  - `ResultTable` highlight prop.
  - Pattern-specific metric selection.
- Proposed implementation location(s):
  - Keep `ResultTable.highlightColumnKey`.
  - Centralize metric key selection/labeling for leaderboard-ish families to reduce duplicated heuristics.
- Evidence:
  - `ResultTable` defines `highlightColumnKey` at lines 35-40 and applies highlighted cell CSS at lines 87-99.
  - Highlight CSS is in `ResultTable.module.css`, lines 76-94.
  - `LeaderboardResult` selects metrics via explicit key, metadata hints, query regex, and priority, lines 332-388.
  - `GameLogResult` uses `metricColumn` from explicit metric or metadata stat, lines 425-437.
  - `TopPerformancesResult` highlights its primary metric, lines 120-124.
  - `RollingStretchResult` highlights `stretch_value`, lines 151-155 and 180-184.
  - `RecordResult` highlights `record`, `win_pct`, or selected leaderboard metric, lines 133-145, 177-181, 210-214.
- Risk:
  - Medium. A shared metric metadata map should not change route semantics.

### Row caps/show-all

- Current location(s):
  - No row-cap support in `ResultTable`.
  - Review page has shape-level "show one example per shape", not table row caps.
- Proposed implementation location(s):
  - Add optional row cap/show-all state to `ResultTable` or a wrapper.
  - Add an explicit renderer context prop such as `displayMode="product" | "review"` or `allowRowCaps`.
  - Product `App` can use row caps; `ReviewPage` should pass review mode to show all rows intentionally.
- Evidence:
  - `ResultTable` renders all `rows.map` rows, lines 117-123.
  - `ResultRenderer` props only include `data`, lines 17-19.
  - Product `App` calls `<ResultRenderer data={result} />`, lines 570-576.
  - `ReviewPage` also calls `<ResultRenderer data={result} />`, lines 548-550 and 597-600.
  - Review page's existing toggle slices result examples by shape, not table rows, lines 118-120 and 500-502.
- Risk:
  - Medium. Without an explicit mode prop, a product row cap would also affect review screenshots.

### Footer rows

- Current location(s):
  - `ResultTable` footer API and `GameLogResult.tableFooters`.
- Proposed implementation location(s):
  - Keep footer generation pattern-specific, but move repeated average/total definitions into shared helpers if added to more families.
- Evidence:
  - `ResultTableFooterRow` API is lines 19-28.
  - `ResultTable` renders `<tfoot>` at lines 125-140.
  - Footer styling is lines 96-110 in `ResultTable.module.css`.
  - `GameLogResult` builds footer rows from `summary`, lines 108-112 and 284-362.
- Risk:
  - Low. Existing API is sufficient.

### No-result behavior

- Current location(s):
  - `ResultRenderer`, `NoResultDisplay`, `resultShapes`.
- Proposed implementation location(s):
  - Keep unsupported/error as message no-result.
  - Keep valid-empty/no-data/no-match as guided no-result, but source contextual suggestions from backend `metadata.suggested_queries` first.
  - Add only conservative frontend fallbacks for machine-readable reasons and known metadata fields.
- Evidence:
  - `ResultRenderer` sends empty/no-result responses to `NoResultDisplay`, lines 32-83.
  - `resultShapes.noResultShape` maps `error` to message, `no_match`/`no_data`/missing reason to guided, and other reasons to message, lines 271-282.
  - `NoResultDisplay.stateProfile` maps reason/status to profile, lines 42-124.
  - Static suggestion arrays are lines 29-40 and rendered at lines 192-203.
  - Contextual suggested queries from metadata are rendered at lines 169-180 and extracted at lines 226-230.
- Risk:
  - Low-Medium. Safe if suggestion generation remains backend-driven.

### Comparison edge metadata

- Current location(s):
  - `ComparisonResult`.
- Proposed implementation location(s):
  - Add a local metric metadata map near `LOWER_IS_BETTER` first.
  - Later promote to shared metric metadata if records/leaderboards also need direction semantics.
- Evidence:
  - Only `losses` and `tov_avg` are lower-is-better today, line 46.
  - Metric table and edge column are built at lines 435-467.
  - Leader selection uses lower-is-better only, lines 695-717.
  - `edgeSentence` uses "fewer" only for metrics in `LOWER_IS_BETTER`, lines 301-319.
  - `edgeLabel` always formats a positive delta with `+`, lines 719-723.
  - Subject panels cap displayed stat chips at eight, lines 502-524; comparison metric rows themselves have no show-more groups.
- Risk:
  - Medium. Direction metadata is currently partial and can produce misleading edge text for neutral/contextual metrics.

### Playoff labels/results

- Current location(s):
  - `PlayoffHistoryResult`.
- Proposed implementation location(s):
  - Centralize round/result label mapping in a helper module or at top of `PlayoffHistoryResult` before broader reuse.
  - Add explicit display handling for unavailable round data instead of silently rendering a dash.
  - If backend supplies both game and series records, expose both in the table and hero using deterministic priority.
- Evidence:
  - History/round/matchup renderers are in `PlayoffHistoryResult.tsx`, lines 55-147.
  - Round/result hero builders are lines 149-238.
  - History, round-record, and matchup columns are lines 240-383.
  - `cleanRoundLabel` maps `unknown` and `unknown round` to null, lines 559-564.
  - Winner is displayed only if explicit winner fields exist, lines 328-334 and 581-604.
  - Series result is displayed only from `series_result` or `result`, lines 336-345.
  - Team-prefixed records can show both team records if fields exist, lines 347-362.
- Risk:
  - Medium-High. Some improvements require backend payload clarity about game-level vs series-level grain.

### Rolling stretch dedupe

- Current location(s):
  - Backend row production: `src/nbatools/commands/player_stretch_leaderboard.py`.
  - Natural routing/metadata: `src/nbatools/commands/natural_query.py`, `src/nbatools/query_service.py`.
  - Frontend rendering: `RollingStretchResult`.
- Proposed implementation location(s):
  - Prefer backend or response-shaping dedupe for "which players" intent because the backend owns query intent and can preserve raw best-window rows if needed.
  - Frontend fallback can use `metadata.player_context` for named-player mode and otherwise display the supplied rows as "best windows".
- Evidence:
  - Natural query routes stretch requests to `player_stretch_leaderboard` with player/team/opponent/window/metric/limit kwargs, `natural_query.py` lines 931-961.
  - Query metadata includes `window_size` and `stretch_metric`, but no display mode, `query_service.py` lines 395-430 and 1256-1280.
  - Backend computes rolling windows and then sorts/head-limits windows directly, `player_stretch_leaderboard.py` lines 216-260.
  - Frontend distinguishes named-player mode only by `metadata.player_context`, `RollingStretchResult.tsx` lines 106-138 and 446-458.
  - Frontend has separate league and named-player bodies but no dedupe logic, lines 140-203.
- Risk:
  - High. Frontend-only dedupe risks hiding legitimate "best windows" results unless the response says the query asked "which players".

## 6. Fixture and validation map

All minimum fixture indexes from the spec are present in the current extracted parser-example set. The set contains 402 fixtures. Fixture IDs below are 1-based indexes in the extracted order from `src/nbatools/parser_examples.extract_cases()`.

| Fixture ID | Query/family | How to run/check | Notes |
|---:|---|---|---|
| 1 | `Who leads the NBA in points per game this season?` / Family 17 Leaderboard Table | `/review` or run query through `/query`; also covered by `LeaderboardResult` tests | Case ID `S2_2_1_01`. |
| 11 | `Who scored the most points last night?` / Family 3 Guided No Result | `/review` or `/query` | Case ID `S2_2_2_01`. |
| 14 | `What team has played the best defense recently?` / Family 2 Message No Result | `/review` or `/query` | Case ID `S2_2_2_04`; expected category is `unsupported_expected`. |
| 31 | `What were the biggest scoring games this season?` / Family 18 Top Performances | `/review` or `/query` | Case ID `S2_2_4_01`. |
| 36 | `Which players have the hottest 3-game scoring stretch this year?` / Family 19 Rolling Stretch | `/review` or `/query`; backend-specific tests in `tests/test_player_stretch_leaderboard.py` | Case ID `S2_2_4_06`. |
| 44 | `How has Jayson Tatum played against good teams this season?` / Family 1 or 4 depending game-log rows | `/review` or `/query` | Case ID `S2_2_5_04`. |
| 45 | `What is the Celtics' record against playoff teams?` / Family 13 Team Record | `/review` or `/query` | Case ID `S2_2_5_05`; important for opponent-quality context. |
| 51 | `How do the Suns perform when Devin Booker didn't play?` / Split/on-off related evidence | `/review` or `/query` | Case ID `S2_2_6_01`; this is outside the 19-family spec table but appears in source review logs. |
| 71 | `How often has Nikola Jokić recorded a triple-double this season?` / occurrence/count family | `/review` or `/query` | Case ID `S2_2_8_01`; reviewed output may map through leaderboard/no-result depending data. |
| 76 | `How often have the Lakers held opponents under 100 points this year?` / occurrence/count family | `/review` or `/query` | Case ID `S2_2_8_06`. |
| 201 | `Jokic 5 straight games with 20+ points` / Family 8 Streak Table | `/review` or `/query` | Case ID `S4_4_1_01`. |
| 229 | `Heat vs Knicks playoff history` / Family 11 Playoff Matchup History | `/review` or `/query` | Case ID `S4_4_4_02`. |
| 234 | `best finals record since 1980` / Family 10 Playoff Round Records | `/review` or `/query` | Case ID `S4_4_4_07`. |
| 236 | `Warriors record by decade` / Family 14 Record By Decade | `/review` or `/query` | Case ID `S4_4_4_09`. |
| 237 | `winningest team of the 2010s` / Family 15 Record By Decade Leaderboard | `/review` or `/query` | Case ID `S4_4_4_10`. |
| 238 | `Lakers vs Celtics by decade` / Family 16 Matchup By Decade | `/review` or `/query` | Case ID `S4_4_4_11`. |
| 239 | `Jokic vs Embiid recent form` / Family 12 Comparison Panels | `/review` or `/query` | Case ID `S4_4_5_01`. |
| 247 | `Luka last 5` / Family 4 Entity Summary + Recent Games | `/review` or `/query` | Case ID `S5_5_1_01`; expected category is stress/failure-clean-ok. |

Fixture/test/screenshot evidence:

- Parser examples source: `docs/architecture/parser/examples.md` has playoff/history/record/comparison examples at lines 423-463 and stress examples including `Luka last 5` at lines 467-485.
- Extraction source: `src/nbatools/parser_examples.py` reads `docs/architecture/parser/examples.md`, lines 8-10; `Case` fields are lines 12-23; extraction across sections 2-8 is lines 239-418.
- Dev fixture endpoint: `src/nbatools/api_handlers.py` returns `source_path` and `case_id`/`query` fixtures, lines 61-72. `src/nbatools/api.py` exposes `/api/dev/fixtures`, lines 208-211.
- Review page fixture load: `frontend/src/ReviewPage.tsx` lines 129-152.
- Review page display/capture: visible examples at lines 498-552; hidden screenshot capture stage at lines 560-606.
- Screenshot generation: `frontend/src/lib/reviewScreenshots.ts` uses `html-to-image` and `JSZip`, lines 1-2; waits for fonts/images, lines 43-65; captures PNGs and zips them, lines 79-110.
- Frontend scripts: `frontend/package.json` lines 6-13.
- Make targets: `Makefile` lines 15-45 for broad tests, 53-78 for domain targets, 80-93 for smoke and parser sweep targets.
- Parser examples sweep: `tools/parser_examples_full_sweep.py` writes results CSV, report, manifest, and raw JSON artifacts; evidence lines 398-403 and 460-485.

Relevant validation commands:

```bash
cd frontend && npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts
cd frontend && npm run build
make test-api
make test-smoke-queries
make parser-examples-sweep
```

No dedicated "regenerate only targeted fixture IDs" command was found. Lowest-risk targeted check today is manual query execution for the listed query strings through `/review`, `/query`, or the CLI. The full fixture audit is `make parser-examples-sweep`.

## 7. Recommended implementation waves

1. Wave 1A - shared envelope semantics.
   - Implement Context / Interpreted as / Caveats separation in `ResultEnvelope`.
   - Keep caveats for true warnings only; render `metadata.applied_filters` and known context as context.
   - Add/adjust `ResultEnvelope` and no-result tests.

2. Wave 1B - raw/detail toggle substrate.
   - Add a custom label prop to `RawDetailToggle`.
   - Add a small duplicate-detail policy at pattern level.
   - First apply to `GameLogResult`, then `RecordResult`, `ComparisonResult`, `PlayoffHistoryResult`, and `StreakResult`.

3. Wave 1C - table substrate.
   - Add optional column width/min-width support to `ResultTableColumn`.
   - Add row-cap/show-all API with an explicit product vs review mode.
   - Keep `ReviewPage` uncapped.

4. Wave 2 - leaderboard-ish families.
   - Apply table sizing, metric highlighting consistency, and context improvements to `LeaderboardResult`, `TopPerformancesResult`, `RecordByDecadeLeaderboardResult`, `PlayoffRoundRecordResult`, and `RollingStretchResult`.
   - Do not do rolling-stretch dedupe frontend-only unless metadata explicitly marks "which players".

5. Wave 3 - game logs and entity summaries.
   - Improve player/team game-log labels, duplicate raw toggles, footer totals/averages, and hero context.
   - Ensure opponent-quality filters read correctly as context, especially Families 1, 4, 5, 6, 7, and 13.

6. Wave 4 - comparison, records, and playoff semantics.
   - Add comparison metric direction metadata.
   - Centralize playoff round/result labels.
   - Clarify game record vs series record display when both are available.

7. Wave 5 - no-result polish.
   - Keep unsupported as Message No Result.
   - Keep valid-empty/no-match as Guided No Result.
   - Use backend `metadata.suggested_queries` before static fallback chips.

## 8. Open questions / blockers

- Row caps: What product default row cap should apply per family, and should it vary by table type?
- Review mode: Should the renderer receive a general `displayMode` prop or a narrower `disableRowCaps` prop?
- Rolling stretches: Should "which players have the hottest stretch" dedupe to one row per player, while "best stretches/windows" keeps multiple windows per player? Backend metadata should make this explicit.
- Playoffs: When both game record and series record exist, which value belongs in the hero sentence, and should both always be columns?
- Comparison metrics: Which metrics are lower-is-better, higher-is-better, and neutral for edge text? Current metadata only covers `losses` and `tov_avg`.

No open question blocks the first shared-display wave.

## 9. Suggested first execution prompt scope

Start with the smallest high-leverage implementation wave:

```txt
Implement shared result-display substrate changes only.

Scope:
- In ResultEnvelope, separate normal context/interpreted filters from caveats using existing metadata and applied_filters. Do not change backend contracts yet.
- In RawDetailToggle, add configurable collapsed/expanded button labels.
- In GameLogResult only, use the new toggle label to rename duplicate same-row raw details to "Show additional columns" and suppress the toggle if it adds no columns beyond the visible answer table.
- Add focused frontend tests for ResultEnvelope, RawDetailToggle behavior through GameLogResult, and existing no-result behavior.
- Rebuild frontend with cd frontend && npm run build.

Out of scope:
- Rolling-stretch dedupe.
- Playoff record semantics.
- Comparison metric direction metadata.
- Global row caps.
```
