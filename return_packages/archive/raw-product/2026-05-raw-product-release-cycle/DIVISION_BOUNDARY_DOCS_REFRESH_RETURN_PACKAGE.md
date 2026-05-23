# Division Boundary Docs Refresh Return Package

## Executive Summary

- Refreshed durable docs after Division Phrase Boundary Cleanup.
- This was docs-only. No production code, parser/routing behavior, tests, QA
  corpus expectations, data contracts, frontend behavior, or division support
  were changed.
- Durable docs now record that explicit NBA division opponent phrases are
  guarded unsupported behavior:
  - status: `no_result`
  - reason: `filter_not_supported`
  - sections: `{}`
  - `metadata.unsupported_filters=["opponent_division"]`
- The docs also record that named-team division record phrases preserve
  `team_record`, no-subject division record phrases preserve
  `team_record_leaderboard`, and mixed conference-plus-division phrases do not
  return broader conference-only answers.
- Conference-finals record phrasing remains on the existing
  `single_team_playoff_round_record` unsupported boundary.

## Files Changed

Reference docs:

- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

Planning and release docs:

- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md`
- `docs/planning/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/index.md`

Return package:

- `return_packages/raw-product/DIVISION_BOUNDARY_DOCS_REFRESH_RETURN_PACKAGE.md`

## Durable Behavior Recorded

- Division phrases are explicitly unsupported as `opponent_division`.
- The previous broad-fallback issue is resolved.
- Division support was not added.
- Opponent-conference support remains unchanged for clean East/West phrases.
- Conference-finals record phrasing remains a playoff-round unsupported
  boundary using `single_team_playoff_round_record`.
- Release/readiness docs now include the division cleanup evidence and note that
  the current raw QA corpus has 253 cases after the seven division-boundary
  guard additions, while the latest full release run remains the earlier
  246-case run plus targeted division-slice evidence.

## Validation Evidence Recorded

The docs now reference the cleanup validation from
`return_packages/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_RETURN_PACKAGE.md`:

- Targeted snapshot tests: 65 passed.
- `make PYTEST=.venv/bin/pytest test-parser`: 776 passed.
- `make PYTEST=.venv/bin/pytest test-query`: 776 passed.
- Raw QA `natural_query_route_priority` slice: 35/35 passed.
- Raw QA `product_boundaries` slice: 18/18 passed.
- `make PYTEST=.venv/bin/pytest test-preflight`: 2978 passed, 1 xpassed.
- `git diff --check`: passed.

## Validation For This Docs Refresh

```text
git diff --check
passed with no output

git diff --no-index --check /dev/null return_packages/raw-product/DIVISION_BOUNDARY_DOCS_REFRESH_RETURN_PACKAGE.md
no whitespace warnings; command exits nonzero because the new file differs from /dev/null
```

Markdown lint:

- `markdownlint` was not installed on `PATH`.
- `markdownlint-cli2` was not installed on `PATH`.
- No repo-local markdownlint config or binary was found by `rg --files -g
  '*markdownlint*' -g '.markdownlint*'`.
