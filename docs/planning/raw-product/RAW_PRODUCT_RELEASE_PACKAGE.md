# Raw Product Release Package

## 1. Release Status

- Recommended status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- Query feedback status: `FEEDBACK_READY_WITH_NOTES`.
- Public UI status: `PUBLIC_UI_READY_WITH_NOTES`.
- Release date: 2026-05-17.
- Latest feedback readiness refresh: 2026-05-18.
- Latest front-facing UI refresh: 2026-05-19.
- Latest post-review hardening closure refresh: 2026-05-21.
- Latest division boundary cleanup refresh: 2026-05-22.
- Latest expanded visual QA baseline refresh: 2026-05-22.
- Latest visual QA screenshot artifact validation refresh: 2026-05-22.
- Latest public-query acceptance coverage closure refresh: 2026-05-31.
- Scope: current supported and explicitly unsupported Raw Product boundary.
- Production code changed for this package: yes, frontend only.
- Frontend rendering changed for this package: yes, public/default result mode
  added and Wave 2 answer-first/mobile polish completed.
- Backend query behavior changed for this package: no.
- QA corpus expectations changed for this package: no.
- Production-ready: yes after human acceptance of the release notes below.
- Preview-ready: yes, with notes.
- Release-candidate ready: yes, with notes.
- Query Feedback + Diagnostic Logging V1 included in release candidate: yes.
- Query feedback review/export workflow implemented: yes, with notes.
- Final Public UI Release Review passed: yes, with notes.
- Raw Product Post-Review Hardening Waves 1–6 complete: yes, with notes.
- AppTheming test drift fixed: yes; full frontend suite now clean at 352/352.
- Final handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`;
  handoff complete with notes.

This boundary is release-candidate ready for the current product surface. The
backend raw QA corpus is clean, selected frontend-copy QA is clean, the accepted
original 15-case visual baseline has a clean preview rerun, the expanded local
visual corpus baseline now passes 20 cases / 40 desktop-mobile viewport
reviews, the canonical local non-diffing screenshot artifact run also passed
for the expanded 20-case corpus, and the manual preview smoke set passed with
notes. The later
opponent-conference preview blocker is now
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
Front-facing Result UI Productization Wave 1 is also included: `/` now defaults
to public result rendering, `?debug=1` restores debug chrome, result Details
preserve route/status/reason/query-class/freshness/query/filter/metadata/JSON
diagnostics, `/review` remains debug-rich, and `/visual-qa` remains usable for
public rendering checks.
Front-facing Result UI Productization Wave 2 is also included: public `/`
renders the answer hero before successful-result actions, places context chips
and material caveats near the hero before long tables, makes actions visually
secondary, tightens dense mobile tables through shared padding and bounded
column-priority flags, and avoids duplicate public no-result Details while
preserving diagnostics.
Final Public UI Release Review has now passed with
`PUBLIC_UI_READY_WITH_NOTES`: live preview route checks for `/`, `/?debug=1`,
`/review`, and `/visual-qa` passed; 14 desktop public queries passed; 13 mobile
390px family checks passed; debug/details preservation passed; feedback UI
preservation passed; blocking issues were none. Broad public launch is no
longer blocked by debug-heavy default UI.
Post-review hardening is now complete through Wave 6, and the follow-up
AppTheming test drift fix resolved the pre-existing full-suite drift surfaced
during Wave 6 validation. The latest full frontend suite evidence is clean:
25/25 files and 352/352 tests passing. This closure refresh is docs-only and
does not change backend behavior, parser/routing behavior, result contracts,
frontend rendering, QA corpus expectations, or release status.
Division Phrase Boundary Cleanup is also complete: explicit NBA division
opponent phrases no longer broad-fallback to ordinary team-record or
record-leaderboard answers. They return `no_result` /
`filter_not_supported`, empty sections, and
`metadata.unsupported_filters=["opponent_division"]`. Named-team division
record phrases preserve `team_record`; no-subject division record phrases
preserve `team_record_leaderboard`; mixed conference-plus-division text does
not return a broader conference-only answer. Division support was not added.
Public Query Acceptance Coverage Waves 1, 2A, 2B, 2C, and 2D are also
complete. `public_query_acceptance` is now the public phrasing acceptance gate:
its latest run passed 67/67 cases, while `basic_public_availability` passed
7/7 and the combined `natural_query_route_priority` plus `product_boundaries`
regression run passed 49/49. Raw QA corpus size alone is not enough evidence of
public readiness; every advertised feature family needs acceptance-family
coverage. Team-record availability basic failures are fixed,
no-broad-fallback guards are strengthened, and fuzzy player typo correction is
intentionally deferred to V2. Unsupported or misspelled player fragments
return clean no-result behavior instead of silent correction.

Human sign-off still needed:

- Product owner acceptance that selected frontend-copy coverage is sufficient
  for this release and does not need every backend raw QA case rendered.
- Product owner acceptance that visual QA remains manually reviewed even with
  local non-diffing screenshot artifact capture; screenshot diffing, committed
  PNG baselines, and CI gating remain deferred.
- Product owner acceptance that the explicitly guarded unsupported families
  remain unsupported for this release.
- Product owner acceptance that remaining feedback limitations are operational
  follow-ups: heuristic suggestions only, manual corpus conversion, and no
  automatic parser/QA/GitHub issue mutation from review decisions.
- Product owner acceptance that public result UI productization has completed
  the Wave 2 hierarchy/mobile pass and final public UI release review, while
  broader no-result/unsupported copy refinement, screenshot diffing/baseline/CI
  decisions, and wide-table internal scrolling remain post-launch polish notes.
- Product owner acceptance that post-review hardening Waves 1–6 are complete
  with notes, and remaining items are post-launch/deferred: screenshot
  diffing/baseline/CI decisions after the validated local artifact capture,
  `natural_query.py` extraction, return-package archive sweep, and
  branding/name change.
- Product owner acceptance that V1 intentionally defers fuzzy player typo
  correction to V2 and keeps unsupported or misspelled player fragments on a
  clean no-result path.

## 2. Validation Summary

| Area | Status | Evidence |
|---|---|---|
| Backend Raw QA | `PASS` | Latest full release run: `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases; expectation cases `pass: 246`; expectation checks `pass: 1421`; failed IDs none; suspicious flags 0. Current corpus has 294 cases observed at the public-query acceptance closure docs refresh; later targeted evidence is recorded below. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260518T175548Z/frontend_copy_report.md`; 125 selected cases; rendered 125; render failures 0; missing backend records 0; soft checks `480/0/0`. |
| Visual QA | `ACCEPTED_WITH_MANUAL_LIMITATION` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; expanded local manual baseline passed 20 cases / 40 desktop-mobile viewport reviews, and canonical local artifact run `visual_qa_20_case_baseline` captured 20 desktop plus 20 mobile card screenshots with request errors 0, statuses `ok: 15`, `no_result: 5`, `error: 0`, overflow false, and 42 expected PNGs total; the original 15-case desktop/mobile baseline remains the latest deployed preview request-health evidence before expansion; no screenshot diffing, committed PNG baselines, or CI gate. |
| Preview manual QA | `PREVIEW_READY_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; `/`, `/review`, `/visual-qa`, six smoke queries, and five mobile blocker cases passed. |
| Opponent-conference preview smoke | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; four supported opponent-conference queries passed, geography/playoff-round guardrails passed, and `/visual-qa` request errors were 0. |
| R2 data availability | `PASS` | R2 dry-run included `raw/teams/team_conference_membership.csv`; sync uploaded it; `head_object` returned `ContentLength=4999`, `LastModified=2026-05-17T09:03:29+00:00`, and `nbatools-md5=f9cc9a60c8f659651723a55640966d73`. |
| Deployment smoke | `PASS` | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `case_count: 7`, `failure_count: 0`, and `query_celtics_record_against_east_current` returned `team_record` / `ok` with 15 East opponents. |
| Query Feedback + Diagnostic Logging V1 | `FEEDBACK_READY_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; R2 list/get passed, user-submitted feedback writes were verified, automatic diagnostics were verified, sanitization/privacy checks passed, no raw result rows/tables were found, and `/review` plus `/visual-qa` suppression passed. |
| Query feedback review/export workflow | `IMPLEMENTED_WITH_NOTES` | `docs/operations/query_feedback_review.md`; launch review can use `make query-feedback-export`, backed by `tools/export_query_feedback.py`, to generate `feedback_review.md`, `feedback_records.csv`, `feedback_records.jsonl`, `summary.json`, and `triage_decisions_template.csv`. |
| Front-facing result UI productization Wave 1 | `PASS_WITH_NOTES` | Public mode hides route/query-class/status/reason/JSON/dev chrome by default while preserving diagnostics in Details and feedback payloads. `/review` remains debug-rich; `/visual-qa` renders public results with internal case metadata. |
| Front-facing result UI productization Wave 2 | `PASS_WITH_NOTES` | Public successful results are answer-first, context/caveats sit near the hero, actions are secondary, dense mobile tables use tighter padding and column-priority flags, no-result public diagnostics use a single Details disclosure, and debug/review/visual QA/feedback diagnostics are preserved. |
| Final Public UI Release Review | `PUBLIC_UI_READY_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; routes `/`, `/?debug=1`, `/review`, and `/visual-qa` passed; 14 desktop queries and 13 mobile 390px family checks passed; debug/details and feedback preservation passed; blocking issues none. |
| Post-review hardening Waves 1–6 | `COMPLETE_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; waves completed parser/routing guardrails, feature promotion rules, Data/R2 checklist hardening, feedback review cadence, docs/return-package taxonomy, README positioning, homepage product-promise polish, and public context de-duplication. |
| AppTheming test drift fix / full frontend suite | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; test-only drift fixed and full frontend suite passed 25/25 files and 352/352 tests. |
| Division phrase boundary cleanup | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; targeted snapshots passed 65 tests, parser/query slices passed 776 tests each, raw QA `natural_query_route_priority` passed 35/35, raw QA `product_boundaries` passed 18/18, `test-preflight` passed 2978 with 1 xpassed, and `git diff --check` passed. |
| Public-query acceptance coverage | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; Waves 1 and 2A–2D complete; `public_query_acceptance` passed 67/67, `basic_public_availability` passed 7/7, `natural_query_route_priority` + `product_boundaries` passed 49/49, `test-parser` passed 788, final targeted prior `test-query` failures passed, and `git diff --check` passed. |
| Frontend build | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; internal `/review` and `/visual-qa` route chunks split from the public entry, `npm --prefix frontend run build` passed, and the previous Vite large-chunk warning cleared. |
| Frontend lint | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; the internal review-page cleanup passed `npm --prefix frontend run lint` with no lint warnings. |
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
| Opponent-conference coverage gaps / geography / divisions | Current-era `team_record` opponent-conference filters are supported for trusted seasons `2024-25` and `2025-26`; seasons outside trusted coverage return `conference_coverage`; geography phrases such as `east coast teams` return `opponent_conference`; explicit NBA division requests return `opponent_division`. Division phrases preserve the closest record route but return no-result with empty sections instead of broad full-season, record-leaderboard, or conference-only answers. | Historical conference coverage, divisions, and geography semantics are not part of the approved data contract. Division filtering itself is not supported. | Add trusted historical conference membership or division/geography contracts before expanding beyond the current-era East/West team-record filter. |
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
  `outputs/frontend_copy_qa/20260518T175548Z/frontend_copy_report.md`
- Visual QA checklist:
  `docs/operations/frontend_visual_qa.md`
- Preview manual QA evidence:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- Release-readiness checklist:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- Post-review hardening closure evidence:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- AppTheming test drift fix evidence:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- Release-candidate handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- Release-readiness checkpoint:
  `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- Query feedback R2 inspection:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- Query feedback review workflow V1:
  `docs/operations/query_feedback_review.md`
