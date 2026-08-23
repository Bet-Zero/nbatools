# Phase 1 — Trust Repair Queue

Task-coordination artifact. Not durable documentation. See
[`PLAN.md`](PLAN.md) for the program-level objective and baselines.

Ordered. One bounded PR per item. Work the first unchecked item.

## Queue

- [x] **1A — Intent preservation / no-broad-fallback repair** *(complete, PR open)*

  Stop the engine substituting a broad metric-only leaderboard for a question
  whose real conditions it never executed.

  Scope:
  - Concept-level guard preventing metric-only leaderboard defaults when the
    query carries unresolved or unsupported semantics (unbound player
    availability/absence, unresolved role-based player references such as
    "leading scorer" / "best player" / "star", subjective narrative outcome
    concepts with no approved metric, or any other meaningful condition the
    selected route would discard).
  - Clutch blocker identified as clutch context, not an invented points metric.
  - Stale "returning a broad points leaderboard fallback" note removed.
  - Requested-but-unexecuted filters never rendered as applied filters.
  - Unresolved clutch / opponent-quality fragments with no usable subject or
    metric never produce a populated default points leaderboard.

  Acceptance: every required negative probe returns a stable non-`ok` result
  with no populated substituted leaderboard, no invented default metric, no
  unrelated headline, no applied-filter claim for an unexecuted filter, and
  notes describing the real unsupported or ambiguous condition; every required
  positive control keeps its established behavior; filter execution sweep shows
  zero LIED and zero ERROR with every count change explained.

  Delivered on branch `claude/phase-1a-intent-preservation`. Verified against
  data generation `queue-d-local-7e55c810-20260715`: all 15 negative probes
  return a stable non-`ok` result with no rows, no invented metric, and no
  applied-filter badge; all positive controls preserved; Raw QA 361/361;
  filter execution sweep 99 APPLIED / 376 REFUSED / 0 LIED / 46 DROPPED /
  0 ERROR, unchanged from the Phase 0B baseline; parser examples sweep
  394 pass / 8 fail with zero per-case verdict changes from baseline.

- [ ] **1B — Not yet drafted** *(next unchecked item)*

  Drafted after 1A merges. Two same-family defects were found during 1A and
  deliberately left out of its bounded scope; both are pre-existing and
  unchanged by 1A, and both are candidate inputs for 1B:

  - `Lakers record without their leading scorer` returns the Lakers' top-5
    scoring leaderboard (`season_leaders`, 5 rows, `ok`). The record intent and
    the unbound availability condition are both discarded. Same intent-loss
    family as 1A, but with a resolved subject entity, so 1A's subject-less
    guard does not cover it. No applied-filter badge is claimed, so this is a
    silent drop rather than a false claim.
  - `leading scorers this season` returns `error` / `unrouted` with no
    explanation. A plural role population that names its own metric should
    either answer or refuse understandably.

  Do not start Phase 1 items beyond 1A until 1A is merged and 1B is written
  here.

## Rules

- Mark an item complete only when its acceptance criteria are met and the
  required validation passes.
- Completing one item is not Phase 1 completion and is not completion-program
  completion.
