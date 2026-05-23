# Frontend-Copy QA Expansion Preflight Return Package

## 1. Executive summary

- Current frontend-copy coverage: `qa/frontend_copy_corpus.yaml` selects 59
  cases. The latest clean report is
  `outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.md` with
  59 rendered cases, 0 render failures, 0 missing backend records, and soft
  checks `160/0/0`.
- Main coverage gaps: the frontend-copy corpus is pinned to
  `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`, which has
  195 backend rows. The latest clean backend run,
  `outputs/raw_query_answer_qa/20260517T033806Z`, has 243 rows, so the current
  frontend-copy setup cannot select Wave 5 / Wave 8-family case IDs without
  first refreshing the configured source backend run. Coverage is also thin for
  no-result/unsupported copy, team/date records, defensive/opponent-points
  variants, playoff phrasing variants, comparison variants, streak/rolling
  shapes, and finder/count table shapes.
- Recommended expansion size: medium, from 59 to exactly 100 selected cases.
  Add 41 cases after updating the frontend-copy source backend run to the
  latest clean 243-case run or a new clean full raw run.
- Recommended first execution: refresh `source_backend_run`, add the 41
  selected high-copy-risk cases listed below, add targeted fragment-based soft
  checks, and make nonzero render/missing/soft-check failures fail the
  frontend-copy QA command.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Current frontend-copy setup

| Area | Finding | Notes |
|---|---|---|
| Corpus file | `qa/frontend_copy_corpus.yaml` | Defines `version`, `source_backend_run`, description, and selected cases. |
| Selected cases | 59 | The clean report confirms 59 selected, rendered successfully. |
| Source backend mapping | Selected case IDs are joined to backend QA JSONL rows by `id`. | Implemented in `frontend/src/test/frontendCopyQaHarness.tsx::loadBackendQaRecords()` and `buildFrontendCopyReport()`. |
| Source backend run | Fixed configured path: `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`. | That source has 195 rows; latest clean backend run has 243 rows. |
| Latest-run behavior | Does not auto-discover latest raw run. | `buildFrontendCopyReport()` accepts an override path, but `npm run qa:frontend-copy` uses the corpus path by default. |
| Runner | `frontend/src/test/frontendCopyQaReport.test.tsx` + `frontend/src/test/frontendCopyQaHarness.tsx`. | There is no `tools/frontend_copy_qa.py`; the equivalent runner is the Vitest harness. |
| Render path | Rehydrates backend JSONL into `QueryResponse`, renders `ResultEnvelope` and `ResultRenderer` in review mode, and extracts DOM copy. | This checks rendered copy, table headers, top rows, filter chips, no-result text, notes/caveats, and headings. |
| Current route coverage | Covers `team_record`, `player_game_summary`, `season_leaders`, `season_team_leaders`, `top_player_games`, `top_team_games`, playoff routes, comparison routes, split routes, and a few no-result/error shapes. | Latest-route selected counts include `team_record: 10`, `season_leaders: 9`, `player_game_summary: 7`, `top_player_games: 5`, `season_team_leaders: 4`, `player_split_summary: 4`, `player_compare: 3`, `playoff_matchup_history: 3`. |
| Current rendered shapes | Covers Comparison Panels, Entity Summary, Entity Summary + Recent Games, Guided No Result, Message No Result, Leaderboard Table, Matchup By Decade, Player Game Log, Playoff History, Playoff Matchup History, Playoff Round Records, Split Comparison, Team Record, and Top Performances. | No current frontend-copy cases render Streak Table, Rolling Stretch, Team Game Log, Game Summary Log, Record By Decade, Record By Decade Leaderboard, Team Split Summary, On/Off Split, or lineup shapes. |
| Soft checks | Current supported fields are `expected_semantic_facts`, `expected_table_header_fragments`, `expected_filter_chip_fragments`, and `expected_absent_fragments`. | Checks are loose substring checks with array alternatives; haystacks are visible text, table headers, and filter/context chips. |
| Automatic vs manual | The harness automatically produces render/missing/soft-check metrics and report artifacts. The current tests gate corpus loading, ID mapping, representative rendering, and report writing. | The all-case report summary is the main review artifact. Nonzero all-case soft-check failures are reported, but the write-report test does not currently assert `fail === 0`. |
| Unsupported/no-result coverage | Yes, but selected. | Current selected cases include date no-match, cooled-off unsupported, rookie leaderboard, starter/bench leaderboard, opponent-conference filter, and personal-foul leaderboard. It does not cover single-team advanced scalar, team bench scoring, or Wave 5 variants. |
| Defensive/opponent-points coverage | Yes, but partial. | Current selected cases include held/allowed threshold records and points-allowed/opponent-PPG leaderboards. It does not directly cover Wave 5 `gave up`, `held teams`, and `teams allowing` phrasing. |
| Playoff matchup/history coverage | Yes, but partial. | Current selected cases cover Lakers history, Finals appearances, appearance leaderboard, second-round record, Spurs since-2000 history, Heat/Knicks and Lakers/Celtics matchup forms, series record, and by-decade matchup. Wave 5 no-`vs`, series-history, Finals-history, and unsupported single-team round-record boundaries are not selected. |
| Comparison coverage | Yes, but partial. | Current selected cases include player, team, head-to-head, range, last-10, and LeBron/Durant wave4 comparison. Wave 5 imperative/recent/team-record variants are not selected. |
| Filtered leaderboard hero coverage | Yes, but narrow. | Current selected cases include guards FG% and centers rebounds with `expected_absent_fragments: led the NBA`. Other position/advanced combinations are unselected. |
| Mobile/layout scope | Out of scope for frontend-copy QA. | Frontend-copy uses DOM text extraction, not screenshot or layout assertions. Visual/mobile QA should remain separate. |

