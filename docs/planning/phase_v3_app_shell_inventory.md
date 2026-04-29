# Phase V3 App Shell Inventory

> **Role:** ownership and boundary inventory for Phase V3 app-shell and layout
> work before reshaping the React application frame.

---

## Goal

Phase V3 should turn the existing functional UI into a coherent app shell
without moving query behavior, API semantics, result routing, saved-query
workflow logic, or NBA-specific formatting into layout-only code.

The shell should own page structure, visual hierarchy, responsive regions, and
composition of presentation primitives. Feature components should continue to
own their feature behavior.

---

## Reference Inputs

- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`
- `docs/planning/phase_v2_primitives_inventory.md`
- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/SampleQueries.tsx`
- `frontend/src/components/FreshnessStatus.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/Loading.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/RawJsonToggle.tsx`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/DevTools.tsx`

---

## Current Layout Ownership

| Surface | Current owner | Current responsibilities | Phase V3 boundary decision |
| --- | --- | --- | --- |
| Page shell | `frontend/src/App.tsx`, `frontend/src/App.module.css` | Single-column page width, header, query area, result area, saved queries, history, dev tools, save dialog mounting | Extract page-region structure to a presentation-only shell component or layout module. Keep state, API calls, URL state, saved-query state, and event handlers in `App.tsx`. |
| Header and API status | `App.tsx`, `App.module.css` | App title, API health fetch result, version/offline indicator | Shell can own header layout slots. `App.tsx` keeps `fetchHealth`, `version`, and `apiOnline`. Status rendering can use `Badge` or tokenized shell styles only. |
| Query bar area | `App.tsx`, `QueryBar.tsx`, `SampleQueries.tsx` | Input state wiring, submit/running state, clear action, sample-query execution | Shell owns the query-workspace region. `QueryBar` owns form behavior and input controls; `SampleQueries` owns sample strings and selection callbacks. |
| Freshness panel | `FreshnessStatus.tsx` | Fetches freshness, polls, maps status semantics, renders expand/collapse details | Place it in a first-class shell status region, but keep fetching, polling, status labels, detail rows, and freshness semantics inside `FreshnessStatus`. |
| Empty state | `EmptyState.tsx` | First-run copy and starter tips | Shell owns placement in the main result/workspace region. `EmptyState` owns its copy and tips until the later first-run polish phase. |
| Loading state | `Loading.tsx` | Accessible loading status and skeleton preview | Shell owns placement. `Loading` owns status copy, `role="status"`, skeleton shape, and aria behavior. |
| No-result state | `ResultSections.tsx`, `NoResultDisplay.tsx` | Detects no-result/error result payloads, maps reasons to copy, renders notes and suggestions | Keep result-status branching in `ResultSections`; keep reason and suggestion copy in `NoResultDisplay`. Shell only provides result-region spacing. |
| Result metadata | `ResultEnvelope.tsx` plus `ResultEnvelopeShell` primitive | Maps response status, route, query class, freshness, metadata chips, notes, caveats, and alternates | Keep all response interpretation in `ResultEnvelope`. Shell can group the result card with actions and sections. |
| Result actions | `App.tsx`, `CopyButton.tsx`, `RawJsonToggle.tsx` | Copy link/query/JSON, save dialog trigger, raw JSON toggle | Move action-row layout into the result region. Preserve clipboard behavior in `CopyButton`, save-dialog state in `App.tsx`, and raw JSON open state in `RawJsonToggle`. |
| Result sections | `ResultSections.tsx` and query-class section components | Dispatches by `query_class`, chooses section renderer, falls back to generic section tables | Keep dispatch and query-class routing here. Phase V3 should not redesign individual query-class layouts beyond shell spacing. |
| Saved queries | `SavedQueries.tsx`, `useSavedQueries`, `SaveQueryDialog` | Saved-query CRUD, import/export, pinning, tag filtering, edit dialog | Reframe as a secondary shell panel. Keep all persistence, file import/export, tag filtering, dialog state, and row actions in the saved-query components/hooks. |
| Query history | `QueryHistory.tsx`, `useQueryHistory` | In-session history list, time labels, rerun/edit/save actions, clear | Reframe as a secondary shell panel. Keep history state and row actions in the existing hook/component. |
| Dev tools | `DevTools.tsx` | Route loading, structured kwargs JSON parsing, structured-query execution | Keep development behavior in `DevTools`. Shell should make the panel visually secondary and clearly development-oriented. |

---

## Planned Layout Extractions

| Extraction | Owner path | What it should own | What it must not own |
| --- | --- | --- | --- |
| App shell frame | `frontend/src/components/AppShell.tsx` with a colocated CSS module, or a small `frontend/src/components/AppShell/` module if the implementation needs subparts | Header, status, query, main/result, and secondary-panel regions as slots; responsive page structure; token-driven spacing and background depth | Query execution, API fetches, URL state, saved-query persistence, history mutations, result interpretation |
| Header/status presentation | App-shell component plus `App.tsx` supplied content | Branding layout, compact status placement, accessible visual hierarchy | API health fetching, version/offline state, freshness fetching |
| Main workspace | App-shell slots and `App.module.css`/shell CSS | Query region, loading/error/empty/result placement, responsive ordering | Query form behavior, sample query selection, error generation |
| Result region wrapper | App-shell slot or small presentational wrapper near `App.tsx` | Result card/action/sections/raw JSON hierarchy and spacing | Response envelope semantics, query-class routing, copy/save/raw behavior |
| Secondary panel area | App-shell slots | Saved queries, query history, and dev tools as quieter secondary regions | Saved-query CRUD, history actions, structured-query dev execution |

The first implementation should prefer one small shell component with named
slots over multiple new abstractions. Additional subcomponents should only be
added if the shell JSX becomes hard to scan.

---

## Primitive Composition Targets

- Use `Card` for shell panels only when a surface is truly a card. Avoid nested
  card-on-card structure around result sections.
- Use `SectionHeader` for saved-query, history, sample-query, and secondary
  panel headers where it reduces repeated label/count/action layout.
- Use `Button` and `IconButton` for shell actions, save-query triggers, sample
  query chips, saved/history actions, and dev-tool submit controls as practical.
- Use `Badge` for API status, freshness status, route/status chips, query-class
  labels, tags, and compact metadata.
- Keep `ResultEnvelopeShell`, `DataTable`, `Avatar`, `TeamBadge`, `Skeleton`,
  `Stat`, and `StatBlock` as presentation primitives only. Feature wrappers
  choose data, labels, sections, status mappings, and value formatting.

---

## Behavior Boundaries

These behaviors must remain in feature components or hooks:

- Natural and structured query execution stays in `App.tsx` and API client
  wrappers.
- URL parsing, browser history updates, and auto-run-on-load stay in
  `useUrlState` and `App.tsx`.
- API health fetching stays in `App.tsx`.
- Freshness fetching, polling, expand/collapse state, and freshness status
  semantics stay in `FreshnessStatus`.
- Sample query strings stay in `SampleQueries`.
- Result metadata mapping, alternate-query selection, notes, caveats, context
  chips, and data-through display stay in `ResultEnvelope`.
- Query-class routing and no-result/error branching stay in `ResultSections`.
- Clipboard fallback behavior stays in `CopyButton`.
- Raw JSON toggle state stays in `RawJsonToggle`.
- Saved-query CRUD, import/export, tag filtering, pinning, and edit-dialog
  workflow stay in `SavedQueries`, `SaveQueryDialog`, and `useSavedQueries`.
- Query-history storage, time labels, rerun/edit/save actions, and clear
  behavior stay in `QueryHistory` and `useQueryHistory`.
- Structured route fetching, kwargs parsing, and structured-query execution stay
  in `DevTools`.

---

## Residual Risks And Deferrals

- `App.tsx` currently mixes orchestration and markup. Phase V3 should reduce
  layout markup there, but it should not hide state transitions or event wiring
  behind a shell abstraction.
- Inputs, selects, textareas, list rows, modals, and checkboxes remain deferred
  primitives. The shell pass can restyle them through existing components, but
  should not expand the design-system API unless repeated complexity blocks the
  work.
- Result actions are currently split between `App.tsx`, `CopyButton`, and
  `RawJsonToggle`. The shell pass should improve hierarchy without changing
  copy/save/toggle behavior.
- Individual query-class layouts remain Part 2 work. Phase V3 may improve
  region spacing and responsive containers, but should not redesign summary,
  leaderboard, comparison, finder, streak, or split views.
- Player headshots, team logos, and dynamic team-color plumbing remain Phase V4.
  Current `Avatar` and `TeamBadge` use fallback identity treatments only.
- First-run messaging gets deeper polish in Track A Part 3. Phase V3 should make
  the empty state look coherent with the shell without turning it into a
  marketing landing page.
