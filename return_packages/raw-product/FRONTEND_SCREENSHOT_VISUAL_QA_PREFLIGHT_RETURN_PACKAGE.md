# Frontend Screenshot / Visual QA Preflight Return Package

## 1. Executive summary

- Recommended approach: Option D, a hybrid first pass. Add a small case-targeted visual QA surface/checklist that reuses the raw/frontend-copy QA case set, capture manual local screenshots for the first 15 cases, and defer Playwright automation/diffing until the manual baseline has been reviewed.
- Should we use Playwright now? no. Playwright is not a direct frontend dependency, and adding it now would expand the scope before there is a reviewed visual baseline.
- Should we use screenshots now? yes, in the next execution as manual/local evidence screenshots. Do not start with screenshot diff baselines.
- Should we review desktop/mobile?: yes. Use desktop around 1280px and mobile around 390px for the 15-case pass. Defer tablet/intermediate width unless desktop/mobile reveals a breakpoint-specific issue.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Current visual/testing tooling

| Tool/file | Current support | Useful for visual QA? | Notes |
|---|---|---|---|
| `frontend/package.json` | Vite, React, Vitest/jsdom, Testing Library, `html-to-image`, and `jszip`. No direct Playwright/Cypress dependency. | yes | Existing dependencies can support manual DOM screenshot export. There is no browser automation script today. |
| `frontend/package-lock.json` | Contains Vitest optional metadata mentioning `@vitest/browser-playwright`, but no direct installed Playwright package. | limited | `npm --prefix frontend ls @playwright/test playwright @vitest/browser-playwright cypress --depth=0` returned `(empty)`. |
| `frontend/vite.config.ts` | Vite dev server on 5173, FastAPI proxies, jsdom test environment, build output to `src/nbatools/ui/dist`. | yes | Local visual pages can use the existing dev server and API proxy. |
| `frontend/src/main.tsx` | Routes `/review` to `ReviewPage`; all other paths render the product app. | yes | A dedicated `/visual-qa` route would be straightforward but must be treated as internal QA tooling. |
| `frontend/src/ReviewPage.tsx` | Internal review sweep using `/api/dev/fixtures`, live `/query`, shape grouping, localStorage cache, and screenshot ZIP button. | partly | Good for broad renderer-shape smoke review. Not ideal for this pass because it is shape-grouped, not case-targeted, and captures one representative per shape. |
| `frontend/src/lib/reviewScreenshots.ts` | Browser-side `html-to-image` PNG capture into a JSZip download. | yes | Existing screenshot path is manual/browser initiated. It captures DOM elements, not Playwright viewport screenshots. |
| `frontend/src/test/reviewScreenshots.test.ts` | Unit coverage for screenshot ZIP helper options/fallbacks. | partly | Validates helper plumbing only; no browser layout assertions. |
| `frontend/src/test/ReviewPage.test.tsx` | jsdom tests for review fixture loading, live query running, caching, and screenshot-button plumbing. | partly | Useful guardrails if a visual QA page borrows ReviewPage patterns. Not visual evidence. |
| `frontend/src/test/frontendCopyQaHarness.tsx` | Rehydrates raw QA JSONL rows into `QueryResponse`, renders `ResultEnvelope` plus `ResultRenderer`, extracts text/chips/table/no-result copy, writes reports. | yes | Strong reuse for case selection and copy metadata. Limitation: jsdom cannot validate wrapping, clipping, overlap, hierarchy, or responsive layout. |
| `qa/frontend_copy_corpus.yaml` | Selected 59 frontend-copy cases tied to raw run `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`. | partly | Reusable for 13 of the 15 target visual cases. It does not include `bench_scoring_leaders_wave4` or `celtics_bench_scoring_boundary_wave4`. |
| `outputs/frontend_copy_qa/20260515T024718Z/*` | Clean frontend-copy report: 59 rendered, 0 render failures, 0 soft-check failures. | yes | Good source for target case metadata, expected copy, chips, and table headers. Not visual evidence. |
| `outputs/raw_query_answer_qa/20260515T021820Z/*` | Clean raw QA report: 195 cases, 195 expectation passes, 0 suspicious flags. | yes | Source of truth for all 15 target case IDs, including the two bench no-result cases missing from frontend-copy. |
| `src/nbatools/api.py` and `src/nbatools/api_handlers.py` | `/review` shell and `/api/dev/fixtures` for parser examples. | limited | Existing endpoint serves parser examples, not selected frontend-copy/raw QA cases. Avoid backend changes for the first visual pass if possible. |

