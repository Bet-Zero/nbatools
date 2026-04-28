# Phase V2 Primitives Inventory

> **Role:** reconnaissance and API-boundary record for Phase V2 of
> [`visual_foundation_plan.md`](./visual_foundation_plan.md). This document
> defines what the first design-system primitives should own before code
> extraction starts.

---

## Goal

Create a reusable `frontend/src/design-system/` library that captures repeated
visual patterns without moving query behavior, NBA-specific formatting, or API
knowledge into the design system.

The design-system primitives should be presentation-only. Existing feature
components remain responsible for data fetching, query routing, result-shape
interpretation, value formatting, and user workflow behavior.

---

## Surveyed Files

- `frontend/src/App.tsx`
- every `.tsx` component in `frontend/src/components/`
- colocated component CSS modules in `frontend/src/components/`
- `frontend/src/App.module.css`
- `frontend/src/styles/global.css`
- `frontend/src/styles/tokens.css`

Phase V1 already moved frontend styles to tokens and CSS modules. Phase V2 can
therefore extract primitives from repeated token-driven patterns rather than
first fixing raw visual values.

---

## Existing Component Coverage

| File | Current role | Reusable patterns observed | Boundary decision |
| --- | --- | --- | --- |
| `frontend/src/App.tsx` | App orchestration, shell, query execution, saved-query workflow | page shell, header/status indicator, result action row | Keep state, API calls, URL sync, and query workflow in `App`; move repeated action-button styling to `Button`; app shell layout belongs to Phase V3. |
| `frontend/src/components/QueryBar.tsx` | Natural-language query form | primary submit button, clear icon button, recessed input | Query form behavior stays feature-specific; `Button`/`IconButton` should render controls. Input primitive is deferred until repeated form extraction is justified. |
| `frontend/src/components/SampleQueries.tsx` | Sample query chips | chip-like secondary buttons, compact uppercase label | Sample list and query strings stay feature-specific; chip buttons should use `Button` or future `Badge` only for presentation. |
| `frontend/src/components/EmptyState.tsx` | First-run empty state | centered state panel, tip chips | Copy and sample tips stay feature-specific; Phase V2 can reuse `Card`, `Badge`, and later `Skeleton`/state styling patterns. Full first-run redesign belongs to Part 3. |
| `frontend/src/components/Loading.tsx` | Loading indicator | spinner and loading message | Current behavior stays; Phase V2 item 5 should replace the ad hoc spinner with `Skeleton` primitives. |
| `frontend/src/components/ErrorBox.tsx` | Top-level error message | danger callout surface | Message ownership stays feature-specific; surface can later compose `Card` plus `Badge`/status styling. |
| `frontend/src/components/NoResultDisplay.tsx` | No-result and unsupported/error result state | centered card, status icon, suggestions list | Reason mapping and suggestions stay feature-specific; surface and status treatment can use `Card`/`Badge`. Designed no-result copy polish belongs to Part 3. |
| `frontend/src/components/FreshnessStatus.tsx` | Fetches and renders data freshness | collapsible card, status badge, rows, status dots | Fetching and freshness semantics stay here; status badge should migrate to `Badge`, surface to `Card`, and toggle button to `Button`/native details pattern later. |
| `frontend/src/components/ResultEnvelope.tsx` | Renders response envelope metadata | card shell, status badge, route pills, context chips, info blocks, alternate buttons | Data-to-chip construction and response semantics stay here; `ResultEnvelopeShell`, `Badge`, `Card`, and `Button` should own layout/control styling only. |
| `frontend/src/components/ResultSections.tsx` | Dispatches result sections by `query_class` | fallback section shell and title | Query-class dispatch stays feature-specific; fallback section shell should use `SectionHeader` and the feature table wrapper. |
| `frontend/src/components/DataTable.tsx` | Renders result rows and formats values | table shell, rank/entity/numeric styling, highlight rows | Split into generic design-system `DataTable` plus this NBA-specific wrapper. Header/value formatting, entity-column detection, and highlight decisions stay outside the design system. |
| `frontend/src/components/SummarySection.tsx` | Summary and by-season result sections | repeated section shell/header + table | Keep section selection here; move repeated shell/title to `SectionHeader`/`Card` and table presentation to the split table primitive. |
| `frontend/src/components/ComparisonSection.tsx` | Player comparison sections | repeated section shell/header + highlighted table | Same as `SummarySection`; comparison-specific labels and highlight choice stay feature-specific. |
| `frontend/src/components/SplitSummarySection.tsx` | Split summary sections | repeated section shell/header + highlighted table | Same as `SummarySection`; split-specific labels stay feature-specific. |
| `frontend/src/components/FinderSection.tsx` | Matching-games section | repeated section shell/header, count label, table | Count text and section selection stay feature-specific; use `SectionHeader` for title/count layout. |
| `frontend/src/components/LeaderboardSection.tsx` | Leaderboard section | repeated section shell/header, count label, highlighted table | Count text and highlight choice stay feature-specific; use shared section/table primitives. |
| `frontend/src/components/StreakSection.tsx` | Streak section | repeated section shell/header, count label, highlighted table | Count text and highlight choice stay feature-specific; use shared section/table primitives. |
| `frontend/src/components/CopyButton.tsx` | Clipboard action with fallback | secondary/share button visual state | Clipboard behavior stays here; render through `Button` while preserving copied state, titles, and fallback copy behavior. |
| `frontend/src/components/RawJsonToggle.tsx` | Developer raw JSON toggle | secondary button, recessed code block | Toggle state and JSON rendering stay here; button should use `Button`; code block styling may remain feature-specific unless repeated. |
| `frontend/src/components/QueryHistory.tsx` | In-session query history | list section header, status dots, badges, row action buttons | Time formatting and history actions stay feature-specific; buttons/badges should migrate to primitives. List-row primitive is deferred until saved/history lists are redesigned together. |
| `frontend/src/components/SavedQueries.tsx` | Saved-query management | list section header, action buttons, tag chips, route badges, empty state, rows | Saved-query state, import/export, and tag filtering stay here; buttons/badges/cards can migrate. Dedicated list-row and form primitives are deferred. |
| `frontend/src/components/SaveQueryDialog.tsx` | Save/edit modal form | modal surface, inputs, checkbox, primary/secondary buttons | Dialog workflow and form validation stay here; buttons can migrate now. Modal, input, checkbox primitives are deferred until form surfaces repeat outside saved queries. |
| `frontend/src/components/DevTools.tsx` | Structured-query development panel | details panel, select/textarea, submit button | Dev-only behavior stays here; submit button can migrate. Form/input primitives are deferred. |

