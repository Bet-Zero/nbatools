# Vite Internal Route Lazy Split Return Package

## Status

- Execution date: 2026-05-22.
- Goal: run the first measured bundle-improvement wave from
  `docs/planning/raw-product/VITE_BUNDLE_ANALYSIS_PREFLIGHT.md`.
- Public `App` behavior changed: no.
- Backend/parser/result contracts changed: no.
- QA corpus changed: no.
- Vite config changed: no.

## What Changed

The frontend root path selector still defaults to the eager public `App`.
Internal review routes now cross a small lazy route boundary:

- `/review` dynamically imports `ReviewPage`.
- `/visual-qa` dynamically imports `VisualQaPage`.
- `InternalRoutes.tsx` owns the `React.lazy` imports and the small
  `Suspense` fallback so `main.tsx` remains a thin route selector and passes
  the existing React Refresh lint policy.

Existing internal page and screenshot helper behavior stays unchanged. The
lazy route split changes when those modules load, not what they render.

## Files Changed

| File | Change |
| --- | --- |
| `frontend/src/main.tsx` | Keep public `App` eager and route internal paths through lazy route components. |
| `frontend/src/InternalRoutes.tsx` | Add the internal lazy route boundary and loading fallback. |
| `frontend/src/test/ReviewPage.test.tsx` | Cover lazy `/review` route resolution through the root selector. |
| `frontend/src/test/VisualQaPage.test.tsx` | Cover lazy `/visual-qa` route resolution by rendered page output. |
| `docs/planning/raw-product/VITE_BUNDLE_ANALYSIS_PREFLIGHT.md` | Mark Wave 1 complete and record after-build chunk evidence. |
| `docs/operations/ui_guide.md` | Document generated lazy chunks for internal routes under `/assets`. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | Replace stale frontend build/lint warning readiness notes. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | Replace stale frontend build/lint warning handoff notes. |
| `return_packages/raw-product/VITE_INTERNAL_ROUTE_LAZY_SPLIT_RETURN_PACKAGE.md` | Record this execution wave. |

## Before Build Output

Command:

```text
npm --prefix frontend run build
```

Baseline captured immediately before the code change:

| Asset | Build output size | Gzip size |
| --- | --- | --- |
| `index.html` | 0.77 kB | 0.41 kB |
| `assets/index-BiDRvCEu.css` | 79.95 kB | 13.43 kB |
| `assets/index-Wi0lNp-j.js` | 565.50 kB | 164.93 kB |

Vite transformed 140 modules and emitted the prior non-failing warning:

```text
[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

## After Build Output

Same build command after the route split:

| Asset | Build output size | Gzip size |
| --- | --- | --- |
| `index.html` | 0.94 kB | 0.45 kB |
| `assets/ReviewPage-Z-pFk4ZL.css` | 3.62 kB | 1.18 kB |
| `assets/VisualQaPage-DGMi8LNc.css` | 5.60 kB | 1.65 kB |
| `assets/index-0fDmR5Fb.css` | 34.01 kB | 6.18 kB |
| `assets/ResultRenderer-Coq2NU9r.css` | 36.72 kB | 6.15 kB |
| `assets/ReviewPage-BR9gxWuv.js` | 15.22 kB | 4.88 kB |
| `assets/VisualQaPage-C0jwqxgA.js` | 27.23 kB | 7.90 kB |
| `assets/reviewScreenshots-5kCdWxlh.js` | 109.84 kB | 34.00 kB |
| `assets/ResultRenderer-BGbnXNLL.js` | 183.98 kB | 49.45 kB |
| `assets/index-DxycShP5.js` | 231.04 kB | 71.94 kB |

Vite transformed 142 modules. The prior large-chunk warning did not appear.

The public entry JS moved from one 565.50 kB chunk to a 231.04 kB index chunk
plus the shared result-renderer chunk selected by the current public result
graph. Internal review/Visual QA code, their route CSS, and screenshot ZIP
dependencies now land in generated route/shared chunks instead of the old
single JS chunk.

## Route Smoke

Production-like shell:

```text
.venv/bin/uvicorn nbatools.api:app --host 127.0.0.1 --port 8017
```

A headless Playwright browser loaded each route after the built UI was served
by FastAPI:

| Route | Result | `/assets` evidence |
| --- | --- | --- |
| `/` | Passed. Public root rendered. | Index and shared result-renderer JS/CSS returned `200`. No internal page chunk was requested. |
| `/?debug=1` | Passed. Public debug root rendered. | Index and shared result-renderer JS/CSS returned `200`. No internal page chunk was requested. |
| `/review` | Passed. Parser Review page rendered. | `ReviewPage-BR9gxWuv.js`, `ReviewPage-Z-pFk4ZL.css`, and `reviewScreenshots-5kCdWxlh.js` returned `200` from `/assets`. |
| `/visual-qa` | Passed. Frontend Visual QA page rendered. | `VisualQaPage-C0jwqxgA.js`, `VisualQaPage-DGMi8LNc.css`, and `reviewScreenshots-5kCdWxlh.js` returned `200` from `/assets`. |

FastAPI/Vercel asset behavior did not need code changes. The split chunks use
the existing generated `/assets/...` boundary.

## Validation Results

| Command | Result |
| --- | --- |
| `npm --prefix frontend run build` | Passed. Prior Vite large-chunk warning cleared. |
| `npm --prefix frontend test -- src/test/ReviewPage.test.tsx src/test/VisualQaPage.test.tsx` | Passed: 2 test files, 16 tests. |
| `npm --prefix frontend run lint` | Passed. |
| Production-like Playwright route smoke | Passed for `/`, `/?debug=1`, `/review`, and `/visual-qa`; lazy chunks loaded from `/assets` with `200` responses. |
| `git diff --check` | Passed. |
| Untracked file whitespace checks | `git diff --no-index --check /dev/null <new-file>` produced no whitespace diagnostics for `InternalRoutes.tsx` or this return package. |

## Release Impact

This is a frontend loading-boundary improvement. It does not change public
result behavior, query behavior, parser/routing behavior, backend behavior,
result contracts, QA corpus expectations, or screenshot helper behavior.

The previous release/readiness note about the existing Vite large-chunk warning
is no longer current after this wave. The warning cleared without Vite config,
`manualChunks`, or warning-limit changes.

## Next Bundle Step

Stop here unless runtime performance evidence or a new build warning justifies
another bundle wave. If bundle work resumes, measure the after-wave graph first
before choosing among:

- deferring screenshot/download helper loading inside the internal pages
- separating public debug-only surfaces from default public startup
- splitting result patterns, with explicit loading behavior for public answers
