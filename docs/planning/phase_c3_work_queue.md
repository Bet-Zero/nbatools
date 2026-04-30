# Phase C3 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) - _player
> comparison layout._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit, open a PR, wait for CI, merge when
> green, then immediately move on to the next unchecked item and repeat.
> Continue working items in order without stopping until every item is checked
> `[x]` or you hit a genuine blocker (failing tests you cannot resolve, missing
> credentials, an ambiguous decision that needs the user). If blocked, leave the
> item marked `[~]` with an inline note and stop. Do not stop merely because one
> item finished - the default is to keep going.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped (with inline note explaining why)

---

## Phase C3 goal

Replace the generic player-comparison table treatment with a purpose-built
side-by-side comparison layout for player-vs-player queries such as
`Jokic vs Embiid this season`. The layout should make both player identities
visible, keep mixed-player pages visually neutral, highlight the most important
metric differences without inventing new NBA facts, and retain dense table
detail for supporting rows.

C3 is not complete until `player_compare` results have dedicated player cards,
metric comparison treatment, responsive mobile behavior, documented fallbacks,
and generic comparison rendering remains intact for team, matchup, playoff, and
unknown comparison-shaped routes.

Guardrails:

- Keep query parsing, filtering, aggregate computation, and route selection in
  the engine.
- Do not add player comparison business logic to React. React may compare
  existing numeric values only to choose presentation emphasis.
- Route only `player_compare` responses to the player-comparison renderer.
- Preserve `ComparisonSection.tsx` as the generic fallback for `team_compare`,
  team matchup records, playoff comparisons, decade comparisons, and unknown
  comparison routes until their later phases redesign them.
- Keep mixed-player comparison views neutral except for player headshots and
  small team identity badges. Do not split the surface into team-color halves.
- Keep full summary and comparison detail available for columns/rows not
  promoted into the designed layout.

---

## 1. `[x]` Inventory comparison row shapes and renderer boundary

**Why:** `query_class: "comparison"` covers player comparisons, team
comparisons, matchup records, playoff comparisons, and decade breakdowns. C3
needs verified row-shape guidance before routing only the player comparison
subset into a new renderer.

**Scope:**

- Inventory representative `summary` and `comparison` sections for
  `player_compare`, `team_compare`, team matchup records, playoff matchup
  history, and decade comparison routes.
- Identify stable player identity fields, team context fields, primary metric
  candidates, comparison-row shapes, and rows that should remain detail-only.
- Write the inventory as a planning artifact for C3 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c3_comparison_inventory.md` (new)
- `docs/planning/phase_c3_work_queue.md`

**Acceptance criteria:**

- Inventory names representative routes and section fields.
- Inventory distinguishes player-comparison fields from generic comparison
  shapes that must keep fallback rendering.
- Residual API/result-contract gaps are documented without blocking frontend
  work that can use existing rows.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/ComparisonSection.tsx`
- `src/nbatools/commands/player_compare.py`
- `src/nbatools/commands/team_compare.py`

---

## 2. `[x]` Establish the player-comparison renderer boundary

**Why:** Player comparison needs a dedicated owner without accidentally
redesigning every `comparison` result shape.

**Scope:**

- Add a dedicated player-comparison renderer component.
- Route only `player_compare` responses to that component from
  `ResultSections.tsx`.
- Preserve `ComparisonSection.tsx` as the generic comparison fallback for team,
  matchup, playoff, decade, and unknown comparison routes.
- Keep current summary and comparison detail visible; this item may add only
  minimal visual scaffolding needed to prove the boundary.
- Add frontend tests for player-comparison routing and generic comparison
  fallback behavior.

**Files likely touched:**

- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/PlayerComparisonSection.tsx` (new)
- `frontend/src/components/PlayerComparisonSection.module.css` (new)
- `frontend/src/test/ResultSections.test.tsx`

**Acceptance criteria:**

- `player_compare` results have a distinct owner component.
- Team, matchup, playoff, decade, and unknown comparison responses still render
  through the generic comparison path.
- No NBA calculation, filtering, or query parsing is added to React.
- The new component uses existing Part 1 primitives where practical.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c3_comparison_inventory.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/ComparisonSection.tsx`
- `frontend/src/api/types.ts`

