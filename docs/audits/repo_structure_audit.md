# Repository Structure Audit

**Date:** 2026-04-17
**Scope:** Folder/file architecture assessment against `docs/project_conventions.md`

---

## 1. Executive Summary

### Overall repo organization health: Good — with one clear structural bottleneck

The repo's architecture is well-separated at the **layer** level: CLI presentation (`cli.py`, `cli_apps/*`), engine logic (`commands/*`), service facade (`query_service.py`), API layer (`api.py`), and frontend (`frontend/`). That layering is correct and matches the conventions doc.

The main organizational weakness is that `commands/` is a **flat directory containing 60+ files** spanning five distinct lifecycles — query commands, data ingestion, data processing, operational tooling, infrastructure/framework, and analysis. This makes the directory harder to navigate as scale grows, and blurs which files are engine-core vs. operational vs. experimental.

### Biggest strengths

1. **Layer separation is clean.** CLI, API, query service, and frontend are distinct and thin. Business logic lives in `commands/`. The conventions doc's separation of concerns is faithfully implemented.
2. **Private helper convention works well.** The `_`-prefixed helpers (`_constants.py`, `_date_utils.py`, `_parse_helpers.py`, etc.) clearly signal internal-only modules. The decomposition of `natural_query.py` into these helpers was well-executed.
3. **CLI app grouping mirrors the conventions doc.** `cli_apps/` has `raw.py`, `processing.py`, `ops.py`, `analysis.py`, `pipeline.py`, `queries.py` — matching the intended surface groups from §3.7 of conventions.
4. **Frontend folder structure is clean and scalable.** Components, hooks, API client, storage, and tests are logically separated with clear naming.
5. **Docs are comprehensive.** 22 docs covering current state, conventions, contracts, guides, audits, and design targets.

### Biggest organizational risks

1. **`commands/` is a flat bucket of 60+ files with no sub-organization.** Query modules, data-pull modules, build modules, ops modules, framework modules, and analysis modules all live at the same level. A new contributor cannot quickly tell what's "engine-core" vs. "pipeline-ops" vs. "infrastructure."
2. **Docs have accumulated audit/plan artifacts alongside living guides.** 7 of the 22 docs are historical audit snapshots or completed plans. These are useful for reference but clutter the docs directory when someone is looking for current guidance.
3. **Tests are flat with no sub-organization.** 43 test files in one directory, named by feature area but with no grouping. This is manageable now but will become harder to navigate.

---

## 2. Current Structure Assessment

### 2.1 Backend: `src/nbatools/`

#### What is well-organized

| Area | Assessment |
|---|---|
| **Top-level package files** | Clean. `__init__.py` (4 lines), `__main__.py` (5 lines), `api.py` (211 lines), `api_cli.py` (32 lines), `query_service.py` (660 lines), `cli.py` (137 lines). Each has a clear, single purpose. |
| **`cli_apps/` grouping** | Good. Six CLI surface groups (`raw`, `processing`, `ops`, `analysis`, `pipeline`, `queries`) map directly to conventions §3.7. Each is a thin argument-handling wrapper. |
| **Private helper extraction** | Excellent. Nine `_`-prefixed helpers extracted from `natural_query.py` during the cleanup phase. Naming is consistent: `_constants.py`, `_date_utils.py`, `_parse_helpers.py`, `_natural_query_execution.py`, `_leaderboard_utils.py`, `_matchup_utils.py`, `_occurrence_route_utils.py`, `_playoff_record_route_utils.py`, `_seasons.py`. |
| **Query service as facade** | Correct. `query_service.py` is the single programmatic entry point. Both CLI and API dispatch through it. |

#### What is inconsistent

