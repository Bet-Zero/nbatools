# Project Conventions

This document defines the engineering conventions for `nbatools`.

It is the source of truth for how new work should be structured as the repo evolves from a CLI-first development surface into a reusable NBA search engine that can later power a UI and API.

---

## 1. Long-term direction

The product goal is a **UI-based NBA search app with text input**.

The repo now has three consumer surfaces: a CLI (development/power-user), a FastAPI HTTP layer, and a React + TypeScript + Vite web UI. The CLI and web UI are both thin presentation layers over a shared query engine.

That means the repo should be built so that:

- the core query/analytics logic is reusable outside any single interface
- natural language parsing is reusable outside the CLI
- output contracts are consumed by the CLI, the React UI, and any API client
- terminal presentation and browser presentation are treated as layers, not the product core

---

## 2. Architecture principles

### 2.1 Local-first engine

The current implementation is local-first and built around:

- CSV-backed datasets
- pandas-based processing and query logic
- command modules in `src/nbatools/commands/*`

This is acceptable for the current phase.

CSV is the current storage format, not a permanent ideological choice. Storage changes should be driven by real needs such as query complexity, performance, or maintainability.

### 2.2 Engine first, interface second

The repo should optimize for:

1. correct data behavior
2. stable query semantics
3. test-backed iteration
4. reusable command/query internals
5. CLI presentation
6. frontend iteration

### 2.3 Explicit over magical

Prefer explicit route classes, explicit dataset usage, explicit output sections, and explicit tests.

Do not rely on accidental behavior or undocumented coupling.

---

## 3. Separation of concerns

## 3.1 `src/nbatools/cli.py`

Responsibilities:

- top-level app registration
- command group registration
- user-facing CLI entrypoints

Should not contain:

- business logic
- heavy data processing
- natural query parsing internals

## 3.2 `src/nbatools/cli_apps/*`

Responsibilities:

- structured command argument definitions
- CLI-level export wiring
- calling command-layer functions

Should not contain:

- core analytics logic
- query semantics that belong in command modules
- ad hoc domain-specific workarounds

## 3.3 `src/nbatools/commands/*`

The `commands/` directory is organized into lifecycle-based groups:

**Top-level (query engine core):**
- Query command modules (e.g., `player_game_summary.py`, `team_streak_finder.py`)
- Natural-query routing/parsing (`natural_query.py` + `_`-prefixed helpers)
- Engine infrastructure (`data_utils.py`, `format_output.py`, `freshness.py`, `metric_registry.py`, `structured_results.py`, `entity_resolution.py`, `query_boolean_parser.py`)

**`commands/pipeline/`** — data ingestion, processing, and refresh orchestration:
- `pull_*.py` — raw data source pulls
- `build_*.py` — derived dataset builders
- `validate_raw.py` — raw data validation
- `backfill_*.py` — historical backfill tools
- `auto_refresh.py` — automated refresh loop
- `orchestrator.py` — pipeline orchestration (refresh, rebuild, backfill workflows)

**`commands/ops/`** — operational/maintenance tools:
- `inventory.py`, `show_manifest.py`, `update_manifest.py`, `show_team_history.py`, `run_tests.py`

**`commands/analysis/`** — domain analyses outside the main query surface:
- `analyze_3pt_battles.py`, `battle_summary.py`, `advanced_metrics.py`

Query command modules and engine infrastructure stay at the `commands/` top level because they **are** the engine core — what `query_service.py` dispatches to.

## 3.4 `src/nbatools/commands/natural_query.py`

Responsibilities:

- natural-language parsing helpers
- alias detection
- intent detection
- route selection
- orchestration across existing structured command behavior

Should not become the permanent home for all business logic.

If a feature requires substantial calculation, reusable filtering logic, or domain-specific analysis, that logic should live in its own command/helper module and be called from `natural_query.py`.

## 3.5 Formatting/output layer

Pretty formatting is a presentation layer.

Guidelines:

- raw outputs should remain usable by machines
- pretty output should not define core semantics
- the React UI consumes the same `QueryResponse` envelope as JSON export
- if the UI needs a value that only exists in pretty CLI output, add it to the structured result

