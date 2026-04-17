# Architecture & Hygiene Audit

**Date:** 2025-04-16
**Scope:** Full architecture review against `docs/architecture/project_conventions.md`

---

## 1. Executive summary

### Overall architecture health: Strong

The repo has matured into a well-layered system. The conventions doc describes a query engine with thin CLI and UI surfaces, structured results, a service layer, and a canonical pipeline — and the codebase largely delivers on that vision.

### Biggest strengths

- **Result contract system is rock-solid.** All 8 result classes share an identical trust/metadata contract. Status, reason, notes, caveats, current_through are consistent across every route. All 27 routes are fully implemented with no stubs.
- **Query service is the true backend surface.** Both CLI and API dispatch through `query_service.py`. The API layer (`api.py`, 211 lines) is genuinely thin.
- **Frontend is a correct presentation layer.** No business logic, no client-side analytics, clean component structure, TypeScript types aligned with backend contracts.
- **Pipeline and freshness are canonical.** `commands/pipeline.py` is the single operational path. `commands/freshness.py` is isolated and coherent. `auto_refresh.py` calls only the pipeline.
- **Test suite is strong.** ~1,684 test functions across ~21,785 lines covering parser, routing, result contracts, CLI smoke, API, query service, and specialized query areas.

### Biggest risks

1. **`natural_query.py` is a 4,358-line monolith** with 87 functions, a ~900-line if/elif route dispatch, and embedded business logic. It is the single largest maintainability risk in the repo.
2. **README.md is corrupted.** Lines ~50–180 contain garbled/repeated text. This is the most visible user-facing artifact and it is broken.
3. **Dual execution paths (structured vs. stdout-capture) still coexist** in `cli_apps/queries.py` with silent fallbacks. This creates unpredictable behavior and masks bugs.

---

## 2. Area-by-area findings

### 2.1 Natural query / routing architecture

**What is working well:**

- Entity resolution is properly delegated to `entity_resolution.py`
- Boolean parsing is properly delegated to `query_boolean_parser.py`
- Constants/stat aliases are partly externalized to `_constants.py`
- `parse_query()` produces a structured parse state that `_finalize_route()` consumes
- All 28 distinct routes are expressed as explicit conceptual categories matching the conventions doc (finder, summary, comparison, split, leaderboard, streak, matchup, record, occurrence, playoff)

**What is drifting:**

- **Route dispatch is a 900-line procedural if/elif chain** (`_finalize_route()`). Order matters; adding new routes risks collision with existing branches. There is no dispatch table, strategy pattern, or decision documentation.
- **Inline alias dictionaries** (`TEAM_ALIASES`, `PLAYER_ALIASES`, ~100 lines) duplicate data already in `entity_resolution.py`. Sync risk grows with each edit.
- **Leaderboard stat aliases** (~600 lines inline) are dense data that could live in `_constants.py` or a data file.
- **Business logic embedded in the orchestration layer:**
  - All-Star break date inference (`_infer_all_star_break_start()`)
  - DataFrame merging/dedup for OR queries (`_combine_or_results()`)
  - Grouped boolean base-DataFrame loading (`_load_grouped_player_base_df()`, `_load_grouped_team_base_df()`)
  - These belong in dedicated helpers or command modules
- **`_finalize_route()` mutates `notes` in place** during route selection, mixing decision-making with side effects.

**What needs cleanup:**

- The dual execution paths in `run()` (structured-first via query service, then stdout-capture fallback with exception swallowing) should be resolved. The structured path is canonical; the fallback path masks bugs when exceptions are silently caught.
- `_ROUTE_FUNC_MAP` (legacy stdout-capture dispatch) and `_BUILD_RESULT_MAP` (structured dispatch) both exist. Only the structured map should be canonical.

**Severity: High.** The file is functional but its size and complexity are the biggest single risk to safe iteration.

---

### 2.2 Result contract consistency

**What is working well:**

- All 8 result classes (`NoResult`, `SummaryResult`, `ComparisonResult`, `SplitSummaryResult`, `FinderResult`, `LeaderboardResult`, `StreakResult`, `CountResult`) share identical fields: `result_status`, `result_reason`, `current_through`, `metadata`, `notes`, `caveats`.
- All implement `to_labeled_text()`, `to_dict()`, `to_sections_dict()`.
- Status/reason vocabulary is consistent and small: `ok`, `no_result`, `error` for status; `no_data`, `unsupported`, `unrouted`, `ambiguous`, `error` for reason.
- `QueryResponse` envelope in the API cleanly mirrors internal `QueryResult`.

