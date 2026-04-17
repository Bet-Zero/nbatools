# Roadmap

This roadmap describes how `nbatools` should evolve from its current state into a more complete UI-based NBA search app with text input.

It is intentionally phased. The goal is to expand **answerable NBA questions**, improve trustworthiness and maintainability, and strengthen the engine that powers both the CLI and the web UI.

---

## Product direction

`nbatools` is being built toward a **UI-based NBA search app with text input**.

The current CLI is the development interface and power-user surface. The React web UI and FastAPI layer are the product-facing surfaces. All three share the same query engine.

---

## Shipped foundation

The repo has a substantial shipped base.

### Engine foundations

- natural language parsing and routing (25 structured routes)
- player and team finder queries
- player and team summaries
- player and team comparisons
- split summaries (home/away, wins/losses)
- grouped boolean filtering (AND / OR / parentheses)
- sample-aware player advanced metrics (USG%, AST%, REB%)
- export support (CSV / TXT / JSON)
- date-windowed queries (specific month, since month, rolling days, All-Star break)
- career / all-time queries
- last-N-seasons and season-range queries
- player and team streak queries
- team record and matchup-record queries
- team record leaderboards
- playoff history, appearances, round records, by-decade breakdowns
- matchup by decade
- entity resolution with 90+ player aliases and full team alias mapping
- ambiguity detection and confidence-level reporting

### API and UI (shipped)

- FastAPI HTTP layer with `/query`, `/structured-query`, `/health`, `/routes`, `/freshness`
- React + TypeScript + Vite web UI served from FastAPI
- result rendering for all query classes
- query bar, sample queries, query history, saved queries
- raw JSON toggle, Dev Tools panel, URL state for deep links

### Testing

- 1650 passing tests across 41 test files
- coverage spans parser, routing, result contracts, CLI smoke, API, query service, and specialized query areas

---

## Current phase: hardening + remaining coverage gaps

The repo has shipped a broad query surface, a working API, and a functional UI. The current priority is **hardening, coverage gaps, and trustworthiness** — not greenfield feature work.

Current work should focus on:

1. hardening edge cases in shipped query behavior
2. improving data freshness and update trustworthiness
3. closing remaining natural-query phrasing coverage gaps
4. repo and documentation hygiene

---

## Phase 1 — Foundation hardening (largely complete)

### What shipped

- `AGENTS.md` and operating docs established
- `docs/project_conventions.md` and `docs/data_contracts.md` in place
- parser/router cleanup (natural_query.py restructured with intent detectors, entity resolution, occurrence extraction)
- current-state docs aligned with verified behavior
- test suite expanded from ~125 to 1650 tests

### Remaining work

- continued cleanup of any remaining duplication in route branches
- verify edge cases in occurrence queries (player occurrence leaders, team occurrence leaders)
- compound occurrence leaderboards
- first-class game finder output with count intent
- opponent and matchup filters (vs, h2h, head-to-head)
- expanded queryable stats (STL, BLK, TOV combinations)
- tighten edge-case handling for rare stat/filter combinations

---

## Phase 3 — Expand time intelligence (largely complete)

### What shipped

- date-windowed queries (specific month, since month, since All-Star break)
- streaks: player and team threshold streaks, longest streaks, triple-double streaks, made-three streaks, winning/losing streaks
- career / all-time queries
- last-N-seasons, last N seasons
- season-range queries
- season type (playoffs / regular season)

### Remaining work

- verify edge cases around season-boundary date handling
- harden career queries across players with long multi-team histories

---

## Phase 4 — Data freshness and trustworthiness (in progress)

### Goal

Make results trustworthy for real use.

### What exists

- `docs/data_freshness_plan.md` — design and implementation plan
- `commands/freshness.py` — freshness computation, classification, `FreshnessStatus` enum
- `commands/pipeline.py` — canonical data pipeline with manifest tracking
- `commands/auto_refresh.py` — automated refresh loop
- `current_through` metadata is present in query responses

### Remaining work

1. establish a reliable daily/weekly update cadence during the season
2. automate the refresh pipeline (currently manual CLI commands)
3. surface data freshness more prominently in the UI
4. add contract enforcement for refresh output validation

---

## Phase 5 — Product-layer readiness (partially complete)

### What shipped

- query classes formalized: finder, count, summary, comparison, split, leaderboard, streak, record, playoff
- `StructuredResult` objects for all routes with `QueryResult` envelope with metadata, status, and reason
- React UI renders all current result types

### Remaining work

1. stabilize result contracts across all 25 routes (some routes may have inconsistent field shapes)
2. ensure all routes produce consistent `sections` keys in their structured output
3. formalize the export contract for each result class

---

## Phase 6 — First UI (shipped)

### Status: shipped

The first web UI is built and live:

- React + TypeScript + Vite frontend in `frontend/`
- typed API client (`types.ts` + `client.ts`)
- components: QueryBar, SampleQueries, ResultEnvelope, ResultSections, DataTable, QueryHistory, SavedQueries, RawJsonToggle, DevTools, Loading, ErrorBox
- build output served by FastAPI from `src/nbatools/ui/dist/`
- Vite dev server with API proxy for hot reload during development

---

## Remaining priorities

These are the highest-value next areas of work, roughly ordered:

1. **Data freshness automation** — reliable update workflow so results stay current
2. **Result contract stabilization** — consistent structured output across all routes
3. **Phrasing coverage expansion** — support more natural query phrasings
4. **UI polish** — improve table rendering, add result type-specific formatting, better mobile support
5. **Error/edge-case handling** — better user-facing messages for ambiguous or failing queries
6. **Doc maintenance** — keep docs in sync with each shipped change

---

## What not to do

Do not:

- over-polish UI before engine contracts are stable
- add niche metrics before broad search coverage is strong
- do broad architecture rewrites without a clear payoff
- let docs claim support that tests and behavior do not justify
- introduce new infrastructure (databases, caches) unless there is a real performance or complexity need

---

The roadmap is succeeding if `nbatools` becomes progressively better at this core promise:

> A user can type a natural NBA question and get a correct, structured answer from a reusable engine that powers both a CLI and a web UI.
