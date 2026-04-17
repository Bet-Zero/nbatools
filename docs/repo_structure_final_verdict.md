# Repository Structure — Final Verdict

**Date:** 2026-04-17
**Purpose:** Determine whether the repo-structure phase is complete enough to stop and return to feature work, or whether one more structural cleanup is still clearly worth doing.

---

## 1. Executive Verdict

**The repo-structure phase is done enough to stop now.**

The major structural work has been completed:

- `commands/` decomposed into lifecycle subpackages (`pipeline/`, `ops/`, `analysis/`)
- `natural_query.py` decomposed from ~4,000 lines into routing core (~1,041 lines) plus 9 extracted helper modules
- `docs/` reorganized into role-based subdirectories (`reference/`, `architecture/`, `operations/`, `planning/`, `audits/`)
- Conventions doc updated with "where new code goes" cheat sheet
- CLI / query service / API boundaries are clean and thin
- Frontend structure is well-organized

No remaining structural issue is important enough to justify another reorganization pass before returning to feature work.

---

## 2. Area-by-Area Final Check

### Backend folder structure — ✅ Good enough

`src/nbatools/` has 7 top-level files, each with a clear single purpose:

| File | Role | Lines |
|---|---|---|
| `__init__.py` | Package init | 4 |
| `__main__.py` | Entry point | 5 |
| `cli.py` | CLI registration | 137 |
| `api.py` | FastAPI HTTP layer | ~211 |
| `api_cli.py` | Uvicorn launcher | 32 |
| `query_service.py` | Engine facade | 660 |

No structural problems here.

### Commands subpackage layout — ✅ Good enough

37 files at the `commands/` top level, organized as:

- **19 query command modules** — the engine core (`player_game_summary.py`, `team_streak_finder.py`, etc.)
- **9 `_`-prefixed NQ helpers** — parsing infrastructure tightly coupled to `natural_query.py`
- **6 engine infrastructure modules** — `format_output.py`, `structured_results.py`, `freshness.py`, `data_utils.py`, `metric_registry.py`, `entity_resolution.py`
- **2 orchestration modules** — `natural_query.py`, `query_boolean_parser.py`
- **1 `__init__.py`**

Plus 3 lifecycle subpackages:

- `pipeline/` — 18 files (pull, build, validate, backfill, auto-refresh, orchestrator)
- `ops/` — 5 files (inventory, manifests, team history, test runner)
- `analysis/` — 3 files (3pt battles, battle summary, advanced metrics)

The top-level file count (37) is manageable. Query commands, NQ helpers, and engine infrastructure are all "engine core" and belong together. A new contributor can understand the layout by looking at the naming conventions: `_` prefix = internal helper, `player_*`/`team_*`/`game_*`/`season_*` = query commands, everything else = infrastructure.

### Natural-query helper placement — ✅ Good enough

The decomposition is complete:

| Module | Lines | Responsibility |
|---|---|---|
| `natural_query.py` | 1,041 | Routing/orchestration + `__all__` re-exports |
| `_natural_query_execution.py` | 723 | Execution, result manipulation, CLI rendering |
| `_parse_helpers.py` | 729 | Text→value parsing functions |
| `_constants.py` | — | Stat aliases, normalization |
| `_date_utils.py` | — | Date/range extraction |
| `_leaderboard_utils.py` | — | Leaderboard stat detection |
| `_matchup_utils.py` | — | Head-to-head, opponent, player/team detection |
| `_occurrence_route_utils.py` | — | Occurrence/compound event extraction |
| `_playoff_record_route_utils.py` | — | Playoff/record routing |
| `_seasons.py` | — | Season resolution helpers |

`natural_query.py` at 1,041 lines is a reasonable size for a routing/orchestration module. The earlier audit recommended pulling parse helpers into `_parse_helpers.py` — that was done. No further extraction needed.

### CLI / service / API boundaries — ✅ Good enough

Clean three-layer architecture:

1. **CLI** (`cli.py` + `cli_apps/*`) — argument handling and presentation only
2. **Service** (`query_service.py`) — single programmatic entry point, used by both CLI and API
3. **API** (`api.py`) — thin FastAPI wrapper over the service layer

No business logic leaked into presentation layers. The service facade correctly re-exports result types so callers import from one place.

Minor observation: `api_cli.py` (32-line uvicorn launcher) sits at the package root. This is fine — it's small and serves a clear purpose.

### Frontend folder structure — ✅ Good enough

```
frontend/src/
  api/          — client.ts, types.ts, savedQueryTypes.ts (3 files)
  components/   — 21 component files, one per concern
  hooks/        — 3 hooks
  storage/      — savedQueryStorage.ts
  test/         — 8 test files + setup.ts
  App.tsx, App.css, main.tsx, index.css, vite-env.d.ts
```

Well-organized and follows React conventions. Component count (21) is manageable without subdirectories. No structural changes needed.

### Docs folder structure — ✅ Good enough

```
docs/
  index.md                  — navigation hub
  reference/    (7 files)   — current-state, verified behavior, data specs
  architecture/ (4 files)   — design docs, conventions, internal layers
  operations/   (2 files)   — runbooks, pipeline ops, UI dev guide
  planning/     (3 files)   — roadmap, active plans
  audits/       (6 files)   — audit snapshots, historical docs
```

