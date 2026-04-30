# Phase C4 Work Queue

> **Role:** Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) - _player
> game finder layout._
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

## Phase C4 goal

Replace the generic table-first treatment for `player_game_finder` results
with a purpose-built list of game cards for queries such as `Curry 5+ threes`,
`Jokic under 20 points`, and player-opponent game lists. The layout should make
each matching game scannable by date, opponent, home/away, result, player
identity, and key stat values while retaining the full detail table for dense
columns.

C4 is not complete until `player_game_finder` results have a dedicated
route-scoped renderer, game-card treatment, identity/opponent context, metric
emphasis using only supplied row values, responsive mobile behavior,
documented fallbacks, and the generic finder rendering remains intact for
team game finders and unknown finder-shaped routes.

Guardrails:

- Keep filtering, boolean logic, sorting, thresholds, and row construction in
  the engine/API.
- Do not reconstruct natural-query intent or threshold expressions in React.
  React may promote values already present in finder rows.
- Route only `player_game_finder` responses to the player-game-finder
  renderer.
- Preserve `FinderSection.tsx` as the generic fallback for `game_finder`,
  count detail sections, and unknown finder-shaped routes until their later
  phases redesign them.
- Keep player-subject finder pages neutral except for player headshots and
  team/opponent badges. Do not apply result-level team theming from row data.
- Keep the full finder detail table available for columns not promoted into
  game cards.

---

## 1. `[x]` Inventory finder row shapes and renderer boundary

**Why:** `query_class: "finder"` covers player game finders, team game
finders, grouped boolean finder results, and finder detail inside count-style
results; adjacent top-game routes are leaderboard-shaped today. C4 needs
verified row-shape guidance before routing only player game finders into a new
renderer.

**Scope:**

- Inventory representative `finder` rows for `player_game_finder`,
  `game_finder`, grouped boolean finder output, count results that include
  finder detail, and adjacent top-game routes that are currently
  leaderboard-shaped rather than finder-shaped.
- Identify stable player identity fields, team/opponent fields, date/result
  fields, stat candidates, rank/sort fields, and columns that should remain
  detail-only.
- Write the inventory as a planning artifact for C4 implementation.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c4_finder_inventory.md` (new)
- `docs/planning/phase_c4_work_queue.md`

**Acceptance criteria:**

- Inventory names representative routes and section fields.
- Inventory distinguishes `player_game_finder` fields from generic
  finder-shaped routes that must keep fallback rendering.
- Residual API/result-contract gaps are documented without blocking frontend
  work that can use existing rows.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/FinderSection.tsx`
- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/game_finder.py`
- `src/nbatools/commands/structured_results.py`

---

## 2. `[x]` Establish the player-game-finder renderer boundary

**Why:** Player game finder needs a dedicated owner without accidentally
redesigning team finders, count detail, or future finder-shaped payloads.

**Scope:**

- Add a dedicated player-game-finder renderer component.
- Route only `player_game_finder` responses to that component from
  `ResultSections.tsx`.
- Preserve `FinderSection.tsx` as the generic finder fallback for team,
  count-detail, and unknown finder routes.
- Keep current finder detail visible; this item may add only minimal visual
  scaffolding needed to prove the boundary.
- Add frontend tests for player-game-finder routing and generic finder
  fallback behavior.

**Files likely touched:**

- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/PlayerGameFinderSection.tsx` (new)
- `frontend/src/components/PlayerGameFinderSection.module.css` (new)
- `frontend/src/test/ResultSections.test.tsx`

**Acceptance criteria:**

- `player_game_finder` results have a distinct owner component.
- `game_finder`, count detail sections, and unknown finder-shaped responses
  still render through the generic finder/fallback path.
- No NBA calculation, filtering, threshold parsing, or query routing is added
  to React.
- The new component uses existing Part 1 primitives where practical.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c4_finder_inventory.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/FinderSection.tsx`
- `frontend/src/api/types.ts`

---

## 3. `[x]` Build player game-card list layout

**Why:** Finder answers are event lists. The primary view should read as
matching games rather than rows in a dense table.

**Scope:**

- Render player finder rows as game cards with player identity, rank/date,
  opponent, home/away context, W/L result, and top-line stat values.
- Use player headshots when rows contain stable player ids; fall back to
  initials/text for missing ids.
- Use team/opponent badges when row fields provide team/opponent identity.
- Keep the full finder detail table available below the cards.
- Add tests for populated player rows, missing ids/images, missing opponent
  ids, sparse rows, and detail table preservation.

**Files likely touched:**

- `frontend/src/components/PlayerGameFinderSection.tsx`
- `frontend/src/components/PlayerGameFinderSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Matching games are visually primary and scannable as cards.
- Missing identity fields degrade to initials/text/badges without throwing.
- Full finder detail remains reachable for data not promoted into cards.
- Mobile widths stack cleanly without text overlap.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c4_finder_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`
- `frontend/src/design-system/StatBlock.tsx`

---

## 4. `[x]` Add stat emphasis, context, and sparse-row handling

**Why:** Game cards should quickly answer why each game matched while staying
honest about what the API actually supplied.

**Scope:**

- Promote the best available supplied stat values into each game card using
  conservative field priority from the inventory.
- Surface secondary context such as minutes, plus-minus, season, season type,
  clutch/period fields, and rank when available.
- Avoid reconstructing threshold copy when no structured filter summary exists.
- Preserve neutral player-subject styling and do not infer team ownership from
  row teams/opponents.
- Add tests for long player/opponent names, long stat labels, missing promoted
  stats, W/L context, home/away context, and sparse rows.

**Files likely touched:**

- `frontend/src/components/PlayerGameFinderSection.tsx`
- `frontend/src/components/PlayerGameFinderSection.module.css`
- Frontend tests

**Acceptance criteria:**

- Important supplied stat values are easier to scan than in the generic table.
- Context metadata does not overwhelm the date/opponent/result hierarchy.
- Sparse or unusual player finder rows still render and expose detail.
- No new filtering, sorting, or threshold interpretation is added to React.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_c4_finder_inventory.md`
- `frontend/src/components/tableFormatting.ts`
- `frontend/src/components/DataTable.tsx`

