# Division Phrase Boundary Cleanup Return Package

## Executive Summary

- Fixed NBA division opponent phrasing so explicit division requests no longer
  broad-fallback to ordinary `team_record` or `team_record_leaderboard` `ok`
  answers.
- Division support was not added. Division requests now return the documented
  unsupported product boundary:
  - status: `no_result`
  - reason: `filter_not_supported`
  - sections: `{}`
  - `metadata.unsupported_filters=["opponent_division"]`
- The closest record route is preserved:
  - named-team record phrases route to `team_record`
  - no-subject record phrases route to `team_record_leaderboard`
- Opponent-conference support remains unchanged for clean East/West phrases.
- Conference-finals record phrasing remains on the existing
  `single_team_playoff_round_record` unsupported boundary.

## Behavior Covered

New guarded division cases:

- `Celtics record vs Atlantic Division`
- `Lakers record against Pacific Division`
- `Knicks record vs Central Division`
- `record against Northwest Division teams`
- `Lakers record against Western Conference Pacific Division teams`
- `Celtics playoff record vs Atlantic Division`

Preserved higher-priority playoff boundary:

- `Celtics conference finals record vs Atlantic Division`
  - route: `playoff_history`
  - unsupported filter: `single_team_playoff_round_record`

## Files Changed

Production:

- `src/nbatools/commands/_parse_helpers.py`
  - Added a narrow explicit NBA division phrase detector requiring opponent
    wording plus a `Division` marker.
- `src/nbatools/commands/natural_query.py`
  - Threads `opponent_division_boundary` through parse state.
  - Prevents mixed conference-plus-division text from executing as a broader
    conference-only answer.
  - Adds the unsupported record-route branch without broad refactoring.
- `src/nbatools/commands/_natural_query_execution.py`
  - Adds dedicated `opponent_division` no-result guidance.

Tests and QA:

- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_natural_query_unsupported_boundary_snapshots.py`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/natural_query_route_priority.yaml`
- `qa/harness_slices/product_boundaries.yaml`

Docs:

- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `return_packages/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_RETURN_PACKAGE.md`

## QA Harness Results

`natural_query_route_priority`:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --fail-on-expectation-failure

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260522T011838Z
Cases: 35
Result statuses: {'error': 2, 'no_result': 21, 'ok': 12}
Expectation cases: {'pass': 35}
Suspicious flag cases: 0
Informational flag cases: 9
Verified outlier cases: 0
Failed case IDs: none
```

`product_boundaries`:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries --fail-on-expectation-failure

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260522T011919Z
Cases: 18
Result statuses: {'no_result': 10, 'ok': 8}
Expectation cases: {'pass': 18}
Suspicious flag cases: 0
Informational flag cases: 6
Verified outlier cases: 0
Failed case IDs: none
```

## Validation

Completed:

```text
.venv/bin/pytest tests/test_natural_query_route_priority_snapshots.py tests/test_natural_query_unsupported_boundary_snapshots.py tests/test_raw_query_answer_qa.py -n0
65 passed in 208.54s (0:03:28)

make PYTEST=.venv/bin/pytest test-parser
776 passed in 378.85s (0:06:18)

make PYTEST=.venv/bin/pytest test-query
776 passed in 293.71s (0:04:53)

make PYTEST=.venv/bin/pytest test-preflight
2978 passed, 1 xpassed in 537.48s (0:08:57)

git diff --check
passed with no output
```

## Notes

- The implementation intentionally does not resolve division names to team
  lists and does not use the existing `division` data column.
- Division wording uses a separate `opponent_division` filter id instead of
  `opponent_conference` or `conference_coverage`.
- Mixed conference-plus-division requests expose no applied
  `opponent_conference` metadata when returning the unsupported division
  boundary.
