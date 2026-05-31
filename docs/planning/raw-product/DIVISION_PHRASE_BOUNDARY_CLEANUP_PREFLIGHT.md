# Division Phrase Boundary Cleanup Preflight

Discovery date: 2026-05-21

Scope: documentation-only preflight for the known product-boundary issue where
NBA division opponent phrasing broad-falls back to ordinary record answers. This
preflight does not change production code, parser/routing behavior, backend
behavior, frontend behavior, result contracts, tests, QA corpus expectations, or
division support.

Post-cleanup status: the behavior wave is complete. Division opponent phrasing
now returns a guarded unsupported response with
`metadata.unsupported_filters == ["opponent_division"]`; the broad-fallback
issue documented by this preflight is resolved. Division support was not added.

## Executive Summary

Division-opponent phrasing remains unsupported by product policy. The current
parser does not detect NBA division names as a guarded boundary, so the division
phrase is ignored unless another existing boundary wins first.

Observed current behavior:

- named-team regular-season division phrases return unfiltered `team_record`
  `ok` answers with `summary` and `by_season` sections
- no-subject division phrases such as `record against Northwest Division teams`
  return an unfiltered `team_record_leaderboard` `ok` answer
- mixed conference-plus-division phrases such as `Lakers record against Western
  Conference Pacific Division teams` return a supported conference-filtered
  `team_record` `ok` answer while ignoring the narrower division phrase
- explicit `conference finals` record phrasing still routes through the existing
  single-team playoff-round unsupported boundary
- playoff division phrasing without a round, such as `Celtics playoff record vs
  Atlantic Division`, broad-falls back to a playoff `team_record` `ok` answer

Recommended cleanup: add a guarded unsupported division boundary, not division
support. Division requests should return `no_result` /
`filter_not_supported`, empty sections, and
`metadata.unsupported_filters == ["opponent_division"]`. This belongs adjacent
to opponent-conference routing because the phrasing is opponent-filter-like, but
it should use a separate unsupported filter id so division requests are not
misreported as conference geography or conference coverage failures.

Completed cleanup evidence is recorded in
`docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`.
The validation set passed targeted snapshot tests, parser/query slices, raw QA
route-priority and product-boundary slices, `test-preflight`, and
`git diff --check`.

## Inputs Inspected

Required inputs:

- `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md`
- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `docs/operations/parser_routing_growth_guardrails.md`
- `docs/operations/feature_promotion_rules.md`
- `src/nbatools/commands/natural_query.py`
- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_natural_query_unsupported_boundary_snapshots.py`
- `qa/raw_query_answer_corpus.yaml`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

Additional code read:

- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/query_service.py`
- `qa/harness_slices/natural_query_route_priority.yaml`
- `qa/harness_slices/product_boundaries.yaml`

Read-only verification performed:

- `parse_query()` probes for division, conference-plus-division, playoff, and
  conference-finals phrases
- `execute_natural_query()` probes for route, status, reason, sections, notes,
  and `metadata.unsupported_filters`

## Current Policy Boundary

The policy docs already describe division phrasing as guarded and unsupported:

- `PARSER_ROUTING_GROWTH_GUARDRAILS.md` lists `vs Atlantic Division` as a
  rejected/guarded phrase for the opponent-conference team-record family.
- `FEATURE_PROMOTION_RULES.md` uses the opponent-conference promotion as the
  worked example and names division filters as rejected phrasing.
- `query_catalog.md` and `query_guide.md` say division requests remain
  unsupported and should return `no_result` / `filter_not_supported` instead of
  broad full-season records.
- `NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md` records division filters near
  opponent-conference phrasing as not promoted as supported, with expected
  unsupported behavior and no broad team-record fallback.
- `NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md` and the snapshot coverage
  return package call out `Celtics record vs Atlantic Division` as a known
  cleanup candidate, not a behavior to lock in.

Conclusion: divisions remain unsupported. This cleanup should align
implementation with documented policy. It should not add division filtering,
division membership resolution, new data requirements, frontend behavior, or
new result sections.

## Current Behavior Probes

The table below records current behavior as of this preflight. `sections`
summarizes the non-empty section names and row counts returned by
`QueryResult.to_dict()`.

