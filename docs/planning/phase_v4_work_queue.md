# Phase V4 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase V4 of
> [`visual_foundation_plan.md`](./visual_foundation_plan.md) - _Player imagery
> and team theming._
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

## Phase V4 goal

Player and team identity should feel native to the product shell. Player
headshots should render when a stable player id is available and fall back to
the existing initials treatment when not. Team logos should render when a
stable team id or abbreviation is available and fall back to the existing badge
treatment when not. Scoped team colors should enhance single-team contexts
without replacing the global action language or overwhelming multi-team views.

The app remains a presentation layer. Identity helpers may resolve display
assets and scoped CSS variables from structured identity fields, but query
parsing, NBA computation, filtering, and route semantics stay in the engine/API.

---

## 1. `[ ]` Inventory identity data, target surfaces, and fallback semantics

**Why:** Imagery and team theming need a precise contract before code starts
threading ids and assets through result renderers.

**Scope:**

- Inventory existing player/team identity fields in raw data, processed data,
  structured result rows, result metadata, and frontend API types.
- Inventory current `Avatar` and `TeamBadge` call sites in result metadata,
  data tables, and any shell/empty-state surfaces where identity may appear.
- Define target UI locations for player headshots, team logos, and scoped team
  colors.
- Define fallback semantics for missing ids, missing images, historical team
  names, opponent teams, multi-player comparisons, and multi-team leaderboards.
- Create `docs/planning/phase_v4_identity_inventory.md`.
- Do not change runtime behavior in this item.

**Files likely touched:**

- `docs/planning/phase_v4_identity_inventory.md` (new)
- `docs/planning/phase_v4_work_queue.md` - check this item when complete
- `docs/index.md` - add the new inventory doc

**Acceptance criteria:**

- Inventory names the available identity fields and the gaps that require
  API/result-contract work.
- Every target UI location has an owner path and a fallback rule.
- Team-color rules explicitly distinguish single-team context from multi-team
  context.
- Behavior boundaries are explicit: no query/API semantics move into frontend
  identity helpers.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/reference/data_catalog.md`
- `docs/reference/result_contracts.md`
- `frontend/src/api/types.ts`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`

---

## 2. `[ ]` Add frontend identity helper module and tests

**Why:** Asset URL construction, team-color lookup, and image-unavailable
fallbacks should be centralized instead of repeated in table and envelope
renderers.

**Scope:**

- Add a presentation-only identity helper under `frontend/src/` for player and
  team display identity.
- Resolve player headshot URLs only from stable player ids.
- Resolve team logo URLs and team colors from stable team ids and/or
  abbreviations per the Phase V4 inventory.
- Expose helpers for scoped team CSS variables without applying them globally.
- Keep all helpers deterministic and data-free except for the existing
  `team-colors.json` map.
- Add focused frontend unit tests for URL generation, color lookup, unknown
  teams, and missing ids.

**Files likely touched:**

- `frontend/src/lib/identity.ts` or equivalent helper path
- `frontend/src/lib/identity.test.ts`
- `frontend/src/styles/team-colors.json` only if the inventory finds missing
  active-team entries
- `docs/planning/phase_v4_work_queue.md` - check this item when complete

**Acceptance criteria:**

- Helper APIs are typed and presentation-only.
- Missing ids and unknown teams return null/fallback values, not broken asset
  strings.
- Team color CSS variables are scoped values that feature components can opt
  into.
- Frontend tests and build pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v4_identity_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/styles/team-colors.json`

---

## 3. `[ ]` Enrich API/front-end identity metadata contracts

**Why:** The UI cannot reliably render imagery from display names alone. The
API response should expose identity fields where the engine already knows them.

**Scope:**

- Extend shared result metadata where appropriate with player and team identity
  fields identified in the Phase V4 inventory.
- Prefer additive structured fields over changing existing `player`, `players`,
  `team`, `teams`, and `opponent` display fields.
- Update TypeScript API types to match the response envelope.
- Add or update API/query-service tests covering identity metadata for
  representative player, team, opponent, and comparison routes.
- Preserve existing CLI/API output behavior for current fields.

**Files likely touched:**

- `src/nbatools/query_service.py`
- Result/metadata model helpers if identity fields are centralized elsewhere
- `frontend/src/api/types.ts`
- API/query-service tests
- `docs/planning/phase_v4_work_queue.md` - check this item when complete

**Acceptance criteria:**

- Existing metadata fields remain stable.
- New identity fields are additive, typed, and documented by tests.
- The API distinguishes display name, abbreviation, and numeric id when known.
- No frontend component parses display strings to infer engine semantics.

**Tests to run:**

- `make test-impacted`
- `make test-api`
- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v4_identity_inventory.md`
- `docs/reference/result_contracts.md`
- `src/nbatools/query_service.py`
- `frontend/src/api/types.ts`

---

## 4. `[ ]` Render player headshots in metadata chips and data tables

**Why:** Player identity should be recognizable in the primary result surfaces,
with graceful fallback where ids or images are unavailable.

**Scope:**

- Use the identity helper and enriched metadata to pass `imageUrl` into
  `Avatar` for result context chips.
- Update the NBA-specific data-table wrapper to pair player display columns
  with adjacent player id fields when available.
- Preserve current initials fallback, accessible labels, table formatting, and
  horizontal scrolling.