## 3. Coverage gap analysis

| Backend family / route | Backend coverage | Frontend-copy coverage | Gap | Priority |
|---|---:|---:|---|---|
| Full backend corpus | 243 | 59 | 184 backend cases are not rendered in frontend-copy. | High |
| Backend source available to frontend-copy | 243 latest / 195 configured | 59 selected from configured source | Current source predates the latest 243-case run and excludes Wave 5 / Wave 8-family additions. | High |
| `season_leaders` / player leaderboards | 43 route rows; 40 leaderboard-category rows | 9 route rows; 8 category rows | Standard, advanced, position-filtered, stat-alias, and unsupported leaderboard variants are underrepresented. | High |
| `season_team_leaders` / team leaderboards | 18 | 4 | Defensive/opponent-points aliases and advanced team leaderboard copy need broader rendered-copy checks. | High |
| `team_record` | 35 route rows; 22 team-record category rows | 10 route rows; 5 category rows | Road/home, since-date, month-window, last-season, last-10, opponent-conference no-result, and `how did TEAM do` copy need more coverage. | High |
| `player_game_summary` / entity summary | 27 route rows; 22 player-summary category rows | 7 route rows; 5 category rows | Recent/stat-context, role-context, opponent-quality, and player-vs-player-as-opponent wording need more coverage. | High |
| Unsupported / no-result statuses | 41 total (`no_result: 32`, `error: 9`) | 7 total (`no_result: 6`, `error: 1`) | Product boundaries are the highest copy-risk area because wording must avoid promoting unsupported features or implying success. | High |
| Playoff history routes | 17 combined (`playoff_history`, `playoff_appearances`, `playoff_round_record`) | 5 combined | Recent playoff phrasing fixes and unsupported single-team Finals/conference-finals boundaries need rendered-copy coverage. | High |
| Playoff matchup / by-decade routes | 9 combined (`playoff_matchup_history`, `matchup_by_decade`) | 5 combined | Current coverage is decent, but Wave 5 no-`vs`, series-history, matchup-history, and Finals-history phrasing is absent. | Medium-high |
| Comparison routes | 12 combined (`player_compare`, `team_compare`, `team_matchup_record`) | 6 combined | Wave 5 imperative comparison, last-10 comparison, recent-form comparison, and team-record comparison variants are absent. | Medium-high |
| Top performances | 10 combined (`top_player_games`, `top_team_games`) | 6 combined | Core single-game top-performance copy is covered; date-filtered top-scorer and non-scoring variants remain gaps. | Medium |
| Finder/count/game-log routes | 25 combined (`player_game_finder`, `game_finder`, `game_summary`) plus 5 `count_with_finder` shape hints | 1 route row, 0 `count_with_finder` shape hints | Table-only/finder copy, count context, and game-summary detail shapes are barely covered. | Medium |
| Streak and rolling stretch | 16 combined (`player_streak_finder`, `team_streak_finder`, `player_stretch_leaderboard`) | 0 | Shape coverage gap. Lower copy risk than unsupported/playoff/defensive cases, but should be added in a later expansion. | Medium |
| Split/on-off/team split | 9 combined (`player_split_summary`, `team_split_summary`, `player_on_off`) | 4 player-split rows only | Team split and on/off no-result rendering are not covered. | Medium |
| Record by decade / decade leaderboard | 3 combined | 0 | Era record copy is not covered except matchup-by-decade. | Medium-low |
| Lineup routes | 2 combined | 0 | Current product boundary is mostly data availability/unsupported; not a first expansion priority unless no-result copy changes. | Low |

