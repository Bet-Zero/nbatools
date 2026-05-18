# Raw Product Release Package

## 1. Release Status

- Recommended status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- Query feedback status: `FEEDBACK_READY_WITH_NOTES`.
- Release date: 2026-05-17.
- Latest feedback readiness refresh: 2026-05-18.
- Scope: current supported and explicitly unsupported Raw Product boundary.
- Production code changed for this package: no.
- Frontend rendering changed for this package: no.
- Backend query behavior changed for this package: no.
- QA corpus expectations changed for this package: no.
- Production-ready: yes after human acceptance of the release notes below.
- Preview-ready: yes, with notes.
- Release-candidate ready: yes, with notes.
- Query Feedback + Diagnostic Logging V1 included in release candidate: yes.
- Query feedback review/export workflow implemented: yes, with notes.
- Final handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`;
  handoff complete with notes.

This boundary is release-candidate ready for the current product surface. The
backend raw QA corpus is clean, selected frontend-copy QA is clean, the accepted
15-case visual baseline has a clean preview rerun, and the manual preview smoke
set passed with notes. The later opponent-conference preview blocker is now
resolved: R2 contains `raw/teams/team_conference_membership.csv`, the latest
opponent-conference preview smoke passed on
`https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app`, deployment
smoke includes the R2-sensitive membership-data check, and `/visual-qa` loaded
15/15 cases with request errors 0. Query Feedback + Diagnostic Logging V1 is
also no longer a release blocker: the latest R2 record inspection found
user-submitted records, automatic diagnostics, clean sanitizer/privacy output,
and `/review` plus `/visual-qa` suppression under the isolated
`query_feedback/preview` prefix.
Query Feedback Review Workflow V1 is now implemented as a read-only launch
review path: `make query-feedback-export` wraps
`tools/export_query_feedback.py` and writes `feedback_review.md`,
`feedback_records.csv`, `feedback_records.jsonl`, `summary.json`, and
`triage_decisions_template.csv`.

Human sign-off still needed:

- Product owner acceptance that selected frontend-copy coverage is sufficient
  for this release and does not need all 246 backend cases rendered.
- Product owner acceptance that visual QA remains manual, not screenshot-diff
  automation.
- Product owner acceptance that the explicitly guarded unsupported families
  remain unsupported for this release.
- Product owner acceptance that remaining feedback limitations are operational
  follow-ups: no admin dashboard, no mutable triage overlay, heuristic
  suggestions only, and manual corpus conversion.

## 2. Validation Summary

| Area | Status | Evidence |
|---|---|---|
| Backend Raw QA | `PASS` | `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases; expectation cases `pass: 246`; expectation checks `pass: 1421`; failed IDs none; suspicious flags 0. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125 selected cases; rendered 125; render failures 0; missing backend records 0; soft checks `480/0/0`. |
| Visual QA | `ACCEPTED_WITH_MANUAL_LIMITATION` | `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`; 15-case desktop/mobile manual baseline accepted; latest preview `/visual-qa` loaded 15/15 with request errors 0; no screenshot diff automation. |
| Preview manual QA | `PREVIEW_READY_WITH_NOTES` | `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`; `/`, `/review`, `/visual-qa`, six smoke queries, and five mobile blocker cases passed. |
| Opponent-conference preview smoke | `PASS` | `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`; four supported opponent-conference queries passed, geography/playoff-round guardrails passed, and `/visual-qa` request errors were 0. |
| R2 data availability | `PASS` | R2 dry-run included `raw/teams/team_conference_membership.csv`; sync uploaded it; `head_object` returned `ContentLength=4999`, `LastModified=2026-05-17T09:03:29+00:00`, and `nbatools-md5=f9cc9a60c8f659651723a55640966d73`. |
| Deployment smoke | `PASS` | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `case_count: 7`, `failure_count: 0`, and `query_celtics_record_against_east_current` returned `team_record` / `ok` with 15 East opponents. |
| Query Feedback + Diagnostic Logging V1 | `FEEDBACK_READY_WITH_NOTES` | `return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`; R2 list/get passed, user-submitted feedback writes were verified, automatic diagnostics were verified, sanitization/privacy checks passed, no raw result rows/tables were found, and `/review` plus `/visual-qa` suppression passed. |
| Query feedback review/export workflow | `IMPLEMENTED_WITH_NOTES` | `return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_V1_RETURN_PACKAGE.md`; launch review can use `make query-feedback-export`, backed by `tools/export_query_feedback.py`, to generate `feedback_review.md`, `feedback_records.csv`, `feedback_records.jsonl`, `summary.json`, and `triage_decisions_template.csv`. |
| Frontend build | `PASS_WITH_EXISTING_WARNING` | Latest readiness docs record `cd frontend && npm run build` passing with the existing Vite large-chunk warning. |
| Frontend lint | `PASS_WITH_EXISTING_WARNING` | Latest readiness docs record 0 errors and the existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning. |
| Team conference data | `PASS` | `.venv/bin/pytest tests/test_team_conference_membership_data.py -q` passed 15 tests. |
| Parser smoke | `PASS` | Latest readiness docs record `make PYTEST=.venv/bin/pytest test-parser` passing 751 tests. |
| Query smoke | `PASS` | Latest readiness docs record `make PYTEST=.venv/bin/pytest test-query` passing 752 tests. |
| Static diff check | `PASS` | This release-package pass ran `git diff --check` successfully. |

