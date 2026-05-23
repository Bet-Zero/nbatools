# Raw Query Answer QA Fix Wave 7A: P2 Boundary / Routing Cleanup Return Package

## 1. Executive summary

- What was wrong:
  - Position-prefix leaderboards such as `Which centers have the most rebounds this season?` routed to `season_leaders` but dropped the position filter.
  - Full-name player comparison phrasing such as `LeBron James vs Kevin Durant comparison` routed as a player-game finder with `opponent_player`.
  - Unsupported product-boundary queries for rookie leaderboards, league-wide starter/bench leaderboards, team bench scoring, personal fouls, and opponent-conference records broadened into plausible but wrong answers.
- What changed:
  - Added position-prefix/question-form parsing for existing position-backed `season_leaders` support.
  - Added resolver-backed full-name player comparison extraction, with guardrails for player-vs-team and player-game-log forms.
  - Routed unsupported boundary forms through existing `unsupported_filters` so execution returns `no_result` / `filter_not_supported`.
  - Updated corpus expectations, findings, harness plan, and reference docs for the shipped support/boundary split.
- Production code changed? yes
- Tests added/updated:
  - Parser coverage for position-prefix leaderboards, full-name comparisons, comparison guardrails, and unsupported boundary markers.
  - Data-backed query coverage for the two supported fixes, six unsupported boundaries, and nearby guardrails.
- Corpus updated: yes
- Findings updated: yes
- Latest harness run: `outputs/raw_query_answer_qa/20260514T125056Z/report.md`
- Remaining risk:
  - Actual rookie, role leaderboard, team bench scoring, personal-foul, and opponent-conference execution remain deferred until product/data contracts are approved.

## 2. Behavior before/after

### Position-filtered leaderboards

- Before:
  - `Which centers have the most rebounds this season?` returned a broad rebound leaderboard with no `position_filter`.
- After:
  - It routes to `season_leaders`, keeps `stat=reb`, applies `position_filter=centers`, and exposes the Position applied filter.
  - Nearby prefix forms such as `guard scoring leaders this season`, `forwards FG% leaders this season`, and `point guard assist leaders this season` also preserve canonical position groups.

### Player comparison routing

- Before:
  - `LeBron James vs Kevin Durant comparison` routed to `player_game_finder` with LeBron as the player and Durant as `opponent_player`.
- After:
  - Full-name comparison forms route to `player_compare` with `summary` and `comparison` sections.
  - Guardrails keep `Jokic game log vs Embiid` as `player_game_finder` and `Jokic vs Lakers last 30 days` as a player-vs-team finder.

### Unsupported boundaries

- Before:
  - Unsupported role/rookie/PF/conference/team-bench forms returned broad leaderboards or records.
- After:
  - They return `no_result` / `filter_not_supported` with explicit `unsupported_filters`:
    `rookie_leaderboard`, `role_leaderboard`, `team_bench_scoring`, `personal_foul_leaderboard`, or `opponent_conference`.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | parser support / boundary detectors | Added position-prefix extraction and narrow unsupported-boundary detectors. |
| `src/nbatools/commands/_matchup_utils.py` | routing parser | Added full-name player comparison extraction and team-target guardrail. |
| `src/nbatools/commands/natural_query.py` | routing | Wired unsupported boundary slots into existing route kwargs and `unsupported_filters`. |
| `src/nbatools/commands/_natural_query_execution.py` | no-result messaging | Added specific unsupported-filter notes for new boundary IDs. |
| `tests/test_natural_query_parser.py` | tests | Added parser tests for supported gaps and unsupported boundaries. |
| `tests/test_ui_failure_coverage.py` | tests | Added data-backed coverage for Wave 7A targets and nearby guardrails. |
| `qa/raw_query_answer_corpus.yaml` | corpus expectations | Updated the eight target cases and hardened nearby position assertions. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | findings | Marked AQ-018/AQ-019/AQ-022/AQ-023 resolved or expected unsupported. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | plan status | Added Wave 7A status and latest harness results. |
| `docs/reference/query_catalog.md` | reference docs | Documented supported position/comparison forms and unsupported boundaries. |
| `docs/reference/query_guide.md` | reference docs | Added examples and boundary guidance. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_7A_P2_BOUNDARY_ROUTING_CLEANUP_RETURN_PACKAGE.md` | return package | Delivery summary. |

## 4. Behavior after change

- Centers rebound leaders:
  - `season_leaders` / `ok`, `stat=reb`, `position_filter=centers`, leaderboard rows returned.
- LeBron/Durant comparison:
  - `player_compare` / `ok`, `summary` and `comparison` sections returned.
- Rookie leaderboards:
  - `season_leaders` / `no_result`, `filter_not_supported`, `unsupported_filters=["rookie_leaderboard"]`.
- League role leaderboards:
  - `season_leaders` / `no_result`, `filter_not_supported`, `unsupported_filters=["role_leaderboard"]`.
- Team bench scoring:
  - `game_finder` / `no_result`, `filter_not_supported`, `unsupported_filters=["team_bench_scoring"]`.
- Personal foul leaderboards:
  - `season_leaders` / `no_result`, `filter_not_supported`, `unsupported_filters=["personal_foul_leaderboard"]`.
- Opponent-conference filters:
  - `team_record` / `no_result`, `filter_not_supported`, `unsupported_filters=["opponent_conference"]`.
- Nearby guardrails:
  - Named-player bench/starter summaries still execute.
  - Existing position `among guards/centers` forms still execute.
  - Player-game-log/player-vs-team matchup forms still avoid comparison hijacking.

## 5. Test coverage

- `tests/test_natural_query_parser.py`
  - `test_position_prefix_leaderboards_set_position_filter`: prefix/question position leaderboards preserve canonical position groups.
  - `test_among_position_leaderboard_still_sets_position_filter`: existing `among centers` coverage still works.
  - `test_full_name_player_comparison_route`, `test_compare_full_names_and_route`, `test_alias_player_comparison_still_routes`: comparison extraction works for full names and existing aliases.
  - `test_player_game_log_vs_player_stays_finder`: player game-log phrasing is not hijacked by comparison routing.
  - `test_p2_boundary_queries_set_unsupported_filter`: six unsupported boundaries set the expected filter IDs.
- `tests/test_ui_failure_coverage.py`
  - `TestP2BoundaryRoutingCleanup.test_center_rebound_leaders_execute_with_position_filter`: data-backed center leaderboard applies position metadata/filter.
  - `test_full_name_lebron_durant_comparison_executes_as_comparison`: full-name comparison returns `summary` + `comparison`.
  - `test_unsupported_boundary_queries_return_no_result`: unsupported boundary cases do not return broad answers.
  - `test_nearby_supported_queries_still_execute`: starter/bench player routes, position leaderboards, player comparison, and playoff-team record guardrails remain ok.
- `tests/test_natural_date_queries.py::test_parse_matchup_last_30_days`
  - Regression guard for player-vs-team matchup routing after comparison extraction was tightened.

## 6. QA harness validation

- Targeted 8-case harness command:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case centers_rebound_leaders_wave4 --case rookie_scoring_leaders_wave4 --case bench_scoring_leaders_wave4 --case starter_assist_leaders_wave4 --case celtics_bench_scoring_boundary_wave4 --case lebron_durant_comparison_wave4 --case personal_foul_leaders_wave4 --case celtics_against_east_record_wave4
```

