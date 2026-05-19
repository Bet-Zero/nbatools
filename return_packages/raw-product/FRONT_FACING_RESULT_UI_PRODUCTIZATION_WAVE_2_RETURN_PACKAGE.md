# Front-Facing Result UI Productization Wave 2 Return Package

## 1. Executive summary

- What changed: public results now render answer-first, with context chips and
  material caveats adjacent to the answer, secondary actions after the result,
  tighter mobile table density, public-friendly detail toggle labels, and one
  public diagnostics disclosure for no-result states.
- Backend behavior changed? no
- Parser behavior changed? no
- Result contracts changed? no
- Frontend rendering changed? yes
- Public hierarchy: the result renderer is the first successful-result element
  after submission on `/`; public actions moved after the answer and are styled
  as compact secondary actions.
- Mobile polish: shared table padding was tightened, wide tables remain
  internally scrollable, and recurring result families received bounded
  mobile-priority column updates.
- Remaining UI work: optional visual QA corpus expansion, screenshot automation,
  and broader unsupported/no-result copy taxonomy refinement remain deferred.

## 2. Public hierarchy changes

| Area | Before | After |
|---|---|---|
| Successful public result order | The action/title panel appeared before the result body. | `ResultRenderer` appears first; actions render after the answer/result body. |
| Public actions | Copy Link, Save Query, and Report issue stacked as prominent full-width mobile buttons above the answer. | The same actions remain available in a compact secondary row after the answer. |
| Debug mode | Debug-rich affordances were available through `?debug=1`. | Debug mode still keeps the full query output panel, Copy Query, Copy JSON, Raw JSON, route/status/reason diagnostics, and feedback metadata. |
| Context chips | Public context from `ResultEnvelope` usually appeared after the table/body. | User-facing context chips render immediately after the result hero through the result renderer. |
| Material caveats | Caveats often appeared below long tables. | Material caveats render next to the answer/context before long tables when the result pattern has a hero. |
| Visual QA public rendering | `/visual-qa` rendered public components but did not fully match `/` ordering. | `/visual-qa` now uses the same answer-first public result order while preserving case metadata and capture wrappers. |

## 3. Mobile/table density changes

| Family/surface | Change | Notes |
|---|---|---|
| Shared result tables | Reduced mobile padding and font size; row toggles are tighter. | Horizontal overflow remains contained inside table scrollers. |
| Game log/finder | Date, team/opponent, score, W/L, and requested/highlight stats are primary on mobile; rank/location/supporting stats are secondary. | Keeps the public row cap and avoids per-query table redesign. |
| Record | W-L, games, win percentage, and season/decade fields are primary; contextual extras are secondary. | Preserves record table shape and details. |
| Split | Split, GP, Record, and core/requested stats are primary; supporting metrics are secondary. | Public split toggles use friendlier labels. |
| Streak | Condition/entity, length, status, start, and end are primary. | Rank, games, record, and average fields are secondary on mobile. |
| Rolling stretch | Window, metric value, start, and end are primary; supporting stats are secondary. | Named-player game-log table keeps requested metric primary. |
| Raw/detail toggle | Default label changed from raw-table language to `Show details` / `Hide details`. | Debug/raw-specific labels can still be supplied by callers. |

## 4. No-result/unsupported UX

- Public behavior: primary no-result and unsupported messages remain clear, and
  Submit for review is shown before heavier diagnostics.
- Details behavior: public no-result states now avoid the duplicate trailing
  envelope Details drawer; diagnostics remain available in the card disclosure
  and debug mode.
- Feedback behavior: feedback actions still include hidden route, status,
  reason, query-class, metadata, entities, filters, and issue context.

## 5. Debug/details preservation

| Surface | Status | Notes |
|---|---|---|
| `/` public mode | Preserved | Public mode is answer-first with secondary actions and one successful-result Details disclosure. |
| `/?debug=1` | Preserved | Debug mode keeps route/status/reason, Copy Query, Copy JSON, Raw JSON, metadata, notes, caveats, and full diagnostics. |
| `/review` | Preserved | Review page remains debug-rich and the local smoke check confirmed the review route loads. |
| `/visual-qa` | Preserved | Public ordering is aligned with `/`; internal case metadata and visual QA controls remain available. |
| Details drawer | Preserved | Diagnostics remain available, with public context/caveats moved up instead of removed. |
| Feedback payloads | Preserved | Query feedback tests continue to verify hidden diagnostics in issue payloads. |

## 6. Visual/frontend-copy impact

- Visual QA corpus changed? no
- Frontend-copy changed? no corpus or expectation changes; generated QA output
  refreshed at `outputs/frontend_copy_qa/20260519T054657Z/`.
- Manual visual checks: local browser smoke passed at 390px for leaderboard,
  team record, finder/game log, comparison, playoff history, playoff matchup,
  split, streak, rolling stretch, top performances, and no-result/unsupported.
  Route checks also passed for `/`, `/?debug=1`, `/review`, and `/visual-qa`.
- Deferred visual QA additions: `jokic_season_summary`,
  `jokic_triple_double_finder`, `jokic_home_away_split`,
  `curry_3_threes_streak`, `jokic_best_5_rebounding_stretch`, and optional
  `lakers_playoff_history` were not added in this wave to avoid expanding the
  manual visual baseline during layout stabilization.