## 3. Supported Product Boundary

Supported areas for this release are the families covered by the current raw
QA corpus, selected frontend-copy corpus, visual baseline, query catalog, and
query guide.

### Player summaries

- Current-season, career, recent, last-N, opponent, opponent-quality,
  home/away, wins/losses, role-context, and selected stat-context player
  summaries.
- Player-vs-player opponent filters where the query asks for stats or averages
  against a named opposing player.

### Team records

- Overall, home/away, road, explicit-season, last-season, month-window,
  since-date, since All-Star, opponent-quality, scoring-threshold, and
  opponent-points-threshold team records.
- Opponent-conference team-record filters for trusted current-era seasons
  `2024-25` and `2025-26`, resolved from
  `data/raw/teams/team_conference_membership.csv`.
- `how did TEAM do` phrasing routes to record-style W/L summaries where the
  slots are supported.

### Record-when conditions

- Player stat thresholds, player special events such as triple-doubles, player
  shooting thresholds, team scoring thresholds, and team opponent-points
  thresholds.

### No-player / without-player conditions

- Single-player whole-game absence records and summaries where trusted source
  coverage exists.
- Supported phrasing includes `without`, `w/o`, `when PLAYER out`, `when PLAYER
  was out`, `didn't play`, `no PLAYER`, `sans`, and `minus`.

### Player leaderboards

- Standard counting stats, per-game leaderboards, percentage and supported
  advanced-stat aliases, position-filtered leaderboards, occurrence
  leaderboards, last-N/recent forms, home/away filters, and date/window filters.

### Team leaderboards

- Team stat leaderboards, record leaderboards, scoring/team-threes leaderboards,
  opponent-points/points-allowed leaderboards, and filtered team leaderboard
  forms where the route contract exists.

### Team advanced leaderboards

- League-wide net rating, offensive rating, defensive rating, and pace
  leaderboards.

### Top performances

- Player single-game points, assists, rebounds, threes, blocks, steals,
  plus-minus, named-player best-game/season-high phrasing, and selected
  date-filtered top-player performance queries.
- Team top scoring games are supported where the top-team route is covered.

### Finder / count outputs

- Player and team finder rows, count-with-finder outputs, distinct player/team
  threshold counts, compound supported thresholds, defensive threshold finders,
  and game-log detail shapes included in the selected frontend-copy set.

### Streaks

- Player stat-threshold streaks, player special-event streaks, current/completed
  phrasing, team win streaks, and team scoring/three-point threshold streaks.

### Rolling stretches

- Player rolling-stretch leaderboards for supported counting stats, shooting
  percentages, Game Score, named-player variants, and league-wide player
  stretch phrasing.

### Splits

- Player and team home-away splits, wins-losses splits, recent/last-N split
  contexts, and supported stat-context split phrasing.

