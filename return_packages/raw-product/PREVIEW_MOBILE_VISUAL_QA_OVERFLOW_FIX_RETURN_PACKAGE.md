# Preview Mobile Visual QA Overflow Fix Return Package

## 1. Executive summary

- What was wrong: the deployed preview `/visual-qa` page overflowed horizontally
  at about 390px, so the QA wrapper/card clipped primary result content.
- What changed: `/visual-qa` wrapper, card, grid, metadata, checklist, and result
  column CSS now shrink within mobile viewport bounds and wrap long QA-only text.
- Production rendering changed? yes, frontend `/visual-qa` rendering only.
- Backend behavior changed? no.
- Tests added/updated: `VisualQaPage.test.tsx` now covers stable case cards
  inside the page/card/body/result wrapper classes.
- Manual mobile validation: local production shell measured `pageWidth 390` and
  `bodyWidth 390` at a 390px viewport; all five blocker cards stayed inside the
  viewport and required result text was present.
- Preview rerun required? yes.
- Remaining risk: deployed preview has not been rerun after redeploy; manual
  visual QA is still measurement/spot-check based, not screenshot diffing.

## 2. Root cause

- Overflow source: `/visual-qa` page wrapper and QA card intrinsic sizing, not
  backend data or result computation.
- Affected containers/components: `VisualQaPage.module.css` shell, hero metadata
  grid, case cards, card body, checklist, result column, capture target, and
  long QA metadata/path/case-id text.
- Why preview exposed it: the QA page combined wide result tables with long
  internal checklist/metadata strings. Several grid/flex children lacked
  `min-width: 0` and mobile grids used min-content-friendly tracks, so the page
  expanded to the widest internal content instead of the 390px viewport.

## 3. Behavior before/after

| Case | Before | After |
|---|---|---|
| `biggest_scoring_games` | Card expanded to about 528px in the mobile repro; page scroll width reached 632px and clipped the result area. | Card measured 378px at 390px; `83` and `PTS` were present; table frame stayed contained. |
| `lebron_durant_comparison_wave4` | Card overflow clipped comparison content. | Card measured 378px at 390px; `Edge / Difference` was present and contained. |
| `heat_knicks_playoff_series_record_wave4` | Card overflow clipped playoff matchup content. | Card measured 378px at 390px; `Series Result` was present and contained. |
| `guards_fg_percentage_leaders` | Card overflow clipped leaderboard answer/table content. | Card measured 378px at 390px; guard context and `FG%` were present; wide table overflow stayed inside its scroll frame. |
| `centers_rebound_leaders_wave4` | Card overflow clipped leaderboard answer/table content. | Card measured 378px at 390px; center context and `RPG` were present; wide table overflow stayed inside its scroll frame. |

## 4. Files changed

| File | Change type | Why |
|---|---|---|
| `frontend/src/VisualQaPage.module.css` | CSS fix | Constrain QA page/card/grid widths, add shrink behavior, wrap QA-only long text, and tune mobile padding for the 390px validation target. |
| `frontend/src/test/VisualQaPage.test.tsx` | Test update | Assert stable case cards render inside the expected visual QA layout wrappers. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Docs update | Record preview blocker, frontend-only local fix, local validation, and preview rerun requirement. |
| `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` | Docs update | Add FVQ-003 and mark the five blocker cases as locally fixed pending preview rerun. |
| `return_packages/raw-product/PREVIEW_MOBILE_VISUAL_QA_OVERFLOW_FIX_RETURN_PACKAGE.md` | Return package | Capture root cause, changes, validation, and next recommendation. |

## 5. Validation

- VisualQaPage tests: `cd frontend && npm test -- src/test/VisualQaPage.test.tsx`
  passed, 1 file / 5 tests.
- ResultRenderer/frontend-copy tests: not run; shared result/table components
  were not changed.
- Frontend build: `cd frontend && npm run build` passed. Vite emitted the
  existing large-chunk warning for the 543.51 kB JS bundle.
- Frontend lint: `cd frontend && npm run lint` passed with 0 errors and the
  existing `ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- `git diff --check`: passed with no output.
- Manual 390px `/visual-qa` validation: local production shell reported
  `viewportWidth 390`, `pageWidth 390`, `bodyWidth 390`; blocker cards measured
  378px wide and required text was present for all five cases.
- Desktop spot-check: at 1280px, local production shell reported
  `pageWidth 1280`; `biggest_scoring_games` and
  `lebron_durant_comparison_wave4` remained inside the viewport with required
  result text present.

## 6. Next recommendation

- Redeploy.
- Rerun Raw Product Preview Manual QA.
- If preview passes, mark current boundary `PREVIEW_READY` or
  `PREVIEW_READY_WITH_NOTES`.
