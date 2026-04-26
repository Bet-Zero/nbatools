# Master Completion Plan

> **Role: single top-level completion authority for the whole product plan.**
>
> This is the one document that answers:
>
> - Is the whole plan done?
> - What is the active continuation?
> - What core capability families remain open?
>
> Subplans, phase queues, closure records, and retrospectives roll up here. They
> do not independently answer overall product completion.

---

## Current Whole-Plan Status

**Whole plan status: done.**

The parser/query-surface expansion plan is closed. The parser execution
completion plan is closed. The source-approval and source-backed execution
queues are closed for their documented core capability boundaries.

The full parser-examples sweep is clean after the Phase M closure pass. The
latest sweep (`2026-04-26T10:08:40.940353+00:00`) covered 402 cases with 402
passing, 0 failing, 0 phrasing-pair mismatches, and 0 equivalence-group
mismatches. Remaining Finals-specific record examples were honestly
reclassified to the explicit historical-splits boundary because no approved
entity-grain playoff-round record data contract exists.

---

## Whole-Project Completion Rule

The whole plan is **not done** unless one of the following is true for every
required core capability family:

1. the family is product/capability complete, meaning parser/query-surface
   support and execution/data support are both complete for the documented
   product boundary, or
2. the family is explicitly declared out of scope by a documented product
   decision.

Closed subplans, closed queues, parser completion, route recognition,
placeholder support, unfiltered fallback notes, or explicit deferrals do **not**
by themselves equal whole-plan completion.

An explicit deferral is an honest planning state. It prevents hidden residual
work, but it does not close the master plan unless a product decision also says
the family is no longer required for the core product finish line.

---

## Source and Saved-Dataset Structure Invariant

Any newly approved source path or saved dataset work under this master plan
must preserve the repo's data lifecycle structure and contractual clarity.

Required guardrails for continuation queues and implementation work:

- keep placement explicit across `raw`, `processed`, and `derived`
- avoid silently broadening, overwriting, or repurposing canonical datasets
- keep dataset grain explicit; do not hide mixed-grain semantics in old tables
- define the dataset contract before broad implementation (dataset name,
  lifecycle layer, grain, join keys, trust/coverage fields, fallback behavior,
  and placement rationale)
- prefer additive datasets with dedicated backfill paths over mutating
  unrelated existing tables unless there is a strong documented reason

Queue completion, source approval, and product-capability status must be read
with these structure rules in force; an approved source is not a license to
degrade dataset boundaries.

---

## Active Continuation Rule

This document must always name exactly one of these:

- the current active continuation plan or queue, if the whole plan is not done
- the exact next required action to create that continuation, if no active queue
  exists yet
- an explicit statement that the whole plan is done

There must never be a planning state where subplans are closed, no active queue
is named, meaningful core capability work remains, and the repo can still sound
done.

### Current Active Continuation

The whole plan is done. No active continuation queue remains.

---

## Core Capability Status

