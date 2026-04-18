# AGENTS.md

This file tells coding agents how to work in the `nbatools` repo.

## Project goal

`nbatools` is a **UI-based NBA search app with text input**.

The repo has three consumer surfaces: a CLI (development/power-user), a FastAPI HTTP layer, and a React + TypeScript + Vite web UI. The CLI and web UI are both thin presentation layers over a shared query engine.

That means:

- core logic must remain **UI-agnostic**
- natural query behavior must remain **transport-agnostic**
- CLI wrappers should stay thin
- the React frontend should stay thin — fetch, render, no business logic
- machine-readable outputs must stay stable for all consumers (CLI, API, UI)

## Working style

Agents working in this repo should:

- prefer small, targeted changes over broad rewrites
- preserve existing public behavior unless the task explicitly changes it
- keep parser logic, command logic, data processing, and formatting separated
- avoid editing unrelated files while implementing a feature
- tighten duplication when touching an area that already shows repeated logic
- leave the repo in a cleaner state than they found it when reasonable

Do not introduce architecture churn without a concrete reason tied to maintainability, correctness, or long-term UI/API readiness.

## What this repo is optimizing for

The current phase is about building a durable NBA search engine that powers both the CLI and the web UI.

Priority order:

1. correct data behavior
2. stable command/query semantics
3. test coverage
4. reusable output contracts
5. CLI and UI presentation
6. frontend iteration

## Change rules

### General rule

When adding or changing a feature, agents should usually follow this order:

1. implement or extend the underlying structured behavior
2. wire or update natural query routing
3. add or update tests
4. update docs for verified shipped behavior

A feature should not be treated as shipped if docs changed but tests or behavior did not.

### Command-layer rule

Do not put business logic directly in CLI entrypoints or Typer command wrappers.

- `src/nbatools/cli.py` and `src/nbatools/cli_apps/*` are for command registration, argument handling, and export plumbing
- real query or analytics logic belongs in `src/nbatools/commands/*`

### Natural query rule

`src/nbatools/commands/natural_query.py` is a routing/orchestration layer.

It may contain:

- intent detection
- alias resolution
- route selection
- natural language parsing helpers
- orchestration across structured commands

It should **not** become an unmanaged dumping ground for unrelated business logic.

If a feature requires substantial new computation, reusable filtering logic, or domain-specific analysis, move that logic into a dedicated command/helper module.

For parser work, treat all of these as first-class input styles:

- full question form
- search-bar / fragment form
- compressed shorthand form

Do not assume users will type full grammatical questions. Favor intent + slots over sentence grammar. See `docs/planning/query_surface_expansion_plan.md` for the active parser/query-surface expansion plan and the "Phase-based work queues" section below for how to pick up scheduled work on it.

### Frontend-layer rule

The React frontend in `frontend/` is a presentation layer.

It may contain:

- typed API client code (`frontend/src/api/`)
- React components for rendering results (`frontend/src/components/`)
- UI state management (loading, error, result)
- styling (`App.css`)

It must **not** contain:

- business logic, filtering, or analytics
- data transformations that belong in the engine
- query parsing or routing decisions

The frontend calls the API and renders what it gets back. If a UI feature requires new data, add it to the engine/API response — do not compute it client-side.

After any frontend source change, rebuild with `cd frontend && npm run build` so the FastAPI-served build stays current.

### Duplication rule

When touching duplicated route branches, duplicate post-processing, or repeated helper logic, agents should prefer cleanup instead of adding a third copy.

Do not knowingly leave behind:

- dead branches
- duplicate route handling
- one-off compatibility hacks with no comment or cleanup plan
- silent behavior forks between player/team paths unless justified

## Testing expectations

Every meaningful feature change should include appropriate tests.

### Test commands

Use the Makefile targets — do not invent ad hoc pytest invocations.

