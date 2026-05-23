# Front-Facing Result UI Productization Wave 2 Preflight Return Package

## 1. Executive summary

- Recommended decision: execute a small Wave 2 before broad public launch,
  focused on answer hierarchy, action placement, context/caveat placement, and
  mobile density in the public `/` result surface.
- Main remaining UI issue: the public result is cleaner after Wave 1, but the
  first result element is still an action/title panel, while scope chips,
  caveats, and Details appear after the result body. On dense mobile results,
  the answer is visible but supporting context is often far below the first
  viewport.
- Recommended Wave 2 scope: polish layout and CSS first. Move the answer closer
  to the top, demote the action row, place context/caveats near the answer,
  tighten chip wrapping, improve mobile table density, and make Details less
  visually heavy on phones.
- Should public launch wait for Wave 2? yes for broad public launch; no for
  limited preview or feedback collection.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Current public-mode hierarchy findings

| Result family | Finding | Priority |
|---|---|---|
| All successful public results | `/` renders the action panel before the answer. At 390px, Copy Link, Save Query, and Report issue stack full-width above the hero, consuming about 170px before the result body. | High |
| All successful public results | Public context chips live in `ResultEnvelope` after `ResultRenderer`, so chips usually appear below the table/body rather than next to the answer. | High |
| All successful dense results | Details is available and collapsed, but it usually lands after tables and detail toggles, often well below the first viewport. | Medium |
| Leaderboard | Hero and ranking table are strong, but season/position/filter chips appear after the table. Mobile table scroll is contained; some leaderboards still expose 7 visible columns on mobile. | High |
| Team record | Hero sentence is strong. W-L is visible, but Location/Season chips and caveats appear after the record table. Detail toggles compete with Details on mobile. | High |
| Player/entity summary | Hero is concise and dominant once reached. The action panel is the main hierarchy problem; chips appear after the hero but still within the first viewport for short summaries. | Medium |
| Game log/finder | Count/answer phrase is strong. Public row cap works. The 19-column table is very wide and context chips appear after the capped table and detail toggle. | High |
| Comparison | Hero has a clear edge sentence and subject cards help. On mobile, the comparison body becomes very tall before chips/Details appear. | High |
| Playoff history | Hero and table are understandable. Material historical caveat is visible, but only after the long season table on public `/`. | High |
| Playoff matchup | Matchup hero is clear. Series table is readable at 390px, but caveat placement is late and the raw summary toggle sits before Details. | Medium |
| Streak | Hero clearly states condition, length, and span. Mobile table scroll is contained, but the condition/length columns compete with extra record/date columns. | Medium |
| Rolling stretch | Hero clearly states best window/value. Mobile table scroll is contained, but the top-window table pushes chips/Details below the fold. | Medium |
| Split | Hero identifies the split, but table is 11 columns and uses `Show raw table` labels in public. Split/filter chips appear after two raw-table toggles. | High |
| Top performances | Hero promotes the top row well. Mobile column-priority handling is better here than most families; desktop table still has a moderate horizontal scroll. | Medium |
| No-result/unsupported | Public copy is clear and Submit for review is visible. There are two Details affordances: one inside the no-result card and one in the trailing envelope, which feels duplicative. | High |

## 3. Mobile density findings

