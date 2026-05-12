# Raw Query Answer QA Fix Wave 2: Unsupported / Missing Filter Policy Return Package

## 1. Executive summary

- What was wrong: a multi-player availability query could say "LeBron James and Anthony Davis both play" while returning the full-season Lakers record.
- Root cause: the parser recognized `both play` as an unsupported boundary only in notes, but still routed to `team_record` with no availability filter, so execution aggregated all 82 games.
- What changed: multi-player availability record phrasing now carries `unsupported_filters: ["multi_player_availability"]`; execution returns `no_result` / `filter_not_supported` before building an unfiltered result.
- Production code changed? yes
- Tests added/updated: parser and data-backed natural-query regressions for multi-player availability; single-player availability regression proving `Lakers record without LeBron` still filters.
- Corpus updated: `lakers_lebron_ad_both_play` now expects `no_result`, `filter_not_supported`, no sections, and the stable unsupported-filter marker.
- Findings updated: AQ-005 marked `fixed_as_expected_unsupported`.
- Latest harness run: `outputs/raw_query_answer_qa/20260512T100442Z/report.md`
- Remaining risk: the parser still does not fully extract both availability player names; this wave intentionally blocks unsafe execution rather than implementing multi-player availability.

## 2. Reproduction evidence

- Query: `What is the Lakers record when LeBron James and Anthony Davis both play?`
- Pre-fix route/status: `team_record`, `ok`
- Pre-fix filters: none
- Pre-fix summary behavior: Lakers full-season record, `82` games, `53` wins, `29` losses.
- Parse detail: `both play` produced an unsupported-boundary note, but only Anthony Davis was retained as `player`; no `without_player` or executable availability filter was represented.
- Corrected route/status/reason: `team_record`, `no_result`, `filter_not_supported`
- Corrected metadata: `unsupported_filters: ["multi_player_availability"]`
- Corrected behavior: no `summary` or `by_season` sections are returned; notes tell the caller multi-player availability filters are not supported with current data.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/natural_query.py` | Production fix | Detect multi-player availability record boundaries beyond `both play` and carry an unsupported-filter marker. |
| `src/nbatools/commands/_natural_query_execution.py` | Production fix | Convert requested unsupported filters into `filter_not_supported` no-results before command execution. |
| `src/nbatools/query_service.py` | Metadata | Preserve `unsupported_filters` in API/query metadata. |
| `tests/test_ui_failure_coverage.py` | Test coverage | Proves multi-player availability no longer returns an unfiltered record and single-player availability still works. |
| `qa/raw_query_answer_corpus.yaml` | QA corpus | Updates AQ-005 expectations to the fixed unsupported/no-result behavior. |
| `docs/reference/query_catalog.md` | Reference doc | Updates current behavior for multi-player availability record phrasing. |
| `docs/architecture/parser/examples.md` | Architecture doc | Replaces the old broad-fallback boundary note with unsupported/no-result behavior. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | Planning/status doc | Marks AQ-005 fixed as expected unsupported and points to the latest run. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Planning/status doc | Adds Fix Wave 2 status and latest harness outputs. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_2_UNSUPPORTED_MISSING_FILTER_POLICY_RETURN_PACKAGE.md` | Return package | Records implementation, validation, and remaining work. |

## 4. Behavior after fix

- Multi-player availability query: `What is the Lakers record when LeBron James and Anthony Davis both play?` returns `no_result` / `filter_not_supported`, with no fake full-season summary.
- Single-player availability queries: `Suns without Booker`, `Bucks record when Giannis was out`, `Knicks record when Jalen Brunson does not play`, and `Lakers record without LeBron` still route to filtered `team_record` results with `Without player` applied filters.
- Other unsupported boundaries: this wave only adds a targeted multi-player availability guard; it does not change opponent-quality semantics, date handling, top-performance data quality, or non-scoring top-performance routing.

## 5. Test coverage

- `tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_multi_player_availability_record_sets_unsupported_filter` proves `both play`, `both out`, `with X and Y`, and `without X and Y` record phrasings carry `multi_player_availability`.
- `tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_multi_player_availability_record_returns_unsupported_not_unfiltered` proves the exact AQ-005 query returns `no_result` / `filter_not_supported` and no sections.
- `tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_single_player_availability_record_still_executes_with_filter` proves `Lakers record without LeBron` still returns a filtered `team_record` with fewer than 82 games.

## 6. QA harness validation

- Targeted command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_lebron_ad_both_play`
- Targeted result: `outputs/raw_query_answer_qa/20260512T100432Z`; 1 case, status `no_result: 1`, expectation cases `pass: 1`, expectation checks `pass: 6`, failed IDs `none`, suspicious flag cases `0`.
- Full command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Full result: `outputs/raw_query_answer_qa/20260512T100442Z`; 78 cases, statuses `ok: 67`, `no_result: 5`, `error: 6`, expectation cases `pass: 78`, expectation checks `pass: 381`, failed IDs `[]`.
- Suspicious flags: 21 cases, down from 22 because AQ-005 no longer returns an ok summary; remaining flags are `missing_backend_answer_text: 20`, `playoff_teams_playoff_season_type: 1`, and `top_performance_high_points: 1`.

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_multi_player_availability_record_sets_unsupported_filter tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_multi_player_availability_record_returns_unsupported_not_unfiltered tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_single_player_availability_record_still_executes_with_filter -n0` -> `7 passed in 3.18s`
- `.venv/bin/pytest tests/test_ui_failure_coverage.py -n0` -> `77 passed in 19.60s`
- `.venv/bin/pytest tests/test_query_service.py::TestMetadataPreservation tests/test_query_service.py::TestNoResultAndError -n0` -> `19 passed in 8.70s`
- `make PYTEST=.venv/bin/pytest test-query` -> `688 passed in 140.67s`
- `make PYTEST=.venv/bin/pytest test-preflight` -> `2661 passed, 1 xpassed in 292.28s`

Harness:

- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_lebron_ad_both_play` -> pass, output `outputs/raw_query_answer_qa/20260512T100432Z`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml` -> pass, output `outputs/raw_query_answer_qa/20260512T100442Z`

Always:

- `git diff --check` -> passed.

Optional:

- `.venv/bin/ruff check src/nbatools/commands/natural_query.py src/nbatools/commands/_natural_query_execution.py src/nbatools/query_service.py tests/test_ui_failure_coverage.py` -> `All checks passed!`

## 8. Updated findings / next fix family recommendation

- AQ-005 status: fixed as expected unsupported.
- Remaining highest-priority findings: AQ-001 opponent-quality / playoff-team semantics, AQ-002 top-performance data quality, AQ-007 date handling; AQ-006 and AQ-008 still need product decisions around unsupported boundaries.
- Recommended next fix family: date handling for requested-but-dropped date filters, unless product priority prefers opponent-quality semantics first.
