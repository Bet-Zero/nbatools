# Raw Product Release Package

## 1. Release Status

- Recommended status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- Release date: 2026-05-17.
- Scope: current supported and explicitly unsupported Raw Product boundary.
- Production code changed for this package: no.
- Frontend rendering changed for this package: no.
- Backend query behavior changed for this package: no.
- QA corpus expectations changed for this package: no.
- Production-ready: yes after human acceptance of the release notes below.
- Preview-ready: yes, with notes.
- Release-candidate ready: yes, with notes.

This boundary is release-candidate ready for the current product surface. The
backend raw QA corpus is clean, selected frontend-copy QA is clean, the accepted
15-case visual baseline has a clean preview rerun, and the manual preview smoke
set passed with notes.

Human sign-off still needed:

- Product owner acceptance that selected frontend-copy coverage is sufficient
  for this release and does not need all 246 backend cases rendered.
- Product owner acceptance that visual QA remains manual, not screenshot-diff
  automation.
- Product owner acceptance that the explicitly guarded unsupported families
  remain unsupported for this release.

## 2. Validation Summary

| Area | Status | Evidence |
|---|---|---|
| Backend Raw QA | `PASS` | `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases; expectation cases `pass: 246`; expectation checks `pass: 1421`; failed IDs none; suspicious flags 0. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125 selected cases; rendered 125; render failures 0; missing backend records 0; soft checks `480/0/0`. |
| Visual QA | `ACCEPTED_WITH_MANUAL_LIMITATION` | `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`; 15-case desktop/mobile manual baseline accepted; no screenshot diff automation. |
| Preview manual QA | `PREVIEW_READY_WITH_NOTES` | `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`; `/`, `/review`, `/visual-qa`, six smoke queries, and five mobile blocker cases passed. |
| Frontend build | `PASS_WITH_EXISTING_WARNING` | Latest readiness docs record `cd frontend && npm run build` passing with the existing Vite large-chunk warning. |
| Frontend lint | `PASS_WITH_EXISTING_WARNING` | Latest readiness docs record 0 errors and the existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning. |
| Parser smoke | `PASS` | Latest readiness docs record `make PYTEST=.venv/bin/pytest test-parser` passing 751 tests. |
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
| Opponent-conference missing coverage / geography | Current-era `team_record` opponent-conference filters are supported for trusted seasons `2024-25` and `2025-26`; seasons outside trusted coverage and geography phrases such as `east coast teams` return explicit no-result instead of broad full-season records. | Historical conference coverage, divisions, and geography semantics are not part of the approved data contract. | Add trusted historical conference membership or division/geography contracts before expanding beyond the current-era East/West team-record filter. |
| Single-team playoff round records | Single-team Finals/conference-finals record phrasing returns unsupported-filter no-result. | Current contracts support round leaderboards and matchup history, not single-team round records; some historical round labels are unreliable. | Approve single-team playoff round semantics and fallback behavior for unreliable labels, then add route/output coverage. |
| Subjective/trend queries | Clutch, cooled off, best defender, MVP candidate, best player lately, and similar opinion/trend requests return unsupported/no-result instead of invented definitions. | Product-approved metric definitions and source coverage are required. | Define metric-backed semantics one family at a time, then add parser, execution, copy, and QA coverage. |
| Multi-player availability | Multi-player availability record phrasing returns explicit unsupported/no-result instead of an unfiltered team record. | Multi-player availability semantics are outside the current whole-game single-player absence contract. | Add a dedicated availability model, trusted coverage fields, filter semantics, and result contract. |
| Lineup summaries / leaderboards where trusted coverage is unavailable | Current guarded cases such as `best 5-man lineups` and lineup membership summaries return explicit unsupported/no-result responses. | Trusted lineup/stint coverage is unavailable for those release cases, and generic display contracts remain risky for real lineup identity fields. | Add or verify a dedicated lineup dataset with grain, join keys, trust fields, identity columns, frontend rendering, and fallback behavior. |
| On/off surfaces where trusted data is unavailable | Current guarded on/off cases return explicit unsupported/no-result responses. Whole-game `without_player` remains separate. | Trusted stint/on-off coverage is unavailable for those release cases and cannot be substituted with absence records. | Add trusted on/off coverage with `on` and `off` buckets, source trust semantics, and clear fallback behavior. |
| Team rolling-stretch leaderboards | Team-scoped rolling-stretch wording returns unsupported-filter no-result. | Current rolling-stretch support is player-oriented and no team route/result contract is approved. | Define team rolling-window metrics, result sections, route behavior, and frontend display. |
| Minutes leaderboards | Guarded as unsupported/product-boundary behavior. | Minutes need an explicit stat/leaderboard support decision and display/minimum contract. | Approve the stat contract and add route/output/frontend/corpus coverage. |
| Team single-game threes | Guarded as unsupported/product-boundary behavior where currently unrouted or unsupported. | Team `fg3m` top-game support needs an explicit route and product decision. | Add top-team-game stat support and selected frontend-copy cases if promoted. |

## 5. QA Artifacts

Latest release artifacts:

- Backend raw QA report:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl`
- Backend raw QA Markdown report:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.md`
- Frontend-copy report:
  `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`
- Visual QA checklist:
  `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- Preview manual QA rerun:
  `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`
