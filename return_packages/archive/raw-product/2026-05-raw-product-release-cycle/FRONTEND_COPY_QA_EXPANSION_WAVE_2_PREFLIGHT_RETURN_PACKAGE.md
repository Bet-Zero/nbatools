# Frontend-Copy QA Expansion Wave 2 Preflight Return Package

## 1. Executive summary

- Current frontend-copy coverage: 100 selected cases from `qa/frontend_copy_corpus.yaml`, sourced from `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`. The latest frontend-copy report rendered 100/100 cases with 0 render failures, 0 missing backend records, and soft checks `304/0/0`.
- Main remaining shape gaps: no selected coverage for streak tables, rolling stretches, `count_with_finder` count heroes, successful team finder tables, successful game-summary logs, team split summaries, on/off no-result surfaces, record-by-decade shapes, record-by-decade leaderboards, or lineup no-result routes.
- Recommended expansion size: medium, 100 -> 125 selected cases.
- Recommended first execution: add the 25 cases listed in section 4, using existing fragment-based soft checks first. Do not add visual/screenshot QA or production rendering changes in the same wave.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Current 100-case coverage

| Route/shape/status | Count | Notes |
|---|---:|---|
| All selected cases | 100 | Source backend run is `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`. |
| Rendered successfully | 100 | 0 render failures, 0 missing backend records. |
| Backend status `ok` | 85 | Success copy and table rendering paths. |
| Backend status `no_result` | 14 | Mostly unsupported/no-match boundary copy. |
| Backend status `error` | 1 | Unrouted cooled-off boundary. |
| Frontend `leaderboard_table` | 22 | Season/player/team/playoff appearance leaderboards. |
| Frontend `team_record` | 16 | Team record summaries; 3 selected team-record cases render two tables because they include stacked game logs. |
| Frontend no-result shapes | 15 | 13 `no_result_message`, 2 `no_result_guided`. |
| Frontend `comparison` | 11 | Player/team/head-to-head comparison panels. |
| Frontend `playoff_matchup_history` | 7 | Playoff matchup tables are well represented. |
| Frontend `entity_summary_with_gamelog` | 6 | Player summary plus game-log table. |
| Frontend `top_performances` | 5 | Player points/threes/blocks/plus-minus plus team points. |
| Frontend `game_log_player_table` | 4 | Player finder-style tables exist, but no count-with-finder cases are selected. |
| Frontend `split_table` | 4 | All are player split summaries; team split summaries are absent. |
| Frontend `entity_summary` | 3 | Plain player/entity summary hero. |
| Frontend `playoff_history` | 3 | Includes single-team playoff history/appearance variants. |
| Frontend `matchup_by_decade` | 2 | Covered by Lakers/Celtics and Warriors/Lakers cases. |
| Frontend `playoff_round_record` | 2 | Covered by second-round record variants. |
| Frontend fallback pattern | 0 | No selected case currently falls back to the generic raw table renderer. |
| Table-present selected cases | 82 | 79 selected cases render one table; 3 render two tables; 18 render no tables. |
| Missing table-heavy shapes | 0 selected | `streak_table`, `rolling_stretch`, successful `game_log_team_table`, `game_log_team_detail`, `record_by_decade`, `record_by_decade_leaderboard`, and `on_off_split`. |

## 3. Backend-to-frontend-copy gap analysis