| Surface/family | Finding | Recommendation |
|---|---|---|
| Public result action row | At 390px, successful result actions stack above the answer as full-width buttons. This makes actions visually more important than the answer. | Move public actions below or beside the answer where space allows. On mobile, show one primary share/action affordance plus a compact secondary action cluster after the hero. |
| Answer hero | The hero itself wraps safely and does not clip in probed cases. It is pushed down by header/query/freshness plus the result action panel. | Keep existing `ResultHero`, but make it the first result element inside the result area. |
| Context chips | Chips wrap without page overflow, but placement after tables means filters, season, player/team, and caveats are often detached from the answer. | Move public context chips directly under the hero or between hero and table. Limit repeated chips and keep raw metadata in Details. |
| Table columns | No document-level horizontal overflow was observed. Wide tables scroll internally. Finder, split, streak, rolling stretch, record, and leaderboard remain dense. | Apply shared mobile column-priority defaults for recurring secondary columns. Do not redesign every table in Wave 2. |
| Game log/finder | Finder table probed at 390px had 19 columns and an internal scroll width around 1665px. Public row cap of 12 games works. | Preserve row cap; make Date/Opp/Result/requested stat primary and mark secondary box-score columns as mobile-secondary where safe. |
| Split | Split table probed at 390px had 11 columns and internal scroll around 912px. Raw table toggles appeared before Details. | Change public toggle language away from `Show raw table`; keep Split, GP, Record, and requested/core stats primary. |
| Comparison | Comparison table fit the phone width, but subject cards and metrics made the body very tall before context/Details. | Keep subject cards stacked, move context above the cards/table, and keep secondary metrics behind the existing Show more control. |
| Details drawer | Successful result Details can be extremely tall on phone; the team-record Details probe expanded to roughly 3380px because raw metadata and JSON are inline. | Keep Details capability, but make mobile Details sections collapsed or grouped, with raw metadata/JSON clearly secondary. |
| No-result card | Primary no-result copy stays above diagnostics. Internal Details is full-width and Submit for review is visible. The trailing envelope adds another Details below it. | Prefer one public diagnostics disclosure for no-result states. Preserve all diagnostic metadata in that disclosure. |
| Feedback action | Report issue sits above successful answers; Submit for review sits inside no-result card after Details. | For successful answers, demote feedback below the answer/table or into a compact action row. For no-result, keep Submit for review prominent before heavy diagnostics. |
| Material caveats | Caveats render visibly, but successful-result caveats are often after the body/table; playoff caveats appeared below long tables. | Move material caveats close to the hero/context, before long tables. Keep nonmaterial notes in Details. |

## 4. Result-family polish recommendations

| Family | Wave 2 recommendation | Deferred |
|---|---|---|
| Leaderboard | Use the existing hero as the headline. Keep rank, entity, queried metric, team, and GP/season context as primary. Place filtered context chips directly under the hero. | Custom per-metric mobile column sets for every leaderboard subtype. |
| Record | Keep sentence headline. Treat W-L, GP, and Win% as the main table cells. Put Season/Location/Opponent group chips before the table; caveats before detail toggles. | Redesigning record tables into stat cards or removing by-season/detail tables. |
| Game log/finder | Keep count phrase or answer phrase as headline. Keep row cap. Prioritize Date, Team/Opp, W/L, score, and requested stats on mobile. | Per-query custom game-log columns for every stat combination. |
| Comparison | Keep edge/difference headline. Stack subject panels on mobile. Place context before subject panels and keep Show more metrics as the public expansion point. | Rebuilding comparison as a custom mobile card system. |
| Playoff history | Keep matchup/round/history headline. Move historical caveats near the hero. Keep Season/Round/Opponent/Result/Record as main table columns. | Full postseason-specific mobile table redesign. |
| Streak | Keep condition, length, and span in the hero. On mobile, emphasize Streak/Length/Status/Start/End and push averages/details lower. | Deep condition-language rewrite or route-specific streak layouts. |
| Rolling stretch | Keep window size, metric value, and date span adjacent in the hero. Ensure Window + metric + Start/End stay primary on mobile. | Screenshot automation and custom window-card layouts. |
| Split | Make split labels more readable in public context (`home/away` -> `Home/Away`). Keep Split, GP, Record, and core/requested stats primary. Rename public raw toggles to additional/detail wording. | Reworking every split variant into bespoke cards. |
| Top performances | Keep top row hero. Maintain Rank, Player/Team, Date, requested metric as primary; keep Opp/Result/Score/supporting stats secondary on mobile. | Building a separate top-performance hero row/card before the table. |
| No-result | Keep product-facing title/message and suggestions. Put Submit for review before heavy diagnostics. Avoid duplicate public Details where possible while preserving diagnostics. | Broad unsupported-copy taxonomy rewrite or QA corpus expectation changes. |

## 5. Visual QA implications

- Existing visual cases affected: yes. A Wave 2 layout pass will affect the
  current 15-case corpus because action hierarchy, chip placement, caveat
  placement, and mobile spacing are visible in nearly every case.
- New cases recommended:
  - `jokic_season_summary`: `Jokic this season` for short player summary/no-table
    hierarchy.
  - `jokic_triple_double_finder`: `How often has Nikola Jokic recorded a triple-double this season?`
    for count + capped wide game log.
  - `jokic_home_away_split`: `Jokic home vs away this season` for split table,
    edge chips, and raw/detail toggles.
  - `curry_3_threes_streak`: `Curry longest streak with at least 3 threes` for
    threshold streak density.
  - `jokic_best_5_rebounding_stretch`: `Jokic best 5-game rebounding stretch this season`
    for rolling-window table density.
  - Optional: `lakers_playoff_history` for single-team playoff history caveat
    placement, because the current visual corpus covers playoff matchup but not
    long single-team postseason history.