### Playoff history

- Single-team playoff history, playoff appearances, Finals/conference-finals
  appearance summaries, era/decade records, and supported playoff-history
  phrasing.

### Playoff matchup history

- Explicit team-pair playoff history, series record/history, matchup history,
  Finals matchup history, and adjacent-team playoff series phrasing.

### Playoff round / appearance leaderboards

- Round-record leaderboards and most round or Finals appearance leaderboards,
  including since-year filters where covered.

### Comparisons

- Full-name player comparisons, recent player comparisons, team comparisons,
  matchup records, head-to-head summaries, and guarded stat-vs-player
  interpretations.

### Date / window filters

- Explicit seasons, latest-season defaults, last season, season ranges,
  explicit dates, month windows, since-date windows, last-N games, recent/lately
  defaults, since All-Star, and selected rolling-day phrasing.

### Defensive / opponent-points aliases

- Points allowed, opponent PPG, `gave up`, `allowing`, `held teams under`,
  `held opponents under`, `limited opponents to`, and related defensive
  threshold variants that bind to opponent scoring rather than team scoring.

## 4. Explicit Unsupported Boundaries

These surfaces are current product boundaries, not release blockers. They must
return explicit no-result, unsupported, unsupported-data, or
`filter_not_supported` behavior rather than broad plausible answers.

| Unsupported family | Current expected behavior | Why unsupported | Future support path |
|---|---|---|---|
| Personal-foul leaderboards | Returns `no_result` / `filter_not_supported`, with `personal_foul_leaderboard` metadata where parsed. | Personal fouls committed need an approved leaderboard stat contract and display semantics before ranking users by PF. | Approve the PF stat contract, add execution-backed leaderboard behavior, promote boundary cases into supported expectations, and add frontend-copy coverage. |
| Single-team advanced-stat scalar summaries | Single-team net/offensive/defensive rating or pace summary phrasing returns unsupported metadata; league-wide advanced team leaderboards remain supported. | There is no stable route/result contract for single-team advanced scalar answers or rank-preserving lookups. | Add a dedicated team advanced summary/lookup contract, result sections, metadata, frontend rendering, and no-match semantics. |
| Rookie leaderboards | Returns explicit unsupported-filter no-result. | Rookie status is not part of the trusted current leaderboard filter contract. | Add trusted rookie metadata, parser slots, execution filtering, docs, and tests. |
| League-wide starter/bench leaderboards | Returns explicit unsupported-filter no-result for starter/bench leaderboard phrasing. | League-wide role filters need trusted role classification, minimums, and route contracts. | Define role coverage and minimums, then add execution-backed filters and rendered-copy coverage. |
| Team bench scoring | Returns explicit unsupported-filter no-result for team bench scoring/points. | Team bench scoring needs role-scoped team aggregation outside the current team summary contract. | Define a team bench/unit scoring dataset or derived aggregation with stable summary sections. |
| Opponent-conference coverage gaps / geography / divisions | Current-era `team_record` opponent-conference filters are supported for trusted seasons `2024-25` and `2025-26`; seasons outside trusted coverage, geography phrases such as `east coast teams`, and division requests return explicit no-result instead of broad full-season records. | Historical conference coverage, divisions, and geography semantics are not part of the approved data contract. | Add trusted historical conference membership or division/geography contracts before expanding beyond the current-era East/West team-record filter. |
| Single-team playoff round records | Single-team Finals/conference-finals record phrasing returns unsupported-filter no-result; `conference finals` is playoff-round phrasing, not opponent-conference filtering. | Current contracts support round leaderboards and matchup history, not single-team round records; some historical round labels are unreliable. | Approve single-team playoff round semantics and fallback behavior for unreliable labels, then add route/output coverage. |
| Subjective/trend queries | Clutch, cooled off, best defender, MVP candidate, best player lately, and similar opinion/trend requests return unsupported/no-result instead of invented definitions. | Product-approved metric definitions and source coverage are required. | Define metric-backed semantics one family at a time, then add parser, execution, copy, and QA coverage. |
| Multi-player availability | Multi-player availability record phrasing returns explicit unsupported/no-result instead of an unfiltered team record. | Multi-player availability semantics are outside the current whole-game single-player absence contract. | Add a dedicated availability model, trusted coverage fields, filter semantics, and result contract. |
| Lineup summaries / leaderboards where trusted coverage is unavailable | Current guarded cases such as `best 5-man lineups` and lineup membership summaries return explicit unsupported/no-result responses. | Trusted lineup/stint coverage is unavailable for those release cases, and generic display contracts remain risky for real lineup identity fields. | Add or verify a dedicated lineup dataset with grain, join keys, trust fields, identity columns, frontend rendering, and fallback behavior. |
| On/off surfaces where trusted data is unavailable | Current guarded on/off cases return explicit unsupported/no-result responses. Whole-game `without_player` remains separate. | Trusted stint/on-off coverage is unavailable for those release cases and cannot be substituted with absence records. | Add trusted on/off coverage with `on` and `off` buckets, source trust semantics, and clear fallback behavior. |
| Team rolling-stretch leaderboards | Team-scoped rolling-stretch wording returns unsupported-filter no-result. | Current rolling-stretch support is player-oriented and no team route/result contract is approved. | Define team rolling-window metrics, result sections, route behavior, and frontend display. |
| Minutes leaderboards | Guarded as unsupported/product-boundary behavior. | Minutes need an explicit stat/leaderboard support decision and display/minimum contract. | Approve the stat contract and add route/output/frontend/corpus coverage. |
| Team single-game threes | Guarded as unsupported/product-boundary behavior where currently unrouted or unsupported. | Team `fg3m` top-game support needs an explicit route and product decision. | Add top-team-game stat support and selected frontend-copy cases if promoted. |