| Backend route/shape | Backend count | Frontend-copy count | Gap | Priority |
|---|---:|---:|---|---|
| `player_streak_finder` / `streak_table` | 5 | 0 | 5 | High |
| `team_streak_finder` / `streak_table` | 4 | 0 | 4 | High |
| `player_stretch_leaderboard` / `rolling_stretch` ok | 5 | 0 | 5 | High |
| `player_stretch_leaderboard` / no-result boundary | 2 | 0 | 2 | Medium |
| `player_game_finder` / `count_with_finder` | 4 | 0 | 4 | High |
| `game_finder` / `count_with_finder` | 1 | 0 | 1 | High |
| `player_game_finder` / `game_log_table` ok | 11 | 4 | 7 | Medium-high |
| `game_finder` / `game_log_team_table` ok | 3 | 0 | 3 | High |
| `game_summary` / `game_log_team_detail` ok | 1 | 0 | 1 | High |
| `game_summary` / no-result boundary | 1 | 1 | 0 | Covered |
| `team_split_summary` / split table | 3 | 0 | 3 | High |
| `player_split_summary` / split table | 4 | 4 | 0 | Covered |
| `player_on_off` / no-result boundary | 2 | 0 | 2 | High |
| `record_by_decade` | 1 | 0 | 1 | High |
| `record_by_decade_leaderboard` | 2 | 0 | 2 | High |
| `matchup_by_decade` | 2 | 2 | 0 | Covered |
| `lineup_leaderboard` / no-result boundary | 1 | 0 | 1 | Medium-high |
| `lineup_summary` / no-result boundary | 1 | 0 | 1 | Medium-high |
| `top_player_games` / `top_performances` ok | 8 | 4 | 4 | Medium-high |
| `top_player_games` / no-result boundary | 1 | 1 | 0 | Covered |
| `top_team_games` / `top_performances` ok | 1 | 1 | 0 | Covered |

## 4. Recommended Wave 2 cases

| Bucket | Case IDs | Count | Why |
|---|---|---:|---|
| Streak/rolling/stretch shapes | `curry_3_threes_streak`, `jokic_triple_double_streak`, `lebron_active_20_point_streak`, `lakers_win_streak`, `celtics_120_point_streak`, `hottest_3_game_scoring_stretch`, `jokic_5_game_rebound_stretch`, `efficient_10_game_stretch` | 8 | Opens the two missing dedicated table shapes: `streak_table` and `rolling_stretch`, including player/team streaks, active/current wording, special-event streaks, league rolling windows, named-player windows, and efficiency metric windows. |
| Finder/count shapes | `jokic_triple_double_count`, `curry_5_threes_count`, `lakers_held_opponents_under_100_count`, `celtics_road_losses_finder`, `celtics_120_points_15_threes`, `jokic_30_points_10_assists_finder_misparsed` | 6 | Adds `count_with_finder` heroes, player finder rows, team finder rows, defensive threshold counts, compound team thresholds, and compact two-threshold player finder copy. |
| Game-summary/table-log shape | `suns_without_booker` | 1 | Adds the only successful backend `game_summary` / `game_log_team_detail` row, including summary strip, team log, and top-performer detail. |
| Split/on-off/team split shapes | `celtics_wins_losses_split`, `lakers_home_away_split_wave4`, `celtics_tatum_on_off_boundary_wave4` | 3 | Adds team split rendering plus one on/off unsupported no-result surface. Do not claim successful on/off table support from this wave. |
| Record-by-decade shapes | `warriors_record_by_decade`, `winningest_team_2010s`, `best_record_2020s_wave4` | 3 | Adds both missing record decade patterns: single-team decade breakdown and ranked decade leaderboards. |
| Top-performance variants | `most_assists_single_game`, `specific_date_jan_1` | 2 | Adds non-scoring top-player stat and date-filtered top-performance coverage. Rebounds can be a backup if one selected case proves unstable. |
| Lineup no-result boundaries | `best_5_man_lineups_unsupported`, `lineups_edwards_gobert_wave4` | 2 | Covers both lineup leaderboard and lineup summary unsupported surfaces without promoting lineup execution support. |

Detailed candidate plan:

| Case ID | Query | Backend route/shape/status | Rendered-copy value | Recommended soft checks |
|---|---|---|---|---|
| `curry_3_threes_streak` | Curry longest streak with at least 3 threes | `player_streak_finder` / `streak_table` / `ok` | Player made-threes streak table. | Semantic: Curry, threes, streak. Headers: Streak, Length, Start, End, 3PM. Filter chip: 3. |
| `jokic_triple_double_streak` | Jokic longest triple-double streak | `player_streak_finder` / `streak_table` / `ok` | Special-event player streak table. | Semantic: Nikola Jokic, triple-double, streak. Headers: Streak, Length, Start, End. Filter chip: Triple Double. |
| `lebron_active_20_point_streak` | LeBron current 20+ point streak | `player_streak_finder` / `streak_table` / `ok` | Active/current streak copy and Status column. | Semantic: LeBron James, current, 20, streak. Headers: Streak, Length, Status, PTS. |
| `lakers_win_streak` | longest Lakers winning streak | `team_streak_finder` / `streak_table` / `ok` | Team outcome streak. | Semantic: Lakers, winning, streak. Headers: Team, Streak, Length, Record. |
| `celtics_120_point_streak` | Celtics 5 straight games scoring 120+ | `team_streak_finder` / `streak_table` / `ok` | Team threshold streak shorthand. | Semantic: Celtics, 120, streak. Headers: Team, Streak, Length, PTS. |
| `hottest_3_game_scoring_stretch` | Which players have the hottest 3-game scoring stretch this year? | `player_stretch_leaderboard` / `rolling_stretch` / `ok` | League rolling scoring leaderboard. | Semantic: 3-game, scoring stretch. Headers: Rank, Player, Window, PPG, Start, End. |
| `jokic_5_game_rebound_stretch` | Jokic best 5-game rebounding stretch this season | `player_stretch_leaderboard` / `rolling_stretch` / `ok` | Named-player rolling stretch variant. | Semantic: Nikola Jokic, 5-game, rebounding. Headers: Window, RPG, Start, End. |
| `efficient_10_game_stretch` | most efficient 10-game rolling stretch | `player_stretch_leaderboard` / `rolling_stretch` / `ok` | Efficiency/TS% rolling stretch wording. | Semantic: efficient, 10-game, stretch. Headers: Window, TS%, Start, End. |
| `jokic_triple_double_count` | How often has Nikola Jokic recorded a triple-double this season? | `player_game_finder` / `count_with_finder` / `ok` | Count hero plus player game log. | Semantic: Nikola Jokic, triple-double, 34. Headers: Date, TM, Opp, PTS, REB, AST. |
| `curry_5_threes_count` | How often has Stephen Curry made 5 or more threes this year? | `player_game_finder` / `count_with_finder` / `ok` | Made-threes count hero plus finder table. | Semantic: Stephen Curry, 5, threes. Headers: Date, 3P, PTS. Filter chip: 5. |
| `lakers_held_opponents_under_100_count` | How often have the Lakers held opponents under 100 points this year? | `game_finder` / `count_with_finder` / `ok` | Defensive team count hero plus team finder table. | Semantic: Lakers, under 100, opponent. Headers: Date, Team, Opp, Opp PTS. Absent: scored the most. |
| `celtics_road_losses_finder` | Celtics road losses this season | `game_finder` / `game_log_team_table` / `ok` | Successful team finder table with location/outcome filters. | Semantic: Celtics, road, losses. Headers: Date, Team, Opp, W/L. Filter chips: Away, Losses. |
| `celtics_120_points_15_threes` | Celtics games with 120+ points and 15+ threes | `game_finder` / `game_log_team_table` / `ok` | Compound team finder table. | Semantic: Celtics, 120, 15, threes. Headers: Date, Team, PTS, 3PM. Filter chips: PTS, 3PM. |
| `jokic_30_points_10_assists_finder_misparsed` | Jokic games with 30 points and 10 assists | `player_game_finder` / `game_log_table` / `ok` | Compact compound player finder. | Semantic: Nikola Jokic, 30, 10 assists. Headers: Date, PTS, AST. |
| `suns_without_booker` | How do the Suns perform when Devin Booker didn't play? | `game_summary` / `game_log_team_detail` / `ok` | Successful game-summary log and top-performer detail path. | Semantic: Suns, without, Devin Booker. Headers: Team, Opp, PTS, Opp PTS. Semantic/heading: Top Performers or Game Detail. |
| `celtics_wins_losses_split` | Celtics wins vs losses | `team_split_summary` / `entity_summary` hint / `ok` | Team split route renders as split table despite backend approximation. | Semantic: Celtics, wins, losses. Headers: Split, GP, Record. |
| `lakers_home_away_split_wave4` | Lakers home away split this season | `team_split_summary` / `entity_summary` hint / `ok` | Team home/away split table. | Semantic: Lakers, home, away. Headers: Split, GP, Record. Filter chips: Home, Away. |
| `celtics_tatum_on_off_boundary_wave4` | Celtics net rating with Jayson Tatum on the floor vs off | `player_on_off` / `no_result` / `no_result` | On/off unsupported no-result boundary. | Semantic: Unsupported Query or Data Not Available, Jayson Tatum, on/off, play-by-play or lineup-stint. Absent: led the NBA. |
| `warriors_record_by_decade` | Warriors record by decade | `record_by_decade` / `record_by_decade` / `ok` | Single-team decade breakdown table. | Semantic: Warriors, decade. Headers: Decade, W-L, Win %. |
| `winningest_team_2010s` | winningest team of the 2010s | `record_by_decade_leaderboard` / `record_by_decade_leaderboard` / `ok` | Ranked decade leaderboard for wins. | Semantic: 2010s, winningest. Headers: Team, Wins, W-L, Decade. |
| `best_record_2020s_wave4` | best NBA record in the 2020s | `record_by_decade_leaderboard` / `record_by_decade_leaderboard` / `ok` | Decade leaderboard with recent era context. | Semantic: 2020s, record. Headers: Team, W-L, Win %, Decade. |
| `most_assists_single_game` | What were the most assists in a game this season? | `top_player_games` / `top_performances` / `ok` | Non-scoring top-player performance metric. | Semantic: assists. Headers: Player, Date, AST. |
| `specific_date_jan_1` | Who scored the most points on January 1 2026? | `top_player_games` / `top_performances` / `ok` | Date-filtered top-player performance. | Semantic: Jan 1, 2026, points. Headers: Player, Date, PTS. Filter chip: Jan 1. |
| `best_5_man_lineups_unsupported` | best 5-man lineups | `lineup_leaderboard` / `no_result` / `no_result` | Lineup leaderboard unsupported boundary. | Semantic: Unsupported Query or Data Not Available, lineup, trusted coverage unavailable. Absent: Net leaderboard success phrasing. |
| `lineups_edwards_gobert_wave4` | lineups with Anthony Edwards and Rudy Gobert | `lineup_summary` / `no_result` / `no_result` | Lineup summary unsupported boundary. | Semantic: Unsupported Query or Data Not Available, lineup, Anthony Edwards. Avoid exact teammate assertions until rendered copy is inspected. |

