# Frontend Hero / Copy QA Wave 1 Report Review Return Package

## 1. Executive summary

- Cases reviewed: 5 soft-check misses plus 11 high-risk successful cases.
- Confirmed defects: 3 finding families.
- Harmless soft-check mismatches: 2.
- Product decisions: no new product decisions required; unsupported leaderboard boundaries already exist, but no-result summary wording needs refinement.
- Recommended next execution: run one grouped semantic-copy fix wave covering position-filter source/visibility, opponent-points leaderboard hero wording, and unsupported no-result specificity.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Soft-check miss review

| Case ID | Soft miss | Classification | Frontend rendered behavior | Verdict | Recommended action |
|---|---|---|---|---|---|
| `guards_fg_percentage_leaders` | `filter_chip_fragment "guards"` | `real_semantic_defect` | Query asks for the best field-goal percentage among guards. Backend facts show `season_leaders / ok`, `stat=fg_pct`, `position_filter=null`, no applied filters, and top row `Jaxson Hayes`. The UI renders no applied filter chip or context item for guards, and the hero says `Jaxson Hayes led the NBA with 75.6% field-goal percentage...`. | Misleading. This is not just a missing frontend chip: the backend source row is unfiltered, so the rendered answer is a broad FG% leaderboard for a guard-filtered query. | Fix or replace the source/backend case so this phrasing emits `position_filter=guards` plus an applied position filter, then verify the frontend chip. Do not treat this as a frontend-only display fix. |
| `fewest_points_allowed_team_leader` | `semantic_fact "points allowed"` | `real_semantic_defect` | Query asks which team allowed the fewest points per game. Backend facts rank `opponent_pts_per_game` with Boston first at `107.1585`. The table header is clear: `Opponent PTS Per Game`. The hero says `The Boston Celtics had the most opponent pts per game...`. | Misleading. The hero direction contradicts the query and backend ranking: it says `most` for a `fewest` result. | Add structured/display support for opponent-points leaderboard direction and copy. This case should render as fewest/lowest opponent points per game or points allowed per game. |
| `most_points_allowed_team_leaders_wave4` | `semantic_fact "points allowed"` | `harmless_check_fragment_mismatch` | Query asks which teams allow the most points per game. Backend facts rank `opponent_pts_per_game` with Utah first at `126.0122`. UI hero says `most opponent pts per game`; table header says `Opponent PTS Per Game`. | Not misleading. `Opponent pts per game` is equivalent enough to points allowed, and `most` is not framed as best defense. | Update the soft-check corpus to accept `opponent pts per game` or `Opponent PTS Per Game`. Optional copy polish can happen with FCQ-002. |
| `opponent_ppg_leaders_wave4` | `semantic_fact "points per game"` | `harmless_check_fragment_mismatch` | Query asks for opponent PPG leaders. Backend facts rank `opponent_pts_per_game` with Utah first at `126.0122`. UI hero says `most opponent pts per game`; table header says `Opponent PTS Per Game`. | Not misleading. The soft check expected expanded wording, but the rendered wording conveys opponent PPG. | Update the soft-check corpus to accept `opponent pts per game` / `Opponent PTS Per Game`. Optional copy polish can happen with FCQ-002. |
| `personal_foul_leaders_wave4` | `semantic_fact "Unavailable Metric"` | `no_result_guidance_issue` | Query asks for personal-foul leaders. Backend facts return `season_leaders / no_result / filter_not_supported`, `stat=pf`, unsupported filter `personal_foul_leaderboard`, with a note that personal-foul leaderboards are unsupported. UI title is `Unavailable Filter`; message is `Pf is not available for this query.` Details do mention personal-foul leaderboards. | Partly misleading at the primary-message level. The details explain the boundary, but the title/message are generic and expose `Pf` instead of product copy. | Make no-result guidance boundary-specific: `Personal-foul leaderboards are not supported...`, and humanize `pf` as `personal fouls`. Consider `Unavailable Metric` for this specific boundary. |

## 3. High-risk pass spot-checks

