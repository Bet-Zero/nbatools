# Raw Query Answer QA Fix Wave 4A: Scalar Stat / Threshold Semantics Return Package

## 1. Executive summary

- What was wrong: defensive `allow fewer than N points` phrasing bound to team `pts`; points-allowed team leaderboards ranked low scoring teams; clear shooting percentage thresholds were dropped or left on 40.0 scale.
- What changed: parser aliases/normalization, `opponent_pts_per_game` team leaderboard support, corpus expectations, docs, and regression tests.
- Production code changed? yes
- Tests added/updated: parser coverage, team leaderboard engine coverage, and data-backed QA regression coverage.
- Corpus updated: yes, the three scalar target cases now have pass manual review and hard assertions.
- Findings updated: yes, AQ-011 and AQ-013 fixed; AQ-014 remains deferred.
- Latest harness run: `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`
- Remaining risk: compound threshold representation/execution is still open by design.

## 2. Behavior before/after

### Defensive / opponent-points record

- Before: Knicks `allow fewer than 110` parsed as `pts max`, returning 26 games, 8-18.
- After: parses as `opponent_pts max=109.9999`, returning 35 games, 32-3.

### Points-allowed leaderboard

- Before: `allowed the fewest points per game` ranked lowest team scoring.
- After: ranks `opponent_pts_per_game` ascending; Boston is top at about 107.159 opponent PPG.

### Percentage thresholds

- Before: `shoots under 40%` had no filter; `FG% under 40%` could parse on the wrong scale.
- After: clear shooting contexts infer `fg_pct` / `fg3_pct` / `ft_pct` and normalize `40%` to `0.40`.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | production | Opponent-points aliases and shooting percentage threshold normalization. |
| `src/nbatools/commands/_leaderboard_utils.py` | production | Team leaderboard points-allowed aliases. |
| `src/nbatools/commands/season_team_leaders.py` | production | Derive and expose `opponent_pts_per_game`. |
| `src/nbatools/commands/natural_query.py` | production | Preserve selected team leaderboard stat in parsed metadata. |
| `tests/test_natural_query_parser.py` | tests | Parser guardrails for opponent points, team scoring, team leaderboards, and shooting percentages. |
| `tests/test_season_team_leaders.py` | tests | Engine test for opponent PPG derivation. |
| `tests/test_ui_failure_coverage.py` | tests | Data-backed target/regression QA coverage. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Hard assertions and pass review for fixed scalar cases. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | AQ-011/AQ-013 fixed, AQ-014 deferred. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Wave 4A status and latest harness paths. |
| `docs/reference/query_catalog.md` | docs | Shipped query surface update. |
| `docs/reference/query_guide.md` | docs | User-facing examples update. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | docs | Notes `opponent_pts_per_game` team leaderboard metric. |

## 4. Behavior after change

- Knicks allowed under 110: `team_record`, `OPP PTS max=109.9999`, 35 games, 32 wins, 3 losses.
- Fewest points allowed leaderboard: `season_team_leaders`, `opponent_pts_per_game`, Boston top row, about 107.159.
- Tatum under 40% FG: `player_game_summary`, `fg_pct max=0.3999`, 6 games, 4 wins, 2 losses.
- Existing held-opponents-under filters: Lakers held opponents under 100 still returns 7-0.
- Existing scoring thresholds: Celtics scoring over 120 still uses team `pts min`.
- Compound thresholds: unchanged and still failing/open for the next wave.

## 5. Test coverage

- `tests/test_natural_query_parser.py`: added parser assertions for `allow fewer`, `score fewer`, held-opponents regression, points-allowed leaderboard, scoring leaderboard guardrail, defensive-rating guardrail, FG% thresholds, and 3PT% threshold.
- `tests/test_season_team_leaders.py`: added `opponent_pts_per_game` derivation from `pts - plus_minus`.
- `tests/test_ui_failure_coverage.py`: added data-backed exact checks for Knicks 32-3, Boston opponent PPG leaderboard, and Tatum 4-2, plus existing Lakers/Celtics regression coverage.

## 6. QA harness validation

- Targeted scalar run:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T071000Z_wave4a_targeted --case knicks_allowed_under_110_record --case fewest_points_allowed_team_leader --case boston_tatum_under_40_fg_record_missing_filter`
  Result: 3 cases, `ok: 3`, expectation cases `pass: 3`, failed IDs none.
- Adjacent regression run:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T071100Z_wave4a_adjacent --case lakers_held_opponents_under_100_record --case celtics_scored_over_120_record --case celtics_120_15_threes_count_missing_filter --case jokic_30_points_10_assists_finder_misparsed`
  Result: 4 cases, `ok: 3`, `no_result: 1`, expectation cases `pass: 2`, `fail: 2`; failed IDs are the deferred compound cases.
- Regression check after narrowing leaderboard metadata:
  `20260513T071800Z_wave4a_regression_check`, 4 cases, `ok: 4`, expectation cases `pass: 4`, failed IDs none.
- Full corpus:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T072000Z_wave4a_full`
  Result: 145 cases, `ok: 126`, `no_result: 13`, `error: 6`; expectation cases `pass: 139`, `fail: 6`; expectation checks `pass: 705`, `fail: 15`.
- Remaining failed case IDs: `anthony_edwards_last_10_summary_no_match`, `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, `celtics_120_15_threes_count_missing_filter`, `jokic_30_points_10_assists_finder_misparsed`, `anthony_edwards_wins_losses_split_no_match`.

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_natural_query_parser.py -n0`: 135 passed in 56.65s.
- `.venv/bin/pytest tests/test_season_team_leaders.py -n0`: 5 passed in 6.05s.
- `.venv/bin/pytest tests/test_ui_failure_coverage.py -k "knicks_record_allowing_under_110 or points_allowed_leaderboard_ranks_opponent_ppg or tatum_under_40_fg_record or lakers_record_holding_opponents_under_100 or celtics_record_scoring_over_120" -n0`: 5 passed, 84 deselected in 38.90s.
- `.venv/bin/pytest tests/test_record_queries.py -n0`: 114 passed, 1 xpassed in 66.33s.
- `make PYTEST=.venv/bin/pytest test-parser`: 653 passed in 149.04s.
- `make PYTEST=.venv/bin/pytest test-query`: 702 passed in 261.63s.
- `make PYTEST=.venv/bin/pytest test-preflight`: 2720 passed, 1 xpassed in 416.67s.

Harness:

- Targeted scalar run: `outputs/raw_query_answer_qa/20260513T071000Z_wave4a_targeted/report.md`
- Adjacent regression run: `outputs/raw_query_answer_qa/20260513T071100Z_wave4a_adjacent/report.md`
- Full corpus run: `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`

Always:

- `git diff --check`: passed with no output.

Optional:

- `.venv/bin/ruff check` on changed Python/test files: `All checks passed!`

## 8. Updated findings / next recommendation

- AQ-011 status: fixed for both scalar cases.
- AQ-013 status: fixed.
- AQ-014 status: open/deferred; compound threshold cases intentionally unchanged.
- Remaining highest-priority findings: Anthony Edwards no-match diagnostics, KD TS% top-defense context, Lakers last-season context, and compound thresholds.
- Recommended next phase: compound threshold representation/execution wave for count/finder routes.
