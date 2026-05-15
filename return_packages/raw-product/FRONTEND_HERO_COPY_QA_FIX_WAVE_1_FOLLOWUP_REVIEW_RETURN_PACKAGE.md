# Frontend Hero / Copy QA Fix Wave 1 Follow-Up Review Return Package

## 1. Executive summary

- Cases reviewed: 15 requested cases total: 10 fixed-family cases and 5 nearby high-risk spot checks. The latest frontend-copy report directly rendered 13 of these; `bench_scoring_leaders_wave4` and `celtics_bench_scoring_boundary_wave4` were not selected in that frontend-copy run, so they were reviewed from raw QA plus the no-result message mapping.
- FCQ-001 status: resolved.
- FCQ-002 status: resolved.
- FCQ-003 status: resolved, with a report-coverage caveat for the two bench cases that were not rendered in the latest frontend-copy artifact.
- New defects found: none.
- Recommended next phase: screenshot/visual QA for the fixed families and spot-check set; no additional semantic-copy fix wave is recommended.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Fixed finding verification

| Finding | Cases reviewed | Status | Evidence | Notes |
|---|---|---|---|---|
| FCQ-001 | `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | resolved | Raw QA has `position_filter=guards`, applied `Position guards`, `stat=fg_pct`, and top row `Gary Payton II` for the guard FG% case. The frontend-copy report renders `Position guards`, context lines `Filter: Position: guards` and `Filter: Position group: guards`, table header `FG%`, and first row `Gary Payton II`. The center rebound guardrail still renders `Position centers`, `RPG`, and first row `Nikola Jokic`. | The guard hero still uses the generic phrase `led the NBA`; because the position chip/context and filtered table are present, this is no longer a semantic-copy defect. Visual QA should verify those chips are visually close enough to the hero/table. |
| FCQ-002 | `fewest_points_allowed_team_leader`, `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4` | resolved | Raw QA exposes `stat=opponent_pts_per_game` and executed direction: `ascending=true` for fewest and `ascending=false` for most/opponent PPG. Frontend-copy renders `allowed the fewest points per game` for Boston, `allowed the most points per game` for Utah, and table header `Opponent PTS Per Game` in all three cases. | No misleading `most` wording remains in the fewest case; the most/opponent-PPG cases are not framed as best defense. |
| FCQ-003 | `personal_foul_leaders_wave4`, `rookie_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `bench_scoring_leaders_wave4`, `celtics_bench_scoring_boundary_wave4` | resolved | Frontend-copy renders product-facing primary no-result messages for the three selected cases: `Personal-foul leaderboards are not supported yet.`, `Rookie leaderboards are not supported yet.`, and `League-wide starter/bench leaderboards are not supported yet.` Raw QA returns `unsupported_filters=["role_leaderboard"]` for bench league leaders and `unsupported_filters=["team_bench_scoring"]` for Celtics bench scoring. The no-result mapping returns `Team bench-scoring summaries are not supported yet.` for `team_bench_scoring`. | Details still include diagnostic `blocked:` IDs, which is acceptable under the requested criteria. The two bench cases should be included in the next visual pass because they were not in the latest frontend-copy report. |

## 3. Case review details