Answers to the tooling questions:

- Is Playwright already installed? No direct dependency is installed in `frontend`; `npm ls` for Playwright/Cypress returned empty.
- Is there an existing browser screenshot path? Yes, ReviewPage can download `html-to-image` screenshots as a ZIP, but only for one representative result per shape.
- Can the frontend-copy selected corpus be reused? Yes for 13 of 15 target cases. The visual pass should source the full 15 from the raw QA report or a new visual corpus so the two bench boundary cases are included.
- Is ReviewPage better for screenshots, or should a dedicated visual QA route/page be added? Add a dedicated visual QA route/page for this pass. ReviewPage is useful for shape smoke checks, but the current need is case-targeted desktop/mobile review.
- Can screenshots be generated locally without heavy setup? Yes for manual screenshots using the existing Vite/FastAPI stack and current `html-to-image` dependency. Automated Playwright screenshots would require new setup.

## 3. Strategy options

| Option | Value | Complexity | Runtime cost | Brittleness | Best use | Recommendation |
|---|---:|---:|---:|---:|---|---|
| A - Use existing ReviewPage/manual screenshots | 2/5 | 1/5 | 1/5 | 2/5 | Quick renderer-shape smoke checks and broad manual review. | Do not use as the primary pass. It is not case-targeted and misses mobile/viewport framing. |
| B - Add a dedicated Visual QA page/route using frontend-copy/raw QA cases | 4/5 | 3/5 | 1/5 | 2/5 | First 15-case desktop/mobile manual review with stable case IDs, visual focus notes, and per-case screenshot targets. | Good core of the next execution. Keep it internal and avoid product rendering changes. |
| C - Add Playwright screenshot runner | 4/5 | 4/5 | 3/5 | 4/5 | Repeatable screenshots after manual baselines are accepted. | Defer. Browser install, server orchestration, viewport timing, and diff policy can balloon scope. |
| D - Hybrid static/manual visual QA page first, optional automation later | 5/5 | 3/5 | 2/5 | 2/5 | Evidence gathering now, automation once the team knows what the baseline should preserve. | Recommended. Build the case-targeted surface and artifacts first; add Playwright later only if manual review finds enough value. |

Option notes:

- Option A pros: already exists, no dependency changes, screenshots can be generated from the browser today. Cons: shape representative capture hides case-level risks, target cases are not guaranteed to appear, capture width is fixed at 1120px, and mobile screenshots are not covered.
- Option B pros: aligns directly with the 15 requested cases, can show desktop/mobile checklist metadata, can reuse `ResultEnvelope` and `ResultRenderer`, and can avoid backend behavior changes by using a static case manifest plus live `/query`. Cons: adds internal frontend QA surface and needs guardrails so it does not alter product rendering.
- Option C pros: repeatable viewport screenshots and future CI/manual artifact generation. Cons: Playwright is not installed, browser setup can be slow, and screenshot diffs are likely brittle before a human-approved baseline.
- Option D pros: captures the highest-risk layout evidence now while keeping automation optional. Cons: manual capture is less repeatable until a later runner is added.

## 4. Recommended visual QA corpus

Use the 15 requested case IDs as the initial visual corpus. Source all case IDs from `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`; carry over frontend-copy report metadata where available. The two bench cases are not in `qa/frontend_copy_corpus.yaml`, so the visual corpus should not depend only on that file.

