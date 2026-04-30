# Phase C5 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) - _team
> summary, team record, and split layouts._
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

## Phase C5 goal

Replace generic table-first treatment for the team-context layouts that are
closely related in shape: team summaries, team records, and split summaries.
The phase should make team identity, record/sample context, and split buckets
scannable while preserving detail tables and keeping player-summary,
player-comparison, player-game-finder, playoff, and unknown fallback boundaries
intact.

C5 is not complete until team summaries have a team-specific hero layout, team
record/matchup-record results have a record-first treatment, split summaries
have designed bucket comparison cards, responsive mobile behavior is covered,
docs describe the renderer boundaries and fallbacks, and generic summary/split
fallbacks remain available for routes not owned by C5.

Guardrails:

- Keep aggregation, filtering, split construction, record computation, and
  route selection in the engine/API.
- Do not calculate new team metrics or infer unavailable advanced metrics in
  React.
- Use scoped team theming only when metadata indicates a safe single-team
  context; mixed team or matchup contexts should use identity accents rather
  than full-surface team-color splits.
- Keep full detail tables visible for columns not promoted into designed
  layouts.
- Preserve existing `PlayerSummarySection`, `PlayerComparisonSection`,
  `PlayerGameFinderSection`, leaderboard, finder, streak, playoff, and generic
  fallback behavior.

---

## 1. `[ ]` Inventory team summary, record, and split row shapes

**Why:** `query_class: "summary"` and `query_class: "split_summary"` cover
multiple routes. C5 needs verified row-shape guidance before assigning
team-specific renderer ownership.

**Scope:**

- Inventory representative rows and metadata for `game_summary`, `team_record`,
  `team_matchup_record`, `team_split_summary`, `player_split_summary`, and
  summary/split-shaped playoff or unknown routes that should keep fallback
  rendering.
- Identify stable team identity fields, opponent fields, record fields, split
  bucket labels, stat candidates, scoped-team-theme inputs, and detail-only
  columns.
- Write the inventory as a planning artifact for C5 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c5_team_split_inventory.md` (new)
- `docs/planning/phase_c5_work_queue.md`

**Acceptance criteria:**

- Inventory names representative routes and section fields.
- Inventory distinguishes C5-owned team/split routes from routes that must keep
  current fallbacks.
- Residual API/result-contract gaps are documented without blocking frontend
  work that can use existing rows.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/SplitSummarySection.tsx`
- `src/nbatools/commands/game_summary.py`
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/team_split_summary.py`
- `src/nbatools/commands/player_split_summary.py`

---

## 2. `[ ]` Establish team-summary and team-record renderer boundaries

**Why:** Team-specific layouts need dedicated owners without leaking into
player summaries, playoff summaries, or unknown summary-shaped routes.

**Scope:**

- Add dedicated renderer ownership for team summary and team record routes
  identified by the inventory.
- Route only the approved C5 summary routes from `ResultSections.tsx`.
- Preserve `PlayerSummarySection.tsx` for `player_game_summary`.
- Preserve `SummarySection.tsx` for playoff and unknown summary-shaped routes
  not owned by C5.
- Keep existing summary detail visible; this item may add only minimal visual
  scaffolding needed to prove the boundary.
- Add frontend tests for owned team summary/record routing and generic summary
  fallback behavior.

**Files likely touched:**

- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/TeamSummarySection.tsx` (new or extended owner)
- `frontend/src/components/TeamSummarySection.module.css` (new)
- Frontend tests

**Acceptance criteria:**

- Team summary/record routes have a distinct owner component.
- Player, playoff, and unknown summary routes retain their current paths.
- No team metric computation, filtering, or route decisions move into React.
- Full summary detail remains visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c5_team_split_inventory.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/api/types.ts`

---

## 3. `[ ]` Build team summary hero layout

**Why:** Team summaries should first read as the team, record, and headline
stats instead of as anonymous summary rows.

**Scope:**

- Render team summary rows with team identity, logo/badge, scoped team accent
  when safe, record/sample context, and supplied headline stats.
- Promote only fields already present in the response, such as wins/losses,
  win percentage, points, rebounds, assists, shooting, plus-minus, games, and
  season/date context.
- Keep full summary and by-season/detail sections visible.
- Add tests for populated team summaries, missing team ids/logos, missing
  optional stats, long team names, and generic fallback preservation.

**Files likely touched:**

- `frontend/src/components/TeamSummarySection.tsx`
- `frontend/src/components/TeamSummarySection.module.css`
- Frontend tests

**Acceptance criteria:**

- Team identity and record/sample context are visually primary.
- Missing identity/stat fields degrade without throwing.
- Scoped team theming is applied only in safe single-team contexts.
- Detail tables remain visible.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c5_team_split_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/design-system/TeamBadge.tsx`
- `frontend/src/design-system/StatBlock.tsx`

