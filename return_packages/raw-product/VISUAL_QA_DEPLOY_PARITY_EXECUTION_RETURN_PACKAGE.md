# Visual QA Deploy Parity Execution Return Package

## 1. Executive summary

- What changed: added `/visual-qa` to the same deployed and local SPA shell routing path used by `/review`.
- `/visual-qa` deployed parity status: implemented in `vercel.json` by rewriting `/visual-qa` to `/api/review`.
- `/review` regression status: preserved; local API and Vercel function tests still pass.
- Production rendering changed? no.
- Backend query behavior changed? no.
- Tests added/updated: API shell route coverage now includes `/review` and `/visual-qa`; Vercel function entrypoint coverage now includes `api.review`.
- Manual local validation: local production API shell returns 200 HTML for `/review` and `/visual-qa`; browser load of `/visual-qa` requested JS/CSS assets and issued 15 live `/query` POSTs.
- Deployed preview validation: not run; no preview URL was available in this execution.
- Remaining risk: deployed behavior depends on Vercel applying the inspected rewrite config; validate `/visual-qa` on the next preview URL.

## 2. Route behavior before/after

| Route | Before | After |
|---|---|---|
| `/review` | Local API route and Vercel rewrite served the SPA shell. | Unchanged; local API route and Vercel rewrite still serve the SPA shell. |
| `/visual-qa` local Vite | Vite route worked through `frontend/src/main.tsx`. | Unchanged; Vite route remains `http://127.0.0.1:5173/visual-qa` or the active Vite port. |
| `/visual-qa` local production API | No FastAPI route; local production API would 404. | `GET /visual-qa` serves the same SPA shell as `/review`. |
| `/visual-qa` deployed | No explicit Vercel rewrite; likely 404. | Rewrites to `/api/review`, serving the same internal SPA shell as `/review`. |

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `vercel.json` | Updated | Added `/visual-qa` rewrite to `/api/review`. |
| `src/nbatools/api.py` | Updated | Added local production `GET /visual-qa` route using the existing internal UI shell helper. |
| `tests/test_api.py` | Updated | Proves `/review` and `/visual-qa` both return the HTML shell. |
| `tests/test_vercel_functions.py` | Updated | Keeps `api.review` covered as a Vercel function entrypoint. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Updated | Records deploy parity, hidden/internal route policy, and local/Vite URLs. |
| `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` | Updated | Adds local production API capture URL alongside Vite dev URL. |
| `return_packages/raw-product/VISUAL_QA_DEPLOY_PARITY_EXECUTION_RETURN_PACKAGE.md` | Added | Records this execution wave and validation results. |

## 4. Tests / validation

- API route tests:
  `.venv/bin/pytest tests/test_api.py -k "review or visual"`
  Result: passed, `2 passed in 13.44s`.
- VisualQaPage tests:
  `npm test -- src/test/VisualQaPage.test.tsx`
  Result: passed, `1` file, `4` tests, duration `15.70s`.
- Vercel function tests:
  `.venv/bin/pytest tests/test_vercel_functions.py`
  Result: passed, `10 passed in 3.35s`.
- Vercel config inspection:
  `node -e "const fs=require('fs'); const c=JSON.parse(fs.readFileSync('vercel.json','utf8')); const r=c.rewrites.find((x)=>x.source==='/visual-qa'); console.log(JSON.stringify(r));"`
  Result: `{"source":"/visual-qa","destination":"/api/review"}`.
- Broader API route/static slice:
  `make PYTEST=.venv/bin/pytest test-api`
  Result: passed, `51 passed, 2792 deselected in 4.28s`.
- Frontend build:
  `npm run build`
  Result: passed. Output included `index.html`, `assets/index-C-OtNn3G.css`, and `assets/index-DhFSwvX9.js`; Vite emitted the existing large chunk warning.
- Frontend lint:
  `npm run lint`
  Result: passed with the existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- Manual local `/review`:
  `curl http://127.0.0.1:8000/review`
  Result: `HTTP/1.1 200 OK`, `content-type: text/html; charset=utf-8`, shell contained `<title>nbatools</title>`, `id="root"`, and built asset links.
- Manual local `/visual-qa`:
  `curl http://127.0.0.1:8000/visual-qa`
  Result: `HTTP/1.1 200 OK`, `content-type: text/html; charset=utf-8`, shell contained `<title>nbatools</title>`, `id="root"`, and built asset links.
- Manual local supporting routes:
  `/api/dev/fixtures` returned `HTTP/1.1 200 OK` with `402` fixtures; `/query` returned `HTTP/1.1 200 OK` with `ok=true`, `route=season_leaders`, and `sections=["leaderboard"]`; `/assets/index-C-OtNn3G.css` returned `HTTP/1.1 200 OK`, `text/css`.
- Manual browser `/visual-qa`:
  Safari loaded `http://127.0.0.1:8000/visual-qa` with document title `nbatools`. Uvicorn logs showed `GET /visual-qa 200`, built JS/CSS asset requests `200`, and `15` live `POST /query 200` requests. Safari's Apple Events JavaScript bridge was disabled, so DOM text scraping was unavailable.
- Deployed preview `/visual-qa`:
  Not run; no preview URL was available.
- `git diff --check`:
  Passed with no output.

## 5. Policy / exposure note

- `/visual-qa` is hidden/internal but accessible like `/review`.
- Any gating added? no.
- Any future gating recommended? only if `/review` receives equivalent gating or the product policy changes for internal QA surfaces.

## 6. Next recommendation

- Accept visual QA route parity.
- Validate `/visual-qa` on the next Vercel preview URL, then continue with the next corpus expansion, visual QA automation, or release checklist item.