## 3.6 Frontend (`frontend/`)

Responsibilities:

- typed API client (fetch wrappers + TypeScript interfaces)
- React components for rendering query results
- UI state management (loading, error, result display)
- styling

Should not contain:

- business logic, filtering, or analytics
- data transformations that belong in the engine
- query parsing or routing decisions

The frontend calls the API and renders what it gets back.

After any frontend source change, rebuild with `cd frontend && npm run build` so the FastAPI-served build stays current.

## 3.7 Pipeline / ops / analysis subpackages

These lifecycle groups now live in dedicated subpackages under `commands/`:

- `commands/pipeline/` → source ingestion (`pull_*`), derived datasets (`build_*`), validation, backfills, auto-refresh, and the pipeline orchestrator
- `commands/ops/` → maintenance, manifests, inventory, team history
- `commands/analysis/` → domain analyses outside the main natural query surface

They are accessed through `cli_apps/` wrappers and are **not** part of the query engine dispatch path. Their import paths use the subpackage prefix (e.g., `from nbatools.commands.pipeline.pull_games import run`).

---

## 4. Query design conventions

## 4.1 Every natural query feature should map to a clear structured behavior

Natural language is an interface layer, not a separate product logic path.

Before adding a new natural feature, identify the underlying structured behavior it maps to.

If the behavior cannot be expressed clearly in structured form, it should be reconsidered before shipping.

## 4.2 Preferred route classes

Use explicit conceptual route classes whenever possible:

- finder
- summary
- split summary
- comparison
- leaderboard
- streak
- matchup / head-to-head

New features should fit into one of these route classes or justify a new one clearly.

## 4.3 Keep player/team symmetry intentional

Player and team functionality should be aligned where appropriate, but not forced into fake symmetry.

Good symmetry:

- finder behavior
- summary behavior
- split behavior
- export behavior

Acceptable asymmetry:

- player-only advanced rate metrics
- player-specific streak or sample-aware calculations
- team-specific season/pace/offensive metrics

## 4.4 Avoid ambiguous route expansion without tests

If a new parser rule broadens what a phrase can mean, tests should confirm the intended route for representative examples.

Do not assume “it probably routes correctly” is enough.

---

## 5. Data design conventions

## 5.1 Every dataset must have a defined grain

Examples:

- one row per player-game
- one row per team-game
- one row per player-season
- one row per team-season

A dataset should not be treated as a generic table with accidental columns.

## 5.2 Commands should depend on known data contracts

A command should know:

- which dataset(s) it reads
- expected grain
- required columns
- derived columns it depends on

Do not let commands depend on “whatever columns happen to exist.”

## 5.3 Derived metrics must define their sample source

For sample-aware metrics, the source sample must be clear.

This is especially important for:

- USG%
- AST%
- REB%
- any future filtered-sample or matchup-aware metrics

## 5.4 Data contracts should be documented

When datasets, required columns, or downstream consumers change, update `docs/reference/data_contracts.md`.

---

## 6. Naming conventions

## 6.1 File naming

Use descriptive, domain-aligned names.

Examples:

- `player_game_summary.py`
- `team_streak_finder.py`
- `season_team_leaders.py`

Do not use vague names like `helpers2.py`, `misc_queries.py`, or `temp_parser.py`.

## 6.2 Command naming

Structured command names should be explicit and user-readable.

Prefer names like:

- `player-game-summary`
- `team-split-summary`
- `season-leaders`
- `team-streak-finder`

## 6.3 Route naming

Natural query route names should stay aligned with structured command concepts.

Prefer stable route identifiers over ad hoc intent names.

## 6.4 Output section labels

Keep machine-readable section labels stable where already established.

Examples:

- `SUMMARY`
- `BY_SEASON`
- `COMPARISON`
- `SPLIT_COMPARISON`

Do not rename output sections casually, because they may be consumed downstream.

---

## 7. Testing conventions

## 7.1 Parser changes need parser tests

