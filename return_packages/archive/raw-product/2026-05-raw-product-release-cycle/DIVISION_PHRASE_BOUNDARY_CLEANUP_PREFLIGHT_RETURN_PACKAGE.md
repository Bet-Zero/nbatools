# Division Phrase Boundary Cleanup Preflight Return Package

## What changed

- Created a documentation-only preflight for the division phrase
  product-boundary cleanup candidate.
- Documented current broad-fallback behavior for regular-season, no-subject,
  conference-plus-division, conference-finals, and playoff division phrases.
- Recommended a future guarded unsupported response with
  `metadata.unsupported_filters == ["opponent_division"]`.
- Created a future implementation and test plan.
- Did not change production code, parser/routing behavior, backend behavior,
  frontend behavior, result contracts, tests, QA corpus expectations, or
  division support.

## Files changed

Created:

- `docs/planning/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT.md`
- `return_packages/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT_RETURN_PACKAGE.md`

Updated:

- `docs/index.md`

## Current behavior documented

Read-only probes confirmed:

- `Celtics record vs Atlantic Division`, `Lakers record against Pacific
  Division`, and `Knicks record vs Central Division` currently return
  unfiltered `team_record` `ok` answers with no unsupported filter.
- `record against Northwest Division teams` currently returns an unfiltered
  `team_record_leaderboard` `ok` answer.
- conference-plus-division phrases currently return conference-filtered
  `team_record` `ok` answers while ignoring the division phrase.
- `conference finals` record phrases with division text still hit the existing
  `single_team_playoff_round_record` unsupported boundary.
- playoff division phrases without a round currently return broad playoff
  `team_record` `ok` answers.

## Recommendation

Divisions should remain unsupported for this cleanup. The future behavior wave
should return:

- route: closest record route (`team_record` or `team_record_leaderboard`)
- status: `no_result`
- reason: `filter_not_supported`
- sections: `{}`
- unsupported filter: `opponent_division`

Use `opponent_division` as a separate filter id. The boundary is
opponent-conference-adjacent for route priority, but division requests should
not be reported as `opponent_conference` or `conference_coverage` failures.

## Test plan recorded

The preflight recommends extending:

- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_natural_query_unsupported_boundary_snapshots.py`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/natural_query_route_priority.yaml`
- `qa/harness_slices/product_boundaries.yaml`

Representative future cases include:

- `Celtics record vs Atlantic Division`
- `Lakers record against Pacific Division`
- `Knicks record vs Central Division`
- `record against Northwest Division teams`
- `Lakers record against Western Conference Pacific Division teams`
- `Celtics playoff record vs Atlantic Division`
- `Celtics conference finals record vs Atlantic Division`

## Validation

Completed docs-only validation:

- `git diff --check`
  - Result: passed for tracked diff.
- `git diff --no-index --check /dev/null docs/planning/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT.md`
  - Result: no whitespace warnings. The command exits nonzero because the new
    file differs from `/dev/null`.
- `git diff --no-index --check /dev/null return_packages/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT_RETURN_PACKAGE.md`
  - Result: no whitespace warnings. The command exits nonzero because the new
    file differs from `/dev/null`.

Markdown lint:

- `markdownlint` was not installed on `PATH`.
- `markdownlint-cli2` was not installed on `PATH`.
- No repo-local markdownlint config or binary was found in a shallow discovery
  check.

## Next action

Use
`docs/planning/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT.md` as the
scope contract for a future narrow behavior-change wave. Do not add division
support or refactor `natural_query.py` as part of that wave.