- Query feedback implementation evidence:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
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

Durable supporting evidence:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/operations/query_feedback_review.md`
- `docs/operations/deployment.md`

## 6. Known Limitations

- Frontend-copy QA is selected coverage: 125 rendered cases from the latest
  clean 246-case backend run, not every backend raw QA case.
- Frontend-copy QA checks DOM text and rendered component output; it is not
  visual layout or screenshot diff automation.
- Visual QA remains manually reviewed. The expanded local 20-case
  desktop/mobile pass is complete, and canonical local non-diffing screenshot
  artifact run `visual_qa_20_case_baseline` passed for that corpus. Screenshot
  diffing, committed PNG baselines, and a CI gate remain deferred; the original
  15-case desktop/mobile pass remains the deployed preview request-health
  evidence from before the five-case expansion.
- Preview manual QA is `PREVIEW_READY_WITH_NOTES`; notes include the manual
  nature of visual QA and selected frontend-copy coverage.
- The previous opponent-conference preview `BLOCKED` status is resolved by the
  R2 sync fix; missing R2 data for required release files remains a deploy
  blocker for future previews.
- Unsupported features are guarded and documented; opponent-conference
  `team_record` filters are execution-backed only for trusted seasons
  `2024-25` and `2025-26`.
- Opponent-conference expansion outside trusted current-era coverage, explicit
  division phrases, and geography phrases remain unsupported/no-result.
  Division phrases use `unsupported_filters=["opponent_division"]`; no
  division support was added.
- Conference Finals phrasing remains a playoff-round surface, not an
  opponent-conference filter.
- Frontend lint is clean; the internal review-page cleanup cleared the previous
  `react-hooks/exhaustive-deps` warning.
- Frontend build is clean; the internal-route lazy split cleared the previous
  Vite large-chunk warning.
- Query feedback is `FEEDBACK_READY_WITH_NOTES`, not blocked: preview records
  are verified under `nbatools-data` prefix `query_feedback/preview`, and the
  read-only review/export workflow is implemented. Remaining feedback notes are
  heuristic suggestions only, manual corpus conversion, and no automatic
  parser/QA/GitHub issue mutation from review decisions.
- Public result UI productization Wave 2 is implemented and the final public UI
  release review passed with `PUBLIC_UI_READY_WITH_NOTES`. Remaining public UI
  follow-ups are post-launch polish: broader no-result/unsupported copy
  coverage, screenshot diffing/baseline/CI decisions, and accepted internal
  horizontal scrolling for wide tables.
- Raw Product Post-Review Hardening Waves 1–6 are complete, and the AppTheming
  test drift fix restored a clean 352/352 full frontend-suite baseline.
  Remaining hardening-cycle notes are post-launch/deferred:
  `natural_query.py` extraction, return-package archive sweep, branding/name
  change, and screenshot diffing/baseline/CI decisions after local artifact
  capture.
- `public_query_acceptance` is the public phrasing acceptance gate. A raw QA
  case count alone does not establish public readiness; each advertised family
  needs acceptance-family coverage.
- Fuzzy player typo correction is deferred to V2. Unsupported or misspelled
  player fragments return clean no-result behavior instead of silently
  correcting through last-name or nickname aliases.

## 7. Future Deployment Checklist

Before deploying this boundary again:

- Run the full backend raw QA corpus:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Run the public phrasing acceptance gate:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure`
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
- Confirm `/` is public by default and answer-first, public context/caveats sit
  near the answer, `/` with `?debug=1` exposes route/status, Copy JSON, Raw JSON,
  and Dev Tools, `/review` remains debug-rich, and `/visual-qa` renders the
  visual case results.