- Targeted result:
  - Output: `outputs/raw_query_answer_qa/20260514T125005Z/report.md`
  - Cases: 8
  - Result statuses: `no_result: 6`, `ok: 2`
  - Expectation cases: `pass: 8`
  - Suspicious flag cases: 0
  - Failed case IDs: none

- Adjacent regression harness command:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case jokic_as_starter_summary_wave4 --case malik_monk_off_bench_summary_wave4 --case tatum_brown_last10_comparison_wave4 --case guards_scoring_leaders_wave4 --case tatum_playoff_teams_summary --case celtics_regular_season_record_vs_playoff_teams_wave4
```

- Adjacent result:
  - Output: `outputs/raw_query_answer_qa/20260514T125038Z/report.md`
  - Cases: 6
  - Result statuses: `ok: 6`
  - Expectation cases: `pass: 6`
  - Suspicious flag cases: 0
  - Failed case IDs: none

- Full corpus command:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
```

- Full corpus result:
  - Output: `outputs/raw_query_answer_qa/20260514T125056Z/report.md`
  - Cases: 195
  - Result statuses: `error: 8`, `no_result: 22`, `ok: 165`
  - Expectation cases: `pass: 195`
  - Expectation checks: `pass: 1037`
  - Suspicious flag cases: 0
  - Informational flag cases: 112
  - Verified outlier cases: 1
  - Remaining failed case IDs: none

## 7. Standard validation

Backend:

```text
.venv/bin/python -m pytest tests/test_natural_query_parser.py -k "full_name_player_comparison or compare_full_names or alias_player_comparison or player_game_log_vs_player or position_prefix or among_position or p2_boundary" -n0
```

- Result: `15 passed, 164 deselected in 44.91s`

```text
.venv/bin/python -m pytest tests/test_ui_failure_coverage.py -k "P2BoundaryRoutingCleanup" -n0
```

- Result: `13 passed, 99 deselected in 50.91s`

```text
.venv/bin/pytest tests/test_natural_date_queries.py::test_parse_matchup_last_30_days -n0
```

- Result: `1 passed in 3.36s`

```text
make PYTEST=.venv/bin/pytest test-parser
```

- Result: `703 passed in 143.02s`

```text
make PYTEST=.venv/bin/pytest test-query
```

- First run found `test_parse_matchup_last_30_days` regression; fixed by blocking player comparison extraction when the `vs` target resolves as a team.
- Final result: `725 passed in 232.62s`

```text
make PYTEST=.venv/bin/pytest test-preflight
```

- Result: `2800 passed, 1 xpassed in 1022.76s`

Harness:

- Targeted run: pass, see section 6.
- Adjacent run: pass, see section 6.
- Full corpus run: pass, see section 6.

Always:

```text
git diff --check
```

- Result: passed with no output.

Optional:

```text
.venv/bin/ruff check src/nbatools/commands/_parse_helpers.py src/nbatools/commands/_matchup_utils.py src/nbatools/commands/natural_query.py src/nbatools/commands/_natural_query_execution.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py
```

- Result: `All checks passed!`

## 8. Updated findings / next recommendation

- AQ-018 status:
  - Fixed as partial support plus expected unsupported boundaries. Position noun-prefix leaderboards are supported; rookie/role/team-bench forms are clean unsupported boundaries.
- AQ-019 status:
  - Fixed.
- AQ-022 status:
  - Fixed as expected unsupported.
- AQ-023 status:
  - Fixed as expected unsupported.
- Remaining failed IDs:
  - None in the 195-case corpus.
- Recommended next phase:
  - With the corpus at 195/195 and zero suspicious flags, choose between frontend hero/copy QA, targeted backend answer phrase enrichment for high-value direct-answer routes, or another focused corpus expansion wave.