| Query | Current parsed route | Current result | Unsupported filters | Sections | Notes |
| --- | --- | --- | --- | --- | --- |
| `Celtics record vs Atlantic Division` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | Division phrase ignored. |
| `Lakers record against Pacific Division` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | Division phrase ignored. |
| `Knicks record vs Central Division` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | Division phrase ignored. |
| `record against Northwest Division teams` | `team_record_leaderboard` | `ok` | none | `leaderboard: 10` | Division phrase ignored and widened to league record leaderboard. |
| `Celtics record vs Atlantic Division teams` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | `teams` suffix does not help. |
| `Celtics record vs the Atlantic Division` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | Optional `the` does not help. |
| `Celtics playoff record vs Atlantic Division` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | Playoff season type is retained, but division is ignored. |
| `Lakers record against Pacific Division in playoffs` | `team_record` | `ok` | none | `summary: 1`, `by_season: 1` | Playoff season type is retained, but division is ignored. |
| `Celtics conference finals record vs Atlantic Division` | `playoff_history` | `no_result` / `filter_not_supported` | `single_team_playoff_round_record` | none | Existing conference-finals boundary wins. |
| `Celtics record vs Atlantic Division in conference finals` | `playoff_history` | `no_result` / `filter_not_supported` | `single_team_playoff_round_record` | none | Existing conference-finals boundary wins. |

Mixed conference-plus-division probes showed a second fallback risk:

| Query | Current parsed route | Current opponent conference | Current result | Unsupported filters | Sections |
| --- | --- | --- | --- | --- | --- |
| `Celtics record against Eastern Conference Atlantic Division teams` | `team_record` | `East` | `ok` | none | `summary: 1`, `by_season: 1` |
| `Lakers record against Western Conference Pacific Division teams` | `team_record` | `West` | `ok` | none | `summary: 1`, `by_season: 1` |
| `Nuggets record against Western Conference Northwest Division teams` | `team_record` | `West` | `ok` | none | `summary: 1`, `by_season: 1` |
| `Heat record against Eastern Conference Southeast Division teams` | `team_record` | `East` | `ok` | none | `summary: 1`, `by_season: 1` |
| `Celtics record against the East Atlantic Division` | `team_record` | `East` | `ok` | none | `summary: 1`, `by_season: 1` |
| `Lakers record against the West Pacific Division` | `team_record` | `West` | `ok` | none | `summary: 1`, `by_season: 1` |

These answers are not merely unfiltered fallback. They can also be
conference-filtered fallback that ignores the narrower division phrase.

## Expected Product Boundary

Recommended boundary contract:

| Area | Recommendation |
| --- | --- |
| Product support | NBA opponent-division filters remain unsupported. Do not add division support in this cleanup. |
| Route family | Use the closest existing record route for clean unsupported responses: `team_record` for single-team record phrasing and `team_record_leaderboard` for no-subject league record phrasing. |
| Result status | `no_result`. |
| Result reason | `filter_not_supported`. |
| Sections | `{}`. No `summary`, `by_season`, `leaderboard`, or finder rows. |
| Unsupported filter id | `opponent_division`. |
| Parser note | Include an `unsupported_boundary` note such as `unsupported_boundary: opponent-division filters are not supported yet`. |
| Metadata | `metadata.unsupported_filters == ["opponent_division"]`. Do not expose an applied `opponent_conference` or resolved opponent list for mixed conference-plus-division unsupported cases. |
| Data contract | No new data contract in this cleanup. The existing conference-membership data has a `division` column, but using it would be a separate feature promotion. |
| Frontend/API contract | No new frontend behavior or response shape. Existing no-result rendering should handle the unsupported response. |

Use `opponent_division` rather than `opponent_conference` for division
phrases. The boundary is opponent-conference-adjacent for route priority and
test placement, but a separate filter id is clearer because:

- the user requested a division, not a conference
- `opponent_conference` already covers east/west geography phrases and
  unsupported conference route variants
- `conference_coverage` already covers missing trusted conference membership
  for supported conference filters
- a separate id makes future division support or promotion easier to audit
- mixed conference-plus-division phrases should not be allowed to pass as
  conference-only answers

### Expected Case Matrix

| Query | Expected route | Expected status | Expected reason | Expected unsupported filters |
| --- | --- | --- | --- | --- |
| `Celtics record vs Atlantic Division` | `team_record` | `no_result` | `filter_not_supported` | `["opponent_division"]` |
| `Lakers record against Pacific Division` | `team_record` | `no_result` | `filter_not_supported` | `["opponent_division"]` |
| `Knicks record vs Central Division` | `team_record` | `no_result` | `filter_not_supported` | `["opponent_division"]` |
| `record against Northwest Division teams` | `team_record_leaderboard` | `no_result` | `filter_not_supported` | `["opponent_division"]` |
| `Lakers record against Western Conference Pacific Division teams` | `team_record` | `no_result` | `filter_not_supported` | `["opponent_division"]` |
| `Celtics playoff record vs Atlantic Division` | `team_record` | `no_result` | `filter_not_supported` | `["opponent_division"]` |
| `Celtics conference finals record vs Atlantic Division` | `playoff_history` | `no_result` | `filter_not_supported` | `["single_team_playoff_round_record"]` |

