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

**Whole plan status: not done.**

The parser/query-surface expansion plan is closed. The parser execution
completion plan is closed. Those closures only mean their scoped planning chains
finished with explicit boundaries. They do not mean the core product finish line
has been reached.

The whole plan remains open because core capability families are still partial
or explicitly deferred at the product level.

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

The active continuation queue is
[`source_backed_execution_queue.md`](./source_backed_execution_queue.md).

**Current required action:** work the first unchecked item in that queue:
`Close the master-plan implementation blockers`.

That queue records the next product path: source-backed implementation for the
approved `clutch`, `on/off`, and `lineups` source paths. Broader route
expansion for quarter / half / OT, schedule-context, or starter / bench role is
not part of the core finish line.

---

## Core Capability Status

| Capability family        | Parser/query-surface status                                                         | Execution/data status                                                                                                                                                                                                                                                                                                                                 | Product/capability status                                                                                                                                                                      | Done state                                   | Active continuation if not done                                                    |
| ------------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------- |
| Clutch                   | Parser-recognized and route-propagated                                              | Coverage-gated execution path exists via trusted `player_game_clutch_stats` and `team_game_clutch_stats` rows derived from official `PlayByPlayV3` events, documented in [`clutch_source_boundary.md`](./clutch_source_boundary.md). Missing or untrusted coverage keeps the explicit unfiltered-results note.                                      | Product complete for the approved route boundary; broader metrics beyond validated event-derived points remain out of scope unless a future queue reopens them                                | Done for core finish line                    | None                                                                               |
| On/off                   | Dedicated `player_on_off` route and parser surface exist                            | Coverage-gated execution path exists via trusted `team_player_on_off_summary` rows normalized from upstream `teamplayeronoffsummary`, documented in [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md). Missing or untrusted coverage keeps the explicit unsupported-data response.                                           | Product complete for the approved single-player source boundary; broader multi-player/stint semantics remain out of scope unless a future queue reopens them                                   | Done for core finish line                    | None                                                                               |
| Lineups                  | Dedicated `lineup_summary` and `lineup_leaderboard` routes and parser surface exist | Coverage-gated execution path exists via trusted `league_lineup_viz` rows normalized from upstream `leaguelineupviz`, documented in [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md). Missing or untrusted coverage keeps the explicit unsupported-data response.                                                                                 | Product complete for the approved lineup-unit source boundary; roster membership remains out of scope as a lineup-unit substitute unless a future queue reopens it                            | Done for core finish line                    | None                                                                               |
| Quarter / half / OT      | Parser-recognized and route-propagated                                              | Coverage-gated execution on `player_game_finder` and `team_record`; other routes still use explicit unfiltered notes                                                                                                                                                                                                                                  | Product complete for the core finish-line route boundary; broader route expansion is explicitly out of scope unless a future product queue reopens it                                          | Done for core finish line                    | None                                                                               |
| Schedule-context filters | Parser-recognized and route-propagated                                              | Coverage-gated execution on `team_record` and `player_game_summary`; unsupported routes and missing/untrusted coverage use explicit notes                                                                                                                                                                                                             | Product complete for the core finish-line route boundary; broader route expansion is explicitly out of scope unless a future product queue reopens it                                          | Done for core finish line                    | None                                                                               |
| Starter / bench role     | Parser-recognized for player context                                                | Coverage-gated execution on `player_game_summary` and `player_game_finder` when trusted `player_game_starter_roles` rows exist                                                                                                                                                                                                                        | Product complete for the core finish-line player-route boundary; team-level bench semantics and broader route expansion are explicitly out of scope unless a future product queue reopens them | Done for core finish line                    | None                                                                               |

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
  the active master-plan continuation queue for implementing the approved
  source-backed clutch, on/off, and lineup paths.
- [`clutch_source_boundary.md`](./clutch_source_boundary.md) records the
  approved clutch source path and future dataset boundary; it does not mark
  clutch execution as shipped.
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
