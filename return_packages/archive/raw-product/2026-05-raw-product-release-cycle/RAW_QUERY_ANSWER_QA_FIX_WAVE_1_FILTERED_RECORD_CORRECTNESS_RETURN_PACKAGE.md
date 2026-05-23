# Raw Query Answer QA Fix Wave 1: Filtered Record Correctness Return Package

## 1. Executive summary

- What was wrong: filtered `team_record` summaries could advertise an opponent-points threshold while aggregating the full season.
- Root cause: `team_record._apply_game_filters()` only applied a stat threshold when the stat already existed as a source column. Team game rows do not carry `opponent_pts`, so `stat="opponent_pts"` became a silent no-op.
- What changed: `team_record` now supports threshold filtering through an explicit stat allowlist and derives `opponent_pts` from `pts - plus_minus` when needed before summary/by-season aggregation.
- Production code changed? yes
- Tests added/updated: engine coverage for `opponent_pts` team-record thresholds and unsupported threshold stats; data-backed natural-query regressions for Lakers under-100 and Celtics over-120 team records.
- Corpus updated: `lakers_held_opponents_under_100_record` now has hard assertions for `games=7`, `wins=7`, `losses=0` and manual review status `pass`.
- Findings updated: AQ-004 marked fixed with latest run path.
- Latest harness run: `outputs/raw_query_answer_qa/20260512T085014Z/report.md`
- Remaining risk: `opponent_pts` is inferred from team points and margin when absent, so it depends on those source fields being correct.

## 2. Reproduction evidence

- Query: `What is the Lakers record when they held opponents under 100 points?`
- Route: `team_record`
- Filters: `OPP PTS max=99.9999`
- Pre-fix summary record: `82` games, `53` wins, `29` losses.
- Corrected summary record: `7` games, `7` wins, `0` losses.
- Corrected by-season record: `7` games, `7` wins, `0` losses.
- Companion query: `How often have the Lakers held opponents under 100 points this year?`
- Companion count/finder result: `7` matching games, `7-0`.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/team_record.py` | Production fix | Apply supported stat thresholds before record aggregation; derive `opponent_pts`; reject unsupported threshold stats. |
| `tests/test_record_queries.py` | Test coverage | Proves opponent-points thresholds use opponent score and unsupported threshold stats do not return unfiltered records. |
| `tests/test_ui_failure_coverage.py` | Test coverage | Adds data-backed natural-query regressions for Lakers under-100 and Celtics over-120 records. |
| `qa/raw_query_answer_corpus.yaml` | QA corpus | Adds hard AQ-004 assertions and marks the fixed manual-review case as pass. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | Planning/status doc | Marks AQ-004 fixed and points to the latest clean run. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Planning/status doc | Adds Fix Wave 1 status and latest harness outputs. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_1_FILTERED_RECORD_CORRECTNESS_RETURN_PACKAGE.md` | Return package | Records implementation, validation, and remaining work. |

## 4. Behavior after fix

- Lakers held opponents under 100 record: `team_record`, status `ok`, summary and by-season both return `7-0` over `7` games.
- Celtics score over 120 record: still supported; summary is filtered (`23` games, not full season) and wins/losses sum to games.
- Existing supported team-record filters: location and other non-threshold record queries still work; `win_pct` with no threshold remains a record metric, not a filter.
- Unsupported filters: unsupported threshold stats now raise through the service as unsupported/no-result instead of returning an unfiltered record.

## 5. Test coverage

- `tests/test_record_queries.py::TestBuildTeamRecordResult::test_record_with_opponent_points_threshold_uses_opponent_score` proves `team_record` derives and filters by opponent score before summary/by-season aggregation.
- `tests/test_record_queries.py::TestBuildTeamRecordResult::test_record_with_unsupported_stat_filter_does_not_return_unfiltered_record` proves unsupported threshold stats do not silently pass.
- `tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_lakers_record_holding_opponents_under_100_uses_filtered_sample` proves the exact AQ-004 natural query returns `7` games, `7` wins, `0` losses.
- `tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_celtics_record_scoring_over_120_uses_filtered_sample` proves a nearby team-points threshold record remains filtered and internally consistent.

## 6. QA harness validation

- Targeted command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_held_opponents_under_100_record`
- Targeted result: `outputs/raw_query_answer_qa/20260512T085005Z`; 1 case, status `ok: 1`, expectation cases `pass: 1`, expectation checks `pass: 9`, failed IDs `none`.
- Full command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Full result: `outputs/raw_query_answer_qa/20260512T085014Z`; 78 cases, statuses `ok: 68`, `no_result: 4`, `error: 6`, expectation cases `pass: 78`, expectation checks `pass: 379`, failed IDs `[]`.
- Suspicious flags: 22 cases, unchanged from the prior accepted run; AQ-004 still only has the expected missing-backend-answer-text review flag.

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_record_queries.py::TestBuildTeamRecordResult::test_record_with_opponent_points_threshold_uses_opponent_score tests/test_record_queries.py::TestBuildTeamRecordResult::test_record_with_unsupported_stat_filter_does_not_return_unfiltered_record tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_lakers_record_holding_opponents_under_100_uses_filtered_sample tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_celtics_record_scoring_over_120_uses_filtered_sample -n0` -> `4 passed in 3.25s`
- `.venv/bin/pytest tests/test_record_queries.py -n0` -> `114 passed, 1 xpassed in 13.21s`
- `make PYTEST=.venv/bin/pytest test-query` -> `683 passed in 134.20s`

Harness:

- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_held_opponents_under_100_record` -> pass, output `outputs/raw_query_answer_qa/20260512T085005Z`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml` -> pass, output `outputs/raw_query_answer_qa/20260512T085014Z`

Always:

- `git diff --check` -> passed.

Optional:

- `.venv/bin/ruff check src/nbatools/commands/team_record.py tests/test_record_queries.py tests/test_ui_failure_coverage.py` -> `All checks passed!`

## 8. Updated findings / next fix family recommendation

- AQ-004 status: fixed.
- Remaining highest-priority findings: AQ-001 opponent-quality / playoff-team semantics, AQ-002 top-performance data quality, AQ-005 unsupported/no-result policy for multi-player availability, AQ-007 date handling.
- Recommended next fix family: unsupported/no-result policy for missing filters, unless product priority prefers AQ-001 opponent-quality semantics first.