| Issue | Details |
|---|---|
| **`commands/` is flat across five lifecycles** | The directory mixes: (a) 21 query command modules, (b) 9 data-pull modules, (c) 4 data-build modules, (d) 10 ops/pipeline modules, (e) 8 infrastructure/framework modules, (f) 3 analysis modules, (g) 9 private helpers. All 60+ files at the same level. |
| **Naming convention split** | Private helpers use `_` prefix. Query commands use domain names (`player_game_summary.py`). Pipeline modules use verb prefixes (`pull_`, `build_`, `backfill_`). This is acceptable but the verb-prefix convention is the only structural signal for lifecycle — there's no directory-level separation. |
| **`run_tests.py` in `commands/ops/`** | A test runner command (`commands/ops/run_tests.py`, 21 lines) lives in the ops subpackage. It's wired through `cli_apps/ops.py`. |

#### What will become a future pain point

| Risk | Details |
|---|---|
| **Adding new query commands** | With 21 query commands and growing, the flat `commands/` directory will become harder to scan. A contributor looking for "where do streak commands live" has to mentally filter past `pull_*`, `build_*`, `backfill_*`, `pipeline.py`, `format_output.py`, etc. |
| **Adding new pipeline stages** | If the data pipeline grows (new sources, new derived datasets), `pull_*` and `build_*` files will multiply in the same flat directory, further diluting the query-command signal. |
| **Private helpers growing** | There are already 9 `_`-prefixed helpers. If more are extracted (which is healthy), the `_` prefix alone won't distinguish "NQ parsing helpers" from "data utility helpers" from "general framework helpers." |

### 2.2 CLI / Service / API boundaries

#### What is well-organized

- **`cli.py`** is registration-only (137 lines). It registers sub-apps and the `ask`/`version`/`test`/`serve` commands. No business logic.
- **`cli_apps/*`** are argument-handling wrappers. `queries.py` is the largest at 663 lines (many structured commands), but its logic is "parse typer args → call command module."
- **`api.py`** is genuinely thin (211 lines). FastAPI routes, Pydantic models, CORS config, static file serving.
- **`query_service.py`** is the correct facade layer. It holds `execute_natural_query()`, `execute_structured_query()`, and the `QueryResult` envelope.

#### Remaining placement oddities

| Item | Notes |
|---|---|
| **`api_cli.py` at package root** | This is a 32-line uvicorn launcher. It works fine here, but it's the only non-core file at the package root. Low-priority. |
| **`freshness.py` in `commands/`** | `freshness.py` (418 lines) provides data-freshness metadata used by the API layer. It's imported by both `api.py` and `query_service.py`. It's not a user-facing query command — it's infrastructure. Functionally correct where it is, but conceptually it's more "engine metadata" than "command." |

### 2.3 Frontend: `frontend/`

#### Current structure

```
frontend/src/
  api/          — client.ts, types.ts, savedQueryTypes.ts
  components/   — 21 component files (well-named, one per concern)
  hooks/        — 3 hooks (useQueryHistory, useSavedQueries, useUrlState)
  storage/      — savedQueryStorage.ts
  test/         — 8 test files + setup.ts
  App.tsx, App.css, main.tsx, index.css, vite-env.d.ts
```

#### Assessment

**This is well-organized and scalable.** The frontend structure follows React conventions well:

- `api/` clearly separates API types and client code
- `components/` has one file per UI concern with descriptive names
- `hooks/` has focused, well-scoped custom hooks
- `storage/` properly isolates localStorage persistence
- `test/` is co-located and has good coverage

#### Minor observations

| Item | Notes |
|---|---|
| **`savedQueryTypes.ts` in `api/`** | Types for saved queries live in `api/` but saved queries are a local-only feature (no API calls). These types could arguably live in `storage/` or alongside the hook. Low-priority cosmetic issue. |
| **`App.css` at 1,444 lines** | All styles in one file. Works for now but could benefit from component-scoped styles or CSS modules if the UI grows significantly. Not a structural problem yet. |
| **No `utils/` or `lib/` directory** | Not needed yet. If shared frontend helpers emerge, having a clear place for them would help. |

### 2.4 Docs: `docs/`