---

## 5. `[x]` Polish finder responsive detail and docs

**Why:** C4 should close implementation with player game finders feeling
complete on desktop and mobile, with docs accurately describing boundaries and
fallbacks.

**Scope:**

- Verify and tighten player-game-finder layout at representative desktop,
  tablet, and mobile widths.
- Ensure long player names, long opponent/team labels, missing identities,
  missing results, and sparse rows do not overlap or hide detail.
- Update `docs/operations/ui_guide.md` with player-game-finder renderer
  behavior, neutral player-subject treatment, detail-table fallback, and
  edge-case handling.
- Add or adjust frontend tests for edge cases found during polish.
- Confirm generic finder fallback rendering remains unaffected.

**Files likely touched:**

- `frontend/src/components/PlayerGameFinderSection.tsx`
- `frontend/src/components/PlayerGameFinderSection.module.css`
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- UI docs name the player-game-finder renderer and its boundary.
- Edge cases have either test coverage or documented fallback behavior.
- Generic finder routes still work through `FinderSection.tsx`.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/FinderSection.tsx`

---

## 6. `[x]` Phase C4 retrospective and C5 handoff

**Why:** Self-propagating final task. It closes player-game-finder work and
creates the next executable Part 2 queue.

**Scope:**

- Write the Phase C4 retrospective in this file.
- Refresh `component_experience_plan.md` if C4 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c5_work_queue.md` for team summary, team record, and split
  layout work.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C5.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c4_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c5_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c5_work_queue.md` exists with concrete PR-sized team/split layout
  items.
- Active-continuation docs point to Phase C5.
- Phase C4 is explicitly closed without implying Part 2 or the polish plan is
  complete.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- This file
- `docs/planning/component_experience_plan.md`
- `docs/planning/product_polish_master_plan.md`

---

## Phase C4 retrospective

**Status:** Phase C4 is closed. Player-game-finder layout work is complete,
but Track A Part 2 and the overall product polish plan remain in progress.

**What went well:**

- The finder inventory clarified the route boundary before implementation:
  only `player_game_finder` moved to the dedicated layout, while
  `game_finder`, count detail, top-game leaderboards, and unknown
  finder-shaped routes stayed on existing renderers.
- The renderer shipped incrementally: first ownership and fallback tests, then
  game cards, then broader stat/context treatment, and finally docs/fallback
  polish.
- Existing primitives carried the experience. `Avatar`, `TeamBadge`, `Badge`,
  `Card`, `SectionHeader`, `StatBlock`, and `DataTable` covered the identity,
  result, stat, and detail-table surfaces without introducing new primitives.
- Tests now cover route dispatch, generic finder fallback, count-detail
  fallback, populated player game cards, missing player ids, missing opponent
  context, missing W/L/results, long labels, custom numeric stat fallback, and
  full detail-table preservation.

**What was harder:**

- Finder responses do not expose structured threshold/filter copy, primary
  matched stat, sort direction, limit, or truncation state. The UI therefore
  promotes supplied fields conservatively and avoids explaining why a game
  matched beyond the values in the row.
- `player_game_finder` currently loads team and opponent ids but does not emit
  them in `output_cols`, so team/opponent badges often use abbreviation/text
  fallbacks rather than logos.
- Single-game top routes such as `top_player_games` are leaderboard-shaped
  today. They may eventually want game-card treatment, but C4 left them on the
  leaderboard path to keep the boundary honest.

**Residuals carried forward:**

- A future engine/API improvement could emit `team_id`, `opponent_team_id`,
  primary stat/filter metadata, sort direction, and truncation metadata for
  finder results.
- Team game finders still need a team-specific event-list design in a later
  team/head-to-head phase if they remain a supported primary surface.
- Team summary, team record, split, streak, occurrence/count, head-to-head, and
  playoff layouts still need their Part 2 designs.

**Immediate handoff:** Continue Track A Part 2 with Phase C5, using
[`phase_c5_work_queue.md`](./phase_c5_work_queue.md).

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase C4 is complete. The draft of
`phase_c5_work_queue.md` from item 6 is the handoff artifact.
