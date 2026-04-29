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

## Identity imagery and team theming

Phase V4 adds presentation-only identity treatment for players and teams:

- Player headshots render only from stable `player_id` values supplied by the
  API. Missing ids or failed image loads fall back to the initials avatar.
- Team logos render only from stable `team_id` values. Known abbreviations use
  `frontend/src/styles/team-colors.json` for badge colors; unknown or
  historical abbreviations fall back to neutral text badges.
- Result-level team color is scoped to a safe single-team context from
  `team_context`. Player-subject, multi-team, comparison, and league-wide
  leaderboard results remain neutral.
- Team color treatment is limited to identity surfaces: badges, a subtle result
  stripe, and a light surface wash. Buttons, body copy, table text, and global
  action states keep the design-system colors.
- Tables remain horizontally scrollable for dense results. Player avatars and
  team logo marks have fixed dimensions so image loading and fallback states do
  not change row height.

Useful Phase V4 visual checks:

- Player result: `Jokic last 10 games`
- Single-team result: `Celtics record 2024-25`
- Multi-team comparison: `Celtics vs Lakers record 2024-25`
- League leaderboard: `top 10 scorers 2024-25`

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
- Design-system primitives: `frontend/src/design-system/`
- Hooks: `frontend/src/hooks/`
- Tests: `frontend/src/test/`

## Design-system primitives

Reusable frontend primitives live in `frontend/src/design-system/` and are
exported from the barrel import:

```tsx
import { Badge, Button, Card, DataTable, SectionHeader } from "../design-system";
```

These primitives are presentation-only. They own token-driven layout, spacing,
color, type, borders, radii, shadows, and accessible fallback structure. Feature
components still own query behavior, API response interpretation, NBA-specific
value formatting, metric selection, and route-specific labels.

| Primitive | Purpose | Variant guidance |
| --------- | ------- | ---------------- |
| `Button` | Text buttons for submit, copy, toggle, and destructive actions | Use `primary` for the main action in a zone, `secondary` for ordinary actions, `ghost` for low-emphasis tools, and `danger` only for destructive actions. Sizes are `sm` and `md`; `loading` disables and marks the button busy. |
| `IconButton` | Icon-only buttons with required accessible labels | Use when the visible control is an icon. Always provide `aria-label`; the icon node is decorative. |
| `Card` | Tokenized surface with depth, padding, and system tone | `depth` maps to `elevated`, `card`, or `input`; `tone` is for UI/system states, not team identity. |
| `SectionHeader` | Section title row with optional eyebrow, count, and actions | Feature components provide labels and counts; the primitive owns alignment and wrapping. |
| `ResultEnvelopeShell` | Slot layout for result metadata, query text, context, notices, alternates, and children | Keep status, route, freshness, notes, caveats, and alternate-query behavior in `ResultEnvelope`. |
| `Badge` | Compact chip for statuses, tags, routes, and context | Use `success`, `warning`, `danger`, and `info` for UI/system states; use `win` and `loss` only for sports outcome semantics; use `accent` sparingly for route/context emphasis. |
| `Stat` | Single label/value/context display with mono numeric value styling | Pass already-computed values only. The primitive does not calculate NBA metrics or trends. |
| `StatBlock` | Responsive grid of `Stat` items | Feature wrappers choose which stats appear and in what order. |
| `Skeleton`, `SkeletonText`, `SkeletonBlock` | Loading placeholders | Use to approximate upcoming content while preserving feature-level loading copy and state. |
| `DataTable` | Generic table shell for supplied columns, rows, alignment, highlight, and cell classes | It does not format NBA values or infer player/team/rank columns; `components/DataTable.tsx` remains the NBA-specific wrapper. |
| `Avatar` | Player/person fallback identity mark | Use existing names only. Real image source integration remains Phase V4. |
| `TeamBadge` | Team fallback identity mark with `--team-primary` / `--team-secondary` hooks | Use team colors only as contextual identity accents, not button colors or body text. Real logo source integration remains Phase V4. |

### Primitive examples

```tsx
<Button variant="primary" loading={isSubmitting}>
  Query
</Button>

<Badge variant="success" uppercase>
  fresh
</Badge>

<SectionHeader title="Leaderboard" count={`${rows.length} entries`} />

<StatBlock
  stats={[
    { label: "PTS", value: "28.4", semantic: "accent" },
    { label: "REB", value: "11.2" },
  ]}
  columns={2}
/>
```

```tsx
<DataTable
  rows={rows}
  columns={[
    {
      key: "player",
      header: "Player",
      render: (row) => row.player,
    },
  ]}
/>
```

The generic table example above intentionally renders supplied values as-is.
NBA-specific header formatting, percentage formatting, entity-column detection,
and highlight choices belong in feature wrappers outside `design-system/`.

### Primitive checklist

Before adding or consuming a primitive:

- Import from `frontend/src/design-system/index.ts`, not a deep path, unless a
  test needs a CSS module.
- Keep parser, query, filtering, analytics, and NBA metric logic outside the
  primitive.
- Use existing tokens for colors, spacing, typography, borders, radii, shadows,
  and motion.
- Keep team colors contextual through `--team-primary` / `--team-secondary`;
  do not apply team colors to global actions or dense table text.
- Add or update focused tests when a feature component migrates to a primitive.

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
    DataTable.tsx         # NBA-specific wrapper over the generic table primitive
    NoResultDisplay.tsx   # No-result and error state display
    RawJsonToggle.tsx     # Raw JSON toggle
    CopyButton.tsx        # Copy-to-clipboard button
    DevTools.tsx          # Structured query panel (route selector + kwargs)
    Loading.tsx           # Loading status with skeleton preview
    ErrorBox.tsx          # Error display
  design-system/
    Avatar.tsx            # Player/person fallback identity mark
    Badge.tsx             # Status/context chip primitive
    Button.tsx            # Button and IconButton primitives
    Card.tsx              # Tokenized surface primitive
    DataTable.tsx         # Generic table shell primitive
    ResultEnvelopeShell.tsx # Result-envelope slot layout primitive
    SectionHeader.tsx     # Section heading/count/action primitive
    Skeleton.tsx          # Skeleton, SkeletonText, SkeletonBlock primitives
    Stat.tsx              # Single stat display primitive
    StatBlock.tsx         # Stat grid primitive
    TeamBadge.tsx         # Team fallback identity mark
    index.ts              # Barrel export for primitives and prop types
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
  App.module.css         # App shell styles
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

## App shell layout notes

The Phase V3 shell is slot-based: `App.tsx` still owns query state, URL state,
API calls, saved-query state, and dialog mounting, while
`components/AppShell.tsx` owns the page regions for header, freshness, query,
main results, and secondary panels.

Responsive expectations for future frontend work:

- Keep primary query/result controls in the main region; saved queries, history,
  and dev tools belong in the secondary panel area.
- Long query text and dense results should stay inside their region. Tables
  remain horizontally scrollable through the data-table wrapper instead of
  forcing the whole page wider.
- Section-header actions should wrap at mobile widths. Avoid adding fixed-width
  controls to shell regions unless they also have a mobile wrapping rule.
- Freshness and API status are shell chrome, but their fetching and semantics
  remain in `App.tsx` and `FreshnessStatus.tsx`.

## Out of scope (intentional)

- Authentication / user accounts
- Database or persistence
- Production deployment / hosting
- Client-side routing library (URL state is managed with native History API)
- State management libraries
- Raw JSON toggle persistence in URL