If parsing, route selection, or query-intent behavior changes, update parser tests.

## 7.2 Behavior changes need smoke tests

If a command’s real behavior or user-visible output changes, add or update smoke tests.

## 7.3 Calculations need unit/formula tests

If you add a metric, scoring rule, or streak logic, add targeted tests for the calculation itself.

## 7.4 Exports need export tests

If raw/structured output behavior changes, validate:

- CSV
- TXT
- JSON

as applicable.

## 7.5 Regression fixes need regression tests

If a bug is fixed once, protect it with a test.

## 7.6 Docs must not get ahead of verification

README and current-state docs should reflect verified shipped behavior only.

Do not advertise new capability just because code was added. Code + tests + verified behavior come first.

---

## 8. Refactor conventions

## 8.1 Fix duplication when you touch duplication

If you are already editing an area with repeated branches or mirrored logic, prefer removing duplication instead of adding another copy.

## 8.2 Avoid architecture churn

Do not perform broad rewrites unless there is a clear payoff in:

- correctness
- maintainability
- reduced duplication
- UI/API readiness

## 8.3 Keep compatibility intentional

Temporary compatibility code should be:

- minimal
- documented if non-obvious
- removed when no longer needed

## 8.4 Split large modules before they become unstable

If `natural_query.py` or another command module becomes too large to reason about safely, split helpers intentionally by responsibility instead of letting the file become a permanent catch-all.

Potential split boundaries include:

- date parsing
- leaderboard detection
- streak parsing
- matchup parsing
- grouped boolean orchestration

---

## 9. UI conventions

## 9.1 Core behavior must remain interface-agnostic

The same underlying logic should be callable from:

- CLI
- React web UI
- FastAPI / any HTTP client

## 9.2 Prefer structured outputs beneath pretty outputs

Even if the CLI presents pretty text, the underlying behavior should still produce stable structured/raw outputs.

## 9.3 Avoid terminal-only or browser-only assumptions in core logic

Core commands should not depend on terminal formatting, color, width, or print-only semantics. Equally, they should not depend on browser APIs or React rendering.

## 9.4 UI components map to result sections

The React frontend already renders these result types:

- summary tables
- comparison tables
- split tables
- streak results
- leaderboard tables
- finder / matching-games tables
- no-result status messages

New result types should produce structured data that the existing component set can render. If a new layout is needed, add a component — do not change the engine to match a rendering assumption.

## 9.5 Frontend rebuild after changes

After any change to files under `frontend/`, run `cd frontend && npm run build` to rebuild the production assets that FastAPI serves. Forgetting this leaves the served UI out of sync with the source.

---

## 10. Documentation roles

## 10.1 `README.md`

Use for:

- project overview
- what the tool is
- high-level examples
- broad user-facing capability summary

## 10.2 `docs/reference/current_state_guide.md`

Use for:

- verified shipped behavior only
- current supported query types
- current supported language/features
- current tested state

Do not use it for speculative or planned behavior.

## 10.3 `docs/planning/roadmap.md`

Use for:

- future work
- phased milestones
- planned expansions
- not-yet-shipped ideas

## 10.4 `docs/reference/data_contracts.md`

Use for:

- dataset definitions
- grain
- required columns
- producers and consumers

## 10.5 `docs/operations/ui_guide.md`

Use for:

- web UI setup and dev workflow
- frontend file layout and component reference
- how the React UI communicates with the API

## 10.6 `AGENTS.md`

Use for:

- repo workflow expectations for coding agents
- implementation guardrails
- testing and doc update expectations

---

## 11. Feature delivery checklist

Before calling a feature shipped, confirm:

- structured behavior exists or was intentionally extended
- natural query routing maps clearly to that behavior
- parser tests were updated if parsing changed
- smoke tests were added if behavior changed
- formula/export tests were added if relevant
- docs were updated only after verification
- the change improves the reusable engine, not just the CLI surface
- if the API response shape changed, the React frontend was updated
- if the frontend changed, `npm run build` was run

If that chain is incomplete, the feature is not done yet.
