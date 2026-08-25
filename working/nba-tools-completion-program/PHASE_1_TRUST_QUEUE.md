# Phase 1 — Trust Repair Queue

Task-coordination artifact. Not durable documentation. See
[`PLAN.md`](PLAN.md) for the program-level objective and baselines.

Ordered. One bounded PR per item. Work the first unchecked item.

## Queue

- [ ] **1A — Intent preservation / no-broad-fallback repair** *(under repair after independent reject — PR #294 open)*

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

  ### Status: repair iteration 2, awaiting exact-head independent re-review

  Candidate `69d9a1e` was **rejected** by independent review (Codex) for two
  blocking design defects and one high-severity copy defect. Do not mark this
  item complete until the new exact head is independently accepted.

  **Blocker 1 — the guard was phrase-oriented.** Three regexes were the
  authoritative safety boundary, so paraphrases escaped: `best team when leading
  scorer is suspended`, `teams that do best shorthanded`, `best team with no
  stars` and five more still returned a populated points-per-game leaderboard.
  Replaced with a normalized condition ledger in parse state
  (`commands/_condition_semantics.py`): detectors record `RequestedCondition`
  records, `ROUTE_CONDITION_SUPPORT` declares what each route can represent, and
  a broad default may fire only when every recorded condition is represented or
  bound. Detectors can no longer authorize a default by failing to match.

  **Blocker 2 — `no_match` did not prove execution.** `Tatum clutch stats at
  home on January 1 2024` returned `no_match` showing a `Clutch` applied badge
  over a sample the clutch filter never touched, because the date and location
  filters emptied it first. Replaced with per-filter execution receipts
  (`commands/_filter_receipts.py`) recorded by the route that filters.
  `applied_filters` is now derived from receipts. **Bounded migration:**
  `player_game_finder`, `player_game_summary`, `season_leaders`, `team_record`.
  The contract in `result_contracts.md` states that boundary rather than
  claiming universal coverage.

  **High — copy was context-inaccurate.** Opponent quality no longer claims the
  product does not support it (`Celtics record against playoff teams` answers);
  the message is scoped to this query and route. Clutch now splits into two
  blockers: `clutch` for an unbound fragment, `clutch_coverage` for an
  understood question whose trusted play-by-play coverage is missing.

  **Validation blind spot.** The filter sweep classified every `no_result` as
  REFUSED before reading badges, so it could not see the false claim. Added
  `tools/filter_receipt_validator.py` (fails 7/11 on `69d9a1e`, passes 11/11 on
  the repair) and taught the sweep to classify an unproven badge on a non-ok
  result as LIED. Sweep totals are unchanged because its seed matrix contains no
  mixed-filter short-circuit case — that is why the separate validator exists,
  and the sweep total must not be cited as proof this defect is fixed.

  Verified against data generation `queue-d-local-7e55c810-20260715`:
  `make test` 3959 passed / 0 failed / 0 skipped; Raw QA 372/372; parser
  examples sweep 394 pass / 8 fail with zero verdict changes versus the rejected
  candidate; filter sweep 99 APPLIED / 376 REFUSED / 0 LIED / 46 DROPPED /
  0 ERROR with zero classification changes.

- [ ] **1B — Not yet drafted**

  Not drafted while 1A is under repair. Two same-family defects remain
  pre-existing and unchanged, and are candidate inputs:

  - `Lakers record without their leading scorer` returns the Lakers' top-5
    scoring leaderboard (`season_leaders`, 5 rows, `ok`). The record intent and
    the unbound availability condition are both discarded. Same intent-loss
    family as 1A, but with a resolved subject entity, so 1A's subject-less
    guard does not cover it. No applied-filter badge is claimed, so this is a
    silent drop rather than a false claim. 1A's condition ledger already records
    both conditions for this query (`player_availability` and `role_reference`,
    both unresolved) even though a team resolved, so 1B can consume that state
    without new detection work.
  - `leading scorers this season` returns `error` / `unrouted` with no
    explanation. A plural role population that names its own metric should
    either answer or refuse understandably.

  Do not start Phase 1 items beyond 1A until 1A is independently accepted,
  merged, and 1B is written here.

## Rules

- Mark an item complete only when its acceptance criteria are met and the
  required validation passes.
- Completing one item is not Phase 1 completion and is not completion-program
  completion.
