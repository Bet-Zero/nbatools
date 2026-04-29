# Phase C1 Work Queue

> **Role:** First Track A Part 2 work queue for
> [`component_experience_plan.md`](./component_experience_plan.md) - _player
> summary layout._
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

## Phase C1 goal

Replace the generic player-summary table treatment with a purpose-built player
summary layout for queries such as `Jokic last 10` and `Embiid this season`.
The layout should use the Part 1 visual foundation: player headshot, stat
hierarchy, cards, responsive structure, and residual tables only where they are
the right secondary detail.

C1 is not complete until the player summary has a real hero/stat layout, a
game-by-game scoring sparkline backed by structured engine/API data, by-season
detail, and mobile behavior that looks intentionally designed.

Guardrails:

- Keep query parsing, filtering, and metric computation in the engine.
- Do not fetch a hidden second query from React to build the sparkline.
- Preserve generic summary rendering for team, playoff, and unknown summary
  routes until their phases redesign them.
- Keep player-subject pages visually neutral except for player imagery and
  small team badges. Do not apply single-team page theming to player summaries.

---

## 1. `[ ]` Establish the player-summary renderer boundary

**Why:** `SummarySection.tsx` currently owns every summary-shaped result.
Player summary needs a dedicated owner before C1 can redesign it without
accidentally changing team summaries, team records, or playoff summaries.

**Scope:**

- Add a dedicated player-summary renderer component.
- Route only `player_game_summary` / player-summary responses to that
  component from `ResultSections.tsx`.
- Preserve `SummarySection.tsx` as the generic summary fallback for team,
  playoff, and unknown summary routes.
- Keep current summary and by-season data visible; this item may add only
  minimal visual scaffolding needed to prove the boundary.
- Add or update frontend tests covering player-summary routing and generic
  summary fallback behavior.

**Files likely touched:**

- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/PlayerSummarySection.tsx` (new)
- `frontend/src/components/PlayerSummarySection.module.css` (new)
- `frontend/src/test/ResultSections.test.tsx`

**Acceptance criteria:**

- Player summaries have a distinct owner component.
- Team summary, team record, and playoff summary responses still render through
  the generic summary path.
- No NBA calculation, filtering, or query parsing is added to React.
- The new component uses existing Part 1 primitives where practical.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/api/types.ts`

---

## 2. `[ ]` Build the player-summary hero and stat hierarchy

**Why:** The first visible C1 improvement should make the answer feel like a
designed player summary instead of a table dump.

**Scope:**

- Use `metadata.player_context` for the hero identity and headshot.
- Promote `pts_avg`, `reb_avg`, `ast_avg`, `games`, `wins`, `losses`,
  `win_pct`, and selected shooting/efficiency fields from the summary row into
  a designed hero/stat layout.
- Keep full summary details and `by_season` available as secondary content.
- Preserve neutral player-subject theming.
- Add frontend tests for populated summary rows, missing player identity
  fallback, and no-layout-crash behavior when optional metrics are absent.

**Files likely touched:**

- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/PlayerSummarySection.module.css`
- `frontend/src/components/tableFormatting.ts` only if existing formatting
  helpers need a small reusable export
- Frontend tests

**Acceptance criteria:**

- Player headshot/name and top-line stats are the primary visual answer.
- The renderer handles missing optional fields without throwing.
- Full table detail remains reachable for data not yet promoted.
- Mobile widths stack cleanly without text overlap.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`
- `frontend/src/design-system/Stat.tsx`
- `frontend/src/design-system/StatBlock.tsx`
- `frontend/src/design-system/Avatar.tsx`

---

## 3. `[ ]` Add an exact-sample game-series section for player summaries

**Why:** The C1 sparkline and recent-game context need structured
game-by-game data for the same sample as the summary. React should render that
data, not compute or refetch it.

**Scope:**

- Add an additive structured section for player-summary sample games, named
  consistently for API consumers.
