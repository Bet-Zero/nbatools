# Phase C8 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) -
> _full mobile pass across redesigned result components._
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

## Phase C8 goal

Run a dedicated mobile-quality pass across every redesigned Part 2 result
surface. Earlier phases added route-specific layouts with component-level
responsive rules; C8 verifies the whole UI at phone/tablet/desktop widths and
fixes the cross-component rough edges that only show up after the full set of
layouts exists together.

C8 is not complete until the shell, result envelope, redesigned summaries,
comparisons, finders, leaderboards, streak/count/occurrence, head-to-head, and
playoff surfaces have explicit mobile verification, dense detail tables remain
contained, and docs record the mobile behavior and remaining Part 3 work.

Guardrails:

- Keep business logic, parsing, ranking, record math, playoff interpretation,
  and filtering out of React.
- Do not hide full detail tables to make mobile look cleaner; detail may scroll
  horizontally inside its own wrapper, but it must remain visible.
- Preserve desktop behavior while tightening mobile. Avoid desktop regressions
  from mobile-only CSS changes.
- Keep mixed-player, mixed-team, matchup, playoff, and league-wide surfaces
  neutral except for identity accents.
- Prefer focused component CSS/tests over broad visual rewrites.

---

## 1. `[x]` Inventory mobile risks and verification fixtures

**Why:** A whole-app mobile pass needs a concrete matrix of routes, edge cases,
and widths before making polish changes.

**Scope:**

- Inventory representative mobile verification fixtures for every redesigned
  result family from C1-C7.
- Include at least phone, tablet, and desktop widths, plus long names, sparse
  rows, missing identities, dense tables, raw JSON, and dev tools.
- Identify which fixtures can be covered by automated tests and which require
  manual/browser visual checks.
- Write the inventory as a planning artifact for C8 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c8_mobile_inventory.md` (new)
- `docs/planning/phase_c8_work_queue.md`

**Acceptance criteria:**

- Inventory names the component families, representative route/query-class
  fixtures, widths, and risk areas to verify.
- Inventory separates mobile layout risks from data/engine concerns.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`

---

## 2. `[x]` Polish shell, query, envelope, and side panels on mobile

**Why:** The result components sit inside the app shell. Mobile polish is not
credible if query controls, freshness, result metadata, history, saved queries,
or dev tools force horizontal overflow.

**Scope:**

- Verify and tighten mobile behavior for `AppShell`, query bar/sample queries,
  freshness status, result envelope metadata/actions, query history, saved
  queries, dev tools, loading, no-result, and error states.
- Ensure long query text, route labels, context chips, notices, saved-query
  labels, and structured kwargs stay inside their regions.
- Preserve desktop/two-panel behavior.
- Add or adjust focused frontend tests for mobile-sensitive state/markup where
  useful.

**Files likely touched:**

- App shell/envelope/query/history/dev-tools components and CSS
- Frontend tests
- `docs/planning/phase_c8_work_queue.md`

**Acceptance criteria:**

- Shell and envelope controls wrap or stack cleanly on phone/tablet widths.
- Side-panel content does not force the main result region wider.
- Loading, empty, no-result, and error states stay readable on mobile.
- Desktop shell behavior remains intact.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/ResultEnvelope.tsx`

---

## 3. `[x]` Polish summary, record, and split result cards on mobile

**Why:** Summary-style cards are the largest hero surfaces and are most likely
to expose long-name, stat-grid, and identity-stacking issues.

**Scope:**

- Verify and tighten mobile behavior for player summaries, team summaries,
  team records, split summaries, and their detail tables.
- Cover long player/team names, missing ids/logos, sparse stats, zero games,
  one-row game logs, long split labels, and dense by-season rows.
- Preserve scoped team theming only for safe single-team contexts.
- Add or adjust frontend tests for edge cases found during polish.

**Files likely touched:**

- `PlayerSummarySection`, `TeamSummarySection`, `TeamRecordSection`,
  `SplitSummaryCardsSection`, shared table/detail CSS, and tests
- `docs/planning/phase_c8_work_queue.md`

**Acceptance criteria:**

- Hero identity, stats, sparkline/recent-game strips, records, and split cards
  stack cleanly on phone widths.
- Detail tables remain visible and contained.
- Unknown summary/split fallbacks still render.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/TeamSummarySection.tsx`
- `frontend/src/components/TeamRecordSection.tsx`
- `frontend/src/components/SplitSummaryCardsSection.tsx`

---

## 4. `[x]` Polish comparison, head-to-head, and playoff matchup mobile layouts

