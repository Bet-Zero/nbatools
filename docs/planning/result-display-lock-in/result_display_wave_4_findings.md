# Result Display Lock-In Wave 4 Findings

## Summary

Wave 4 locked the remaining record, comparison, and playoff-history display families:

- Family 13 — Team Record
- Family 14 — Record By Decade
- Family 16 — Matchup By Decade
- Family 12 — Comparison Panels
- Family 9 — Playoff History
- Family 11 — Playoff Matchup History

The implementation stayed in the frontend result-display layer. No backend query execution or metadata contracts changed.

## Implemented

### Team Record

- Team-record heroes now preserve opponent-group filters from `metadata.applied_filters`.
- The playoff-team opponent group renders as `against {season} playoff teams` instead of `in the playoffs`.
- The one-row record table uses the locked required columns: `Team`, `W-L`, `Games`, `Win %`, `PPG`, `+/-`, `REB`, `AST`, and `3PM`.
- Optional context columns now use semantic labels such as `Season Type`, `Opponent Group`, `Season`, `Home/Away`, and `Opponent`.
- `Type` is no longer used as a vague label for team-record tables.

### Record By Decade

- The decade table keeps the locked team breakdown shape: `Decade`, `Seasons`, `W-L`, `Win %`, and `Games`.
- Record-by-decade aggregation notes now render as Context instead of Caveats.

### Matchup By Decade

- Matchup-by-decade tables now include total `Games` per decade, derived from the team record fields when no explicit game count is present.
- Hero copy includes regular-season/playoff game population and range when the payload exposes it through metadata or normal range notes.
- Matchup interpretation notes now render as Context instead of Caveats.

### Comparison Panels

- Comparison panels now use compact subject summaries instead of large stat dashboards.
- Recent-form player comparisons lead with performance averages instead of wins.
- The comparison table defaults to a focused primary metric set and puts deeper rows behind `Show more metrics`.
- A synthetic `Record` row is available when summary records exist.
- Metric direction handling now distinguishes higher-better, lower-better, and neutral metrics:
  - lower-better rows render copy such as `3 fewer losses`
  - neutral rows render `Difference`
  - win-percentage edge copy uses percentage points

### Playoff History

- Playoff-history heroes now use the locked historical sentence shape:
  `From {start} through {end}, the {team} made the playoffs {appearances} times and went {wins}-{losses}.`
- Season tables use `Round Reached` and continue to render readable unavailable labels instead of unexplained dashes.
- The pre-2001-02 round-data limitation renders with the locked caveat copy.
- Playoff-history aggregation notes now render as Context.

### Playoff Matchup History

- Matchup heroes now clarify game record and, when series rows are available, series record.
- Series tables always expose `Season`, `Round`, `Winner`, and `Series Result`.
- Winner and series result are derived from team-prefixed win/loss fields when explicit winner/result fields are missing.
- Series game counts are derived from series win/loss fields when no explicit game count is present.
- Matchup/range interpretation notes now render as Context.

## Validation

Passed:

- `npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts LayoutPrimitives.test.tsx`
- `npm run build`

Fixture/API checks:

- Fixture 45 returned `team_record` with opponent-quality metadata for `playoff teams`, 1 summary row, and a 6-5 record.
- Fixture 236 returned `record_by_decade` with 4 decade rows and a normal aggregation note.
- Fixture 238 returned `matchup_by_decade` with 4 comparison rows and range/context caveats.
- Fixture 239 returned `player_compare` with 2 summary rows, 20 metric rows, and a last-10-games filter.
- Fixture 229 returned `playoff_matchup_history` with 6 series rows and team-prefixed records suitable for winner/result derivation.
- Fixture 228 (`Lakers playoff history`) returned `playoff_history` with 21 season rows and the pre-2001-02 round-data caveat.

Visual note:

- Browser screenshot automation was not rerun as an ID-targeted set. Wave 4 validation used targeted renderer tests plus live query/API payload checks for the required fixtures.

## Remaining Risk

- Fixture 45 still carries backend `season_type: Playoffs` while also carrying the opponent-quality filter `playoff teams`. The renderer avoids presenting that as season type for this opponent-group query, but a future backend metadata field could make the distinction first-class.
- Playoff matchup winner/result derivation depends on team-abbreviation-prefixed fields such as `MIA_wins` and `NYK_wins`. If future payloads use a different prefix scheme, the frontend will need matching metadata or explicit winner/result fields.
- Playoff history still depends on available round labels. Unknown values render as `Round unavailable`.

## Recommended Next Wave

Proceed to Wave 5 as planned for Message No Result and Guided No Result behavior. Wave 4 does not need a blocking follow-up.
