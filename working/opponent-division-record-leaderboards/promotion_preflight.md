# Opponent-Division Record Leaderboards Promotion Preflight

## Current Unsupported Boundary

No-subject opponent-division record phrasing currently preserves the closest
`team_record_leaderboard` route but returns an unsupported-filter no-result.
Examples:

- `record against Northwest Division teams`
- `best record against Atlantic Division teams`
- `team records vs Pacific Division`

Named-team regular-season opponent-division records are already promoted through
`team_record` for trusted `team_conference_membership` seasons. This promotion
extends the same trusted division-resolution contract to record leaderboards
only when the query has no named subject team and asks for a regular-season team
record ranking.

## Accepted Scope

- Route: `team_record_leaderboard`
- Result contract: existing `leaderboard` result section
- Season type: `Regular Season` only
- Data source: existing `team_conference_membership` contract with
  `coverage_trusted=1`
- Coverage: seasons where the division resolves to exactly 5 trusted teams and
  the opponent set is stable across the requested season/range
- Accepted examples:
  - `record against Northwest Division teams`
  - `best record against Atlantic Division teams`
  - `team records vs Pacific Division`

Execution resolves the requested division to opponent team abbreviations and
passes the list to the existing team-record leaderboard game filter. Missing,
untrusted, partial, or changing membership keeps the existing unsupported-data
response instead of returning an unfiltered leaderboard.

## Rejected Scope

These remain unsupported or no-result boundaries:

- named-team behavior outside the already promoted regular-season boundary
- playoff division record leaderboards
- no-subject division phrases that are not record leaderboards
- mixed conference-plus-division phrasing such as `Western Conference Pacific
  Division`
- geography phrasing such as `east coast teams`
- conference-finals or playoff-round phrasing that mentions a division
- historical seasons outside trusted `team_conference_membership` coverage

## Data Contract

No new data source is required. The feature depends on the existing
`team_conference_membership` contract:

- `season`
- `team_abbr`
- `conference`
- `division`
- `coverage_trusted`

The route requires exactly five trusted teams for the requested division in
each resolved season. Multi-season ranges are accepted only when the resolved
opponent team set is stable across the range.

## Parser And Routing

Parser support is limited to explicit opponent-division record phrasing:

- `against <division> Division [teams]`
- `vs <division> Division [teams]`
- `versus <division> Division [teams]`

The plural phrase `team records` is treated as record intent only for the
existing no-subject record-leaderboard route. The promotion must not broaden
generic `teams vs division` fragments into a supported answer.

## Raw QA And Tests

Promote the existing Raw QA guard for `record against Northwest Division teams`
to an `ok` leaderboard expectation and keep adjacent rejected cases for:

- historical coverage guard
- mixed conference-plus-division guard
- playoff division guard
- conference-finals division guard

Add parser/routing/query-service tests for accepted leaderboard phrasing and
preserve explicit rejected-boundary assertions.

## Frontend And Deployment

No frontend contract or renderer change is expected. The feature reuses the
existing `leaderboard` section and result envelope metadata. No new R2 object or
deployment data key is required.
