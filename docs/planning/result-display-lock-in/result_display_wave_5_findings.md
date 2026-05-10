# Result Display Lock-In Wave 5 Findings

## Summary

Wave 5 locked the final no-result display families:

- Family 2 — Message No Result
- Family 3 — Guided No Result

The implementation stayed in the frontend display layer. Backend routing, query execution, and no-result result contracts were not changed.

## Implemented

### Message No Result

- Hard unsupported states continue to render without generic recovery suggestions.
- Metric/column failures now use human-first primary copy instead of backend column wording.
- Metric-unavailable states use a softer `Unavailable Metric` title when the raw backend reason is a generic unsupported result with a metric detail.
- Technical backend strings remain available in the secondary details section.

### Guided No Result

- Valid-empty date no-matches now explain the resolved date directly, for example:
  `No NBA games matched Apr 11, 2026.`
- Date no-matches use date-specific next steps rather than spelling fallback text.
- Unsupported recent defensive-rating team queries now classify as guided no-result when the response has safe recovery alternatives, without pretending defensive rating was answered.
- Hard unsupported results without safe alternatives remain Message No Result.

### Date/Range Formatting

- No-result copy formats single dates as `Apr 11, 2026`.
- Same-month ranges format as `Apr 1–12, 2026` in prose/UI text.
- Applied-filter date chips in the envelope also format raw ISO ranges into readable dates.
- Raw backend details are preserved in the details area when useful.

### Suggestion Generation

- Backend-provided `metadata.suggested_queries` still take priority.
- Frontend fallbacks are conservative:
  - date no-match: previous/next NBA game day guidance plus known supported season/week scoring queries
  - recent defensive rating unsupported: supported recent team-record query plus a named-team opponent-points threshold example
- Opponent FG% was not suggested because it was not verified as a safe supported defensive query.
- Generic spelling guidance is no longer shown for date no-matches.

### Details Handling

- No-result details now use the softer heading `Why this happened`.
- Top-level notes/caveats and metadata notes are deduped and shown as secondary details.
- Wave 1 context/caveat separation remains intact.

## Validation

Passed:

- `cd frontend && npm test -- UIComponents.test.tsx LayoutPrimitives.test.tsx resultShapes.test.ts`
- `cd frontend && npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts LayoutPrimitives.test.tsx UIComponents.test.tsx`
- `cd frontend && npm run build`

Fixture/API checks:

- Fixture 11 returned `season_leaders`, `no_result`, `no_match`, with `start_date=end_date=2026-04-11`.
- Fixture 14 returned `season_team_leaders`, `no_result`, `unsupported`, with `stat=def_rating` and `Last N games: 10`.

Visual checks:

- Headless Chrome rendered the built app for fixture 11 and fixture 14 through the local FastAPI server.
- Screenshots were captured to:
  - `/private/tmp/result_display_wave5_fixture_11.png`
  - `/private/tmp/result_display_wave5_fixture_14.png`
- Fixture 11 rendered readable date copy and no raw ISO date range in the visible result.
- Fixture 14 rendered readable primary copy; the raw `Column 'def_rating' not available` string remained only in `Why this happened`.

## Remaining Risk

- Previous/next NBA game day suggestions are intentionally phrased generally because the frontend does not receive the nearest actual game dates.
- Defensive-rating alternatives remain conservative. Broader defensive proxy guidance would be better with backend metadata naming verified supported alternatives.
- Metadata notes can still contain technical strings; Wave 5 keeps them secondary rather than removing them.

## Lock-In Status

All 19 reviewed result-display families are now implemented for the current lock-in scope. Remaining work is follow-up enrichment rather than a blocking family implementation gap.
