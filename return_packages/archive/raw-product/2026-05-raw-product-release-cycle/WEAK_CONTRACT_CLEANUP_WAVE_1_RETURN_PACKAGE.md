# Weak Contract Cleanup — Wave 1 Return Package

## 1. Executive summary

- What changed: added source-backed lineup labels, added single-team playoff appearances rendering, and recorded `player_on_off` as accepted current behavior.
- Targets addressed: `lineup_summary`, `player_on_off`, `playoff_appearances`.
- Production code changed? yes, frontend only.
- Tests added/updated: route mapping, result shape, Wave 2 section contract, and Wave 2 table/rendering tests.
- Docs updated: `docs/reference/result_contracts/core_result_table_contracts.md`.
- Main product risk fixed: successful single-team `playoff_appearances` results no longer map to a leaderboard-only renderer that can show no visible content.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `frontend/src/components/results/config/routeToPattern.ts` | Production update | Branches `playoff_appearances` by available sections while preserving leaderboard behavior. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | Production update | Resolves lineup labels from actual backend keys and metadata-backed lineup members. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | Production update | Adds appearances mode for single-team playoff appearance summaries. |
| `frontend/src/components/results/resultShapes.ts` | Production update | Classifies appearances mode as the existing playoff-history shape. |
| `frontend/src/test/routeToPattern.test.ts` | Test update | Covers leaderboard and single-team `playoff_appearances` route branching. |
| `frontend/src/test/resultShapes.test.ts` | Test update | Covers both `playoff_appearances` shapes and actual lineup summary backend keys. |
| `frontend/src/test/wave2SectionContracts.test.ts` | Test update | Protects single-team `playoff_appearances` sections and source-backed lineup summary rows. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Test update | Protects rendered single-team appearances hero/table and lineup labels from actual row keys. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Doc update | Documents accepted `player_on_off`, lineup label keys, and the two `playoff_appearances` variants. |
| `return_packages/raw-product/WEAK_CONTRACT_CLEANUP_WAVE_1_RETURN_PACKAGE.md` | New return package | Records implementation, validation, and remaining decisions. |

## 3. Target outcomes

### lineup_summary

- Previous behavior: `EntitySummaryResult` recognized synthetic `lineup`, `lineup_members`, and `members`, but not actual source-backed `lineup_name` or pipe-delimited `player_names`.
- New behavior: `lineup_summary` still maps to `entity_summary`, and the hero label can come from `lineup_name`, `player_names`, `metadata.lineup_members`, or the previous synthetic keys.
- Tests added/updated: actual backend-key fixture in `resultShapes.test.ts`, `wave2SectionContracts.test.ts`, and `wave2TableContracts.test.tsx`; synthetic `lineup_members` behavior remains covered.
- Deferred decisions: dedicated lineup summary pattern/table remains deferred.

### player_on_off

- Previous behavior: frontend rendered `SummaryResult.summary` rows as a split using `presence_state`.
- New behavior: unchanged.
- Why no code change: current renderer, route mapping, and tests already match the backend contract and produce visible on/off split rows.
- Tests/docs confirming decision: existing `player_on_off` route/shape/table tests remain passing; result contracts now state the `summary`-row contract is accepted for now.

### playoff_appearances single-team

- Previous behavior: all `playoff_appearances` results mapped to `leaderboard`, so single-team `summary` + `by_season` results could render as an empty shell.
- New behavior: leaderboard results still use `LeaderboardResult`; single-team results without a `leaderboard` section use `PlayoffHistoryResult` appearances mode.
- Tests added/updated: route branch test, shape classification test, section contract test, and rendered hero/table smoke test.
- Deferred decisions: broader playoff renderer redesign remains deferred.

## 4. Route/pattern/shape behavior after cleanup

| Route/result variant | Sections | PatternConfig | Result shape | Renderer |
|---|---|---|---|---|
| `lineup_summary` | `summary` | `{ type: "entity_summary", sectionKey: "summary" }` | `entity_summary` | `EntitySummaryResult` |
| `player_on_off` | `summary` | `{ type: "split", sectionKey: "summary", summaryKey: "summary", bucketKey: "presence_state", splitLabelOverride: "On/Off" }` | `on_off_split` | `SplitResult` |
| `playoff_appearances` leaderboard variant | `leaderboard` | `{ type: "leaderboard", sectionKey: "leaderboard", metricKey: "appearances", sentenceMetricLabel: "playoff appearances" }` | `leaderboard_table` | `LeaderboardResult` |
| `playoff_appearances` single-team summary variant | `summary`, `by_season` | `{ type: "playoff_history", mode: "appearances" }` | `playoff_history` | `PlayoffHistoryResult` |

## 5. Validation

| Command | Result |
|---|---|
| `npm test -- routeToPattern.test.ts resultShapes.test.ts wave2SectionContracts.test.ts wave2TableContracts.test.tsx ResultRenderer.test.tsx` from `frontend/` | Passed: 5 files, 91 tests. |
| `npm run build` from `frontend/` | Passed; Vite emitted the existing large-chunk warning. |
| `make PYTEST=.venv/bin/pytest test-output` | Passed: 332 tests. |
| `git diff --check` | Passed. |

## 6. Remaining risks / deferred decisions

- Dedicated lineup pattern deferred.
- `player_on_off` `split_comparison` normalization deferred.
- Broader playoff renderer redesign deferred.
- `routeToPattern` registry deferred.

## 7. Recommended next phase

Next smallest useful phase: lock any remaining weak result/table contracts that are already source-backed but still depend on inferred frontend behavior, starting with route-specific leaderboard supporting columns.
