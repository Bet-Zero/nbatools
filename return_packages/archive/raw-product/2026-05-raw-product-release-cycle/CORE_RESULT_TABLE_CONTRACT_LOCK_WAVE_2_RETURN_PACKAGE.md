# Core Result/Table Contract Lock — Wave 2 Return Package

## 1. Executive summary

- What was locked: Wave 2 route-to-pattern mappings, result-shape classifications, frontend section keys, backend structured-result section names, key visible table headers, and Wave 2 fallback guards.
- Routes covered: `player_split_summary`, `team_split_summary`, `player_on_off`, `player_streak_finder`, `team_streak_finder`, `player_compare`, `team_compare`, `team_matchup_record`, `playoff_history`, `playoff_appearances`, `playoff_matchup_history`, `playoff_round_record`, `record_by_decade`, `record_by_decade_leaderboard`, `matchup_by_decade`, `lineup_summary`, `lineup_leaderboard`.
- Table patterns covered: Split Comparison, On/Off Split, Streak Table, Comparison Metrics, Playoff History, Playoff Round Record, Playoff Matchup History, Record By Decade, Record By Decade Leaderboard, Matchup By Decade, Lineup Summary, Lineup Leaderboard.
- Tests added/updated: frontend route mapping, shape classification, section contracts, table/header smoke tests; backend structured-result section-key tests.
- Docs added/updated: `docs/reference/result_contracts/core_result_table_contracts.md`.
- Any production code changed? yes. Narrow frontend display changes only: `lineup_summary` now maps to `entity_summary`, `RouteName` includes lineup routes, and `EntitySummaryResult` renders lineup-aware hero text.
- Remaining risks: several supporting columns remain inferred from row keys; `player_on_off` uses `summary` rows rather than `split_comparison`; `record_by_decade` keeps decade rows in `by_season`; `playoff_appearances` has an unhandled direct backend single-team summary variant; lineup summary still uses a generic hero rather than a dedicated lineup pattern.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/reference/result_contracts/core_result_table_contracts.md` | Updated reference doc | Added Wave 2 shared table behavior, route contracts, current weak contracts, examples, and fallback notes. |
| `frontend/src/api/types.ts` | Production type update | Added lineup routes to the typed route union. |
| `frontend/src/components/results/config/routeToPattern.ts` | Production mapping update | Mapped `lineup_summary` to `entity_summary` so it no longer falls through to `fallback_table`. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | Production rendering update | Added lineup-aware hero sentence support for `lineup_summary` rows. |
| `frontend/src/test/routeToPattern.test.ts` | Expanded tests | Added Wave 2 exact route-to-pattern expectations and non-fallback guard. |
| `frontend/src/test/resultShapes.test.ts` | Expanded tests | Added representative Wave 2 result-shape classification fixtures and changed the fallback fixture to a truly unmapped route. |
| `frontend/src/test/wave2SectionContracts.test.ts` | Added tests | Protects Wave 2 frontend-consumed section names and shapes. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Added tests | Protects key visible headers/labels for Wave 2 table families. |
| `tests/test_core_result_table_contracts.py` | Expanded tests | Added backend structured-result section serialization coverage for Wave 2 families. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_2_RETURN_PACKAGE.md` | Added return package | Records implementation, coverage, validation, and deferred decisions. |

## 3. Route contract coverage

| Route | PatternConfig | Result shape | Sections protected | Table pattern | Test coverage |
|---|---|---|---|---|---|
| `player_split_summary` | `split(subject=player)` | `split_table` | `summary`, `split_comparison` | Split Comparison | route, shape, section, table, backend section tests |
| `team_split_summary` | `split(subject=team)` | `split_table` | `summary`, `split_comparison` | Split Comparison | route, shape, section, backend section tests |
| `player_on_off` | `split(sectionKey=summary, bucketKey=presence_state, splitLabelOverride=On/Off)` | `on_off_split` | `summary` | On/Off Split | route, shape, section, table, backend section tests |
| `player_streak_finder` | `streak(sectionKey=streak)` | `streak_table` | `streak` | Streak Table | route, shape, section, table, backend section tests |
| `team_streak_finder` | `streak(sectionKey=streak)` | `streak_table` | `streak` | Streak Table | route, shape, section, table, backend section tests |
| `player_compare` | `comparison(subject=player)` | `comparison` | `summary`, `comparison` | Comparison Metrics | route, shape, section, table, backend section tests |
| `team_compare` | `comparison(subject=team)` | `comparison` | `summary`, `comparison` | Comparison Metrics | route, shape, section, backend section tests |
| `team_matchup_record` | `comparison(subject=team, headToHead=true)` | `comparison` | `summary`, `comparison` | Comparison Metrics | route, shape, section, table, backend section tests |
| `playoff_history` | `playoff_history(mode=history)` | `playoff_history` | `summary`, `by_season` | Playoff History | route, shape, section, table, backend section tests |
| `playoff_appearances` | `leaderboard(sectionKey=leaderboard, metricKey=appearances)` | `leaderboard_table` | `leaderboard` | Leaderboard | route, shape, section, backend section tests |
| `playoff_matchup_history` | `playoff_history(mode=matchup)` | `playoff_matchup_history` | `summary`, `comparison` | Playoff Matchup History | route, shape, section, table, backend section tests |
| `playoff_round_record` | `playoff_history(mode=round_record)` | `playoff_round_record` | `leaderboard` | Playoff Round Record | route, shape, section, table, backend section tests |
| `record_by_decade` | `record(mode=record_by_decade)` | `record_by_decade` | `summary`, `by_season` | Record By Decade | route, shape, section, table, backend section tests |
| `record_by_decade_leaderboard` | `record(mode=record_by_decade_leaderboard)` | `record_by_decade_leaderboard` | `leaderboard` | Record By Decade Leaderboard | route, shape, section, table, backend section tests |
| `matchup_by_decade` | `record(mode=matchup_by_decade)` | `matchup_by_decade` | `summary`, `comparison` | Matchup By Decade | route, shape, section, table, backend section tests |
| `lineup_summary` | `entity_summary(sectionKey=summary)` | `entity_summary` | `summary` | Lineup Summary | route, shape, section, table, backend section tests |
| `lineup_leaderboard` | `leaderboard(sectionKey=leaderboard, metricKey=net_rating)` | `leaderboard_table` | `leaderboard` | Lineup Leaderboard | route, shape, section, table, backend section tests |