Every component in `frontend/src/components/` is represented above.

---

## Repeated Pattern Inventory

| Pattern | Current locations | Proposed primitive owner | Decision |
| --- | --- | --- | --- |
| Standard buttons | `QueryBar`, `CopyButton`, `RawJsonToggle`, `SavedQueries`, `QueryHistory`, `SaveQueryDialog`, `DevTools`, `App` result actions, `ResultEnvelope` alternates, `SampleQueries` | `frontend/src/design-system/Button.tsx` | Design-system primitive owns variants, size, disabled/loading visuals, and accessible icon-only rendering. Feature components own click behavior and labels. |
| Card/panel surfaces | `ResultEnvelope`, `FreshnessStatus`, `NoResultDisplay`, `ErrorBox`, `SaveQueryDialog`, table blocks, saved/history hover rows | `frontend/src/design-system/Card.tsx` | Primitive owns depth, border, padding, radius, and optional semantic tone. Feature wrappers own data and copy. |
| Section headers | all `*Section.tsx`, `SavedQueries`, `QueryHistory`, `SampleQueries` label | `frontend/src/design-system/SectionHeader.tsx` | Primitive owns title/count/action layout. Feature wrappers own section labels, count text, and which actions appear. |
| Status/context badges and chips | `ResultEnvelope`, `FreshnessStatus`, `SavedQueries`, `QueryHistory`, `EmptyState` tips | `frontend/src/design-system/Badge.tsx` | Primitive owns neutral/accent/status/win/loss variants. Feature wrappers own semantic mapping from engine/API values. |
| Numeric stat treatment | current tables only; future summary/hero cards | `frontend/src/design-system/Stat.tsx` and `StatBlock.tsx` | Primitive renders provided label/value/context with mono numeric styling. It must never calculate NBA metrics. |
| Tables | `DataTable` and every result section | `frontend/src/design-system/DataTable.tsx` plus existing `frontend/src/components/DataTable.tsx` wrapper | Generic table primitive owns table layout only. NBA-specific header/value formatting and entity detection stay in the wrapper. |
| Loading placeholders | `Loading` | `frontend/src/design-system/Skeleton.tsx` | Primitive owns skeleton blocks/text and restrained motion. Feature wrapper owns loading copy and placement. |
| Player/team identity | result metadata chips, table entity columns, saved/history references by text | `frontend/src/design-system/Avatar.tsx` and `TeamBadge.tsx` | Phase V2 builds fallback-only identity primitives. Real player image and logo source integration stays in Phase V4. |
| Result envelope layout | `ResultEnvelope` | `frontend/src/design-system/ResultEnvelopeShell.tsx` | Primitive owns surface and slot layout. Feature component owns response metadata, notes, caveats, alternates, and freshness semantics. |
| Inputs and form fields | `QueryBar`, `SaveQueryDialog`, `DevTools` | Later phase | Defer until form-control duplication expands. Query parsing, validation, and structured JSON handling stay feature-specific. |
| Modal/dialog | `SaveQueryDialog` | Later phase | Defer until another modal exists. Current dialog behavior remains feature-specific. |
| List rows | `SavedQueries`, `QueryHistory` | Later phase | Defer until saved/history experience is redesigned; current row behavior is workflow-specific. |

