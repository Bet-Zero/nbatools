# Roadmap

This roadmap describes how `nbatools` should evolve from its current CLI-first engine into a UI-based NBA search app with text input.

It is intentionally phased. The goal is not to add random commands. The goal is to expand **answerable NBA questions**, improve trustworthiness and maintainability, and strengthen the engine that powers both the CLI and the web UI.

---

## Product direction

`nbatools` is being built toward a **UI-based NBA search app with text input**.

The current CLI is the development interface and power-user surface used to build and validate:

- parsing
- filtering
- grouping
- aggregation
- sample-aware metrics
- tested execution
- operational data workflows

The hardest part already exists: the engine foundation.

What is still missing is mostly:

- broader question coverage
- stronger product shape
- data freshness discipline
- cleaner engine contracts for CLI and UI consumers

---

## Current phase

### Current phase: engine hardening + search coverage expansion

The repo now has a real packaged CLI, a natural query layer, structured commands, exports, grouped boolean support, advanced player sample-aware metrics, and broader query coverage than the earlier baseline.

However, the current priority is still **coverage and product readiness**, not UI polish.

That means current work should focus on:

1. verifying and tightening shipped search behavior
2. cleaning up routing/engine boundaries where needed
3. expanding coverage for common NBA questions
4. improving data/update trustworthiness
5. preparing reusable result shapes for the web UI

---

## Shipped foundation

The repo already has a strong base in place.

### Engine foundations already in place

- natural language parsing and routing
- player and team finder queries
- player and team summaries
- player and team comparisons
- split summaries
- grouped boolean filtering
- sample-aware player advanced metrics
- exports to CSV / TXT / JSON
- packaged CLI with structured command groups

### Broader surface now present in the repo

The current repo also includes support or partial support for:

- player and team season leaderboards
- matchup / head-to-head phrasing
- date-aware natural queries
- player and team streak queries
- raw / processing / ops / analysis command groups

These should continue to be hardened and verified, not treated as “done forever” just because the code exists.

---

## Phase 1 — Foundation hardening

### Goal

Stabilize the engine and repo conventions so future work scales cleanly.

### Why this phase matters

The biggest risk now is not lack of capability. It is feature growth without enough structure.

### Work in this phase

#### 1. Conventions and operating docs

Establish and maintain:

- `AGENTS.md`
- `docs/project_conventions.md`
- `docs/data_contracts.md`
- `docs/roadmap.md`

#### 2. Capability reality audit

Audit the currently advertised surface and classify features as:

- verified and protected by tests
- implemented but still needing hardening
- planned but not yet shipped

Priority audit targets:

- leaderboard queries
- date-aware queries
- streak queries
- matchup / head-to-head queries

#### 3. Parser/router cleanup

`src/nbatools/commands/natural_query.py` is now a major complexity hotspot.

Short-term goals:

- remove duplicated route branches
- remove repeated post-processing where possible
- keep routing/orchestration logic readable
- push reusable business logic into dedicated helpers/modules

#### 4. Docs alignment

Ensure:

- README reflects user-facing verified capability
- `docs/current_state_guide.md` reflects verified shipped behavior only
- roadmap stays roadmap, not current-state

### Definition of done

This phase is in good shape when:

- core conventions docs exist and are respected
- current-state docs do not overclaim
- route logic is cleaner and easier to reason about
- priority advertised features have an explicit verification status

---

## Phase 2 — Expand question coverage

### Goal

Answer far more NBA searches without changing the overall architecture.

This is the phase where `nbatools` moves from a strong analytics CLI toward a stronger NBA search product.

### Major work areas

#### 1. League-wide player search

Add or harden support for queries like:

- top scorers this season
- players averaging 25+ over last 10
- most 40 point games
- highest TS%

Build/harden:

- league-wide player summary dataset behavior
- sortable/rankable outputs
- top N / leaderboard semantics

Why first:

This is one of the largest “type an NBA question and get an answer” gaps.

#### 2. League-wide team search

Add or harden support for queries like:

- best offense this season
- teams with most threes
- best TS%
- highest assist rate

Build/harden:

- team leaderboard queries
- sortable/rankable outputs

#### 3. First-class game finder output

The engine can already find games, but game-list output should become a first-class product surface.

Target queries include:

- show me Jokic games with 30+ points and 10+ assists
- show me Celtics games with 120+ points and 15+ threes

Needs:

- consistent game-list result mode
- better default columns
- better sorting defaults
- clearer distinction between list-vs-summary intent

#### 4. Opponent and matchup coverage

Add or harden support for:

- `vs Lakers`
- `vs Celtics`
- head-to-head queries
- player vs team matchup filtering
- team vs opponent filtering

This is a major part of real NBA search behavior.

#### 5. Expand queryable stats

You already compute a lot. More of it should become queryable.

Priority stats:

- STL
- BLK
- TOV
- eFG%
- TS%
- plus/minus

Later, if reliable enough:

- advanced player rates as query filters

### Definition of done

This phase is in good shape when the tool can answer a much broader set of common league-wide, matchup, and filtered-game questions through a stable natural query surface.

---

## Phase 3 — Expand time intelligence

### Goal

Make searches feel more natural and historically flexible.

### Work in this phase

#### 1. Date ranges

Add or harden support for:

- since January
- in March
- since All-Star break
- last 30 days

#### 2. Streak queries

Add or harden support for:

- 5 straight games with 20+
- longest streak of 30 point games
- consecutive games with a made three
- longest triple-double streak
- team winning / losing streak queries

This is a major user-facing win.

