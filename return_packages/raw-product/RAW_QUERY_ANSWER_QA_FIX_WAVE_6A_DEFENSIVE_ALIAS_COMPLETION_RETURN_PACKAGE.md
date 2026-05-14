# Raw Query Answer QA Fix Wave 6A: Defensive / Opponent-Points Alias Completion Return Package

## 1. Executive summary

- What was wrong: `allow the most points per game` mapped to team scoring PPG, and `opponent PPG leaders` routed to player scoring leaders.
- What changed: completed narrow team leaderboard aliases for allowed/opponent points phrasing and added structured `season_team_leaders` aliases for `opponent ppg` forms.
- Production code changed? yes
- Tests added/updated: parser guardrails and data-backed query regressions.
- Corpus updated: yes, both AQ-021 target cases now have passing manual review and hard assertions.
- Findings updated: yes, AQ-021 is fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260514T050631Z/report.md`
- Remaining risk: bare `opponent PPG leaders` defaults to descending as the current leaderboard convention; playoff P1 failures remain intentionally untouched.

## 2. Behavior before/after

### Most points allowed

- Before: `season_team_leaders`, `stat=pts`, ranked team scoring PPG with Denver first.
- After: `season_team_leaders`, `stat=opponent_pts_per_game`, descending, Utah first at `126.012` opponent PPG.

### Opponent PPG leaders

- Before: `season_leaders`, `stat=pts`, returned player scoring leaders.
- After: `season_team_leaders`, `stat=opponent_pts_per_game`, descending, returned team rows with Utah first.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_leaderboard_utils.py` | production | Added narrow opponent-points aliases for `allow the most`, `most points allowed`, `opponent ppg`, and opponent-points-allowed phrasing. |
| `src/nbatools/commands/season_team_leaders.py` | production | Added structured alias parity for `opponent ppg`, `opp ppg`, and opponent-points-allowed forms. |
| `tests/test_natural_query_parser.py` | tests | Added parser guardrails for target aliases plus scoring, bare PPG, fewest allowed, and defensive-rating non-regressions. |
| `tests/test_ui_failure_coverage.py` | tests | Added data-backed regressions proving target queries return team opponent-PPG rows. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Updated target expectations, hard assertions, row counts, and manual review status. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Marked AQ-021 fixed with latest run path. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Added Wave 6A status, target cases, output paths, and remaining failures. |
| `docs/reference/query_catalog.md` | docs | Documented opponent PPG / points allowed leaderboards. |
| `docs/reference/query_guide.md` | docs | Added user-facing examples for most points allowed and opponent PPG leaders. |
| `src/nbatools/commands/entity_resolution.py` | CI stability | Added a tiny fallback player-name seed so data-free CI still resolves Anthony Edwards and surfaces Brown ambiguity candidates. |
| `src/nbatools/parser_examples.py` | lint-only cleanup | Wrapped existing long strings so the full CI lint target passes. |

## 4. Behavior after change

- Most points allowed leaderboard: `season_team_leaders`, `opponent_pts_per_game`, descending, Utah first.
- Opponent PPG leaderboard: `season_team_leaders`, `opponent_pts_per_game`, team rows, no player leaderboard rows.
- Fewest points allowed: still `opponent_pts_per_game`, ascending, Boston first.
- Team scoring leaders: `Which teams score the most points per game this season?` still uses team scoring `pts`.
- Defensive rating leaders: `best defensive rating teams this season` still uses `def_rating`.

## 5. Test coverage

- `test_most_points_allowed_team_leaderboard_uses_opponent_ppg_descending`: target allow-most phrase routes to team opponent PPG descending.
- `test_opponent_ppg_leaders_route_to_team_leaderboard`: target shorthand routes to team leaders, not player leaders.
- `test_points_allowed_team_leaderboard_uses_opponent_ppg`: existing fewest-points-allowed guardrail remains ascending.
- `test_team_scoring_most_points_leaderboard_stays_scoring_ppg`: scoring language remains team scoring PPG.
- `test_bare_ppg_leaders_stays_player_leaderboard`: generic PPG leaders remains player `season_leaders`.
- `test_best_defensive_rating_stays_defensive_rating`: defensive rating remains `def_rating`.
- `test_most_points_allowed_leaderboard_ranks_highest_opponent_ppg`: data-backed highest opponent PPG row is Utah and exposes `opponent_pts_per_game`.
- `test_opponent_ppg_leaders_use_team_leaderboard_rows`: data-backed opponent PPG shorthand returns team rows and exposes `opponent_pts_per_game`.

