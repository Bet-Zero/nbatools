# Primitive Audit Report

Date: 2026-05-06

Scope:

- Read `frontend/src/design-system/` and `frontend/src/styles/tokens.css` as the visual source of truth.
- Walked imports under `frontend/src/components/results/patterns/` and confirmed the shared renderer surface: `ResultHero`, `ResultTable`, `EntityIdentity`, `RawDetailToggle`, `DataTable`, `NoResultDisplay`, `ResultEnvelope`, and `ResultShell`.
- Did not modify files under `frontend/src/components/results/patterns/`.

## Primitives Touched

- `ResultHero`: now renders through the design-system `Card`, uses tokenized neutral surfaces, removes team-color hero washes, and limits accent/cool tones to a narrow left rule plus a very subtle wash.
- `ResultTable`: moved to neutral card/table layers, tokenized table typography, kept text in Inter, moved numeric cells to JetBrains Mono, and fixed the undefined `--surface-base` / `--font-xs` usage.
- `EntityIdentity`: replaced undefined font tokens, standardized Inter identity text, tightened secondary labels, and kept team color isolated inside the `TeamBadge` mark.
- `RawDetailToggle`: kept the semantic `h3`, added a tokenized row count, and aligned spacing/borders/typography with the section-header treatment without changing props.
- `DataTable`: added an NBA wrapper override so generic result rows use Inter for text and JetBrains Mono only for numeric/rank cells; neutralized rank/sticky-header accent overuse.
- `NoResultDisplay`: replaced undefined text tokens, normalized label tracking/typography, removed the orange-warning mixed ambiguous stripe, and moved suggestion cards to neutral design-system surfaces.
- `ResultEnvelope`: route/query-class badges now use neutral badges, alternate suggestions use standard secondary buttons, and notes/caveats use tokenized inset emphasis instead of hardcoded border widths.

## Audited Without Code Change

- `ResultShell`: already used tokenized width and spacing only; no API or visual change was needed.

## Design System Gaps

- `DataTable` in the design system applies JetBrains Mono to the whole table and orange header treatment by default. Result views need text cells in Inter and numeric cells in JetBrains Mono, so the NBA wrapper now overrides that locally.
- There is no design-system `ResultTable` primitive with footer rows, highlighted metric columns, and result-specific table semantics. The result renderer still needs its custom `ResultTable`.
- `SectionHeader` has no heading-level or `as` support. `RawDetailToggle` kept a local `h3` instead of adopting `SectionHeader` directly.
- There is no token for readable text measure or entity-name clamp width. `EntityIdentity` uses token math for its max width, but a named token would be clearer.

## Punted Decisions

- Result-table header treatment:
  1. Keep neutral headers with accent only on highlighted metric columns.
  2. Update the design-system `DataTable` to support a neutral header variant.
  3. Make all tables use the current accent header treatment and accept heavier orange presence.

- Raw-detail disclosure action:
  1. Keep text buttons, which are clear and preserve the current API.
  2. Add a design-system disclosure icon/button pattern, then migrate raw detail toggles.
  3. Replace raw drawers with always-visible detail sections for result shapes where details are core content.

- Team-context hero emphasis:
  1. Keep team colors only in `TeamBadge` / identity blocks, as this pass now does.
  2. Add a design-system-approved team-context stripe that is explicitly scoped and not global accent.
  3. Let shape patterns render a separate team-context metadata chip instead of tinting hero surfaces.

## Next Steps

- Shape-level CSS under `frontend/src/components/results/patterns/` still contains undefined `--font-xs`, hardcoded fallback colors, and one off-grid `gap: 1px`; those were not changed because this pass was primitives-only.
- Several pattern-level stat chips and subject panels duplicate badge/stat treatments. A follow-up shape pass should consolidate those with the design-system `Badge`, `Stat`, or a new approved comparison-chip primitive.
- Some patterns still choose `tone="team"` for heroes. The primitive now intentionally renders that as a neutral hero, but a shape-level pass should decide whether those routes need a separate team-context affordance.

## Verification

- `npm test -- DataTable.test.tsx RawDetailToggle.test.tsx UIComponents.test.tsx LayoutPrimitives.test.tsx ResultRenderer.test.tsx` passed: 5 files, 85 tests.
- `npm test` passed: 16 files, 221 tests.
- `npm run build` passed.