| Command               | What it does                                                                   | When to use                                                                                  |
| --------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `make test-impacted`  | Runs only tests whose file-level dependencies changed (pytest-testmon, serial) | **Default** — during active development and as the normal finishing step                     |
| `make test`           | Full regression suite (parallel via xdist)                                     | Maximum-confidence validation: before merging, after broad changes, or explicitly risky work |
| `make test-preflight` | All tests except `slow` (parallel via xdist, no testmon)                       | Broad, cross-cutting, or higher-risk changes only — not the default finishing step           |

### Domain subset targets

Run a specific subsystem's tests regardless of file changes:

| Command            | What it runs                                                  |
| ------------------ | ------------------------------------------------------------- |
| `make test-unit`   | All tests except `needs_data` and `slow` — fast and data-free |
| `make test-parser` | Parsing helpers, boolean parser, entity resolution            |
| `make test-query`  | Natural query routing, intent detection, orchestration        |
| `make test-engine` | Core command computation, metrics, records, streaks, pipeline |
| `make test-api`    | HTTP API layer                                                |
| `make test-output` | Formatting, result contracts, export                          |

These targets do **not** use `--testmon`. They always run every test with the marker.

### Choosing a test command based on what changed

| Code area changed                      | Recommended command                             |
| -------------------------------------- | ----------------------------------------------- |
| A single command module                | `make test-impacted` (testmon catches it)       |
| `natural_query.py` parsing helpers     | `make test-impacted`, then `make test-parser`   |
| `natural_query.py` routing logic       | `make test-impacted`, then `make test-query`    |
| A command module + NQ routing together | `make test-impacted`, then `make test-engine`   |
| `api.py` or API response shape         | `make test-api`                                 |
| `format_output.py` or result contracts | `make test-output`                              |
| Broad refactor or unclear scope        | `make test-preflight` (escalation, not default) |

### Testmon + marker interaction

`pytest --testmon -m parser -n0` runs impacted tests that are also `parser`-marked.
This is an **intersection** — fewer tests than either flag alone.
Agents may combine them manually for narrow, fast feedback.
The Makefile subset targets intentionally avoid `--testmon` so they always run
the full slice.

**Workflow for agents:**

1. While iterating, run `make test-impacted` for fast feedback.
2. If the change is localized to a known subsystem, also run the matching `make test-<domain>` target.
3. Steps 1–2 are the normal "done" signal for ordinary implementation work. Do not escalate further by default.
4. Run `make test-preflight` only for broad, cross-cutting, or higher-risk changes (e.g., refactors spanning multiple subsystems, unclear scope, or changes to shared infrastructure like `natural_query.py` routing).
5. Run `make test` only for maximum-confidence validation — before merging, or when `test-impacted` is known to be unreliable for the change (dynamic imports, data file changes, monkey-patching).

Testmon tracks file-level dependencies. It does **not** detect changes in data files, environment variables, or dynamically loaded modules. When in doubt, run the full suite.

### Minimum expectations by change type

- parsing change -> parser tests
- output behavior change -> smoke tests
- new calculation or metric -> formula/unit tests
- export behavior change -> export tests
- regression fix -> regression test covering the bug

### Required mindset

- do not claim a feature is supported just because one manual example worked
- do not update README or current-state docs unless the behavior is verified
- do not remove tests to make a failing implementation look clean

## CI testing policy

CI is defined in `.github/workflows/ci.yml`. It implements a layered testing strategy:

### What runs when

| Trigger             | `lint` | `test-fast` | `test-full` |
| ------------------- | ------ | ----------- | ----------- |
| Pull request        | ✓      | ✓           |             |
| Push to `main`      | ✓      | ✓           | ✓           |
| Nightly (06:00 UTC) | ✓      | ✓           | ✓           |
| Manual dispatch     | ✓      | ✓           | ✓           |

- **`test-fast`** calls `make test-unit`. Excludes `slow` and `needs_data` tests. Runs in parallel. This is the fast feedback path.
- **`test-full`** calls `make test`. Full regression suite in parallel. This is the correctness backstop.

### How this maps to agent workflow