**What is drifting:**

- `CountResult` extraction from `LeaderboardResult` (in `query_service.py`, ~55 lines) is tightly coupled to column naming conventions and silently returns `count=0` when extraction fails. This should add a note/caveat when fallback occurs.
- `metadata` field exists on all result objects but is always populated at the `QueryResult` envelope level, never by the command modules themselves. This is fine architecturally but could be documented more clearly.

**What needs cleanup:**

- Nothing urgent. The count-extraction coupling is a minor robustness issue.

**Severity: Low.** The result contract system is one of the strongest parts of the repo.

---

### 2.3 Service / API / CLI boundaries

**What is working well:**

- `query_service.py` (613 lines) is the true backend surface. Both `cli_apps/queries.py` and `api.py` call through it.
- `api.py` (211 lines) is a thin Pydantic-over-FastAPI layer. No business logic.
- `cli.py` (137 lines) is pure command registration.
- `cli_apps/ops.py` and `cli_apps/pipeline.py` are thin wrappers.

**What is drifting:**

- `cli_apps/queries.py` has accumulated **export orchestration logic** with a three-path dispatch:
  1. Structured-first path via `execute_structured_query()` — correct
  2. `build_result()` direct call for positional-arg backward compat
  3. `redirect_stdout` capture for legacy text-output commands
- CSV/JSON export parsing in `cli_apps/queries.py` re-parses raw stdout text using heuristics (looking for section labels, sniffing column names). This is parsing presentation artifacts instead of consuming structured results.

**What needs cleanup:**

- The three-path dispatch should converge to a single structured path. The stdout-capture fallback is a transitional shim that should have a documented deprecation plan or be removed.
- Export logic should consume `to_dict()` / `to_labeled_text()` from result objects, not re-parse formatted text.

**Severity: Medium.** The service boundary is correct in architecture; the CLI export plumbing is where the drift lives.

---

### 2.4 Data / pipeline / freshness architecture

**What is working well:**

- `commands/pipeline.py` (582 lines) is the canonical data ingestion path: raw pulls → validate → build → manifest update. Returns structured `PipelineResult`.
- `commands/freshness.py` (422 lines) is focused: `compute_current_through()`, `classify_freshness()`, `FreshnessStatus` enum, `FreshnessInfo` dataclass. No duplication with pipeline.
- `commands/auto_refresh.py` is clean: loop + sleep + call `refresh_current_season()`.
- Freshness is consumed cleanly by API (`/freshness` endpoint) and frontend (`FreshnessStatus.tsx`).

**What is drifting:**

- `/scripts/` contains 4 standalone analysis scripts (`nba_3pt_battle_records/`, `top10_h2h/`, `top10_h2h_required_players/`, `top10_pointdiff/`) that:
  - Directly call `nba_api.stats.endpoints` (bypassing the pipeline)
  - Have their own retry logic and custom headers
  - Output to `outputs/<script_name>/`
  - Overlap partially with CLI commands (e.g., `battle-summary`)
- `/outputs/` contains leftover output files from manual runs.

**What needs cleanup:**

- The `/scripts/` directory should be evaluated: migrate useful scripts into `commands/` + CLI wrappers, or explicitly retire them with a CHANGELOG note.
- `/outputs/` sample files should be in `.gitignore` or documented as examples.

**Severity: Low–Medium.** The pipeline is canonical. Scripts are vestigial but not actively harmful.

---

### 2.5 Frontend architecture

**What is working well:**

- Purely a rendering layer. No business logic, no client-side filtering or analytics.
- TypeScript types (`types.ts`) are fully aligned with the backend `QueryResponse` envelope, all 7 query classes, and 27+ route names.
- 21 components, each focused. `DataTable` is reused in 6+ places.
- Clean dispatcher pattern: `ResultSections.tsx` switches on `query_class` and delegates to per-type renderers.
- State management is appropriate: `useState` for transient state, `useUrlState` for shareable deep links, `useSavedQueries` for localStorage persistence.
- 9 test files covering client, components, hooks, and rendering.

