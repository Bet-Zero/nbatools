# Phase V3 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase V3 of
> [`visual_foundation_plan.md`](./visual_foundation_plan.md) - _App shell
> and layout._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit, open a PR, wait for CI, merge when
> green, then immediately move on to the next unchecked item and repeat.
> Continue working items in order without stopping until every item is
> checked `[x]` or you hit a genuine blocker (failing tests you cannot
> resolve, missing credentials, an ambiguous decision that needs the user).
> If blocked, leave the item marked `[~]` with an inline note and stop. Do
> not stop merely because one item finished - the default is to keep going.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped (with inline note explaining why)

---

## Phase V3 goal

Turn the current functional React app into a coherent product shell: a
token-driven layout with clear header, prominent query area, visible freshness
state, organized result region, and secondary saved/history/dev surfaces that
support repeated use without crowding the primary workflow.

The app shell remains a presentation layer. Query parsing, API response
semantics, filtering, analytics, and NBA metric computation stay in the engine,
API, or existing feature wrappers.

---

## 1. `[x]` Inventory app-shell layout and ownership boundaries

**Why:** Phase V2 created primitives. Before reshaping the app shell, define
which parts of the current UI belong to the shell versus feature components.

**Scope:**

- Review `frontend/src/App.tsx`, `frontend/src/App.module.css`,
  `frontend/src/components/QueryBar.tsx`, `FreshnessStatus.tsx`,
  `EmptyState.tsx`, `SavedQueries.tsx`, `QueryHistory.tsx`, `DevTools.tsx`,
  `ResultEnvelope.tsx`, and `ResultSections.tsx`.
- Inventory current layout ownership for header, query bar, freshness,
  sample queries, empty state, result actions, result region, saved queries,
  query history, and dev tools.
- Define which surfaces should compose existing primitives from
  `frontend/src/design-system/`.
- Create `docs/planning/phase_v3_app_shell_inventory.md`.
- Explicitly call out any behavior that must remain in feature components.

**Files likely touched:**

- `docs/planning/phase_v3_app_shell_inventory.md` (new)
- `docs/planning/phase_v3_work_queue.md` - check this item when complete
- `docs/index.md` - add the new inventory doc

**Acceptance criteria:**

- Inventory covers the app shell, query-bar area, freshness panel, empty
  state, saved queries, query history, dev tools, and result region.
- Each planned layout extraction has a clear owner path.
- Behavior boundaries are explicit: no query/API behavior moves into layout
  primitives or shell-only components.
- Residual risks and deferrals are documented before layout code changes.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`
- `docs/planning/phase_v2_primitives_inventory.md`

---

## 2. `[x]` Build AppShell layout component and page regions

**Why:** The app needs one coherent page frame before individual sections are
rearranged. A shell component keeps layout structure separate from query
execution state.

**Scope:**

- Add an app-shell component or small layout module under
  `frontend/src/components/` or `frontend/src/design-system/` only if it is
  presentation-only.
- Define regions for header, query area, freshness/status area, main result
  area, and secondary panels.
- Migrate `App.tsx` to compose the shell while keeping query execution, URL
  state, saved-query state, and API calls in `App.tsx`.
- Use existing primitives (`Card`, `SectionHeader`, `Button`, `Badge`) where
  appropriate.
- Preserve all current user workflows and URL behavior.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- Optional layout component/CSS module
- Frontend tests as needed

**Acceptance criteria:**

- The app has stable named regions and no nested-card page-section layout.
- `App.tsx` still owns state and orchestration; shell/layout code is
  presentation-only.
- Header, query area, result area, and secondary panels remain visible and
  usable.
- Desktop and mobile widths do not overlap or clip core controls.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/planning/phase_v3_app_shell_inventory.md`
- `docs/architecture/design_system.md`
- `frontend/src/App.tsx`

---

## 3. `[x]` Redesign header, API status, and freshness placement

**Why:** The product needs a calm top frame that identifies the app and makes
data/API status visible without competing with the query workflow.

**Scope:**

- Redesign the header using existing primitives and tokens.
- Keep API health fetching in `App.tsx`.
- Keep freshness fetching and freshness semantics in `FreshnessStatus.tsx`.
- Move or restyle freshness placement so it reads as a first-class status
  panel in the app shell.
- Preserve all current freshness details and expand/collapse behavior.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/components/FreshnessStatus.tsx`
- `frontend/src/components/FreshnessStatus.module.css`
- Freshness/UI tests

**Acceptance criteria:**

- Header and status styling uses tokens and existing primitives.
- Freshness status remains honest and fully rendered.
- API offline/online states remain accessible and clear.
- No API client or freshness semantics move into the shell.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/FreshnessStatus.tsx`

---

## 4. `[x]` Make the query area the primary workspace

**Why:** The text input is the product's main interaction. It should feel
prominent and efficient without becoming a marketing hero.

**Scope:**

- Restyle the query area around `QueryBar` and `SampleQueries`.
- Preserve query submission, disabled/running behavior, clear behavior, sample
  query selection, and URL updates.
- Use `Button`/`IconButton` primitives consistently.
- Keep sample query strings feature-specific.
- Ensure mobile layout keeps the input and submit action usable.

**Files likely touched:**

- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/QueryBar.module.css`
- `frontend/src/components/SampleQueries.tsx`
- `frontend/src/components/SampleQueries.module.css`
- `frontend/src/App.module.css`
- Button/UI tests

**Acceptance criteria:**

- Query input has clear visual priority as a working tool, not a landing-page
  hero.
- Keyboard submit, button submit, clear, loading, and sample selection behavior
  are unchanged.
- Text and buttons fit at mobile and desktop widths.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/planning/phase_v3_app_shell_inventory.md`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/SampleQueries.tsx`

---

## 5. `[x]` Redesign empty, loading, and no-result shell states

**Why:** First-run and transitional states are part of the app shell. They
should establish product quality before any query result appears.

**Scope:**

- Restyle `EmptyState`, `Loading`, and `NoResultDisplay` with existing
  primitives.
- Preserve all current loading text, no-result reason handling, unsupported
  handling, ambiguous handling, notes, and suggestions.
- Keep copy modest and task-oriented; do not create a marketing landing page.
- Ensure loading skeletons align with the result-region layout.

**Files likely touched:**

- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/EmptyState.module.css`
- `frontend/src/components/Loading.tsx`
- `frontend/src/components/Loading.module.css`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/NoResultDisplay.module.css`
- UI tests

**Acceptance criteria:**

- Empty/loading/no-result states look designed and consistent with the shell.
- No-result semantics and suggestions are unchanged.
- Loading behavior and accessible status remain intact.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/NoResultDisplay.tsx`

---

## 6. `[x]` Organize result actions and result region layout

**Why:** Results should have a stable area for metadata, actions, tables, raw
JSON, and future designed query-class layouts.

**Scope:**

- Restyle the result region around `ResultEnvelope`, result actions,
  `ResultSections`, and `RawJsonToggle`.
- Preserve copy-link, copy-query, copy-JSON, save-query, raw-JSON toggle, and
  alternate-query behavior.
- Use existing primitives for action rows and section layout.
- Do not redesign individual query-class layouts beyond shell spacing and
  region structure.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/RawJsonToggle.tsx`
- Result/action tests

**Acceptance criteria:**

- Result metadata, actions, sections, and raw JSON have clear hierarchy.
- Existing result tables and query-class routing render unchanged data.
- Copy/save/raw/alternate actions keep current behavior.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/ResultSections.tsx`
- `docs/operations/ui_guide.md`

---

## 7. `[ ]` Reframe saved queries, history, and dev tools as secondary panels

**Why:** Saved queries and history are useful, but they should not compete
with the primary query/result workflow. Dev tools should remain available
without looking like product chrome.

**Scope:**

- Restyle `SavedQueries`, `QueryHistory`, and `DevTools` as secondary panels
  in the app shell.
- Preserve saved-query CRUD, pinning, import/export, tag filtering, history
  rerun/edit/save, and structured-query dev behavior.
- Use primitives for buttons, badges, cards, and section headers where
  practical.
- Keep dev-tool behavior explicitly development-oriented.

**Files likely touched:**

- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/SavedQueries.module.css`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/QueryHistory.module.css`
- `frontend/src/components/DevTools.tsx`
- `frontend/src/components/DevTools.module.css`
- Saved/history/dev tests

**Acceptance criteria:**

- Secondary panels are scannable and visually quieter than the main workflow.
- All saved-query, history, and dev-tool behavior is preserved.
- Import/export controls remain accessible.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/planning/phase_v3_app_shell_inventory.md`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/DevTools.tsx`

---

## 8. `[ ]` Responsive and visual-quality verification pass

**Why:** The shell is not complete until it works at realistic desktop and
mobile widths with no clipped controls, overlapping text, or awkward region
ordering.

**Scope:**

- Review the complete app shell at representative mobile and desktop widths.
- Fix responsive issues in header, query area, freshness, result actions,
  tables, saved/history panels, and dev tools.
- Add focused tests only where behavior changed or a regression risk is
  concrete.
- Update `docs/operations/ui_guide.md` with any shell/layout notes that are
  useful for future frontend work.

**Files likely touched:**

- `frontend/src/App.module.css`
- Component CSS modules touched by earlier Phase V3 items
- `docs/operations/ui_guide.md`

**Acceptance criteria:**

- No core text or controls overlap, clip, or become unreachable at mobile and
  desktop widths.
- Tables remain horizontally scrollable where needed.
- Shell hierarchy remains clear with long query text and dense results.
- Build and tests pass.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`

**Reference docs to consult:**

- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`

---

## 9. `[ ]` Phase V3 retrospective and Phase V4 handoff

**Why:** Self-propagating final task. Captures shell/layout learnings and
drafts the player imagery and team-theming queue.

**Scope:**

- Review every checked Phase V3 item: outcomes, surprises, residuals.
- Document any shell/layout decisions that affect Phase V4.
- Draft `phase_v4_work_queue.md` for player imagery, team logos, and dynamic
  team-color plumbing.
- The first item of Phase V4 should inventory available player/team identity
  data, target UI locations, and fallback semantics.
- The final item of Phase V4 should draft Phase V5.
- Update `visual_foundation_plan.md`, `product_polish_master_plan.md`, and
  `docs/index.md` if active continuation or scope changes are needed.

**Files likely touched:**

- `docs/planning/phase_v3_work_queue.md` - check this item, add retrospective
- `docs/planning/phase_v4_work_queue.md` (new)
- `docs/planning/visual_foundation_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_v4_work_queue.md` exists with concrete PR-sized items.
- The final item of Phase V4 drafts Phase V5.
- Active-continuation docs point to Phase V4.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `visual_foundation_plan.md` - Phase V4 scope
- This file as the structural template for Phase V4

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase V3 is complete. The draft of
`phase_v4_work_queue.md` from item 9 is the handoff artifact.