| Case ID | Category | Viewports | Visual focus |
|---|---|---|---|
| `guards_fg_percentage_leaders` | fixed family: position-filtered leaderboard | desktop 1280, mobile 390 | Chip proximity to generic hero, `Position guards` visibility, `FG%` header visibility, table clipping/wrapping. |
| `centers_rebound_leaders_wave4` | fixed family: position-filtered leaderboard guardrail | desktop 1280, mobile 390 | `Position centers` chip, `RPG` header, hero/table alignment, player/team wrapping. |
| `fewest_points_allowed_team_leader` | fixed family: defensive team leaderboard | desktop 1280, mobile 390 | Hero says fewest, table header says `Opponent PTS Per Game`, no visual implication that this is best offensive scoring. |
| `most_points_allowed_team_leaders_wave4` | fixed family: defensive team leaderboard guardrail | desktop 1280, mobile 390 | Hero says most allowed, table header is readable, top row context remains clear. |
| `opponent_ppg_leaders_wave4` | fixed family: opponent metric alias | desktop 1280, mobile 390 | Opponent/allowed-points semantics visible in hero/table; `Opponent PTS Per Game` not clipped. |
| `personal_foul_leaders_wave4` | fixed family: unsupported no-result | desktop 1280, mobile 390 | Primary no-result hierarchy, product-facing message above diagnostics, `PF` context not mistaken for the answer. |
| `rookie_scoring_leaders_wave4` | fixed family: unsupported no-result | desktop 1280, mobile 390 | Primary `Unsupported Leaderboard`/rookie message, diagnostics visually secondary, mobile readability. |
| `starter_assist_leaders_wave4` | fixed family: unsupported no-result | desktop 1280, mobile 390 | Starter/bench unsupported message hierarchy, wrapping of long details, no hidden primary message. |
| `bench_scoring_leaders_wave4` | fixed family: bench no-result missing from latest frontend-copy report | desktop 1280, mobile 390 | League-wide bench unsupported boundary, primary message visibility, details below primary state. |
| `celtics_bench_scoring_boundary_wave4` | fixed family: team bench no-result missing from latest frontend-copy report | desktop 1280, mobile 390 | Team bench-scoring unsupported message, team/context visibility, no diagnostic-first layout. |
| `record_when_jokic_triple_double` | high-risk spot check: record-when | desktop 1280, mobile 390 | Special-event chip proximity to hero, hero hierarchy, no table absence looking like a failure. |
| `lakers_road_record_last_season` | high-risk spot check: team record | desktop 1280, mobile 390 | `Location Away` and `Season 2024-25` chips, table `Home/Away` column visibility, hero/table alignment. |
| `heat_knicks_playoff_series_record_wave4` | high-risk spot check: playoff matchup | desktop 1280, mobile 390 | Dense playoff series table readability, caveat placement, `Round`/winner/series columns not clipped. |
| `lebron_durant_comparison_wave4` | high-risk spot check: comparison | desktop 1280, mobile 390 | Dense comparison table, player column headers, edge/difference readability, mobile stacking. |
| `biggest_scoring_games` | high-risk spot check: verified outlier | desktop 1280, mobile 390 | Verified outlier presentation, 83-point hero/table visibility, table width and row wrapping. |

Viewport recommendation:

