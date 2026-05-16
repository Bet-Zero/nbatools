# Frontend Screenshot / Visual QA Fix Wave 1: Mobile Tables + Filtered Leaderboard Heroes Return Package

## 1. Executive summary

- What was wrong: mobile dense tables could hide key answer columns, and position-filtered leaderboard heroes still used generic `led the NBA` wording.
- What changed: added mobile-priority table columns for the affected result patterns, allowed long comparison edge cells to wrap, and added position-aware leaderboard hero scope.
- Production frontend rendering changed? yes
- Backend behavior changed? no
- Tests added/updated: `ResultRenderer` hero and mobile-priority assertions; frontend-copy corpus checks for filtered hero wording; frontend-copy artifact test timeout made explicit for the full 59-case report write.
- Frontend-copy QA run: passed, `59` rendered, `0` render failures, `0` soft-check failures.
- Manual visual recheck: completed at `390px` through local `/visual-qa` browser inspection for the five affected cases.
- Remaining risk: fresh screenshots should be requested for the five affected cases to replace the manual baseline artifacts.

## 2. Findings addressed

| Finding | Cases | Status | Notes |
|---|---|---|---|
| FVQ-001 | `biggest_scoring_games`, `lebron_durant_comparison_wave4`, `heat_knicks_playoff_series_record_wave4` | fixed/targeted | Mobile tables now prioritize the requested answer columns and hide lower-priority dense columns below `640px`. |
| FCQ/FVQ-002 | `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | fixed | Heroes now say `led guards` / `led centers`; unfiltered leaderboards still say `led the NBA`. |

## 3. Behavior before/after

### FVQ-001 mobile dense table clipping
- Before: top-performance `PTS`, comparison `Edge / Difference`, and playoff `Series Result` could be off-screen or clipped on mobile.
- After: top performances show Rank, Player, Date, and requested stat; comparisons show Metric, both players, and Edge / Difference; playoff matchup tables show Season, Round, Winner, and Series Result.

### FCQ/FVQ-002 filtered leaderboard hero context
- Before: filtered player leaderboards said `led the NBA`.
- After: guard and center leaderboards include position context, while unfiltered leaderboards keep `led the NBA`.

## 4. Files changed

| File | Change type | Why |
|---|---|---|
| `frontend/src/components/results/primitives/ResultTable.tsx` | Updated | Added column-level mobile priority metadata. |
| `frontend/src/components/results/primitives/ResultTable.module.css` | Updated | Hides secondary columns on mobile and lets wrapped dense cells break cleanly. |
| `frontend/src/components/results/patterns/TopPerformancesResult.tsx` | Updated | Prioritizes Rank, Player, Date, and requested stat on mobile. |
| `frontend/src/components/results/patterns/ComparisonResult.tsx` | Updated | Keeps comparison metric/value/edge columns visible on mobile. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | Updated | Keeps playoff matchup interpretation columns visible on mobile. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Updated | Uses `position_filter` / applied position filter metadata in player leaderboard hero copy. |
| `frontend/src/test/ResultRenderer.test.tsx` | Updated | Covers filtered hero wording and mobile-priority column contracts. |
| `frontend/src/test/frontendCopyQaReport.test.tsx` | Updated | Adds an explicit timeout for the full report artifact-writing test. |
| `qa/frontend_copy_corpus.yaml` | Updated | Tightens guard/center hero soft checks. |
| `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` | Updated | Records confirmed findings and targeted checks. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Updated | Records Fix Wave 1 status and validation artifacts. |

## 5. Test coverage

- `ResultRenderer.test.tsx`: proves unfiltered leaderboards still say `led the NBA`; guard-filtered heroes mention guards and omit `led the NBA`; center-filtered heroes mention centers and omit `led the NBA`.
- `ResultRenderer.test.tsx`: proves mobile-priority metadata keeps top-performance, comparison, and playoff matchup critical columns primary.
- `frontendCopyQaReport.test.tsx`: continues to render the selected report cases and write artifacts.
- `VisualQaPage.test.tsx`: existing visual QA page coverage still passes.

## 6. QA validation

- Frontend-copy QA: `cd frontend && npm run qa:frontend-copy` passed.
- Latest report: `outputs/frontend_copy_qa/20260515T224620Z/frontend_copy_report.md`
- Summary: `59` selected, `59` rendered, `0` render failures, `0` missing backend records, soft checks `160/0/0`.
- Mobile `/visual-qa` recheck at `390px`: passed for the five affected cases.
- Mobile screenshot artifacts:
  - `/private/tmp/visualqa_mobile_biggest_scoring_games.png`
  - `/private/tmp/visualqa_mobile_lebron_durant_comparison_wave4_after_wrap.png`
  - `/private/tmp/visualqa_mobile_heat_knicks_playoff_series_record_wave4.png`
  - `/private/tmp/visualqa_mobile_guards_fg_percentage_leaders.png`
  - `/private/tmp/visualqa_mobile_centers_rebound_leaders_wave4.png`
- Desktop spot-check: `biggest_scoring_games` at `1280px` still showed desktop supporting columns including `Opp`, `Result`, and `3PM`.

## 7. Standard validation

- `cd frontend && npm test -- src/test/ResultRenderer.test.tsx src/test/frontendCopyQaReport.test.tsx src/test/VisualQaPage.test.tsx`
  - Result: passed, `3` files, `65` tests.
- `cd frontend && npm run qa:frontend-copy`
  - Result: passed, `4` tests; report run `20260515T224620Z`.
- `cd frontend && npm run build`
  - Result: passed. Vite emitted the existing large chunk warning for the main JS bundle.
- `cd frontend && npm run lint`
  - Result: passed with the existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- `git diff --check`
  - Result: passed with no output.

## 8. Next recommendation

- Request fresh screenshots for the five affected cases.
- Accept no-result cards as the current visual baseline; this wave did not change them.
- Proceed to deploy-safe `/visual-qa` parity with `/review`.
- Consider Playwright only after one more manual baseline, and only as optional capture automation rather than screenshot diffing.
