# Raw Query Answer QA Fix Wave 6: Top-Performance Routing + Team Stretch Boundary Return Package

## 1. Executive summary

- AQ-006 result: fixed. Non-scoring single-game top-performance wording now routes to `top_player_games` with `stat=ast` or `stat=reb`.
- AQ-008 result: fixed as expected unsupported. Team-scoped rolling-stretch wording now returns `no_result` / `filter_not_supported` with `unsupported_filters=["team_rolling_stretch"]`.
- What changed: parser/routing support for AST/REB top single-game queries, plus a scoped unsupported guard for generic team rolling-stretch queries.
- Production code changed? yes.
- Tests added/updated: parser route tests and data-backed natural query regressions.
- Corpus updated: yes, AQ-006 now expects `ok`; AQ-008 now expects unsupported/no-result.
- Findings updated: yes.
- Latest harness run: `outputs/raw_query_answer_qa/20260513T040809Z/report.md`.
- Remaining risk: backend answer text / frontend hero extraction remains the highest-priority limitation flagged by the harness.

## 2. Behavior before/after

### AQ-006

- Before: `What were the most assists in a game this season?` and `What were the most rebounds in a game this season?` returned unrouted errors; `single-game assist leaders` and `single-game rebound leaders` could fall to season leaderboards.
- After: clear single-game AST/REB top-performance wording routes to `top_player_games`, returns `ok`, keeps the `top_performances` shape, and exposes the selected game stat column.

### AQ-008

