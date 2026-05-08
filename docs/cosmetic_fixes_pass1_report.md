# Cosmetic Fixes Pass 1 Report

Date: 2026-05-08

## Scope

This pass applied the three screenshot-driven cosmetic fixes requested for the `/review` surface:

- chip text no longer wraps mid-word in result metadata and filter tags
- average-style numeric values now render to one decimal place
- game-log style dates now use compact display formatting instead of raw timestamp-like strings

## Files Touched Per Pattern

### Pattern A — Chip text wrapping

- `frontend/src/components/ResultEnvelope.module.css`
- `frontend/src/design-system/TeamBadge.module.css`

### Pattern B — Decimal precision on averages

- `frontend/src/components/tableFormatting.ts`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`

### Pattern C — Date formatting in game logs

- `frontend/src/components/tableFormatting.ts`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`

### Validation-related test updates

- `frontend/src/test/ResultRenderer.test.tsx`
- `frontend/src/test/FirstRun.test.tsx`

## Formatter Utility Used

The pass extended the existing shared formatter utility in `frontend/src/components/tableFormatting.ts` instead of introducing new primitives.

Added/shared helpers:

- `formatValue()` for general cell and metric rendering
- `formatAverageValue()` for contexts where raw stat keys represent averaged values
- `formatCompactDate()` for `Mar 10`-style game-log dates
- `formatLongDateRange()` for metadata date ranges that need timestamp stripping with year context

Underlying platform formatters used:

- `Intl.NumberFormat` for integer and one-decimal numeric output
- `Intl.DateTimeFormat` for compact and long date display

## Behavior Notes

- Result-envelope route tags, filter chips, and alternate-action chips now keep each chip on a single line and wrap only between chips.
- `TeamBadge` was also hardened with `white-space: nowrap` so the remaining chip-like primitive matches the same non-wrapping behavior.
- Team `game_summary` stat panels no longer render the meaningless `MIN` box.
- Average footer rows in game-log tables now use explicit average formatting even when the raw stat key is reused (for example `PTS`, `REB`, `AST`, `MIN`).
- Comparison metadata date ranges now strip timestamp suffixes via the shared long-date formatter.

## Test / Rendering Follow-up

- Renderer tests that expected raw ISO-style dates were updated to the new compact `Mar 1` / `Jan 2` display.
- One comparison/split expectation moved from whole-number text to one-decimal text (`Home +8.0 PPG`) after the average formatter became consistent across shapes.
- Two App-level interaction tests in `FirstRun.test.tsx` remained behaviorally correct but exceeded Vitest's default 5s timeout under the full-suite load on this machine. Those two tests were raised to a 10s timeout after isolated confirmation that they pass functionally.
- A full-page badge audit on `/review` found no multiline chip labels after the CSS changes. One internal team-logo mark node still appeared in the generic badge selector because it shares a badge-like class name, so the `TeamBadge` root was explicitly pinned to `white-space: nowrap` as a final hardening step.

## Verification

Frontend validation completed:

- `cd frontend && npm test` -> passed (`240` tests)
- `cd frontend && npm run build` -> passed
- `cd frontend && npm test -- --run src/test/LayoutPrimitives.test.tsx` -> passed (`15` tests) after the final `TeamBadge` tweak

Visual verification completed on `/review` once all `19` visible shape groups were loaded.

Spot-checked representative shapes:

- Player Game Log
- Team Record
- Game Summary Log
- Top Performances
- Comparison Panels
- Rolling Stretch

Observed results:

- no chip labels broke mid-word in the loaded review groups
- average-style values rendered to one decimal place (`103.8`, `43.1`, `21.7`, `105.7`, `45.3`, `35.2`)
- game-log and single-game date columns rendered without timestamp suffixes (`Apr 12`, `Mar 10`, `Mar 16`)
- team `game_summary` stat panels omitted the `MIN` box as intended

Backend validation:

- `make test-preflight` -> passed with exit code `0` (`2601` passed, `1` xpassed, `355` warnings, `22m22s`)