## 5. QA Artifacts

Latest release artifacts:

- Backend raw QA Markdown report:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.md`
- Backend raw QA JSONL report:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl`
- Frontend-copy report:
  `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`
- Visual QA checklist:
  `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- Preview manual QA rerun:
  `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`
- Release-readiness checklist:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- Release-candidate handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- Release-readiness checkpoint:
  `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- Query feedback R2 inspection:
  `return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`
- Query feedback review workflow V1:
  `return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_V1_RETURN_PACKAGE.md`
- Query feedback implementation package:
  `return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_V1_RETURN_PACKAGE.md`
- Backend harness plan:
  `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- Latest deployment smoke:
  `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`
- Harness slices:
  - `qa/harness_slices/defensive_aliases.yaml`
  - `qa/harness_slices/playoff_phrasing.yaml`
  - `qa/harness_slices/team_date_context.yaml`
  - `qa/harness_slices/player_entity_stat_context.yaml`
  - `qa/harness_slices/product_boundaries.yaml`

Supporting return packages:

- `return_packages/raw-product/RAW_QA_HARNESS_EFFICIENCY_WAVE_1_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_1_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md`
- `return_packages/raw-product/OPPONENT_CONFERENCE_PROMOTION_RETURN_PACKAGE.md`
- `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_SMOKE_RERUN_RETURN_PACKAGE.md`
- `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_RELEASE_PACKAGE_REFRESH_AFTER_R2_SYNC_FIX_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_V1_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_PREVIEW_R2_ENABLE_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_V1_RETURN_PACKAGE.md`

## 6. Known Limitations

- Frontend-copy QA is selected coverage: 125 rendered cases from the latest
  clean 246-case backend run, not all 246 backend cases.
- Frontend-copy QA checks DOM text and rendered component output; it is not
  visual layout or screenshot diff automation.
- Visual QA remains a manual 15-case baseline with accepted desktop/mobile
  checks, not automated Playwright screenshot diffing.
- Preview manual QA is `PREVIEW_READY_WITH_NOTES`; notes include the manual
  nature of visual QA and selected frontend-copy coverage.
- The previous opponent-conference preview `BLOCKED` status is resolved by the
  R2 sync fix; missing R2 data for required release files remains a deploy
  blocker for future previews.
- Unsupported features are guarded and documented; opponent-conference
  `team_record` filters are execution-backed only for trusted seasons
  `2024-25` and `2025-26`.
- Opponent-conference expansion outside trusted current-era coverage, divisions,
  and geography phrases remains unsupported/no-result.
- Conference Finals phrasing remains a playoff-round surface, not an
  opponent-conference filter.
- Frontend lint remains clean with 0 errors and the existing
  `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- Frontend build remains clean with the existing Vite large-chunk warning.
