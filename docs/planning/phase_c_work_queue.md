# Phase C Work Queue

> **Role:** Sequenced, PR-sized work items for Phase C of [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — _Explicit defaults for underspecified queries._
>
> **How to work this file:** Find the first unchecked item below. Review the reference docs it cites. Execute per its acceptance criteria. Run the test commands. Check the item off, commit. Repeat. When every item above is checked, work the final meta-task.
>
> **Do not skip ahead** unless an earlier item is genuinely blocked. Items are ordered to minimize rework — later items assume earlier ones are done.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Phase B retrospective (context for Phase C)

Phase B consolidated the scattered alias and normalization infrastructure:

- Unified stat aliases into a single source of truth (`STAT_ALIASES` in `_constants.py`)
- Auto-generated `STAT_PATTERN` from the alias dict
- Created `_glossary.py` for fuzzy-term definitions
- Reserved undefined skill/quality terms with `shipped=False`
- Normalized text once at pipeline entry
- Consolidated threshold extraction (`extract_threshold_conditions` now handles `N+ STAT`)
- Added verbal-form aliases (`blocked`, `blocking`, `stolen`, `stealing`, `assisting`)

Phase C can now focus purely on default-rule formalization because the alias and term infrastructure is stable.

---

## 1. `[x]` Audit current implicit defaults in `_finalize_route`

**Why:** Before formalizing defaults, we need a clear inventory of where implicit defaults exist, what they do, and whether they match spec §15. The `_finalize_route` function has ~400 lines of if/elif routing with defaults embedded inline.

**Scope:**

- Walk every branch of `_finalize_route` and catalog each implicit default
- For each default, record: trigger condition, what it defaults, whether a `notes` entry exists
- Compare against spec §15.1 (already in place) and §15.2 (to formalize)
- Produce an inventory in `docs/planning/phase_c_defaults_inventory.md`

**Files likely touched:**

- `docs/planning/phase_c_defaults_inventory.md` (new)
- No code changes — reconnaissance only

**Acceptance criteria:**

- Every implicit default in `_finalize_route` is cataloged
- Each is mapped to its spec §15 rule (or flagged as undocumented)
- Gaps between spec and code are identified

**Tests to run:**

- None (reconnaissance only)

**Reference docs to consult:**

- [`parser/specification.md §15`](../architecture/parser/specification.md#15-defaults-for-underspecified-queries)
- `src/nbatools/commands/natural_query.py` — `_finalize_route`

---

## 2. `[ ]` Formalize `<player> + <timeframe>` → summary default

**Why:** This is the most common underspecified pattern. "Jokic last 10" should always route to summary. The rule exists (Phase A item 4 added it) but has a long guard-clause list and no `notes` entry documenting the default.

**Scope:**

- Add a `notes` entry when this default fires: `"default: <player> + <timeframe> → summary"`
- Review the guard-clause list for correctness — ensure it excludes all patterns that should route elsewhere
- Add test cases that verify the default fires and the `notes` entry is present
- Document the rule in spec §15.2 if not already there

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — summary default branch
- `tests/` — new or extended tests for default-rule assertions
- `docs/architecture/parser/specification.md` — §15.2 update if needed

**Acceptance criteria:**

- `notes` includes `"default: <player> + <timeframe> → summary"` when the rule fires
- Guard-clause list is complete and documented
- At least 5 test cases verify the default (e.g., `Jokic last 10`, `Embiid this season`, `LeBron 2023-24`)

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §15.2`](../architecture/parser/specification.md#152-defaults-to-formalize)
- Phase A item 4 implementation

---

## 3. `[ ]` Formalize `<metric>` only → league-wide leaderboard default

**Why:** "points leaders" with no subject should always route to a league-wide leaderboard. This works today but has no explicit `notes` documentation and the rule isn't formally tracked.

**Scope:**

- Add a `notes` entry when a no-subject leaderboard fires: `"default: <metric> only → league-wide leaderboard"`
- Verify edge cases: stat-only (`"scoring"`), stat + timeframe (`"rebounds last 10"`), stat + filter (`"blocks in wins"`)
- Add test cases that verify the default and its `notes` entry

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — leaderboard routing branch
- `tests/` — default-rule assertion tests

**Acceptance criteria:**

- `notes` documents the default when no subject is present
- At least 3 test cases verify the default

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §15.2`](../architecture/parser/specification.md#152-defaults-to-formalize)

---

## 4. `[ ]` Formalize `<player> + <threshold>` → finder default

**Why:** "Curry 5+ threes" should route to occurrence/count. "Jokic over 25 points" should route to finder. The routing exists but the policy isn't explicit and `notes` don't document it.

**Scope:**

- Add `notes` entries when threshold-only queries fire defaults: `"default: <player> + <threshold> → finder"` or `"default: <player> + <threshold> → occurrence count"`
- Clarify the boundary between finder and occurrence routing for threshold queries
- Add test cases covering the boundary

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — threshold-based routing branches
- `tests/` — default-rule assertion tests

**Acceptance criteria:**

- `notes` documents which default rule fired for threshold-only queries
- Boundary between finder and occurrence is explicit and tested
- At least 5 test cases verify the defaults

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §15.2`](../architecture/parser/specification.md#152-defaults-to-formalize)

---

## 5. `[ ]` Add `notes` entries for all remaining default branches

**Why:** After items 2–4 cover the highest-impact defaults, remaining branches (team summary, team record, season-high, fallback finder/game_finder) should also document their defaults via `notes`.

**Scope:**

- Walk every routing branch in `_finalize_route`
- Add `notes` entries for any branch that applies a default (season, stat, limit, sort order) without the user explicitly requesting it
- Focus on defaults that affect the result shape, not cosmetic defaults

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — multiple branches

**Acceptance criteria:**

- Every branch that applies a non-obvious default has a `notes` entry
- Existing `notes` entries (season_high, distinct_count, stat_fallback) remain unchanged
- All tests pass

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §15`](../architecture/parser/specification.md#15-defaults-for-underspecified-queries)

---

## 6. `[ ]` Extract default rules into a named-rules module

**Why:** Default rules are currently inline conditions scattered through `_finalize_route`. Extracting them into named, documented functions makes the policy inspectable and testable independent of the routing chain.

**Scope:**

- Create a helper (e.g., `_default_rules.py` or a section in `_parse_helpers.py`) with named functions for each default rule
- Each function takes the parse state and returns a `(should_fire, notes_message)` tuple
- Refactor `_finalize_route` to call these named rules instead of inline conditions
- Ensure the refactor is behavior-preserving

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — `_finalize_route` refactor
- Possibly new `src/nbatools/commands/_default_rules.py`

**Acceptance criteria:**

- Each default rule has a named function with a docstring stating the policy
- `_finalize_route` calls named rules instead of inline conditions
- All existing tests pass with no behavior change

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §15.4`](../architecture/parser/specification.md#154-defaults-are-product-policy)

---

## 7. `[ ]` Sync spec §15 with implemented defaults

**Why:** After items 1–6, spec §15 should be an exact mirror of what's implemented. This is the documentation-lockstep step.

**Scope:**

- Update spec §15.1 to reflect all defaults now in place
- Update spec §15.2 — move formalized defaults to §15.1, note any that remain unformalized
- Update §15.3 worked examples to match current behavior
- Cross-reference each rule to its named function from item 6

**Files likely touched:**

- `docs/architecture/parser/specification.md` — §15

**Acceptance criteria:**

- Every implemented default is documented in spec §15.1
- §15.2 only contains rules not yet formalized (if any)
- §15.3 worked examples are verified against actual `parse_query` output

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/planning/phase_c_defaults_inventory.md` from item 1

---

## 8. `[ ]` Phase C retrospective and Phase D work queue draft

**Why:** Self-propagating final task. Ensures learnings are captured and the next phase is scoped before this one closes.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals
- Review the plan's Phase D scope ([`query_surface_expansion_plan.md §5.4`](./query_surface_expansion_plan.md)) against what Phase C actually accomplished
- If the plan needs changes, edit [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) in the same session
- Draft `phase_d_work_queue.md` following the same structure as this file

**Files likely touched:**

- `docs/planning/phase_d_work_queue.md` (new)
- `docs/planning/query_surface_expansion_plan.md` (if scope change)
- `docs/planning/phase_c_work_queue.md` (check this item as done)

**Acceptance criteria:**

- `phase_d_work_queue.md` exists and covers Phase D's scope
- Every item in the new queue is PR-sized with clear acceptance criteria
- The final item is the meta-task "retrospective + draft Phase E work queue"
- This item in `phase_c_work_queue.md` is checked off

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_surface_expansion_plan.md §9`](./query_surface_expansion_plan.md) — work queue convention
- [`query_surface_expansion_plan.md §5.4`](./query_surface_expansion_plan.md) — Phase D scope
- This file as a structural template

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase C is complete. The draft of `phase_d_work_queue.md` from item 8 is the handoff artifact.

If any item is skipped (`[-]`), note the reason inline so the reason survives in git history.