High-risk copy gaps by family:

- Defensive/opponent-points wording: current coverage checks canonical
  allowed/opponent-PPG cases, but not Wave 5 `gave up`, `held teams`, or
  `teams allowing` wording.
- Filtered leaderboard hero context: current guards/centers checks are useful,
  but other position filters and advanced metrics need the same `not led the
  NBA generically` protection.
- Playoff matchup/history phrasing: current selected cases cover baseline
  matchup/history forms, but not the latest no-`vs`, series-history,
  Finals-history, and single-team unsupported round-record boundaries.
- Unsupported/no-result guidance: current selected cases cover some boundaries,
  but not single-team advanced scalar, team bench scoring, Wave 5 personal-foul,
  Wave 5 rookie, opponent-West filter, or clutch unsupported wording.
- Date/window phrasing: current selected cases cover last season and All-Star,
  but not January 1, March, home 2024-25, and last-10 team-record variants.
- Comparison edge/difference wording: current coverage checks baseline
  comparisons, but not Wave 5 imperative/recent/team-record variants.
- Wave 5 / Wave 8-family fixes: no Wave 5 IDs are selected today because the
  configured source backend run has only 195 rows.

## 4. Recommended case buckets

Target: add these 41 IDs for a 100-case frontend-copy corpus.

| Bucket | Suggested cases | Why |
|---|---|---|
| Supported leaderboard copy | `forwards_efg_leaders_wave4`, `point_guard_assist_leaders_wave4`, `centers_blocks_leaders_wave4`, `who_had_highest_true_shooting_wave5`, `true_shooting_leaders_phrase_wave5`, `who_averaged_blocks_wave5` | Adds position-filtered, advanced-stat, defensive-stat, and question/fragment phrasing coverage beyond current points/guards/centers checks. |
| Defensive/team allowed/opponent PPG copy | `team_gave_up_fewest_ppg_wave5`, `teams_allowing_fewest_points_wave5`, `opponent_points_per_game_leaders_wave5`, `lakers_held_teams_under_100_wave5`, `warriors_gave_up_under_100_wave5` | Directly targets historically risky allowed/gave-up/opponent-points wording and recent defensive alias fixes. |
| Team record date/window copy | `lakers_how_did_road_last_season_wave5`, `celtics_road_record_since_jan_1_wave5`, `knicks_record_in_march_wave5`, `lakers_home_record_2024_25_wave5`, `warriors_last_10_record_wave5` | Adds rendered-copy coverage for search-bar phrasing, road/home, since-date, month window, explicit season, and last-N team record copy. |
| Player/entity/stat context copy | `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `sga_scoring_since_all_star_wave5`, `tatum_points_in_wins_wave5`, `malik_monk_off_bench_summary_wave4` | Covers possessive record-when phrasing, threes/from-three stat context, All-Star date context, wins split context, and supported role-context copy. |
| Playoff/history copy | `heat_knicks_playoff_history_no_vs_wave5`, `lakers_celtics_playoff_series_history_wave5`, `warriors_cavs_finals_history_wave5`, `lakers_celtics_playoff_matchup_history_wave5`, `most_conf_finals_appearances_since_2000_wave5`, `best_second_round_record_since_2010_wave5` | Adds latest playoff phrasing variants and era/round context without expanding the visual QA surface. |
| Playoff unsupported boundary copy | `bulls_finals_record_question_wave5`, `celtics_record_in_conference_finals_wave5` | Guards against promoting unsupported single-team Finals/conference-finals record splits. |
| Comparison copy | `compare_lebron_durant_wave5`, `lebron_durant_last10_wave5`, `compare_jokic_embiid_recent_wave5`, `celtics_bucks_comparison_this_season_wave5`, `warriors_lakers_record_this_season_wave5` | Adds imperative comparison, recent comparison, player comparison, team comparison, and team head-to-head record variants. |
| Unsupported boundary copy | `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`, `rookie_assist_leaders_wave5`, `celtics_bench_points_wave5`, `lakers_record_against_west_wave5`, `most_clutch_player_wave5` | Covers personal-foul, single-team advanced scalar, rookie leaderboard, team bench scoring, opponent-conference, and subjective/clutch unsupported boundaries. |

Recommended deferrals for the next wave after this one:

- Streak and rolling-stretch rendered-copy shapes.
- Finder/count shape coverage (`count_with_finder`, `game_finder`,
  `game_summary`) beyond selected stat-context additions.
- Record-by-decade and record-by-decade leaderboard copy.
- Lineup unsupported/data-availability copy.
- Broader top-performance date-filtered and non-scoring variants.

## 5. Soft-check recommendations

| Check | Cases/family | Value | Risk |
|---|---|---|---|
| Make all-case report failures gating in `qa:frontend-copy` | All selected cases | Prevents a green command when a selected case has render failures, missing backend records, soft-check failures, or `not_checked` checks. | Low. This is not exact-copy overfitting; it only gates the selected fragment checks already authored. |
| Add hero-scoped fragment checks | Leaderboards, comparisons, playoff matchup, record/date cases | Checks high-risk hero wording without matching entire sentences. | Medium. Requires extending the harness beyond full visible-text fragments. Keep fragments short. |
| Add hero-scoped absent-fragment checks | Filtered leaderboards and defensive/opponent-points cases | Guards against generic `led the NBA` for filtered leaderboards and `scored` wording for allowed/opponent-points team leaderboards. | Medium. Avoid broad absent terms that appear elsewhere in table labels. |
| Add no-result title/message fragment checks | Unsupported boundaries and no-result date cases | Verifies unsupported cards use boundary-specific wording like `Unsupported Leaderboard`, `Unavailable Filter`, `Personal-foul leaderboards`, `single-team net rating`, or `No Matching Results`. | Low. Current no-result extraction already captures title/message/details. |
| Add backend status/reason/shape expectations to frontend-copy corpus | Unsupported/no-result selected cases | Ensures unsupported cases do not silently become `ok` rendered tables, and no-match cases do not claim success. | Low-medium. Keep route/status expectations aligned with raw QA records; do not duplicate full backend assertions. |
| Position-filter hero check | Position-filtered leaderboards | Require visible/hero copy to mention `guards`, `centers`, `forwards`, or `point guards`, and require `expected_absent_fragments: led the NBA` where appropriate. | Low. Existing corpus already uses this pattern for guards/centers. |
| Defensive/opponent-points wording check | `team_gave_up_fewest_ppg_wave5`, `teams_allowing_fewest_points_wave5`, `opponent_points_per_game_leaders_wave5`, threshold record cases | Require one of `allowed`, `gave up`, `opponent points`, or `points allowed`; reject `scored the fewest/most` in the hero. | Medium. Scope to hero text so ordinary table stat labels do not cause false positives. |
| Playoff matchup entity check | Playoff matchup/history cases | Require both teams in hero or visible text, plus `playoff`/`series` where relevant. | Low. Already compatible with current semantic facts. |
| Comparison entity check | Player/team comparison cases | Require both compared players/teams and either comparison/head-to-head context or the comparison table heading. | Low. Current semantic facts cover entities but not always comparison context. |
| Date/window context check | Since-date, month, last-season, last-10, All-Star cases | Require `Jan`, `March`, `2024-25`, `last 10`, or `All-Star` to appear in rendered copy or applied filters. | Low. Current filter-chip checks can cover some of this today. |
| Stat-context check | `from three`, threes, TS/eFG, blocks/steals | Require `threes`/`from three`, `true shooting`, `effective field-goal`, `blocks`, or `steals` as appropriate. | Low. Prefer alternatives for abbreviations like `TS%`, `eFG%`, `3PM`. |

Do not add exact full-sentence expectations in this wave. The useful target is
semantic copy confidence: entity, metric, scope, unsupported boundary, and
dangerous absent phrases.

## 6. Backend safety loop

- Raw harness commands using `--slice` / `--compare-to`:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice defensive_aliases --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice playoff_phrasing --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice team_date_context --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice player_entity_stat_context --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

For comparison cases, either run direct case selection:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl --case compare_lebron_durant_wave5 --case lebron_durant_last10_wave5 --case compare_jokic_embiid_recent_wave5 --case celtics_bucks_comparison_this_season_wave5 --case warriors_lakers_record_this_season_wave5
```

