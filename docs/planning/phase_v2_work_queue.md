# Phase V2 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase V2 of
> [`visual_foundation_plan.md`](./visual_foundation_plan.md) - _Primitives
> library._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit, open a PR, wait for CI, merge when
> green, then immediately move on to the next unchecked item and repeat.
> Continue working items in order without stopping until every item is
> checked `[x]` or you hit a genuine blocker (failing tests you cannot
> resolve, missing credentials, an ambiguous decision that needs the user).
> If blocked, leave the item marked `[~]` with an inline note and stop. Do
> not stop merely because one item finished — the default is to keep going.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped (with inline note explaining why)

---

## Phase V2 goal

Create a reusable frontend primitives library in `frontend/src/design-system/`
so future result layouts compose shared, token-driven components instead of
rebuilding buttons, cards, tables, badges, stats, loading states, avatars, and
section shells inside every feature component.

The primitives must stay presentation-only. Query parsing, filtering,
analytics, and route-specific transformations remain in the engine/API or the
existing thin frontend wrappers.

---

## 1. `[x]` Inventory primitive needs and define component API boundaries

**Why:** The current UI already implies several primitives, but they are
embedded inside feature components. Before extracting code, define the reusable
surface and decide which behavior belongs in primitives versus wrappers.

**Scope:**

- Walk `frontend/src/components/`, `frontend/src/App.tsx`, and existing CSS
  modules.
- Identify repeated visual patterns: buttons, icon buttons, cards/panels,
  badges/chips, stat values, section headers, tables, loading states, player
  and team identity display, and result-envelope shells.
- Document what already exists, what should become a primitive, and what
  should remain feature-specific.
- Define proposed props, variants, and ownership boundaries for each primitive.
- Create `docs/planning/phase_v2_primitives_inventory.md`.
- Explicitly call out that the generic table primitive must not own
  NBA-specific value formatting.

**Files likely touched:**

- `docs/planning/phase_v2_primitives_inventory.md` (new)
- `docs/planning/phase_v2_work_queue.md` - check this item when complete
- `docs/index.md` - add the new inventory doc

**Acceptance criteria:**

- Inventory covers every existing component in `frontend/src/components/`.
- Each proposed primitive has a short API sketch and a clear owner path.
- Each boundary decision says whether behavior belongs in the design-system
  primitive, an existing feature wrapper, or a later phase.
- Residual risks or deferrals are documented before code extraction starts.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/archive/product-polish/completed-work-queues/phase_v1_work_queue.md` retrospective
- `frontend/src/components/`

---

## 2. `[x]` Establish `frontend/src/design-system/` and Button primitives

**Why:** Buttons are the most reused controls and set interaction language for
the rest of the primitive library.

**Scope:**

- Create `frontend/src/design-system/` with an `index.ts` barrel export.
- Add `Button` and `IconButton` primitives with token-only CSS modules.
- Support at least `primary`, `secondary`, `ghost`, and `danger` variants;
  `sm` and `md` sizes; disabled and loading states; and accessible labels for
  icon-only controls.
- Migrate a small, representative set of existing controls to the new
  primitives without changing behavior. Good candidates: `QueryBar`,
  `CopyButton`, and `RawJsonToggle`.
- Add focused component tests for primitive rendering and migrated behavior.

**Files likely touched:**

- `frontend/src/design-system/Button.tsx`
- `frontend/src/design-system/Button.module.css`
- `frontend/src/design-system/index.ts`
- Selected existing components and tests

**Acceptance criteria:**

- The design-system folder and export surface exist.
- Button primitives consume only design tokens for visual styling.
- Migrated controls keep their current labels, disabled states, submit/click
  behavior, and accessibility semantics.
- No query or API behavior changes.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/planning/phase_v2_primitives_inventory.md`
- AGENTS.md frontend rules

---

## 3. `[x]` Build Card, SectionHeader, and ResultEnvelopeShell primitives

**Why:** Most result views need a consistent surface, heading, metadata, and
envelope structure before individual query layouts are redesigned in Part 2.

**Scope:**

- Add `Card`, `SectionHeader`, and `ResultEnvelopeShell` primitives.
- Support elevation/depth variants that map to the background depth system.
- Keep status, route, freshness, notes, caveats, and alternate-query behavior
  in feature components; the shell primitive only owns layout and surface
  styling.
- Migrate `ResultEnvelope` and one or two section components enough to prove
  the primitives compose cleanly.
- Add or update tests for migrated rendering.

**Files likely touched:**

- `frontend/src/design-system/Card.tsx`
- `frontend/src/design-system/SectionHeader.tsx`
- `frontend/src/design-system/ResultEnvelopeShell.tsx`
- Selected existing components and tests

**Acceptance criteria:**

- Cards and section headers use tokenized backgrounds, borders, radii,
  spacing, type, and shadows.
