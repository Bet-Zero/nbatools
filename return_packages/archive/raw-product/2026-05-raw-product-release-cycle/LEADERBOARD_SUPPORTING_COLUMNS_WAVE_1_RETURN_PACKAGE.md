# Leaderboard Supporting Columns — Wave 1 Return Package

## 1. Executive summary

- What changed: added route-specific frontend column selection for configured
  generic `LeaderboardResult` routes while preserving dynamic fallback behavior
  for unknown leaderboard payloads.
- Routes/families addressed: `season_leaders`, `season_team_leaders`,
  `team_record_leaderboard`, `player_occurrence_leaders`,
  `team_occurrence_leaders`, ranked `playoff_appearances`, and
  `lineup_leaderboard`.
- Production code changed? yes, frontend only.
- Tests added/updated: route mapping, shape classification, Wave 1 table
  contracts, Wave 2 table contracts, and broader result-renderer fixtures.
- Docs updated: `docs/reference/result_contracts/core_result_table_contracts.md`.
- Main product improvement: scoped leaderboard routes now show predictable,
  useful support context and suppress raw IDs instead of exposing whatever row
  keys happen to be present.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Production update | Adds route-aware column configs, source-backed lineup label handling, W-L display, and ID suppression. |
| `frontend/src/test/routeToPattern.test.ts` | Test update | Confirms `team_record_leaderboard` remains mapped to the generic leaderboard pattern. |
| `frontend/src/test/resultShapes.test.ts` | Test update | Uses backend-like lineup leaderboard keys while preserving `leaderboard_table` classification. |
| `frontend/src/test/wave1TableContracts.test.tsx` | Test update | Locks scoped season, team, record, and occurrence leaderboard columns. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Test update | Locks ranked playoff appearances and backend-like lineup leaderboard columns. |
| `frontend/src/test/ResultRenderer.test.tsx` | Test update | Updates integration-level expectations for route-specific leaderboard columns and hidden raw IDs. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Doc update | Documents locked route-specific leaderboard columns, hidden fields, and deferred enrichment ideas. |
| `return_packages/raw-product/LEADERBOARD_SUPPORTING_COLUMNS_WAVE_1_RETURN_PACKAGE.md` | New return package | Records implementation, validation, and next-phase recommendation. |

## 3. Leaderboard behavior after implementation

| Route/family | Primary metric | Locked supporting columns | Hidden fields | Renderer |
|---|---|---|---|---|
| `season_leaders` | Metadata/query/row metric, usually player stat | `Team`, `GP`, shooting makes/attempts when present, `Season`, `Season Type` | `player_id`, unconfigured support keys | `LeaderboardResult` |
| `season_team_leaders` | Metadata/query/row metric, usually team stat | optional `W-L`/`Win %`, `GP`, shooting makes/attempts when present, `Season`, `Season Type` | `team_id`, unconfigured support keys | `LeaderboardResult` |
| `team_record_leaderboard` | `win_pct`, `wins`, `losses`, or `games_played` | `W-L`, `Win %`, `Games`, `Season`/`Seasons`, `Season Type` | `team_id`, separate raw wins/losses columns | `LeaderboardResult` |
| `player_occurrence_leaders` | Dynamic occurrence-count field | `Team`, `GP`, `Season`, `Season Type` | `player_id`; no invented rate/frequency | `LeaderboardResult` |
| `team_occurrence_leaders` | Dynamic occurrence-count field | `GP`, `Season`, `Season Type`; team abbreviation works as identity | `team_id`; no invented rate/frequency | `LeaderboardResult` |
| ranked `playoff_appearances` | `appearances` | `Round`, `Seasons` or `Season` | IDs and unrelated postseason metadata | `LeaderboardResult` |
| `lineup_leaderboard` | `net_rating` by route config unless another metric is supplied | `Team`, primary metric, `Minutes`, `ORtg`, `DRtg`, `Pace`, `TS%` | `lineup_id`, `player_ids`, raw `player_names`, `unit_size`, `minute_minimum` | `LeaderboardResult` |

## 4. Test coverage

| Route/family | Fixture type | Assertions added |
|---|---|---|
| `season_leaders` | Standard scoring and shooting rows | `Team`, `GP`, season context, `FGM`/`FGA`, and hidden `player_id`. |
| `season_team_leaders` | Rating and record-ish rows | `ORtg`, `GP`, season context, `Wins`, `W-L`, `Win %`, and hidden `team_id`. |
| `team_record_leaderboard` | Record row | `W-L`, `Win %`, `Games`, season context, and hidden `team_id`. |
| `player_occurrence_leaders` | Special event and threshold event rows | Dynamic count column, `Team`, `GP`, and season context. |
| `team_occurrence_leaders` | Team-abbreviation-only row | Clean team identity, dynamic count, `GP`, and no raw team-id column. |
| ranked `playoff_appearances` | League-wide ranked row | `Appearances`, `Round`, `Seasons`, and hidden `team_id`; single-team variant still renders playoff history. |
| `lineup_leaderboard` | Backend-like lineup rows | `Lineup`, `Team`, ratings, pace, TS%, readable labels from `lineup_name`, pipe-delimited `player_names`, and array-like `player_names`; hidden lineup/player IDs/raw pipe string. |

## 5. Specialized routes confirmed unchanged

- `player_stretch_leaderboard` still maps to and renders through
  `RollingStretchResult`.
- `record_by_decade_leaderboard` still maps to and renders through
  `RecordResult`.
- `top_player_games` still maps to and renders through `TopPerformancesResult`.
- `top_team_games` still maps to and renders through `TopPerformancesResult`.

## 6. Validation

| Command | Result |
|---|---|
| `npm test -- routeToPattern.test.ts resultShapes.test.ts wave1TableContracts.test.tsx wave2TableContracts.test.tsx ResultRenderer.test.tsx` from `frontend/` | Passed: 5 files, 96 tests. |
| `npm run build` from `frontend/` | Passed; Vite emitted the existing large-chunk warning. |
| `make PYTEST=.venv/bin/pytest test-output` | Passed: 332 tests. |
| `git diff --check` | Passed. |

## 7. Remaining risks / deferred decisions

- Backend metadata-driven columns deferred.
- Occurrence rate/frequency deferred.
- First/last playoff appearance deferred.
- MPG and richer secondary stats deferred.
- Team PPG/Opp PPG for record leaderboards deferred.
- Player top-game score fields deferred.
- Mobile density manual QA still needed, especially for lineup and season
  leaderboards.

## 8. Recommended next phase

Next smallest useful phase: perform mobile/desktop visual QA for the new
leaderboard column density, then do a narrow label/enrichment preflight for
occurrence-event labels and optional backend metadata that could improve
leaderboard column labels without changing route semantics.