Backup cases if one selected case proves noisy:

- `most_rebounds_single_game`: top-player rebound metric variant.
- `wemby_5_blocks_count`: player count-with-finder defensive stat.
- `thunder_wins_losses_split_wave4`: third team split summary.
- `team_5_game_scoring_stretch`: team rolling-stretch unsupported no-result boundary.

## 5. Soft-check recommendations

| Check | Cases/family | Value | Risk |
|---|---|---|---|
| Keep existing `expected_semantic_facts` | All Wave 2 cases | Enough for entity, metric, window, unsupported-boundary, no-result title/message, count phrase, and broad heading fragments because the harness checks visible text. | Low. Avoid full sentence matching. |
| Keep existing `expected_table_header_fragments` | Streak, rolling stretch, finder, game summary, split, record-by-decade, top-performance cases | Verifies the table family rendered: Streak/Length, Window/Start/End, Date/Opp, Split/GP/Record, Decade/W-L/Win %, AST/PTS. | Low. Header fragments are stable and intentionally not exact full tables. |
| Keep existing `expected_filter_chip_fragments` | Threshold, date, location, outcome, special-event, and window cases | Verifies key filters survive into envelope chips or context items. | Low. Use alternatives when labels may abbreviate, such as `[3PM, 3P]` or `[Jan 1, Jan]`. |
| Keep existing `expected_absent_fragments` | Defensive count/no-result and unsupported boundary cases | Guards against promoted unsupported success copy or offensive wording for defensive metrics. | Medium. Keep absent fragments narrow, for example `scored the most` or `led the NBA`. |
| Optional future `expected_section_heading_fragments` | Rolling stretch named-player detail, game summary top-performer detail, raw detail drawers | Would scope checks to headings instead of full text. | Low, but not required for the first Wave 2 execution. Add only if existing semantic checks produce false positives. |
| Optional future `expected_no_result_title_fragments` | On/off and lineup unsupported no-results | Would make no-result title checks explicit instead of relying on visible text. | Low, but not required unless the execution wave finds title/message false positives. |
| Not recommended now: exact row-label checks | Table-heavy cases | First-row exact labels are more brittle than headers and semantic facts. | Medium-high. Use only for a regression tied to a known row-label bug. |