**Why:** Multi-entity layouts have the highest risk of overlap, accidental
winner implication, and cramped detail when stacked on small screens.

**Scope:**

- Verify and tighten mobile behavior for player comparisons, generic
  comparisons, head-to-head results, playoff history summaries, playoff
  matchups, and playoff leaderboards.
- Cover long player/team names, ties, missing identities, missing records,
  long round labels, sparse playoff rows, and wide dynamic comparison columns.
- Preserve neutral mixed-subject treatment and full detail tables.
- Add or adjust frontend tests for edge cases found during polish.

**Files likely touched:**

- `PlayerComparisonSection`, `HeadToHeadSection`, `PlayoffSection`,
  `ComparisonSection`, detail/table CSS, and tests
- `docs/planning/phase_c8_work_queue.md`

**Acceptance criteria:**

- Multi-entity cards and rankings stack without overlap on phone widths.
- Ties and sparse records remain neutral and do not imply winners.
- Playoff round/series labels wrap without hiding the table detail.
- Generic comparison fallback remains available.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/HeadToHeadSection.tsx`
- `frontend/src/components/PlayoffSection.tsx`

---

## 5. `[ ]` Polish list, ranking, finder, streak, count, and occurrence mobile layouts

**Why:** Repeated card and ranking lists need stable mobile dimensions, readable
metric blocks, and contained detail when many rows render.

**Scope:**

- Verify and tighten mobile behavior for generic leaderboards, occurrence
  leaderboards, player game finders, generic finders, streaks, and counts.
- Cover long entity names, long metric/event labels, missing identities, missing
  streak spans, zero counts, sparse finder rows, and dense detail tables.
- Preserve ordinary leaderboard/finder/fallback behavior.
- Add or adjust frontend tests for edge cases found during polish.

**Files likely touched:**

- `LeaderboardSection`, `OccurrenceLeaderboardSection`,
  `PlayerGameFinderSection`, `FinderSection`, `StreakSection`, `CountSection`,
  shared table/detail CSS, and tests
- `docs/planning/phase_c8_work_queue.md`

**Acceptance criteria:**

- Ranking and finder rows stack metric/context regions cleanly on phone widths.
- Streak/count answer cards stay readable with sparse or zero-valued rows.
- Full detail tables remain visible.
- Generic leaderboard/finder/fallback routes remain intact.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/OccurrenceLeaderboardSection.tsx`
- `frontend/src/components/PlayerGameFinderSection.tsx`
- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/CountSection.tsx`

---

## 6. `[ ]` Polish tables, raw JSON, copy actions, and mobile docs

**Why:** Dense tables and utility panels are the common fallback for every
result. They must stay usable after all card layouts are polished.

**Scope:**

- Verify and tighten mobile behavior for `DataTable`, raw JSON, copy buttons,
  share links, structured dev-tool kwargs, and detail sections across result
  families.
- Ensure wide tables scroll inside their wrappers and do not widen the shell.
- Update `docs/operations/ui_guide.md` with C8 mobile verification guidance,
  known responsive boundaries, and remaining Part 3 polish residuals.
- Add or adjust frontend tests for edge cases found during polish.

**Files likely touched:**

- `DataTable`, `RawJsonToggle`, copy/dev-tool components, shared CSS, tests
- `docs/operations/ui_guide.md`
- `docs/planning/phase_c8_work_queue.md`

**Acceptance criteria:**

- Dense detail tables, raw JSON, and dev-tool JSON stay contained on phone
  widths.
- Copy/share actions remain accessible and do not overlap text.
- UI docs describe mobile behavior and remaining residuals.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/components/RawJsonToggle.tsx`
- `frontend/src/components/CopyButton.tsx`
- `frontend/src/components/DevTools.tsx`

---

## 7. `[ ]` Phase C8 retrospective and C9 handoff

**Why:** Self-propagating final task. It closes the dedicated mobile pass and
creates the next executable Part 2 closing queue.

**Scope:**

- Write the Phase C8 retrospective in this file.
- Refresh `component_experience_plan.md` if C8 changes Part 2 status,
  guardrails, or residuals.
- Draft `phase_c9_work_queue.md` for the Part 2 retrospective and Part 3
  handoff.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C9.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c8_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c9_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c9_work_queue.md` exists with concrete PR-sized Part 2 closure items.
- Active-continuation docs point to Phase C9.
- Phase C8 is explicitly closed without implying Part 2 or the polish plan is
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

When all items above are checked `[x]`, Phase C8 is complete. The draft of
`phase_c9_work_queue.md` from item 7 is the handoff artifact.
