# Natural Query Route Priority Snapshot Preflight Return Package

## 1. Executive summary

- Completed a documentation-only preflight for the next safety-net wave before
  further `natural_query.py` extraction.
- No production code, tests, parser behavior, QA corpus expectations, result
  contracts, API behavior, or frontend behavior were changed.
- Recommended first executable wave: add a dedicated parser route-priority
  snapshot file, a dedicated query unsupported/no-broad-fallback snapshot file,
  and a raw QA harness slice using existing corpus IDs.
- Main finding: coverage is broad but scattered; extraction needs compact
  route-priority and no-broad-fallback matrices.
- Notable gap: `Celtics record vs Atlantic Division` currently returns broad
  `team_record` `ok` behavior, despite division phrasing being policy-guarded.
  This should be handled as a separate product-boundary cleanup candidate, not
  as a passing snapshot in the first wave.

## 2. Files inspected

Required files:

- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `docs/planning/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`
- `return_packages/raw-product/NATURAL_QUERY_CONSTANTS_EXTRACTION_WAVE_1_RETURN_PACKAGE.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`
- `src/nbatools/commands/natural_query.py`
- parser/query tests under `tests/`
- `qa/raw_query_answer_corpus.yaml`

Additional files:

- `qa/harness_slices/*.yaml`
- `Makefile`
- representative raw-product preflight and return package artifacts

## 3. Files changed

Created:

- `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md`
- `return_packages/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT_RETURN_PACKAGE.md`

Updated:

- `docs/index.md`

No code, tests, frontend, backend, or QA corpus files were changed.

## 4. Recommended first executable wave

Add tests only:

1. `tests/test_natural_query_route_priority_snapshots.py`
   - parser-marked route/collision snapshot matrix
   - asserts route, key route kwargs, unsupported filters, and route-winner
     slots
2. `tests/test_natural_query_unsupported_boundary_snapshots.py`
   - query-marked execution snapshot matrix
   - asserts status, reason, unsupported filters, and empty sections for
     no-broad-fallback cases
3. `qa/harness_slices/natural_query_route_priority.yaml`
   - references existing raw QA case IDs only
   - no corpus expectation changes in the first wave

Do not extract production code in that same wave.

## 5. Exact coverage recommended

Collision groups covered by the proposed parser snapshots:

- opponent conference vs Conference Finals vs geography phrases
- team record vs team comparison vs team matchup record
- player comparison vs player-vs-opponent finder/summary
- top single-game performances vs ordinary leaderboards
- on/off vs whole-game absence
- team rolling stretch boundary vs player rolling stretch support
- single-team advanced stat boundary vs league team advanced leaderboard

Unsupported/no-broad-fallback boundaries covered by the proposed query
snapshots:

- `team_rolling_stretch`
- `rookie_leaderboard`
- `role_leaderboard`
- `team_bench_scoring`
- `personal_foul_leaderboard`
- `opponent_conference`
- `conference_coverage`
- `single_team_advanced_stat_summary`
- `single_team_playoff_round_record`
- `multi_player_availability`
- on/off unsupported data
- lineup unsupported data
- clutch unsupported data
- subjective/unrouted concepts

## 6. Validation performed

Read-only checks performed during preflight:

- inspected existing planning docs, tests, raw QA corpus, harness slices, and
  `natural_query.py`
- ran representative `parse_query()` checks for candidate collision phrases
- ran representative `execute_natural_query()` checks for candidate
  route/status/reason behavior
- checked for markdown lint binaries in the shell path

Commands run after doc creation:

```text
git diff --check
git diff --no-index --check /dev/null docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md
git diff --no-index --check /dev/null return_packages/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT_RETURN_PACKAGE.md
```

Result: passed. The `--no-index` checks exit nonzero because the files differ
from `/dev/null`, but they emitted no whitespace warnings.

Markdown lint:

- `markdownlint`, `markdownlint-cli2`, and `pymarkdown` were not available in
  the shell path, so no markdown lint command was available to run.

## 7. Recommended validation for next wave

```text
make PYTEST=.venv/bin/pytest test-parser
make PYTEST=.venv/bin/pytest test-query
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --fail-on-expectation-failure
git diff --check
```

Before any subsequent `natural_query.py` extraction, also run:

```text
make PYTEST=.venv/bin/pytest test-preflight
```

## 8. Stop conditions

Stop the snapshot wave if it requires:

- production-code changes
- parser/routing behavior changes
- raw QA expectation changes
- new query support
- result-contract, API, frontend, or data changes
- accepting broad fallback behavior as the expected unsupported result

Stop later extraction if it changes route selection, route kwargs, parser notes,
result status/reason, section shape, or `metadata.unsupported_filters` for the
snapshot matrix.
