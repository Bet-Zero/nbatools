# Core Result/Table Contract Lock — Wave 1 Return Package

## 1. Executive summary

- What was locked: Wave 1 route-to-pattern mappings, result-shape classification, frontend section keys, backend structured-result section names, and key visible table headers for core result patterns.
- Routes covered: `player_game_summary`, `player_game_finder`, `game_finder`, `game_summary`, `team_record`, `season_leaders`, `season_team_leaders`, `top_player_games`, `top_team_games`, `player_occurrence_leaders`, `team_occurrence_leaders`, `player_stretch_leaderboard`.
- Table patterns covered: Entity Summary, Player Game Log, Team Game Log, Game Summary Log, Team Record, Leaderboard, Top Performances, Rolling Stretch.
- Tests added/updated: frontend route mapping, shape classification, section contracts, table header smoke tests; backend structured result section-key tests.
- Docs added/updated: `docs/reference/result_contracts/core_result_table_contracts.md`, `docs/index.md`.
- Any production code changed? no.
- Remaining risks: leaderboard supporting columns are still inferred dynamically; row caps are split between backend limits and frontend product-mode caps; detail drawers remain route-configured; `routeToPattern` is still a switch; fallback remains available outside Wave 1.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/reference/result_contracts/core_result_table_contracts.md` | Added doc | Reference contract for Wave 1 route/result/table behavior. |
| `docs/index.md` | Updated doc index | Links the new reference doc. |
| `frontend/src/test/routeToPattern.test.ts` | Expanded tests | Explicit Wave 1 route-to-pattern coverage and non-fallback guard. |
| `frontend/src/test/resultShapes.test.ts` | Expanded tests | Representative Wave 1 shape classification coverage. |
| `frontend/src/test/wave1SectionContracts.test.ts` | Added tests | Protects frontend-consumed section names and conditional stacks. |
| `frontend/src/test/wave1TableContracts.test.tsx` | Added tests | Protects key visible headers for Wave 1 table families. |
| `tests/test_core_result_table_contracts.py` | Added tests | Protects backend structured-result section serialization for Wave 1 families. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_1_RETURN_PACKAGE.md` | Added return package | Records implementation, coverage, validation, and deferred decisions. |

## 3. Route contract coverage

| Route | PatternConfig | Result shape | Sections protected | Table pattern | Test coverage |
|---|---|---|---|---|---|
| `player_game_summary` | `entity_summary`; conditionally `entity_summary + game_log` | `entity_summary`, `entity_summary_with_gamelog` | `summary`; optional `game_log`, `by_season` | Entity Summary, Player Game Log | route, shape, section, table, backend section tests |
| `player_game_finder` | `game_log(sectionKey=finder, mode=player)` | `game_log_player_table` | `finder` | Player Game Log | route, shape, section, backend section tests |
| `game_finder` | `game_log(sectionKey=finder, mode=team)` | `game_log_team_table` | `finder` | Team Game Log | route, shape, section, table, backend section tests |
| `game_summary` | `game_log(sectionKey=game_log, summaryKey=summary, mode=team, detailSectionKeys=[top_performers])` | `game_log_team_detail` | `game_log`; optional `summary`, `top_performers`, `by_season` | Game Summary Log | route, shape, section, backend section tests |
| `team_record` | `record(mode=team_record)`; conditionally stacked `game_log` | `team_record` | `summary`; optional `by_season`, `game_log` | Team Record, optional Team Game Log | route, shape, section, table, backend section tests |
| `season_leaders` | `leaderboard(sectionKey=leaderboard)` | `leaderboard_table` | `leaderboard` | Leaderboard | route, shape, section, table, backend section tests |
| `season_team_leaders` | `leaderboard(sectionKey=leaderboard)` | `leaderboard_table` | `leaderboard` | Leaderboard | route, section, backend section tests |
| `top_player_games` | `top_performances(sectionKey=leaderboard, subject=player)` | `top_performances` | `leaderboard` | Top Performances | route, shape, section, table, backend section tests |
| `top_team_games` | `top_performances(sectionKey=leaderboard, subject=team)` | `top_performances` | `leaderboard` | Top Performances | route, section, table, backend section tests |
| `player_occurrence_leaders` | `leaderboard(sectionKey=leaderboard)` | `leaderboard_table` | `leaderboard` | Leaderboard | route, section, backend section tests |
| `team_occurrence_leaders` | `leaderboard(sectionKey=leaderboard)` | `leaderboard_table` | `leaderboard` | Leaderboard | route, section, backend section tests |
| `player_stretch_leaderboard` | `rolling_stretch(sectionKey=leaderboard)` | `rolling_stretch` | `leaderboard`; optional named-player game-log detail sections | Rolling Stretch | route, shape, section, table, backend section tests |

