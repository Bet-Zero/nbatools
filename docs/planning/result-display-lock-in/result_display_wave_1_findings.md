# Result Display Lock-In Wave 1 Findings

## Summary

Wave 1 implemented shared frontend display rules only. The change stayed inside the result-display UI layer and did not modify backend query behavior.

Implemented:

- `ResultEnvelope` now separates conservative context/interpreted-as items from true caveats.
- `RawDetailToggle` supports custom open/closed labels.
- Shared detail-table helpers suppress duplicate raw/detail toggles when visible answer tables already cover the same row fields.
- `ResultTable` supports low-risk column sizing metadata and default readable minimum widths.
- Playoff round/result cells use readable unavailable labels for important semantic blanks.
- No-result primary copy humanizes backend column names such as `def_rating`.

Not implemented:

- Rolling-stretch dedupe.
- Comparison panel redesign.
- Game-log column expansion beyond source-key metadata needed for duplicate checks.
- Product/review row caps.

## Implementation Notes

### Context vs Caveats

`frontend/src/components/ResultEnvelope.tsx` now builds context items from existing metadata and conservatively reclassifies notice strings only when they are clearly query interpretation:

- `metadata.interpreted_as`, `interpretation`, and `disambiguation_note`
- `metadata.start_date` / `end_date`
- `metadata.start_season` / `end_season`
- metric hints such as `stat`, `metric`, `target_stat`, `target_metric`
- `metadata.applied_filters`
- caveat/note strings with safe context prefixes such as `filtered to`, `date window:`, `schedule-context filter:`, `clutch filter:`, and `head-to-head:`

Strings containing limitation language such as `not available`, `missing`, `excluded`, `partial`, `approx`, `degraded`, or `unsupported` remain caveats/notes.

### Raw/Detail Toggles

`frontend/src/components/results/primitives/detailTables.ts` adds shared source-key comparison helpers. Pattern components now use visible answer-table source keys before rendering same-row detail toggles.

Applied suppressions:

- `GameLogResult`: hides duplicate same-row game detail; shows `Show additional columns` if hidden fields exist.
- `StreakResult`: hides duplicate full streak detail.
- `RecordResult`: hides duplicate team-record summary/by-season detail.
- `PlayoffHistoryResult`: hides duplicate season/series/round detail where visible tables already cover the data.
- `ComparisonResult`: hides duplicate summary/metric details unless subject panels or metric tables omit additional fields.

### Table Sizing

`ResultTableColumn` now accepts:

- `sourceKeys`
- `minWidth`
- `width`
- `nowrap`

`ResultTable` also applies default minimum widths for rank, numeric, date/season, identity, record/result, metric, and streak columns. This keeps dense answer tables scrollable and reduces value crushing without changing each family layout.

### Semantic Missing Labels

`PlayoffHistoryResult` now renders `Round unavailable` and `Result unavailable` for important playoff round/result values that are unknown or unavailable. Ordinary optional numeric blanks still use the existing dash behavior.

### No-Result Copy

`NoResultDisplay` now maps backend column messages such as `Column 'def_rating' not available` to human-readable primary copy:

```txt
Defensive rating is not available in the current dataset.
```

Technical details remain available in the details section when supplied as notes/caveats.

## Validation

Passed:

- `cd frontend && npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts`
- `cd frontend && npm test -- UIComponents.test.tsx LayoutPrimitives.test.tsx`
- `cd frontend && npm run build`

## Fixture Review

The requested fixture IDs were not visually regenerated as an ID-targeted set. Current `/review` screenshot tooling captures all visible shape groups after a review run and does not expose an explicit fixture-ID selection workflow.

Manual review path:

1. Run the app and API locally.
2. Open `/review`.
3. Run the review sweep.
4. Turn off `Show one example per shape`.
5. Inspect fixture numbers `1, 11, 14, 31, 36, 44, 45, 51, 71, 76, 201, 229, 234, 236, 237, 238, 239, 247`.

## Remaining Risk

The context/caveat split is intentionally conservative and frontend-only. If backend commands continue putting normal query interpretation into `caveats` without recognizable prefixes, those strings will remain caveats until a first-class response contract is added.

The duplicate suppression helper depends on pattern-maintained `sourceKeys`. New answer-table columns should include `sourceKeys` when they represent renamed or composite row fields.

## Recommended Next Wave

Proceed to Wave 2 as planned. No Wave 1 blocker remains, but future family-specific rewrites should preserve the `sourceKeys` convention so duplicate detail suppression remains accurate.