#### 3. Career and multi-season aggregation

Add support for:

- career leaderboards
- since 2020
- over the last 3 seasons
- playoff-only historical spans

### Definition of done

This phase is in good shape when users can ask natural time-window and streak questions without having to think in rigid season-only terms.

---

## Phase 4 — Data freshness and trustworthiness

### Goal

Make results trustworthy for real use.

### Why this phase matters

A strong search surface is not enough if users cannot trust how current the data is.

### Work in this phase

#### 1. Update pipeline

Establish a clear answer to:

- where data comes from
- when it refreshes
- how it backfills
- how corrections are handled

Minimum viable target:

- daily update workflow during season
- re-run final game ingestion after game nights
- season-level rebuild script
- one command/workflow to refresh raw + derived datasets

#### 2. Data contract enforcement

Keep explicit contracts for the datasets that power:

- player game finder
- team game finder
- summaries
- splits
- comparisons
- leaderboards
- streaks

This prevents future spaghetti.

#### 3. Visibility into freshness

Longer-term, the product should make it clear:

- what season/data window is loaded
- how recent the underlying data is
- whether outputs are current through the latest completed games

### Definition of done

This phase is in good shape when the update story is explicit, repeatable, and trustworthy enough to support real user-facing search.

---

## Phase 5 — Product-layer readiness

### Goal

Make the engine easy to expose through a UI.

### Status

Partially shipped. The React UI already consumes the `QueryResponse` envelope and renders all current result types. Remaining work is about formalizing result classes and stabilizing contracts.

### Work in this phase

#### 1. Query classes

Formalize the major supported question types:

- finder
- summary
- split
- comparison
- leaderboard
- streak
- matchup

These classes should guide:

- parser routing
- command structure
- docs
- React UI result layouts

#### 2. Better output modes

Make result intent more explicit.

Examples:

- list games
- summarize
- rank players
- rank teams
- compare entities

Right now some of this is implicit in routing. That should become more deliberate over time.

#### 3. UI-ready result shapes

Stabilize result structures so a UI can map them into:

- summary cards
- tables
- split views
- comparison views
- streak result lists
- leaderboard tables

### Definition of done

This phase is in good shape when the core engine behaves like a reusable application backend instead of a CLI-only surface.

---

## Phase 6 — First UI

### Status: shipped

The first web UI has been built and is live:

- React + TypeScript + Vite frontend in `frontend/`
- Typed API client (`types.ts` + `client.ts`)
- Components: QueryBar, SampleQueries, ResultEnvelope, ResultSections, DataTable, RawJsonToggle, DevTools, Loading, ErrorBox
- Build output served by FastAPI from `src/nbatools/ui/dist/`
- Vite dev server with API proxy for hot reload during development

### What the first UI provides

- text input for natural-language NBA queries
- pre-filled sample query buttons
- result rendering for all query classes (summary, comparison, split, finder, leaderboard, streak)
- envelope metadata display (status, route, freshness, notes, caveats)
- raw JSON toggle
- Dev Tools panel for structured (route-based) queries

### Important constraint

Do not jump to UI before engine contracts and search coverage are stable enough.

---

## Immediate priorities

These are the highest-value next areas of work.

1. finish feature reality audit for leaderboard/date/streak/head-to-head behavior
2. tighten `natural_query.py` structure and reduce duplication
3. harden and verify leaderboards
4. harden and verify matchup/head-to-head behavior
5. harden and verify date-aware and streak behavior
6. define a concrete data update/freshness plan

---

## Recommended build order

This was the original recommended order and it still mostly holds, with one adjustment: some of these areas now exist in partial or early form and should be hardened instead of treated as brand-new.

### Build 1 — League-wide player leaderboard queries

Examples:

- top scorers this season
- highest TS% among players
- most 30 point games

### Build 2 — League-wide team leaderboard queries

Examples:

- best offensive teams
- most threes per game
- best eFG%

### Build 3 — Opponent and matchup filters

Examples:

- Jokic vs Lakers
- Celtics vs Bucks
- Embiid head-to-head vs Jokic

### Build 4 — Date ranges

Examples:

- since January
- in March
- last 30 days

### Build 5 — Streak queries

Examples:

- 5 straight 20 point games
- longest triple-double streak

That sequence still gives the biggest search-surface gain fastest.

---

## What not to do yet

Do not:

- jump straight to UI before engine contracts are ready
- over-polish README instead of improving coverage
- add niche metrics before broad search coverage is strong
- do broad architecture rewrites without a clear payoff
- let docs claim support that tests and behavior do not justify

The real missing thing is not prettier output. It is **more answerable questions and more trustworthy behavior**.

---

## Version-oriented milestone view

These versions are directional, not promises. They help sequence the work.

### v0.8.x

League-wide player leaderboards and player ranking hardening

- top N player queries
- ranking semantics
- broader player season/league summary coverage

### v0.9.x

League-wide team leaderboards and team ranking hardening

- team ranking queries
- better team season summary coverage

### v1.0.x

Matchup + date-range hardening

- vs filters
- head-to-head semantics
- since/in date handling
- broader natural search coverage

### v1.1.x

Streak engine hardening

- consecutive games
- longest streaks
- threshold streak queries

### v1.2.x

Freshness pipeline + frontend iteration

- reliable update story
- cleaner reusable result shapes
- UI polish and expanded component coverage

---

## Definition of roadmap success

The roadmap is succeeding if `nbatools` becomes progressively better at this core promise:

> A user can type a real NBA question into a text input and get a trustworthy answer from a reusable engine that powers both a CLI and a web UI.