Role-based organization is clean. `index.md` provides reading paths. Historical audits are separated from living guides. The "where new docs go" table in conventions is clear.

### Test layout — ✅ Good enough

43 test files, flat in `tests/`, with consistent `test_<feature>.py` naming. Marker-based grouping (`parser`, `query`, `engine`, `api`, `output`) provides logical organization without directory overhead. Makefile targets (`test-parser`, `test-query`, etc.) give fast subsystem feedback.

At 43 files, flat layout is still navigable. Directory-based grouping would add value at ~60+ files but isn't needed now.

### Conventions / "where new code goes" clarity — ✅ Good enough

`docs/architecture/project_conventions.md` covers:

- Layer separation rules (§3.1–3.7)
- Commands subpackage layout (§3.3)
- Natural query scope constraints (§3.4)
- Frontend rules (§3.6)
- Query design conventions (§4)
- Testing conventions (§7)
- Refactor conventions (§8)
- UI conventions (§9)

The repo structure audit (`docs/audits/repo_structure_audit.md`) includes a "Where New Code Goes" cheat sheet covering backend, frontend, docs, and tests. `AGENTS.md` mirrors these rules for coding agents.

A new contributor has clear guidance on where to put new code.

---

## 3. Remaining Structural Issues

### Can wait

| Issue | Why it can wait |
|---|---|
| `savedQueryTypes.ts` lives in `api/` but saved queries are local-only | Cosmetic. Three developers would put it in three different places. Not worth moving. |
| `freshness.py` is infrastructure, not a query command, but lives in `commands/` | Functionally correct where it is. Moving it would change imports in `api.py` and `query_service.py` for marginal clarity gain. |
| `App.css` is 1,444 lines in one file | Works for now. Component-scoped styles become worthwhile only if the UI grows significantly. |
| Test directory could use subdirectories at ~60+ files | Currently at 43. Markers + Makefile targets provide equivalent organization. Revisit when test count grows. |

### Not worth doing

| Issue | Why |
|---|---|
| Moving query commands into a `commands/query/` subpackage | Would change imports in `query_service.py`, `cli_apps/queries.py`, `natural_query.py`, `_natural_query_execution.py`, and dozens of tests. High churn, marginal benefit — these files are the engine core and belong at the top level. |
| Moving NQ `_`-prefixed helpers into a `commands/_nq/` subpackage | The `_` prefix convention already signals internal use. Adding a directory would increase import depth without clarity gain. |
| Splitting `format_output.py` (1,166 lines) proactively | It's a single-responsibility formatting layer. Large but coherent. Split only when a specific pain point emerges. |
| Reorganizing frontend components into subdirectories | 21 files, well-named, manageable. Subdirectories (`sections/`, `shared/`) would add folder depth without solving a real problem. |
| Restructuring test files into directories matching markers | Markers already provide the same grouping semantics. Adding directories would require updating test discovery config for no functional benefit at current scale. |

---

## 4. Stop Line

**Do not reorganize further right now:**

- Do not move query command modules into a subdirectory
- Do not create a `commands/_nq/` or `commands/parsing/` subpackage
- Do not split `format_output.py`, `query_service.py`, or `natural_query.py` proactively
- Do not create test subdirectories
- Do not create frontend component subdirectories
- Do not move `freshness.py` or `api_cli.py`
- Do not rename any existing modules for cosmetic reasons

Any of these moves could be justified in isolation, but none clears the bar of "clearly worth doing now." The churn cost exceeds the clarity benefit in every case.

---

## 5. Return-to-Feature-Work Recommendation

**Yes. The repo is clean enough. Return to feature/product work now.**

The structural foundation is solid:

- Layer separation is correct and enforced by conventions
- Commands directory is organized by lifecycle with clear "where things go" guidance
- NQ decomposition is complete — routing, parsing, and execution are separated
- Docs are role-organized with a navigable index
- Frontend follows standard React patterns
- Testing infrastructure (markers, Makefile targets, CI layers) is mature

The next structural improvement that would matter — test subdirectories, component subdirectories, or a `commands/query/` subpackage — only becomes worthwhile after significant growth in file count. That growth comes from feature work, which is what should happen next.

---

## 6. Rules to Keep It Clean From Here

1. **New query commands go at `commands/` top level.** Do not create subdirectories for them unless there are 40+ query command files.
2. **New pipeline/ops/analysis code goes in the matching subpackage.** Do not add new `pull_*` or `build_*` files at the `commands/` top level.
3. **New NQ helpers follow the `_` prefix convention.** Group by responsibility: `_<family>_utils.py` for route-family helpers, `_parse_helpers.py` for parsing, `_natural_query_execution.py` for execution.
4. **New docs go in the role-matching subdirectory.** Reference in `reference/`, design in `architecture/`, runbooks in `operations/`, plans in `planning/`, historical snapshots in `audits/`.
5. **New tests follow the `test_<feature>.py` pattern with appropriate markers.** No subdirectories needed yet.
6. **New frontend components follow the flat `components/` pattern.** One file per concern, descriptive name.
7. **If a file grows past ~1,500 lines, consider extraction** — but only if there are two clearly distinct responsibilities, not just because it's large.
8. **Do not reorganize unless a specific pain point justifies the churn.** "It would be slightly cleaner" is not sufficient justification.
