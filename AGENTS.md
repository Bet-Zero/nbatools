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

Do not assume users will type full grammatical questions. Favor intent + slots over sentence grammar. See `docs/planning/master_completion_plan.md` for the top-level completion authority and active continuation, `docs/planning/query_surface_expansion_plan.md` for the completed Part 1 parser/query-surface plan, `docs/planning/parser_execution_completion_plan.md` for the closed Part 2 execution/data closure record, and the "Phase-based work queues" section below for how to pick up scheduled work.

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

### Data placement and dataset-structure rule

Data changes must preserve the repo's intentional dataset structure.

- New saved data is allowed only when it cleanly fits the lifecycle model (`raw`, `processed`, `derived`) and has a documented contract.
- Do not overwrite, silently repurpose, or quietly broaden canonical datasets to carry unrelated semantics.
- Do not mix lifecycle layers (for example, play-by-play-derived outputs into canonical raw game-log tables).
- Do not blur grains inside existing tables (for example, game-level, period-level, stint-level, and play-by-play-derived rows in one contract without an explicit approved design).
- Do not add ad hoc files or one-off tables without defined consumers and contract coverage.

If a new source is approved, implementation must document before broad rollout:

- dataset name
- lifecycle layer (`raw`, `processed`, or `derived`)
- grain
- join keys
- trust fields and coverage semantics
- fallback behavior when coverage/trust is missing
- why the chosen placement is structurally correct

Prefer a dedicated dataset and backfill path over mutating unrelated existing tables unless there is a strong documented reason approved in planning docs.

## Testing expectations

Every meaningful feature change should include appropriate tests.

### Test commands

Use the Makefile targets — do not invent ad hoc pytest invocations.

| Command               | What it does                                                                   | When to use                                                                                  |
| --------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `make test-impacted`  | Runs only tests whose file-level dependencies changed (pytest-testmon, serial) | Default for **localized** changes — small, leaf-level edits in a single module               |
| `make test-preflight` | All tests except `slow` (parallel via xdist, no testmon)                       | Default for **cross-cutting** changes, or any time the rules below apply                     |
| `make test`           | Full regression suite (parallel via xdist)                                     | Maximum-confidence validation: before merging, after broad changes, or explicitly risky work |

#### When to skip `make test-impacted`

Testmon runs serial (`-n0`). When it selects a large number of tests, it costs more wall time than `make test-preflight` running in parallel. Skip `test-impacted` and use `make test-preflight` instead when **any** of these apply:

- The diff touches a high fan-in module: `src/nbatools/query_service.py`, `src/nbatools/commands/natural_query.py`, parser core, the API layer, or shared fixtures/conftest files.
- The diff exceeds ~50 lines in a single `src/` file.
- A previous `test-impacted` run on the same change selected more than ~300 tests.
- Data files, environment variables, or dynamically loaded modules changed (testmon does not track these).

For these cases, use `make test-preflight` (parallel, broad). If you also want a tight iteration loop first, run the matching domain slice (`make test-query`, `make test-api`, `make test-parser`, etc.) — these run the whole slice, not the testmon subset.

#### Bail out fast when `test-impacted` runs slow

Testmon should complete a small-change run in well under a minute. If it has not finished within **60 seconds**, or if its progress indicator is climbing slower than ~10% per minute, **kill it and use a focused pytest invocation instead** — do not "wait it out." This is the most common cause of agent loops dragging from minutes to hours.

Replace the stalled `test-impacted` with a direct pytest call on the test files for the changed code, e.g.:

```bash
.venv/bin/pytest tests/test_<changed_file>.py -n0
```

Or run the matching domain slice (`make test-query`, `make test-api`, etc.). Either is sufficient for local "is my change sane" feedback.

#### CI is the backstop — local tests are for fast feedback

CI (`.github/workflows/ci.yml`) runs lint, `make test-unit`, and `make test` (the full parallel suite) on every PR. Local tests do not need to duplicate that coverage — they exist for fast iteration, not for full confidence. For most localized agent-loop changes:

- Run focused pytest on the directly-changed test files, **or** the matching `make test-<domain>` slice.
- Push the PR. CI runs the comprehensive suite in parallel while you move on.
- Trust CI to catch what focused tests miss.

Only run `make test` or `make test-preflight` locally when CI is unavailable, when you need maximum confidence before pushing (e.g., a risky cross-cutting change), or when investigating a CI-only failure.

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

| Code area changed                      | Recommended command                                               |
| -------------------------------------- | ----------------------------------------------------------------- |
| A single small command module          | `make test-impacted` (testmon catches it)                         |
| `natural_query.py` parsing helpers     | `make test-parser`, then `make test-preflight`                    |
| `natural_query.py` routing logic       | `make test-query`, then `make test-preflight`                     |
| `query_service.py`                     | `make test-query` and `make test-api`, then `make test-preflight` |
| A command module + NQ routing together | `make test-engine`, then `make test-preflight`                    |
| `api.py` or API response shape         | `make test-api`, then `make test-preflight`                       |
| `format_output.py` or result contracts | `make test-output`, then `make test-preflight`                    |
| Broad refactor or unclear scope        | `make test-preflight` (or `make test` for maximum confidence)     |

### Testmon + marker interaction

`pytest --testmon -m parser -n0` runs impacted tests that are also `parser`-marked.
This is an **intersection** — fewer tests than either flag alone.
Agents may combine them manually for narrow, fast feedback.
The Makefile subset targets intentionally avoid `--testmon` so they always run
the full slice.