- Add tests for rows with player ids, rows without player ids, and image
  fallback behavior.

**Files likely touched:**

- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/design-system/Avatar.tsx` and CSS only if fallback handling
  needs a primitive-level adjustment
- Frontend tests
- `docs/planning/phase_v4_work_queue.md` - check this item when complete

**Acceptance criteria:**

- Player headshots render where a stable player id is available.
- Missing ids or unavailable images fall back to initials without layout shift.
- Existing entity-column formatting and result rendering behavior are unchanged.
- Frontend tests and build pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v4_identity_inventory.md`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/design-system/Avatar.tsx`

---

## 5. `[ ]` Render team logos and color-aware badges

**Why:** Team identity should be visible and consistent in metadata, opponent
chips, and team/opponent table columns without overloading the UI with color.

**Scope:**

- Use the identity helper and enriched metadata to pass `logoUrl` and scoped
  color variables into `TeamBadge`.
- Update the NBA-specific data-table wrapper to pair team display columns with
  adjacent team id/abbreviation fields when available.
- Preserve abbreviation fallback for unknown or historical teams.
- Keep team colors out of global buttons, body text, and dense table values.
- Add tests for known active teams, unknown teams, opponent columns, and
  abbreviation-only rows.

**Files likely touched:**

- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/design-system/TeamBadge.tsx`
- `frontend/src/design-system/TeamBadge.module.css`
- Frontend tests
- `docs/planning/phase_v4_work_queue.md` - check this item when complete

**Acceptance criteria:**

- Team logos render where a stable identity is available.
- Unknown teams fall back to text badges.
- Team color appears only as contextual identity treatment.
- Frontend tests and build pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v4_identity_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/design-system/TeamBadge.tsx`

---

## 6. `[ ]` Apply scoped team theming to single-team result surfaces

**Why:** Team color should thread through the shell only when the result has a
clear single-team context, such as one team summary or one opponent-filtered
team card.

**Scope:**

- Use identity metadata and helper output to detect safe single-team context in
  presentation code.
- Apply scoped `--team-primary` and `--team-secondary` variables to result
  surfaces that have a single team subject.
- Add subtle team treatment such as a thin accent stripe or badge wash, not
  team-colored buttons or body copy.
- Do not apply single-team theming to league leaderboards, multi-team
  comparisons, or ambiguous/mixed contexts.
- Add focused tests for single-team and multi-team behavior.

**Files likely touched:**

- `frontend/src/App.tsx` or result-region wrapper components
- `frontend/src/App.module.css`
- `frontend/src/components/ResultEnvelope.tsx`
- Frontend tests
- `docs/planning/phase_v4_work_queue.md` - check this item when complete

**Acceptance criteria:**

- Single-team results receive scoped team CSS variables and subtle team accent
  treatment.
- Multi-team results remain neutral.
- Global action colors remain the design-system accent, not team colors.
- Frontend tests and build pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/phase_v4_identity_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/App.tsx`
- `frontend/src/components/ResultEnvelope.tsx`

---

## 7. `[ ]` Responsive and visual-quality verification for imagery/theming

**Why:** Images and logos can introduce clipping, layout shift, network-failure
states, and excess visual noise if not verified across realistic result shapes.

**Scope:**

- Review representative player, team, opponent-filtered, comparison, and
  leaderboard results at mobile and desktop widths.
- Fix clipping, overlap, row-height instability, broken-image layout, and
  excessive color emphasis.
- Update `docs/operations/ui_guide.md` with identity/theming notes useful for
  future component work.
- Add tests only where behavior changed or a regression risk is concrete.

**Files likely touched:**

- Frontend component/CSS modules touched by earlier Phase V4 items
- `docs/operations/ui_guide.md`
- `docs/planning/phase_v4_work_queue.md` - check this item when complete

**Acceptance criteria:**

- Headshots, logos, fallback initials, and text badges do not overlap or clip
  at mobile or desktop widths.
- Tables remain horizontally scrollable where needed.
- Team color treatment is visible in the right places and restrained in
  multi-team contexts.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`

---

## 8. `[ ]` Phase V4 retrospective and Phase V5 handoff

**Why:** Self-propagating final task. Captures identity/theming learnings and
drafts the final Track A Part 1 handoff queue.

**Scope:**

- Review every checked Phase V4 item: outcomes, surprises, residuals.
- Document any identity, image-source, or team-color decisions that affect Part
  2 component layouts.
- Draft `phase_v5_work_queue.md` for the Part 1 retrospective and Part 2
  handoff.
- The final item of Phase V5 should draft `component_experience_plan.md` and
  `phase_c1_work_queue.md`.
- Update `visual_foundation_plan.md`, `product_polish_master_plan.md`, and
  `docs/index.md` if active continuation or scope changes are needed.

**Files likely touched:**

- `docs/planning/phase_v4_work_queue.md` - check this item, add retrospective
- `docs/planning/phase_v5_work_queue.md` (new)
- `docs/planning/visual_foundation_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_v5_work_queue.md` exists with concrete PR-sized items.
- The final item of Phase V5 drafts Part 2 planning and its first queue.
- Active-continuation docs point to Phase V5.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `visual_foundation_plan.md` - Phase V5 scope
- This file as the structural template for Phase V5

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase V4 is complete. The draft of
`phase_v5_work_queue.md` from item 8 is the handoff artifact.
