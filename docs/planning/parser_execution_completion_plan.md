# Parser Execution Completion Plan

> **Role: closed Part 2 planning / closure record.**
>
> **Purpose:** carry parser-shipped capabilities to true end-to-end completion. This plan continues where [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) stops.
>
> **Master rollup:** this document does not answer whether the whole product
> plan is done. Use [`master_completion_plan.md`](./master_completion_plan.md)
> as the single authority for whole-plan completion, active continuation, and
> remaining core capability families.

---

## 1. Context

[`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) completed Part 1: parser/query-surface expansion through Phase E.

That work shipped:

- broad phrasing coverage for shipped capabilities
- explicit defaults, confidence, alternates, and canonical parse-state structure
- new parser-recognized capability families including expanded context filters, opponent-quality filters, on/off placeholders, lineup placeholders, and stretch queries

It did **not** finish every user-facing capability family end-to-end. Several families are still parser-recognized, route-recognized, placeholder-backed, or explicitly unfiltered because their execution/data layer is incomplete.

This plan exists so the repo does not mistake subsystem completion for product completion.

---

## 2. Completion model

For the overall product answer to "is the plan done?", use
[`master_completion_plan.md`](./master_completion_plan.md). The definitions in
this section apply to Part 2's scoped execution/data closure record and roll up
into the master completion plan.

Use these terms precisely across planning docs, work queues, retrospectives, and current-state claims.

### 2.1 Parser/query-surface complete

All of the following are true:

- the parser recognizes the intended phrasing family
- the parse state carries the necessary slots
- routing exists
- parser/query docs and tests are updated

This level can still be placeholder-backed or unfiltered.

### 2.2 Execution/data complete

At least one of the following is true for the documented product boundary:

1. the intended user-facing query family returns execution-backed results using the required data source or aggregation layer
2. the capability is explicitly out of scope by documented product decision

Placeholder notes, explicit deferrals, or unfiltered fallbacks do **not**
satisfy this level for the master plan. A Part 2 queue may close with an
explicit deferral only because the source boundary is documented; that does not
make the family product/capability complete.

### 2.3 Product/capability complete

The capability family is both parser/query-surface complete and execution/data complete, and the repo's current-state docs can honestly describe it as fully supported.

### 2.4 Planning rule

A subplan, phase, or queue may not declare product/capability completion from parser/query-surface completion alone. Whole-plan completion is answered only by [`master_completion_plan.md`](./master_completion_plan.md).

If a plan only completes parser/query-surface work, it must:

- label itself as **Part 1** (or equivalent)
- link to the continuation path for execution/data completion
- name the next active queue or the exact review-handoff required to create it

---

## 3. Scope of Part 2

This plan covers execution/data completion for capability families that are already parser-shipped or route-shipped but not yet execution-backed.

### 3.1 In scope

- true clutch execution
- true quarter / half / overtime execution
- schedule-context execution: back-to-back, rest, one-possession, national TV, and related joins
- starter / bench execution for the `role` slot, including the prerequisite starter-role source / derivation work
- real on/off execution for `player_on_off`
- real lineup execution for `lineup_summary` and `lineup_leaderboard`
- closure audit for any remaining placeholder or unfiltered route surfaced by parser docs, examples, or query catalog entries

### 3.2 Out of scope

- replacing the local-first CSV + pandas storage model without a concrete need
- ML-based parser changes
- broad conversational/multi-turn query state
- new parser capability families that are not already part of Part 1's shipped surface, unless they are required to finish execution-backed support for an already-shipped family

---

## 4. Capability closure status

These are the capability families Part 2 tracked from parser-shipped surface to
execution/data closure. At closure, each family is either coverage-gated
execution-backed on a documented route boundary or explicitly deferred with a
named source prerequisite.

| Capability family        | Parser / route status                  | Execution status                                                                                                                                                                  | Primary evidence                                                                                                                                         |
| ------------------------ | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clutch                   | Parser-recognized and route-propagated | Source path approved after Part 2 closure: official `PlayByPlayV3` plus local score-state derivation. Execution still returns the unfiltered note until the derived clutch datasets and route execution are implemented. | `parser/specification.md` §8, `parser/examples.md` §7.7, `phase_g_segment_data_review_handoff.md`, `clutch_source_boundary.md` |
| Quarter / half / OT      | Parser-recognized and route-propagated | Coverage-gated execution on `player_game_finder` / `team_record` via period-window backfills; other routes still remain unfiltered                                                | `parser/specification.md` §8, `parser/examples.md` §7.8, `phase_g_period_only_work_queue.md`                                                            |
| Schedule-context filters | Parser-recognized and route-propagated | Coverage-gated execution on `team_record` / `player_game_summary` via `schedule_context_features`; unsupported routes and missing/untrusted coverage still fall back with explicit notes | `parser/specification.md` §8, `parser/examples.md` §§7.9, 7.12-7.14, `docs/reference/data_contracts.md`                                                   |
| Starter / bench role     | Parser-recognized for player context   | Coverage-gated execution on `player_game_summary` / `player_game_finder` when trusted `player_game_starter_roles` rows exist; explicit unfiltered note otherwise                 | `parser/specification.md` §8, `parser/examples.md` §7.10, `docs/reference/data_contracts.md`                                                             |
| On/off                   | Dedicated route exists                 | Coverage-gated execution implemented after Part 2 closure via `team_player_on_off_summary`, normalized from upstream `teamplayeronoffsummary` through `nba_api.stats.endpoints.TeamPlayerOnOffSummary`. Missing/untrusted coverage keeps the unsupported-data response. | `parser/specification.md` §11, `parser/examples.md` §7.15, `phase_e_data_inventory.md`, `phase_i_on_off_source_boundary.md`, `docs/reference/data_contracts.md` |
| Lineups                  | Dedicated routes exist                 | Source path approved after Part 2 closure: upstream `leaguelineupviz` via `nba_api.stats.endpoints.LeagueLineupViz`. Execution still returns unsupported-data placeholders until the lineup dataset and route execution are implemented. | `parser/specification.md` §11, `parser/examples.md` §§7.16-7.17, `phase_e_data_inventory.md`, `phase_j_lineup_source_boundary.md`, `docs/reference/data_contracts.md` |

These families are not allowed to disappear under a generic “plan complete”
statement. Each remaining deferral names the missing source artifact required to
resume implementation.

---

## 5. Part 2 phases

### 5.1 Phase F — Execution-gap audit and shared contracts

**Goal:** turn the current informal residual list into a verified, execution-oriented backlog with explicit data contracts and route ownership.

**Scope:**

- audit every parser-shipped but execution-partial capability family listed in §4
- trace each family to the exact routes, route kwargs, data files, and missing joins/aggregations it needs
- produce or update the inventories/contracts needed so subsequent phases are implementation-ready rather than retrospective-only
- verify whether any current-state or catalog wording still overstates completion

**Definition of done:**

- a single audited inventory exists for all execution-partial capability families
- required data sources/contracts are named for each family
- the next implementation queue (Phase G) can target real execution work instead of more ambiguity about scope

### 5.2 Phase G — Execution-backed context filters

**Goal:** finish execution for context filters that already have parser support but still return unfiltered results.

**Scope:**

- clutch
- quarter / half / overtime
- starter / bench role, including the starter-role source / derivation prerequisite exposed by the current player-game-data blocker

For starter / bench role specifically, the current `player_game_stats`-derived `starter_flag` is not a usable execution input. Item 2A identified the real source path as a dedicated per-game starter-role backfill sourced from `BoxScoreTraditionalV3.PlayerStats.position`, with explicit trust validation because sampled historical coverage is not uniformly clean. Phase G therefore has to land that dataset + trust-gating path before route-level role filtering can ship honestly.

**Definition of done:**

- these filters no longer rely on unfiltered fallback behavior for their supported routes, or are explicitly deferred with a documented reason

**Post-queue status:** The original Phase G queue landed the shared transport
work and the trusted starter-role path. The follow-up segment review recorded in
[`phase_g_segment_data_review_handoff.md`](./phase_g_segment_data_review_handoff.md)
then split the remaining segment-backed scope:

- quarter / half / OT continue in the active
  [`phase_g_period_only_work_queue.md`](./phase_g_period_only_work_queue.md)
- `clutch` remained explicitly deferred at Phase G closure; the later
  master-plan continuation approved official `PlayByPlayV3` plus local
  score-state derivation in
  [`clutch_source_boundary.md`](./clutch_source_boundary.md), but execution is
  still not shipped

The period-only continuation has now landed the initial implementation boundary
for that remaining scope:

- `BoxScoreTraditionalV3` window requests are the source of record for the
  initial period datasets
- `BoxScoreAdvancedV3` enriches only the player-grain period dataset with the
  rate fields needed by `player_game_finder`
- `player_game_finder` and `team_record` now execute quarter / half / OT filters
  when trusted `player_game_period_stats` / `team_game_period_stats` coverage
  exists for the requested slice, and otherwise fall back with an explicit
  unfiltered-results note
- this contract remains period-only and does not broaden into `clutch`

### 5.3 Phase H — Schedule-context execution

**Goal:** make schedule-context filters execution-backed instead of parser-only.

**Scope:**

- back-to-back
- rest advantage / disadvantage / day-count filters
- one-possession filters
- nationally televised filters
- any shared schedule/context feature joins required across those families

**Definition of done:**

- supported schedule-context queries return execution-backed results rather than unfiltered notes

**Post-queue status:** Phase H shipped the shared `schedule_context_features`
table and route execution boundary:

- `schedule_context_features` is a processed team-game table keyed by
  `game_id` + `team_id`
- it centralizes `back_to_back`, normalized `rest_days` / rest advantage,
  one-possession final-margin semantics, and national-TV source trust
- `team_record` and `player_game_summary` execute schedule-context filters when
  trusted feature coverage exists for the requested slice
- unsupported routes, missing feature coverage, and untrusted national-TV source
  coverage still produce explicit unfiltered-results notes
- `clutch` remains explicitly deferred and was not changed by Phase H

### 5.4 Phase I — Real on/off execution

**Goal:** replace placeholder on/off execution with data-backed results.

**Scope:**

- `player_on_off`
- required on/off split data source or locally derived stint model
- contract and tests for supported on/off query families

**Definition of done:**

- supported on/off queries return real results rather than placeholder notes, or the capability is explicitly deferred with a documented reason

**Post-queue status:** Phase I originally deferred real on/off execution in
[`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md). The
later master-plan source-approval queue approved upstream
`teamplayeronoffsummary` via
`nba_api.stats.endpoints.TeamPlayerOnOffSummary` for future implementation. The
later source-backed execution queue added the `team_player_on_off_summary`
dataset path and coverage-gated `player_on_off` route execution. Whole-game
`without_player` remains explicitly separate and is not an on/off substitute.