---

## 3. `[x]` Build side-by-side player identity cards

**Why:** A player comparison should first read as "these two players" instead
of as anonymous table rows.

**Scope:**

- Use player identity fields from existing summary rows and metadata when
  available.
- Render side-by-side player cards with headshots, names, team context badges,
  games/sample context, and top-line stats.
- Promote only values already present in the response, such as points,
  rebounds, assists, record, efficiency, or games/sample metrics.
- Keep full summary detail available below the cards.
- Add tests for populated player comparison rows, missing ids/images, missing
  optional stats, and sparse summary rows.

**Files likely touched:**

- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/PlayerComparisonSection.module.css`
- Frontend tests

**Acceptance criteria:**

- The two compared players are visually primary.
- Missing identity fields degrade to initials/text without throwing.
- Full summary detail remains reachable for data not promoted into cards.
- Mobile widths stack cleanly without text overlap.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c3_comparison_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`
- `frontend/src/design-system/StatBlock.tsx`

---

## 4. `[x]` Add metric comparison and difference emphasis

**Why:** The user needs to scan who leads each important metric without losing
the exact underlying table.

**Scope:**

- Render the `comparison` section as a metric comparison layout instead of only
  a generic table.
- Highlight leaders/differences using only existing numeric values supplied by
  the response.
- Preserve neutral mixed-player styling and avoid implying team ownership of
  the whole surface.
- Keep the full comparison detail table available for all metric rows.
- Add tests for numeric leader emphasis, ties, nonnumeric/missing values, and
  detail-table preservation.

**Files likely touched:**

- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/PlayerComparisonSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Key metric rows are easier to scan than the generic table.
- Leader/tie emphasis is presentation-only and never changes data.
- Nonnumeric or sparse rows degrade without throwing.
- The full comparison table remains available.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c3_comparison_inventory.md`
- `frontend/src/components/tableFormatting.ts`
- `frontend/src/components/DataTable.tsx`

---

## 5. `[x]` Polish comparison responsive detail and docs

**Why:** C3 should close implementation with player comparisons feeling
complete on desktop and mobile, with docs accurately describing boundaries and
fallbacks.

**Scope:**

- Verify and tighten player-comparison layout at representative desktop,
  tablet, and mobile widths.
- Ensure long player names, long metric labels, missing identities, ties, and
  sparse rows do not overlap or hide detail.
- Update `docs/operations/ui_guide.md` with player-comparison renderer
  behavior, neutral mixed-player treatment, detail-table fallback, and edge-case
  handling.
- Add or adjust frontend tests for edge cases found during polish.
- Confirm generic comparison fallback rendering remains unaffected.

**Files likely touched:**

- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/PlayerComparisonSection.module.css`
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- UI docs name the player-comparison renderer and its boundary.
- Edge cases have either test coverage or documented fallback behavior.
- Generic comparison routes still work through `ComparisonSection.tsx`.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/ComparisonSection.tsx`

---

## 6. `[ ]` Phase C3 retrospective and C4 handoff

**Why:** Self-propagating final task. It closes player-comparison work and
creates the next executable Part 2 queue.

**Scope:**

- Write the Phase C3 retrospective in this file.
- Refresh `component_experience_plan.md` if C3 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c4_work_queue.md` for player game finder layout work.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C4.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c3_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c4_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c4_work_queue.md` exists with concrete PR-sized player-game-finder
  items.
- Active-continuation docs point to Phase C4.
- Phase C3 is explicitly closed without implying Part 2 or the polish plan is
  complete.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- This file
- `docs/planning/component_experience_plan.md`
- `docs/planning/product_polish_master_plan.md`

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase C3 is complete. The draft of
`phase_c4_work_queue.md` from item 6 is the handoff artifact.
