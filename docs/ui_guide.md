# UI Guide

## Overview

nbatools ships a React + TypeScript + Vite single-page UI.
The frontend source lives in `frontend/` and builds into `src/nbatools/ui/dist/`,
which the FastAPI server serves at `GET /`.

## Running locally

### Production-like (API serves built assets)

```bash
# 1. Build the frontend (once, or after changes)
cd frontend && npm run build

# 2. Start the API (serves the built UI at /)
nbatools-api              # default: http://127.0.0.1:8000
nbatools-api --port 9000  # custom port
nbatools-api --reload     # auto-reload during development

# Or via uvicorn directly:
uvicorn nbatools.api:app --reload
```

Then open **http://127.0.0.1:8000** in a browser.

### Development (two terminals, hot reload)

```bash
# Terminal 1: API server
uvicorn nbatools.api:app --reload

# Terminal 2: Vite dev server with API proxy
cd frontend && npm run dev
```

The Vite dev server proxies `/health`, `/routes`, `/query`, and `/structured-query`
to the API at `http://127.0.0.1:8000`. Open **http://localhost:5173** for hot
module replacement during frontend development.

## What the UI does

- **Query bar** — type a natural-language NBA query and press Enter or click Query.
- **Sample buttons** — pre-filled example queries you can click to try immediately.
- **Result envelope** — shows query metadata: status, route, data freshness, notes, caveats.
- **Data tables** — renders the result payload as readable tables. Layout adapts to the result type (summary, comparison, leaderboard, finder, streak, split).
- **Raw JSON** — toggle to inspect the full API response.
- **Dev Tools panel** — collapsible structured-query interface for calling `POST /structured-query` with a route selector and kwargs JSON input.

## How it works

```
Browser (index.html)
  │
  ├─ GET  /           → serves the HTML page (same origin)
  ├─ GET  /health     → version badge
  ├─ GET  /routes     → populates the Dev Tools route dropdown
  ├─ POST /query      → natural-language queries
  └─ POST /structured-query → structured/route-based queries
```

All communication is same-origin fetch calls — no CORS issues, no proxy needed.
CORS middleware is enabled for flexibility if someone wants to open the HTML file separately.

## Result types rendered

| query_class   | Sections displayed              |
| ------------- | ------------------------------- |
| summary       | Summary, By Season (if present) |
| comparison    | Summary, Comparison             |
| split_summary | Summary, Split Comparison       |
| finder        | Matching Games                  |
| leaderboard   | Leaderboard                     |
| streak        | Streaks                         |
| (no result)   | Status message with reason      |

## File locations

- Frontend source: `frontend/` (React + TypeScript + Vite)
- Build output: `src/nbatools/ui/dist/` (served by FastAPI)
- API serving: `src/nbatools/api.py` → `GET /` + `/assets` static mount
- Vite config: `frontend/vite.config.ts` (proxy + build output path)

## Tech stack

- React 19, TypeScript, Vite
- Typed API client: `frontend/src/api/client.ts` + `types.ts`
- Components: `frontend/src/components/`

## Out of scope (intentional)

- Authentication / user accounts
- Database or persistence
- Production deployment / hosting
- Client-side routing
- State management libraries
