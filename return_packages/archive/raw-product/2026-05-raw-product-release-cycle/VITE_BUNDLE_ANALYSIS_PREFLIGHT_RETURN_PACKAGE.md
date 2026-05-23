# Vite Bundle Analysis Preflight Return Package

## Status

- Mode: preflight only.
- Preflight date: 2026-05-22.
- Production code changed: no.
- Frontend rendering, routing, and Vite config changed: no.
- Backend/parser/result contracts changed: no.
- QA corpus changed: no.

## What Was Created

- `docs/planning/raw-product/VITE_BUNDLE_ANALYSIS_PREFLIGHT.md`
- `return_packages/raw-product/VITE_BUNDLE_ANALYSIS_PREFLIGHT_RETURN_PACKAGE.md`
- `docs/index.md` entry for the new planning doc

## Build Baseline

Validation command:

```text
npm --prefix frontend run build
```

The build passed on 2026-05-22 with `vite v8.0.8`, 140 transformed modules,
one JS asset, one CSS asset, and the existing large-chunk warning.

| Asset | Build output size | Gzip size |
| --- | --- | --- |
| `index.html` | 0.77 kB | 0.41 kB |
| `assets/index-BiDRvCEu.css` | 79.95 kB | 13.43 kB |
| `assets/index-Wi0lNp-j.js` | 565.50 kB | 164.93 kB |

Exact warning:

```text
[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

## Main Findings

| Area | Finding |
| --- | --- |
| Entry graph | `frontend/src/main.tsx` statically imports public `App`, internal `ReviewPage`, and internal `VisualQaPage`. Path selection is runtime only today. |
| Current output | The build emits one JS chunk, so `/`, `/review`, and `/visual-qa` currently share the same entry bundle. |
| Screenshot libraries | `ReviewPage` and `VisualQaPage` statically import `reviewScreenshots.ts`; that helper statically imports `html-to-image` and `jszip`, and both implementations appear in the emitted JS. |
| Visual QA data | `visualQaCases.ts` imports `qa/frontend_visual_qa_corpus.json`; the JSON was 21,045 bytes and its case text appears in the emitted JS because `VisualQaPage` is eager. |
| Review fixture data | Review fixtures are fetched from `/api/dev/fixtures`, not bundled as corpus data. |
| Result renderers | `ResultRenderer.tsx` statically imports every current result pattern renderer, so result families are all eager in the public app graph. |
| Public debug surface | `App.tsx` statically imports debug/dev UI hidden from default public display mode. This is a later candidate, not the lowest-risk first split. |
| Static serving | FastAPI and Vercel already serve generated `/assets/...` files generally, so dynamic chunks should fit the existing asset boundary. Production-like route smoke is still required after any split. |

## Recommendation

The first execution wave should be a measured route-level split for internal
routes only:

1. lazy load `/review` from the frontend route entrypoint
2. lazy load `/visual-qa` from the frontend route entrypoint
3. keep public `App`, result rendering, API paths, Vite config, backend, and
   result contracts unchanged
4. capture before/after Vite asset output and whether the warning remains

Do not start with `manualChunks`, warning-limit changes, result-renderer
splitting, or screenshot helper splitting. Route splitting should first remove
the clearly internal page/corpus/screenshot path from public startup. If the
warning remains after that measurement, use the new chunk graph to choose the
next step.

## First-Wave Files

Likely changes:

- `frontend/src/main.tsx`
- `frontend/src/test/VisualQaPage.test.tsx` or a focused root-view route test
- a wave return package with before/after asset evidence

Expected unchanged in the first wave:

- `frontend/vite.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/lib/reviewScreenshots.ts`
- result pattern components

## First-Wave Validation

```text
npm --prefix frontend run build
npm --prefix frontend test -- src/test/ReviewPage.test.tsx src/test/VisualQaPage.test.tsx
npm --prefix frontend run lint
git diff --check
```

Production-like route smoke after build:

- `/`
- `/?debug=1`
- `/review`
- `/visual-qa`

The smoke must prove that split route chunks load from `/assets`, public query
results still render on `/`, and internal screenshot controls still appear on
the internal routes.

## Stop Conditions

Stop and re-plan if the route split:

- changes public result rendering, routing behavior, API/result contracts, or
  QA corpus behavior
- requires Vite config changes before its size effect can be measured
- breaks FastAPI deep-route loading or generated asset loading
- leaves the public warning unchanged after internal route chunks are visibly
  separated

The final stop condition means the route split was measured successfully and a
new candidate should be chosen from the after-split bundle graph.

## Files Reviewed

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

## Preflight Validation

| Command / check | Result |
| --- | --- |
| `npm --prefix frontend run build` | Passed with the captured existing Vite large-chunk warning. |
| `git diff --check` | Passed. |
| Untracked markdown whitespace checks | `git diff --no-index --check /dev/null <new-file>` produced no whitespace diagnostics for the two new Markdown files. |
| Markdown lint availability | Not run. No `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH. |