Or add a saved comparison slice in the execution wave if repeated comparison
loops are expected.

- Whether full raw corpus should run: no full run is needed at the start if
  `outputs/raw_query_answer_qa/20260517T033806Z` remains the source. Run a new
  full raw corpus only if the execution wave wants a fresh `source_backend_run`
  path for frontend-copy. If any selected slice changes backend behavior or the
  source run is stale, run the full corpus once at the end and point
  `source_backend_run` at that clean output.
- Expected backend status: no backend behavior changes expected. The selected
  raw slices should remain expectation-case pass with no failed IDs, matching
  the clean 243/243 run.

## 7. Recommended execution scope

- Target case count: exactly 100 frontend-copy cases.
- Cases/families to add: the 41 IDs listed in section 4.
- Files likely to change:
  - `qa/frontend_copy_corpus.yaml`: update `source_backend_run` and add selected
    cases with semantic facts / table fragments / filter fragments / absent
    fragments.
  - `frontend/src/test/frontendCopyQaHarness.tsx`: only if adding new soft-check
    fields such as hero-scoped or no-result-scoped checks.
  - `frontend/src/test/frontendCopyQaReport.test.tsx`: add gating assertions for
    render failures, missing backend records, soft-check failures, and
    unchecked cases.
  - No production rendering files should change.