---

## Proposed Primitive APIs

These sketches are intentionally small. They define ownership boundaries for
implementation items, not final exhaustive TypeScript interfaces.

### Button and IconButton

**Owner path:** `frontend/src/design-system/Button.tsx`
**Styles:** `frontend/src/design-system/Button.module.css`

```ts
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
}

interface IconButtonProps
  extends Omit<ButtonProps, "children"> {
  "aria-label": string;
  icon: React.ReactNode;
}
```

**Design-system owns:** tokenized color, radius, spacing, hover/focus,
disabled, loading visuals, size, and icon-only accessible structure.

**Feature wrappers own:** submit/click behavior, labels, clipboard behavior,
alternate-query behavior, query clearing, import/export, and route execution.

### Card

**Owner path:** `frontend/src/design-system/Card.tsx`
**Styles:** `frontend/src/design-system/Card.module.css`

```ts
type CardDepth = "elevated" | "card" | "input";
type CardPadding = "none" | "sm" | "md" | "lg";
type CardTone = "neutral" | "danger" | "warning" | "success";

interface CardProps extends React.HTMLAttributes<HTMLElement> {
  as?: React.ElementType;
  depth?: CardDepth;
  padding?: CardPadding;
  tone?: CardTone;
  children: React.ReactNode;
}
```

**Design-system owns:** background depth, borders, radii, shadows, padding, and
optional UI/system tone.

**Feature wrappers own:** result metadata, freshness fetching, error strings,
saved-query behavior, and any team-context resolution.

### SectionHeader

**Owner path:** `frontend/src/design-system/SectionHeader.tsx`
**Styles:** `frontend/src/design-system/SectionHeader.module.css`

```ts
interface SectionHeaderProps {
  title: React.ReactNode;
  eyebrow?: React.ReactNode;
  count?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}
```

**Design-system owns:** title/count/action alignment, uppercase treatment,
spacing, divider styling, and responsive wrapping.

**Feature wrappers own:** section names such as `Leaderboard`, `Matching
Games`, result counts, and which action buttons are available.

### ResultEnvelopeShell

**Owner path:** `frontend/src/design-system/ResultEnvelopeShell.tsx`
**Styles:** `frontend/src/design-system/ResultEnvelopeShell.module.css`

```ts
interface ResultEnvelopeShellProps {
  meta?: React.ReactNode;
  query?: React.ReactNode;
  context?: React.ReactNode;
  notices?: React.ReactNode;
  alternates?: React.ReactNode;
  children?: React.ReactNode;
}
```

**Design-system owns:** result-envelope card layout, row spacing, separators,
and responsive wrapping.

**Feature wrappers own:** status labels, route labels, freshness copy,
context-chip construction from metadata, notes, caveats, and alternate-query
button behavior.

### Badge

**Owner path:** `frontend/src/design-system/Badge.tsx`
**Styles:** `frontend/src/design-system/Badge.module.css`

```ts
type BadgeVariant =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "win"
  | "loss";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  uppercase?: boolean;
  children: React.ReactNode;
}
```

**Design-system owns:** chip shape, tokenized color semantics, typography,
spacing, and compact variants.

**Feature wrappers own:** mapping `result_status`, freshness status, route
names, saved-query tags, and query classes to badge variants.

### Stat and StatBlock

**Owner paths:**

- `frontend/src/design-system/Stat.tsx`
- `frontend/src/design-system/StatBlock.tsx`

**Styles:** colocated CSS modules.

```ts
interface StatProps {
  label: React.ReactNode;
  value: React.ReactNode;
  context?: React.ReactNode;
  semantic?: "neutral" | "accent" | "success" | "warning" | "danger" | "win" | "loss";
  size?: "md" | "hero";
}

interface StatBlockProps {
  stats: StatProps[];
  columns?: 1 | 2 | 3 | 4;
}
```

**Design-system owns:** mono/tabular numeric presentation, label hierarchy,
compact/hero sizing, and layout.

