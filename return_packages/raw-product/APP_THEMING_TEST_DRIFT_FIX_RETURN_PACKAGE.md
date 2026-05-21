# App Theming Test Drift Fix — Return Package

## 1. Executive summary

- Task: Fix the two pre-existing `src/test/AppTheming.test.tsx`
  failures surfaced during Raw Product Hardening Wave 6 validation.
- Root cause: **test drift, not a production theming bug.** Both tests
  used `await waitFor(() => expect(screen.getByText("Result")).
  toBeInTheDocument())` as a wait gate for "result section is mounted".
  The `Result` text is a `SectionHeader` eyebrow that only renders in
  the debug result actions panel under `?debug=1` (see
  [App.tsx:611-625](frontend/src/App.tsx#L611-L625)). When the
  Front-facing Result UI Productization Wave 1 work made `/` default
  to public mode, that debug-only eyebrow stopped rendering on the
  default URL the tests use (`window.history.replaceState(null, "",
  "/")`). The actual theming logic — the `data-team-theme="<abbr>"`
  attribute and the `--team-primary` / `--team-secondary` CSS
  variables on the result section — is rendered in both display modes
  and has not regressed.
- Production code changed: **no.**
- Tests changed: **yes** — only the two wait gates in
  `src/test/AppTheming.test.tsx`. The actual theming assertions
  (`--team-primary: #007A33`, `--team-secondary: #BA9653`, no
  `[data-team-theme]` for multi-team results) are unchanged.
- Validation: full frontend test suite now passes 25 / 25 files,
  352 / 352 tests. Build, lint, and `git diff --check` clean.
- Release impact: none. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`. The previously documented
  `Frontend lint: PASS_WITH_EXISTING_WARNING` and
  `Frontend build: PASS_WITH_EXISTING_WARNING` evidence rows in
  `RAW_PRODUCT_RELEASE_PACKAGE.md` §2 remain accurate; the
  full-suite vitest evidence improves from "350 pass / 2 pre-existing
  failures" to a clean 352 / 352.

## 2. Root cause

Both failing tests submit a query in default (`/`, public) display
mode, then wait for `screen.getByText("Result")` before asserting on
the themed result surface. The string `Result` comes from
[App.tsx:621-625](frontend/src/App.tsx#L621-L625):

```tsx
<SectionHeader
  eyebrow="Result"
  title="Query output"
  actions={resultActions}
/>
```

That `SectionHeader` lives inside the `isDebugMode ? (...) : (...)`
ternary, so the `Result` eyebrow renders only when
[App.tsx:611](frontend/src/App.tsx#L611) `isDebugMode` is true. The
default route is public; `isDebugMode` is `false`; the `Result`
eyebrow never mounts; `waitFor` exhausts its timeout and both tests
fail with `Unable to find an element with the text: Result`.

The theming behavior the tests are meant to verify is unrelated:
[App.tsx:599-610](frontend/src/App.tsx#L599-L610) renders the result
section's `data-state-surface="result"` and `data-team-theme=
{teamTheme?.team.teamAbbr ?? undefined}` attributes and CSS-variable
style outside the `isDebugMode` branch, so the team theme is applied
in both display modes. The post-Wave-6 production code is correct;
only the wait gate was looking at the wrong element.

This is consistent with the Wave 6 return package §5.2 / §7
observation that the failures reproduced on unmodified `main` — they
pre-existed Wave 6 and were uncovered when the full suite was
exercised during Wave 6 validation.

## 3. Fix

Both tests were updated to wait on a stable, display-mode-independent
signal that the result section has mounted:

- **`applies scoped team variables to single-team result surfaces`** —
  now waits for `container.querySelector('[data-team-theme="BOS"]')`
  to be non-null. This is the exact element the test then asserts CSS
  variables on, so the wait gate is the strongest possible signal that
  the assertions will be meaningful.
- **`keeps multi-team results neutral`** — now waits for
  `container.querySelector("[data-state-surface='result']")` to be
  non-null. The result section's `data-state-surface` attribute is
  rendered in both display modes when a result is present. After the
  wait, the assertion that `container.querySelector("[data-team-theme]")
  === null` is unchanged.

Both wait gates target attributes set on the same `<section>` element
that the original tests cared about, so the tests still fail correctly
if either the team-theme rendering or the result-section mounting
breaks.

## 4. Production code change

None. The fix is test-only.

The team-theme rendering at [App.tsx:599-610](frontend/src/App.tsx#L599-L610),
the `resolveScopedTeamTheme` lib call at
[App.tsx:408-414](frontend/src/App.tsx#L408-L414), the
`teamThemedSurfaceClass` styling, and the CSS-variable application via
`teamThemeStyle` are all unchanged. The public vs debug ternary at
[App.tsx:611-694](frontend/src/App.tsx#L611-L694) is unchanged. No
component, design-system primitive, identity helper, or CSS module was
modified.

## 5. Tests changed

Only [frontend/src/test/AppTheming.test.tsx](frontend/src/test/AppTheming.test.tsx).
The two `waitFor(() => expect(screen.getByText("Result")).
toBeInTheDocument())` blocks were replaced with
display-mode-independent wait gates as described in §3. Comments were
added on each wait gate explaining why it does not look for the
"Result" eyebrow.

The two preserved assertion sets:

- Single-team test: `surface` is the `[data-team-theme="BOS"]`
  element; `expect(surface).toHaveStyle("--team-primary: #007A33")`
  and `expect(surface).toHaveStyle("--team-secondary: #BA9653")`
  unchanged.
- Multi-team test:
  `expect(container.querySelector("[data-team-theme]")).toBeNull()`
  unchanged.

No assertions were deleted, weakened, or replaced with a no-op.

## 6. Validation results

### 6.1 Targeted test file

Command: `npx vitest run src/test/AppTheming.test.tsx --no-file-parallelism`.

Result: **1 file passed, 2 tests passed.**

```text
 Test Files  1 passed (1)
      Tests  2 passed (2)
   Duration  5.31s
```

### 6.2 Full frontend test suite

Command: `npx vitest run --no-file-parallelism` (from `frontend/`).

Result: **25 files passed, 352 tests passed.**

```text
 Test Files  25 passed (25)
      Tests  352 passed (352)
   Duration  62.89s
```

This is a clean improvement from the Wave 6 baseline of
"24 / 25 files, 350 / 352 tests".

### 6.3 `npm run build`

Result: **build succeeded.** Three production assets emitted; the
pre-existing Vite large-chunk warning (recorded in
`RAW_PRODUCT_RELEASE_PACKAGE.md` §2 as
`Frontend build: PASS_WITH_EXISTING_WARNING`) is unchanged.

```text
../src/nbatools/ui/dist/index.html                   0.77 kB │ gzip:   0.41 kB
../src/nbatools/ui/dist/assets/index-BiDRvCEu.css   79.95 kB │ gzip:  13.43 kB
../src/nbatools/ui/dist/assets/index-BEkMlUwV.js   561.04 kB │ gzip: 163.73 kB
✓ built in 860ms
```

### 6.4 `npm run lint`

Result: **0 errors, 1 warning (pre-existing).** The single remaining
warning is the existing `frontend/src/ReviewPage.tsx`
`react-hooks/exhaustive-deps` warning recorded in
`RAW_PRODUCT_RELEASE_PACKAGE.md` §2 as `Frontend lint:
PASS_WITH_EXISTING_WARNING`. This task did not touch
`ReviewPage.tsx`.

### 6.5 `git diff --check`

Result: **clean** (no whitespace errors flagged).

## 7. Files changed

| File | Change type | Why |
| --- | --- | --- |
| `frontend/src/test/AppTheming.test.tsx` | Test fix | Replaced both `waitFor(screen.getByText("Result"))` wait gates with display-mode-independent waits on the result section's data attributes. Preserved all theming assertions. |
| `return_packages/raw-product/APP_THEMING_TEST_DRIFT_FIX_RETURN_PACKAGE.md` | Added return package | This file — records root cause, test-only fix, and validation. |

No other files were created, modified, moved, or deleted. No
production source file changed.

## 8. Release impact

None.

- Raw Product release status is unchanged:
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`.
- The team-theme behavior on the public result surface continues to
  match the existing release-package contract: single-team results
  carry `data-team-theme=<abbr>` plus per-team CSS variables;
  multi-team results stay neutral with no `data-team-theme`.
- The Wave 6 §5.2 note that flagged the two pre-existing failures for
  visibility is now resolved. The Wave 6 return package can be read
  alongside this one to confirm that the failure was test drift, not
  a Wave 6 regression and not a real theming bug.
- No durable docs change is required: `RAW_PRODUCT_RELEASE_PACKAGE.md`
  §2 already records frontend-lint and frontend-build as
  `PASS_WITH_EXISTING_WARNING`, which remains accurate. Future
  release docs that quote the full-suite vitest evidence can cite the
  clean 352 / 352 baseline established here.

## 9. Scope discipline

What this task intentionally did not do:

- Did not change any production source under `frontend/src/components`,
  `frontend/src/design-system`, `frontend/src/lib`, `frontend/src/hooks`,
  `frontend/src/App.tsx`, or any other production file.
- Did not change parser, routing, backend, structured-result, query
  service, deployment, R2 sync, smoke harness, feedback endpoint, or
  any `src/nbatools/` file.
- Did not change result contracts, raw QA corpus, frontend-copy QA
  corpus, or visual QA expectations.
- Did not change the public-mode answer-first contract; debug chrome
  remains gated behind `?debug=1`.
- Did not change Wave 6's `BASE_SCOPE_CHIP_KEYS` filter, the
  `EmptyState` copy, the `QueryBar` placeholder, or any other Wave 6
  surface.
- Did not modify the `/review` (`ReviewPage`) or `/visual-qa`
  (`VisualQaPage`) routes.
- Did not touch the `ReviewPage.tsx` `react-hooks/exhaustive-deps`
  warning. That is a separately scoped item if/when it is later
  addressed.
- Did not move, rename, archive, or delete any file.
- Did not redeclare release status.