### 5.5 Phase J — Real lineup execution and closure audit

**Goal:** replace lineup placeholders with data-backed execution and perform the final closure audit for any remaining parser-shipped-but-not-product-complete capability families.

**Scope:**

- `lineup_summary`
- `lineup_leaderboard`
- lineup-unit data source / aggregation path
- audit parser docs, examples, query catalog, and current-state docs for any remaining placeholder or unfiltered capabilities

**Definition of done:**

- supported lineup queries return real results or are explicitly deferred with a documented reason
- the final closure audit names any remaining deferrals explicitly
- no parser-shipped family remains in an implicit “we’ll get to that later” state

**Post-queue status:** Phase J originally deferred real lineup execution in
[`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md). The
later master-plan source-approval queue approved upstream `leaguelineupviz` via
`nba_api.stats.endpoints.LeagueLineupViz`; the later source-backed execution
queue ingested, validated, and wired that source into coverage-gated route
execution. Roster membership remains explicitly separate and is not a
lineup-unit substitute.

**Part 2 closure status:** closed with explicit boundaries. Deferred
capabilities were named rather than implicit:

- `clutch` — source path approved in
  [`clutch_source_boundary.md`](./clutch_source_boundary.md); coverage-gated
  execution shipped after Part 2 closure
- `player_on_off` — coverage-gated execution shipped after Part 2 closure
- `lineup_summary` / `lineup_leaderboard` — source path approved after Part 2
  closure; coverage-gated execution shipped after Part 2 closure

Coverage-gated execution-backed boundaries are:

- quarter / half / OT on `player_game_finder` and `team_record`
- starter / bench role on player summary/finder routes when trusted
  `player_game_starter_roles` rows exist
- schedule-context filters on `team_record` and `player_game_summary` when
  trusted `schedule_context_features` coverage exists

---

## 6. Queue and continuation rules for Part 2

- A queue in this plan cannot close while leaving execution-partial capability families without an explicit continuation path.
- The final item of each Part 2 queue must either:
  1. draft the next queue toward end-to-end completion, or
  2. create a review-handoff that names the exact files/artifacts to review, who should review them, and the immediate next action after review.
- “Parser-recognized,” “route exists,” “honest placeholder,” and “unfiltered with note” are allowed as interim states but do not count as final completion.
- Current-state docs may only describe a capability as fully supported once it reaches product/capability completion per §2.3.

---

## 7. Active continuation step

The next step for this closed Part 2 plan is explicit:

- **Completed queue:** [`phase_j_work_queue.md`](./phase_j_work_queue.md)
- **Active queue:** none; Part 2 is closed with explicit deferrals and
  coverage-gated execution boundaries
- **Master-plan continuation:** [`master_completion_plan.md`](./master_completion_plan.md)
  is the single authority for current whole-plan status. It now names
  [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
  and [`phase_l_work_queue.md`](./phase_l_work_queue.md) as the active
  continuation for the examples-library surface.

If the active master-plan continuation discovers that a later implementation
queue cannot responsibly be authored without additional review, it must create
the explicit review-handoff rather than closing with an informal residual list.

---

## 8. Reference docs to keep in lockstep

- [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — Part 1 handoff source
- [`phase_e_work_queue.md`](./phase_e_work_queue.md) — Part 1 residuals that became Part 2 scope
- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md) — current on/off and lineup data audit
- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md) — mixed-status capability definitions
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md) — parser surface examples that still carry execution notes
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md) — current-state catalog of placeholder/unfiltered vs execution-backed behavior