- Include at minimum `game_date`, `game_id`, opponent identity, `wl`, `minutes`,
  `pts`, `reb`, and `ast`.
- Ensure the section uses the exact filtered sample used by the summary,
  including season, season type, last-N/date filters, opponent filters, and
  grouped boolean filters where supported.
- Preserve existing CLI pretty/raw behavior unless a deliberate additive label
  is added with tests.
- Update API/query-service/engine tests for the new section.
- Update frontend TypeScript only if stronger typed helpers are introduced.

**Files likely touched:**

- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/query_service.py` only if envelope metadata or exact sample
  plumbing needs adjustment
- API/query-service/engine tests
- `frontend/src/api/types.ts` only if needed

**Acceptance criteria:**

- Player summary API responses expose the exact-sample game series.
- Existing summary and by-season sections remain stable.
- The new section is additive and machine-readable.
- Tests cover normal player summary and a filtered/last-N style sample.

**Tests to run:**

- `make test-engine`
- `make test-api`
- `make test-preflight`

**Reference docs to consult:**

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/query_service.py`

---

## 4. `[ ]` Render scoring sparkline and recent-game context

**Why:** The sparkline turns a player summary from static aggregates into a
quick read on form across the queried sample.

**Scope:**

- Render a compact scoring sparkline from the new exact-sample game-series
  section.
- Add a small recent-games strip or compact list that shows date, opponent,
  W/L, and core stats without replacing the finder layout.
- Keep chart code presentation-only: scale and render provided numbers, do not
  alter query semantics or compute new NBA metrics.
- Add frontend tests for present, missing, single-game, and empty game-series
  cases.

**Files likely touched:**

- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/PlayerSummarySection.module.css`
- A small local sparkline component if useful
- Frontend tests

**Acceptance criteria:**

- Sparkline renders only when the game-series section is present and useful.
- Missing or single-game series degrade gracefully.
- Recent-game context uses opponent identity fields when available.
- The layout remains responsive and does not hide the summary details.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_v5_component_layout_inventory.md`
- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/DataTable.tsx`

---

## 5. `[ ]` Polish player-summary responsive detail and docs

**Why:** C1 should close with the player summary feeling complete on desktop
and mobile, with docs reflecting shipped UI behavior.

**Scope:**

- Verify and tighten player-summary layout at representative desktop, tablet,
  and mobile widths.
- Ensure long player names, missing images, short samples, and dense stat labels
  do not overlap or resize the layout unexpectedly.
- Update `docs/operations/ui_guide.md` with the new player-summary renderer
  ownership and any reusable component guidance.
- Add or adjust frontend tests for edge cases found during the polish pass.

**Files likely touched:**

- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/PlayerSummarySection.module.css`
- Frontend tests
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- Player-summary layout works cleanly on mobile and desktop.
- Edge cases have either test coverage or a documented fallback.
- UI docs name the renderer and its boundary.
- Generic summary routes are still unaffected.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/architecture/design_system.md`
- `docs/planning/component_experience_plan.md`

---

## 6. `[ ]` Phase C1 retrospective and C2 handoff

**Why:** Self-propagating final task. It closes player-summary work and creates
the next executable Part 2 queue.

**Scope:**

- Write the Phase C1 retrospective in this file.
- Refresh `component_experience_plan.md` if C1 changes Part 2 ordering,
  guardrails, or data-contract assumptions.
- Draft `phase_c2_work_queue.md` for leaderboard layout work.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C2.
- Update `docs/index.md` for new active queue/planning docs.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c1_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c2_work_queue.md` (new)
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c2_work_queue.md` exists with concrete PR-sized leaderboard items.
- Active-continuation docs point to Phase C2.
- Phase C1 is explicitly closed without implying Part 2 or the polish plan is
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

When all items above are checked `[x]`, Phase C1 is complete. The draft of
`phase_c2_work_queue.md` from item 6 is the handoff artifact.
