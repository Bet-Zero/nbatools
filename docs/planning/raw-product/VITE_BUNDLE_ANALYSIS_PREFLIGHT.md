# Vite Bundle Analysis Preflight

## 1. Scope

This is a preflight only. It does not change production code, frontend
rendering, frontend routing behavior, Vite config, parser/backend behavior,
result contracts, QA corpus files, or code-splitting behavior.

The current Raw Product deferred-work priority ranks the Vite large-chunk
warning as a medium-low, non-blocking follow-up. This preflight captures the
current build evidence and chooses the smallest next measurement wave before
any bundle implementation work starts.

Current recommendation:

1. Do not start with `manualChunks` or a warning-limit change.
2. Make the first execution wave a measured route-level split for internal
   `/review` and `/visual-qa` pages.
3. Compare emitted assets before deciding whether screenshot helper splitting,
   public debug-surface splitting, or result-renderer splitting is worth the
   added complexity.

Launch blocker found: no. The production build still succeeds.

## 2. Evidence Reviewed

Required inputs inspected:

- `docs/planning/raw-product/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/operations/ui_guide.md`
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/components/results/`
- `frontend/src/lib/reviewScreenshots.ts`
- `frontend/src/visualQaCases.ts`

Supporting context inspected:

- `qa/frontend_visual_qa_corpus.json`
- `frontend/src/test/ReviewPage.test.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `src/nbatools/api.py`
- `src/nbatools/api_ui.py`
- `api/assets.py`
- `vercel.json`
- `tests/test_api.py`
- `tests/test_vercel_functions.py`
- `docs/index.md`

## 3. Current Build Baseline

Command run on 2026-05-22:

```text
npm --prefix frontend run build
```

Vite reported `vite v8.0.8`, transformed 140 modules, and emitted one hashed
CSS asset plus one hashed JS asset:

| Asset | Build output size | Gzip size |
| --- | --- | --- |
| `index.html` | 0.77 kB | 0.41 kB |
| `assets/index-BiDRvCEu.css` | 79.95 kB | 13.43 kB |
| `assets/index-Wi0lNp-j.js` | 565.50 kB | 164.93 kB |

The emitted JS file on disk was 565,507 bytes. The emitted CSS file on disk
was 79,955 bytes. The build succeeded in 844 ms.

Exact Vite warning:

```text
[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

This is a minified-chunk threshold warning. The current output is also a real
single-chunk signal: there is no route or helper JS split in the captured
build.

## 4. Current Bundle Composition

### 4.1 Entry graph

`frontend/src/main.tsx` statically imports all three root views:

- `App` for public `/`
- `ReviewPage` for `/review`
- `VisualQaPage` for `/visual-qa`

`resolveRootView()` selects a page from `window.location.pathname`, but the
static imports mean that selection happens after all three page modules are in
the same entry graph. The build baseline confirms that Vite currently emits one
JS chunk for that graph.

### 4.2 Internal review and Visual QA pages

The internal pages are currently bundled into the public entry:

- `ReviewPage` is imported by `main.tsx`.
- `VisualQaPage` is imported by `main.tsx`.
- both pages reuse `ResultRenderer` and `ResultEnvelope`.
- both pages import `downloadReviewScreenshots` from
  `frontend/src/lib/reviewScreenshots.ts`.

`ReviewPage` does not bundle its fixture inventory. It fetches that inventory
from `/api/dev/fixtures` when the internal page runs.

`VisualQaPage` does bundle its corpus today. `frontend/src/visualQaCases.ts`
imports `qa/frontend_visual_qa_corpus.json`, and that JSON file was 21,045
bytes at inspection time. The built JS chunk contains the Visual QA case text
and case IDs because `VisualQaPage` is in the public entry graph.

### 4.3 Screenshot/download helper

`frontend/src/lib/reviewScreenshots.ts` statically imports:

- `toPng` from `html-to-image`
- `JSZip` from `jszip`

The built JS chunk contains `html-to-image` code and a `JSZip` implementation.
That is expected from the current graph: public `/` reaches the internal pages,
which reach the screenshot helper, even though public query users do not use
the internal screenshot ZIP controls.

The inspected installed package trees provide order-of-magnitude evidence, not
compiled contribution totals:

- `jszip/lib/*.js`: 136,565 bytes before Vite transforms/minification
- `html-to-image/lib/*.js`: 74,814 bytes before Vite transforms/minification

These are likely large avoidable public-entry contributors.

### 4.4 Result renderers and public debug surface

The public app statically imports `ResultRenderer`. `ResultRenderer` statically
imports every current pattern renderer:

- comparison
- entity summary
- fallback table
- game log
- leaderboard
- playoff history
- record
- rolling stretch
- split
- streak
- top performances

`routeToPattern()` chooses pattern configs at runtime, but every pattern module
and its imported presentation primitives/CSS are eager at build time. Result
renderers are therefore all in the main app graph today.

`App.tsx` also statically imports surfaces that are hidden from the default
public display mode, including `DevTools` and raw/debug result chrome. That is
a candidate boundary if later measurement says public-only startup remains too
large after internal routes are split. It is not the lowest-risk first change
because debug mode on `/` is a supported release behavior.

### 4.5 Likely contributor ranking

No repo-owned bundle visualizer is installed in the inspected frontend package,
so this preflight uses build output and import-graph evidence rather than
claiming exact per-module percentages.

| Rank | Contributor | Evidence | Public-entry avoidability |
| --- | --- | --- | --- |
| 1 | Screenshot ZIP/capture stack | `reviewScreenshots.ts` imports `html-to-image` and `jszip`; both implementations appear in the emitted JS. | High. Public `/` does not need internal screenshot download code. |
| 2 | React runtime and public app shell | `react` and `react-dom` are direct entry dependencies for every UI route. | Low for the current app. |
| 3 | Result renderer patterns, primitives, and table formatting | `ResultRenderer.tsx` statically imports every pattern renderer used by public answers. | Medium, but splitting result families affects public answer loading. |
| 4 | Internal review and Visual QA page modules/CSS | `main.tsx` imports both pages eagerly. | High for public startup. |
| 5 | Visual QA corpus | 21,045-byte JSON is imported through `VisualQaPage`. | High for public startup. |
| 6 | Public debug-only components | `App.tsx` statically imports debug surfaces hidden in default public mode. | Possible, but behavior-sensitive. |

## 5. Candidate Fixes

| Candidate | Expected value | Risk / cost | Disposition |
| --- | --- | --- | --- |
| Lazy load `/review` from `main.tsx` | Removes internal review page code and its screenshot-helper path from the public route graph when paired with the internal route split. | Requires a route-loading boundary and route-selection test updates. `/review` gains an async chunk load. | Recommended first wave. |
| Lazy load `/visual-qa` from `main.tsx` | Removes Visual QA page code, CSS, and visual corpus from the public route graph. | Requires the same route-loading boundary. `/visual-qa` gains an async chunk load. | Recommended first wave with `/review`. |
| Dynamically import screenshot/download helpers only when a download starts | Keeps `html-to-image` and `jszip` off an internal page load until the screenshot button is used. | Changes async control paths and existing screenshot mocks/tests on both internal pages. After route-level splitting, public-startup value is smaller. | Measure after the route split. |
| Separate debug/dev surfaces from default public `App` | Could keep `DevTools` and debug-only UI off default public `/`. | Must preserve `/?debug=1`, URL behavior, diagnostics, and test coverage. Size value is not measured yet. | Later candidate if route split is insufficient. |
| Split result renderers by pattern | Could defer uncommon public answer renderers. | Query responses could trigger new async loads; fallback/loading behavior becomes answer-path behavior. Shared primitives may still keep chunks coupled. | Not a first wave. |
| Configure vendor/manual chunks | Can create separate cacheable chunks or move the warning. | Does not itself remove initial bytes and can hide the high-value graph boundary. Needs Vite 8/Rolldown-aware config work. | Do not start here. |
| Raise `chunkSizeWarningLimit` | Silences the current warning. | No startup or maintainability benefit. | Do not do this for the first wave. |
| Do nothing | Keeps a passing build and avoids code-splitting complexity. | Public `/` continues to pay for clearly internal QA/download paths. | Acceptable if performance work is deprioritized, but not the recommended measured next step. |

## 6. Risk Analysis

### 6.1 Public startup impact

The current public entry includes internal QA pages, Visual QA case data, and
the screenshot ZIP/capture dependency path. Route-level internal-page splitting
should reduce public startup bytes without changing public answer rendering.
It may not clear the 500 kB warning if the public app, React runtime, and eager
result renderers still dominate the remaining chunk.

Result-renderer splitting would target more bytes if needed, but it also moves
loading behavior into the public answer path. That is a higher UX risk than
making internal tools load on demand.

### 6.2 Complexity added

The smallest route-level split adds dynamic imports and a route loading
boundary near `main.tsx`. It should not require Vite config or result contract
changes. Test coverage around `resolveRootView()` will need to stop assuming
that the Visual QA component type is a directly imported function if that
route becomes lazy.

Helper-level screenshot splitting adds more async state transitions to capture
buttons and test mocks. Manual chunking adds build configuration ownership
without addressing whether the public route graph is correct.

### 6.3 Build and deployment behavior

After dynamic imports, a successful Vite build should emit multiple hashed JS
assets under `src/nbatools/ui/dist/assets/`. That changes asset shape, not the
application contract.

Current serving paths already support more hashed assets:

- FastAPI serves `/`, `/review`, and `/visual-qa` with the same built HTML
  shell and mounts the whole `dist/assets` directory at `/assets`.
- Vercel names `src/nbatools/ui/dist` as output and has an `/assets/:path*`
  fallback rewrite through `api/assets.py`.
- `ui_asset_response()` serves arbitrary files under the generated UI asset
  tree and rejects path escapes.

Inference: split chunks should work with the existing FastAPI and Vercel asset
boundaries because they are additional `/assets/...` files, not new app
routes. That inference still needs production-like route smoke validation
after a split lands.

### 6.4 Test impact

Expected first-wave test impact:

- route-resolution assertions in `frontend/src/test/VisualQaPage.test.tsx`
  currently compare `resolveRootView("/visual-qa")` to the direct
  `VisualQaPage` component type.
- existing `ReviewPage` and `VisualQaPage` tests should keep verifying internal
  page behavior when those page modules are rendered directly.
- existing Python API tests prove the deep routes return the UI shell and that
  asset serving works, but they do not execute browser dynamic imports.

A future route split therefore needs both build output inspection and a
production-like browser/manual smoke of `/`, `/review`, and `/visual-qa`.

## 7. Recommended First Execution Wave

### 7.1 Scope

Make one measurement-oriented change:

- lazy load `ReviewPage` and `VisualQaPage` from the route entrypoint
- keep `App` as the default public root view
- keep all API paths, route paths, Vite config, result rendering, backend
  behavior, and contracts unchanged
- record before/after emitted asset sizes and whether the warning remains

Likely files:

| File | Expected change |
| --- | --- |
| `frontend/src/main.tsx` | Introduce the route-level dynamic imports and route loading boundary for internal pages. |
| `frontend/src/test/VisualQaPage.test.tsx` or a focused root-view test | Update direct component-type assumptions for lazy route selection while preserving `/visual-qa` routing coverage. |
| Follow-up return package | Record before/after build size evidence and route smoke evidence. |

`ReviewPage.tsx`, `VisualQaPage.tsx`, `reviewScreenshots.ts`, result pattern
components, and `frontend/vite.config.ts` should stay unchanged in that first
wave unless the measured route split exposes a narrowly necessary test hook or
route-loading defect.

### 7.2 Validation commands

Use build output as the primary metric:

```text
npm --prefix frontend run build
```

Run the focused internal-page coverage and lint for the entrypoint change:

```text
npm --prefix frontend test -- src/test/ReviewPage.test.tsx src/test/VisualQaPage.test.tsx
npm --prefix frontend run lint
git diff --check
```

Then use a production-like UI shell to open and query the three relevant route
families:

```text
/
/?debug=1
/review
/visual-qa
```

The smoke should verify that dynamic route chunks load from `/assets`, public
query results still render on `/`, and internal screenshot controls still
appear on the internal routes. If route asset serving changes are needed, add
or run the relevant API/Vercel asset tests before continuing.

### 7.3 Stop conditions

Stop and re-plan if the first route split:

- changes public result rendering, routing behavior, API/result contracts, or
  QA corpus behavior
- requires Vite config work before the route graph can be measured
- breaks deep-route loading under the FastAPI production-like shell
- causes internal route loading UX that cannot be handled with a small local
  entrypoint boundary
- leaves the public chunk warning unchanged and the after-build output shows
  that internal routes are already separated

The last case is not a failed measurement. It means the next decision should
use the after-split bundle graph, not pile `manualChunks`, screenshot helper
splitting, debug splitting, and result-renderer splitting into the same wave.

## 8. Preflight Decision

The current warning is real but not a correctness blocker. The current graph
also has a straightforward boundary error for public startup: internal review
and Visual QA pages are static entry imports.

The first execution wave should fix only that boundary and measure it. If the
warning clears and public JS bytes fall materially, stop there unless runtime
performance evidence asks for more. If it does not clear, use the new emitted
chunks to decide between helper-level screenshot splitting, public debug-surface
splitting, result-pattern splitting, or accepting the remaining public bundle
cost for now.