| Case ID | Category | Rendered behavior | Verdict | Notes |
|---|---|---|---|---|
| `record_when_jokic_triple_double` | Record-when | Backend says Denver/Nikola Jokic are `24-10` across 34 triple-double games. UI hero says `The Nuggets are 24-10 when Nikola Jokic records a triple-double this season`; chip shows `Special Event Triple Double`. | Pass | No obvious mismatch. |
| `knicks_allowed_under_110_record` | Record-when | Backend says Knicks are `32-3` when `opponent_pts <= 109.9999`. UI hero is generic record copy; chip/context show `Opp PTS <= 110` and `opponent_pts <= 109.9999`. | Pass | Hero omits the condition, but visible filter context carries it. No confirmed defect in this wave. |
| `boston_tatum_under_40_fg_record_missing_filter` | Record-when | Backend says Celtics are `4-2` when Tatum has `fg_pct <= 0.3999`. UI hero says `records 40% or fewer fg pct`; chip shows `<= 0.4 FG PCT`. | Pass | Copy is awkward, but the condition is visible and semantically aligned. |
| `lakers_road_record_last_season` | Last-season/context | Backend says Lakers road record was `19-22` in `2024-25`. UI hero gives `19-22` and `2024-25`; chips show `Location Away` and `Season 2024-25`. | Pass | No mismatch. |
| `sga_playoff_teams_last_season_wave4` | Last-season/context | Backend says SGA averaged `33.566 PPG` in 53 games against playoff teams in `2024-25`. UI hero says `33.6 points... against playoff teams in the 2024-25 regular season`; chips show opponent group and season. | Pass | No mismatch. |
| `rookie_scoring_leaders_wave4` | Unsupported/no-result | Backend says rookie leaderboards are unsupported. UI title says `Unavailable Filter`; details name the rookie leaderboard boundary. Primary message says `Points is not available for this query.` | Guidance issue, low severity | Same FCQ-003 family: details are correct, but primary message should name the unsupported rookie leaderboard boundary rather than the stat. |
| `starter_assist_leaders_wave4` | Unsupported/no-result | Backend says league-wide starter/bench leaderboards are unsupported. UI title says `Unavailable Filter`; details name the starter/bench boundary. Primary message says `Assists is not available for this query.` | Guidance issue, low severity | Same FCQ-003 family: details are correct, but primary message should name the unsupported role leaderboard boundary. |
| `celtics_against_east_record_wave4` | Unsupported/no-result | Backend says opponent-conference record filters are unsupported. UI title says `Unavailable Filter`; details name the conference metadata boundary and suggest supported alternatives. | Pass | Primary message is generic, but the detail copy exposes the actual boundary clearly enough. |
| `heat_knicks_playoff_series_record_wave4` | Playoff matchup | Backend says Heat lead Knicks `19-16` in playoff games and the series record is tied `3-3`. UI hero says both facts; table shows playoff series rows with round-unavailable caveat. | Pass | No obvious mismatch. |
| `lebron_durant_comparison_wave4` | Comparison | Backend comparison includes LeBron and Durant 2025-26 regular-season rows. UI hero chooses the wins edge: Durant `48` wins to LeBron `39`; table shows comparison metrics. | Pass | Edge choice is acceptable. No obvious mismatch between structured facts and copy. |
| `biggest_scoring_games` | Verified outlier/top performance | Backend top row is Bam Adebayo with `83 PTS` on Mar 10, 2026 vs WAS. UI hero says he had the top scoring game with `83 points`; table shows `PTS`. | Pass | Verified-outlier display is semantically aligned. |

## 4. Confirmed finding families

| Finding ID | Priority | Family | Cases | Issue | Recommended fix |
|---|---|---|---|---|---|
| FCQ-001 | P1 | Position filter source/visibility | `guards_fg_percentage_leaders` | Guard-filtered query renders as an unfiltered broad FG% leaderboard. Backend facts have no `position_filter` or applied position filter, so no frontend chip can appear. | Fix the backend/parser/source case for `among guards` FG% phrasing, or replace this frontend-copy case with a hard-asserted guard-position case after backend support is verified. Then verify the UI shows a position filter chip. |
| FCQ-002 | P1 | Defensive/opponent metric labeling and direction | `fewest_points_allowed_team_leader`; related soft-check-only wording in `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4` | `opponent_pts_per_game` table labels are clear, but the fewest query hero says `most opponent pts per game`. The generic hero cannot distinguish lowest/fewest from highest/most. | Expose/consume structured leaderboard direction or rank label for `opponent_pts_per_game`, then render `fewest/lowest points allowed per game` for ascending results and clear `most opponent points allowed per game` for descending results. |
| FCQ-003 | P2 | Unsupported/no-result guidance specificity | `personal_foul_leaders_wave4`; lower-severity related spot-checks: `rookie_scoring_leaders_wave4`, `starter_assist_leaders_wave4` | No-result details explain unsupported boundaries, but primary title/message can be generic or metric-centric (`Pf`, `Points`, `Assists`) instead of naming the unsupported leaderboard/filter boundary. | Use `metadata.unsupported_filters` and/or backend notes to produce boundary-specific primary messages. Humanize `pf` as `personal fouls`; consider `Unavailable Metric` for personal-foul leaderboards and boundary-specific `Unavailable Filter` copy for rookie/starter leaderboards. |