#### Current inventory (22 files)

**Living guides (actively maintained):**
- `current_state_guide.md` — shipped behavior reference
- `query_guide.md` — full query reference
- `quick_query_guide.md` — quick-start examples
- `project_conventions.md` — engineering rules (source of truth)
- `system_conventions.md` — data/naming conventions
- `data_contracts.md` — dataset definitions
- `data_catalog.md` — data catalog
- `pipeline_runbook.md` — pipeline operations guide
- `ui_guide.md` — web UI guide
- `roadmap.md` — future plans
- `index.md` — docs navigation hub

**Architecture design docs (semi-living):**
- `api_layer.md` — API design
- `query_service_layer.md` — service layer design
- `structured_result_layer.md` — result object design
- `result_contracts.md` — result shape targets
- `data_freshness_plan.md` — freshness system design

**Historical audits and completed plans (reference-only):**
- `architecture_hygiene_audit.md` — pre-cleanup architecture audit
- `natural_query_cleanup_plan.md` — NQ cleanup plan (partially completed)
- `natural_query_final_scope_audit.md` — final NQ scope audit
- `glue_layer_scope_audit.md` — query_service/format_output audit
- `result_contracts_audit.md` — result contracts pre-implementation audit
- `scripts_retirement.md` — scripts retirement record

#### What is well-organized

- `index.md` provides a clear reading order and navigation
- Living guides are well-separated from design targets
- `project_conventions.md` is comprehensive and authoritative

#### What is inconsistent

| Issue | Details |
|---|---|
| **Historical audits mixed with living docs** | 6 files are completed audit snapshots or finished plans. They're useful as reference but they sit alongside current guides with no visual or organizational separation. A contributor scanning the `docs/` directory sees `architecture_hygiene_audit.md` next to `api_layer.md` with no signal that one is historical and the other is current. |
| **No naming convention signals doc lifecycle** | Living guides, design targets, historical audits, and completed plans all use the same naming pattern. The `index.md` provides some grouping but the flat directory doesn't. |

### 2.5 Tests: `tests/`

#### Current structure

43 test files, all flat in `tests/`, with one `conftest.py`. Test files are named by feature area (`test_natural_query_parser.py`, `test_api.py`, etc.).

#### Assessment

- **Naming is descriptive and consistent.** `test_<feature>.py` pattern throughout.
- **Markers provide logical grouping** (`parser`, `query`, `engine`, `api`, `output`) even without directory-based grouping.
- **Single `conftest.py`** manages shared fixtures and the `needs_data` marker.

This flat structure is adequate for now. The marker-based grouping and Makefile targets (`test-parser`, `test-query`, etc.) provide the organizational value that directories would provide in a larger project. At 43 files, directory-based grouping would add value but is not urgent.

---

## 3. Recommended Folder Architecture

### 3.1 `commands/` — lifecycle sub-packages ✅ IMPLEMENTED

The `commands/` directory has been reorganized into lifecycle-based subpackages:

```
src/nbatools/commands/
  __init__.py
  
  # ── Query engine (the core product) ──────────────────────
  # Query command modules — what users interact with
  game_finder.py
  game_summary.py
  player_advanced_metrics.py
  player_compare.py
  player_game_finder.py
  player_game_summary.py
  player_occurrence_leaders.py
  player_split_summary.py
  player_streak_finder.py
  playoff_history.py
  season_leaders.py
  season_team_leaders.py
  team_compare.py
  team_occurrence_leaders.py
  team_record.py
  team_split_summary.py
  team_streak_finder.py
  top_player_games.py
  top_team_games.py
  
  # ── NQ routing/parsing infrastructure ────────────────────
  natural_query.py
  _constants.py
  _date_utils.py
  _leaderboard_utils.py
  _matchup_utils.py
  _natural_query_execution.py
  _occurrence_route_utils.py
  _parse_helpers.py
  _playoff_record_route_utils.py
  _seasons.py
  query_boolean_parser.py
  entity_resolution.py
  
  # ── Engine infrastructure ────────────────────────────────
  data_utils.py
  format_output.py
  freshness.py
  metric_registry.py
  structured_results.py
  
  # ── Data pipeline ────────────────────────────────────────
  pipeline/
    __init__.py
    orchestrator.py          ← was pipeline.py (renamed to avoid package/module collision)
    pull_games.py
    pull_player_game_stats.py
    pull_player_season_advanced.py
    pull_rosters.py
    pull_schedule.py
    pull_standings_snapshots.py
    pull_team_game_stats.py
    pull_team_season_advanced.py
    pull_teams.py
    build_game_features.py
    build_league_season_stats.py
    build_player_game_features.py
    build_team_game_features.py
    validate_raw.py
    backfill_range.py
    backfill_season.py
    auto_refresh.py
  
  # ── Ops ──────────────────────────────────────────────────
  ops/
    __init__.py
    inventory.py
    show_manifest.py
    show_team_history.py
    update_manifest.py
    run_tests.py
  
  # ── Analysis ─────────────────────────────────────────────
  analysis/
    __init__.py
    analyze_3pt_battles.py
    battle_summary.py
    advanced_metrics.py
```

**Why this structure:**

**Implementation notes:**

- Query command modules stay at the top level of `commands/` because they **are** the engine. They're what `query_service.py` dispatches to.
- Pipeline, ops, and analysis files live in sub-packages. These are accessed only through `cli_apps/` wrappers, not through the query service.
- The `_`-prefixed NQ helpers and engine infrastructure stay at the top level alongside the query commands they support.
- `pipeline.py` was renamed to `orchestrator.py` to avoid the Python package/module name collision with the `pipeline/` directory.
- `cli_apps/` import paths use the subpackage prefix (e.g., `from nbatools.commands.pipeline.pull_games import run`).
- `pipeline/orchestrator.py` imports from `commands/ops/update_manifest` (cross-subpackage dependency for manifest updates).

### 3.2 `docs/` — add a historical reference subdirectory

```
docs/
  index.md
  
  # Living guides
  current_state_guide.md
  quick_query_guide.md
  query_guide.md
  project_conventions.md
  system_conventions.md
  data_contracts.md
  data_catalog.md
  pipeline_runbook.md
  ui_guide.md
  roadmap.md
  repo_structure_audit.md
  
  # Architecture design docs
  api_layer.md
  query_service_layer.md
  structured_result_layer.md
  result_contracts.md
  data_freshness_plan.md
  
  # Historical reference
  archive/
    architecture_hygiene_audit.md
    natural_query_cleanup_plan.md
    natural_query_final_scope_audit.md
    glue_layer_scope_audit.md
    result_contracts_audit.md
    scripts_retirement.md
```

**Why:** Moving completed audits and finished plans to `archive/` reduces noise in the main docs directory. These files are still valuable for understanding decisions, but they shouldn't compete for attention with living guides.

### 3.3 Frontend — no changes needed

The current structure is clean and scalable. Component naming is consistent, API/hooks/storage/test separation is correct. No reorganization needed unless the component count doubles.

### 3.4 Tests — optional marker-based subdirectories

If the test count grows past ~60 files, consider:

```
tests/
  conftest.py
  parser/
  query/
  engine/
  api/
  output/
```

This matches the existing marker-based grouping and Makefile targets. **Not needed yet** — the marker system provides the same value without the directory overhead.

---

## 4. Top Structure Cleanup Opportunities

### Priority 1: Move pipeline/ops/analysis into sub-packages ✅ DONE

**Status:** Implemented. 26 files moved into `commands/pipeline/`, `commands/ops/`, and `commands/analysis/`. 36 files touched total (mostly import-line updates). Zero test regressions.

### Priority 2: Move completed audits to `docs/archive/` (high value, zero risk)

