# Visual QA Deploy Parity Preflight Return Package

## 1. Executive summary

- Recommended policy: Option A — Deploy `/visual-qa` alongside `/review` with explicit route fallback.
- Why: `/visual-qa` is already a built SPA route and calls only the public `/query` API. The only missing deploy piece is host routing/fallback, not frontend or backend query behavior.
- Production code changed? no
- Tests changed? no
- Docs changed? no

## 2. `/review` vs `/visual-qa` route comparison

| Area                          | `/review`                                                                           | `/visual-qa`                                                                      | Gap                                                        |
| ----------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Frontend routing registration | `frontend/src/main.tsx` maps normalized path `"/review"` to `<ReviewPage />`        | `frontend/src/main.tsx` maps normalized path `"/visual-qa"` to `<VisualQaPage />` | both pages are included in SPA route selector              |
| Local backend route           | `src/nbatools/api.py` defines `GET /review` and serves the UI shell                 | no `GET /visual-qa` route exists in `src/nbatools/api.py`                         | local production server (`uvicorn`) would 404 `/visual-qa` |
| Deployed rewrite              | `vercel.json` rewrites `/review` to `/api/review`                                   | no rewrite for `/visual-qa`                                                       | deployed site will not reach the SPA for `/visual-qa`      |
| Bundle inclusion              | Page component imported in `frontend/src/main.tsx`, included in build               | Page component imported in `frontend/src/main.tsx`, included in build             | no gap                                                     |
| Dev-only imports              | none; `VisualQaPage` imports `qa/frontend_visual_qa_corpus.json` and `./api/client` | none                                                                              | no gap                                                     |
| Data source                   | live `/query` responses from backend                                                | live `/query` responses from backend                                              | no gap                                                     |

## 3. Deployment/static fallback findings

- Current deployed/static behavior: `vercel.json` currently rewrites `/` to `/api`, `/review` to `/api/review`, and routes known API/static asset paths explicitly. There is no SPA catch-all fallback for arbitrary routes.
- Whether `/visual-qa` is covered: no. `/visual-qa` is not rewritten, so on Vercel it will be treated as a static file path and likely return 404 unless an explicit rewrite is added.
- Required rewrite/fallback if any: add `/visual-qa` rewrite to the same UI shell delivery path as `/` or `/review`.
- Is `/review` specially handled somewhere? yes: `vercel.json` has a dedicated rewrite from `/review` to `/api/review`.
- Does Vercel/serverless routing treat `/visual-qa` as an API route or static route incorrectly? It is currently not handled; it would be attempted as a static route and fail because no matching file exists.

## 4. API/data compatibility findings

- Query execution path: `/visual-qa` uses `postQuery(caseItem.query)` in `frontend/src/VisualQaPage.tsx`, which sends `POST /query` via `frontend/src/api/client.ts`.
- Does it require `/api/dev/fixtures` or only the 15-case manifest? only the 15-case manifest. It does not call `/api/dev/fixtures`.
- Does it use repo-local YAML/TS manifest in a way that works in production build? It imports `qa/frontend_visual_qa_corpus.json` from `frontend/src/visualQaCases.ts`; that is a repo-local JSON manifest. The YAML corpus is not parsed at runtime, so the old YAML parsing crash is not present in current runtime code.
- Would deployed backend data match the latest local raw QA behavior? Yes, because it relies on the same deployed `/query` backend as normal product pages. The live query behavior is the real backend path.
- Are there environment/base URL differences that would break `/visual-qa` but not `/review`? No. Both use relative same-origin fetches to `/query`, so base URL handling is identical.

## 5. Gating options

| Option                                 | Pros                                                                                                                 | Cons                                                                                                              | Risk                                                                | Recommendation                                                                          |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Option A — Deploy alongside `/review`  | Simple; consistent with existing `/review` internal route; no new backend or API surface; only routing change needed | Exposes another hidden internal QA route on production                                                            | Low, if the team already accepts `/review` as hidden-but-accessible | Recommended if the current product posture already allows `/review` on deployed site    |
| Option B — Gate behind dev/review mode | Safer if the team wants fewer public QA entrypoints; avoids accidental discovery                                     | Requires new gating mechanism or preview-only routing; more implementation work                                   | Moderate, but more secure than open route                           | Recommended if the organizational policy is to keep QA tooling non-public               |
| Option C — Keep local-only             | Simplest to preserve current safety; no deploy changes                                                               | Loses parity with `/review`; local-only QA decreases visibility and makes visual baseline capture less convenient | Lowest exposure                                                     | Use only if the team decides this QA surface must never be deployed without auth/gating |

## 6. Recommended execution scope

- Exact goal: make `/visual-qa` reachable from deployed site with the same host routing model as `/review`, while preserving current internal QA exposure semantics.
- Files likely to change:
  - `vercel.json` — add rewrite for `/visual-qa` to `/api` or `/api/review`
  - `src/nbatools/api.py` — add `GET /visual-qa` local UI shell route for parity with `uvicorn`/local production server
  - optional: `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` or internal QA docs to mention deploy parity and hidden route status
- Tests to add:
  - frontend route selection or smoke test validating `resolveRootView("/visual-qa")` returns `VisualQaPage`
  - local API test verifying `GET /visual-qa` returns UI HTML if a local production server route is added
  - deployment config smoke test for `vercel.json` rewrite semantics if the test harness supports it
- Manual validation:
  1. `cd frontend && npm run build`
  2. Run local production API: `uvicorn nbatools.api:app --reload`
  3. Open `http://127.0.0.1:8000/visual-qa` and confirm page loads and begins executing the 15 cases.
  4. In deployed preview, verify `/visual-qa` returns the SPA shell and no 404.
- Stop conditions:
  - `/visual-qa` loads the React page from deployed site
  - the page can run live `/query` cases
  - the route is not accidentally exposed as a new API endpoint beyond the existing internal QA surface

## 7. Validation performed

- Inspected `frontend/src/main.tsx`, `frontend/src/VisualQaPage.tsx`, `frontend/src/ReviewPage.tsx`, `frontend/src/visualQaCases.ts`, `frontend/src/api/client.ts`
- Inspected `frontend/vite.config.ts`, `frontend/package.json`, `vercel.json`
- Inspected `src/nbatools/api.py`, `api/review.py`, `api/index.py`, `api/ui_fallback_asset.py`, and `src/nbatools/vercel_functions.py`
- Confirmed the YAML parse crash is already mitigated by importing `qa/frontend_visual_qa_corpus.json` instead of raw YAML text
- No production code or tests were modified as requested