| Case ID | Category | Rendered behavior | Verdict | Notes |
|---|---|---|---|---|
| `guards_fg_percentage_leaders` | FCQ-001 | Frontend-copy rendered `Position guards`, `Filter: Position: guards`, `FG%`, and first row `Gary Payton II` at 58.3%. | resolved | Raw QA hard assertions pass for `position_filter=guards` and applied position filter. |
| `centers_rebound_leaders_wave4` | FCQ-001 guardrail | Frontend-copy rendered `Position centers`, `RPG`, and first row `Nikola Jokic` at 12.9 RPG. | resolved | No regression found in the position-filtered rebound leaderboard guardrail. |
| `fewest_points_allowed_team_leader` | FCQ-002 | Hero: `The Boston Celtics allowed the fewest points per game...`; table header: `Opponent PTS Per Game`; first row Boston at 107.2. | resolved | Raw QA has `ascending=true`; no `most` wording in the primary hero. |
| `most_points_allowed_team_leaders_wave4` | FCQ-002 | Hero: `The Utah Jazz allowed the most points per game...`; table header: `Opponent PTS Per Game`; first row Utah at 126.0. | resolved | Not framed as best defense. |
| `opponent_ppg_leaders_wave4` | FCQ-002 | Hero: `The Utah Jazz allowed the most points per game...`; table header: `Opponent PTS Per Game`; first row Utah at 126.0. | resolved | Clear enough for opponent PPG because both context and table say opponent points. |
| `personal_foul_leaders_wave4` | FCQ-003 | Primary no-result title/message: `Unsupported Leaderboard`; `Personal-foul leaderboards are not supported yet.` | resolved | Primary copy no longer exposes raw `pf`; details include acceptable diagnostics. |
| `rookie_scoring_leaders_wave4` | FCQ-003 | Primary no-result title/message: `Unsupported Leaderboard`; `Rookie leaderboards are not supported yet.` | resolved | Product boundary is explicit. |
| `starter_assist_leaders_wave4` | FCQ-003 | Primary no-result title/message: `Unsupported Leaderboard`; `League-wide starter/bench leaderboards are not supported yet.` | resolved | Product boundary is explicit. |
| `bench_scoring_leaders_wave4` | FCQ-003 | Not present in latest frontend-copy report. Raw QA returns `no_result`, `filter_not_supported`, and `unsupported_filters=["role_leaderboard"]`. | resolved by raw/code-path evidence | The shared frontend mapping for `role_leaderboard` returns the same league-wide starter/bench message rendered by `starter_assist_leaders_wave4`. Include this case in visual QA. |
| `celtics_bench_scoring_boundary_wave4` | FCQ-003 | Not present in latest frontend-copy report. Raw QA returns `no_result`, `filter_not_supported`, and `unsupported_filters=["team_bench_scoring"]`. | resolved by raw/code-path evidence | The frontend mapping returns `Team bench-scoring summaries are not supported yet.` Include this case in visual QA. |
| `record_when_jokic_triple_double` | spot check | Hero: `The Nuggets are 24-10 when Nikola Jokic records a triple-double this season.` Applied filter: `Special Event Triple Double`. | pass | No new semantic mismatch found. |
| `lakers_road_record_last_season` | spot check | Hero: Lakers `19-22` in `2024-25`; applied filters `Location Away` and `Season 2024-25`; table first row has 41 away games. | pass | No regression to relative-season or location copy. |
| `heat_knicks_playoff_series_record_wave4` | spot check | Hero: Heat lead Knicks `19-16` in playoff games; series record tied `3-3`; table is playoff series history. | pass | No new mismatch found. |
| `lebron_durant_comparison_wave4` | spot check | Hero compares Kevin Durant's 48 wins to LeBron James' 39; table columns include both player names and edge/difference. | pass | No player-comparison copy regression found. |
| `biggest_scoring_games` | spot check | Hero: Bam Adebayo top scoring game with 83 points; table header includes `PTS`; first row is Bam Adebayo vs Washington. | pass | This remains the previously verified high-point outlier, not a new frontend-copy defect. |

## 4. Remaining risks

- Visual/layout risks: no screenshot or Playwright visual QA has been run yet. The highest-value visual checks are chip proximity for position-filtered leaderboards, no-result primary message hierarchy, and table header visibility on desktop and mobile.
- Copy/polish risks: filtered leaderboard heroes still use generic `led the NBA` phrasing. This is acceptable with visible filter chips/context, but screenshot review should confirm the filtered context is hard to miss. Abbreviations such as `RPG` and `Opponent PTS Per Game` are acceptable for this pass.
- Backend/data risks: `bench_scoring_leaders_wave4` and `celtics_bench_scoring_boundary_wave4` were not in the latest frontend-copy selected set, so their rendered UI should be captured in the visual phase. Unsupported boundaries remain intentional product decisions, not execution-backed leaderboards.

