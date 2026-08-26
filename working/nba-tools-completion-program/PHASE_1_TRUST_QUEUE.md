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

  ### Status: repair iteration 3 — under repair, not accepted

  Candidate `69d9a1e` was rejected by independent review. Candidate `7d56a664`
  (repair iteration 2) was rejected again by the same reviewer. Do not mark this
  item complete until a new exact head is independently accepted.

  #### Why iteration 2 was rejected

  **Blocker 1 — the condition ledger still failed open.** Iteration 2 moved the
  detections into `RequestedCondition` records, but the gate still read

      if no condition was recorded: allow the default

  so a detector miss remained a grant of permission. Eight reviewer
  counterexamples proved it: `best team while down two starters`, `best team at
  less than full strength` and `which team won most while missing half its
  rotation` still returned populated 10-row team points-per-game leaderboards on
  `7d56a664`. The claim that "a detector miss now only loses coverage" was not
  true of that implementation.

  **Blocker 2 — the advertised receipt migration was incomplete.** The docs named
  four migrated routes. `player_game_summary` declared fifteen filters and marked
  one; `team_record` and `season_leaders` serialized the ledger on some paths and
  not others; no route attached receipts to a successful result. The validator
  could not see any of it, because it only inspected badges on non-ok results and
  scored "every badge dropped" as a pass.

  #### What iteration 3 changes

  **Broad-default authorization is now positive and fail-closed.**
  `commands/_broad_default_authorization.py` decides eligibility by span
  coverage: every content-bearing word must be claimed by a component the
  leaderboard implements (ranking intent, sort direction, population, requested
  metric, time window, a supported qualifier, or grammar). Anything left over is
  residual and refuses with `residual_query_content`. Each claimer is gated on
  the parse slot it explains, so an unrecognized phrase produces *no claim* —
  vocabulary gaps cost coverage, they cannot manufacture permission. Metric
  evidence found inside a condition span is recorded and never promoted, so
  `scorer` in `when its leading scorer was out` cannot become a scoring
  leaderboard. `RequestedCondition` records still run and still sharpen the
  refusal copy; they are additive evidence with no authorizing power.

  A second, narrow backstop refuses on **any** route when a recorded condition
  never bound to an entity, which covers the two counterexamples where the parser
  over-resolved a common word to a player name (`key` → Braxton Key).

  **The receipt migration is now complete for the four advertised routes.**
  `MIGRATED_ROUTE_FILTERS` in `commands/_filter_receipts.py` is the single
  published contract read by the docs, the route tests, and the validator.
  `build_result` on each route is wrapped in `@emits_filter_receipts`, which
  opens the ledger and stamps it onto every result the route returns — success
  included — so a `return` added later is instrumented by construction rather
  than by remembering. `declare()` no longer tests truthiness: `rest_days = 0`
  ("on no rest") is a genuine request and was being dropped from the ledger
  entirely.

  **The validator now checks three claims, not one:** completeness (every
  requested tracked filter has a serialized final state), no false badge, and no
  *lost* badge. The third is the one that made "drop everything" look safe.

  #### Proofs that fail on `7d56a664`

  | Proof | On `7d56a664` | On this head |
  | --- | --- | --- |
  | 10 out-of-vocabulary residual queries | 10/10 returned populated leaderboards with an invented metric | 10/10 refuse with `residual_query_content` |
  | `tools/filter_receipt_validator.py` | 8/24 pass, 16 fail | 24/24 pass, 4/4 routes covered |
  | Receipt matrix (11 natural + 5 structured) | 12/16 rows fail | 16/16 pass |
  | `FilterExecutionLedger.declare("rest_days", 0)` | dropped, ledger empty | declared |
  | Truthful badge preservation | `LOST_BADGE` on the structured finder case | preserved |

  #### Validation, data generation `queue-d-local-7e55c810-20260715`

  | Suite | Result |
  | --- | --- |
  | `make test` | 4054 passed / 0 failed / 0 skipped |
  | `make test-parser` | 1050 passed |
  | `make test-query` | 1194 passed |
  | `make test-api` | 232 passed, 3822 deselected |
  | `make test-output` | 350 passed |
  | `make test-preflight` | 3982 passed |
  | focused: integrity + intent + receipts | 289 passed |
  | Raw QA | 380/380 expectation pass, 0 failed case ids |
  | `make parser-examples-sweep` | 402 cases, 394 pass / 8 fail, **0 verdict changes** vs `7d56a664` |
  | `tools/filter_execution_sweep.py` | 521 combinations, 99 APPLIED / 376 REFUSED / 0 LIED / 46 DROPPED / 0 ERROR — **0 classification changes** vs `7d56a664` |
  | `tools/filter_receipt_validator.py` | 24/24 pass, 4/4 advertised routes covered (8/24 on `7d56a664`) |
  | frontend build / lint / test | build ok, lint clean, 425 tests in 37 files |
  | `ruff check` / `ruff format --check` | clean / 252 files formatted |
  | `make docs-governance` | inventory check + governance check pass |
  | `git diff --check` | clean |

  The filter sweep total is unchanged and **must not be cited as evidence for
  either blocker**. Its seed matrix contains no out-of-vocabulary residual query
  and no mixed-filter short-circuit case; that is why the receipt validator and
  the intent-preservation counterprobes exist.

  #### Known coverage losses, deliberate

  - `NBA three point leaders this season` and `top three point shooters this
    season` now refuse. Both resolved to `pts` — an invented metric for a
    three-point question — so the refusal is the honest outcome. Both are
    input-only exploratory samples with no assertion; giving them a real 3PT
    metric is parser work outside this PR.
  - `how do teams do when their star is out` now reports its refusal on
    `season_team_leaders` rather than `season_leaders`, because the question
    names teams. Corpus expectation updated.
  - `Lakers record without their leading scorer` — listed below as a 1B input —
    is no longer a lying answer. On `7d56a664` it returned the Lakers' top-5
    scoring leaderboard (`season_leaders`, 5 rows, `ok`). The unbound-condition
    backstop now refuses it with both conditions named. **The feature is still
    not built**: this is the lie removed, not the question answered, and it stays
    in the 1B queue.

- [ ] **1B — Not yet drafted**

  Not drafted while 1A is under repair. Two same-family defects remain
  pre-existing and unchanged, and are candidate inputs:

  - `Lakers record without their leading scorer` — as of 1A's unbound-condition
    backstop this refuses honestly instead of returning the Lakers' top-5 scoring
    leaderboard, but it still does not *answer*. The record intent is understood
    and the availability condition is recorded (`player_availability` and
    `role_reference`, both unresolved); what is missing is a way to resolve "the
    team's leading scorer" to a player and hand it to `team_record` as
    `without_player`. That resolution is the 1B feature, and 1B can consume the
    parse state 1A already produces without new detection work.
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