**What is drifting:**

- `savedQueryTypes.ts` + `storage/savedQueryStorage.ts` is a frontend-only feature (saved queries in localStorage). This is technically outside the "frontend should not contain business logic" rule, but it is UI convenience (like browser bookmarks), well-isolated, and does not affect engine behavior. **This is an acceptable exception.**

**What needs cleanup:**

- Nothing urgent.

**Severity: Low.** The frontend is architecturally sound.

---

### 2.6 Project / documentation hygiene

**What is working well:**

- `project_conventions.md` (474 lines) is comprehensive and matches the actual architecture.
- `current_state_guide.md` (468 lines) is intentionally scoped to verified shipped behavior.
- `data_freshness_plan.md` and `pipeline_runbook.md` are tightly scoped and match implementation.
- `query_service_layer.md` clearly documents the service interface.
- `data_contracts.md` and `data_catalog.md` are thorough.

**What is drifting:**

- **README.md is corrupted.** Lines ~50–180 contain garbled/repeated text fragments. Critical user-facing issue.
- **Multiple query guide docs** with unclear precedence: `query_guide.md`, `quick_query_guide.md`, `current_state_guide.md` all cover "what you can ask" from different angles.
- **Result contracts naming confusion:** `result_contracts.md` describes target state but is named as if it were current. `result_contracts_audit.md` is the actual current-state audit. Labels should be clearer.
- **AGENTS.md vs project_conventions.md overlap:** Both define conventions and philosophy. AGENTS.md is more operational (testing workflow, CI); project_conventions.md is more architectural. Content is complementary but creates a "which do I read?" question.
- **`natural_query_cleanup_plan.md`** is a living cleanup plan — should be checked for staleness after each major pass.

**What needs cleanup:**

- README.md must be regenerated or restored.
- Result contracts docs should be relabeled or merged.
- Query guide docs could be consolidated (one reference, one quick-start).

**Severity: High** (README), **Medium** (doc overlap), **Low** (naming).

---

## 3. Top cleanup opportunities

Ranked by value / risk ratio:

| Priority | Opportunity                                                                                                                                              | Value                              | Risk                                       | Effort  |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------ | ------- |
| **1**    | Fix corrupted README.md                                                                                                                                  | High (user-facing)                 | None                                       | Small   |
| **2**    | Remove dual execution paths in `cli_apps/queries.py` and `natural_query.py` `run()` — make structured-first the only path                                | High (bug masking, complexity)     | Low (structured path is already canonical) | Medium  |
| **3**    | Extract leaderboard stat aliases from `natural_query.py` into `_constants.py`                                                                            | Medium (reduces NQ module density) | None                                       | Small   |
| **4**    | Extract inline `TEAM_ALIASES`/`PLAYER_ALIASES` from `natural_query.py` — consolidate into `entity_resolution.py`                                         | Medium (eliminates duplication)    | Low                                        | Small   |
| **5**    | Extract date utilities (`_infer_all_star_break_start`, `_resolve_year_for_month_in_season`) from `natural_query.py` into a `_date_utils.py` module       | Medium (separation of concerns)    | None                                       | Small   |
| **6**    | ~~Retire `/scripts/` analysis scripts — migrate or archive~~ **Resolved** (see `docs/audits/scripts_retirement.md`)                                             | Medium (removes confusion)         | Low                                        | Small   |
| **7**    | ~~Clarify result contracts docs — rename `result_contracts.md` to `result_contracts_target.md` or add banner~~ **Resolved** (banners added to both docs) | Low (reduces confusion)            | None                                       | Trivial |
| **8**    | ~~Consolidate query guide docs (merge `quick_query_guide.md` into `query_guide.md`)~~ **Resolved** (kept separate with role banners; see below)          | Low (reduces doc surface)          | None                                       | Small   |

---

## 4. Recommended cleanup sequence

### Phase 1: Immediate (safe, high-signal)

1. **Fix README.md** — Regenerate from current capabilities. This is the most visible issue.
2. **~~Retire `/scripts/`~~** — **Done.** Scripts retired with replacement mapping in `docs/audits/scripts_retirement.md`. Stale lint rule removed from `pyproject.toml`.

