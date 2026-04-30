# Phase C2 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) -
> _leaderboard layout._
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

## Phase C2 goal

Replace the generic leaderboard table treatment with a purpose-built ranked
layout for player and team leaderboards. The layout should make rank, entity
identity, and the ranked metric immediately scannable, keep the #1 row visually
distinct, and retain table detail for supporting columns.

C2 is not complete until leaderboard results have a ranked-card/list treatment,
identity-aware rows, metric-value prominence, responsive mobile behavior, and
documentation that names the renderer boundary.

Guardrails:

- Keep ranking, filtering, qualifiers, and metric computation in the engine.
- Do not infer new basketball facts in React; use values already present in the
  leaderboard rows and metadata.
- Preserve generic fallback rendering for unknown result shapes.
- Team colors may appear only as badge/identity accents in mixed league-wide
  leaderboards; do not theme the whole result by one team.
- Keep dense table detail available for columns that are not promoted into the
  ranked-row layout.

---

## 1. `[x]` Inventory leaderboard row shapes and metric priorities

**Why:** Leaderboard rows vary across player, team, and occurrence-style
routes. The renderer needs a verified row-shape inventory before selecting
which fields become the primary rank/value/entity treatment.

**Scope:**

- Inventory representative `leaderboard` result rows for player leaderboards,
  team leaderboards, and occurrence leaderboards that currently render through
  `LeaderboardSection.tsx`.
- Identify stable identity fields, rank fields, likely ranked metric fields,
  qualifier/context fields, and columns that should remain detail-only.
- Write the inventory as a planning artifact for C2 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c2_leaderboard_inventory.md` (new)
- `docs/planning/phase_c2_work_queue.md`

**Acceptance criteria:**

- Inventory names representative routes and row fields.
- Inventory distinguishes reliable fields from inferred/display-only fields.
- Residual API/result-contract gaps are documented without blocking frontend
  work that can use existing rows.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/LeaderboardSection.tsx`
- `src/nbatools/commands/season_leaders.py`
- `src/nbatools/commands/season_team_leaders.py`

---

## 2. `[x]` Build the ranked leaderboard row layout

**Why:** The primary leaderboard answer should read as ranked results, not a
generic table dump.

**Scope:**

- Replace the primary leaderboard presentation with a ranked card/list layout
  inside `LeaderboardSection.tsx`.
- Promote rank, entity name, and the selected ranked metric/value into the row
  hierarchy.
- Keep a full detail table available below the ranked list for supporting
  columns.
- Preserve no-result/empty behavior.
- Add tests for populated leaderboards, empty leaderboards, and detail table
  preservation.

**Files likely touched:**

- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/LeaderboardSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Leaderboards render as ranked rows/cards before the detail table.
- The #1 row has stronger but restrained emphasis.
- Supporting columns remain reachable in the detail table.
- No ranking or qualifier calculation is added to React.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c2_leaderboard_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/DataTable.tsx`

---

## 3. `[x]` Add identity-aware leaderboard rows

**Why:** Player and team leaderboards should make the ranked entity visually
recognizable while staying neutral in mixed league-wide contexts.

**Scope:**

- Use player headshots when rows contain stable player identity fields.
- Use team badges/logos when rows contain stable team identity fields.
- Keep fallback initials/badges for missing ids and historical/unknown teams.
- Ensure mixed player/team or sparse rows still render without throwing.
- Add tests for player rows, team rows, missing ids, and sparse rows.

**Files likely touched:**

- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/LeaderboardSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Player leaderboard rows show avatar treatment when possible.
- Team leaderboard rows show badge/logo treatment when possible.
- Missing identity fields degrade to text/fallback marks.
- The result remains visually neutral except for identity accents.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c2_leaderboard_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`

---

## 4. `[x]` Tighten metric emphasis, qualifiers, and mobile behavior

**Why:** Leaderboards need to scan cleanly on desktop and mobile, even when
metric names are long, qualifier/context fields are present, or rows are
sparse.

**Scope:**

- Refine ranked metric selection and display labels using only existing row
  fields and inventory guidance.
- Surface qualifier/context fields as secondary metadata when they exist.
- Verify and tighten layout at representative desktop, tablet, and mobile
  widths.
- Add tests for long names, long metric labels, missing ranked values, and
  compact mobile-safe row content.

**Files likely touched:**

- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/LeaderboardSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Ranked metric values are visually prominent and consistently aligned.
- Qualifier/context metadata does not overwhelm the primary rank/entity/value.
- Long labels and sparse rows do not overlap or hide detail.
- Mobile rows remain readable without horizontal-only dependence.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c2_leaderboard_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/components/LeaderboardSection.module.css`

---

## 5. `[ ]` Polish leaderboard docs and renderer boundary

**Why:** C2 should close implementation with docs that accurately describe the
shipped leaderboard renderer and its fallbacks.

**Scope:**

- Update `docs/operations/ui_guide.md` with leaderboard renderer behavior,
  identity treatment, detail-table fallback, and edge-case handling.
- Add or adjust tests for any edge cases found during polish.
- Confirm generic fallback rendering remains unaffected for unknown sections.
- Keep this item scoped to polish/docs; defer broader query-class work to later
  phases.

**Files likely touched:**

- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/LeaderboardSection.module.css`
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- UI docs name the leaderboard renderer and its boundary.
- Edge cases have either test coverage or documented fallback behavior.
- Generic fallback rendering still works for unknown query classes.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`

---

## 6. `[ ]` Phase C2 retrospective and C3 handoff

**Why:** Self-propagating final task. It closes leaderboard work and creates
the next executable Part 2 queue.

**Scope:**

- Write the Phase C2 retrospective in this file.
- Refresh `component_experience_plan.md` if C2 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c3_work_queue.md` for player comparison layout work.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C3.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c2_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c3_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c3_work_queue.md` exists with concrete PR-sized player-comparison
  items.
- Active-continuation docs point to Phase C3.
- Phase C2 is explicitly closed without implying Part 2 or the polish plan is
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

When all items above are checked `[x]`, Phase C2 is complete. The draft of
`phase_c3_work_queue.md` from item 6 is the handoff artifact.
