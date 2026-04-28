# Visual Foundation Plan

> **Role: Track A Part 1 plan for the product polish master plan.** Lifts
> the design system from a tokens file into a real, usable primitives
> library, app shell, and visual foundation that the rest of the visual
> work builds on.
>
> Whole-plan completion authority is
> [`product_polish_master_plan.md`](./product_polish_master_plan.md). This
> doc covers Track A Part 1 only.

---

## Goal

By the end of this plan:

- The design tokens are wired in everywhere — no raw hex values, no raw
  font sizes, no off-grid spacing anywhere in the frontend
- A real primitives library exists (Button, Card, Stat, DataTable, Badge,
  StatBlock, etc.) that future component work consumes
- The app has a real layout shell — header with logo, prominent query bar,
  results region, freshness indicator
- Player headshots and team logos render consistently and reliably
  throughout the app
- A working team-color theming system exists — when the user queries
  Lakers stuff, Lakers colors thread through correctly; same for every
  team
- The existing query result rendering still works (no behavior regression),
  it just looks dramatically better

This plan does NOT redesign individual query class layouts — that's Part 2.
Part 1 builds the frame; Part 2 fills it.

---

## Why this comes first within Track A

Every component redesign in Part 2 will need:

- design tokens to reference
- primitives like Card and Stat to compose into
- player headshot and team logo components to drop into layouts
- a layout shell to live inside
- team-color theming to use

Building those foundations first means Part 2 work is fast and consistent.
Building them piecemeal during Part 2 means each component reinvents its
own pieces.

---

## Phase structure

Four phases, each with its own work queue.

### Phase V1 — Tokens audit and CSS architecture

Goal: every existing CSS rule in the frontend is converted to use design
tokens. The current `App.css` becomes a tokens-only file. Component-specific
styles move into proper component-scoped CSS modules or styled approach.
Result: the foundation is real, not just a tokens file sitting unused.

**Companion queue:** [`phase_v1_work_queue.md`](./phase_v1_work_queue.md)

### Phase V2 — Primitives library

Goal: build the reusable component primitives that everything else composes
out of. Button, Card, Stat, StatBlock, DataTable, Badge, Skeleton, Avatar
(player headshot wrapper), TeamBadge (team logo + color treatment),
SectionHeader, ResultEnvelopeShell. Each documented with usage examples.

**Companion queue:** drafted at end of V1.

### Phase V3 — App shell and layout

Goal: the app gets a real layout — header with branding and query bar,
main content area, results region, freshness indicator at the top, sample
queries when empty. Replaces the current bare-bones structure.

**Companion queue:** drafted at end of V2.

### Phase V4 — Player imagery and team theming

Goal: player headshots load reliably with fallback handling. Team logos
render consistently. The `--team-primary` and `--team-secondary` CSS
variables get populated dynamically based on team context. Existing
results render with the new theming applied automatically.

**Companion queue:** drafted at end of V3.

### Phase V5 — Retrospective and Part 2 handoff

Goal: capture learnings, draft `component_experience_plan.md` (Part 2 of
Track A), draft `phase_c1_work_queue.md` (Part 2's first queue).

**Companion queue:** drafted at end of V4.

---

## Done definition for Track A Part 1

Part 1 is done when:

1. Every CSS file in the frontend uses design tokens — no raw hex codes
   for colors that should be tokens, no raw px values for spacing that
   should be on the 4px grid, no font sizes that bypass the type scale
2. A documented primitives library exists in `frontend/src/design-system/`
   with at minimum: Button, Card, Stat, StatBlock, DataTable, Badge,
   Skeleton, Avatar, TeamBadge, SectionHeader
3. The app has a real layout shell: header, query bar prominent, results
   region styled, freshness indicator visible
4. Player headshots render for every player reference in the existing UI
5. Team logos render for every team reference in the existing UI
6. Team colors thread through correctly: Lakers query → subtle Lakers
   accent stripe on team-context cards
7. All existing tests pass — no functional regression
8. Visual quality bar met: a friend looking at the product would say
   "this looks like a real product" even though no individual component
   has been redesigned yet

---

## Visual quality bar for Part 1

This is the felt difference between "engineering-complete" and "looks like
a real product":

- Backgrounds layer correctly (page → elevated → card → recessed input)
- Typography is consistent and readable, never inline-default
- Spacing is rhythmic — every gap is on the 4px grid
- The query bar feels like the product's centerpiece, not a developer input
- Player imagery makes results feel basketball-y, not generic
- Team colors add personality where they belong, not everywhere
- Loading and empty states exist and are designed (not browser defaults)

If this bar isn't met by the end of Part 1, Part 2 inherits a half-finished
foundation and component redesign quality suffers. Item-level acceptance
criteria in each queue should reinforce this bar.