| Agent phase                                  | Local command         | CI equivalent |
| -------------------------------------------- | --------------------- | ------------- |
| Active iteration                             | `make test-impacted`  | —             |
| Subsystem confidence                         | `make test-<domain>`  | —             |
| Before declaring work complete (normal)      | `make test-impacted`  | —             |
| Before declaring work complete (broad/risky) | `make test-preflight` | —             |
| PR pushed                                    | —                     | `test-fast`   |
| Merged to main / nightly                     | —                     | `test-full`   |

Local development uses `make test-impacted` (testmon) for the fastest feedback. CI does not use testmon — it uses `make test-unit` (marker-based exclusion, parallel) as the fast path instead. Testmon state is a local development optimization only.

### Caching

CI caches pip dependencies via `actions/setup-python`'s `cache: pip`. Testmon state (`.testmondata`) is **not** cached in CI — it is a local development tool and its state is not meaningful across CI runs from clean checkouts.

### Key invariant

The full regression suite (`make test`) always runs on merge to main and nightly. This is the backstop. Do not remove it.

## Documentation expectations

Each doc has a specific role. The `docs/` directory is organized by role:

- `docs/reference/` — current-state, verified behavior, data specs
- `docs/architecture/` — design docs, conventions, internal layers
- `docs/operations/` — runbooks, pipeline ops, UI dev guide
- `docs/planning/` — roadmap, active plans
- `docs/audits/` — audit snapshots, historical docs

Key docs:

- `README.md` -> user-facing overview and high-level examples
- `docs/reference/current_state_guide.md` -> verified shipped behavior only
- `docs/reference/query_catalog.md` -> living catalog of supported question/query types and common phrasing patterns
- `docs/planning/query_surface_expansion_plan.md` -> active plan for broadening question/search/shorthand query coverage
- `docs/planning/roadmap.md` -> planned or next capabilities
- `docs/architecture/project_conventions.md` -> architecture and engineering rules
- `docs/reference/data_contracts.md` -> dataset definitions and expectations
- `docs/operations/ui_guide.md` -> web UI setup, dev workflow, and component reference

Agents should keep these boundaries clean.

When adding a new doc, place it in the directory matching its role (see `docs/architecture/project_conventions.md` §10.7 for the full placement table). Update `docs/index.md` after adding or moving a doc.

In particular:

- do not put roadmap material into current-state docs
- do not advertise unsupported or untested behavior in README
- do not silently broaden claims without code and tests backing them up
- when a meaningful shipped query capability changes, update `docs/reference/query_catalog.md` in the same pass so the repo keeps a living inventory of supported question types and phrasing patterns

### Phase-based work queues

Some active plans in `docs/planning/` organize their work into phases with companion **work queue** files — sequenced, PR-sized task lists that live alongside the plan. The parser/surface expansion plan uses this pattern; other large, multi-phase efforts may adopt it.

#### How it works

- The **plan doc** (e.g. `docs/planning/query_surface_expansion_plan.md`) defines phases, scope, guardrails, and direction. It stays stable across a phase.
- The **active phase's work queue** (e.g. `docs/planning/phase_a_work_queue.md`) contains the current sequenced items, each with acceptance criteria and test commands. It changes continuously as items complete.
- The **final item of each queue** is always to draft the next phase's queue. This makes phase transitions self-triggering — the same "work the next item" prompt naturally produces the next queue when the current one is done.

#### Agent workflow

To pick up scheduled work on a phase-based plan, use this prompt:

> Read the plan doc and the active work queue (the most recent `phase_*_work_queue.md` in the plan's directory with unchecked items). Find the next unchecked item. Review the reference docs it cites. Execute the item per its acceptance criteria. Run the specified test commands. When everything passes, check the item off, update any docs the item requires.

The active queue is always the most recent `phase_*_work_queue.md` file in the plan's directory that still has unchecked items. No separate prompt is needed for phase transitions.

#### Keeping plan and queue in sync

If phase work uncovers a reason to change the plan's scope, priorities, or guardrails, update the plan in the same session as the queue item that triggered the change. Plan and queue should not drift apart silently.

## Output and interface expectations

Outputs in this repo serve multiple consumers:

- CLI pretty output
- raw/export output (CSV, TXT, JSON)
- web UI (React frontend consuming the API)
- any future API clients

Agents should treat raw command output as part of the engine contract.

Guidelines:

- pretty formatting is presentation only
- structured/raw outputs must remain machine-readable
- the React UI already consumes the same `QueryResponse` envelope the API returns
- avoid coupling core logic to terminal-only or browser-only assumptions
- if the UI needs a value that only exists in pretty CLI output, add it to the structured result

## Assumptions agents must not make

Agents must **not** assume:

- the CLI is the only consumer of engine output
- current docs are automatically correct
- one passing example means broad support
- all logic belongs in `natural_query.py`
- all data will remain CSV forever
- a refactor is justified just because it feels cleaner
- frontend changes don't need a rebuild (`npm run build`)
- the React UI should contain business logic

CSV + pandas is the current local-first implementation model. That is acceptable for now. Any storage-layer change should be justified by a real need, not novelty.

## Preferred implementation mindset

When in doubt, optimize for:

- explicitness over cleverness
- correctness over breadth
- reusable internals over CLI-only shortcuts
- stable contracts over ad hoc output tweaks
- documented and tested behavior over implied behavior

## If adding a new feature

Use this checklist:

- Does the behavior belong in an existing command, or does it need a new one?
- Is the new behavior expressible in structured form?
- Does natural query routing map cleanly to that structured behavior?
- Are parser tests updated if parsing changed?
- Are smoke tests added if output/behavior changed?
- Are docs updated only after verification?
- Does this move the repo toward a reusable engine?
- If changing the API response shape, is the React frontend updated to handle it?
- If changing the frontend, was `npm run build` run to update the served assets?
- If the shipped query surface changed, was `docs/reference/query_catalog.md` updated so the repo’s living query inventory stays current?

If a feature does not improve the reusable engine or its consumers, rethink the implementation.

## Frontend file layout

```
frontend/
  src/
    api/
      types.ts          # TypeScript interfaces matching the API response envelope
      client.ts         # Typed fetch wrappers (fetchHealth, postQuery, etc.)
    components/
      QueryBar.tsx       # Text input + submit
      SampleQueries.tsx  # Pre-filled example query buttons
      EmptyState.tsx     # Welcome state shown before first query
      QueryHistory.tsx   # In-session query history list
      FreshnessStatus.tsx # Collapsible data freshness panel (status, current_through, details)
      ResultEnvelope.tsx # Envelope metadata (status, route, notes, caveats)
      ResultSections.tsx # Dispatcher — routes to per-query-class renderers
      SummarySection.tsx     # Summary + By Season tables
      ComparisonSection.tsx  # Players + Comparison tables
      SplitSummarySection.tsx # Summary + Split Comparison tables
      FinderSection.tsx      # Matching Games table with count
      LeaderboardSection.tsx # Leaderboard table with count
      StreakSection.tsx       # Streaks table with count
      DataTable.tsx      # Generic table renderer with highlight mode
      NoResultDisplay.tsx # No-result and error state display
      RawJsonToggle.tsx  # Raw JSON toggle
      CopyButton.tsx     # Copy-to-clipboard button
      DevTools.tsx       # Structured query panel (route selector + kwargs)
      Loading.tsx        # Loading spinner
      ErrorBox.tsx       # Error display
    hooks/
      useQueryHistory.ts # In-session query history state hook
      useUrlState.ts     # URL search-param sync for shareable deep links
    test/
      setup.ts           # Vitest + jest-dom setup
      client.test.ts     # API client tests
      DataTable.test.tsx  # DataTable component tests
      ResultSections.test.tsx # Result rendering tests for all query classes
      UIComponents.test.tsx # EmptyState, NoResult, Loading, ErrorBox tests
      FreshnessStatus.test.tsx # Freshness panel rendering tests
      useUrlState.test.ts  # URL state parsing, building, and hook behavior tests
    App.tsx              # Main app component — wires state + components
    App.css              # All styles (dark theme, CSS custom properties)
    main.tsx             # React entry point
  vite.config.ts         # Dev proxy + build output path + vitest config
```

Build output lands in `src/nbatools/ui/dist/` and is served by FastAPI.
