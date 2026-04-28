> **Archive status:** Completed / superseded historical planning document.
>
> **Current active plan:** See [../../planning/product_polish_master_plan.md](../../planning/product_polish_master_plan.md).
>
> **Do not use this file as the active continuation source.**

# Phase G Work Queue

> **Role:** Sequenced, PR-sized work items for Phase G of [`parser_execution_completion_plan.md`](../completed-plans/parser_execution_completion_plan.md) — _execution-backed context filters._
>
> **How to work this file:** Find the first unchecked item below. Review the reference docs it cites. Execute per its acceptance criteria. Run the test commands. Check the item off, commit. Repeat. When every item above is checked, work the final meta-task.
>
> For any item here that changes real natural-query behavior, updating `PHASE_G_QUERY_SMOKE_CASES` in `tests/_query_smoke.py` and running the listed smoke targets is part of done.
>
> **Do not skip ahead** unless an earlier item is genuinely blocked. Items are ordered to minimize rework — later items assume earlier ones are done.
>
> **⚠️ Segment-data caveat:** Items 3–5 depend on a real segment-level source for clutch / period execution (play-by-play, upstream split tables, or an equivalent joinable segment dataset). If item 3 proves that no trustworthy segment source is available within current repo constraints, do not fake these filters from whole-game logs. Record the blocker explicitly, mark the blocked items with inline rationale, and let the final meta-task create the required handoff.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Phase F retrospective (context for Phase G)

Phase F established the execution-oriented baseline for the remaining parser-shipped capability gaps:

- Consolidated the six execution-partial families into `phase_f_execution_gap_inventory.md`
- Traced route ownership, kwarg transport, command ownership, and missing data/join requirements for each family
- Defined four shared prerequisites instead of six one-off fixes: execution plumbing, segment-split data, a starter-role source/data contract, and schedule-context feature joins
- Confirmed the Phase boundary: Phase G owns shared execution plumbing plus the starter-role path, `clutch`, and `quarter / half / overtime`; Phase H owns whole-game schedule-context joins

Phase G should use that inventory as its family list of record rather than reopening broad exploration.

---

## 1. `[x]` Replace the global context-filter drop sanitizer with capability-aware transport

**Why:** Phase F showed that context filters currently follow two inconsistent fallback paths: `clutch` stops at parse-state metadata while `quarter`, `half`, and `role` are preserved into execution and then sanitized away. Phase G needs one transport contract before any filter can become execution-backed.

**Scope:**

- Replace the drop-on-sight behavior in `_natural_query_execution._sanitize_unavailable_context_filters()` with a capability-aware pattern that distinguishes:
  - Phase G routes that should receive `role`, `quarter`, `half`, and `clutch`
  - still-unsupported routes that must keep their explicit fallback notes
  - Phase H schedule-context filters that should remain honestly unsupported for now
- Ensure `clutch` is transported through `route_kwargs` and execution metadata the same way as the other context filters
- Keep the current honest note behavior for still-unsupported routes; this item is about transport and capability gating, not about pretending execution exists where it does not

**Files likely touched:**

- `src/nbatools/commands/natural_query.py`
- `src/nbatools/query_service.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/` — route-kwarg / fallback-note coverage

**Acceptance criteria:**