For explicit conference-finals record phrasing, preserve the existing
single-team playoff-round boundary. Division cleanup should not preempt or
weaken that higher-priority playoff boundary.

## Risk And Collision Analysis

### Opponent-conference phrases

Supported phrases such as `Celtics record against the East this season` and
`Lakers record against Western Conference teams` must keep returning supported
`team_record` answers for trusted seasons. Division cleanup must not weaken
current opponent-conference support.

Collision risk: mixed phrases currently parse and execute as conference-only
answers. The division guard should detect a division phrase first or explicitly
block execution before the supported opponent-conference route can return an
answer that ignores the division.

Recommended invariant: if a recognized NBA division phrase appears in an
opponent-record context, no conference-only answer should be returned even when
the text also contains `Eastern Conference`, `Western Conference`, `East`, or
`West`.

### Geography phrases

Existing geography phrases such as `east coast teams` are already guarded with
`unsupported_filters == ["opponent_conference"]`. Keep that behavior unchanged.
The division guard should not absorb east/west coast phrases, and geography
tests should continue to assert `opponent_conference`.

Recommended invariant: geography remains `opponent_conference`; NBA divisions
use `opponent_division`.

### Conference Finals phrases

`conference finals` is a playoff-round concept, not an opponent-conference or
division filter. Existing single-team round-record phrases return
`playoff_history` `no_result` / `filter_not_supported` with
`single_team_playoff_round_record`.

Recommended invariant: explicit `conference finals` record phrases keep the
existing playoff boundary. The division cleanup should not reroute
`Celtics conference finals record vs Atlantic Division` to `team_record` or to
an opponent-division-only boundary.

### Playoff division phrases

Plain playoff record phrases with division filters currently broad-fall back to
playoff `team_record` answers. They should be guarded like regular-season
division filters:

```text
Celtics playoff record vs Atlantic Division
-> team_record / no_result / filter_not_supported / opponent_division
```

This does not add division support in playoffs. It only prevents an unfiltered
playoff record answer.

### Division names and common-word overlap

NBA division names to guard:

- `Atlantic`
- `Central`
- `Southeast`
- `Northwest`
- `Pacific`
- `Southwest`

False-positive risks:

- `Central` is a common adjective.
- `Atlantic`, `Pacific`, `Northwest`, `Southwest`, and `Southeast` can be
  geography words outside NBA division context.
- None of the six names is an NBA team alias, but they may appear in non-NBA
  text or future schedule/venue/geography phrasing.

Recommended parser constraint: require an explicit `division` marker near the
division name and opponent-style wording (`against`, `vs`, `versus`) in a record
context for the first cleanup wave. Do not initially treat bare phrases such as
`against the Atlantic` or `against Central teams` as division filters unless a
later promotion explicitly accepts them.

## Test Plan

This cleanup should extend existing snapshot files. Do not create a new
division-support test file unless the implementation grows beyond this narrow
guard.

### Parser-level snapshots

Extend `tests/test_natural_query_route_priority_snapshots.py` with cases that
pin route, slots, unsupported filters, and note tags:

| Query | Parser assertions |
| --- | --- |
| `Celtics record vs Atlantic Division` | `route == "team_record"`, `team == "BOS"`, `opponent_conference is None`, `route_kwargs.unsupported_filters == ["opponent_division"]`, note contains `unsupported_boundary`. |
| `Lakers record against Pacific Division` | `route == "team_record"`, `team == "LAL"`, `route_kwargs.unsupported_filters == ["opponent_division"]`. |
| `Knicks record vs Central Division` | `route == "team_record"`, `team == "NYK"`, `route_kwargs.unsupported_filters == ["opponent_division"]`. |
| `record against Northwest Division teams` | `route == "team_record_leaderboard"`, no `team`, `route_kwargs.unsupported_filters == ["opponent_division"]`. |
| `Lakers record against Western Conference Pacific Division teams` | `route == "team_record"`, `team == "LAL"`, no executable conference-only filter, `route_kwargs.unsupported_filters == ["opponent_division"]`. |
| `Celtics conference finals record vs Atlantic Division` | `route == "playoff_history"`, `season_type == "Playoffs"`, `route_kwargs.unsupported_filters == ["single_team_playoff_round_record"]`. |
| `Celtics playoff record vs Atlantic Division` | `route == "team_record"`, `season_type == "Playoffs"`, `route_kwargs.unsupported_filters == ["opponent_division"]`. |

If the implementation adds a parser-only field such as
`opponent_division_boundary` or `opponent_division`, snapshots should pin it.
Do not expose a new API metadata field unless the implementation preflight is
expanded to a result-contract change.

### Query-level unsupported snapshots

