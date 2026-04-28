# Phase V1 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase V1 of
> [`visual_foundation_plan.md`](./visual_foundation_plan.md) — _Tokens audit
> and CSS architecture._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit. Repeat. When every item above is
> checked, work the final meta-task.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Phase V1 goal

Take the design tokens that already exist in `frontend/src/styles/tokens.css`
and make them the actual source of truth for the entire frontend. By the
end of this phase, no CSS file in the frontend uses raw color hex values for
things that should be tokens, raw spacing values that bypass the 4px grid,
or raw font sizes that bypass the type scale.

This is the foundation phase. Nothing visible should dramatically change.
What changes is that every future visual decision now has a clean foundation
to build on.

---

## 1. `[x]` Audit current frontend CSS for token-replaceable values

**Why:** Before refactoring CSS, we need to know what's there. The agent
should walk every `.css`, `.scss`, and inline `style={...}` in the frontend
and produce an inventory of: hardcoded color values, hardcoded font sizes,
hardcoded spacing values, hardcoded border radii, and any inline styles that
should move into proper CSS.

**Scope:**

- Walk `frontend/src/` recursively
- Catalog every hardcoded color (anything that should be a token but isn't)
- Catalog every hardcoded font size, weight, family
- Catalog every hardcoded spacing value (padding, margin, gap)
- Catalog every hardcoded border radius
- Catalog every inline style attribute on JSX elements
- For each finding, note: file path, line number, what it currently is,
  what token it should map to
- Flag items that don't have a clear token mapping (these need design
  decisions, not mechanical replacement)
- Produce inventory at `docs/planning/phase_v1_css_inventory.md`

**Files likely touched:**

- `docs/planning/phase_v1_css_inventory.md` (new)
- No code changes — reconnaissance only

**Acceptance criteria:**

- Every hardcoded value across the frontend is cataloged
- Each entry has a proposed token mapping (or is flagged as needing
  decision)
- Inventory is structured as a punchlist for items 2-4 to consume
- Inventory is committed to the repo

**Tests to run:**

- None (reconnaissance only)

**Reference docs to consult:**

- `frontend/src/styles/tokens.css` — the token catalog
- `docs/architecture/design_system.md` — the design system philosophy
- `frontend/` — all CSS and TSX files

---

## 2. `[x]` Replace hardcoded colors with tokens

**Why:** Most-impactful first refactor. Every color in the app should
reference a token, so future global color adjustments require editing one
file, not hunting through dozens.

**Scope:**

- Use the inventory from item 1 to replace every hardcoded color value
- Color hex values map to: `--bg-page`, `--bg-elevated`, `--bg-card`,
  `--bg-input`, `--border-subtle`, `--border-default`, `--border-strong`,
  `--text-primary`, `--text-secondary`, `--text-tertiary`, `--accent`,
  `--accent-hover`, status colors (`--success`, `--danger`, etc.), and
  win/loss colors (`--win`, `--loss`)
- Inline `style={{ color: '#xxx' }}` patterns get hoisted into proper CSS
  classes that reference tokens
- For colors that don't cleanly map to existing tokens, flag in commit
  message — do not invent new tokens without justification
- The visible appearance should be very close to identical (the existing
  CSS approximated the new tokens; this just makes the relationship
  explicit)

**Files likely touched:**

- `frontend/src/App.css` — primary
- Any component files with inline color styles
- Possibly `frontend/src/styles/tokens.css` if the inventory found
  legitimate token gaps

**Acceptance criteria:**

