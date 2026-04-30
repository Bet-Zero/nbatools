# Phase C6 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) - _streak
> and occurrence layouts._
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

## Phase C6 goal

Replace table-first treatment for event-over-time query families: streak
results and occurrence/count results. Streak results should make the streak
length, entity, condition, date span, active status, and supporting stats
scannable before the dense detail table. Occurrence and count results should
make the event/count answer prominent while preserving any underlying finder or
leaderboard detail.

C6 is not complete until player/team streaks have designed layouts, count
results have a dedicated answer-first renderer, occurrence leaderboards have
route-aware event-count treatment, responsive mobile behavior is covered, docs
describe renderer boundaries and fallbacks, and unrelated leaderboard/finder
fallbacks remain available.

Guardrails:

- Keep streak extraction, occurrence detection, threshold parsing, counting,
  ranking, and filtering in the engine/API.
- Do not compute streak length, occurrence counts, leader ordering, or event
  qualification in React.
- Use identity imagery and scoped team theming only when metadata or row shape
  identifies a safe single-entity context. League-wide occurrence leaderboards
  stay neutral except for row identity accents.
- Preserve full detail tables for columns not promoted into designed layouts.
- Keep existing player summary, leaderboard, comparison, finder, team/split,
  playoff, and generic fallback behavior intact.

---

## 1. `[x]` Inventory streak, count, and occurrence row shapes

**Why:** C6 spans multiple query classes and routes. The queue needs verified
row-shape guidance before assigning renderer ownership.

**Scope:**

- Inventory representative rows and metadata for `player_streak_finder`,
  `team_streak_finder`, finder-derived `query_class: "count"` results,
  `player_occurrence_leaders`, `team_occurrence_leaders`, and occurrence count
  variants that route through occurrence leaderboards.
- Identify stable entity fields, streak length/date fields, active-status
  fields, condition/event labels, count fields, ranked occurrence metrics,
  finder-detail sections, identity inputs, and detail-only columns.
- Distinguish C6-owned routes from leaderboard, finder, playoff, and unknown
  fallback routes that must keep current behavior.
- Write the inventory as a planning artifact for C6 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c6_streak_occurrence_inventory.md` (new)
- `docs/planning/phase_c6_work_queue.md`

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
- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/FinderSection.tsx`
- `src/nbatools/commands/player_streak_finder.py`
- `src/nbatools/commands/team_streak_finder.py`
- `src/nbatools/commands/player_occurrence_leaders.py`
- `src/nbatools/commands/team_occurrence_leaders.py`
- `src/nbatools/commands/structured_results.py`

---

## 2. `[x]` Establish streak and occurrence renderer boundaries

**Why:** Streaks, occurrence leaderboards, and count answers need dedicated
owners without hijacking generic leaderboard/finder/count-shaped fallbacks.

**Scope:**

- Add or update renderer routing for C6-owned streak and occurrence/count
  routes identified by the inventory.
- Preserve `LeaderboardSection.tsx` for ordinary season leaders, team leaders,
  top-game leaderboards, and unknown leaderboard-shaped responses.
- Preserve `FinderSection.tsx` and existing player-game finder cards for finder
  routes not owned by count rendering.
- Preserve generic fallback rendering for unknown query classes and empty/sparse
  section combinations.
- Add frontend tests proving owned route routing and fallback preservation.

**Files likely touched:**

- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/CountSection.tsx` (new)
- `frontend/src/components/OccurrenceLeaderboardSection.tsx` (new or deferred
  owner depending on inventory)
- Frontend tests

**Acceptance criteria:**

- C6-owned routes have explicit component ownership.
- Existing non-occurrence leaderboard and finder routes retain current paths.
- No event qualification, count math, or route decisions move into React.
- Full detail sections remain visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c6_streak_occurrence_inventory.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/api/types.ts`

---

## 3. `[x]` Build player and team streak answer layout

**Why:** Streak queries should answer with the streak length and span first,
then expose the supporting rows.

**Scope:**

- Render streak rows as designed streak cards with entity identity, streak
  length, condition/event label, start/end dates, active status when supplied,
  sample context, and supplied secondary stats.
- Support both player and team streak routes from existing response fields.
- Use a compact span/pill visualization only from supplied streak rows and date
  fields; do not reconstruct per-game streak events in React.
- Preserve the full streak detail table for all columns.
- Add tests for player streaks, team streaks, active/inactive values when
  supplied, missing identity, missing condition labels, long names/conditions,
  and detail table preservation.

**Files likely touched:**

- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/StreakSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Streak length and date span are visually primary.
- Player/team identity and condition context are readable at desktop and mobile
  widths.