| Capability family        | Parser/query-surface status                                                         | Execution/data status                                                                                                                                                                                                                                                                                          | Product/capability status                                                                                                                                                                      | Done state                | Active continuation if not done                                                                                                   |
| ------------------------ | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Clutch                   | Parser-recognized and route-propagated                                              | Coverage-gated execution path exists via trusted `player_game_clutch_stats` and `team_game_clutch_stats` rows derived from official `PlayByPlayV3` events, documented in [`clutch_source_boundary.md`](./clutch_source_boundary.md). Missing or untrusted coverage keeps the explicit unfiltered-results note. | Product complete for the approved route boundary; broader metrics beyond validated event-derived points remain out of scope unless a future queue reopens them                                 | Done for core finish line | None                                                                                                                              |
| On/off                   | Dedicated `player_on_off` route and parser surface exist                            | Coverage-gated execution path exists via trusted `team_player_on_off_summary` rows normalized from upstream `teamplayeronoffsummary`, documented in [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md). Missing or untrusted coverage keeps the explicit unsupported-data response.    | Product complete for the approved single-player source boundary; broader multi-player/stint semantics remain out of scope unless a future queue reopens them                                   | Done for core finish line | None                                                                                                                              |
| Lineups                  | Dedicated `lineup_summary` and `lineup_leaderboard` routes and parser surface exist | Coverage-gated execution path exists via trusted `league_lineup_viz` rows normalized from upstream `leaguelineupviz`, documented in [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md). Missing or untrusted coverage keeps the explicit unsupported-data response.                    | Product complete for the approved lineup-unit source boundary; roster membership remains out of scope as a lineup-unit substitute unless a future queue reopens it                             | Done for core finish line | None                                                                                                                              |
| Quarter / half / OT      | Parser-recognized and route-propagated                                              | Coverage-gated execution on `player_game_finder` and `team_record`; other routes still use explicit unfiltered notes                                                                                                                                                                                           | Product complete for the core finish-line route boundary; broader route expansion is explicitly out of scope unless a future product queue reopens it                                          | Done for core finish line | None                                                                                                                              |
| Schedule-context filters | Parser-recognized and route-propagated                                              | Coverage-gated execution on `team_record` and `player_game_summary`; unsupported routes and missing/untrusted coverage use explicit notes                                                                                                                                                                      | Product complete for the core finish-line route boundary; broader route expansion is explicitly out of scope unless a future product queue reopens it                                          | Done for core finish line | None                                                                                                                              |
| Starter / bench role     | Parser-recognized for player context                                                | Coverage-gated execution on `player_game_summary` and `player_game_finder` when trusted `player_game_starter_roles` rows exist                                                                                                                                                                                 | Product complete for the core finish-line player-route boundary; team-level bench semantics and broader route expansion are explicitly out of scope unless a future product queue reopens them | Done for core finish line | None                                                                                                                              |
| Examples-library surface | Full-sweep audit exists for `docs/architecture/parser/examples.md`                  | Latest sweep (`2026-04-26T10:08:40.940353+00:00`) covers 402 cases with 402 passing, 0 failing, 0 phrasing-pair mismatches, and 0 equivalence-group mismatches.                                                                                                             | Complete: failures were fixed in behavior or honestly reclassified in docs, and the full-sweep protocol shows no unresolved canonical/example-library blockers                                | Done                      | None                                                                                                                              |

---

## Rollup From Subplans

- [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) is the
  closed Part 1 parser/query-surface plan. It cannot answer whole-plan
  completion.
- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
  is the closed Part 2 execution/data closure record for parser-shipped
  families. It records explicit boundaries and deferrals. It cannot answer
  whole-plan completion.
- [`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md)
  is the closed master-plan continuation queue that resolved the remaining
  source approvals and route-expansion product decisions.
- [`source_backed_execution_queue.md`](./source_backed_execution_queue.md) is
  the closed master-plan continuation queue that implemented the approved
  source-backed clutch, on/off, and lineup paths.
- [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
  is closed. It made the examples-library surface behaviorally honest and
  documented, with a clean 402/402 closure sweep.
- [`phase_k_work_queue.md`](./phase_k_work_queue.md) is the completed queue
  that built the blocker inventory, repaired the largest mismatch families,
  reran the full sweep, and drafted the Phase L continuation.
- [`phase_l_work_queue.md`](./phase_l_work_queue.md) is the completed queue
  that reran the full parser-examples sweep, refreshed the blocker inventory,
  and drafted the Phase M continuation.
- [`phase_m_work_queue.md`](./phase_m_work_queue.md) is the completed closure
  queue for the remaining parser-examples blockers from the fresh 399/3 sweep.
  Its final bundled item produced the clean 402/402 closure sweep and closed the
  master plan.
- [`clutch_source_boundary.md`](./clutch_source_boundary.md) records the
  approved clutch source path used by shipped source-backed clutch execution.
- [`roadmap.md`](./roadmap.md) remains the broad product direction. It should
  treat this master plan as the authority for core capability completion status.

---

## Agent Rule

When an agent is asked "is the plan done?", "what is next?", "is this finished?",
or any similar completion-status question without a narrower qualifier, it must
interpret the question as asking about the whole/master plan.

The agent must answer from this master completion plan, not from the nearest
closed subplan, work queue, closure record, or retrospective. If this document
says the whole plan is not done, the agent must follow the active continuation
path named here.