## 4. Table contract coverage

| Table pattern | Headers/columns protected | Row behavior protected | Gaps/deferred decisions |
|---|---|---|---|
| Entity Summary | Summary route stack and shape classification; by-season documented. | Summary-only vs summary-plus-game-log behavior. | No new hero visual or copy decisions. |
| Player Game Log | `Date`, `TM`, `Opp`, `Score`, `W/L`, `MIN`, `PTS`, `REB`, `AST`, `FG`, `3P`, `FT`, `STL`, `BLK`, `TOV`, `+/-`, `TS%`, `eFG%`. | Footer rows `Average` and `Total` when summary exists. | Row cap/pagination unchanged. |
| Team Game Log | `Date`, `Team`, `Opp`, `Score`, `W/L`, `PTS`, `Opp PTS`, `Margin`, `REB`, `AST`, `3PM`, `FG`, `3P`, `FT`, `TOV`, `STL`, `BLK`, `ORB`, `DRB`. | Team mode and finder/game-log section use. | Row cap/pagination unchanged. |
| Team Record | `Team`, `W-L`, `Games`, `Win %`, `PPG`, `+/-`, `REB`, `AST`, `3PM`, `Season Type`, `Season`, `Opp PPG`, `Net`. | Summary-only vs optional stacked game-log behavior. | Whether record columns should be configurable is deferred. |
| Leaderboard | `#`, entity label, primary metric. | Primary metric selection smoke-tested. | Dynamic supporting columns remain current behavior -- needs product decision. |
| Top Performances | `Rank`, `Player`/`Team`, `Date`, `Opp`, `Result`, `Score`, primary metric. | Player and team subjects both smoke-tested. | Supporting stat count/order unchanged. |
| Rolling Stretch | `Rank`, `Player`, `Window`, primary stretch metric, `Start`, `End`, `Season`. | Rolling-stretch section and primary metric behavior smoke-tested. | Named-player secondary game-log detail behavior documented, not exhaustively tested. |

## 5. Fallback guard result

- Guaranteed not to `fallback_table`: all 12 Wave 1 routes listed above.
- Any route still falling back: not checked globally in this wave. Existing fallback behavior remains for non-Wave 1 or unmapped routes.
- Whether fallback is intentional or needs later work: intentional as existing behavior for this wave, but still a product risk for future routes.

## 6. Validation

| Command | Result |
|---|---|
| `npm test -- routeToPattern.test.ts resultShapes.test.ts wave1SectionContracts.test.ts wave1TableContracts.test.tsx` from `frontend/` | Passed: 4 files, 29 tests. |
| `make test-output` | Failed: `pytest` not found on PATH in this shell. |
| `make PYTEST=.venv/bin/pytest test-output` | Passed: 315 tests. |
| `npm run build` from `frontend/` | Passed; Vite emitted the existing large-chunk warning. No tracked dist diff resulted. |
| `git diff --check` | Passed. |

## 7. Deferred decisions

- Whether columns should change: deferred; current visible columns are documented and smoke-tested.
- Whether row caps should change: deferred; current frontend 12-row product cap for game logs is documented.
- Whether detail drawers should remain: deferred; current opt-in raw/detail behavior is documented.
- Whether table filters should be added: deferred; no client-side filtering added.
- Whether `routeToPattern` should later become a registry: deferred; this wave intentionally avoided a registry refactor.

## 8. Recommended next phase

Next smallest useful phase: Wave 2 should lock the next route family outside this core set, starting with split/streak/comparison/playoff patterns, and add the same three layers of protection: route-to-pattern non-fallback tests, result-shape tests, and minimal table/header smoke tests.
