# Raw Query Answer QA Fix Wave 4B: Compound Threshold Representation Return Package

## 1. Executive summary

- What was wrong: compound thresholds were represented twice or not consumed by the right route. The Celtics count route applied `conditions` during occurrence aggregation, then post-filtered the aggregate row with duplicate `extra_conditions` and returned 0. The compact Jokic finder detected `pts>=30` and `ast>=10`, but executed `ast>=30`.
- What changed: compound thresholds now use a canonical route-consumed `conditions` list. Finder routes accept condition lists and apply them before sorting/limiting. Occurrence routes no longer receive duplicate post-aggregate filters for consumed conditions.
- Production code changed? yes
- Tests added/updated: parser, compound occurrence/query, and query service regressions.
- Corpus updated: yes, both target cases now have hard assertions and `manual_review.status: pass`.
- Findings updated: yes, AQ-014 is fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`
- Remaining risk: broad compact shorthand such as `25/10/10` and `30-10` remains intentionally unsupported. Count phrase grammar remains AQ-016-style answer text quality, though the compound phrase now includes both thresholds.

## 2. Behavior before/after

### Celtics 120 + 15 threes count

- Before: parse route was `team_occurrence_leaders`; `route_kwargs.conditions` had `pts>=120` and `fg3m>=15`, but `extra_conditions` also kept `fg3m>=15`. Execution built the correct compound occurrence row, then post-filtered the aggregate leaderboard row on missing `fg3m`, converted the `NoResult` to count 0, and applied filters exposed only `pts min` plus season range.
- After: parse route is still `team_occurrence_leaders`; `route_kwargs.conditions` has both thresholds and `extra_conditions` is empty. Result status is `ok`, primary count is `125`, and applied filters expose `pts min`, `fg3m min`, and season range.

### Jokic 30 points + 10 assists finder

- Before: parse route was `player_game_finder`; `compound_occurrence_conditions` detected `pts>=30` and `ast>=10`, but route execution used `stat=ast`, `min_value=30`, returned `no_result`, and exposed `ast min 30`.
- After: parse route is `player_game_finder`; `route_kwargs.conditions` has `pts>=30` and `ast>=10`, `stat=pts` is used for sorting, result status is `ok`, and 14 returned rows satisfy both thresholds.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_condition_utils.py` | production | Shared canonical stat-threshold condition normalization, coverage checks, and DataFrame filtering. |
| `src/nbatools/commands/natural_query.py` | production | Promotes compound threshold lists into route-consumed `conditions` and clears duplicate extras. |
| `src/nbatools/commands/_natural_query_execution.py` | production | Skips duplicate post-filters when conditions are consumed and moves finder extras into pre-limit condition execution. |
| `src/nbatools/commands/player_game_finder.py` | production | Applies compound condition lists before result sorting/limiting. |
| `src/nbatools/commands/game_finder.py` | production | Applies compound condition lists before result sorting/limiting, including derived `opponent_pts`. |
| `src/nbatools/query_service.py` | production | Exposes condition metadata/applied filters and builds compound count phrases from condition lists. |
| `tests/test_natural_query_parser.py` | tests | Parser guardrails for compound conditions, single thresholds, and unsupported shorthand. |
| `tests/test_compound_occurrence_queries.py` | tests | Data-backed execution regressions for Celtics count and Jokic finder. |
| `tests/test_query_service.py` | tests | Service-layer checks that conditions are passed to execution and duplicate extras are not used. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Target expectations, row counts, hard assertions, and manual review statuses. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | AQ-014 fixed and latest full run updated. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Wave 4B status, run paths, and remaining failures. |
| `docs/reference/query_catalog.md` | docs | Supported compound finder/count examples. |
| `docs/reference/query_guide.md` | docs | User-facing compound finder examples. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | docs | Finder examples include compound threshold forms. |

## 4. Behavior after change

- Team occurrence compound count: `how many Celtics games with 120+ points and 15+ threes since 2022` returns count `125`.
- Player finder compound filters: `Jokic games with 30 points and 10 assists` returns 14 rows, all with `pts >= 30` and `ast >= 10`.
- Applied filter metadata: compound routes expose both threshold filters.
- Existing single-stat thresholds: adjacent QA cases for player counts, team counts, made threes, and opponent-points counts passed.
- Scalar Wave 4A cases: Knicks allowed under 110, fewest points allowed, and Tatum under 40% FG all passed in the adjacent QA run.

