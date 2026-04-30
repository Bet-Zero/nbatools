# Phase C7 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) -
> _head-to-head and playoff layouts._
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

## Phase C7 goal

Replace table-first treatment for head-to-head and playoff-specific query
families with purpose-built layouts. Head-to-head results should make the two
participants, record/sample, season/date scope, and supplied game/detail rows
scannable before dense tables. Playoff results should expose team/round/series
context, appearances, records, and matchup history in a layout that reads like
postseason history instead of generic summary or leaderboard rows.

C7 is not complete until head-to-head/matchup routes and playoff routes have
explicit renderer ownership, full detail tables remain visible, mobile behavior
is covered, docs describe renderer boundaries and fallbacks, and unrelated
summary/comparison/leaderboard fallback paths remain available.

Guardrails:

- Keep record calculation, playoff round parsing, series aggregation,
  head-to-head filtering, and leaderboard ranking in the engine/API.
- Do not infer missing playoff series, game lists, records, or winner labels in
  React. Only promote fields supplied in the result payload.
- Mixed-team and mixed-player views remain neutral except for row/card identity
  accents. Do not apply full-surface team theming to head-to-head or playoff
  matchup views.
- Preserve full detail tables for columns not promoted into designed layouts.
- Keep existing player summary, leaderboard, comparison, finder, team/split,
  streak, count, occurrence, and generic fallback behavior intact.

---

## 1. `[x]` Inventory head-to-head and playoff row shapes

**Why:** C7 spans comparison, summary, and leaderboard query classes. The queue
needs verified row-shape guidance before assigning renderer ownership.

**Scope:**

- Inventory representative rows and metadata for head-to-head-style results:
  `team_matchup_record`, `player_compare` with `head_to_head_used`,
  `team_compare` with `head_to_head_used`, and `matchup_by_decade`.
- Inventory representative rows and metadata for playoff routes:
  `playoff_history`, `playoff_appearances`, `playoff_matchup_history`, and
  `playoff_round_record`.
- Identify stable participant fields, record/sample fields, round/series
  fields, season/date fields, detail sections, identity inputs, and
  detail-only columns.
- Distinguish C7-owned routes from generic comparison, generic summary,
  generic leaderboard, team-record, playoff-shaped unknown, and fallback
  routes that must keep current behavior.
- Write the inventory as a planning artifact for C7 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c7_head_to_head_playoff_inventory.md` (new)
- `docs/planning/phase_c7_work_queue.md`

**Acceptance criteria:**

- Inventory names representative route/query-class combinations and section
  fields.
- Inventory identifies renderer ownership boundaries and fallback boundaries.
- Residual API/result-contract gaps are documented without blocking frontend
  work that can use existing rows.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/TeamRecordSection.tsx`
- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/player_compare.py`
- `src/nbatools/commands/team_compare.py`
- `src/nbatools/commands/playoff_history.py`
- `src/nbatools/commands/structured_results.py`

---

## 2. `[x]` Establish C7 renderer boundaries

**Why:** Head-to-head and playoff routes need dedicated owners without taking
over ordinary comparisons, generic summaries, generic leaderboards, or the C5
team-record paths that already work.

**Scope:**

- Add or update renderer routing for C7-owned routes identified by the
  inventory.
- Decide whether `team_matchup_record` remains in `TeamRecordSection.tsx` with
  a C7-specific path or moves into a new head-to-head owner.
- Preserve generic comparison rendering for ordinary `team_compare` and
  unknown comparison-shaped responses.
- Preserve generic summary rendering for non-owned summary-shaped responses.
- Preserve generic leaderboard rendering for non-playoff leaderboards.
- Add frontend tests proving owned route routing and fallback preservation.

**Files likely touched:**

- `frontend/src/components/ResultSections.tsx`
- New or existing C7 renderer files
- Frontend tests

**Acceptance criteria:**

- C7-owned routes have explicit component ownership.
- Existing non-owned comparison, summary, leaderboard, and fallback routes
  retain current paths.
- No record math, playoff parsing, or route decisions move into React.
- Full detail sections remain visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c7_head_to_head_playoff_inventory.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/api/types.ts`

---

## 3. `[x]` Build head-to-head answer layout

**Why:** Head-to-head queries should answer with the participants and record or
comparison result first, then expose supporting rows.

**Scope:**

- Render owned head-to-head rows as matchup cards with both participants,
  supplied record/sample, season/date context, home/away or filter context when
  present, and neutral identity accents.
- Support the head-to-head shapes identified by the inventory, including team
  matchup records and player/team comparison responses when metadata marks a
  head-to-head sample.
- Preserve all supplied summary/comparison/finder/detail tables below the
  designed layout.
