# Raw Product Hardening — Wave 6 Return Package

## 1. Executive summary

- Wave executed: Wave 6 — Lightweight Product Promise/Homepage Pass, per
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5
  (Wave 6) and folding in the public answer context duplication audit
  from `RAW_PRODUCT_POST_REVIEW_NOTES.md` §4.
- What was produced: a small, lightweight UX pass on the public homepage
  surface plus a public result-context audit. Three product files
  changed plus one targeted test file. No backend, parser/routing,
  result-contract, or QA-corpus changes.
- Scope summary:
  - Stronger search-first placeholder copy on the query bar.
  - First-run empty state copy now directs the user to type or pick a
    starter query.
  - Public `ResultContextSummary` chip strip no longer duplicates scope
    (`player`, `players`, `team`, `teams`, `season`, `opponent`,
    `split`) that is already stated in the answer hero. Applied
    filters, date ranges, included opponents, "without X", clutch
    filters, and similar non-obvious trust/scope context still render.
  - Debug `?debug=1`, `/review`, `/visual-qa`, the Details disclosure,
    and the query-feedback payload diagnostics are unchanged.
- Release status: unchanged. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`.
- Wave 6 also completes the docs-first portion of the post-review
  hardening plan: Waves 1–5 were docs/policy only; Wave 6 is the first
  wave to touch frontend source. All Wave 1–5 stop conditions remain
  honored.

## 2. Files changed

| File | Change type | Why |
| --- | --- | --- |
| `frontend/src/components/QueryBar.tsx` | Public copy | Replaced the generic `placeholder="Type an NBA query…"` with a stronger search-first prompt that shows two concrete starter examples in-line: `Ask a stat-shaped question — e.g. Jokic recent form, top scorers this season`. Helps first-time users see what kind of question the engine answers without forcing a tutorial or category selector. |
| `frontend/src/components/EmptyState.tsx` | Public copy | Extended the first-run description with one short sentence guiding the user to either type a question or pick a starter query (already rendered in the secondary panel). No layout change, no required onboarding, no required category selector. |
| `frontend/src/components/ResultEnvelope.tsx` | Public rendering | Added a `BASE_SCOPE_CHIP_KEYS` set (`player`, `players`, `team`, `teams`, `season`, `opponent`, `split`) and filtered those out of the public `ResultContextSummary` chip strip. Applied filters, date ranges, included opponents, "without X", clutch filters, schedule-context filters, and other non-obvious trust/scope context still render. Debug `ResultEnvelope` (which renders its own chip row only when `?debug=1`) is **not** touched and still shows base scope chips for diagnostic completeness. |
| `frontend/src/test/LayoutPrimitives.test.tsx` | Test update | Updated the existing public chip test to assert the new no-duplication behavior (team/season/split base chips are absent in public mode; applied filters and derived date-range chips still render) and added a new test covering the all-base-scope collapse case (when only base scope chips would have rendered, the public context strip is omitted entirely). |
| `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_6_RETURN_PACKAGE.md` | Added return package | Records what changed, files changed, acceptance-criteria check, validation result, and scope discipline for Wave 6. |
| `outputs/frontend_copy_qa/20260521T025916Z/*` | Generated QA artifact | New frontend-copy QA report run after the rendering change. 125 / 125 rendered, 0 render failures, soft checks `480 / 0 / 0`. Per Wave 4's `outputs/` rule, this is a generated artifact under `outputs/<workflow>/<run_id>/` and is not a durable doc. |

No other files were created, modified, moved, or deleted.

## 3. What changed (substantive content)

### 3.1 QueryBar placeholder

The previous placeholder was `Type an NBA query…`. The new placeholder
is `Ask a stat-shaped question — e.g. Jokic recent form, top scorers
this season`. This:

- Keeps the search box first (no required tutorial, no category
  selector).
- Names the product surface in the placeholder (`stat-shaped question`)
  so first-time users see what kind of question the engine accepts.
- Shows two starter examples (`Jokic recent form`, `top scorers this
  season`) without taking real estate from the search field.
- Does not claim support outside the verified boundary; both examples
  are existing supported starter queries already shipped in
  `SampleQueries.tsx`.

### 3.2 EmptyState copy

The first-run description was extended with one short sentence:

> Type a question above, or pick one from the starter queries to see how
> it answers.

This directs the user to either path (search-first or starter-pick)
without forcing onboarding. The existing capabilities grid (Players /
Teams / History) and `First run` eyebrow badge are unchanged. No
layout change, no new required surface.

### 3.3 Public answer context duplication audit

The audit follows the explicit POST §4 working rule:

```text
Put essential scope in the answer when natural.
Show only non-obvious or trust-relevant context separately.
Do not duplicate the answer with chips.
```

Concretely, `ResultContextSummary` now applies a base-scope filter
after the chip set is built:

```tsx
const BASE_SCOPE_CHIP_KEYS: ReadonlySet<string> = new Set([
  "player",
  "players",
  "team",
  "teams",
  "season",
  "opponent",
  "split",
]);

const contextChips = allContextChips.filter(
  (chip) => !BASE_SCOPE_CHIP_KEYS.has(chip.key),
);
```

The keys were chosen by inspecting `buildContextChips` in
`ResultEnvelope.tsx`. They are exactly the entity chips that the public
answer hero already names verbatim in supported routes:

- `entity_summary` patterns name the player (and season if present).
- `leaderboard` patterns name the metric and the leader's identity.
- `comparison` patterns name both subjects.
- `record` / `playoff_history` patterns name the team (and opponent for
  matchup cases).
- `split` patterns name the subject and split type in the hero
  sentence.

What is **not** filtered, and continues to render in the public chip
strip:

- Applied filters (variant `accent`): e.g. `Last 10 games`,
  `Opp PTS <= 100`, `Triple Double`, `Special Event`. These add
  non-obvious filter scope that the hero sentence cannot always carry.
- Derived context items (variant `neutral`): `Interpreted as ...`,
  `Date range Apr 1–12, 2026`, `Season range 2010-11 to 2019-20`,
  `Metric ...`, `Window ...`, `Opponent group ...`, `Included
  opponents ...`, generic `Filter ...` chips. These are the
  trust-relevant scope items POST §4 explicitly calls out as
  non-obvious and worth keeping.
- Material caveats: e.g. `Round-level data is unavailable before
  2001-02 ...`. These already render as a separate caveats block under
  the chip strip and are unchanged.

If, after the base-scope filter, no chips remain and no caveats remain,
`ResultContextSummary` returns `null` (existing behavior, lifted from
the original `contextChips.length === 0 && caveatItems.length === 0`
guard). The new test covers this collapse explicitly.

### 3.4 Debug, /review, /visual-qa, and feedback payload diagnostics

Unchanged. Specifically:

- The debug `ResultEnvelope` (rendered only when `?debug=1`) calls
  `buildContextChips` with `includeDerivedContext=false` and renders
  the resulting chip row inside `ResultEnvelopeShell`. It still
  includes base scope (`player`, `team`, `season`, `opponent`,
  `split`) chips for diagnostic completeness — only the **public**
  `ResultContextSummary` filters those out.
- The debug result actions panel (`Result` eyebrow, `Query output`
  title, `Copy Query`, `Copy JSON`) is unchanged.
- `Details` disclosure on the public result still exposes route,
  status, result reason, applied filters, notes, caveats, and the
  raw JSON. The existing FirstRun test at lines 263–313 of
  `frontend/src/test/FirstRun.test.tsx` continues to pass: public mode
  hides route/query-class/status/reason/JSON/dev chrome by default;
  toggling `Details` restores them.
- `/review` (`ReviewPage`) and `/visual-qa` (`VisualQaPage`) routes
  are not touched.
- Query feedback payload generation
  (`queryFeedbackPayload.ts`) is not touched. Feedback continues to
  carry the full diagnostic context regardless of display mode.

### 3.5 No backend / parser / routing / result-contract / QA-corpus changes

None. Specifically:

- No file under `src/nbatools/` was modified.
- No parser rule, route registration, or result contract was modified.
- The raw QA corpus (`outputs/raw_query_answer_qa/.../`) and the
  frontend-copy QA corpus (`docs/planning/raw-product/...` /
  `tools/...`) selection were not modified. The new
  `outputs/frontend_copy_qa/20260521T025916Z/` directory is a freshly
  generated *report* run against the existing corpus, not a corpus
  change.
- `Makefile`, `pyproject.toml`, deployment scripts, R2 sync, smoke
  harness, and the feedback endpoint are not touched.

### 3.6 No required onboarding or required category selector

Per Wave 6 stop conditions:

- No tutorial, required walkthrough, or modal is added.
- No required category selector is added before the search box.
- The search box is still the first focusable element in the primary
  workspace; `autoFocus` and the existing Cmd/Ctrl-K shortcut are
  preserved.
- The optional collapsible "What can I ask?" helper was considered but
  intentionally **not** added in this wave because the existing
  starter-queries panel already serves that role and adding another
  collapsible surface would not be lightweight. If a homepage helper
  is later wanted, it should be added as a separate scoped pass.

## 4. Acceptance-criteria check

From `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5 Wave 6 acceptance
criteria:

| Criterion | Status | Evidence |
| --- | --- | --- |
| Homepage shows search box first, helpful placeholder, strong starter examples, and optional collapsible help only | met | Search box is first (unchanged); placeholder now reads `Ask a stat-shaped question — e.g. Jokic recent form, top scorers this season`; strong starter examples already render in `SampleQueries`; no required help, no required category selector, no required tutorial. |
| Public result hero does not duplicate scope already stated in the answer sentence; non-obvious trust/scope context (data freshness, filter window, "without LeBron James") remains visible | met | `ResultContextSummary` filters base-scope chips (`player`, `players`, `team`, `teams`, `season`, `opponent`, `split`). Applied filters (`Last 10 games`, `Triple Double`, `Opp PTS <= 100`, etc.), date ranges, included-opponents groups, and material caveats still render. Data freshness continues to render in the dedicated `FreshnessStatus` panel. |
| Debug, `/review`, `/visual-qa`, and feedback payloads remain unchanged | met | Debug `ResultEnvelope` chip row (only shown under `?debug=1`) is unmodified and still carries base scope. `/review` (`ReviewPage`) and `/visual-qa` (`VisualQaPage`) routes are not touched. `queryFeedbackPayload.ts` is not touched. The FirstRun debug test asserting `entity_summary + game_log`, `API online`, `Dev Tools`, `Copy JSON`, `Raw response` continues to pass. |

From the user's explicit Wave 6 task list:

| Required item | Status |
| --- | --- |
| Search box first | met (unchanged) |
| No required tutorial | met (none added) |
| No required category selector | met (none added) |
| Improved placeholder / starter examples / helper copy | met (QueryBar placeholder + EmptyState description) |
| Optional/collapsible "What can I ask?" only if lightweight | met (not added; starter queries panel already covers this) |
| Audit public answer context for scope duplication | met (`BASE_SCOPE_CHIP_KEYS` filter in `ResultContextSummary`) |
| Preserve non-obvious trust/scope context | met (applied filters, derived context items, caveats unchanged) |
| Preserve debug mode, `/review`, `/visual-qa`, feedback payload diagnostics | met (none modified) |
| No backend behavior change | met |
| No parser/routing behavior change | met |
| No result-contract change | met |
| No raw QA corpus change | met (a fresh QA *report* was run against the unchanged corpus) |
| No required onboarding | met |
| No required category selector | met |
| No claim of support outside the verified boundary | met (placeholder examples are existing supported queries) |
| Wave 6 return package created | met (this file) |

## 5. Validation result

### 5.1 Targeted frontend tests for changed components

Command: `npx vitest run src/test/LayoutPrimitives.test.tsx src/test/FirstRun.test.tsx --no-file-parallelism`.

Result: **2 files passed, 35 tests passed.**

```text
 Test Files  2 passed (2)
      Tests  35 passed (35)
   Duration  15.70s
```

Coverage:

- `LayoutPrimitives.test.tsx` covers the updated `ResultContextSummary`
  behavior (no base-scope duplication; non-obvious context retained;
  collapse when only base-scope chips would have rendered) and the
  debug `ResultEnvelope` chip row (still includes base scope).
- `FirstRun.test.tsx` covers the homepage flow: starter-query keyboard
  flow, command-palette focus shortcut, query history recall, Escape
  to clear, debug vs public display modes, loading preview, retry
  paths, and the public-mode result strip assertion
  (`expect(screen.getByLabelText("Result context")).toHaveTextContent("Last 5 games")`).

### 5.2 Full frontend test suite

Command: `npx vitest run --no-file-parallelism` (from `frontend/`).

Result: **24 files passed, 1 file failed (`src/test/AppTheming.test.tsx`).
350 tests passed, 2 tests failed.**

The two failures in `AppTheming.test.tsx` (`applies scoped team
variables to single-team result surfaces` and `keeps multi-team results
neutral`) both wait for `screen.getByText("Result")` after submitting
a query in public mode. The `Result` eyebrow is only rendered in
`?debug=1` mode (App.tsx debug branch, around line 622); the public
default does not render that eyebrow. **These two failures reproduce
on the unmodified `main` branch** (verified by stashing the Wave 6
diff and re-running the same test file — same two failures, same line
numbers). They are pre-existing on `main`, not caused by this wave,
and live entirely outside the surfaces Wave 6 touched. They are
flagged here for visibility but are out of scope for Wave 6.

### 5.3 `npm run qa:frontend-copy`

Command: `npm run qa:frontend-copy` (writes a fresh frontend-copy QA
report because public copy and rendering changed).

Result: **4 / 4 tests passed; 125 / 125 cases rendered; 0 render
failures; 480 / 0 / 0 soft checks (pass / fail / not-checked).**

```text
 Test Files  1 passed (1)
      Tests  4 passed (4)
   Duration  12.33s
```

New report artifact:
`outputs/frontend_copy_qa/20260521T025916Z/frontend_copy_report.md`.
Summary block:

```text
- Run ID: 20260521T025916Z
- Source backend run: outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl
- Selected cases: 125
- Rendered successfully: 125
- Render failures: 0
- Missing backend records: 0
- Soft check pass/fail/not checked: 480/0/0
- Cases needing manual review: 125
```

The earlier release-package frontend-copy report
(`outputs/frontend_copy_qa/20260518T175548Z/frontend_copy_report.md`)
is preserved unchanged for historical comparison; the Wave 6 run is a
new generated artifact, not a replacement.

### 5.4 `npm run build`

Command: `npm run build` (from `frontend/`).

Result: **Build succeeded.** TypeScript build passed
(`tsc -b`); Vite build emitted three production assets:

```text
../src/nbatools/ui/dist/index.html                   0.77 kB │ gzip:   0.41 kB
../src/nbatools/ui/dist/assets/index-BiDRvCEu.css   79.95 kB │ gzip:  13.43 kB
../src/nbatools/ui/dist/assets/index-BEkMlUwV.js   561.04 kB │ gzip: 163.73 kB
```

The Vite large-chunk warning (`Some chunks are larger than 500 kB
after minification`) is the existing/expected warning recorded in
`RAW_PRODUCT_RELEASE_PACKAGE.md` §2 (`Frontend build:
PASS_WITH_EXISTING_WARNING`) and is unchanged by this wave.

### 5.5 `npm run lint`

Command: `npm run lint` (from `frontend/`).

Result: **0 errors, 1 warning (pre-existing).**

```text
/Users/brenthibbitts/nba_tools/frontend/src/ReviewPage.tsx
  159:27  warning  The ref value 'abortControllersRef.current' ...
✖ 1 problem (0 errors, 1 warning)
```

The single warning is the existing
`frontend/src/ReviewPage.tsx`
`react-hooks/exhaustive-deps` warning recorded in
`RAW_PRODUCT_RELEASE_PACKAGE.md` §2 (`Frontend lint:
PASS_WITH_EXISTING_WARNING`). Wave 6 did not touch `ReviewPage.tsx`.

### 5.6 `git diff --check`

Result: **clean** (no whitespace errors flagged).

## 6. Commands run for validation

```text
npx vitest run src/test/LayoutPrimitives.test.tsx src/test/FirstRun.test.tsx --no-file-parallelism
npx vitest run --no-file-parallelism
npm run qa:frontend-copy
npm run build
npm run lint
git diff --check
```

## 7. Scope discipline

What this wave intentionally did not do:

- Did not change parser, routing, backend, structured-result, query
  service, deployment, R2 sync, smoke harness, or feedback endpoint
  behavior.
- Did not change result contracts or raw QA corpus expectations.
- Did not modify the existing frontend-copy QA corpus selection; it
  re-ran the harness against the same selection to record a fresh
  report for the new rendering.
- Did not modify the debug `ResultEnvelope` chip row or the
  `?debug=1` display mode; base scope still renders in debug.
- Did not touch `/review` (`ReviewPage.tsx`) or `/visual-qa`
  (`VisualQaPage.tsx`).
- Did not modify `queryFeedbackPayload.ts` or the feedback endpoint
  payload shape.
- Did not add a required tutorial, required category selector, or any
  required onboarding surface.
- Did not add a new top-level homepage section or collapsible helper;
  the starter-queries panel already covers the "What can I ask?"
  role.
- Did not rebrand or rename the product, the CLI, the API, or any
  visible surface.
- Did not modify the layout, app shell, header, freshness panel,
  saved queries, query history, or DevTools surfaces.
- Did not touch any `docs/` file. Wave 4's "Return Packages" subsection
  of `docs/index.md` is unchanged; Wave 5's `README.md` is unchanged.
- Did not move, rename, archive, or delete any file under
  `return_packages/`, `docs/`, `outputs/`, or anywhere else.
- Did not redeclare release status.

Pre-existing items flagged here for visibility (not changed by Wave
6):

- `src/test/AppTheming.test.tsx` has two failing tests on the
  unmodified `main` branch (`applies scoped team variables to
  single-team result surfaces`, `keeps multi-team results neutral`),
  both blocked on `screen.getByText("Result")` which only renders in
  debug mode. Filing or fixing this is out of scope for Wave 6.
- The `react-hooks/exhaustive-deps` warning in
  `frontend/src/ReviewPage.tsx` and the Vite large-chunk build warning
  remain the same pre-existing warnings recorded in the release
  package.

## 8. Wave 6 closes the post-review hardening plan

Waves 1–5 were docs/policy only. Wave 6 is the first wave to touch
frontend source. With Wave 6 complete:

- Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion Rules.
  Done (Wave 1 return package; new policy docs under
  `docs/planning/raw-product/`).
- Wave 2 — Data/R2 Promotion Checklist Hardening. Done (Wave 2 return
  package; `docs/operations/deployment.md` updated).
- Wave 3 — Feedback Review Cadence. Done (Wave 3 return package;
  `docs/operations/query_feedback_review.md` updated).
- Wave 4 — Docs/Return Package Taxonomy. Done (Wave 4 return package;
  `docs/index.md` updated).
- Wave 5 — README/Product Positioning Refresh. Done (Wave 5 return
  package; `README.md` updated).
- Wave 6 — Lightweight Product Promise/Homepage Pass. Done (this
  return package).

Deferred / explicit non-goals from
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §7 remain deferred:

- `natural_query.py` extraction execution.
- Required category selector before search.
- Branding / name change.
- Admin dashboard or mutable triage overlay for feedback.
- Automatic corpus mutation from feedback.
- Execution of return-package archive moves (Wave 4 documented the
  rules; the archive sweep is a separate later pass).
- Broad new feature support outside the current verified boundary.

A reasonable next pass — outside the hardening plan — would be to
address the two pre-existing `AppTheming.test.tsx` failures observed
during Wave 6 validation, since they predate this work but were
surfaced by the full-suite validation.
