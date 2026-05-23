# Raw Query Answer QA Corpus Expansion Wave 4 Return Package

## 1. Executive summary

- What changed: expanded `qa/raw_query_answer_corpus.yaml` from 145 to 195 curated cases and updated Wave 4 findings/plan docs.
- Production code changed? no
- Tests changed? no hard tests changed; QA corpus/docs changed.
- Corpus size before/after: 145 -> 195
- Latest harness run: `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.md`
- Expectations: 181 pass, 14 fail; 953 checks pass, 48 checks fail
- Open suspicious flags: 8 cases
- Informational flags: 113 cases, all `frontend_hero_expected`
- Verified outliers: 1 case, `top_performance_high_points`
- Main new finding families: position/role leaderboards, player comparison routing, playoff round/matchup routing, defensive/opponent-points aliases, unsupported stat aliases, opponent-conference filters.
- Recommended next step: group the Wave 4 failures into fix families before frontend hero/copy QA, with P1 attention on playoff round/matchup routing and defensive/opponent-points aliases.

## 2. Corpus expansion summary

| Area | Cases added | Purpose |
|---|---:|---|
| Position/role/context aliases | 12 | Cover position-filtered leaderboards, rookie/bench/starter leaderboard boundaries, and named-player starter/bench contexts. |
| Splits/comparisons | 10 | Cover player/team splits, player/team comparisons, head-to-head matchup records, and on/off unsupported guidance. |
| Playoff/history/era | 10 | Cover Finals/conference-finals record phrasing, playoff history, series records, since-year, decade, and season-type guardrails. |
| Stat aliases/advanced metrics | 10 | Cover eFG%, turnovers, personal fouls, pace, defensive rating, points allowed/opponent PPG, AST%, and TOV%. |
| Context/filter combinations | 5 | Cover explicit road season, East opponent context, playoff teams last season, since All-Star plus stat, and explicit-date no-match. |
| Unsupported/product boundaries | 3 | Cover subjective defensive, award, and lineup membership boundaries. |
| Total | 50 | Expanded from 145 to 195 cases. |

## 3. Strategy coverage

Position/role/context aliases were covered with center/guard/forward leaderboards, rookie/bench/starter leaderboards, `Jokic as a starter`, `Malik Monk off the bench`, and team bench-scoring boundary phrasing.

Splits/comparisons were covered with Curry/Lakers/Thunder/Brunson splits, Tatum/Brown and Warriors/Lakers comparisons, Lakers/Celtics head-to-head record, Heat/Knicks head-to-head since 2020, LeBron/Durant comparison routing, and Tatum on/off unsupported behavior.

Playoff/history/era coverage added Finals and conference-finals record phrasing, conference-finals appearances, Spurs playoff history since 2000, Heat/Knicks playoff series record, Lakers since 2010, best record in the 2020s, Warriors/Lakers by decade, and regular-season vs playoff-team guardrails.

Stat aliases/advanced metrics covered eFG%, turnovers/fewest turnovers, personal fouls, pace, defensive rating, points allowed, opponent PPG, assist percentage, and turnover rate.

Context/filter combinations covered Warriors road record in 2024-25, Celtics against the East, SGA points against playoff teams last season, Jokic assists since All-Star break, and an explicit February 14, 2026 no-match top-scorer query.

Unsupported/product boundaries covered perimeter defenders, MVP opinion, and lineup membership with Edwards/Gobert.

## 4. Harness/report changes

None. This wave did not change `tools/raw_query_answer_qa.py` or report behavior.

## 5. Latest run summary

- Run ID: `20260513T214500Z_wave4_full`
- Output path: `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.md`
- Case count: 195
- Result status counts: `ok: 172`, `no_result: 15`, `error: 8`
- Expectation pass/fail counts: cases `pass: 181`, `fail: 14`; checks `pass: 953`, `fail: 48`
- Suspicious flags: 8 cases, `expected_ok_returned_non_ok: 2`, `expected_unsupported_returned_ok: 6`
- Informational flags: 113 cases, `frontend_hero_expected: 113`
- Verified outliers: 1 case, `top_performance_high_points: 1`
- Failed case IDs: `centers_rebound_leaders_wave4`, `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, `lebron_durant_comparison_wave4`, `bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, `celtics_conference_finals_record_wave4`, `heat_knicks_playoff_series_record_wave4`, `personal_foul_leaders_wave4`, `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4`, `celtics_against_east_record_wave4`

## 6. New/updated findings

| Finding ID | Priority | Category | Case/query | Finding type | Status | Recommended fix family |
|---|---|---|---|---|---|---|
| AQ-018 | P2 | Position/role-filtered leaderboards | `centers_rebound_leaders_wave4`; `rookie_scoring_leaders_wave4`; `bench_scoring_leaders_wave4`; `starter_assist_leaders_wave4`; `celtics_bench_scoring_boundary_wave4` | missing_filter / unsupported_no_result_policy | open | position/role-filtered leaderboards |
| AQ-019 | P2 | Player comparison routing | `lebron_durant_comparison_wave4` | route_mismatch | open | comparison routing / player-vs-player intent |
| AQ-020 | P1 | Playoff round and matchup phrasing | `bulls_finals_record_wave4`; `warriors_finals_record_since_2015_wave4`; `celtics_conference_finals_record_wave4`; `heat_knicks_playoff_series_record_wave4` | route_and_season_type_issue | open | playoff round/matchup routing |
| AQ-021 | P1 | Defensive stat aliases | `most_points_allowed_team_leaders_wave4`; `opponent_ppg_leaders_wave4` | stat_mapping_issue / route_mismatch | open | defensive/opponent-points stat mapping |
| AQ-022 | P2 | Unsupported stat alias boundary | `personal_foul_leaders_wave4` | unsupported_no_result_policy | open | product boundary / stat coverage |
| AQ-023 | P2 | Opponent conference filters | `celtics_against_east_record_wave4` | missing_filter / unsupported_no_result_policy | open | context filter preservation |

