# UI Guide

## Overview

nbatools ships a single-page query UI served directly from the API.
No build step, no npm, no extra process — open a browser and start querying.

## Running locally

```bash
# 1. Start the API (which also serves the UI)
nbatools-api              # default: http://127.0.0.1:8000
nbatools-api --port 9000  # custom port
nbatools-api --reload     # auto-reload during development

# Or via uvicorn directly:
uvicorn nbatools.api:app --reload
```

Then open **http://127.0.0.1:8000** in a browser.

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

- UI source: `src/nbatools/ui/index.html`
- API serving: `src/nbatools/api.py` → `GET /`
- No build artifacts, no dependencies beyond the API extras.

## Out of scope (intentional)

- Authentication / user accounts
- Database or persistence
- Production deployment / hosting
- Polished visual design
- Client-side routing
- State management libraries
