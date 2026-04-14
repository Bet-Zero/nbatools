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

- **Query bar** — type a natural-language NBA query and press Enter or click Query. Includes a clear (✕) button and shows "Running…" state during queries.
- **Sample buttons** — pre-filled example queries with a label, click to run immediately.
- **Empty state** — welcome screen with tips shown before the first query.
- **Result envelope** — shows query metadata with clear visual hierarchy:
  - **Status badge** — color-coded pill (Success/No Result/Error)
  - **Route + query class** — displayed as pills
  - **Data freshness** — "Data through" date prominently shown
  - **Context chips** — player, team, season, opponent, split type
  - **Notes** — blue-bordered info block
  - **Caveats** — orange/yellow-bordered warning block
- **Data tables** — renders the result payload as readable tables. Layout adapts to the result type (summary, comparison, leaderboard, finder, streak, split). Entity columns (player names, teams) are bolded; rank columns are highlighted.
- **Copy buttons** — copy the query text, full JSON response, or shareable link to clipboard.
- **Copy Link** — copies the current URL with query state, so the result can be shared or bookmarked.
- **Raw JSON** — toggle to inspect the full API response.
- **URL-driven state** — the active query is stored in the URL (`?q=...` for natural queries, `?route=...&kwargs=...` for structured queries). Refreshing the page re-runs the query. Browser back/forward navigates across prior query states.
- **Query history** — in-session history with:
  - Status dots (green/yellow/red)
  - Query class and route labels
  - Query count
  - **Edit** button — populates the input bar for modification without running
  - **Rerun** button — immediately re-executes the query
  - Time-ago display
  - Not persisted across sessions
- **No-result / error display** — friendly messages for empty results (with suggestions) and errors.
- **Dev Tools panel** — collapsible structured-query interface for calling `POST /structured-query` with a route selector and kwargs JSON input.
- **Health indicator** — live green/red dot showing API connectivity and version.

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
- Vitest + Testing Library for frontend tests
- Typed API client: `frontend/src/api/client.ts` + `types.ts`
- Components: `frontend/src/components/`
- Hooks: `frontend/src/hooks/`
- Tests: `frontend/src/test/`

## Frontend file structure

```
frontend/src/
  api/
    types.ts             # TypeScript interfaces for API envelope, result types, query history
    client.ts            # Typed fetch wrappers (fetchHealth, postQuery, fetchFreshness, etc.)
  components/
    QueryBar.tsx          # Text input + submit
    SampleQueries.tsx     # Pre-filled example query buttons
    EmptyState.tsx        # Welcome state shown before first query
    QueryHistory.tsx      # In-session query history list
    FreshnessStatus.tsx   # Collapsible freshness panel (status, current_through, details)
    ResultEnvelope.tsx    # Envelope metadata (status, route, notes, caveats)
    ResultSections.tsx    # Dispatcher — routes to per-query-class renderers
    SummarySection.tsx    # Summary + By Season tables
    ComparisonSection.tsx # Players + Comparison tables
    SplitSummarySection.tsx # Summary + Split Comparison tables
    FinderSection.tsx     # Matching Games table with count
    LeaderboardSection.tsx # Leaderboard table with count
    StreakSection.tsx      # Streaks table with count
    DataTable.tsx         # Generic table renderer with highlight mode
    NoResultDisplay.tsx   # No-result and error state display
    RawJsonToggle.tsx     # Raw JSON toggle
    CopyButton.tsx        # Copy-to-clipboard button
    DevTools.tsx          # Structured query panel (route selector + kwargs)
    Loading.tsx           # Loading spinner
    ErrorBox.tsx          # Error display
  hooks/
    useQueryHistory.ts    # In-session query history state hook
    useUrlState.ts        # URL search-param sync for shareable deep links
  test/
    setup.ts             # Vitest + jest-dom setup
    client.test.ts       # API client tests
    DataTable.test.tsx   # DataTable component tests
    ResultSections.test.tsx # Result rendering tests for all query classes
    UIComponents.test.tsx # EmptyState, NoResult, Loading, ErrorBox tests
    FreshnessStatus.test.tsx # Freshness panel rendering and status display tests
    useUrlState.test.ts  # URL state parsing, building, and hook behavior tests
  App.tsx                # Main app component — wires state + components
  App.css                # All styles (dark theme, CSS custom properties)
  main.tsx               # React entry point
```

## Running frontend tests

```bash
cd frontend
npm test          # run once
npm run test:watch  # watch mode
```

## URL state model

The app stores query state in URL search params so every result is linkable:

| Param    | Purpose                            | Example                                |
| -------- | ---------------------------------- | -------------------------------------- |
| `q`      | Natural-language query text        | `?q=Jokic+last+10+games`               |
| `route`  | Structured route name (dev tools)  | `?route=season_leaders`                |
| `kwargs` | Structured kwargs JSON (dev tools) | `&kwargs=%7B%22stat%22%3A%22pts%22%7D` |

**Behavior:**

- On submit: a new browser history entry is pushed with the query in the URL.
- On page load: if the URL contains query params, the query auto-runs.
- Browser back/forward: navigates across prior queries, re-running each.
- Copy Link button: copies the shareable URL to clipboard.
- Natural and structured params are mutually exclusive in the URL.

## Out of scope (intentional)

- Authentication / user accounts
- Database or persistence
- Production deployment / hosting
- Client-side routing library (URL state is managed with native History API)
- State management libraries
- Raw JSON toggle persistence in URL
