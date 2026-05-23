# Natural Query Decision Map and Test Matrix Return Package

## 1. Executive summary

- Completed the docs-only first wave recommended by
  `docs/planning/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`.
- Created a durable decision map and extraction test matrix at
  `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`.
- Updated `docs/index.md` because a new durable planning doc was added under
  `docs/`.
- No production code, tests, QA corpus expectations, backend, frontend, result
  contracts, or parser behavior were changed.
- The new doc treats the current `_finalize_route()` order as a behavior
  contract until a future preflight says otherwise.
- The new doc explicitly states that wrong-route prevention matters more than
  making vague queries work, and includes the no-broad-fallback rule.

## 2. Files changed

Created:

- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `return_packages/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX_RETURN_PACKAGE.md`

Updated:

- `docs/index.md`

No code, test, corpus, backend, frontend, or result-contract files were
changed.

## 3. Durable doc contents

The decision map doc includes:

- current `natural_query.py` structure map
- current `_finalize_route()` decision order
- unsupported-boundary inventory
- route collision groups
- existing test coverage map
- test gaps before extraction
- required validation commands before extraction
- stop conditions for future extraction waves
- recommended first code extraction candidate

## 4. Key decisions recorded

- Current route order is contract for extraction purposes.
- Unsupported boundaries are shipped behavior.
- No broad fallback answers should be added for unsupported or low-confidence
  queries.
- Existing note-tagged broad fallback branches are documented as current
  behavior, not as a pattern to expand.
- The first code extraction candidate remains pure stat-availability constants:
  `_TEAM_SEASON_ADVANCED_STATS`, local `_team_season_only`, local
  `_player_season_only`, and local `_lower_is_better_stats`.
- Unsupported-boundary helper extraction, note/caveat extraction,
  route-family extraction, parse-state object conversion, dispatch-table
  routing, and bucket-first routing remain deferred.

## 5. Validation

Validation performed:

```text
git diff --check
markdown lint if available
```

Result:

- `git diff --check` passed.
- No markdown lint command was available in the shell path. Checked
  `markdownlint`, `markdownlint-cli2`, `mdl`, and `mdformat`.

No behavior tests were run because this was a docs-only change and the prompt
explicitly prohibited code/test/corpus behavior changes.

## 6. Next recommended action

If a future wave proceeds to code, start only with the pure stat-availability
constants named above, preserve values exactly, and run:

```text
make test-parser
make test-query
make raw-query-answer-qa
make test-preflight
```

Stop immediately if route order, unsupported filters, result reasons, notes,
or QA corpus expectations need to change.