**Workflow for agents:**

1. First, check the "When to skip `make test-impacted`" rules above against your diff. If any apply, jump to step 4.
2. Otherwise, while iterating, run `make test-impacted` for fast feedback on small, localized changes.
3. If the change is localized to a known subsystem, also run the matching `make test-<domain>` target. Steps 2–3 are the normal "done" signal for ordinary localized work.
4. Run `make test-preflight` for cross-cutting changes, high fan-in edits (`query_service.py`, `natural_query.py` routing, parser core, API layer, shared fixtures), diffs >~50 lines in one `src/` file, or any time `test-impacted` is selecting hundreds of tests.
5. Run `make test` only for maximum-confidence validation — before merging, or when even `test-preflight` is known to be unreliable for the change (dynamic imports, data file changes, monkey-patching).

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

| Agent phase                                              | Local command         | CI equivalent |
| -------------------------------------------------------- | --------------------- | ------------- |
| Active iteration on a small, localized change            | `make test-impacted`  | —             |
| Active iteration on a cross-cutting / high fan-in change | `make test-<domain>`  | —             |
| Subsystem confidence                                     | `make test-<domain>`  | —             |
| Before declaring work complete (localized)               | `make test-impacted`  | —             |
| Before declaring work complete (cross-cutting/risky)     | `make test-preflight` | —             |
| PR pushed                                                | —                     | `test-fast`   |
| Merged to main / nightly                                 | —                     | `test-full`   |

Local development uses `make test-impacted` (testmon) for the fastest feedback **on localized changes**. For cross-cutting changes it degenerates into "almost the whole suite, but serial," so use `make test-preflight` (parallel) instead. CI does not use testmon — it uses `make test-unit` (marker-based exclusion, parallel) as the fast path. Testmon state is a local development optimization only.

### Caching

CI caches pip dependencies via `actions/setup-python`'s `cache: pip`. Testmon state (`.testmondata`) is **not** cached in CI — it is a local development tool and its state is not meaningful across CI runs from clean checkouts.

### Key invariant

The full regression suite (`make test`) always runs on merge to main and nightly. This is the backstop. Do not remove it.

### Merge policy

This is a solo-developer repo. PRs are used for CI gating and atomic per-change history, not for review. The expected workflow is:

1. Open a PR for each queue item or logical unit of work
2. Wait for CI (`lint` + `test-fast`) to pass
3. Merge immediately once CI is green — no review wait

Permanent execution rule for queue-driven work:

1. A queue item is complete only when its acceptance criteria are met and required local tests pass.
2. As soon as that queue item is complete, commit it as its own PR-sized unit, push, and open the PR immediately.
3. Wait for CI (`lint` + `test-fast`) on that PR, then merge immediately once CI is green.
4. After merge, immediately continue to the next unchecked item in the active queue.
5. Do not treat one merged item as whole-plan completion; stop only when `master_completion_plan.md` says the whole plan is done, or when the queue's current step explicitly requires review-handoff/blocker escalation.

This gives us atomic per-item git history, keeps `main` green via CI, and avoids ceremony that doesn't apply to solo work. Do not leave PRs open waiting for review. Do not skip PRs in favor of direct-to-main commits unless explicitly told to.

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

`docs/planning/master_completion_plan.md` is the top-level completion authority.
When asked whether "the plan" is done, agents must interpret that as the whole
master plan unless the user explicitly names a narrower subplan. Closed
subplans, completed queues, explicit deferrals, placeholders, and parser-only
completion do not answer overall completion. If the master plan says the whole
plan is not done, follow the active continuation path named there.

#### How it works

- The **plan doc** (e.g. `docs/planning/query_surface_expansion_plan.md`) defines phases, scope, guardrails, and direction. It stays stable across a phase.
- The **active phase's work queue** (e.g. `docs/planning/phase_a_work_queue.md`) contains the current sequenced items, each with acceptance criteria and test commands. It changes continuously as items complete.
- The **final item of each queue** must either draft the next queue/phase or write an explicit review-handoff that names the files/artifacts to review and the immediate next action after review.

#### Completion-level rule

Planning docs must distinguish between:

- **parser/query-surface completion** — parser recognition, slot extraction, routing, and docs/tests for the surface are in place
- **execution/data completion** — the user-facing query family returns execution-backed results for the documented product boundary, or the family is explicitly out of scope by documented product decision
- **product/capability completion** — parser/query-surface completion and execution/data completion are both true, or the capability is explicitly out of scope by documented product decision

Do **not** let a plan, phase, or queue imply product completion from parser/route/placeholder completion alone. Explicit deferral is a tracked open state for the master plan unless a documented product decision marks the family out of scope. If a plan only completes a subsystem, it must label itself as Part 1 (or equivalent) and link to the continuation path.

#### Agent workflow

To pick up scheduled work on a phase-based plan, use this prompt:

> Read the relevant plan doc and the active work queue it explicitly identifies as next. Find the next unchecked item. Review the reference docs it cites. Execute the item per its acceptance criteria. Run the specified test commands. When everything passes, check the item off, update any docs the item requires, commit as a PR-sized unit, open the PR immediately, wait for CI, merge once green, then continue to the next unchecked item.

The active queue is the queue named by the plan as the current continuation step. Do not infer global product completion from the absence of unchecked items in a subsystem-only queue. No separate prompt is needed for phase transitions as long as the current queue's final task drafts the next queue or writes the explicit review-handoff.

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