Conclusion: existing soft-check fields are enough for the first 100 -> 125 execution. The only likely harness additions worth considering later are `expected_section_heading_fragments` and `expected_no_result_title_fragments`, and only if the first implementation finds that full visible-text checks are too loose.

## 6. Rendering-risk findings

| Case/shape | Risk | Recommendation |
|---|---|---|
| `count_with_finder` backend shapes | Frontend does not classify these as a separate `count_with_finder` shape. They render through `game_log_player_table` or `game_log_team_table`, with the count phrase as the hero when metadata exposes `primary_count` / `count_phrase`. | Safe to add, but soft checks should target the count phrase plus game-log headers. Do not expect frontend `result_shape_key` to equal `count_with_finder`. |
| `team_split_summary` backend shape hint | Backend approximation reports `entity_summary`, while `routeToPattern` renders the route as `split_table`. | Safe to add. Treat actual frontend shape as `split_table`; do not use backend `shape_hint` as the only shape oracle. |
| `player_on_off` selected candidate | Backend returns `no_result` unsupported; it does not cover successful `on_off_split` rendering. | Add one no-result boundary case only. A successful on/off split should be a separate backend/data/rendering wave. |
| `lineup_summary` and `lineup_leaderboard` selected candidates | Backend returns unsupported no-result. Lineup execution remains unsupported. | Add only as no-result boundary coverage. Do not promote lineup support in docs or copy. |
| `lineups_edwards_gobert_wave4` | Backend metadata should be treated cautiously for entity details in a no-result route; the query text is the stable user-facing fact. | Use loose unsupported/lineup checks and avoid exact teammate checks until the execution wave inspects rendered copy. |
| `record_by_decade` | Current contract stores decade rows in `by_season` for backward compatibility. | Safe to add; this is documented current behavior in `core_result_table_contracts.md`. |
| Missing dedicated patterns | No candidate route in the recommended 25 requires fallback rendering. | No production rendering change is needed before corpus expansion. Stop if any selected candidate renders as `fallback_table` unexpectedly. |

## 7. Backend safety loop

- Raw harness commands if needed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case curry_3_threes_streak --case jokic_triple_double_streak --case lebron_active_20_point_streak --case lakers_win_streak --case celtics_120_point_streak --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case hottest_3_game_scoring_stretch --case jokic_5_game_rebound_stretch --case efficient_10_game_stretch --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case jokic_triple_double_count --case curry_5_threes_count --case lakers_held_opponents_under_100_count --case celtics_road_losses_finder --case celtics_120_points_15_threes --case jokic_30_points_10_assists_finder_misparsed --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case suns_without_booker --case celtics_wins_losses_split --case lakers_home_away_split_wave4 --case celtics_tatum_on_off_boundary_wave4 --case warriors_record_by_decade --case winningest_team_2010s --case best_record_2020s_wave4 --case most_assists_single_game --case specific_date_jan_1 --case best_5_man_lineups_unsupported --case lineups_edwards_gobert_wave4 --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

- Whether full raw corpus should run: no, not for Wave 2 corpus-only execution if the source remains `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl` and backend behavior is unchanged.
- Expected backend status: unchanged from the clean 243/243 source run. Run direct `--case` probes only if the execution wave finds a selected case has unexpected frontend copy or needs risk triage.

## 8. Recommended execution scope

- Target case count: 125 selected frontend-copy cases.
- Cases/families to add: the 25 IDs in section 4.
- Files likely to change:
  - `qa/frontend_copy_corpus.yaml` only, if existing soft-check fields are sufficient.
  - `frontend/src/test/frontendCopyQaHarness.tsx` only if `expected_section_heading_fragments` or `expected_no_result_title_fragments` becomes necessary after a failed first pass.
  - `frontend/src/test/frontendCopyQaReport.test.tsx` should not need changes because current gating already checks selected count, render failures, missing backend records, soft-check failures, and unchecked soft checks.
  - No production rendering files should change in this wave.
- Tests/harness changes: none recommended for the first execution. Add harness fields only if an existing-field soft check cannot express a real risk without becoming too broad.
- Validation commands:

```bash
cd frontend && npm run qa:frontend-copy
```

```bash
cd frontend && npm test -- src/test/frontendCopyQaReport.test.tsx
```

```bash
git diff --check
```

- Stop conditions:
  - Any selected case renders as `fallback_table`.
  - Any selected case has a render failure or missing backend record.
  - Any selected successful shape exposes misleading copy that cannot be checked with loose fragments.
  - Any lineup/on-off no-result candidate appears to promote unsupported support.
  - Any backend direct-case probe differs from `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`.

## 9. Validation performed

Files inspected:

- `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_1_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_PREFLIGHT_RETURN_PACKAGE.md`
- `qa/frontend_copy_corpus.yaml`
- `qa/raw_query_answer_corpus.yaml`
- `outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.md`
- `outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.jsonl`
- `outputs/frontend_copy_qa/20260517T051450Z/summary.json`
- `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`
- `outputs/raw_query_answer_qa/20260517T033806Z/summary.json`
- `frontend/src/test/frontendCopyQaHarness.tsx`
- `frontend/src/test/frontendCopyQaReport.test.tsx`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/resultShapes.ts`
- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/SplitResult.tsx`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
- `frontend/src/components/results/patterns/FallbackTableResult.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `docs/reference/result_contracts/core_result_table_contracts.md`

Commands/probes run:

```bash
git status --short
```

```bash
sed -n '1,220p' return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_1_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_PREFLIGHT_RETURN_PACKAGE.md
sed -n '1,260p' outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.md
sed -n '1,5p' outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.jsonl
sed -n '1,5p' outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
sed -n '1,220p' outputs/frontend_copy_qa/20260517T051450Z/summary.json
sed -n '1,220p' outputs/raw_query_answer_qa/20260517T033806Z/summary.json
```

```bash
sed -n '1,980p' frontend/src/test/frontendCopyQaHarness.tsx
sed -n '1,260p' frontend/src/test/frontendCopyQaReport.test.tsx
sed -n '1,260p' frontend/src/components/results/config/routeToPattern.ts
sed -n '1,520p' frontend/src/components/results/resultShapes.ts
sed -n '1,260p' frontend/src/components/NoResultDisplay.tsx
sed -n '1,620p' frontend/src/components/ResultEnvelope.tsx
sed -n '1,260p' docs/reference/result_contracts/core_result_table_contracts.md
```

```bash
sed -n '1,320p' frontend/src/components/results/patterns/StreakResult.tsx
sed -n '1,320p' frontend/src/components/results/patterns/RollingStretchResult.tsx
sed -n '1,320p' frontend/src/components/results/patterns/GameLogResult.tsx
sed -n '1,320p' frontend/src/components/results/patterns/SplitResult.tsx
sed -n '1,320p' frontend/src/components/results/patterns/RecordResult.tsx
sed -n '1,260p' frontend/src/components/results/patterns/TopPerformancesResult.tsx
sed -n '1,260p' frontend/src/components/results/patterns/FallbackTableResult.tsx
```

```bash
rg -n "streak|stretch|finder|game_summary|record_by_decade|team_split|on_off|lineup|top_player_games|top_team_games|count" qa/raw_query_answer_corpus.yaml
rg -n "streak|stretch|finder|game_summary|record_by_decade|team_split|on_off|lineup|top_player_games|top_team_games|count" qa/frontend_copy_corpus.yaml
```

```bash
node <<'NODE'
// Coverage-count probe over frontend_copy_report.jsonl and backend report.jsonl.
// Computed frontend route counts, frontend shape counts, status counts,
// backend route/shape counts, and unselected target candidates.
NODE
```

```bash
node <<'NODE'
// Targeted gap-table probe for player_streak_finder, team_streak_finder,
// player_stretch_leaderboard, count_with_finder, game_finder,
// game_summary, team_split_summary, player_on_off, record_by_decade,
// lineup, and top-performance routes.
NODE
```

```bash
node <<'NODE'
// Candidate-detail probe for the 25 recommended IDs, including query,
// route, shape_hint, status, result_reason, section row counts,
// stat/window/split metadata, and applied filters.
NODE
```

No production code, test code, corpus expectations, backend behavior, frontend rendering, or visual QA automation was changed.