- Release-readiness checklist:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- Release-readiness checkpoint:
  `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- Backend harness plan:
  `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
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
- `return_packages/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`

## 6. Known Limitations

- Frontend-copy QA is selected coverage: 125 rendered cases from the latest
  clean 246-case backend run, not all 246 backend cases.
- Frontend-copy QA checks DOM text and rendered component output; it is not
  visual layout or screenshot diff automation.
- Visual QA remains a manual 15-case baseline with accepted desktop/mobile
  checks, not automated Playwright screenshot diffing.
- Preview manual QA is `PREVIEW_READY_WITH_NOTES`; notes include the manual
  nature of visual QA and selected frontend-copy coverage.
- Unsupported features are guarded and documented; opponent-conference
  `team_record` filters are execution-backed only for trusted seasons
  `2024-25` and `2025-26`.
- Opponent-conference expansion outside trusted current-era coverage, divisions,
  and geography phrases remains unsupported/no-result.
- Frontend lint remains clean with 0 errors and the existing
  `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- Frontend build remains clean with the existing Vite large-chunk warning.

## 7. Future Deployment Checklist

Before deploying this boundary again:

- Run the full backend raw QA corpus:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Run frontend-copy QA:
  `cd frontend && npm run qa:frontend-copy`
- Run frontend build and lint:
  `cd frontend && npm run build`
  `cd frontend && npm run lint`
- Open `/`, `/review`, and `/visual-qa` on the target preview or production URL.
- Run the six smoke queries:
  - `Who leads the NBA in points per game this season?`
  - `What is Denver's record when Nikola Jokic has a triple-double?`
  - `Which team gave up the fewest points per game?`
  - `Lakers Celtics playoff matchup history`
  - `Warriors net rating this season`
  - `players with most personal fouls this season`
- Run a mobile visual QA five-case spot check:
  - `biggest_scoring_games`
  - `lebron_durant_comparison_wave4`
  - `heat_knicks_playoff_series_record_wave4`
  - `guards_fg_percentage_leaders`
  - `centers_rebound_leaders_wave4`
- Confirm unsupported boundaries still return explicit unsupported/no-result
  behavior and have not broadened into plausible but unsupported answers.

## 8. Next Roadmap Options

Recommended order after this release package:

1. Promote one unsupported family into real support.
   - Best first candidates: opponent-conference filters now that the
     current-era data prerequisite exists, single-team advanced scalar
     summaries, or rookie/role leaderboards, depending on product need and
     available source contracts.
2. Visual QA automation.
   - Add Playwright/screenshot baselines or pixel/layout assertions for the
     accepted 15-case visual corpus before expanding visual scope.
3. Frontend-copy Wave 3 only after fresh gap analysis.
   - Expand only if a route/shape risk is still meaningfully undercovered after
     the 125-case set.
4. Harness tag/category filters.
   - Add focused selection by corpus tags/categories if future fix waves need
     faster iteration than saved slices provide.
5. Broader release/CI artifact packaging.
   - Package raw QA, frontend-copy, preview manual QA, and visual QA outputs
     into a repeatable CI/release artifact bundle.
