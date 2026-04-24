# Source Approval and Route Expansion Queue

> **Role:** Active master-plan continuation for
> [`master_completion_plan.md`](./master_completion_plan.md).
>
> This queue decides the next product path for the open core capability
> families that remain after the closed Part 1 parser/query-surface plan and
> closed Part 2 execution/data closure record.
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the listed
> test commands. Check the item off, commit. Repeat. When every source decision
> is resolved, work the final meta-task to either draft the next implementation
> queue or update the master plan with documented out-of-scope decisions.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped, with an inline product decision explaining why

---

## Product path decisions

This queue makes these product path decisions before feature implementation
resumes:

| Capability family | Product path for this queue | Product decision |
| --- | --- | --- |
| Clutch | Pursue a source-approval decision before implementation. A source may be an official game-grain clutch split keyed for route joins, or a play-by-play derivation path that can apply the NBA clutch definition honestly. | In scope for source approval. Do not approximate clutch from whole-game logs or period-only box scores. |
| On/off | Pursue a source-approval decision before implementation. Prefer a shared play-by-play plus substitution / stint path if it can also support lineups, but an upstream on/off split table can be approved if it satisfies the route contract. | In scope for source approval. Whole-game `without_player` remains out of scope as an on/off substitute. |
| Lineups | Pursue a source-approval decision before implementation. Prefer a shared play-by-play plus substitution / lineup-stint path if it can also support on/off, but an upstream lineup-unit table can be approved if it satisfies the route contract. | In scope for source approval. Roster membership remains out of scope as a lineup-unit substitute. |
| Quarter / half / OT | Do not pursue route expansion beyond the current coverage-gated boundary as part of the core finish line. | Current boundary is final for core completion: `player_game_finder` and `team_record` only, with trusted period coverage required. Other routes remain out of scope unless a future product queue reopens them. |
| Schedule-context filters | Do not pursue route expansion beyond the current coverage-gated boundary as part of the core finish line. | Current boundary is final for core completion: `team_record` and `player_game_summary` only, with trusted `schedule_context_features` coverage required. Other routes remain out of scope unless a future product queue reopens them. |
| Starter / bench role | Do not pursue route expansion beyond the current coverage-gated player-route boundary as part of the core finish line. | Current boundary is final for core completion: `player_game_summary` and `player_game_finder` only, with trusted `player_game_starter_roles` rows required. Team-level bench semantics are out of scope for the core finish line. |

The out-of-scope route-expansion decisions above are product decisions, not
implementation gaps. Unsupported routes should keep honest notes or unsupported
responses, and current-state docs should describe the supported boundary rather
than implying broader route coverage.

---

## Guardrails

- This is a source-approval and route-scope queue. It should not implement
  source-backed execution directly unless a later item explicitly drafts and
  points to an implementation queue.
- Do not approve a source unless it has clear grain, join keys, coverage
  semantics, trust fields, and enough sample fields to support route execution.
- Do not replace possession-level features with whole-game approximations.
- Do not broaden coverage-gated filters to routes whose command output cannot
  apply the filter honestly.
- Do not update current-state docs to imply product completion until the master
  plan is updated with either execution-backed support or a documented
  out-of-scope product decision.

---

## 1. `[ ]` Sync route-expansion out-of-scope decisions

**Why:** Quarter / half / OT, schedule-context, and starter / bench role are
execution-backed only inside documented coverage-gated route boundaries. The
master plan requires a decision on whether to expand them. This queue decides
not to expand them for the core finish line, so the docs need to carry that
decision explicitly.

**Scope:**

- Update the master plan's core capability table so these families no longer
  read as open-ended route-expansion work.
- Confirm current-state docs describe the final supported route boundaries:
  - quarter / half / OT on `player_game_finder` and `team_record`
  - schedule-context filters on `team_record` and `player_game_summary`
  - starter / bench role on `player_game_summary` and `player_game_finder`
- Keep unsupported-route fallback notes documented where those notes are part of
  shipped behavior.
- Do not remove coverage-gating language; trusted source coverage is still part
  of the supported boundary.

**Files likely touched:**

- `docs/planning/master_completion_plan.md`
- `docs/reference/query_catalog.md`
- `docs/reference/current_state_guide.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`

**Acceptance criteria:**

- Broader route expansion for the three coverage-gated families is documented
  as out of scope for the core finish line.
- The docs still name the supported route boundaries and coverage gates.
- The master plan no longer treats those three families as open core blockers
  once this item is complete.

**Tests to run:**

- None for docs-only scope decisions.
- If query smoke inventory changes, run `make test-phase-smoke` and
  `make test-smoke-queries`.

**Reference docs to consult:**

- [`master_completion_plan.md`](./master_completion_plan.md)
- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 2. `[ ]` Approve or reject the clutch source path

**Why:** Clutch remains unfiltered because no trustworthy source is approved.
The product needs either a source-backed implementation path or a product
out-of-scope decision.

**Scope:**

- Review current source-boundary artifacts for clutch, especially the Phase G
  segment review.
- Evaluate approved-source candidates:
  - an official game-grain clutch split source that can join to current route
    outputs without changing the meaning of the result
  - play-by-play plus score-state derivation using the NBA clutch definition:
    last 5 minutes of the fourth quarter or overtime, score within 5
- If a source is approved, document the dataset contract before implementation:
  grain, keys, clutch definition, player/team scope, metrics, sample-size
  fields, trust fields, and coverage fallback behavior.