---

## 4. `[ ]` Build team record and matchup record treatment

**Why:** Record queries should answer with the record first, then expose the
supporting stat table.

**Scope:**

- Render team record and matchup-record results with a record-first callout,
  team/opponent identity accents, sample-size context, W/L percentage, and
  supplied secondary stats.
- Keep mixed-team/matchup views neutral except for identity badges and restrained
  accents.
- Preserve full summary/comparison detail for all unpromoted columns.
- Add tests for single-team records, opponent records, matchup records, missing
  opponent identity, and detail table preservation.

**Files likely touched:**

- Team summary/record renderer files
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- Record answers are scannable without reading the table first.
- Matchup/multi-team views do not imply full-surface ownership by one team.
- Sparse rows degrade to text/detail tables without throwing.
- No record math is added to React beyond displaying supplied values.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c5_team_split_inventory.md`
- `src/nbatools/commands/team_record.py`
- `frontend/src/components/ComparisonSection.tsx`
- `frontend/src/components/DataTable.tsx`

---

## 5. `[ ]` Redesign split summary layout

**Why:** Split summaries are comparisons between buckets. They should render as
bucket cards before dense split tables.

**Scope:**

- Add or redesign split summary rendering for the owned split routes identified
  by the inventory.
- Render bucket cards for common split dimensions such as home/away,
  wins/losses, and other supplied split labels.
- Promote supplied record/sample/stat values without computing new metrics.
- Preserve full summary and split-comparison detail tables.
- Add tests for team split summaries, player split summaries if they remain in
  scope, long bucket labels, missing optional stats, and generic fallback
  behavior for unknown split-shaped routes.

**Files likely touched:**

- `frontend/src/components/SplitSummarySection.tsx`
- `frontend/src/components/SplitSummarySection.module.css`
- `frontend/src/components/ResultSections.tsx`
- Frontend tests

**Acceptance criteria:**

- Split buckets are visually primary and mobile readable.
- Bucket labels are user-readable without changing data semantics.
- Detail tables remain visible.
- Unknown split-shaped responses keep a safe fallback.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c5_team_split_inventory.md`
- `frontend/src/components/SplitSummarySection.tsx`
- `frontend/src/components/tableFormatting.ts`

---

## 6. `[ ]` Polish team/split responsive detail and docs

**Why:** C5 should close implementation with team and split layouts documented
and safe on desktop and mobile.

**Scope:**

- Verify and tighten team summary, team record, and split layouts at
  representative desktop, tablet, and mobile widths.
- Ensure long team names, long opponent names, long bucket labels, missing
  identities, missing records, and sparse rows do not overlap or hide detail.
- Update `docs/operations/ui_guide.md` with renderer behavior, scoped/neutral
  team treatment, detail-table fallbacks, and edge-case handling.
- Add or adjust frontend tests for edge cases found during polish.
- Confirm unrelated renderers remain unaffected.

**Files likely touched:**

- Team/split renderer files
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- UI docs name C5 renderers and boundaries.
- Edge cases have either test coverage or documented fallback behavior.
- Generic summary/split fallback rendering remains available.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`

---

## 7. `[ ]` Phase C5 retrospective and C6 handoff

**Why:** Self-propagating final task. It closes team/split layout work and
creates the next executable Part 2 queue.

**Scope:**

- Write the Phase C5 retrospective in this file.
- Refresh `component_experience_plan.md` if C5 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c6_work_queue.md` for streak and occurrence layouts.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C6.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c5_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c6_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c6_work_queue.md` exists with concrete PR-sized streak/occurrence
  layout items.
- Active-continuation docs point to Phase C6.
- Phase C5 is explicitly closed without implying Part 2 or the polish plan is
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

When all items above are checked `[x]`, Phase C5 is complete. The draft of
`phase_c6_work_queue.md` from item 7 is the handoff artifact.
