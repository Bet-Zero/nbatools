# Parser Execution Completion Plan

> **Role: active Part 2 planning doc.**
>
> **Purpose:** carry parser-shipped capabilities to true end-to-end completion. This plan continues where [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) stops.

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

Use these terms precisely across planning docs, work queues, retrospectives, and current-state claims.

### 2.1 Parser/query-surface complete

All of the following are true:

- the parser recognizes the intended phrasing family
- the parse state carries the necessary slots
- routing exists
- parser/query docs and tests are updated

This level can still be placeholder-backed or unfiltered.

### 2.2 Execution/data complete

At least one of the following is true:

1. the intended user-facing query family returns execution-backed results using the required data source or aggregation layer
2. the capability is explicitly deferred/out of scope with a documented reason and boundary

Placeholder notes or unfiltered fallbacks do **not** satisfy this level.

### 2.3 Product/capability complete

The capability family is both parser/query-surface complete and execution/data complete, and the repo's current-state docs can honestly describe it as fully supported.

### 2.4 Planning rule

A top-level plan, phase, or queue may not declare product/capability completion from parser/query-surface completion alone.

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
- starter / bench execution for the `role` slot
- real on/off execution for `player_on_off`
- real lineup execution for `lineup_summary` and `lineup_leaderboard`
- closure audit for any remaining placeholder or unfiltered route surfaced by parser docs, examples, or query catalog entries

### 3.2 Out of scope

- replacing the local-first CSV + pandas storage model without a concrete need
- ML-based parser changes
- broad conversational/multi-turn query state
- new parser capability families that are not already part of Part 1's shipped surface, unless they are required to finish execution-backed support for an already-shipped family

---

## 4. Current open capability gaps

These are the capability families that still require Part 2 work.

| Capability family        | Parser / route status                  | Execution status                                         | Primary evidence                                                                             |
| ------------------------ | -------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Clutch                   | Parser-recognized and route-propagated | Unfiltered note; no clutch-capable data source yet       | `parser/specification.md` §8, `parser/examples.md` §7.7                                      |
| Quarter / half / OT      | Parser-recognized and route-propagated | Unfiltered note; no period split execution yet           | `parser/specification.md` §8, `parser/examples.md` §7.8                                      |
| Schedule-context filters | Parser-recognized and route-propagated | Unfiltered note; joins/features incomplete               | `parser/specification.md` §8, `parser/examples.md` §§7.9, 7.12-7.14                          |
| Starter / bench role     | Parser-recognized for player context   | Unfiltered note; role filter not wired through execution | `parser/specification.md` §8, `parser/examples.md` §7.10                                     |
| On/off                   | Dedicated route exists                 | Placeholder execution only                               | `parser/specification.md` §11, `parser/examples.md` §7.15, `phase_e_data_inventory.md`       |
| Lineups                  | Dedicated routes exist                 | Placeholder execution only                               | `parser/specification.md` §11, `parser/examples.md` §§7.16-7.17, `phase_e_data_inventory.md` |

These families are not allowed to disappear under a generic “plan complete” statement. Each one must either become execution-backed or be explicitly deferred.

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
- starter / bench role

**Definition of done:**

- these filters no longer rely on unfiltered fallback behavior for their supported routes, or are explicitly deferred with a documented reason

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

### 5.4 Phase I — Real on/off execution

**Goal:** replace placeholder on/off execution with data-backed results.

**Scope:**

- `player_on_off`
- required on/off split data source or locally derived stint model
- contract and tests for supported on/off query families

**Definition of done:**

- supported on/off queries return real results rather than placeholder notes, or the capability is explicitly deferred with a documented reason

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

The next step is explicit:

- **Active queue:** [`phase_g_work_queue.md`](./phase_g_work_queue.md)
- **Immediate action:** work the first unchecked item in Phase G

If Phase G discovers that a later queue cannot responsibly be authored without additional review, the queue must create the explicit review-handoff rather than closing with an informal residual list.

---

## 8. Reference docs to keep in lockstep

- [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — Part 1 handoff source
- [`phase_e_work_queue.md`](./phase_e_work_queue.md) — Part 1 residuals that became Part 2 scope
- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md) — current on/off and lineup data audit
- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md) — mixed-status capability definitions
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md) — parser surface examples that still carry execution notes
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md) — current-state catalog of placeholder/unfiltered vs execution-backed behavior
