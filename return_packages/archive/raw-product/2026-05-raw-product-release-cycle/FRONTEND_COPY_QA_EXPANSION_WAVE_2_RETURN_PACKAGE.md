# Frontend-Copy QA Expansion Wave 2 Return Package

## 1. Executive summary

- What changed: expanded `qa/frontend_copy_corpus.yaml` from 100 to exactly 125 selected frontend-copy cases, targeting undercovered rendered result shapes from the existing clean backend source run.
- Production code changed? no
- Frontend rendering changed? no
- Harness/test code changed? yes, only the frontend-copy selected-count gate changed from 100 to 125.
- Frontend-copy corpus size before/after: 100 -> 125 selected cases.
- Source backend run: `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`
- Latest frontend-copy run: `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md`
- Remaining risk: selected DOM-copy coverage only, not all 243 backend cases; no visual/screenshot QA; on/off and lineup cases are unsupported no-result boundary coverage only.

## 2. Corpus expansion summary

| Bucket | Cases added | Purpose |
|---|---:|---|
| Streak/rolling/stretch shapes | 8 | Add player/team streak tables and player rolling-stretch tables. |
| Finder/count shapes | 6 | Add count-with-finder heroes, player finder tables, and successful team finder tables. |
| Game-summary/table-log shape | 1 | Add the successful `game_summary` / `game_log_team_detail` path. |
| Split/on-off/team split shapes | 3 | Add successful team split tables and an on/off unsupported boundary. |
| Record-by-decade shapes | 3 | Add single-team decade records plus decade leaderboard tables. |
| Top-performance variants | 2 | Add non-scoring and date-filtered top-player performance cases. |
| Lineup no-result boundaries | 2 | Add lineup leaderboard and lineup summary unsupported boundaries. |

## 3. Shape coverage added

| Shape/family | Cases | Coverage value |
|---|---|---|
| `streak_table` | `curry_3_threes_streak`, `jokic_triple_double_streak`, `lebron_active_20_point_streak`, `lakers_win_streak`, `celtics_120_point_streak` | Covers player threshold, special-event, completed/current phrasing, team outcome, and team threshold streak rendering. |
| `rolling_stretch` | `hottest_3_game_scoring_stretch`, `jokic_5_game_rebound_stretch`, `efficient_10_game_stretch` | Covers league, named-player, scoring, rebounding, and efficiency rolling-window tables. |
| Finder/count tables | `jokic_triple_double_count`, `curry_5_threes_count`, `lakers_held_opponents_under_100_count`, `celtics_road_losses_finder`, `celtics_120_points_15_threes`, `jokic_30_points_10_assists_finder_misparsed` | Covers player and team finder rows, count heroes, defensive thresholds, and compound thresholds. |
| `game_log_team_detail` | `suns_without_booker` | Covers the successful game-summary log plus detail drawer path. |
| `split_table` / unsupported on/off | `celtics_wins_losses_split`, `lakers_home_away_split_wave4`, `celtics_tatum_on_off_boundary_wave4` | Covers team split rendering and no-result on/off boundary copy. |
| Decade records | `warriors_record_by_decade`, `winningest_team_2010s`, `best_record_2020s_wave4` | Covers single-team decade breakdown and ranked decade leaderboard rendering. |
| `top_performances` variants | `most_assists_single_game`, `specific_date_jan_1` | Covers assist metric and date-filtered scoring top-performance tables. |
| Lineup unsupported boundaries | `best_5_man_lineups_unsupported`, `lineups_edwards_gobert_wave4` | Covers lineup no-result surfaces without promoting lineup support. |

## 4. Soft-check coverage

| Family | Checks added | Notes |
|---|---|---|
| Streaks | Entity/context semantic fragments, table headers, stable threshold/special-event chips. | The LeBron source row renders a completed 20-point streak, so no `Status` header assertion is used. |
| Rolling stretches | Window/metric semantic fragments and `Window`, metric, `Start`, `End` headers. | Uses alternatives for efficiency wording (`efficient`, `true-shooting`, `TS%`). |
| Finder/count | Count/entity/context fragments, game-log headers, threshold/location/outcome chips where stable. | Count-with-finder backend shapes render as game-log player/team shapes in the frontend, as expected. |
| Game summary | Suns/Booker/without semantic fragments and team game-log headers. | No top-performer heading assertion was added. |
| Splits | Team/split semantic fragments plus `Split`, `GP`, `Record` headers. | Team split backend shape hints remain approximations; frontend shape is `split_table`. |
| Unsupported on/off/lineup | Unsupported/no-result semantic fragments and narrow absent-fragment guards. | These are unsupported boundary checks only. |
| Decade records | Team/decade semantic fragments and decade/record leaderboard headers. | Confirms both decade result shapes render without fallback. |
| Top performances | Metric/date semantic fragments, table headers, and date chip where stable. | No exact row-label assertions. |

## 5. Frontend-copy validation

Command:

```bash
cd frontend && npm run qa:frontend-copy
```

Report path:

- `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md`

Result:

| Item | Value |
|---|---:|
| Selected cases | 125 |
| Rendered successfully | 125 |
| Render failures | 0 |
| Missing backend records | 0 |
| Soft checks pass/fail/not checked | `475/0/0` |

Notable report findings:

- The 25 Wave 2 cases rendered as `streak_table: 5`, `rolling_stretch: 3`, `game_log_player_table: 3`, `game_log_team_table: 3`, `game_log_team_detail: 1`, `split_table: 2`, `no_result_message: 3`, `record_by_decade: 1`, `record_by_decade_leaderboard: 2`, and `top_performances: 2`.
- No Wave 2 case rendered as `fallback_table`.
- All selected IDs existed in the configured source backend run.

## 6. Backend safety validation

No backend direct-case raw harness probes were run. This wave did not change backend code, raw backend corpus expectations, or the configured source backend run. A source-report inspection confirmed the 25 selected IDs exist in `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl` with the expected routes/statuses.

## 7. Standard validation

| Command | Result |
|---|---|
| `cd frontend && npm run qa:frontend-copy` | Passed: 1 test file, 4 tests; latest report `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md`. |
| `cd frontend && npm test -- src/test/frontendCopyQaReport.test.tsx` | Passed: 1 test file, 4 tests. |
| `cd frontend && npm run lint` | Passed with 0 errors and the existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning. |
| `git diff --check` | Passed. |

## 8. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/frontend_copy_corpus.yaml` | Corpus expansion | Added exactly 25 selected frontend-copy cases and loose soft checks. |
| `frontend/src/test/frontendCopyQaReport.test.tsx` | Test gate update | Updated selected/rendered count assertions from 100 to 125. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Docs update | Recorded the 125-case frontend-copy run and Wave 2 shape coverage. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | Docs update | Updated frontend-copy status, validation path, and remaining limitations. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Docs update | Added Wave 2 frontend-copy status and latest run summary. |
| `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md` | New return package | Captures scope, validation, changed files, and recommendation. |

## 9. Next recommendation

Release packaging is the best next step if the goal is to ship the current supported and explicitly unsupported product boundary. Choose frontend-copy expansion wave 3 only after a fresh gap analysis identifies meaningful remaining rendered-shape risk.