- No raw color hex codes remain in `frontend/src/` for colors that should
  be tokens (status messages from libraries are fine if they're isolated)
- All visible colors still look right — no surprise rendering changes
- Build still succeeds: `cd frontend && npm run build`
- Existing tests still pass: `cd frontend && npm test`
- "Looks done" check: open the running app, scroll through it, confirm
  visual rendering is consistent with what existed before

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`
- Manual: run `npm run dev` locally and visually verify no obvious color
  regressions

**Reference docs to consult:**

- Item 1's CSS inventory
- `frontend/src/styles/tokens.css`
- `docs/architecture/design_system.md`

---

## 3. `[x]` Replace hardcoded spacing and sizing with tokens

**Why:** The 4px-base spacing scale is what makes a layout feel rhythmic
and intentional. Random padding/margin values are the single biggest "looks
amateur" tell.

**Scope:**

- Replace every padding/margin/gap value in the frontend with the spacing
  tokens (`--space-1` through `--space-16`)
- Replace every border-radius value with the radius tokens (`--radius-sm`,
  `--radius-md`, `--radius-lg`, `--radius-xl`)
- For values that aren't on the 4px grid, round to the nearest grid value
  rather than introducing new tokens
- Document any pixel value that genuinely cannot be on the grid (rare —
  things like 1px borders) so future devs know not to "fix" them

**Files likely touched:**

- `frontend/src/App.css` — primary
- Any component files with inline spacing styles

**Acceptance criteria:**

- Every spacing value in the frontend is either a token or a documented
  exception
- Border radii consistently use the radius tokens
- Visual layout is similar enough to before that it doesn't feel broken,
  though small spacing tweaks are expected and fine
- Build and tests pass

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`
- Manual: visually verify layout is sane after the change

**Reference docs to consult:**

- Item 1's CSS inventory
- `frontend/src/styles/tokens.css` (spacing and radii sections)

---

## 4. `[x]` Replace hardcoded typography with tokens

**Why:** Final piece of the token wiring. Font sizes, weights, and family
references should all flow from the type scale.

**Scope:**

- Replace every font-size value with the size tokens (`--font-stat-hero`,
  `--font-display`, `--font-h1`, `--font-h2`, `--font-stat-md`, `--font-h3`,
  `--font-body`, `--font-small`, `--font-micro`)
- Replace font-family references with `--font-sans` or `--font-mono`
- Replace font-weight values with the weight tokens
- Apply `font-feature-settings: 'tnum'` (tabular numerals) to elements that
  display stat numbers, especially in tables — this is the single biggest
  perceived-quality upgrade for a stats product
- Apply letter-spacing tokens where appropriate (display text gets
  `--tracking-tight` or `--tracking-display`, uppercase labels get
  `--tracking-uppercase`)

**Files likely touched:**

- `frontend/src/App.css`
- Any component files with inline font styles

**Acceptance criteria:**

- All typography in the frontend uses the type scale
- Stat numbers (anywhere a number is displayed in a row alongside other
  numbers) use JetBrains Mono with tabular numerals
- Build and tests pass
- "Looks done" check: stat columns in result tables align beautifully —
  the digits in column N all sit in the same horizontal positions

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`
- Manual: run the app, search a leaderboard, confirm stat columns are
  visually aligned

**Reference docs to consult:**

- Item 1's CSS inventory
- `frontend/src/styles/tokens.css` (typography section)
- `docs/architecture/design_system.md` (typography philosophy)

---

## 5. `[ ]` Establish CSS architecture: scoped component styles

**Why:** Right now most styles live in one big `App.css`. As the app grows,
this gets unwieldy. Component-scoped CSS makes it easier to find styles
that belong to a component and prevents global CSS pollution.

**Scope:**

- Pick a styling approach: CSS modules (`Component.module.css`) is the
  recommended default — works with Vite, doesn't require new dependencies,
  preserves the simplicity the rest of the codebase expects
- Migrate existing component-specific styles from `App.css` into per-component
  CSS module files
- Keep truly global styles (resets, body, root layout containers, token
  imports) in a renamed `frontend/src/styles/global.css`
- Update `App.css` (or replace it with `global.css`) to be small and focused
- Each component file imports its own `.module.css` and uses the imported
  class names

**Files likely touched:**

- `frontend/src/components/*.tsx` — many files
- `frontend/src/components/*.module.css` — many new files
- `frontend/src/styles/global.css` (new — replaces or co-exists with App.css)
- `frontend/src/main.tsx` — global.css import
- `frontend/src/App.css` — significantly slimmed down or removed

**Acceptance criteria:**

- Each existing component has its own colocated `.module.css` file (or has
  no styling that isn't via tokens or primitives — explicitly verified)
- Global styles live in one obvious place
- The app renders identically to before the refactor — no visual changes,
  just architectural
- Build and tests pass
- The codebase is easier to navigate: if a developer wants to find styles
  for `QueryBar`, they look at `QueryBar.module.css`, not search through
  `App.css`

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm test`
- Manual: visually verify the app looks identical to before

**Reference docs to consult:**

- Vite's CSS modules documentation
- AGENTS.md frontend rules — keep frontend a thin presentation layer

---

## 6. `[ ]` Phase V1 retrospective and Phase V2 handoff

**Why:** Self-propagating final task. Captures learnings and drafts the next
queue.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals
- Document any "we didn't get to this" items that affect Phase V2's scope
  (e.g., if the inventory found token gaps that Phase V2 needs to address)
- Draft `phase_v2_work_queue.md` for the primitives library work, with
  concrete items at PR-size granularity
- The first item of phase_v2 should be a primitives inventory — what
  primitives exist or are implied by current code, what's needed for the
  full library
- Subsequent items should each build a primitive (or a small group of
  related primitives) with full acceptance criteria
- The final item of phase_v2 should be its own retrospective + draft of
  phase_v3
- Update `visual_foundation_plan.md` if any scope adjustments are needed
  based on V1 learnings

**Files likely touched:**

- `docs/planning/phase_v1_work_queue.md` — check this item, add retrospective
- `docs/planning/phase_v2_work_queue.md` (new)
- `docs/planning/visual_foundation_plan.md` (if scope change)

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, residuals
- `phase_v2_work_queue.md` exists with concrete items at PR-size granularity
- The final item of phase_v2 drafts phase_v3
- This item is checked off

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `visual_foundation_plan.md` — Phase V2 scope (primitives library)
- This file as the structural template for phase_v2

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase V1 is complete. The draft of
`phase_v2_work_queue.md` from item 6 is the handoff artifact.

If any item is skipped (`[-]`), note the reason inline so the reason
survives in git history.
