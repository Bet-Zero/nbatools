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
[`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md).

**Current required action:** work the first unchecked item in that queue:
`Approve or reject the clutch source path`.

That queue records the next product path: pursue source approval for `clutch`,
`on/off`, and `lineups`; do not pursue broader route expansion for quarter /
half / OT, schedule-context, or starter / bench role as part of the core finish
line. Product feature implementation should resume only after the relevant
source decision item approves a trustworthy source and the queue drafts the next
implementation queue.

---

## Core Capability Status

| Capability family | Parser/query-surface status | Execution/data status | Product/capability status | Done state | Active continuation if not done |
| --- | --- | --- | --- | --- | --- |
| Clutch | Parser-recognized and route-propagated | Deferred; current behavior is unfiltered with explicit notes because no trustworthy game-grain clutch source or play-by-play derivation path is approved | Not product complete | Deferred, not fully done | [`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md) item 2: approve or reject the clutch source path |
| On/off | Dedicated `player_on_off` route and parser surface exist | Deferred; placeholder remains because no trustworthy on/off split, play-by-play plus substitutions, or stint source exists | Not product complete | Deferred, not fully done | [`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md) item 3: approve or reject the on/off source path |
| Lineups | Dedicated `lineup_summary` and `lineup_leaderboard` routes and parser surface exist | Deferred; placeholders remain because no trustworthy lineup-unit, play-by-play plus substitutions, or stint source exists | Not product complete | Deferred, not fully done | [`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md) item 4: approve or reject the lineup source path |
| Quarter / half / OT | Parser-recognized and route-propagated | Coverage-gated execution on `player_game_finder` and `team_record`; other routes still use explicit unfiltered notes | Product complete for the core finish-line route boundary; broader route expansion is explicitly out of scope unless a future product queue reopens it | Done for core finish line | None |
| Schedule-context filters | Parser-recognized and route-propagated | Coverage-gated execution on `team_record` and `player_game_summary`; unsupported routes and missing/untrusted coverage use explicit notes | Product complete for the core finish-line route boundary; broader route expansion is explicitly out of scope unless a future product queue reopens it | Done for core finish line | None |
| Starter / bench role | Parser-recognized for player context | Coverage-gated execution on `player_game_summary` and `player_game_finder` when trusted `player_game_starter_roles` rows exist | Product complete for the core finish-line player-route boundary; team-level bench semantics and broader route expansion are explicitly out of scope unless a future product queue reopens them | Done for core finish line | None |

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
  is the active master-plan continuation queue for the remaining source
  approvals and route-expansion product decisions.
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