- `clutch`, `quarter`, `half`, and `role` follow one explicit transport path from parse state into execution
- Capability gating is route-aware instead of one global sanitizer removing every context filter indiscriminately
- Schedule-context filters (`back_to_back`, `rest_days`, `one_possession`, `nationally_televised`) remain honestly unsupported and still append the existing fallback notes
- At least 6 tests verify kwarg transport and fallback behavior across supported vs unsupported route families

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Shared execution-plumbing contract](../inventories/phase_f_execution_gap_inventory.md#shared-prerequisites-for-context-and-schedule-filters)
- [`parser_execution_completion_plan.md` §5.2](../completed-plans/parser_execution_completion_plan.md#52-phase-g--execution-backed-context-filters)
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/query_service.py`

---

## 2. `[-]` Ship starter / bench execution on player-context summary and finder routes — skipped: current player-game logs do not contain trustworthy starter-role data; follow item 2A first

**Why it was skipped:** This item was written against a false assumption: that the current raw player-game corpus already carries usable starter-role data. Repo audit showed that assumption is false, so route-level role execution cannot ship honestly from the current logs.

**Blocker confirmed in repo:**

- `src/nbatools/commands/pipeline/pull_player_game_stats.py` maps `START_POSITION` to `start_position`, fills missing `start_position` with `""`, and derives `starter_flag` from whether `start_position` is non-empty.
- `src/nbatools/commands/data_utils.py` `load_player_games_for_seasons()` loads `data/raw/player_game_stats/*`, which is the dataset consumed by `player_game_summary` and `player_game_finder`.
- The current `data/raw/player_game_stats/*.csv` corpus has `start_position` empty throughout and `starter_flag=0` throughout, so filtering those logs by `role="starter"` would turn valid starter queries into false `no_match` results.
- An exploratory execution attempt to filter on the current derived `starter_flag` was correctly reverted after smoke validation exposed the false-no-match behavior.

**Required current behavior:**

- Keep team-only bench semantics intentionally unsupported.
- Keep the current honest product surface unchanged until trustworthy starter-role data exists: parser recognition stays shipped, `role` continues to propagate through execution metadata, and supported player routes continue to append the explicit unfiltered-results note.

**Continuation path:**

- Work item 2A established the source/contract for this family. Do not reopen route-level role filtering until item 2B lands the validated starter-role dataset and execution wiring.

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Starter-role source and data contract](../inventories/phase_f_execution_gap_inventory.md#3-starter-role-source-and-data-contract)
- [`docs/architecture/parser/specification.md` §8](../architecture/parser/specification.md#8-context-filters)
- `src/nbatools/commands/pipeline/pull_player_game_stats.py`
- `src/nbatools/commands/data_utils.py`

---

## 2A. `[x]` Audit candidate starter-role sources and define the starter-role data contract

**Completion note:** Repo and upstream audit established a real source path. `LeagueGameFinder` does not expose starter-role fields in the current pull shape, but `BoxScoreTraditionalV3.PlayerStats.position` does expose a per-player game position field that behaves like a starter marker on recent sample games. The chosen path is a dedicated starter-role dataset backfilled by `game_id` from the existing raw games inventory, with strict trust validation before any route can execute against it. The same audit also showed why the contract needs trust gating: a 2025-26 sample game and a 2024-25 sample game both returned exactly 5 starter-marked players per team, while a 1996-97 sample game over-labeled starters, so historical coverage cannot be assumed clean without validation.

**Why:** Starter / bench execution remains open, but the current player-game logs cannot support it honestly. The next concrete step is to choose and document a trustworthy starter-role source or derivation path instead of assuming the current derived `starter_flag` is usable.

**Scope:**

- Audit candidate starter-role sources for player-context role execution, including whether the existing upstream pull can expose a trustworthy starter field, whether a new upstream endpoint or join is required, and whether any reliable derivation path exists.
- Lock the supported role semantics for the current product surface: whole-game `starter` vs `bench` for player-context summary/finder routes only.
- Define the minimal starter-role data contract needed for execution-backed filtering: grain, join keys, required fields, coverage/backfill expectations, and failure behavior.
- Leave a follow-on execution item that uses that contract instead of the false “existing logs are already sufficient” assumption. If no trustworthy source is available within current repo constraints, replace that execution item with an explicit handoff that names the missing upstream artifact and the immediate next action.

**Files likely touched:**

- `docs/planning/phase_f_execution_gap_inventory.md`
- `docs/planning/parser_execution_completion_plan.md`
- `docs/reference/data_contracts.md` or a dedicated companion planning doc if the contract is too large
- `src/nbatools/commands/pipeline/pull_player_game_stats.py`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`

**Acceptance criteria:**

- The repo names the exact blocker precisely: current `start_position` / derived `starter_flag` data is not trustworthy enough for honest role execution.
- A concrete candidate path is chosen for starter-role data: ingest, derivation, or explicit upstream dependency review.
- A starter-role data contract exists with explicit grain, join keys, required fields, and coverage expectations.
- The follow-on execution item for starter / bench filtering references that contract instead of assuming the current player-game logs are already sufficient, or the queue contains an explicit review/handoff item if no trustworthy source can yet be landed.

**Tests to run:**

- None for a docs-only audit/contract item. If code or pipeline probes are committed as part of the audit, run the narrow relevant target (typically `make test-engine`).

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Starter-role source and data contract](../inventories/phase_f_execution_gap_inventory.md#3-starter-role-source-and-data-contract)
- [`parser_execution_completion_plan.md` §5.2](../completed-plans/parser_execution_completion_plan.md#52-phase-g--execution-backed-context-filters)
- `src/nbatools/commands/pipeline/pull_player_game_stats.py`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`

---

## 2B. `[x]` Build the validated starter-role dataset and ship player-context role execution

**Completion note:** Landed `pull_player_game_starter_roles.py` as the dedicated `BoxScoreTraditionalV3.PlayerStats.position` backfill path, made the dataset part of the raw-pipeline validation/manifest contract, and wired `player_game_summary` / `player_game_finder` to apply `role` only when every row in the requested slice has trusted starter-role coverage. If coverage is missing or untrusted for any requested row, execution now keeps the explicit unfiltered-results note instead of partially filtering. Because the repo does not currently commit trusted starter-role backfill slices under `data/raw/player_game_starter_roles/`, `PHASE_G_QUERY_SMOKE_CASES` now omits starter/bench smoke cases until a real trusted slice is present in-repo.

**Why:** Item 2A identified the real source path: a per-game starter-role backfill sourced from `BoxScoreTraditionalV3.PlayerStats.position`, not the unusable legacy `LeagueGameFinder`-derived `starter_flag` in `player_game_stats`. The next step is to materialize that source as a dedicated dataset, validate which rows are trustworthy, and use only trusted coverage to power role execution.

**Scope:**

- Backfill a dedicated raw starter-role dataset by fan-out over the existing `data/raw/games/*` inventory, normalizing `BoxScoreTraditionalV3.PlayerStats.position` into the documented role contract.
- Derive `starter_flag` only inside that dedicated dataset; do not reuse the legacy all-zero `player_game_stats.starter_flag` as an execution input.
- Enforce trust validation before execution can use a row, at minimum requiring exactly 5 starter-marked players per `(game_id, team_id)` and recording why a row/game is untrusted when validation fails.
- Join the trusted starter-role dataset into `player_game_summary` and `player_game_finder` execution.
- Keep team-only bench semantics unsupported and preserve honest fallback notes whenever a requested slice lacks trusted starter-role coverage.

**Files likely touched:**

- `src/nbatools/commands/pipeline/` — starter-role backfill command(s)
- `src/nbatools/commands/pipeline/validate_raw.py`
- `src/nbatools/commands/ops/update_manifest.py`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `docs/reference/data_contracts.md`
- `tests/` — role source / execution coverage
- `tests/_query_smoke.py` — `PHASE_G_QUERY_SMOKE_CASES`

**Acceptance criteria:**

- A documented starter-role raw dataset exists and can be backfilled from current repo inputs plus the chosen upstream endpoint.
- Role execution on player summary/finder uses only trusted starter-role coverage; it does not rely on the legacy all-zero `player_game_stats.starter_flag`.
- Queries with unsupported or untrusted role coverage keep the honest fallback note instead of partially filtering.
- At least 6 tests cover starter/bench filtering, trust gating, and fallback behavior.
- `PHASE_G_QUERY_SMOKE_CASES` includes representative starter and bench queries only if their slices are backed by trusted coverage.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Starter-role source and data contract](../inventories/phase_f_execution_gap_inventory.md#3-starter-role-source-and-data-contract)
- [`docs/reference/data_contracts.md` §1A](../reference/data_contracts.md#1a-player_game_starter_roles)
- `src/nbatools/commands/pipeline/pull_player_game_stats.py`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`

---

## 3. `[-]` Build the segment-split contract and ingestion path for clutch / period execution — blocked under the original shared-scope assumption: no trustworthy game-grain clutch source was found under current repo constraints; the follow-on split is recorded in [`phase_g_segment_data_review_handoff.md`](../handoffs-and-boundaries/phase_g_segment_data_review_handoff.md) and continues period-only work in [`phase_g_period_only_work_queue.md`](./phase_g_period_only_work_queue.md)

**Why:** Clutch and quarter / half / overtime are blocked on the same missing prerequisite: execution-grade intra-game segment data. Phase G should solve that once, not separately for each surface phrase.

**Scope:**

- Define and implement the minimal segment-grain contract needed by current routes:
  - player-grain segments
  - team-grain segments
  - join keys compatible with existing command execution (`season`, `season_type`, `game_id`, entity identifiers)
  - segment descriptors that can encode `quarter`, `half`, `OT`, and `clutch`
  - stats columns reusable by current summary / finder / leaderboard paths
- Add the ingestion or derivation path that materializes those segment tables, or another equivalent joinable source inside the repo
- Document the contract where future phases can reuse it

**Files likely touched:**

- Data pipeline files under `src/nbatools/commands/pipeline/`
- Data-loading helpers under `src/nbatools/commands/`
- `docs/reference/data_contracts.md` or a nearby execution-contract doc
- `tests/` — pipeline / loader coverage as needed

**Acceptance criteria:**

- A concrete segment-level source exists in-repo and is documented well enough for command execution to consume it
- The contract can represent clutch and period filters without separate ad hoc tables for each phrase family
- If a trustworthy segment source cannot be landed, this item must stop with an explicit deferral/handoff artifact that names the missing source, the review target, and the immediate next action; do not approximate from whole-game logs

**Tests to run:**

- `make test-engine`
- `make test-preflight`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Segment-split data contract](../inventories/phase_f_execution_gap_inventory.md#2-segment-split-data-contract)
- [`parser_execution_completion_plan.md` §5.2](../completed-plans/parser_execution_completion_plan.md#52-phase-g--execution-backed-context-filters)
- `docs/reference/data_contracts.md`

---

## 4. `[-]` Ship quarter / half / overtime execution on the initial supported routes — blocked in the original Phase G queue behind item 3’s shared segment-contract review; the reviewed continuation path is now [`phase_g_period_only_work_queue.md`](./phase_g_period_only_work_queue.md)

**Why:** Once the segment contract exists, period filters should stop returning full-game results with a note and start using real intra-game slices.

**Scope:**

- Enable execution-backed `quarter`, `half`, and `OT` filtering on the currently documented supported routes:
  - `player_game_finder`
  - `team_record`
- Remove the period fallback note on routes where execution becomes real
- Preserve honest fallback notes on any route not yet covered by the segment contract

**Files likely touched:**

- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/team_game_finder.py` or team-record command owners
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/` — period execution coverage
- `tests/_query_smoke.py` — `PHASE_G_QUERY_SMOKE_CASES`

**Acceptance criteria:**

- `quarter`, `half`, and `OT` filters return actually filtered results on the documented supported routes
- Supported routes no longer append the unfiltered period note
- At least 6 tests verify period filtering behavior across quarter, half, and overtime shapes
- `PHASE_G_QUERY_SMOKE_CASES` includes representative quarter / half / OT queries

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Quarter / half / overtime](../inventories/phase_f_execution_gap_inventory.md#2-quarter--half--overtime)
- [`docs/architecture/parser/examples.md` §7.8](../architecture/parser/examples.md#78-period-context--4th-quarter-scoring-leaders)
- `src/nbatools/commands/player_game_finder.py`
- team-record command owner

---

## 5. `[-]` Ship clutch execution on the initial supported routes — blocked: no trustworthy clutch-capable game-grain source was approved; `clutch` remains explicitly deferred per [`phase_g_segment_data_review_handoff.md`](../handoffs-and-boundaries/phase_g_segment_data_review_handoff.md)

**Why:** Clutch is still the most user-visible unfiltered context family. After the shared transport and segment contract land, Phase G should close the gap on the routes that already claim support.

**Scope:**

- Enable execution-backed `clutch` filtering on the currently documented supported routes:
  - `player_game_summary`
  - `player_game_finder`
  - `team_record`
  - `season_leaders`
- Use the glossary/product definition already pinned in `_glossary.py`
- Remove the clutch fallback note on routes where execution becomes real
- Preserve honest fallback notes on any route still outside the supported set

**Files likely touched:**

- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/season_leaders.py`
- team-record command owner
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/` — clutch execution coverage
- `tests/_query_smoke.py` — `PHASE_G_QUERY_SMOKE_CASES`

**Acceptance criteria:**

- `clutch=True` queries return actually filtered results on the documented supported routes
- Supported routes no longer append the unfiltered clutch note
- At least 6 tests verify clutch filtering behavior on multiple route families
- `PHASE_G_QUERY_SMOKE_CASES` includes representative clutch queries

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Clutch](../inventories/phase_f_execution_gap_inventory.md#1-clutch)
- [`docs/architecture/parser/specification.md` §8](../architecture/parser/specification.md#8-context-filters)
- `src/nbatools/commands/_glossary.py`

---

## 6. `[x]` Sync current-state docs and Phase G smoke inventory with the shipped execution boundary

**Completion note:** Updated the current-state parser/query docs to reflect the actual shipped boundary: player-context `role` execution is now coverage-gated by trusted `player_game_starter_roles` data, while clutch / period filters remain deferred. `PHASE_G_QUERY_SMOKE_CASES` now excludes role smoke cases until a real trusted role slice exists in-repo.

**Why:** Once any Phase G route stops being unfiltered, the reference docs and smoke inventory must stop describing it as parser-only behavior.

**Scope:**

- Update `docs/reference/query_catalog.md`, `docs/architecture/parser/specification.md`, and `docs/architecture/parser/examples.md` to reflect the real Phase G execution boundary
- Move any newly execution-backed Phase G families out of the unfiltered / placeholder wording and into current supported behavior
- Ensure `tests/_query_smoke.py` has a durable `PHASE_G_QUERY_SMOKE_CASES` tuple representing the shipped execution-backed surface

**Files likely touched:**

- `docs/reference/query_catalog.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`
- `tests/_query_smoke.py`

**Acceptance criteria:**

- Current-state docs match the actual supported Phase G execution boundary exactly
- `PHASE_G_QUERY_SMOKE_CASES` exists and covers the shipped role / period / clutch surface, with honest exclusions if any items were explicitly deferred
- Docs do not overstate support beyond the routes actually enabled in Phase G

**Tests to run:**

- None beyond the shipping-item smoke and test runs above

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md`](../inventories/phase_f_execution_gap_inventory.md)
- [`parser_execution_completion_plan.md`](../completed-plans/parser_execution_completion_plan.md)

---

## 7. `[x]` Phase G retrospective and Phase H work queue draft

**Completion note:** Phase G closed with an explicit review handoff instead of a Phase H queue draft because items 3–5 could not land responsibly without a reviewed clutch-capable game-grain source. That handoff later resolved to the period-only continuation queue [`phase_g_period_only_work_queue.md`](./phase_g_period_only_work_queue.md) for quarter / half / OT. A later master-plan source-approval queue approved official `PlayByPlayV3` plus local score-state derivation for future clutch work; Phase G itself did not ship clutch execution. The original handoff artifact remains [`phase_g_segment_data_review_handoff.md`](../handoffs-and-boundaries/phase_g_segment_data_review_handoff.md).

**Why:** Phase G should end with a concrete handoff into schedule-context execution, or an explicit review-handoff if segment-data blockers prevent a clean close.

**Scope:**

- Review Phase G outcomes and any residual blockers
- Draft `phase_h_work_queue.md` for schedule-context execution using the shared feature-join contract from Phase F
- If items 3–5 could not responsibly land because segment data remained unavailable, write an explicit review-handoff that names:
  - the segment-data artifact or upstream source to review
  - the files/artifacts produced during Phase G
  - the immediate next action after review

**Files likely touched:**

- `docs/planning/phase_g_work_queue.md` (check this item)
- `docs/planning/phase_h_work_queue.md` (new), or an explicit review-handoff note if a queue cannot yet be authored responsibly
- `docs/planning/parser_execution_completion_plan.md` if phase boundaries need adjustment

**Acceptance criteria:**

- Phase H queue exists, or an explicit review-handoff exists with the exact files and next action
- This queue does not close with only an informal residual list
- This item is checked off

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Schedule-context feature-join contract](../inventories/phase_f_execution_gap_inventory.md#4-schedule-context-feature-join-contract)
- [`parser_execution_completion_plan.md`](../completed-plans/parser_execution_completion_plan.md)