- Manual/mobile checks: run the existing 15 cases plus the new mobile cases at
  390px. Spot-check `/` for the same queries because `/visual-qa` renders public
  components but currently orders the envelope before the result renderer, while
  `/` orders the result renderer before the envelope in public mode.
- Screenshot automation deferred: yes. Keep Wave 2 manual/visual baseline
  refresh lightweight; add screenshot automation later if visual QA becomes a
  repeated release gate.

## 6. Frontend-copy implications

- Soft checks to preserve: current 125/125 rendered, soft checks `480/0/0`.
  Preserve semantic facts, table header fragments, and filter-chip fragments
  unless Wave 2 intentionally changes public copy.
- Cases likely affected:
  - `team_record` cases if context chip order/labels or caveat placement changes.
  - `split` cases if `home_away` becomes `Home/Away` or raw toggle labels change.
  - `top_performances` cases if mobile-priority changes accidentally alter
    rendered table headers in the harness.
  - `playoff_history` and `playoff_matchup_history` cases if caveat wording or
    round labels change.
  - `no_result_unsupported` cases if public no-result Details or unsupported
    titles/messages are consolidated.
- Whether corpus updates are expected: not for CSS-only spacing, ordering, and
  action hierarchy. Corpus updates are expected only if public copy, table
  headers, chip labels, no-result messages, or toggle labels deliberately
  change.

## 7. Recommended execution scope

- Exact goal: make the public result answer-first and mobile-readable without
  changing backend behavior, parser behavior, result contracts, QA expectations,
  or debug/review diagnostics.
- Files likely to change:
  - `frontend/src/App.tsx`
  - `frontend/src/App.module.css`
  - `frontend/src/components/ResultEnvelope.tsx`
  - `frontend/src/components/ResultEnvelope.module.css`
  - `frontend/src/components/NoResultDisplay.tsx`
  - `frontend/src/components/NoResultDisplay.module.css`
  - `frontend/src/components/results/primitives/ResultTable.module.css`
  - `frontend/src/components/results/primitives/RawDetailToggle.tsx`
  - `frontend/src/components/results/primitives/RawDetailToggle.module.css`
  - narrowly selected pattern files only if they need `mobilePriority` on
    existing columns (`GameLogResult.tsx`, `RecordResult.tsx`,
    `SplitResult.tsx`, `StreakResult.tsx`, `RollingStretchResult.tsx`)
  - `frontend/src/test/*` targeted tests for public/debug ordering and no-result
    diagnostics preservation
  - `docs/operations/ui_guide.md` only after verified shipped behavior changes
  - `qa/frontend_visual_qa_corpus.json` only if adding the recommended visual
    cases in the execution wave
- Tests to update/add:
  - App/public rendering test that the answer/result renderer appears before
    public actions or that actions are visually secondary by DOM/order contract.
  - ResultEnvelope public test for context/caveat placement and Details
    diagnostics preservation.
  - NoResultDisplay test ensuring public message and Submit for review remain
    prominent while diagnostic details remain available.
  - ResultTable or pattern tests only for any new mobile-priority column flags
    that affect rendered markup/classes.
  - VisualQaPage test only if the corpus expands or `/visual-qa` ordering is
    intentionally aligned with `/`.
- QA validation:
  - `cd frontend && npm test -- src/test/FirstRun.test.tsx src/test/UIComponents.test.tsx src/test/LayoutPrimitives.test.tsx src/test/QueryFeedback.test.tsx src/test/VisualQaPage.test.tsx`
  - Add changed component test files to the targeted command.
  - `cd frontend && npm run qa:frontend-copy`
  - Manual visual QA baseline refresh for current 15 cases plus recommended
    mobile additions.
  - Preview smoke for `/`, `/?debug=1`, `/review`, and `/visual-qa`.
  - Mobile spot checks at 390px for leaderboard, record, finder, comparison,
    playoff, split, streak, rolling stretch, top performances, and no-result.
  - `cd frontend && npm run build`
  - `cd frontend && npm run lint`
  - No backend raw QA unless result contracts/backend behavior change.
- Stop conditions:
  - Any backend contract, parser, route, or query behavior change becomes
    necessary.
  - `/review` loses route/status/reason/query-class/raw diagnostics.
  - `/?debug=1` loses debug rendering.
  - `/visual-qa` loses internal case metadata or capture selectors.
  - Feedback payloads lose hidden diagnostic metadata.
  - Material caveats or unsupported-boundary guidance become less visible or
    less accurate.
  - Layout changes require broad per-family table rewrites instead of bounded
    mobile-priority tweaks.