Extend `tests/test_natural_query_unsupported_boundary_snapshots.py` with
execution cases asserting:

- route as listed in the parser matrix
- `qr.result.result_status == "no_result"`
- `qr.result.result_reason == "filter_not_supported"`
- `qr.metadata["unsupported_filters"] == ["opponent_division"]`, except for
  explicit conference-finals cases that keep
  `["single_team_playoff_round_record"]`
- `qr.to_dict()["sections"] == {}`
- no broad `summary`, `by_season`, or `leaderboard` sections

### Raw QA corpus and harness slices

After behavior changes, add raw QA cases. Recommended case IDs:

- `celtics_atlantic_division_guard`
- `lakers_pacific_division_guard`
- `knicks_central_division_guard`
- `record_against_northwest_division_teams_guard`
- `lakers_western_conference_pacific_division_guard`
- `celtics_playoff_atlantic_division_guard`

Expected raw QA shape for division guard cases:

```yaml
expected_status: no_result
expected_reason: filter_not_supported
expected_sections: []
hard_assertions:
  - path: result.metadata.unsupported_filters.0
    equals: opponent_division
```

Add the new cases to both relevant harness slices:

- `qa/harness_slices/natural_query_route_priority.yaml`
- `qa/harness_slices/product_boundaries.yaml`

### Reference docs

`docs/reference/query_catalog.md` and `docs/reference/query_guide.md` already
state the intended boundary. After implementation, refresh wording only if the
new `opponent_division` unsupported-filter id or examples should be explicit.
Do not make docs claim division support.

## Implementation Plan

Smallest safe behavior-change wave:

1. Add a narrow division-boundary detector in
   `src/nbatools/commands/_parse_helpers.py`.
   - Recognize only explicit NBA division phrases with a nearby `division`
     marker.
   - Require opponent-style wording in record contexts for the first wave.
   - Do not resolve division names to teams.
2. Thread the detector into `src/nbatools/commands/natural_query.py` parse
   state and route finalization.
   - Add an unsupported route branch near opponent-conference geography and
     supported opponent-conference routing.
   - Place it so mixed conference-plus-division text cannot return a
     conference-only answer.
   - Preserve existing conference-finals playoff boundary priority.
3. For single-team record division phrases, route to `team_record` with the
   existing season/date/location context and
   `unsupported_filters=["opponent_division"]`.
4. For no-subject record leaderboard division phrases, route to
   `team_record_leaderboard` with
   `unsupported_filters=["opponent_division"]`.
5. Add a dedicated message for `opponent_division` in
   `src/nbatools/commands/_natural_query_execution.py` if the generic
   unsupported-filter message is not clear enough.
6. Add parser snapshots, query unsupported snapshots, raw QA corpus cases, and
   harness slice entries.
7. Update reference docs only to clarify the verified unsupported filter id, not
   to advertise support.

Expected files likely to change in the future behavior wave:

- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/natural_query.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_natural_query_unsupported_boundary_snapshots.py`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/natural_query_route_priority.yaml`
- `qa/harness_slices/product_boundaries.yaml`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- a behavior-wave return package under `return_packages/raw-product/`

Do not touch frontend files unless the future wave deliberately changes
rendered no-result copy, which should be treated as a scope expansion.

## Validation Plan For Future Behavior Wave

Because the future cleanup touches parser helpers and `natural_query.py`, skip
`make test-impacted` and use broader parser/query validation:

```bash
make test-parser
make test-query
make test-preflight
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --fail-on-expectation-failure
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries --fail-on-expectation-failure
git diff --check
```

Add `make test-api` only if the implementation changes API metadata shape.
Add frontend build/tests only if frontend source changes, which this cleanup
should avoid.

## Stop Conditions

Stop and re-plan if the future cleanup:

- requires adding division-filter support or resolving division names to team
  lists
- requires a new data contract or R2 data requirement
- makes any division phrase return `ok` broad `team_record`,
  `team_record_leaderboard`, or conference-only rows
- changes supported opponent-conference answers for clean East/West phrases
- changes `east coast teams` / `west coast teams` geography behavior away from
  `unsupported_filters == ["opponent_conference"]`
- changes `conference finals` record behavior away from the existing
  `single_team_playoff_round_record` unsupported boundary
- changes existing raw QA expectations to make the cleanup pass
- changes result contracts, API response shape, frontend rendering, or frontend
  copy
- refactors `natural_query.py` beyond the narrow guard needed for the boundary
- updates reference docs to claim division support

## Preflight Validation

Docs-only validation for this preflight:

```bash
git diff --check
```

Run markdown lint if an available repo-local or installed markdown lint command
is present. If no markdown lint command is available, record that in the return
package.
