# Phase N2 Frontend Deployment Inventory

> **Role:** Reconnaissance artifact for Phase N2 item 1. This records the
> current React/Vite deployment path and chooses the build strategy for item 2.

Measured from the primary worktree on 2026-05-02.

---

## Current Shape

The React source lives under `frontend/` and Vite is configured to build into
`src/nbatools/ui/dist/`.

Relevant current settings:

| Area | Current state | Deployment implication |
| --- | --- | --- |
| Vite output | `frontend/vite.config.ts` uses `outDir: "../src/nbatools/ui/dist"` | `src/nbatools/api_ui.py` already knows where to find `index.html` |
| Python package data | `pyproject.toml` includes `nbatools = ["ui/dist/**"]` | built UI files are available when present in the package/function bundle |
| Git ignore | root `.gitignore` ignores any `dist/` directory | generated UI assets are currently untracked local build output |
| Vercel function excludes | `vercel.json` excludes `frontend/**`, `data/**`, tests, docs, and caches from Python function bundles | frontend source and `node_modules` should not inflate function bundles; generated `src/nbatools/ui/dist/**` is not excluded |
| Root route | `/` rewrites to `api/index.py`, which calls `load_ui_html()` | root can serve the real UI once `index.html` exists in the bundle |
| Asset route | only `/assets/index-fallback.js` rewrites to a fallback function | Vite hashed assets such as `/assets/index-*.js` and `/assets/index-*.css` need a general deployed asset route |
| API calls | frontend uses same-origin `/health`, `/routes`, `/freshness`, `/query`, and `/structured-query` | no frontend API base-url rewrite is needed for preview or production |

The Phase N1 preview served the expected fallback because the deployed artifact
did not contain a Vite-built `src/nbatools/ui/dist/index.html`.

---

## Strategy Chosen For Item 2

Use a **Vercel build-time frontend build** and keep generated UI assets out of
git.

Item 2 should add a Vercel build command that runs the frontend install/build
before Python functions are packaged:

```bash
npm --prefix frontend ci && npm --prefix frontend run build
```

This keeps `src/nbatools/ui/dist/**` generated in the deployment workspace, not
committed. The existing Python UI loader can then read `index.html` from the
generated package path, while the function `excludeFiles` rules continue to
exclude `frontend/**` and `node_modules` from runtime bundles.

This strategy was chosen over committing `src/nbatools/ui/dist/**` because Vite
emits hashed asset filenames and committing build output would create frequent
generated-file churn. It was chosen over moving the Vite output to a separate
root-level static directory because the local FastAPI workflow and package-data
contract already expect `src/nbatools/ui/dist/`.

---

## Item 2 Punchlist

Item 2 should make these exact changes:

1. Add a top-level `buildCommand` to `vercel.json`:

   ```json
   "buildCommand": "npm --prefix frontend ci && npm --prefix frontend run build"
   ```

2. Add a Vercel function for UI static assets, for example `api/assets.py`,
   that serves files from `src/nbatools/ui/dist/assets/` with safe path
   validation and correct content types for `.js`, `.css`, `.svg`, `.map`,
   `.ico`, `.png`, `.jpg`, `.jpeg`, `.webp`, and `.json`.

3. Add root asset rewrites for generated UI files:

   - `/assets/(.*)` -> `/api/assets`
   - `/favicon.svg` -> a UI asset function or a dedicated file route
   - `/icons.svg` -> a UI asset function or a dedicated file route

   The existing `/assets/index-fallback.js` route may remain, but generated
   Vite assets must take precedence when the bundle exists.

4. Update tests for the shared UI/static helper and Vercel asset function:

   - built asset response succeeds when the file exists
   - missing asset returns `404`
   - path traversal returns `404`
   - fallback route still serves when no built bundle exists

5. Update operations docs with the deployed frontend build command and clarify
   that generated `dist/` files are build artifacts, not source.

6. Verify preview manually after merge:

   - `GET /` returns real React HTML, not fallback copy
   - `/assets/index-*.js` and `/assets/index-*.css` return HTTP `200`
   - `/health`, `/freshness`, and one `/query` still work

---

## Constraints And Risks

- Vercel must have Node and npm available during the project build. The command
  uses `npm --prefix frontend` so no root `package.json` is required.
- The build command adds a frontend dependency install step to every Vercel
  deploy. This is slower than the Phase N1 API-only deploy, but it keeps
  generated Vite output out of git.
- Runtime function bundles should still exclude `frontend/**`; only generated
  `src/nbatools/ui/dist/**` should be needed at runtime.
- `src/nbatools/api_ui.py` reads `index.html` directly and returns fallback
  HTML when missing. That fallback should remain for local checkouts and failed
  build-output cases.
- Serving assets through a Python function is acceptable for this friends-tier
  deployment, but it is not a CDN-optimized frontend architecture. If asset
  volume or latency becomes a problem, a later phase can move static files to a
  root/public static output path.
- The UI must remain a thin presentation layer. Same-origin API calls should
  stay in `frontend/src/api/client.ts`; query parsing, filtering, and analytics
  must remain in the Python engine/API.

---

## Rollback Path

If the build-time strategy fails in Vercel, remove the `buildCommand` and asset
rewrites. The root route will fall back to the existing "UI bundle not built"
shell while API routes continue to work.