## 4. Table contract coverage

| Table pattern | Headers/columns protected | Row behavior protected | Gaps/deferred decisions |
|---|---|---|---|
| Split Comparison | `Split`, `GP`, `Record`, `PTS`, `REB`, `AST`, `MIN`, `3PM`, `TS%`, `eFG%`, `+/-`. | Bucket labels and edge chip behavior. | Per-route split columns remain inferred from row keys. |
| On/Off Split | `Split`, `GP`, `ORtg`, `DRtg`, `Net`, `MIN`, `+/-`. | `presence_state` bucket labels and `On/Off Detail`. | Whether on/off should move to `split_comparison` is deferred. |
| Streak Table | `#`, `Player`/`Team`, `Streak`, `Length`, conditional `Status`, `Start`, `End`, `Games`, `Record`, `PTS`, `AST`, `+/-`. | Active status renders; completed-only single-status samples omit `Status`. | Longest/current visual hierarchy unchanged. |
| Comparison Metrics | `Metric`, compared entity columns, `Edge / Difference`. | Subject panels, head-to-head participant labels, metric edge behavior. | Metric grouping remains flat with a show-more toggle. |
| Playoff History | `Season`, `Round Reached`, `Record`, `Result`, `Opponent`, `Win Pct`, `Games`. | Season-row display and postseason detail behavior. | History hierarchy and round labeling remain current behavior. |
| Playoff Round Record | `#`, `Team`, `Round`, `Record`, `Games`, `Win Pct`, `Seasons`. | Selected metric highlight behavior. | Row cap stays backend-limited only. |
| Playoff Matchup History | `Season`, `Round`, `Winner`, `Series Result`, team record columns, `Games`. | Team-abbreviation record columns and series result rows. | No stronger visual grouping for series rows yet. |
| Record By Decade | `Decade`, `Seasons`, `W-L`, `Win %`, `Games`, `Season Type`. | Decade rows sourced from `by_season`; summary detail toggle. | Section naming remains backward-compatible but semantically weak. |
| Record By Decade Leaderboard | `#`, `Team`, `Decade`, `Win %`, `W-L`, `Games`, `Seasons`, `Season Type`. | Primary metric selection/highlight. | Supporting columns remain inferred. |
| Matchup By Decade | `Decade`, `Games`, `<team> W-L`, `<team> Win %`. | Team-prefix record columns and summary detail toggle. | Prefix ordering depends on metadata/row keys. |
| Lineup Summary | Lineup label and rating stats in the entity-summary hero. | `lineup` label no longer falls back to generic raw table. | Dedicated lineup summary pattern/table remains deferred. |
| Lineup Leaderboard | `#`, `Name`, `Net`, `TM`, `Minutes`, `ORtg`, `DRtg`. | Lineup label as entity and `net_rating` primary metric. | Supporting columns remain inferred. |

## 5. Fallback guard result

- Guaranteed not to `fallback_table`: all 17 Wave 2 routes listed above.
- Any route still falling back: no Wave 2 route falls back after this wave.
- Whether fallback is intentional or needs later work: fallback remains intentional for truly unmapped routes only. `lineup_summary` was moved out of fallback because the Wave 2 contract requires entity-summary rendering.

## 6. Validation

| Command | Result |
|---|---|
| `npm test -- routeToPattern.test.ts resultShapes.test.ts wave1SectionContracts.test.ts wave1TableContracts.test.tsx wave2SectionContracts.test.ts wave2TableContracts.test.tsx` from `frontend/` | Passed: 6 files, 49 tests. |
| `make PYTEST=.venv/bin/pytest test-output` | Passed: 332 tests. |
| `npm run build` from `frontend/` | Passed; Vite emitted the existing large-chunk warning. |
| `git diff --check` | Passed. |

## 7. Deferred decisions

- Whether columns should change: deferred; current dynamic columns are documented and smoke-tested.
- Whether row caps should change: deferred; Wave 2 frontend tables do not add new caps and backend limits remain route-specific.
- Whether detail drawers should remain: deferred; current opt-in/detail-only behavior is documented.
- Whether table filters should be added: deferred; no client-side filtering added.
- Whether comparison metrics should be grouped: deferred; the current flat metric table plus show-more behavior is locked only as current behavior.
- Whether playoff/history rows need stronger visual hierarchy: deferred; current season/round/series rows are documented.
- Whether routeToPattern should later become a registry: deferred; this wave intentionally avoided a registry refactor.
- Whether `player_on_off` should use `SplitSummaryResult.split_comparison`: deferred.
- Whether `lineup_summary` needs a dedicated pattern instead of generic entity summary: deferred.
- Whether `playoff_appearances` should support the backend's single-team summary variant in the UI: deferred.

## 8. Recommended next phase

Next smallest useful phase: resolve the documented weak contracts that now have guardrails, starting with product decisions for `lineup_summary`, `player_on_off` section shape, and the `playoff_appearances` single-team summary variant. After those decisions, either add narrow production changes with matching contract tests or explicitly mark the variants out of UI scope.
