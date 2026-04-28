# Design System Reference

This document defines the locked visual foundation for nbatools product polish work.

## Design philosophy

The visual direction is analytical, calm, and considered.

- Analytical: the interface should read like a serious tool for comparing and evaluating performance, not a marketing splash page.
- Calm: a restrained neutral-gray base keeps large datasets legible and lowers visual noise.
- Considered: emphasis is intentional and sparse, so important moments are obvious when they appear.

The system intentionally avoids loud saturation across the entire screen. Most surfaces stay neutral, and emphasis appears only when a user action or key metric justifies it.

## Foundation files and contracts

- Token source: `frontend/src/styles/tokens.css`
- Team brand map: `frontend/src/styles/team-colors.json`
- Runtime theme hook for team context: `--team-primary`, `--team-secondary`

All new components in Part 2 and Part 3 should consume these foundations rather than introducing one-off values.

## Background depth system

The background stack uses four layers to communicate hierarchy without heavy borders everywhere.

1. Page background (`--bg-page`): the global canvas.
2. Elevated background (`--bg-elevated`): major containers and full-width sections sitting above the page.
3. Card background (`--bg-card`): cards, result panels, and modular content blocks.
4. Input/recessed background (`--bg-input`): controls and recessed zones that should feel inset.

Rationale:

- The four-layer model gives enough tonal range to establish depth in dense data views.
- It reduces the need for stronger borders and heavy shadow on every element.
- It supports both table-heavy and card-heavy layouts with the same visual grammar.

Guidance:

- Prefer changing layer depth before adding stronger borders.
- Avoid skipping layers arbitrarily; move one step at a time unless a section break needs stronger contrast.

## Border weight system

Use the border scale to communicate separation strength.

- Subtle (`--border-subtle`): soft internal separations and row dividers.
- Default (`--border-default`): standard card outlines and control boundaries.
- Strong (`--border-strong`): focused states, high-priority grouping edges, or places where layers are too close in value.

Usage guidance:

- Most components should use default borders.
- Use subtle borders for dense areas where strong outlines would create clutter.
- Reserve strong borders for explicit emphasis and interaction state, not baseline structure.

## Text hierarchy

- Primary text (`--text-primary`): key labels, values, and user-focus content.
- Secondary text (`--text-secondary`): supporting metadata and helper copy.
- Tertiary text (`--text-tertiary`): low-priority annotations and non-essential context.

Guidance:

- Do not use tertiary for core data values.
- Keep large data tables mostly primary + secondary; tertiary should be sparse.

## Accent color and restraint principle

Accent is warm orange:

- Base: `--accent`
- Hover: `--accent-hover`
- Muted wash: `--accent-muted`
- Glow/focus aid: `--accent-glow`

Restraint principle:

- Orange appears only on primary actions, hero stats, focus rings, and key highlights.
- Orange should not be applied to every button, label, and chip in the same view.
- If everything is highlighted, nothing is highlighted.

Practical rules:

- One primary CTA per zone can use full accent.
- Secondary actions should usually stay neutral.
- Focus rings can blend border + glow without turning full surfaces orange.

## Status colors

- Success (`--success`): successful actions, positive confirmations.
- Win (`--win`): game outcome win semantics.
- Danger (`--danger`): destructive actions and hard errors.
- Loss (`--loss`): game outcome loss semantics.
- Warning (`--warning`): cautionary states that still allow progression.
- Info (`--info`): neutral informational messaging.

Guidance:

- Use win/loss only for sports outcome semantics.
- Use success/danger for UI/system semantics.
- Do not overload warning as a substitute for missing emphasis design.

## Team color treatment principles

Team color is contextual and additive, not the global action system.

Where team colors should appear:

- thin accent stripe on team-context cards
- around team logos or badges
- subtle background wash in hero sections where a single team is the subject

Where team colors should not appear:

- buttons (buttons remain accent-orange per global action language)
- body text and paragraph copy
- dense data tables (avoid overwhelming scanability)
- multi-team contexts (for example, league leaderboards with many teams)

Application model:

- Resolve team context in UI logic.
- Read primary/secondary from `frontend/src/styles/team-colors.json`.
- Set `--team-primary` and `--team-secondary` on the component container via inline style or scoped custom property override.
- If no team context exists, allow defaults from tokens (`--team-primary: var(--accent)`, `--team-secondary: var(--text-secondary)`).

## Typography system

Typeface roles:

- Inter (`--font-sans`): all interface text, labels, controls, and narrative copy.
- JetBrains Mono (`--font-mono`): stat numerals, dense data values, and code-like technical snippets.

Why mono numerals matter:

- Tabular-width numeral rendering keeps columns visually aligned.
- Scanning adjacent rows is faster when digits occupy predictable horizontal space.
- It reduces perceived jitter in rapidly changing or comparison-heavy stat blocks.

## Type scale

Use the locked token scale for consistent hierarchy.

- Stat hero (`--font-stat-hero`, 56px): top-line signature metric on hero surfaces.
- Display (`--font-display`, 48px): major page-level or section-level showcases.
- H1 (`--font-h1`, 32px): primary section title.
- H2 (`--font-h2`, 24px): secondary heading and major card title.
- Stat md (`--font-stat-md`, 24px): important metrics in compact hero cards.
- H3 (`--font-h3`, 18px): tertiary heading and table block title.
- Body (`--font-body`, 15px): default reading and UI body text.
- Small (`--font-small`, 13px): metadata, helper copy, dense control labels.
- Micro (`--font-micro`, 11px): compact annotations only where necessary.

Weight and tracking:

- Use tokenized weights (`--weight-regular` through `--weight-bold`) instead of arbitrary values.
- Use `--tracking-display` or `--tracking-tight` for hero/display headings.
- Use `--tracking-uppercase` for compact uppercase labels.

## Spacing scale

Spacing is based on a 4px grid.

Tokens:

- `--space-1` (4px), `--space-2` (8px), `--space-3` (12px), `--space-4` (16px)
- `--space-5` (20px), `--space-6` (24px), `--space-8` (32px)
- `--space-10` (40px), `--space-12` (48px), `--space-16` (64px)

Principle:

- No layout decision should use an off-grid spacing value.
- If spacing feels wrong, choose a neighboring token instead of introducing custom numbers.

## Radii system

- Small (`--radius-sm`): compact controls and chips.
- Medium (`--radius-md`): standard cards and inputs.
- Large (`--radius-lg`): prominent cards and grouped containers.
- Extra large (`--radius-xl`): hero blocks or special callout surfaces.

Guidance:

- Keep radii progression predictable inside a view.
- Avoid mixing many radius sizes in one component tree.

## Shadow system

- Small (`--shadow-sm`): subtle lift for interactive controls.
- Medium (`--shadow-md`): standard elevated cards.
- Large (`--shadow-lg`): high-emphasis overlays or hero layers.

When to use shadows:

- Use shadows to communicate elevation changes or interaction affordance.
- Skip shadows when background depth layers already provide enough separation.
- Avoid combining strong borders, deep shadows, and high-contrast backgrounds on routine components.

## Component implementation checklist

Before marking a new component visually complete:

1. Uses token values only for color, spacing, typography, radii, motion, and elevation.
2. Uses text hierarchy intentionally (primary/secondary/tertiary roles are clear).
3. Uses accent sparingly and only for approved emphasis roles.
4. Applies team colors only in allowed contexts.
5. Uses on-grid spacing exclusively.
6. Keeps shadows and borders proportional to background depth.

This checklist is the minimum contract for "design-system compliant" implementation in Part 2 and beyond.