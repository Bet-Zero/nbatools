# Shape Cleanup Report

Date: 2026-05-06

## Decisions Applied

### 1. Table Header Treatment: Option A

Result-table headers remain neutral by default, and only the primary measured metric column receives accent styling through `highlightColumnKey`.

Files:

- `frontend/src/components/results/primitives/ResultTable.module.css`
- `frontend/src/components/DataTable.module.css`

Notes:

- `ResultTable` already determines the highlighted metric through `highlightColumnKey`; this pass kept that contract and added an explicit neutral-header comment at the table primitive.
- The generic NBA `DataTable` wrapper already neutralizes the design-system table header for fallback/raw result tables; raw-table `highlight` remains row-level and is not treated as a metric-column highlight.

### 2. Raw-Detail Disclosure: Option A

`RawDetailToggle` was intentionally left as shipped by the primitive audit.

Files:

- No code changes.

### 3. Team-Context Hero Emphasis: Option B

Added a subtle single-team hero stripe driven by existing team color data. The hero remains on neutral design-system surfaces; only a thin left stripe and very light team wash are scoped to single-team contexts.

Files:

- `frontend/src/styles/tokens.css`
- `frontend/src/components/results/primitives/ResultHero.tsx`
- `frontend/src/components/results/primitives/ResultHero.module.css`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/components/results/patterns/SplitResult.tsx`
- `frontend/src/components/results/patterns/StreakResult.tsx`

Two-team choice:

- Two-team matchup/comparison heroes fall back to neutral. Rendering two competing stripes would add visual noise and undermine the single-subject identity rule.

## Cleanup Items

### A. Undefined Token References

Replaced the flagged undefined pattern tokens with valid design tokens.

Files:

- `frontend/src/components/results/patterns/ComparisonResult.module.css`
- `frontend/src/components/results/patterns/GameLogResult.module.css`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.module.css`
- `frontend/src/components/results/patterns/SplitResult.module.css`
- `frontend/src/components/results/patterns/StreakResult.module.css`

### B. Hardcoded Fallback Colors

Removed hardcoded fallback colors from pattern CSS and used existing status tokens directly.

Files:

- `frontend/src/components/results/patterns/ComparisonResult.module.css`
- `frontend/src/components/results/patterns/StreakResult.module.css`

### C. Off-Grid Spacing

Replaced the flagged `gap: 1px` stat-chip spacing by moving comparison stats to the design-system `Stat` primitive.

Files:

- `frontend/src/components/results/patterns/ComparisonResult.module.css`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`

### D. Duplicated Badge / Stat Treatments

Consolidated local repeated chip/card treatments onto design-system primitives where appropriate.

Files:

- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.module.css`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.module.css`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.module.css`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/components/results/patterns/RecordResult.module.css`
- `frontend/src/components/results/patterns/SplitResult.tsx`
- `frontend/src/components/results/patterns/SplitResult.module.css`
- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/components/results/patterns/StreakResult.module.css`

Changes:

- Comparison subject panels now use `Card`; their stat chips now use `Stat`; participant index and `vs` labels now use `Badge`.
- Game-log summary strip now uses `Stat`.
- Split edge chips now use `Badge`.
- Streak status pills now use `Badge`.
- Playoff and record matchup `vs` labels now use `Badge`.

## New Design-System Surface

Tokens:

- `--team-accent`
- `--team-accent-muted`

Primitive prop:

- `ResultHero.teamAccentAbbr?: string | null`

No new design-system components were added.

## Test And Build Status

`npm test`

```text
> frontend@0.0.0 test
> vitest run --no-file-parallelism

 RUN  v4.1.4 /Users/brenthibbitts/nba_tools/frontend

 Test Files  16 passed (16)
      Tests  221 passed (221)
   Start at  05:57:33
   Duration  124.63s (transform 2.30s, setup 5.85s, import 11.54s, tests 30.64s, environment 64.74s)
```

`npm run build`

```text
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.0.8 building client environment for production...
transforming...✓ 113 modules transformed.
rendering chunks...
computing gzip size...
../src/nbatools/ui/dist/index.html                   0.77 kB │ gzip:  0.41 kB
../src/nbatools/ui/dist/assets/index-qQHs2xRm.css   63.57 kB │ gzip: 10.81 kB
../src/nbatools/ui/dist/assets/index-BiSkJeus.js   330.31 kB │ gzip: 98.73 kB

✓ built in 1.10s
```

## Intentionally Not Fixed

- `RawDetailToggle` disclosure copy remains text-based because decision 2 selected Option A.
- Pattern-level fixed max-width values such as `16rem` remain because they are layout constraints, not the flagged off-grid spacing issue.
- The design-system `DataTable` still has its own default accent header; the result-specific NBA wrapper neutralizes it for renderer use, and a global design-system variant was outside this visual cleanup pass.