## 7. Tests/validation

- Targeted frontend tests:
  `npm test -- src/test/FirstRun.test.tsx src/test/UIComponents.test.tsx src/test/LayoutPrimitives.test.tsx src/test/QueryFeedback.test.tsx src/test/VisualQaPage.test.tsx src/components/RawDetailToggle.test.tsx`
  - Passed: 6 test files, 81 tests.
- Frontend-copy QA:
  `npm run qa:frontend-copy`
  - Passed: 125 selected, 125 rendered, 0 failures, 0 missing backend records,
    soft checks `480/0/0`.
- Build:
  `npm run build`
  - Passed. Existing Vite large-chunk warning remains.
- Lint:
  `npm run lint`
  - Passed with the existing `ReviewPage.tsx` `react-hooks/exhaustive-deps`
    warning.
- Diff hygiene:
  `git diff --check`
  - Passed after return package creation.
- Manual/mobile checks:
  local Chrome/CDP smoke passed at 390px for the listed result families and
  confirmed no document-level horizontal overflow in the probed public result
  pages.

## 8. Files changed

| File | Change type | Why |
|---|---|---|
| `frontend/src/App.tsx` | Rendering order | Make public results answer-first and move public actions after the result. |
| `frontend/src/App.module.css` | Styling | Make public actions compact and visually secondary, including on mobile. |
| `frontend/src/VisualQaPage.tsx` | Rendering order | Align visual QA public rendering with `/` while preserving QA metadata. |
| `frontend/src/components/ResultEnvelope.tsx` | Component behavior | Add public context summary, dedupe/humanize chips, preserve debug Details. |
| `frontend/src/components/ResultEnvelope.module.css` | Styling | Style public context/caveat summary and tighten mobile details spacing. |
| `frontend/src/components/NoResultDisplay.tsx` | Component behavior | Keep Submit for review prominent and reduce duplicate public diagnostics. |
| `frontend/src/components/results/ResultRenderer.tsx` | Component contract | Pass public context into the first rendered result pattern after the hero. |
| `frontend/src/components/results/patterns/ComparisonResult.tsx` | Layout hook | Render context/caveats after the hero. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | Layout hook | Render context/caveats after the hero. |
| `frontend/src/components/results/patterns/FallbackTableResult.tsx` | Layout hook | Render context/caveats before fallback raw cards. |
| `frontend/src/components/results/patterns/GameLogResult.tsx` | Layout/mobile priority | Render context/caveats after the hero and tune mobile columns. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Layout hook | Render context/caveats after the hero. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | Layout hook | Render context/caveats after the hero. |
| `frontend/src/components/results/patterns/RecordResult.tsx` | Layout/mobile priority | Render context/caveats after the hero and tune mobile columns. |
| `frontend/src/components/results/patterns/RollingStretchResult.tsx` | Layout/mobile priority | Render context/caveats after the hero and tune mobile columns. |
| `frontend/src/components/results/patterns/SplitResult.tsx` | Layout/mobile priority | Render context/caveats after the hero, tune mobile columns, improve public toggle labels. |
| `frontend/src/components/results/patterns/StreakResult.tsx` | Layout/mobile priority | Render context/caveats after the hero and tune mobile columns. |
| `frontend/src/components/results/patterns/TopPerformancesResult.tsx` | Layout hook | Render context/caveats after the hero. |
| `frontend/src/components/results/primitives/RawDetailToggle.tsx` | Copy | Default public toggle label now uses details language instead of raw-table language. |
| `frontend/src/components/results/primitives/RawDetailToggle.module.css` | Styling | Tighten mobile toggle presentation. |
| `frontend/src/components/results/primitives/ResultTable.module.css` | Styling | Improve mobile density while keeping internal horizontal scroll. |
| `frontend/src/test/FirstRun.test.tsx` | Test coverage | Verify public answer-first ordering, context placement, and debug affordances. |
| `frontend/src/test/LayoutPrimitives.test.tsx` | Test coverage | Verify public context/caveat summary and preserved diagnostics. |
| `frontend/src/test/UIComponents.test.tsx` | Test coverage | Verify no-result diagnostics consolidation and Submit for review prominence. |
| `frontend/src/components/RawDetailToggle.test.tsx` | Test coverage | Verify public-friendly default toggle labels. |
| `docs/operations/ui_guide.md` | Documentation | Record Wave 2 public hierarchy/mobile behavior and preserved debug surfaces. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | Documentation | Update release handoff with Wave 2 completion and remaining UI work. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | Documentation | Update release package readiness with answer-first public rendering. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Documentation | Mark Wave 2 hierarchy/mobile polish as completed and note preserved debug paths. |
| `return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_WAVE_2_RETURN_PACKAGE.md` | Return package | Summarize Wave 2 implementation, validation, and release impact. |

## 9. Release impact

- Engine readiness: unchanged; no engine, parser, backend, data, or result
  contract changes were made.
- UI readiness: public `/` is now answer-first and more mobile-readable across
  the probed common result families, with diagnostics preserved.
- Public launch recommendation: suitable for continued limited preview and
  closer to broad public launch; run final release review with updated visual
  baselines before broad launch.
- Next UI wave, if any: optional visual QA corpus expansion, screenshot
  automation, and broader unsupported/no-result copy refinement.