- First pass: both desktop 1280px and mobile 390px for all 15 cases.
- If time is constrained: desktop for all 15, then mobile for `guards_fg_percentage_leaders`, `fewest_points_allowed_team_leader`, `personal_foul_leaders_wave4`, `bench_scoring_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, `heat_knicks_playoff_series_record_wave4`, `lebron_durant_comparison_wave4`, and `biggest_scoring_games`.
- Tablet/intermediate width: defer unless mobile/desktop exposes a breakpoint-specific layout problem.

## 5. Visual pass/fail rubric

- Blocking:
  - A critical filter chip exists but is visually disconnected from the hero/table or easy to miss.
  - The hero contradicts the table because layout hides filter, metric, or direction context.
  - A no-result primary message is buried below diagnostics, caveats, notes, or raw boundary identifiers.
  - Table headers or important answer columns are clipped, hidden, or unreadable.
  - Mobile layout overlaps or truncates the critical answer.
  - Comparison/playoff tables become unreadable.
  - Result card hierarchy makes the wrong element look primary.
- Non-blocking:
  - Slightly awkward wrapping that preserves the primary answer.
  - Minor spacing differences between cards/chips/tables.
  - Understandable abbreviations such as `RPG`, `PTS`, `FG%`, or `Opponent PTS Per Game`.
  - Long details requiring scroll, as long as the primary message is visible before the diagnostic detail.
- Product decision:
  - Whether verified outliers should have a visual marker or badge.
  - Whether unsupported diagnostics should be hidden/collapsed by default.
  - Whether position/filter chips should be repeated inside the hero area for filtered leaderboards.
  - Whether internal review routes should be shipped in the built FastAPI UI or gated to local/dev use.
- Needs manual review:
  - Whether generic leaderboard heroes such as `led the NBA` remain acceptable when a nearby position chip is visible.
  - Whether unsupported boundary details with `blocked:` identifiers are acceptable as visible secondary diagnostics.
  - Whether playoff caveats should appear before or after dense tables.

## 6. Recommended execution scope

- Exact goal: produce the first case-targeted visual QA evidence set for the 15 target cases, covering desktop 1280px and mobile 390px, without changing product result rendering or backend behavior.
- Files likely to change:
  - `frontend/src/VisualQaPage.tsx` - new internal case-targeted visual QA page.
  - `frontend/src/VisualQaPage.module.css` - layout for visual review cards and capture targets.
  - `frontend/src/main.tsx` - route `/visual-qa` to the internal page.
  - `frontend/src/visualQaCases.ts` or `qa/frontend_visual_qa_corpus.yaml` - 15 case IDs, queries, focus, and viewport notes. Prefer a `qa/` corpus if a small loader/generator is added; otherwise keep a small static TypeScript manifest for the first manual pass.
  - `frontend/src/lib/reviewScreenshots.ts` or a new `frontend/src/lib/visualQaScreenshots.ts` - only if reusing the existing `html-to-image` ZIP helper for per-case screenshots.
  - Optional tests: `frontend/src/test/VisualQaPage.test.tsx` if the page has non-trivial loading/capture behavior.
- New artifacts:
  - `outputs/frontend_visual_qa/<run_id>/summary.json`
  - `outputs/frontend_visual_qa/<run_id>/visual_qa_report.md`
  - `outputs/frontend_visual_qa/<run_id>/manual_capture_checklist.md`
  - `outputs/frontend_visual_qa/<run_id>/screenshots/desktop/<case_id>.png`
  - `outputs/frontend_visual_qa/<run_id>/screenshots/mobile/<case_id>.png`
- Scripts/commands:
  - Do not add Playwright in the next execution.
  - Do not add screenshot diffing in the next execution.
  - Do not update npm scripts unless a small manual report generator is added. Existing `npm run dev`, `npm run build`, `npm run test`, and `npm run lint` are enough for a manual page pass.
  - Local run path should be: start FastAPI, start Vite, open `/visual-qa`, run the 15 cases, then capture desktop/mobile screenshots manually or through a browser ZIP button.
- Validation:
  - `cd frontend && npm test -- src/test/ReviewPage.test.tsx src/test/reviewScreenshots.test.ts`
  - If a Visual QA page test is added: `cd frontend && npm test -- src/test/VisualQaPage.test.tsx`
  - `cd frontend && npm run build`
  - `cd frontend && npm run lint`
  - Manual validation: confirm all 15 case IDs render in the page and screenshots/checklist artifacts exist for the selected viewport set.
- Stop conditions:
  - Stop if visual QA requires production result-rendering changes before evidence is gathered.
  - Stop if Playwright setup balloons the scope.
  - Stop if screenshot diffs become brittle before manual baseline review.
  - Stop if route/page design would expose dev-only tools in production accidentally.
  - Stop if the page needs backend API behavior changes to load cases; use a static visual case manifest or live `/query` calls first.

## 7. Risks / open decisions

- Tooling risks:
  - Playwright is not installed as a direct frontend dependency.
  - ReviewPage screenshot support is shape-based, not case-based.
  - Browser-side `html-to-image` screenshots may differ from true viewport screenshots and can miss browser chrome/scrolling issues.
- Screenshot brittleness risks:
  - NBA names, logos, fonts, and table widths can make pixel baselines noisy.
  - Mobile screenshots may require scroll stitching or per-card capture instead of full-page capture.
  - Diff thresholds should not be introduced until manual baselines are accepted.
- Responsive layout risks:
  - Dense comparison/playoff tables are the highest clipping risk.
  - No-result cards with long diagnostics may bury primary messages on mobile.
  - Position chips may be too far from generic leaderboard heroes on narrow screens.
- Product decisions:
  - Whether to badge verified official outliers visually.
  - Whether to collapse unsupported diagnostics by default.
  - Whether filtered leaderboard context belongs in the hero sentence, a repeated hero-adjacent chip, or the existing envelope only.
  - Whether internal QA pages should be accessible in deployed builds or only local/dev builds.

## 8. Validation performed

Files inspected:

- `return_packages/raw-product/FRONTEND_HERO_COPY_QA_FIX_WAVE_1_FOLLOWUP_REVIEW_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONTEND_HERO_COPY_QA_FIX_WAVE_1_SEMANTIC_COPY_CLEANUP_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONTEND_HERO_COPY_QA_HARNESS_WAVE_1_RETURN_PACKAGE.md`
- `qa/frontend_copy_corpus.yaml`
- `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl`
- `outputs/frontend_copy_qa/20260515T024718Z/summary.json`
- `outputs/raw_query_answer_qa/20260515T021820Z/report.md`
- `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- `outputs/raw_query_answer_qa/20260515T021820Z/summary.json`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/ReviewPage.module.css`
- `frontend/src/lib/reviewScreenshots.ts`
- `frontend/src/test/reviewScreenshots.test.ts`
- `frontend/src/test/ReviewPage.test.tsx`
- `frontend/src/test/frontendCopyQaReport.test.tsx`
- `frontend/src/test/frontendCopyQaHarness.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/results/ResultRenderer.tsx`
- `src/nbatools/api.py`
- `src/nbatools/api_handlers.py`
- `src/nbatools/vercel_functions.py`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`

