# Raw Query Answer QA Fix Wave 3: Date Filter Drop Prevention Return Package

## 1. Executive summary

- What was wrong: `Who scored the most points on January 1 2026?` returned broad season PPG leaders with no date filter.
- Root cause: explicit calendar dates like `January 1 2026` were not parsed, so the metric-only leaderboard fallback executed with `start_date=None` and `end_date=None`.
- What changed: explicit month-day calendar dates now parse to a single-day date range, and explicit-date top-scorer wording routes to date-filtered game-level `top_player_games`.
- Production code changed? yes
- Tests added/updated: parser, query-service metadata, and data-backed UI failure regressions for AQ-007 plus preserved working date-window cases.
- Corpus updated: `specific_date_jan_1` now expects `top_player_games`, a date filter, top-performance shape, and Kawhi Leonard's 45-point row.
- Findings updated: AQ-007 marked fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260512T105201Z/report.md`
- Remaining risk: this wave only fixes explicit-date top-scorer drop prevention. It does not address Bam 83-point data quality, opponent-quality/playoff-team semantics, non-scoring top performances, or frontend hero extraction.

## 2. Reproduction evidence

Before:

- Query: `Who scored the most points on January 1 2026?`
- Parse: `start_date=None`, `end_date=None`
- Route/status: `season_leaders`, `ok`
- Filters/date metadata: none
- Sections: `leaderboard`
- Behavior: returned unfiltered season PPG leaders, headed by Luka Doncic at 33.484 PPG.

After:

- Query: `Who scored the most points on January 1 2026?`
- Parse: `start_date=2026-01-01`, `end_date=2026-01-01`
- Route/status: `top_player_games`, `ok`
- Filters/date metadata: `Date range=2026-01-01 - 2026-01-01`
- Sections: `leaderboard` with game-level rows
- Corrected top row: Kawhi Leonard, 45 points, `2026-01-01`, Clippers vs Jazz.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_date_utils.py` | Production fix | Parse explicit month-day calendar dates into single-day date ranges. |
| `src/nbatools/commands/natural_query.py` | Production routing fix | Route explicit-date top-scorer questions to `top_player_games` instead of season aggregate leaders. |
| `tests/test_natural_date_queries.py` | Test coverage | Proves explicit-date top-scorer parsing and route selection. |
| `tests/test_query_service.py` | Test coverage | Proves query-service metadata preserves the date filter and executes `top_player_games`. |
| `tests/test_ui_failure_coverage.py` | Test coverage | Data-backed AQ-007 regression plus preserved March, All-Star break, and last-night date cases. |
| `qa/raw_query_answer_corpus.yaml` | QA corpus | Updates `specific_date_jan_1` hard expectations to the fixed behavior. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | Findings doc | Marks AQ-007 fixed and updates latest run counts/path. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Plan doc | Adds Fix Wave 3 status and remaining fix families. |
| `docs/reference/query_catalog.md` | Reference doc | Documents explicit calendar dates and explicit-date top-scorer behavior. |

## 4. Behavior after fix

- Specific-date top-scorer query: routes to `top_player_games`, preserves `2026-01-01 - 2026-01-01`, and returns game-level scoring rows.
- Working date-window leaderboards: `top scorers in March` still returns date-window `season_leaders`; `best offensive teams since January` still returns date-window `season_team_leaders`.
- Last-night no-result: still returns `season_leaders`, `no_result` / `no_match`, no sections, and the `2026-04-11 - 2026-04-11` date filter.
- Unsupported or unsupported-like date cases: unchanged; this wave does not broaden non-scoring top-performance support.

## 5. Test coverage

- `tests/test_natural_date_queries.py::test_parse_explicit_date_top_scorer_uses_game_level_route` proves the explicit date parses and routes to `top_player_games`.
- `tests/test_query_service.py::TestMetadataPreservation::test_specific_calendar_date_top_scorer_preserves_date_filter` proves service metadata and applied filters preserve the date.
- `tests/test_ui_failure_coverage.py::TestDateFilterDropPrevention::test_specific_date_top_scorer_uses_game_level_date_filtered_result` proves the exact AQ-007 query returns game-level rows, not PPG season leaders.
- `tests/test_ui_failure_coverage.py::TestDateFilterDropPrevention::test_working_date_window_cases_still_preserve_date_filters` proves March, All-Star break, and last-night date cases did not regress.

## 6. QA harness validation

- Targeted command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case specific_date_jan_1`
- Targeted result: `outputs/raw_query_answer_qa/20260512T105137Z`; 1 case, status `ok: 1`, expectation cases `pass: 1`, expectation checks `pass: 7`, failed IDs `none`, suspicious flag cases `0`.
- Full command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Full result: `outputs/raw_query_answer_qa/20260512T105201Z`; 78 cases, statuses `ok: 67`, `no_result: 5`, `error: 6`, expectation cases `pass: 78`, expectation checks `pass: 384`, failed IDs `[]`.
- Suspicious flags: 21 cases, unchanged from Wave 2; remaining flags are `missing_backend_answer_text: 20`, `playoff_teams_playoff_season_type: 1`, and `top_performance_high_points: 1`.

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_natural_date_queries.py::test_parse_explicit_date_top_scorer_uses_game_level_route tests/test_ui_failure_coverage.py::TestDateFilterDropPrevention -n0` -> `3 passed in 8.49s`
- `.venv/bin/pytest tests/test_query_service.py::TestMetadataPreservation::test_specific_calendar_date_top_scorer_preserves_date_filter -n0` -> `1 passed in 3.69s`
- `.venv/bin/pytest tests/test_natural_date_compare_leaderboard_queries.py tests/test_natural_all_star_break_queries.py::test_parse_player_since_all_star_break tests/test_natural_all_star_break_queries.py::test_natural_player_since_all_star_break_raw_smoke -n0` -> `14 passed in 12.01s`
- `make PYTEST=.venv/bin/pytest test-query` -> first run hit one unrelated xdist/order-sensitive metadata failure that passed in isolation; rerun passed with `691 passed in 133.50s`.

Harness:

- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case specific_date_jan_1` -> pass, output `outputs/raw_query_answer_qa/20260512T105137Z`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml` -> pass, output `outputs/raw_query_answer_qa/20260512T105201Z`

Always:

- `git diff --check` -> passed.

Optional:

- `.venv/bin/ruff check src/nbatools/commands/_date_utils.py src/nbatools/commands/natural_query.py tests/test_natural_date_queries.py tests/test_ui_failure_coverage.py tests/test_query_service.py` -> `All checks passed!`

## 8. Updated findings / next fix family recommendation

- AQ-007 status: fixed.
- Remaining highest-priority findings: AQ-001 opponent-quality / playoff-team semantics, AQ-002 top-performance data quality, AQ-006 non-scoring top-performance product decision, AQ-008 team-scoped rolling-stretch product decision.
- Recommended next fix family: opponent-quality / playoff-team semantics, unless product priority prefers top-performance data quality first.
