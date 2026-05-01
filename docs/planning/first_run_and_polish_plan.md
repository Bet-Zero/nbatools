# First-Run and Polish Plan

> **Role: Track A Part 3 plan for the product polish master plan.** The
> closing-phase plan that handles first-run experience and the small-but-felt
> polish details.
>
> Whole-plan completion authority is
> [`product_polish_master_plan.md`](./product_polish_master_plan.md). This
> doc covers Track A Part 3 only.

---

## Goal

A friend who has never seen the product before should:

- Land on the URL cold
- Understand what the product is in under 30 seconds
- Run a useful query on their first attempt without help
- Have it work on their phone

This plan handles everything that bridges "every query class has a designed
layout" (Part 2) and "the product feels finished" (Part 3 done).

---

## Why this comes last

The first-run experience is informed by what the rest of the product looks
like. Designing the landing page before knowing what designed component
results look like would mean redesigning the landing page later. By doing
this last, every starter query the landing page suggests is rendered with
its real, designed layout.

The polish work also benefits from being last. Many polish details (loading
skeletons, transitions, error states) are component-specific — best built
when the components themselves are stable.

---

## Scope

The work breaks into four areas:

### 1. First-run experience

- Landing / empty state when no query has been run yet
- Hero positioning of the query bar
- Starter query buttons grouped by intent (Players, Teams, Comparisons,
  Records, History)
- Optional: small "today's auto-generated highlights" section that uses
  the engine to surface interesting recent stats — doubles as both demo
  and a useful feature
- Freshness banner at the top — "Data through April 26"

### 2. Mobile pass

- Every component gets explicit mobile verification
- Touch targets sized appropriately
- Layouts adapt rather than just shrinking
- Query bar is thumb-reachable
- Tables that exist (where genuinely tabular) collapse to cards on mobile

### 3. Loading and error states

- Skeleton loaders shaped like incoming results, not spinners
- Empty result states with helpful suggestions ("try X instead")
- Error states that don't show stack traces, ever
- Network failure handling with retry affordance
- Stale-data state with prominent messaging

### 4. Felt polish

- Smooth transitions between query results
- Number animations on hero stats (count up to value)
- Copy-to-clipboard buttons with confirmation feedback
- Share-link buttons that produce deep-linked URLs
- Number formatting standardized everywhere
- Tooltips on stat abbreviations (eFG%, TS%, USG%, etc.)
- Keyboard shortcuts: cmd-K to focus query bar, up/down arrows for query
  history, enter to submit
- Query history UI that's actually visible and useful

---

## Phase structure

### Phase P1 — Landing and first-run experience

Goal: the landing/empty state, freshness banner, starter queries, hero
query bar treatment.

Status: complete. P1 shipped the first-run surface, grouped starter queries,
first-run freshness banner, and first-run mobile/accessibility polish. The
queue is [`phase_p1_work_queue.md`](./phase_p1_work_queue.md).

### Phase P2 — Loading, error, and empty states

Goal: every state that isn't "showing a result" gets designed.

Status: complete. P2 shipped designed loading, no-result, unsupported,
ambiguous, empty-section, and network/API failure states with retry paths. The
queue is [`phase_p2_work_queue.md`](./phase_p2_work_queue.md).

### Phase P3 — Mobile verification and fixes

Goal: explicit mobile pass on every existing component, with fixes.

Status: complete. P3 shipped explicit mobile verification and fixes across the
app shell, first-run/non-result states, result chrome, secondary panels,
table-heavy results, and card-heavy renderers. The queue is
[`phase_p3_work_queue.md`](./phase_p3_work_queue.md).

### Phase P4 — Felt polish and small details

Goal: the 50 small things — transitions, animations, copy buttons, share
links, tooltips, keyboard shortcuts, query history UI.

Status: complete. P4 shipped keyboard shortcuts and query-history recall,
copy/share success and failure feedback, stat abbreviation help, restrained
state/value motion, and saved/history ergonomics. The queue is
[`phase_p4_work_queue.md`](./phase_p4_work_queue.md).

### Phase P5 — Retrospective and master-plan closure

Goal: capture learnings. Update `product_polish_master_plan.md` to declare
the polish plan complete (or name a continuation if any blockers remain).

Status: active. The active queue is
[`phase_p5_work_queue.md`](./phase_p5_work_queue.md).

---

## Done definition for Track A Part 3

Part 3 is done when:

1. The landing experience exists and explains the product in under 30
   seconds when shown to someone unfamiliar
2. Every component has been explicitly verified on mobile and any issues
   have been fixed
3. Loading, error, and empty states are designed for every relevant
   surface
4. The felt-polish list is complete — keyboard shortcuts, copy buttons,
   share links, transitions, tooltips
5. The freshness banner correctly surfaces data age, prominently when
   data is stale
6. All existing tests pass

---

## Visual quality bar for Part 3

This is "feels finished":

- The landing page is welcoming, not sparse
- Stale data is honest and visible — never silently degrading
- Loading states feel anticipatory, not blocking
- Error messages help the user, not blame them
- Mobile is a real first-class experience, not an afterthought
- Small interactions have the right amount of feedback — not overdesigned,
  not underdesigned
- The product feels like something you'd be proud to send a friend

---

## Phase queue handoff

Phase P1's queue was drafted by Track A Part 2's final phase retrospective:
[`phase_p1_work_queue.md`](./phase_p1_work_queue.md). Phase P2's queue was
drafted by Phase P1's retrospective:
[`phase_p2_work_queue.md`](./phase_p2_work_queue.md). Phase P3's queue was
drafted by Phase P2's retrospective:
[`phase_p3_work_queue.md`](./phase_p3_work_queue.md). Phase P4's queue was
drafted by Phase P3's retrospective:
[`phase_p4_work_queue.md`](./phase_p4_work_queue.md). Phase P5's queue was
drafted by Phase P4's retrospective:
[`phase_p5_work_queue.md`](./phase_p5_work_queue.md). Each subsequent phase's
queue is drafted by the prior phase's retrospective.

When Phase P5 declares the master plan done, Track A is closed. If Track B
(deployment) is also closed at that point, the polish plan is complete.