No confirmed FCQ-004, FCQ-005, or FCQ-006 findings were found in this review pass.

## 5. Recommended execution scope

- Exact goal: one grouped semantic-copy fix wave for the confirmed Wave 1 findings: restore/verify guard position filtering for the selected source case, fix opponent-points leaderboard hero direction/wording, and make unsupported no-result summary copy boundary-specific.
- Files likely to change: `src/nbatools/commands/natural_query.py` or nearby parser/leaderboard helpers if the guard filter source issue is fixed in the engine; `src/nbatools/commands/season_team_leaders.py` or structured-result metadata if leaderboard direction needs to be emitted; `frontend/src/components/results/patterns/LeaderboardResult.tsx`; `frontend/src/components/noResultDisplayUtils.ts`; possibly `frontend/src/components/ResultEnvelope.tsx` only if filter-chip rendering lacks a valid backend filter after the engine fix.
- Tests/report checks to update: targeted parser/query tests for the guard FG% phrasing if backend behavior changes; `frontend/src/test/ResultRenderer.test.tsx` for opponent-points hero wording; `frontend/src/test/UIComponents.test.tsx` or no-result utility coverage for unsupported boundary messages; then `cd frontend && npm run qa:frontend-copy`.
- Corpus/report updates: after behavior is verified, update `qa/frontend_copy_corpus.yaml` soft-check fragments for harmless wording mismatches, and mark reviewed cases in a follow-up corpus/report wave. Do not update corpus before behavior is fixed or explicitly accepted.
- Harness validation: rerun the frontend-copy harness against a fresh raw QA source run; confirm zero render failures and re-review the five original misses plus the unsupported spot-checks.
- Stop conditions: stop if the guard case still has no backend `position_filter=guards`; stop if the fewest-points-allowed hero still says `most`; stop if personal-foul no-result copy still exposes `Pf` or hides the personal-foul leaderboard boundary in the primary message.

## 6. Risks / open decisions

- Copy exactness risks: `opponent_pts_per_game` can be shown as `opponent PPG`, `opponent points per game`, or `points allowed per game`. The fix should choose one product phrase and align soft checks to it.
- Visual review needs: this jsdom harness verifies rendered DOM copy, not visual hierarchy, wrapping, or chip prominence. Position-filter chip visibility and no-result detail prominence should get screenshot QA after the semantic fixes.
- Product decisions: no new boundary decision is needed for rookie, starter/bench league-wide, personal-foul, or opponent-conference leaderboards. Current docs already describe these as unsupported boundaries; the issue is guidance specificity.

## 7. Validation performed

Exact files inspected:

- `return_packages/raw-product/FRONTEND_HERO_COPY_QA_HARNESS_WAVE_1_RETURN_PACKAGE.md`
- `qa/frontend_copy_corpus.yaml`
- `qa/raw_query_answer_corpus.yaml`
- `outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md`
- `outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.jsonl`
- `outputs/frontend_copy_qa/20260514T153729Z/summary.json`
- `outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl`
- `docs/reference/result_contracts/core_result_table_contracts.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/noResultDisplayUtils.ts`
- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- `frontend/src/components/results/`

Commands/probes run:

```bash
sed -n '1,220p' return_packages/raw-product/FRONTEND_HERO_COPY_QA_HARNESS_WAVE_1_RETURN_PACKAGE.md
sed -n '1,260p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
cat outputs/frontend_copy_qa/20260514T153729Z/summary.json
rg -n "guards_fg_percentage_leaders|fewest_points_allowed_team_leader|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4|personal_foul_leaders_wave4|record_when_jokic_triple_double|knicks_allowed_under_110_record|boston_tatum_under_40_fg_record_missing_filter|lakers_road_record_last_season|sga_playoff_teams_last_season_wave4|rookie_scoring_leaders_wave4|starter_assist_leaders_wave4|celtics_against_east_record_wave4|heat_knicks_playoff_series_record_wave4|lebron_durant_comparison_wave4|biggest_scoring_games" outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md qa/frontend_copy_corpus.yaml
sed -n '520,690p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
sed -n '180,270p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
sed -n '1060,1145p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
node -e 'const fs=require("fs"); const line=fs.readFileSync("outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.jsonl","utf8").trim().split(/\n/)[0]; const o=JSON.parse(line); console.log(Object.keys(o).join("\n")); console.log(JSON.stringify(o,null,2).slice(0,3000));'
node -e 'const fs=require("fs"); const line=fs.readFileSync("outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl","utf8").trim().split(/\n/)[0]; const o=JSON.parse(line); console.log(Object.keys(o).join("\n")); console.log(JSON.stringify(o,null,2).slice(0,3000));'
sed -n '1,220p' docs/reference/result_contracts/core_result_table_contracts.md
sed -n '1,240p' frontend/src/components/ResultEnvelope.tsx
sed -n '240,520p' frontend/src/components/ResultEnvelope.tsx
sed -n '520,900p' frontend/src/components/ResultEnvelope.tsx
sed -n '1,260p' frontend/src/components/NoResultDisplay.tsx
find frontend/src/components/results -maxdepth 3 -type f | sort
sed -n '1,240p' docs/reference/query_catalog.md
sed -n '1,260p' docs/reference/query_guide.md
sed -n '1,260p' frontend/src/components/results/patterns/LeaderboardResult.tsx
sed -n '1,260p' frontend/src/components/noResultDisplayUtils.ts
sed -n '1,260p' frontend/src/components/results/patterns/EntitySummaryResult.tsx
sed -n '1,260p' frontend/src/components/results/patterns/PlayoffHistoryResult.tsx
sed -n '260,620p' frontend/src/components/results/patterns/LeaderboardResult.tsx
sed -n '260,620p' frontend/src/components/noResultDisplayUtils.ts
sed -n '260,620p' frontend/src/components/results/patterns/EntitySummaryResult.tsx
sed -n '260,620p' frontend/src/components/results/patterns/PlayoffHistoryResult.tsx
sed -n '620,980p' frontend/src/components/results/patterns/LeaderboardResult.tsx
sed -n '980,1220p' frontend/src/components/results/patterns/LeaderboardResult.tsx
sed -n '420,470p' docs/reference/query_catalog.md
sed -n '760,805p' docs/reference/query_catalog.md
sed -n '190,210p' docs/reference/query_guide.md
sed -n '315,325p' docs/reference/query_guide.md
node -e 'const fs=require("fs"); const ids = new Set(["guards_fg_percentage_leaders","fewest_points_allowed_team_leader","most_points_allowed_team_leaders_wave4","opponent_ppg_leaders_wave4","personal_foul_leaders_wave4","record_when_jokic_triple_double","knicks_allowed_under_110_record","boston_tatum_under_40_fg_record_missing_filter","lakers_road_record_last_season","sga_playoff_teams_last_season_wave4","rookie_scoring_leaders_wave4","starter_assist_leaders_wave4","celtics_against_east_record_wave4","heat_knicks_playoff_series_record_wave4","lebron_durant_comparison_wave4","biggest_scoring_games"]); const lines=fs.readFileSync("outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.jsonl","utf8").trim().split(/\n/); for (const line of lines) { const o=JSON.parse(line); if (!ids.has(o.case_id)) continue; console.log(o.case_id, o.backend.query, o.frontend.hero_text); }'
node -e 'const fs=require("fs"); const ids = new Set(["guards_fg_percentage_leaders","centers_rebound_leaders_wave4","fewest_points_allowed_team_leader","most_points_allowed_team_leaders_wave4","opponent_ppg_leaders_wave4","personal_foul_leaders_wave4","record_when_jokic_triple_double","knicks_allowed_under_110_record","boston_tatum_under_40_fg_record_missing_filter","lakers_road_record_last_season","sga_playoff_teams_last_season_wave4","rookie_scoring_leaders_wave4","starter_assist_leaders_wave4","celtics_against_east_record_wave4","heat_knicks_playoff_series_record_wave4","lebron_durant_comparison_wave4","biggest_scoring_games"]); const lines=fs.readFileSync("outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl","utf8").trim().split(/\n/); for (const line of lines) { const o=JSON.parse(line); if (!ids.has(o.id)) continue; console.log(o.id, o.route, o.result_status, o.result_reason, JSON.stringify(o.applied_filters), JSON.stringify({stat:o.metadata?.stat, position_filter:o.metadata?.position_filter, unsupported_filters:o.metadata?.unsupported_filters})); }'
sed -n '1338,1375p' qa/raw_query_answer_corpus.yaml
sed -n '2668,2725p' qa/raw_query_answer_corpus.yaml
sed -n '280,382p' qa/frontend_copy_corpus.yaml
sed -n '560,610p' qa/frontend_copy_corpus.yaml
sed -n '960,1005p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
sed -n '830,860p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
sed -n '415,445p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
sed -n '35,55p' outputs/frontend_copy_qa/20260514T153729Z/frontend_copy_report.md
sed -n '1,320p' frontend/src/components/results/patterns/ComparisonResult.tsx
sed -n '320,660p' frontend/src/components/results/patterns/ComparisonResult.tsx
git status --short
git diff --check
```

No production code, tests, backend behavior, or corpus expectations were changed.