- The result envelope renders the same metadata and actions as before.
- Feature components remain thin presentation layers.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/*Section.tsx`

---

## 4. `[x]` Build Badge, Stat, and StatBlock primitives

**Why:** Result layouts need consistent chips, labels, and numeric stat
treatments before hero and comparison components can become opinionated.

**Scope:**

- Add `Badge`, `Stat`, and `StatBlock` primitives.
- Support neutral, accent, success, warning, danger, win, and loss semantics
  where appropriate.
- Ensure all numeric stat values use the mono typeface and tabular numerals.
- Migrate status/context chips and at least one summary-style stat display to
  use the primitives.
- Add tests for variants and migrated rendering.

**Files likely touched:**

- `frontend/src/design-system/Badge.tsx`
- `frontend/src/design-system/Stat.tsx`
- `frontend/src/design-system/StatBlock.tsx`
- Selected existing components and tests

**Acceptance criteria:**

- Badge/status semantics match the design-system status-color guidance.
- Stat primitives never compute NBA metrics; they only render provided label,
  value, context, and trend/semantic props.
- Migrated components render the same data as before.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/planning/phase_v2_primitives_inventory.md`

---

## 5. `[x]` Build Skeleton and loading-state primitives

**Why:** Loading states should feel designed and consistent before the app
shell and result layouts get more visual weight.

**Scope:**

- Add `Skeleton`, `SkeletonText`, and `SkeletonBlock` primitives or a similarly
  small grouped API.
- Migrate the existing loading component to use the skeleton primitives while
  preserving the current loading behavior.
- Keep motion restrained and token-driven where tokens exist; document any
  animation-duration exception if a token is not appropriate.
- Add tests for loading rendering.

**Files likely touched:**

- `frontend/src/design-system/Skeleton.tsx`
- `frontend/src/design-system/Skeleton.module.css`
- `frontend/src/components/Loading.tsx`
- `frontend/src/test/UIComponents.test.tsx`

**Acceptance criteria:**

- Loading state is visibly designed, not browser-default text only.
- Skeleton colors, radii, spacing, and motion use existing design-system
  conventions.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `frontend/src/components/Loading.tsx`

---

## 6. `[ ]` Split generic DataTable primitive from NBA-specific table wrapper

**Why:** The current `DataTable` owns both table presentation and
NBA-specific formatting. Future layouts need a reusable table primitive
without moving business logic into the design system.

**Scope:**

- Add a generic design-system `DataTable` primitive that renders supplied
  columns, rows, alignment, and cell content/classes.
- Keep `formatColHeader`, `formatValue`, entity-column detection, and
  query-result-specific decisions in `frontend/src/components/DataTable.tsx`
  or another thin wrapper outside the design-system folder.
- Migrate the existing component to compose the primitive.
- Preserve highlight mode and current table rendering.
- Update DataTable tests to cover the split.

**Files likely touched:**

- `frontend/src/design-system/DataTable.tsx`
- `frontend/src/design-system/DataTable.module.css`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/test/DataTable.test.tsx`

**Acceptance criteria:**

- The design-system table has no NBA-specific formatting or query semantics.
- Existing result tables render the same columns, formatted values, and
  highlight behavior as before.
- Stat/numeric columns keep tabular numeral alignment.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- AGENTS.md frontend-layer rule
- `docs/architecture/design_system.md`
- `frontend/src/components/DataTable.tsx`

---

## 7. `[ ]` Build Avatar and TeamBadge fallback primitives

**Why:** Phase V4 will add real player imagery and team-logo plumbing, but
Part 1 needs stable identity primitives first so later image work has a
consistent target.

**Scope:**

- Add `Avatar` for player/person identity with initials and unavailable-image
  fallback states.
- Add `TeamBadge` for team identity with abbreviation/name display and optional
  `--team-primary` / `--team-secondary` styling hooks.
- Do not add new player headshot or logo data sources in this item.
- Migrate low-risk identity displays where the API already provides a player or
  team name.
- Add tests for fallback rendering and accessible labels.

**Files likely touched:**

- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`
- Selected existing components and tests

**Acceptance criteria:**

- Avatar and TeamBadge render useful fallback UI without external image
  dependencies.
- Team color hooks follow the design-system rule: contextual identity only,
  not button or body-text coloring.
- Phase V4 remains the owner for real image/logo source integration.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `frontend/src/styles/team-colors.json`

---

## 8. `[ ]` Document primitive usage and finish library export hygiene

**Why:** The primitives library should be easy to consume during Phase V3 and
Track A Part 2 without rediscovering variants from source files.

**Scope:**

- Update `docs/operations/ui_guide.md` with the design-system primitive list,
  import path, variant guidance, and short usage examples.
- Verify every primitive is exported from `frontend/src/design-system/index.ts`.
- Verify each primitive has colocated CSS modules and token-only styling.
- Add a short checklist for future components that consume primitives.

**Files likely touched:**

- `docs/operations/ui_guide.md`
- `frontend/src/design-system/index.ts`
- `docs/planning/phase_v2_work_queue.md` - check this item when complete

**Acceptance criteria:**

- UI guide documents every primitive built in Phase V2.
- Example snippets are presentation-only and do not imply unsupported query
  behavior.
- Export surface is complete and consistent.
- Build and tests pass if source files changed.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/operations/ui_guide.md`
- `docs/architecture/design_system.md`

---

## 9. `[ ]` Phase V2 retrospective and Phase V3 handoff

**Why:** Self-propagating final task. Captures learnings and drafts the next
queue.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals.
- Document any primitive gaps or design-system decisions that affect Phase V3.
- Draft `phase_v3_work_queue.md` for app shell and layout work.
- The first item of Phase V3 should be an app-shell inventory of current
  layout, query-bar, freshness, empty-state, saved-query, and result-region
  ownership.
- The final item of Phase V3 should draft Phase V4.
- Update `visual_foundation_plan.md` and `product_polish_master_plan.md` if
  active continuation or scope changes are needed.

**Files likely touched:**

- `docs/planning/phase_v2_work_queue.md` - check this item, add retrospective
- `docs/planning/phase_v3_work_queue.md` (new)
- `docs/planning/visual_foundation_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_v3_work_queue.md` exists with concrete items at PR-size granularity.
- The final item of Phase V3 drafts Phase V4.
- Active-continuation docs point to Phase V3.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `visual_foundation_plan.md` - Phase V3 scope
- This file as the structural template for Phase V3

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase V2 is complete. The draft of
`phase_v3_work_queue.md` from item 9 is the handoff artifact.