## 5. Test coverage

- `tests/test_natural_query_parser.py`: proves Celtics count parses two route conditions and no duplicate extras; Jokic compact finder binds 30 to points and 10 to assists; single-stat Curry threshold stays scalar; `Jokic 25/10/10` is not expanded.
- `tests/test_compound_occurrence_queries.py`: proves Celtics count returns 125 with both filters and Jokic finder rows satisfy both thresholds.
- `tests/test_query_service.py`: proves route-consumed conditions are sent to execution with empty extras and applied filter metadata includes both conditions.
- `tests/test_structured_first_orchestration.py::TestExecuteBuildResult::test_extra_conditions_applied`: confirms finder extra conditions still execute safely through the new pre-limit path.

## 6. QA harness validation

- Targeted compound command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T083000Z_wave4b_targeted --case celtics_120_15_threes_count_missing_filter --case jokic_30_points_10_assists_finder_misparsed`
  - Result: 2 cases, result statuses `ok: 2`, expectation cases `pass: 2`, failed IDs none.
- Adjacent regression command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T083500Z_wave4b_adjacent --case players_40_point_count --case players_10_assist_count --case curry_5_threes_count --case curry_5_threes_finder --case lakers_held_opponents_under_100_count --case teams_120_point_count_answer_text_review --case knicks_allowed_under_110_record --case fewest_points_allowed_team_leader --case boston_tatum_under_40_fg_record_missing_filter`
  - Result: 9 cases, result statuses `ok: 9`, expectation cases `pass: 9`, failed IDs none.
- Full corpus command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T084000Z_wave4b_full`
  - Result: 145 cases; result statuses `ok: 127`, `no_result: 12`, `error: 6`; expectation cases `pass: 141`, `fail: 4`; expectation checks `pass: 716`, `fail: 10`.
  - Latest output path: `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`
  - Remaining failed case IDs: `anthony_edwards_last_10_summary_no_match`, `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, `anthony_edwards_wins_losses_split_no_match`.

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_natural_query_parser.py tests/test_compound_occurrence_queries.py tests/test_query_service.py -k "compound or multi_condition or natural_player_finder_metadata_preserves_threshold_context" -n0`: 61 passed, 202 deselected in 40.05s.
- `.venv/bin/pytest tests/test_natural_query_parser.py -n0`: 139 passed in 82.39s.
- `.venv/bin/pytest tests/test_compound_occurrence_queries.py -n0`: 53 passed in 38.02s.
- `.venv/bin/pytest tests/test_query_service.py -k "compound or natural_player_finder_metadata_preserves_threshold_context" -n0`: 3 passed, 68 deselected in 12.06s.
- `.venv/bin/pytest tests/test_structured_first_orchestration.py::TestExecuteBuildResult::test_extra_conditions_applied -n0`: 1 passed in 3.94s.
- `make PYTEST=.venv/bin/pytest test-parser`: 657 passed in 111.23s.
- `make PYTEST=.venv/bin/pytest test-query`: 702 passed in 297.77s.
- `make PYTEST=.venv/bin/pytest test-preflight`: 2729 passed, 1 xpassed in 704.09s.

Harness:

- Targeted compound run: `outputs/raw_query_answer_qa/20260513T083000Z_wave4b_targeted/report.md`
- Adjacent regression run: `outputs/raw_query_answer_qa/20260513T083500Z_wave4b_adjacent/report.md`
- Full corpus run: `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`

Always:

- `git diff --check`: passed with no output.

Optional:

- `.venv/bin/python -m ruff check` on changed Python/test files: `All checks passed!`

## 8. Updated findings / next recommendation

- AQ-014 status: fixed.
- Remaining failed IDs: `anthony_edwards_last_10_summary_no_match`, `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, `anthony_edwards_wins_losses_split_no_match`.
- Remaining highest-priority findings: Anthony Edwards summary/split no-match diagnostics, KD TS% top-defense context preservation, and Lakers last-season relative season parsing.
- Recommended next phase: context/filter preservation and no-match diagnostics.