- Tests to add/update:
  - Add or update harness tests for any new soft-check field.
  - Add a report-level assertion that the selected corpus produces 0 render
    failures, 0 missing backend records, 0 soft-check failures, and 0
    `not_checked` checks.
- Validation commands:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice defensive_aliases --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice playoff_phrasing --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice team_date_context --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice player_entity_stat_context --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries --compare-to outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl
```

```bash
cd frontend && npm run qa:frontend-copy
```

```bash
git diff --check
```

- Stop conditions:
  - Any selected backend slice has failed raw expectations.
  - The configured `source_backend_run` does not contain every selected case ID.
  - Frontend-copy render failures or missing backend records are nonzero.
  - Soft-check failures are nonzero after case fragments are reviewed for
    brittleness.
  - Any unsupported/no-result selected case renders as a successful supported
    answer.
  - Any recommended case requires production rendering or backend query changes
    to pass. That means the expansion has found a product issue and should stop
    for a separate fix wave.
  - Any visual/mobile concern appears. Keep it out of frontend-copy expansion
    and route it to visual QA.

## 8. Validation performed

Files inspected:

- `return_packages/raw-product/RAW_QA_HARNESS_EFFICIENCY_WAVE_1_RETURN_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `outputs/raw_query_answer_qa/20260517T033806Z/report.md`
- `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`
- `outputs/raw_query_answer_qa/20260517T033806Z/summary.json`
- `outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.md`
- `outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.jsonl`
- `outputs/frontend_copy_qa/20260516T230102Z/summary.json`
- `qa/frontend_copy_corpus.yaml`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/defensive_aliases.yaml`
- `qa/harness_slices/playoff_phrasing.yaml`
- `qa/harness_slices/team_date_context.yaml`
- `qa/harness_slices/player_entity_stat_context.yaml`
- `qa/harness_slices/product_boundaries.yaml`
- `frontend/src/test/frontendCopyQaReport.test.tsx`
- `frontend/src/test/frontendCopyQaHarness.tsx`
- `frontend/src/components/results/resultShapes.ts`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/noResultDisplayUtils.ts`
- `docs/reference/result_contracts/core_result_table_contracts.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

Commands/probes run:

```bash
sed -n '1,220p' return_packages/raw-product/RAW_QA_HARNESS_EFFICIENCY_WAVE_1_RETURN_PACKAGE.md
```

```bash
sed -n '1,260p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md
```

```bash
sed -n '1,260p' docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md
```

```bash
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
```

```bash
sed -n '1,260p' outputs/raw_query_answer_qa/20260517T033806Z/report.md
```

```bash
sed -n '1,260p' outputs/raw_query_answer_qa/20260517T033806Z/summary.json
```

```bash
sed -n '1,260p' outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.md
```

```bash
sed -n '1,620p' qa/frontend_copy_corpus.yaml
```

```bash
rg --files | rg 'frontend.*copy|copy.*qa|qa.*frontend|frontendCopyQaHarness|results'
```

```bash
rg -n "frontend-copy|Frontend Copy|frontendCopy|source_backend_run|soft check|expected_semantic" frontend tools qa frontend/package.json
```

```bash
find frontend/src/components -maxdepth 3 -type f | sort
```

```bash
find qa/harness_slices -maxdepth 1 -type f -print -exec sed -n '1,120p' {} \;
```

```bash
sed -n '1,980p' frontend/src/test/frontendCopyQaHarness.tsx
```

```bash
sed -n '1,260p' frontend/src/test/frontendCopyQaReport.test.tsx
```

```bash
sed -n '1,520p' frontend/src/components/results/resultShapes.ts
```

```bash
sed -n '1,520p' frontend/src/components/results/config/routeToPattern.ts
```

```bash
sed -n '1,560p' frontend/src/components/noResultDisplayUtils.ts
```

```bash
sed -n '1,900p' frontend/src/components/results/patterns/LeaderboardResult.tsx
```

```bash
sed -n '1,260p' docs/reference/result_contracts/core_result_table_contracts.md
```

```bash
rg -n "unsupported|personal|rookie|bench|conference|opponent|playoff|comparison|leaderboard|record when|since|date|three|threes|allowed|gave up|net rating" docs/reference/query_catalog.md
```

```bash
rg -n "unsupported|personal|rookie|bench|conference|opponent|playoff|comparison|leaderboard|record when|since|date|three|threes|allowed|gave up|net rating" docs/reference/query_guide.md
```

```bash
.venv/bin/python -c "import yaml; print('yaml-ok')"
```

```bash
wc -l qa/raw_query_answer_corpus.yaml qa/frontend_copy_corpus.yaml outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.md
```

```bash
.venv/bin/python -c "<structured coverage probe over raw corpus, frontend-copy corpus, latest raw JSONL, configured source JSONL, and frontend-copy report JSONL>"
```

Probe findings:

- Raw corpus cases: 243.
- Latest raw JSONL rows: 243.
- Configured frontend-copy source rows: 195.
- Frontend-copy selected cases: 59.
- Frontend-copy selected IDs missing from latest raw run: none.
- Frontend-copy selected IDs missing from configured source run: none.
- Current frontend-copy status coverage from latest raw rows: `ok: 52`,
  `no_result: 6`, `error: 1`.
- Current frontend-copy rendered shape counts: Comparison Panels 6, Entity
  Summary 2, Entity Summary + Recent Games 5, Guided No Result 2, Leaderboard
  Table 11, Matchup By Decade 2, Message No Result 5, Player Game Log 1,
  Playoff History 3, Playoff Matchup History 3, Playoff Round Records 1, Split
  Comparison 4, Team Record 9, Top Performances 5.

No production code, frontend rendering, backend query behavior, corpus
expectations, test files, or frontend-copy cases were changed in this preflight.