**Feature wrappers own:** which metrics appear, all NBA calculations, metric
ordering, query-class-specific context, and trend interpretation.

### Skeleton

**Owner path:** `frontend/src/design-system/Skeleton.tsx`
**Styles:** `frontend/src/design-system/Skeleton.module.css`

```ts
interface SkeletonProps {
  width?: string;
  height?: string;
  radius?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

interface SkeletonTextProps {
  lines?: number;
  width?: string | string[];
}

interface SkeletonBlockProps {
  rows?: number;
}
```

**Design-system owns:** placeholder colors, radii, rhythm, and restrained
motion.

**Feature wrappers own:** loading message, where loading appears, and which
shape best approximates the upcoming content.

### Generic DataTable

**Owner path:** `frontend/src/design-system/DataTable.tsx`
**Styles:** `frontend/src/design-system/DataTable.module.css`

```ts
interface DataTableColumn<Row> {
  key: string;
  header: React.ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
  render: (row: Row, rowIndex: number) => React.ReactNode;
}

interface DataTableProps<Row> {
  columns: DataTableColumn<Row>[];
  rows: Row[];
  getRowKey?: (row: Row, rowIndex: number) => React.Key;
  highlight?: boolean;
  emptyState?: React.ReactNode;
}
```

**Design-system owns:** table scroll container, column alignment, header/body
styling, row dividers, hover/highlight visuals, and tabular numeric class
support when requested through column metadata.

**Feature wrapper owns:** `SectionRow` adaptation, `formatColHeader`,
`formatValue`, rank-column detection, entity-column detection, numeric-column
detection, and all NBA/query-result-specific decisions. The generic table
primitive must not own NBA-specific value formatting.

### Avatar

**Owner path:** `frontend/src/design-system/Avatar.tsx`
**Styles:** `frontend/src/design-system/Avatar.module.css`

```ts
interface AvatarProps {
  name: string;
  imageUrl?: string | null;
  size?: "sm" | "md" | "lg";
  unavailable?: boolean;
}
```

**Design-system owns:** circular image/fallback frame, initials fallback,
accessible labeling, and unavailable-image state.

**Feature wrappers own:** player identity resolution, image URL lookup, and
any headshot source selection. Real image plumbing remains Phase V4.

### TeamBadge

**Owner path:** `frontend/src/design-system/TeamBadge.tsx`
**Styles:** `frontend/src/design-system/TeamBadge.module.css`

```ts
interface TeamBadgeProps {
  abbreviation?: string;
  name?: string;
  logoUrl?: string | null;
  size?: "sm" | "md";
  showName?: boolean;
}
```

**Design-system owns:** fallback abbreviation badge, optional logo slot,
name/abbreviation layout, and `--team-primary` / `--team-secondary` styling
hooks.

**Feature wrappers own:** team lookup, logo URL lookup, color-map resolution,
and deciding whether a view has single-team context. Real logo integration
remains Phase V4.

---

## Extraction Order Notes

The Phase V2 queue order is still appropriate:

1. Buttons first because they appear across query, result, saved-query,
   history, dialog, and developer-tool surfaces.
2. Cards/section headers/envelope shell next because they reduce repeated
   layout before result redesign work begins.
3. Badge/stat primitives after shells because result metadata and future hero
   metrics need shared treatments.
4. Skeletons, table split, and identity fallbacks then close the foundation.

No extra primitive should be added during Phase V2 unless a queue item uncovers
repetition that blocks the listed primitives.

---

## Residual Risks and Deferrals

- Inputs, select, textarea, checkbox, modal, and list-row primitives are
  intentionally deferred. They exist today, but current duplication is not
  broad enough to justify expanding Phase V2 beyond its planned surface.
- `SavedQueries` and `QueryHistory` both contain list-row patterns, but their
  workflows differ enough that extracting a generic list primitive now could
  hide product decisions needed during later saved-query polish.
- `DataTable` is the highest-risk extraction because the existing component
  mixes presentation with NBA-specific formatting. The split should preserve
  the wrapper contract first, then move only generic table structure into the
  design system.
- Phase V2 identity primitives should be fallback-only. Adding player
  headshot, team logo, or color-source plumbing here would blur Phase V4's
  ownership.
- Current icons are text glyphs/emoji in a few places. Phase V2 can preserve
  existing labels and glyphs while building primitive slots; a dedicated icon
  pass belongs with later visual polish unless the button item needs a small
  accessible icon-only control.
- The primitives library must use `frontend/src/styles/tokens.css` and the
  locked design-system rules. It should not introduce raw visual values except
  documented structural exceptions such as 1px borders.