- Handle missing participant ids, missing record fields, ties, long names,
  multi-season context, and sparse detail rows without throwing.
- Add tests for team-vs-team, player-vs-player or player-vs-team where
  supported, long names, sparse records, detail preservation, and fallback
  preservation.

**Files likely touched:**

- C7 head-to-head renderer files
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- Participants and supplied head-to-head answer are visually primary.
- Mixed-subject views stay neutral except for identity accents.
- Sparse rows degrade without inventing a winner, record, or game list.
- Detail tables remain visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c7_head_to_head_playoff_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/design-system/TeamBadge.tsx`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/components/TeamRecordSection.tsx`
- `frontend/src/components/PlayerComparisonSection.tsx`

---

## 4. `[ ]` Build playoff history and matchup layout

**Why:** Playoff history and playoff matchup results should read as postseason
history, with round/series context and records ahead of tables.

**Scope:**

- Render owned playoff summary/comparison routes such as `playoff_history` and
  `playoff_matchup_history` with team identity, round/series/season context,
  supplied records or series counts, and detail tables.
- Show playoff round filters and multi-season context when supplied.
- Keep playoff matchup views neutral for mixed teams.
- Preserve all supplied detail sections and unknown columns.
- Handle missing team ids, missing round labels, missing record fields, long
  round/series labels, and sparse rows without throwing.
- Add tests for team playoff history, playoff matchup history, round filters,
  sparse payloads, detail preservation, and generic fallback preservation.

**Files likely touched:**

- C7 playoff renderer files
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- Playoff route pages expose postseason context before detail tables.
- Mixed-team playoff views stay neutral except for identity accents.
- No series/round/record computation is added to React.
- Detail tables remain visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c7_head_to_head_playoff_inventory.md`
- `src/nbatools/commands/playoff_history.py`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/ComparisonSection.tsx`

---

## 5. `[ ]` Build playoff leaderboard treatment

**Why:** Playoff appearance and round-record leaderboards need postseason
context, not just ordinary regular-season leaderboard rows.

**Scope:**

- Add route-aware rendering for `playoff_appearances` and
  `playoff_round_record`, or extend an existing leaderboard owner with a
  clearly bounded playoff path if that is cleaner.
- Promote supplied playoff count/record fields, team identity, round labels,
  season range, and qualifier context.
- Preserve ordinary season leaderboards, occurrence leaderboards, record
  leaderboards, and unknown leaderboard-shaped behavior.
- Add tests for playoff appearances, playoff round records, long round labels,
  missing identities, sparse rows, and fallback preservation.

**Files likely touched:**

- C7 playoff leaderboard renderer files
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- Playoff leaderboards read as postseason rankings.
- Existing non-playoff leaderboard routes remain unaffected.
- No ranking, record math, or round parsing is added to React.
- Full leaderboard detail remains visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c7_head_to_head_playoff_inventory.md`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/OccurrenceLeaderboardSection.tsx`
- `src/nbatools/commands/playoff_history.py`

---

## 6. `[ ]` Polish C7 responsive detail and docs

**Why:** C7 should close implementation with head-to-head/playoff layouts
documented and safe on desktop and mobile.

**Scope:**

- Verify and tighten C7 layouts at representative desktop, tablet, and mobile
  widths.
- Ensure long team/player names, long round/series labels, missing identities,
  missing records, ties, missing dates, and sparse detail rows do not overlap
  or hide detail.
- Update `docs/operations/ui_guide.md` with C7 renderer behavior,
  neutral/scoped identity treatment, detail-table fallbacks, and edge-case
  handling.
- Add or adjust frontend tests for edge cases found during polish.
- Confirm unrelated renderers remain unaffected.

**Files likely touched:**

- C7 renderer files
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- UI docs name C7 renderers and boundaries.
- Edge cases have either test coverage or documented fallback behavior.
- Generic comparison/summary/leaderboard/fallback rendering remains available.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`

---

## 7. `[ ]` Phase C7 retrospective and C8 handoff

**Why:** Self-propagating final task. It closes head-to-head/playoff layout
work and creates the next executable Part 2 queue.

**Scope:**

- Write the Phase C7 retrospective in this file.
- Refresh `component_experience_plan.md` if C7 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c8_work_queue.md` for the full mobile pass across redesigned
  components.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C8.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c7_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c8_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c8_work_queue.md` exists with concrete PR-sized mobile-polish items.
- Active-continuation docs point to Phase C8.
- Phase C7 is explicitly closed without implying Part 2 or the polish plan is
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

When all items above are checked `[x]`, Phase C7 is complete. The draft of
`phase_c8_work_queue.md` from item 7 is the handoff artifact.