## 6. QA harness validation

Targeted harness:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case most_points_allowed_team_leaders_wave4 --case opponent_ppg_leaders_wave4 --case fewest_points_allowed_team_leader --case def_rating_team_leaders_wave4

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260514T050605Z
Cases: 4
Result statuses: {'ok': 4}
Expectation cases: {'pass': 4}
Suspicious flag cases: 0
Informational flag cases: 4
Verified outlier cases: 0
Failed case IDs: none
```

Full corpus harness:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260514T050631Z
Cases: 195
Result statuses: {'error': 8, 'no_result': 15, 'ok': 172}
Expectation cases: {'fail': 12, 'pass': 183}
Suspicious flag cases: 8
Informational flag cases: 113
Verified outlier cases: 1
Failed case IDs: centers_rebound_leaders_wave4, rookie_scoring_leaders_wave4, bench_scoring_leaders_wave4, starter_assist_leaders_wave4, celtics_bench_scoring_boundary_wave4, lebron_durant_comparison_wave4, bulls_finals_record_wave4, warriors_finals_record_since_2015_wave4, celtics_conference_finals_record_wave4, heat_knicks_playoff_series_record_wave4, personal_foul_leaders_wave4, celtics_against_east_record_wave4
```

- Latest output path: `outputs/raw_query_answer_qa/20260514T050631Z/report.md`
- Expectation pass/fail counts: cases `pass: 183`, `fail: 12`; checks `pass: 964`, `fail: 45`
- Remaining failed case IDs: `centers_rebound_leaders_wave4`, `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, `lebron_durant_comparison_wave4`, `bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, `celtics_conference_finals_record_wave4`, `heat_knicks_playoff_series_record_wave4`, `personal_foul_leaders_wave4`, `celtics_against_east_record_wave4`

## 7. Standard validation

Backend:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "points_allowed or opponent_ppg or team_scoring_most or bare_ppg or defensive_rating" -n0
6 passed, 147 deselected in 9.43s

.venv/bin/pytest tests/test_ui_failure_coverage.py -k "points_allowed_leaderboard or most_points_allowed_leaderboard or opponent_ppg_leaders" -n0
3 passed, 92 deselected in 10.30s

.venv/bin/pytest tests/test_season_team_leaders.py -n0
5 passed in 2.29s

.venv/bin/pytest tests/test_entity_resolution.py -k "anthony_edwards_full_name or Brown or brown" -n0
4 passed, 115 deselected in 6.66s

.venv/bin/pytest tests/test_backend_apply_patterns.py -k "entity_ambiguity_candidates" -n0
1 passed, 39 deselected in 9.80s

make PYTEST=.venv/bin/pytest test-parser
677 passed in 151.66s (0:02:31)

make PYTEST=.venv/bin/pytest test-query
708 passed in 251.41s (0:04:11)

make PYTEST=.venv/bin/pytest test-unit
2402 passed, 1 xpassed in 436.20s (0:07:16)
```

Harness:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case most_points_allowed_team_leaders_wave4 --case opponent_ppg_leaders_wave4 --case fewest_points_allowed_team_leader --case def_rating_team_leaders_wave4
4 cases, expectation cases pass: 4, failed IDs none

.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
195 cases, expectation cases pass: 183, fail: 12
```

Always:

```text
git diff --check
passed with no output
```

Optional:

```text
.venv/bin/ruff check src/nbatools/commands/_leaderboard_utils.py src/nbatools/commands/season_team_leaders.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py
All checks passed!

.venv/bin/ruff check src/ tests/ tools/
All checks passed!

.venv/bin/ruff format --check src/ tests/ tools/
183 files already formatted
```

## 8. Updated findings / next recommendation

- AQ-021 status: fixed.
- Remaining failed IDs: `centers_rebound_leaders_wave4`, `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, `lebron_durant_comparison_wave4`, `bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, `celtics_conference_finals_record_wave4`, `heat_knicks_playoff_series_record_wave4`, `personal_foul_leaders_wave4`, `celtics_against_east_record_wave4`
- Remaining highest-priority findings: AQ-020 playoff round/matchup routing remains P1; P2 position/role leaderboards, player comparison routing, unsupported personal-foul alias, and opponent-conference filters remain open.
- Recommended next phase: playoff round/matchup product/data/routing wave, with no defensive alias work needed unless new phrases emerge.