- Before: `best 5-game team scoring stretch this season` returned `ok` player rolling-stretch rows.
- After: team-scoped rolling-stretch wording returns `no_result` / `filter_not_supported`, no player leaderboard rows, and guidance that team rolling-stretch leaderboards are not supported with current routes.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | production parser | Detect non-scoring single-game top-performance intent and explicit team-scoped rolling-stretch boundary wording. |
| `src/nbatools/commands/natural_query.py` | production routing | Route team rolling-stretch boundary wording through the existing unsupported-filter path. |
| `src/nbatools/commands/_natural_query_execution.py` | production execution note | Add specific guidance for `team_rolling_stretch`. |
| `tests/test_natural_query_parser.py` | tests | Lock AQ-006 parser routes, ordinary leaderboard guardrails, AQ-008 parser markers, and player-stretch regressions. |
| `tests/test_ui_failure_coverage.py` | tests | Add data-backed AQ-006/AQ-008 query-service regressions. |
| `qa/raw_query_answer_corpus.yaml` | QA corpus | Update AQ-006/AQ-008 expected status, route, shape, sections, and hard assertions. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | planning doc | Mark AQ-006 fixed and AQ-008 fixed-as-unsupported. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | planning doc | Add Fix Wave 6 status and latest harness outputs. |
| `docs/reference/query_catalog.md` | reference doc | Document AST/REB single-game top performances and unsupported team rolling stretches. |
| `docs/reference/query_guide.md` | reference doc | Add examples and boundary wording. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_6_TOP_PERFORMANCE_ROUTING_TEAM_STRETCH_BOUNDARY_RETURN_PACKAGE.md` | return package | Summarize Wave 6 changes and validation. |

## 4. Behavior after change

- Most assists in a game: `top_player_games`, `stat=ast`; top row Ryan Nembhard, 23 AST.
- Most rebounds in a game: `top_player_games`, `stat=reb`; top row Scottie Barnes, 25 REB.
- Ordinary season assist/rebound leaderboards: `assist leaders this season`, `most assists this season`, and `Who leads the NBA in assists this season?` remain `season_leaders`.
- Team-scoped rolling stretch: returns `no_result` / `filter_not_supported`, no sections, `unsupported_filters=["team_rolling_stretch"]`.
- Player rolling stretches: still return `player_stretch_leaderboard` rows.

## 5. Test coverage

- `test_non_scoring_single_game_top_performance_routes_to_top_player_games`: AST/REB single-game wording routes to `top_player_games`.
- `test_ordinary_assist_leaderboards_stay_season_leaders`: ordinary assist leaderboards do not get stolen by top-game routing.
- `test_team_scoped_rolling_stretch_sets_unsupported_filter`: team stretch variants carry `team_rolling_stretch`.
- `test_player_rolling_stretch_queries_do_not_set_team_boundary`: player stretch variants remain normal.
- `test_single_game_assist_leaders_execute_as_top_performances`: data-backed AST top-performance result returns 23 AST for Ryan Nembhard and not season AST-per-game fields.
- `test_single_game_rebound_leaders_execute_as_top_performances`: data-backed REB top-performance result returns 25 REB for Scottie Barnes and not season REB-per-game fields.
- `test_team_scoped_rolling_stretch_returns_unsupported_not_player_rows`: team stretch query returns `filter_not_supported` with no sections.
- `test_player_rolling_stretch_still_returns_rows`: player stretch query still executes and returns 3-game windows.

## 6. QA harness validation

- Targeted command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case most_assists_single_game --case most_rebounds_single_game --case team_5_game_scoring_stretch`
- Targeted result: `outputs/raw_query_answer_qa/20260513T040756Z/report.md`; 3 cases; statuses `ok: 2`, `no_result: 1`; expectation cases `pass: 3`; expectation checks `pass: 20`; suspicious flags `0`; verified outliers `0`; failed case IDs `[]`.
- Full command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Full result: `outputs/raw_query_answer_qa/20260513T040809Z/report.md`; 80 cases; statuses `ok: 70`, `no_result: 6`, `error: 4`; expectation cases `pass: 80`; expectation checks `pass: 409`; suspicious flag cases `22`; suspicious flags `missing_backend_answer_text: 22`; verified outlier cases `1`; verified outliers `top_performance_high_points: 1`; failed case IDs `[]`.

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_natural_query_parser.py::test_non_scoring_single_game_top_performance_routes_to_top_player_games tests/test_natural_query_parser.py::test_ordinary_assist_leaderboards_stay_season_leaders tests/test_natural_query_parser.py::test_team_scoped_rolling_stretch_sets_unsupported_filter tests/test_natural_query_parser.py::test_player_rolling_stretch_queries_do_not_set_team_boundary -n0` -> 17 passed.
- `.venv/bin/pytest tests/test_backend_apply_patterns.py::TestRoutingRules::test_highest_scoring_team_games_trigger tests/test_natural_query_parser.py::test_non_scoring_single_game_top_performance_routes_to_top_player_games -n0` -> 7 passed.
- `.venv/bin/pytest tests/test_ui_failure_coverage.py::TestTopPerformanceAndTeamStretchBoundaries -n0` -> 4 passed.
- `make PYTEST=.venv/bin/pytest test-parser` -> 643 passed.
- `make PYTEST=.venv/bin/pytest test-query` -> 699 passed.
- `make PYTEST=.venv/bin/pytest test-preflight` -> 2701 passed, 1 xpassed; exit code 0.
- `.venv/bin/ruff check src/nbatools/commands/_parse_helpers.py src/nbatools/commands/natural_query.py src/nbatools/commands/_natural_query_execution.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py` -> all checks passed.
- `git diff --check` -> passed with no output.

Harness:

- Targeted harness run: passed, `outputs/raw_query_answer_qa/20260513T040756Z/report.md`.
- Full harness run: passed, `outputs/raw_query_answer_qa/20260513T040809Z/report.md`.

## 8. Updated findings / next recommendation

- AQ-006 status: fixed.
- AQ-008 status: fixed_as_expected_unsupported.
- Remaining highest-priority finding/family: frontend answer extraction / backend answer text limitation (`missing_backend_answer_text` remains the only suspicious flag family in the latest full harness).
- Recommended next phase: decide whether to build rendered frontend answer extraction or enrich backend `answer_phrase` coverage for summary-style routes.