## 5. Recommended next phase

- If screenshot/visual QA:
  - scope: the 15 requested follow-up cases, with emphasis on the three fixed finding families and including the two bench no-result cases absent from the frontend-copy report.
  - case count: 15 cases minimum; optionally add a small desktop/mobile pair for each no-result shape and each leaderboard shape.
  - artifacts: per-case screenshots, extracted visible text, viewport metadata, and a compact markdown/json summary under `outputs/`.
  - pass/fail style: block on misleading hero/table semantics, missing or visually disconnected filter chips, hidden primary no-result messages, unclear opponent-points table labeling, clipping/overlap, or mobile layout breakage. Treat minor wording polish as non-blocking unless it changes meaning.
- If follow-up semantic fix:
  - scope: not recommended based on this review.
  - files likely involved: none.

## 6. Validation performed

Files inspected:

- `return_packages/raw-product/FRONTEND_HERO_COPY_QA_FIX_WAVE_1_SEMANTIC_COPY_CLEANUP_RETURN_PACKAGE.md`
- `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl`
- `outputs/frontend_copy_qa/20260515T024718Z/summary.json`
- `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- `qa/frontend_copy_corpus.yaml`
- `qa/raw_query_answer_corpus.yaml`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
- `frontend/src/components/noResultDisplayUtils.ts`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/test/UIComponents.test.tsx` (read-only `rg` check only)

Commands/probes run:

- `sed -n '1,220p' return_packages/raw-product/FRONTEND_HERO_COPY_QA_FIX_WAVE_1_SEMANTIC_COPY_CLEANUP_RETURN_PACKAGE.md`
- `sed -n '1,260p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '1,220p' outputs/frontend_copy_qa/20260515T024718Z/summary.json`
- `sed -n '1,220p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `rg -n 'guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `rg -n 'guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl`
- `rg -n 'guards_fg_percentage_leaders|centers_rebound_leaders_wave4|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|record_when_jokic_triple_double|lakers_road_record_last_season|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games' outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- `sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
- `rg -n 'bench_scoring_leaders_wave4|celtics_bench_scoring_boundary_wave4|personal_foul_leaders_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|guards_fg_percentage_leaders|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4' qa/frontend_copy_corpus.yaml qa/raw_query_answer_corpus.yaml`
- `rg -n 'bench' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl outputs/frontend_copy_qa/20260515T024718Z/summary.json`
- `python3 -c ...` read-only JSONL probe extracting raw QA metadata, applied filters, top rows, unsupported filters, and expectation status for the requested cases.
- `python3 -c ...` read-only JSONL probe extracting frontend-copy hero text, chips, table headers, first rows, no-result copy, and soft-check summaries for the requested cases.
- `sed -n '520,690p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '1050,1145p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '280,382p' qa/frontend_copy_corpus.yaml`
- `sed -n '560,610p' qa/frontend_copy_corpus.yaml`
- `sed -n '1332,1368p' qa/raw_query_answer_corpus.yaml`
- `sed -n '2798,2865p' qa/raw_query_answer_corpus.yaml`
- `sed -n '2908,2935p' qa/raw_query_answer_corpus.yaml`
- `sed -n '3438,3565p' qa/raw_query_answer_corpus.yaml`
- `sed -n '3565,3595p' qa/raw_query_answer_corpus.yaml`
- `sed -n '20,55p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '180,205p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '415,445p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '835,855p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `sed -n '968,990p' outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- `rg -n 'team_bench_scoring|role_leaderboard|rookie_leaderboard|personal_foul_leaderboard|Personal-foul|Rookie leaderboards|starter/bench|bench-scoring' frontend/src/components frontend/src/test`
- `sed -n '1,240p' frontend/src/components/noResultDisplayUtils.ts`
- `sed -n '1,180p' frontend/src/components/NoResultDisplay.tsx`
- `git status --short`

No test command was run. No screenshot/Playwright visual QA was run.