## 8. Release impact

- Engine readiness: unchanged and not part of this wave. Wave 2 should not touch
  the engine.
- UI readiness after Wave 1: preview-ready and much cleaner than the pre-Wave 1
  default, with debug chrome moved behind Details/public debug mode.
- Expected UI readiness after Wave 2: public `/` should feel intentionally
  answer-first across common result families, with diagnostics preserved but no
  longer competing with answer hierarchy.
- Launch recommendation: continue limited preview/feedback after Wave 1; run
  Wave 2 before broad public launch.

## 9. Validation performed

Files inspected:

- `return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_WAVE_1_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_PREFLIGHT_RETURN_PACKAGE.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/ResultEnvelope.module.css`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/NoResultDisplay.module.css`
- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/SplitResult.tsx`
- `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/FallbackTableResult.tsx`
- `frontend/src/components/results/primitives/ResultHero.tsx`
- `frontend/src/components/results/primitives/ResultHero.module.css`
- `frontend/src/components/results/primitives/ResultTable.tsx`
- `frontend/src/components/results/primitives/ResultTable.module.css`
- `frontend/src/components/results/primitives/RawDetailToggle.tsx`
- `frontend/src/components/results/primitives/RawDetailToggle.module.css`
- `frontend/src/design-system/ResultEnvelopeShell.tsx`
- `frontend/src/design-system/ResultEnvelopeShell.module.css`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `frontend/src/visualQaCases.ts`
- `qa/frontend_visual_qa_corpus.json`
- `qa/frontend_copy_corpus.yaml`
- `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`

Commands/probes run:

- `sed -n '1,240p' return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_WAVE_1_RETURN_PACKAGE.md`
- `sed -n '1,260p' return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_PREFLIGHT_RETURN_PACKAGE.md`
- `sed -n '1,260p' docs/operations/ui_guide.md`
- `sed -n '1,260p' outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`
- `sed -n ... frontend/src/App.tsx`
- `sed -n ... frontend/src/components/ResultEnvelope.tsx`
- `sed -n ... frontend/src/components/NoResultDisplay.tsx`
- `sed -n ... frontend/src/components/results/ResultRenderer.tsx`
- `rg --files frontend/src/components/results/patterns frontend/src/components/results/primitives frontend/src/components/results/config`
- `sed -n ... frontend/src/components/results/patterns/*`
- `sed -n ... frontend/src/components/results/primitives/*`
- `sed -n ... frontend/src/design-system/ResultEnvelopeShell.*`
- `sed -n ... frontend/src/VisualQaPage.tsx`
- `sed -n ... frontend/src/test/VisualQaPage.test.tsx`
- `sed -n ... qa/frontend_visual_qa_corpus.json`
- `rg -n "streak|rolling|split|playoff|comparison|finder|top performances|biggest|last 10" qa/frontend_copy_corpus.yaml`
- `rg -n "^## |^### .*streak|^### .*rolling|^### .*split|^### .*comparison|^### .*playoff|^### .*top|^### .*finder|Query:" outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`
- `cat frontend/package.json`
- `git status --short`
- Started local API for probing:
  `PYTHONPATH=src .venv/bin/python -m uvicorn nbatools.api:app --host 127.0.0.1 --port 8000`
- Started Vite dev server for probing:
  `npm run dev -- --host 127.0.0.1 --port 5173`
- Health check:
  `curl -s http://127.0.0.1:8000/health`
- Headless Chrome/CDP public rendering probe at 1280px and 390px for:
  - `Who leads the NBA in points per game this season?`
  - `Lakers road record last season`
  - `Jokic this season`
  - `How often has Nikola Jokic recorded a triple-double this season?`
  - `LeBron James vs Kevin Durant comparison`
  - `Lakers playoff history`
  - `Heat Knicks playoff series record`
  - `Curry longest streak with at least 3 threes`
  - `Jokic best 5-game rebounding stretch this season`
  - `Jokic home vs away this season`
  - `What were the biggest scoring games this season?`
  - `personal fouls leaders this season`
- Headless Chrome/CDP mobile Details probe for:
  - `Lakers road record last season`
  - `personal fouls leaders this season`
  - `Jokic home vs away this season`

Tests were not run because this was a preflight investigation with no
production code, test, or corpus changes.