Short notes:

- AQ-018: position context is not exposed in returned filters; rookie/bench/starter/team-bench phrasing returns broad tables instead of supported filters or clean unsupported responses.
- AQ-019: explicit player comparison wording returns a LeBron game finder instead of a comparison.
- AQ-020: Finals/conference-finals records route to no-result or broad regular-season records; Heat/Knicks playoff series record returns single-team playoff history.
- AQ-021: points-allowed and opponent PPG variants do not bind to opponent-points team semantics.
- AQ-022: personal fouls are not documented as supported but fall back to points leaders.
- AQ-023: `against the East` is dropped and returns a full-season Celtics record.

## 7. Manual review recommendations

Review first:

- P1 playoff/history: `warriors_finals_record_since_2015_wave4`, `bulls_finals_record_wave4`, `celtics_conference_finals_record_wave4`, `heat_knicks_playoff_series_record_wave4`
- P1 defensive aliases: `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4`
- P2 role/position boundaries: `centers_rebound_leaders_wave4`, `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`
- P2 routing/context boundaries: `lebron_durant_comparison_wave4`, `personal_foul_leaders_wave4`, `celtics_against_east_record_wave4`
- Sanity pass on newly green exploratory cases: `jokic_as_starter_summary_wave4`, `malik_monk_off_bench_summary_wave4`, `heat_knicks_h2h_since_2020_wave4`, `spurs_playoff_history_since_2000_wave4`, `sga_playoff_teams_last_season_wave4`

## 8. Validation

Limited harness run:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --limit 25

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T212840Z
Cases: 25
Result statuses: {'error': 1, 'no_result': 2, 'ok': 22}
Expectation cases: {'pass': 25}
Suspicious flag cases: 0
Informational flag cases: 5
Verified outlier cases: 1
Failed case IDs: none
```

Full harness run before the expectation-only correction:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T212927Z
Cases: 195
Result statuses: {'error': 8, 'no_result': 15, 'ok': 172}
Expectation cases: {'fail': 15, 'pass': 180}
Suspicious flag cases: 8
Informational flag cases: 113
Verified outlier cases: 1
Failed case IDs: centers_rebound_leaders_wave4, rookie_scoring_leaders_wave4, bench_scoring_leaders_wave4, starter_assist_leaders_wave4, celtics_bench_scoring_boundary_wave4, heat_knicks_h2h_since_2020_wave4, lebron_durant_comparison_wave4, bulls_finals_record_wave4, warriors_finals_record_since_2015_wave4, celtics_conference_finals_record_wave4, heat_knicks_playoff_series_record_wave4, personal_foul_leaders_wave4, most_points_allowed_team_leaders_wave4, opponent_ppg_leaders_wave4, celtics_against_east_record_wave4
```

Final full harness run after correcting `heat_knicks_h2h_since_2020_wave4` to the current head-to-head-preserving `team_compare` route:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T214500Z_wave4_full

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T214500Z_wave4_full
Cases: 195
Result statuses: {'error': 8, 'no_result': 15, 'ok': 172}
Expectation cases: {'fail': 14, 'pass': 181}
Suspicious flag cases: 8
Informational flag cases: 113
Verified outlier cases: 1
Failed case IDs: centers_rebound_leaders_wave4, rookie_scoring_leaders_wave4, bench_scoring_leaders_wave4, starter_assist_leaders_wave4, celtics_bench_scoring_boundary_wave4, lebron_durant_comparison_wave4, bulls_finals_record_wave4, warriors_finals_record_since_2015_wave4, celtics_conference_finals_record_wave4, heat_knicks_playoff_series_record_wave4, personal_foul_leaders_wave4, most_points_allowed_team_leaders_wave4, opponent_ppg_leaders_wave4, celtics_against_east_record_wave4
```

Notes on command execution:

- The requested exact `.venv/bin/python` full command completed before and after
  the expectation-only correction. The unnamed post-correction run wrote
  `outputs/raw_query_answer_qa/20260513T213513Z`; the named archival rerun above
  wrote `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full`.
- The post-correction run's `summary.json` records expectation checks
  `pass: 953`, `fail: 48`.

`git diff --check`:

```text
exit 0; no output
```

Optional ruff:

```text
not run; no Python/tool code changed
```

## 9. Recommended next phase

Do not start with one-off fixes. Recommended grouped fix families:

- P1: playoff round/matchup routing for Finals/conference-finals/series-record phrasing
- P1: defensive/opponent-points aliases for allowed points and opponent PPG
- P2: position/role-filtered leaderboard support or clean unsupported handling
- P2: player comparison intent routing for explicit comparison wording
- P2: product-boundary decisions for personal fouls and opponent-conference filters

After those fixes or documented product decisions, rerun the 195-case corpus before starting frontend hero/copy QA.