- Confirm the final public UI release-review boundary still holds: no default
  route/status/raw debug chrome on `/`, Details exposes diagnostics, feedback
  controls remain available on `/`, and feedback controls remain suppressed on
  `/review` and `/visual-qa`.
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
  - `Celtics record vs Atlantic Division`
  - `record against Northwest Division teams`
  - `Lakers record against Western Conference Pacific Division teams`
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

1. Broader no-result/unsupported public-copy refinement.
   - Continue refining unsupported-boundary guidance after launch using feedback
     records and public-query evidence.
2. Visual QA screenshot follow-up.
   - Decide whether the validated non-diffing artifact capture should grow into
     screenshot diffing, committed PNG baselines, or a CI gate for the 20-case
     visual corpus.
3. First launch feedback review.
   - Run `make query-feedback-export`, inspect the generated artifacts, and
     manually fill the triage decisions template before converting verified
     issues into corpus or planning updates.
4. Promote another unsupported family into real support.
   - Candidates include historical opponent-conference expansion beyond trusted
     current-era seasons, single-team advanced scalar summaries, or rookie/role
     leaderboards, depending on product need and available source contracts.
5. Broader release/CI artifact packaging.
   - Package raw QA, frontend-copy, preview manual QA, and visual QA outputs
     into a repeatable CI/release artifact bundle.
6. Frontend-copy Wave 3 only after fresh gap analysis.
   - Expand only if a route/shape risk is still meaningfully undercovered after
     the 125-case set.
7. Harness tag/category filters.
   - Add focused selection by corpus tags/categories if future fix waves need
     faster iteration than saved slices provide.
8. Maintain acceptance-family coverage.
   - Require public-query acceptance coverage for every newly advertised
     feature family and keep fuzzy player typo correction deferred until a V2
     product policy explicitly ships it.