- Query feedback is `FEEDBACK_READY_WITH_NOTES`, not blocked: preview records
  are verified under `nbatools-data` prefix `query_feedback/preview`, and the
  read-only review/export workflow is implemented. Remaining feedback notes are
  no admin dashboard, no mutable triage overlay, heuristic suggestions only,
  and manual corpus conversion.

## 7. Future Deployment Checklist

Before deploying this boundary again:

- Run the full backend raw QA corpus:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Run frontend-copy QA:
  `cd frontend && npm run qa:frontend-copy`
- Run frontend build and lint:
  `cd frontend && npm run build`
  `cd frontend && npm run lint`
- If any new or changed data file is required at runtime, run the R2 dry-run and
  sync before preview smoke:
  `.venv/bin/nbatools-cli pipeline sync-r2 --dry-run`
  `.venv/bin/nbatools-cli pipeline sync-r2`
- Verify `raw/teams/team_conference_membership.csv` exists in R2 before any
  opponent-conference preview smoke or release handoff.
- If query feedback env changes, confirm storage still writes compact sanitized
  records and verify the active bucket/prefix. Latest accepted preview evidence
  is `FEEDBACK_READY_WITH_NOTES` under `query_feedback/preview`.
- Run `make query-feedback-export` for launch feedback review and inspect the
  generated Markdown, CSV, JSONL, summary, and triage-template artifacts.
- Run deployment smoke against the target URL and confirm the
  opponent-conference membership-data case passes.
- Open `/`, `/review`, and `/visual-qa` on the target preview or production URL.
- Run the six smoke queries:
  - `Who leads the NBA in points per game this season?`
  - `What is Denver's record when Nikola Jokic has a triple-double?`
  - `Which team gave up the fewest points per game?`
  - `Lakers Celtics playoff matchup history`
  - `Warriors net rating this season`
  - `players with most personal fouls this season`
- Run the opponent-conference preview smoke set:
  - `Celtics record against the East this season`
  - `Lakers record against the West`
  - `Lakers road record against West last season`
  - `Knicks record against Eastern Conference teams since January 1`
  - `Celtics record against east coast teams`
  - `Celtics conference finals record`
- Run a mobile visual QA five-case spot check:
  - `biggest_scoring_games`
  - `lebron_durant_comparison_wave4`
  - `heat_knicks_playoff_series_record_wave4`
  - `guards_fg_percentage_leaders`
  - `centers_rebound_leaders_wave4`
- Confirm unsupported boundaries still return explicit unsupported/no-result
  behavior and have not broadened into plausible but unsupported answers.

## 8. Next Roadmap Options

Current handoff status: release-candidate handoff is complete; see
`docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`.

Recommended order after this handoff:

1. Visual QA automation.
   - Add Playwright/screenshot baselines or pixel/layout assertions for the
     accepted 15-case visual corpus before expanding visual scope.
2. First launch feedback review.
   - Run `make query-feedback-export`, inspect the generated artifacts, and
     manually fill the triage decisions template before converting verified
     issues into corpus or planning updates.
3. Promote another unsupported family into real support.
   - Candidates include historical opponent-conference expansion beyond trusted
     current-era seasons, single-team advanced scalar summaries, or rookie/role
     leaderboards, depending on product need and available source contracts.
4. Broader release/CI artifact packaging.
   - Package raw QA, frontend-copy, preview manual QA, and visual QA outputs
     into a repeatable CI/release artifact bundle.
5. Frontend-copy Wave 3 only after fresh gap analysis.
   - Expand only if a route/shape risk is still meaningfully undercovered after
     the 125-case set.
6. Harness tag/category filters.
   - Add focused selection by corpus tags/categories if future fix waves need
     faster iteration than saved slices provide.