Commands/probes run:

```bash
git status --short
sed -n '1,240p' frontend/package.json
sed -n '1,240p' frontend/vite.config.ts
rg -n "playwright|cypress|screenshot|download|ReviewPage|frontend_copy|frontend-copy|copy_qa|qa" frontend qa scripts tests docs outputs return_packages -g '!node_modules'
sed -n '1,260p' frontend/src/ReviewPage.tsx
sed -n '260,560p' frontend/src/ReviewPage.tsx
sed -n '560,760p' frontend/src/ReviewPage.tsx
sed -n '1,220p' frontend/src/lib/reviewScreenshots.ts
sed -n '1,240p' frontend/src/test/frontendCopyQaReport.test.tsx
sed -n '1,280p' frontend/src/test/frontendCopyQaHarness.tsx
sed -n '280,620p' frontend/src/test/frontendCopyQaHarness.tsx
rg --files frontend/src/test frontend/src/lib frontend/src | sort
sed -n '1,240p' frontend/src/ReviewPage.module.css
sed -n '240,520p' frontend/src/ReviewPage.module.css
sed -n '1,220p' frontend/src/main.tsx
sed -n '1,260p' frontend/src/App.tsx
sed -n '1,260p' frontend/src/components/ResultEnvelope.tsx
sed -n '260,520p' frontend/src/components/ResultEnvelope.tsx
sed -n '1,260p' frontend/src/components/NoResultDisplay.tsx
sed -n '1,260p' frontend/src/components/results/ResultRenderer.tsx
sed -n '1,260p' frontend/src/test/reviewScreenshots.test.ts
sed -n '1,320p' frontend/src/test/ReviewPage.test.tsx
sed -n '320,460p' frontend/src/test/ReviewPage.test.tsx
sed -n '1,180p' frontend/src/api/client.ts
rg -n "dev/fixtures|fetchDevFixtures|DevFixture|review" src frontend/src -g '!dist'
sed -n '130,230p' src/nbatools/api.py
sed -n '1,110p' src/nbatools/api_handlers.py
sed -n '1,90p' src/nbatools/vercel_functions.py
sed -n '180,220p' frontend/src/api/types.ts
sed -n '1,220p' return_packages/raw-product/FRONTEND_HERO_COPY_QA_FIX_WAVE_1_FOLLOWUP_REVIEW_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/FRONTEND_HERO_COPY_QA_FIX_WAVE_1_SEMANTIC_COPY_CLEANUP_RETURN_PACKAGE.md
sed -n '1,240p' return_packages/raw-product/FRONTEND_HERO_COPY_QA_HARNESS_WAVE_1_RETURN_PACKAGE.md
sed -n '1,220p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md
rg -n "guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games" qa/frontend_copy_corpus.yaml
rg -n "guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games" outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md
rg -n "guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games" outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl
rg -n "guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games" outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl
npm --prefix frontend ls @playwright/test playwright @vitest/browser-playwright cypress --depth=0
rg -n "@playwright|playwright|cypress|puppeteer|html-to-image|jszip" package.json package-lock.json frontend/package.json frontend/package-lock.json pnpm-lock.yaml yarn.lock frontend/pnpm-lock.yaml frontend/yarn.lock
rg --files -g '*playwright*' -g '*cypress*' -g '*screenshot*' -g '*visual*' -g '!node_modules'
ls -la frontend
find . -maxdepth 3 -type d -name node_modules -o -name '.playwright'
node -e 'read-only JSONL probe for the 15 raw QA target cases'
node -e 'read-only JSONL probe for frontend-copy rendered target cases'
node -e 'read-only summary probe for outputs/frontend_copy_qa/20260515T024718Z/summary.json'
sed -n '1,220p' outputs/raw_query_answer_qa/20260515T021820Z/summary.json
sed -n '1,180p' outputs/raw_query_answer_qa/20260515T021820Z/report.md
sed -n '1,220p' qa/frontend_copy_corpus.yaml
sed -n '280,380p' qa/frontend_copy_corpus.yaml
sed -n '520,620p' qa/frontend_copy_corpus.yaml
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
```

Notes:

- `jq` was not installed, so JSONL/summary inspection used read-only Node probes.
- No test command was run.
- No Playwright command was run.
- No screenshot capture was run.