**Value:** Declutters the docs directory. Makes it immediately clear which docs are current guidance vs. historical reference.

**Risk:** Zero. No code depends on doc file paths. `index.md` would need updated links.

**Safe now?** Yes. Can be done immediately.

### Priority 3: Evaluate `freshness.py` placement (low value, low risk)

**Value:** Minor clarity improvement. `freshness.py` is infrastructure/metadata, not a query command. It could move to the package root alongside `query_service.py`, since both are "engine metadata" used by the API layer.

**Risk:** Low. Two import sites (`api.py`, `query_service.py`).

**Safe now?** Yes, but low priority. Current placement is functional.

### Priority 4: Test directory sub-grouping (low value, low risk — future)

**Value:** Would make the test directory navigable as it grows. Currently manageable at 43 files.

**Risk:** Low but requires updating any test-discovery configuration.

**Safe now?** Not urgent. Revisit when test count exceeds ~60 files.

---

## 5. Recommended Implementation Sequence

### Phase 1 — Safe, immediate cleanups (this pass or next)

1. **Move completed audit/plan docs to `docs/archive/`.**
   - Move 6 files: `architecture_hygiene_audit.md`, `natural_query_cleanup_plan.md`, `natural_query_final_scope_audit.md`, `glue_layer_scope_audit.md`, `result_contracts_audit.md`, `scripts_retirement.md`
   - Update `docs/index.md` links
   - Zero code risk

### Phase 2 — Pipeline/ops/analysis sub-packaging ✅ DONE

All three sub-packages created and verified:

2. **`commands/pipeline/`** — 18 files moved (pull_*, build_*, validate_raw, backfill_*, auto_refresh, orchestrator.py)
3. **`commands/ops/`** — 5 files moved (inventory, show_manifest, show_team_history, update_manifest, run_tests)
4. **`commands/analysis/`** — 3 files moved (analyze_3pt_battles, battle_summary, advanced_metrics)

Import updates applied to: `cli_apps/raw.py`, `cli_apps/processing.py`, `cli_apps/ops.py`, `cli_apps/pipeline.py`, `cli_apps/analysis.py`, `tests/test_pipeline.py`, `tests/test_auto_refresh.py`, and three internal pipeline modules.

`pipeline.py` renamed to `orchestrator.py` to avoid package/module name collision.

### Phase 3 — Evaluate after Phase 2 settles

5. **Assess whether engine infrastructure modules need grouping.**
   - After pipeline/ops/analysis are sub-packaged, reassess if the remaining `commands/` top-level (query commands + NQ helpers + engine infrastructure) is clean enough or if further grouping is warranted.
   - Likely outcome: it will be clean enough. The query commands, NQ helpers, and engine infrastructure modules are all part of the same "engine-core" concern.

### What should explicitly NOT be reorganized yet

| Item | Why not |
|---|---|
| **Query command modules** | They're the core engine. Moving them into a sub-package would change every import in `query_service.py`, `cli_apps/queries.py`, `natural_query.py`, and many tests. The churn is high and the benefit is marginal — they already live where conventions say they should. |
| **NQ private helpers** | The `_`-prefix convention works. They're tightly coupled to `natural_query.py` and belong alongside it. Moving them to a sub-package would add import complexity with no clarity gain. |
| **Frontend structure** | It's already well-organized. Reorganizing components into subdirectories (e.g., `components/sections/`, `components/shared/`) would add folder depth without solving a real problem at the current scale. |
| **Test directory** | Marker-based grouping provides sufficient organization at 43 files. Directory-based grouping becomes worthwhile only if the count grows significantly. |

---

## 6. Where New Code Goes — Cheat Sheet

### Backend