### Phase 2: Near-term (reduces technical debt)

3. **Extract aliases and constants from `natural_query.py`** — Move leaderboard stat aliases to `_constants.py`, consolidate player/team aliases into `entity_resolution.py`. Pure data moves, no logic changes.
4. **Extract date utilities from `natural_query.py`** — `_infer_all_star_break_start()`, `_resolve_year_for_month_in_season()` into a `_date_utils.py` helper module.

### Phase 3: Medium-term (architecture improvement)

5. **Unify CLI export path** — Make `cli_apps/queries.py` always use the structured result path. Remove stdout-capture fallback and `_ROUTE_FUNC_MAP`. This requires verifying all routes produce equivalent results through the structured path.
6. **Improve `_finalize_route()` readability** — Not a full rewrite, but add a decision table comment at the top documenting the priority order of route checks. Consider extracting the largest route-class blocks (playoff routing, occurrence routing) into sub-functions.

### Phase 4: ~~Can wait~~ Resolved

7. ~~**Doc consolidation**~~ — **Resolved.** Role banners added to `result_contracts.md`, `result_contracts_audit.md`, `query_guide.md`, `quick_query_guide.md`, and `current_state_guide.md`. Query guides kept separate (they serve different audiences) with cross-links. `docs/index.md` updated with correct paths and doc map. `natural_query_cleanup_plan.md` updated with completion status.
8. **AGENTS.md / project_conventions.md dedup** — These serve different audiences (agents vs. human devs) and the overlap is manageable. Left as-is.

### Explicitly do not touch yet

- **Do not rewrite `_finalize_route()` into a dispatch table** unless a new route class is being added. The current if/elif chain works and is well-tested. A structural rewrite has high risk and moderate payoff at current scale.
- **Do not move saved queries to the backend** unless multi-device sync is actually needed.
- **Do not rewrite `format_output.py` heuristics** until all raw-output commands emit section labels (tracked in `result_contracts_audit.md`).
- **Do not split `natural_query.py` into multiple files** in a single pass. Extract helpers incrementally (dates, aliases, constants) and let the file shrink naturally.

---

## 5. No-churn guidance

These areas may look like they need cleanup but should **not** be refactored right now:

| Item                                                                    | Why it looks messy                                        | Why to leave it                                                                                                                                                                    |
| ----------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `natural_query.py` is 4,358 lines                                       | Large file                                                | It is heavily tested, functional, and the risk of a big split outweighs the benefit. Shrink it incrementally by extracting data (aliases, constants) and utilities (dates) first.  |
| `format_output.py` uses heuristics to detect query type from raw output | Violates structured-result philosophy                     | The fix is to add section labels to raw output (tracked in `result_contracts_audit.md`). Rewriting the formatter without fixing the input would create churn.                      |
| Player/team route symmetry in `_finalize_route()`                       | Near-duplicate if/elif branches for player vs. team paths | This mirrors real domain asymmetry (player metrics ≠ team metrics). Forcing unification would create awkward abstractions.                                                         |
| `CountResult` extraction in `query_service.py`                          | Tightly coupled to column names                           | Works for all current routes. Refactoring before adding new count-compatible routes would be premature.                                                                            |
| `savedQueryStorage.ts` in the frontend                                  | Feature outside the "thin UI" rule                        | It is browser-local bookmarking, well-isolated, and does not affect the engine. Moving it to the backend would add complexity with no current need.                                |
| Multiple query-guide docs                                               | Redundant coverage of "what you can ask"                  | Each serves a slightly different audience (quick examples vs. comprehensive reference vs. verified state). **Resolved** by adding role banners and cross-links instead of merging. |

---

## 6. Recommended next prompt

If starting the cleanup sequence, the highest-value first step is:

```
Fix the corrupted README.md. Regenerate it from the current repo state:
- Keep the existing structure (Quick Start, What You Can Ask, Current Capabilities, Exports, Commands, Setup)
- Pull accurate examples from current_state_guide.md and query_guide.md
- Ensure all code blocks are complete and properly formatted
- Reflect the current test count and capability set
- Do not add new claims — only document what is verified and tested
- Run `make test-preflight` after to confirm no regressions
```