- If no source is approved, record a product out-of-scope decision for clutch
  as a core finish-line capability rather than leaving another open deferral.

**Files likely touched:**

- `docs/planning/master_completion_plan.md`
- `docs/planning/phase_g_segment_data_review_handoff.md`
- `docs/reference/data_contracts.md`
- `docs/reference/query_catalog.md`
- a new `docs/planning/*clutch_source_boundary*.md` artifact if rejected or
  deferred by product decision

**Acceptance criteria:**

- Clutch has exactly one of these outcomes:
  - an approved source contract and a named implementation queue to draft next
  - a documented product out-of-scope decision that removes clutch from the
    core finish-line requirements
- The decision explicitly rejects whole-game logs and period-only box scores as
  clutch substitutes.
- The master plan is updated to reflect the decision.

**Tests to run:**

- None for a docs-only source decision.
- If implementation code changes, use the test targets named by the drafted
  implementation queue.

**Reference docs to consult:**

- [`phase_g_segment_data_review_handoff.md`](./phase_g_segment_data_review_handoff.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)

---

## 3. `[ ]` Approve or reject the on/off source path

**Why:** `player_on_off` is a placeholder by explicit Phase I deferral. The
product needs either a trustworthy on/off source path or an out-of-scope
decision for the core finish line.

**Scope:**

- Reopen the Phase I source boundary and verify whether an upstream split,
  play-by-play plus substitutions, or a trusted stint table is now approved.
- Prefer a shared stint-source path if it can also support lineup execution, but
  keep the on/off contract independently testable.
- If a source is approved, document the dataset contract before implementation:
  grain, keys, queried player identity, `presence_state`, possessions/minutes,
  metrics, trust fields, and coverage fallback behavior.
- If no source is approved, record a product out-of-scope decision for on/off as
  a core finish-line capability rather than leaving another open deferral.

**Files likely touched:**

- `docs/planning/master_completion_plan.md`
- `docs/planning/phase_i_on_off_source_boundary.md`
- `docs/reference/data_contracts.md`
- `docs/reference/query_catalog.md`
- a new `docs/planning/*on_off_product_decision*.md` artifact if rejected by
  product decision

**Acceptance criteria:**

- On/off has exactly one of these outcomes:
  - an approved source contract and a named implementation queue to draft next
  - a documented product out-of-scope decision that removes on/off from the
    core finish-line requirements
- The decision keeps whole-game absence separate from possession-level on/off.
- The master plan is updated to reflect the decision.

**Tests to run:**

- None for a docs-only source decision.
- If implementation code changes, use the test targets named by the drafted
  implementation queue.

**Reference docs to consult:**

- [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md)
- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 4. `[ ]` Approve or reject the lineup source path

**Why:** `lineup_summary` and `lineup_leaderboard` are placeholders by explicit
Phase J deferral. The product needs either a trustworthy lineup source path or
an out-of-scope decision for the core finish line.

**Scope:**

- Reopen the Phase J source boundary and verify whether an upstream lineup-unit
  table, play-by-play plus substitutions, or a trusted lineup/stint table is now
  approved.
- Prefer a shared stint-source path if it can also support on/off execution, but
  keep the lineup contract independently testable.
- If a source is approved, document the dataset contract before implementation:
  grain, unit membership key, player identity fields, `unit_size`,
  `minute_minimum`, sample-size fields, metrics, trust fields, and coverage
  fallback behavior.
- If no source is approved, record a product out-of-scope decision for lineups
  as a core finish-line capability rather than leaving another open deferral.

**Files likely touched:**

- `docs/planning/master_completion_plan.md`
- `docs/planning/phase_j_lineup_source_boundary.md`
- `docs/reference/data_contracts.md`
- `docs/reference/query_catalog.md`
- a new `docs/planning/*lineup_product_decision*.md` artifact if rejected by
  product decision

**Acceptance criteria:**

- Lineups have exactly one of these outcomes:
  - an approved source contract and a named implementation queue to draft next
  - a documented product out-of-scope decision that removes lineups from the
    core finish-line requirements
- The decision keeps roster membership separate from lineup-unit execution.
- The master plan is updated to reflect the decision.

**Tests to run:**

- None for a docs-only source decision.
- If implementation code changes, use the test targets named by the drafted
  implementation queue.

**Reference docs to consult:**

- [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md)
- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 5. `[ ]` Draft the next implementation queue or close the master blockers

**Why:** This queue should not close with another informal residual list. After
the source and route-scope decisions are complete, the repo needs exactly one
active continuation or a master-plan completion statement.

**Scope:**

- If any of `clutch`, `on/off`, or `lineups` has an approved source path, draft
  the next implementation queue under `docs/planning/`.
- If multiple families share a play-by-play / substitution / stint source,
  make the first implementation queue source-first rather than route-first.
- If all three source-backed families are product out of scope and the
  route-expansion decisions are already synced, update
  `master_completion_plan.md` with the whole-plan completion status required by
  the master completion rule.
- Update `docs/index.md` and any closed-plan continuation sections that point to
  this queue.

**Acceptance criteria:**

- The master plan names exactly one active continuation after this queue closes,
  or says the whole plan is done.
- No family remains in an open-ended deferral state.
- Any newly drafted queue has PR-sized items, acceptance criteria, and test
  commands.

**Tests to run:**

- None for docs-only queue drafting.
- If implementation work is included by mistake, split it into the next queue
  and run the tests named there.

**Reference docs to consult:**

- [`master_completion_plan.md`](./master_completion_plan.md)
- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`docs/index.md`](../index.md)