- Sparse streak rows degrade without throwing or inventing metrics.
- Detail tables remain visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c6_streak_occurrence_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`
- `frontend/src/design-system/StatBlock.tsx`

---

## 4. `[x]` Build count answer layout

**Why:** Count queries should read as a direct answer rather than a generic
section label followed by a one-row table.

**Scope:**

- Add a dedicated renderer for `query_class: "count"` results.
- Render the supplied count value as the hero answer with available query,
  route, entity, season/date, event, and filter context.
- Preserve any underlying finder/detail sections, such as matching games, below
  the count answer.
- Handle zero counts, missing detail rows, long event labels, and missing
  identity without throwing.
- Add tests for player count, team count, distinct count, zero count, finder
  detail preservation, and generic fallback preservation where applicable.

**Files likely touched:**

- `frontend/src/components/CountSection.tsx` (new)
- `frontend/src/components/CountSection.module.css` (new)
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- The count value is visually primary.
- Detail sections remain visible and table-based where appropriate.
- No count or event qualification is computed in React.
- Sparse count payloads still render a readable answer or safe fallback.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c6_streak_occurrence_inventory.md`
- `src/nbatools/commands/structured_results.py`
- `frontend/src/components/FinderSection.tsx`
- `frontend/src/components/DataTable.tsx`

---

## 5. `[ ]` Build occurrence leaderboard treatment

**Why:** Occurrence leaderboards are leaderboards by event count, not generic
stat leaders. The event and count should be explicit while preserving existing
ranked-row behavior for ordinary leaderboards.

**Scope:**

- Add route-aware rendering for `player_occurrence_leaders` and
  `team_occurrence_leaders`, or extend `LeaderboardSection.tsx` with a clearly
  bounded occurrence path if that is simpler and cleaner.
- Promote supplied occurrence-count/event fields, entity identity, games played,
  season/date filters, and compound-condition labels.
- Keep league-wide occurrence leaderboards neutral except for identity accents.
- Preserve existing ordinary leaderboard, top-game leaderboard, record
  leaderboard, and unknown leaderboard-shaped behavior.
- Add tests for player occurrence leaderboards, team occurrence leaderboards,
  compound occurrence labels, missing identities, long event labels, and
  fallback preservation.

**Files likely touched:**

- `frontend/src/components/OccurrenceLeaderboardSection.tsx` (new) or
  `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- Occurrence-count leaderboards read as event-count rankings.
- Existing leaderboard routes remain unaffected.
- No ranking, threshold qualification, or event parsing is added to React.
- Full leaderboard detail remains visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c6_streak_occurrence_inventory.md`
- `frontend/src/components/LeaderboardSection.tsx`
- `src/nbatools/commands/player_occurrence_leaders.py`
- `src/nbatools/commands/team_occurrence_leaders.py`

---

## 6. `[ ]` Polish streak/occurrence responsive detail and docs

**Why:** C6 should close implementation with event-over-time layouts documented
and safe on desktop and mobile.

**Scope:**

- Verify and tighten streak, count, and occurrence layouts at representative
  desktop, tablet, and mobile widths.
- Ensure long player/team names, long condition/event labels, zero counts,
  missing identities, missing dates, missing streak lengths, and sparse detail
  rows do not overlap or hide detail.
- Update `docs/operations/ui_guide.md` with renderer behavior, scoped/neutral
  identity treatment, detail-table fallbacks, and edge-case handling.
- Add or adjust frontend tests for edge cases found during polish.
- Confirm unrelated renderers remain unaffected.

**Files likely touched:**

- Streak/count/occurrence renderer files
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- UI docs name C6 renderers and boundaries.
- Edge cases have either test coverage or documented fallback behavior.
- Generic leaderboard/finder/fallback rendering remains available.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`

---

## 7. `[ ]` Phase C6 retrospective and C7 handoff

**Why:** Self-propagating final task. It closes streak/occurrence layout work
and creates the next executable Part 2 queue.

**Scope:**

- Write the Phase C6 retrospective in this file.
- Refresh `component_experience_plan.md` if C6 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c7_work_queue.md` for head-to-head and playoff layouts.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C7.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c6_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c7_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c7_work_queue.md` exists with concrete PR-sized head-to-head/playoff
  layout items.
- Active-continuation docs point to Phase C7.
- Phase C6 is explicitly closed without implying Part 2 or the polish plan is
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

When all items above are checked `[x]`, Phase C6 is complete. The draft of
`phase_c7_work_queue.md` from item 7 is the handoff artifact.