| What you're adding | Where it goes |
|---|---|
| New query command (e.g., `player_clutch_stats.py`) | `src/nbatools/commands/` (top level) |
| New NQ parsing helper (e.g., clutch-time detection) | `src/nbatools/commands/_parse_helpers.py` or new `_clutch_utils.py` |
| New route-family helper (e.g., occurrence-like compound routing) | `src/nbatools/commands/_<family>_route_utils.py` |
| New execution/runtime helper | `src/nbatools/commands/_natural_query_execution.py` |
| New stat aliases or constants | `src/nbatools/commands/_constants.py` |
| New date/season parsing | `src/nbatools/commands/_date_utils.py` or `_seasons.py` |
| New data pull source | `src/nbatools/commands/pipeline/pull_<source>.py` |
| New derived dataset builder | `src/nbatools/commands/pipeline/build_<dataset>.py` |
| New ops/maintenance tool | `src/nbatools/commands/ops/<tool>.py` |
| New structured result type | `src/nbatools/commands/structured_results.py` |
| New output format support | `src/nbatools/commands/format_output.py` |
| New metric definition | `src/nbatools/commands/metric_registry.py` |
| New entity alias | `src/nbatools/commands/entity_resolution.py` |
| New API endpoint | `src/nbatools/api.py` |
| New CLI command group | `src/nbatools/cli_apps/<group>.py` + register in `cli.py` |
| New structured route wiring | `src/nbatools/query_service.py` (add to route dispatch) |

### Frontend

| What you're adding | Where it goes |
|---|---|
| New result section renderer | `frontend/src/components/<Section>Section.tsx` |
| New shared UI component | `frontend/src/components/<Name>.tsx` |
| New API type | `frontend/src/api/types.ts` |
| New API call | `frontend/src/api/client.ts` |
| New custom hook | `frontend/src/hooks/use<Name>.ts` |
| New local storage feature | `frontend/src/storage/<feature>Storage.ts` |
| New component test | `frontend/src/test/<Component>.test.tsx` |

### Docs

| What you're writing | Where it goes |
|---|---|
| Shipped behavior update | `docs/current_state_guide.md` |
| Query reference update | `docs/query_guide.md` |
| Dataset schema change | `docs/data_contracts.md` |
| Engineering rule change | `docs/project_conventions.md` |
| Future plan | `docs/roadmap.md` |
| UI documentation | `docs/ui_guide.md` |
| Pipeline operations | `docs/pipeline_runbook.md` |
| Audit or completed plan | `docs/archive/<name>.md` (after Phase 1) |

### Tests

| What you're testing | Where it goes | Marker |
|---|---|---|
| Parsing/entity resolution | `tests/test_<feature>.py` | `@pytest.mark.parser` |
| NQ routing/intent detection | `tests/test_<feature>.py` | `@pytest.mark.query` |
| Command computation | `tests/test_<feature>.py` | `@pytest.mark.engine` |
| API endpoints | `tests/test_api.py` | `@pytest.mark.api` |
| Output formatting/contracts | `tests/test_<feature>.py` | `@pytest.mark.output` |

---

## 7. ~~Optional: Highest-Value Follow-Up Prompt~~ ✅ COMPLETED

The pipeline/ops/analysis sub-packaging (Phase 2) has been implemented. The prompt below was used as a reference for the implementation.

> *(Historical reference — task completed)*

---

## 8. Notes

### Structural changes made

**Phase 2 (pipeline/ops/analysis sub-packaging):** Implemented. 26 files moved into three subpackages. 36 files touched. `pipeline.py` renamed to `orchestrator.py`. Zero test regressions (1294 passed, same pre-existing failures). All imports updated across `cli_apps/`, `commands/`, and `tests/`.

### Relationship to prior audits

This audit builds on but does not replace:
- `architecture_hygiene_audit.md` — focused on code-level architecture (natural_query decomposition, result contracts, etc.)
- `natural_query_final_scope_audit.md` — focused on NQ file-level decomposition
- `glue_layer_scope_audit.md` — focused on query_service and format_output scope

Those audits addressed **code boundaries and module responsibilities**. This audit addresses **folder/file organization and where things physically live**.
