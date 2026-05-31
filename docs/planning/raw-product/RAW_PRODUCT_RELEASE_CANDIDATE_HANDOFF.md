# Raw Product Release Candidate Handoff

## 1. Executive summary

- Release status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- Query feedback status: `FEEDBACK_READY_WITH_NOTES`.
- Public UI status: `PUBLIC_UI_READY_WITH_NOTES`.
- What is ready: the current Raw Product supported and explicitly unsupported
  boundary is ready for handoff. The latest full Backend Raw QA run is clean at
  246/246 cases, selected frontend-copy QA rendered 125/125 cases with soft
  checks `480/0/0`,
  required R2 data is available, deployment smoke passed, and the latest
  preview `/visual-qa` request-health check loaded 15/15 cases with request
  errors 0. Query Feedback + Diagnostic Logging V1 is included in the current
  release candidate, passed R2 record inspection with notes, and now has an
  implemented read-only feedback review/export workflow. Front-facing Result
  UI Productization Wave 1 adds a public default result mode on `/`, preserves
  diagnostics in Details and `?debug=1`, keeps `/review` debug-rich, and keeps
  `/visual-qa` usable for public rendering checks. Wave 2 completes the
  answer-first public hierarchy pass: successful public results now render the
  answer hero before actions, place user-facing context and material caveats
  near the answer, keep actions secondary, tighten dense mobile tables, and
  reduce duplicate public no-result Details. The final Public UI Release
  Review passed on the live main preview with 14 desktop query checks, 13
  mobile 390px family checks, preserved debug/review/visual-QA paths, preserved
  feedback UI, and no blocking issues. Raw Product Post-Review Hardening Waves
  1–6 are now complete, and the follow-up AppTheming test drift fix established
  a clean full frontend suite: 25/25 files and 352/352 tests passing. The
  expanded local Visual QA baseline also passed 20/20 cases at desktop and
  mobile, 40 viewport reviews total, with request errors 0 and no blocking
  visual issue. The canonical local non-diffing screenshot artifact run also
  passed for the expanded 20-case corpus.
- What remains as known notes: frontend-copy QA is selected coverage, visual QA
  remains manually reviewed even with local non-diffing screenshot artifact
  capture, opponent-conference support is limited to trusted seasons `2024-25`
  and `2025-26`, feedback triage suggestions are heuristic, corpus conversion
  remains manual, automatic parser/QA/GitHub issue mutation is not implemented,
  and explicitly unsupported boundaries must continue to return guarded
  no-result or unsupported behavior. Public UI is ready with notes; broader
  unsupported-copy refinement, screenshot diffing/baseline/CI decisions,
  `natural_query.py` extraction, return-package archive sweep, and
  branding/name change are post-launch/deferred notes rather than launch
  blockers.
- Division Phrase Boundary Cleanup is complete for this handoff boundary:
  explicit NBA division opponent phrases return `no_result` /
  `filter_not_supported` with empty sections and
  `metadata.unsupported_filters=["opponent_division"]` instead of broad
  `team_record`, `team_record_leaderboard`, or conference-only answers. This
  did not add division support, and Conference Finals record phrasing remains
  on the `single_team_playoff_round_record` unsupported boundary.
- Public Query Acceptance Coverage Waves 1, 2A, 2B, 2C, and 2D are complete.
  `public_query_acceptance` is now the public phrasing acceptance gate and
  passed 67/67 cases. `basic_public_availability` passed 7/7, and
  `natural_query_route_priority` plus `product_boundaries` passed 49/49. Raw
  QA corpus size alone is not enough public-readiness evidence; every
  advertised family needs acceptance-family coverage. Fuzzy player typo
  correction is intentionally deferred to V2, so unsupported or misspelled
  player fragments no-result cleanly instead of silently correcting.
- Recommended handoff decision: ship or hand off the current release candidate
  with notes. Query feedback and the previous debug-heavy default UI are no
  longer preview/public-launch blockers. Missing required R2 data remains a
  release blocker.

## 2. Validation evidence

| Area | Status | Evidence |
|---|---|---|
| Raw QA | `PASS` | Latest full release run: `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases; expectation cases `pass: 246`; expectation checks `pass: 1421`; failed IDs none; suspicious flags 0. Current corpus has 294 cases observed at the public-query acceptance closure docs refresh; later targeted evidence is recorded below. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260518T175548Z/frontend_copy_report.md`; 125 selected cases rendered; render failures 0; missing backend records 0; soft checks `480/0/0`. |
| Preview smoke | `PASS_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; four supported opponent-conference preview checks passed, two guardrails passed, and `/visual-qa` request errors were 0. |
| R2 data availability | `PASS` | `raw/teams/team_conference_membership.csv` exists in R2; dry-run, sync, and `head_object` evidence passed with `ContentLength=4999`, `LastModified=2026-05-17T09:03:29+00:00`, and `nbatools-md5=f9cc9a60c8f659651723a55640966d73`. |
| Deployment smoke | `PASS` | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `case_count: 7`, `failure_count: 0`, and the R2-sensitive opponent-conference team-record check returned 15 East opponents. |
| Visual QA | `PASS_WITH_MANUAL_LIMITATION` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; expanded local manual baseline passed 20 cases / 40 desktop-mobile viewport reviews, and canonical local artifact run `visual_qa_20_case_baseline` captured the expanded corpus at desktop and mobile with request errors 0, statuses `ok: 15`, `no_result: 5`, `error: 0`, overflow false, and 42 expected PNGs total; the original 15-case baseline remains the latest deployed preview request-health evidence before expansion; no screenshot diffing, committed PNG baselines, or CI gate exists yet. |
| Query Feedback + Diagnostic Logging V1 | `FEEDBACK_READY_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; R2 list/get passed under `nbatools-data` prefix `query_feedback/preview`, user-submitted feedback records were found, automatic diagnostics were found, sanitizer/privacy checks passed, and `/review` plus `/visual-qa` suppression passed. |
| Query feedback review/export workflow | `IMPLEMENTED_WITH_NOTES` | `docs/operations/query_feedback_review.md`; launch review can run `make query-feedback-export`, which wraps `tools/export_query_feedback.py` and writes `feedback_review.md`, `feedback_records.csv`, `feedback_records.jsonl`, `summary.json`, and `triage_decisions_template.csv`. |
| Front-facing result UI productization Wave 1 | `PASS_WITH_NOTES` | `/` now defaults to public result rendering; `?debug=1` restores debug chrome; `/review` remains debug-rich; `/visual-qa` keeps internal case metadata while rendering public results; feedback payload diagnostics remain preserved. |
| Front-facing result UI productization Wave 2 | `PASS_WITH_NOTES` | Public `/` is answer-first, public context/caveats render near the hero, successful-result actions are secondary, dense mobile tables use tighter shared padding and column priorities, public no-result has one diagnostics disclosure, `?debug=1`, `/review`, `/visual-qa`, and feedback diagnostics remain preserved. |
| Final Public UI Release Review | `PUBLIC_UI_READY_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; live main preview checked `/`, `/?debug=1`, `/review`, and `/visual-qa`; 14 desktop public queries and 13 mobile 390px family checks passed; debug/details and feedback preservation passed; blocking issues none. |
| Post-review hardening Waves 1–6 | `COMPLETE_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; Waves 1–6 completed parser/routing guardrails, feature promotion rules, Data/R2 checklist hardening, feedback review cadence, docs/return-package taxonomy, README positioning, homepage product-promise polish, and public answer context de-duplication. |
| AppTheming test drift fix / full frontend suite | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; test-only wait-gate drift fixed in `frontend/src/test/AppTheming.test.tsx`; full frontend suite now passes 25/25 files and 352/352 tests. |
| Division boundary cleanup | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; targeted snapshots passed 65 tests, `test-parser` passed 776, `test-query` passed 776, raw QA route-priority slice passed 35/35, raw QA product-boundaries slice passed 18/18, `test-preflight` passed 2978 with 1 xpassed, and `git diff --check` passed. |
| Public-query acceptance coverage | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; Waves 1 and 2A–2D complete; `public_query_acceptance` passed 67/67, `basic_public_availability` passed 7/7, `natural_query_route_priority` + `product_boundaries` passed 49/49, `test-parser` passed 788, final targeted prior `test-query` failures passed, and `git diff --check` passed. |
| Build/lint/test evidence | `PASS` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`; frontend build passed with the previous Vite large-chunk warning cleared, lint passed with the previous review-page warning cleared, full frontend tests passed 352/352 after the AppTheming test drift fix, team conference data tests passed 15 tests, parser smoke passed 751 tests, and query smoke passed 752 tests. |

## 3. Feedback and diagnostics V1

Query Feedback + Diagnostic Logging V1 is part of the current release
candidate. The latest R2 inspection classified it as
`FEEDBACK_READY_WITH_NOTES`.

Verified feedback evidence:

- Direct endpoint and user-submitted product feedback writes were verified in
  R2.
- Automatic no-result/unsupported and unrouted/error diagnostics were verified
  in R2.
- Sanitization and privacy checks passed: no disallowed PII fields and no raw
  result rows/tables were found in inspected records.
- `/review` and `/visual-qa` suppression passed; inspected records came from
  the product `/` surface, not QA/review pages.
- Preview records currently use bucket `nbatools-data` with isolated prefix
  `query_feedback/preview` because the dedicated feedback bucket was
  unavailable.

The feedback review/export workflow is also implemented:

- Launch review can run `make query-feedback-export`.
- The make target is a thin wrapper around `tools/export_query_feedback.py`.
- Outputs are `feedback_review.md`, `feedback_records.csv`,
  `feedback_records.jsonl`, `summary.json`, and
  `triage_decisions_template.csv`.

Remaining feedback notes are operational follow-ups, not preview blockers:

- Triage suggestions are heuristic and reviewer-owned decisions remain manual.
- Corpus conversion remains manual after review.
- Review decisions do not automatically mutate parser behavior, QA corpus
  files, or GitHub issues.

## 4. Supported product boundary

The release candidate supports the current Raw Product areas covered by the
clean raw QA corpus, selected frontend-copy corpus, visual baseline, query
catalog, and query guide:

- Player summaries: current-season, career, recent, last-N, opponent,
  opponent-quality, home/away, wins/losses, role-context, selected
  stat-context, and supported player-vs-player opponent-filter summaries.
- Team records: overall, home/away, road, explicit-season, last-season,
  month-window, since-date, since All-Star, opponent-quality,
  scoring-threshold, opponent-points-threshold, and `how did TEAM do`
  record-style summaries.
- Record-when conditions: player stat thresholds, player special events,
  player shooting thresholds, team scoring thresholds, and team
  opponent-points thresholds.
- Without-player conditions: single-player whole-game absence records and
  summaries where trusted source coverage exists.
- Leaderboards: standard player and team leaderboards, per-game and percentage
  aliases, supported advanced-stat aliases, position-filtered player
  leaderboards, record leaderboards, scoring/team-threes leaderboards, and
  opponent-points/points-allowed leaderboards.
- Team advanced leaderboards: league-wide net rating, offensive rating,
  defensive rating, and pace leaderboards.
- Top performances: player single-game points, assists, rebounds, threes,
  blocks, steals, plus-minus, named-player best-game/season-high phrasing, and
  supported team top scoring games.
- Finder/count outputs: player and team finder rows, count-with-finder outputs,
  distinct player/team threshold counts, supported compound thresholds,
  defensive threshold finders, and selected game-log detail shapes.
- Streaks: player stat-threshold streaks, player special-event streaks,
  current/completed phrasing, team win streaks, and team scoring/three-point
  threshold streaks.
- Rolling stretches: player rolling-stretch leaderboards for supported counting
  stats, shooting percentages, Game Score, named-player variants, and
  league-wide player stretch phrasing.
- Splits: player and team home-away splits, wins-losses splits, recent/last-N
  split contexts, and supported stat-context split phrasing.
- Playoff history: single-team playoff history, playoff appearances,
  Finals/conference-finals appearance summaries, era/decade records, and
  supported playoff-history phrasing.
- Playoff matchup history: explicit team-pair playoff history, series
  record/history, matchup history, Finals matchup history, and adjacent-team
  playoff series phrasing.
- Playoff round/appearance leaderboards: round-record leaderboards and most
  round or Finals appearance leaderboards, including covered since-year
  filters.
- Comparisons: full-name player comparisons, recent player comparisons, team
  comparisons, matchup records, head-to-head summaries, and guarded
  stat-vs-player interpretations.
- Date/window filters: explicit seasons, latest-season defaults, last season,
  season ranges, explicit dates, month windows, since-date windows, last-N
  games, recent/lately defaults, since All-Star, and selected rolling-day
  phrasing.
- Defensive/opponent-points aliases: points allowed, opponent PPG, `gave up`,
  `allowing`, `held teams under`, `held opponents under`, `limited opponents
  to`, and related defensive threshold variants.
- Opponent-conference team-record filters: East/West team-record filters are
  execution-backed only for trusted seasons `2024-25` and `2025-26`.

## 5. Explicit unsupported boundaries

The following areas are intentionally outside the current product boundary.
They should stay guarded by explicit no-result, unsupported, unsupported-data,
or `filter_not_supported` behavior rather than broad fallback answers:

- Personal-foul leaderboards.
- Single-team advanced-stat scalar summaries.
- Rookie leaderboards.
- League-wide starter/bench leaderboards.
- Team bench scoring.
- Single-team playoff round records.
- Subjective/trend queries such as clutch, cooled off, best defender, MVP
  candidate, and best player lately.
- Lineup summaries and lineup leaderboards where trusted coverage is
  unavailable.
- On/off surfaces where trusted data is unavailable.
- Team rolling-stretch leaderboards.
- Minutes leaderboards.
- Team single-game threes.
- Explicit NBA division opponent phrases: `team_record` for named-team record
  phrases and `team_record_leaderboard` for no-subject record phrases, with
  `unsupported_filters=["opponent_division"]`; no division filtering support.
- Geography phrases such as `east coast teams` and `west coast teams`.
- Historical opponent-conference coverage outside trusted seasons `2024-25` and
  `2025-26`.

## 6. Deployment/data notes

- Preview uses `DATA_SOURCE=r2`.
- Vercel excludes `data/**`.
- New data files required at runtime must be synced to R2 before preview smoke.
- Current required R2 key: `raw/teams/team_conference_membership.csv`.
- Query feedback preview records are verified under `nbatools-data` prefix
  `query_feedback/preview`; the preferred future state remains a dedicated
  feedback bucket/token.
- Deployment smoke now protects opponent-conference data availability through
  an R2-sensitive team-record case.
- Missing required R2 data is a release blocker.
- Deployment workflow details are recorded in
  `docs/operations/deployment.md`.

## 7. Known limitations

- Frontend-copy QA is selected coverage, not every raw QA case.
- Visual QA remains manually reviewed even though local non-diffing screenshot
  artifact capture is implemented and validated; screenshot diffing, committed
  PNG baselines, and CI gating remain deferred.
- Opponent-conference support is limited to trusted seasons `2024-25` and
  `2025-26`.
- Query feedback is ready with notes: R2 inspection passed, the read-only
  review/export workflow and feedback console are implemented, triage
  suggestions are heuristic, corpus conversion remains manual, and review
  decisions do not automatically mutate parser behavior, QA corpus files, or
  GitHub issues.
- Public result mode is now answer-first on `/` after Wave 2, and the final
  Public UI Release Review classified it as `PUBLIC_UI_READY_WITH_NOTES`.
  Remaining UI notes are post-launch polish: broader unsupported-copy
  refinement, screenshot diffing/baseline/CI decisions, and continued internal
  horizontal scrolling for wide tables.
- Raw Product Post-Review Hardening Waves 1–6 are complete. Remaining
  hardening-cycle notes are post-launch/deferred: screenshot
  diffing/baseline/CI decisions after local artifact capture,
  `natural_query.py` extraction, return-package archive sweep, and
  branding/name change.
- The pre-existing AppTheming test drift surfaced during Wave 6 validation is
  fixed; the full frontend suite is now clean at 352/352 tests passing.
- Frontend lint no longer has the previous
  `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning after
  the internal review-page cleanup.
- Frontend build no longer has the previous Vite large-chunk warning after the
  internal-route lazy split.
- External NBA CDN image/logo request failures may occur. They are non-query
  blockers unless they affect the primary user experience.
- `public_query_acceptance` is the public phrasing acceptance gate. Raw corpus
  count alone is not enough evidence of public readiness; every advertised
  family needs acceptance-family coverage.
- Fuzzy player typo correction is deferred to V2. Unsupported or misspelled
  player fragments return clean no-result behavior instead of silent
  correction.

## 8. Final release checklist

- [ ] Run the full Raw QA corpus:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- [ ] Run the public phrasing acceptance gate:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure`
- [ ] Run frontend-copy QA: `cd frontend && npm run qa:frontend-copy`
- [ ] Run deployment smoke against the target preview or production URL.
- [ ] Confirm R2 `head_object` availability for required new data files,
  including `raw/teams/team_conference_membership.csv`.
- [ ] Confirm feedback storage status if feedback env changes; latest accepted
  preview evidence is `FEEDBACK_READY_WITH_NOTES` under
  `query_feedback/preview`.
- [ ] Run `make query-feedback-export` for launch feedback review when there
  are records to triage.
- [ ] Open preview `/`, `/review`, and `/visual-qa`.
- [ ] Confirm `/` is public by default, `/` with `?debug=1` exposes debug
  chrome, `/review` remains debug-rich, and `/visual-qa` still renders the
  selected visual cases.
- [ ] Confirm the public UI still matches the final release-review boundary:
  answer-first `/`, no default debug chrome, debug/details preservation,
  feedback controls on `/`, and no feedback controls on `/review` or
  `/visual-qa`.
- [ ] Run supported and unsupported smoke queries.
- [ ] Include division boundary smoke queries such as
  `Celtics record vs Atlantic Division`,
  `record against Northwest Division teams`, and
  `Lakers record against Western Conference Pacific Division teams`.
- [ ] Mobile spot-check primary result readability.
- [ ] Confirm there is no broad fallback for unsupported boundaries.

## 9. Recommended next roadmap

1. Proceed with launch/handoff using the current `*_WITH_NOTES` statuses.
2. Run the first launch feedback review using `make query-feedback-export`.
3. Treat the remaining notes as post-launch/deferred work: visual QA screenshot
   diffing/baseline/CI decisions, `natural_query.py` extraction, return-package
   archive sweep, and branding/name change.
4. Run the next unsupported-family promotion preflight only through the Wave 1
   and Wave 2 guardrails.
5. Add CI/release artifact packaging or harness tag/category filters only if
   workflow pain returns.
6. Keep acceptance-family coverage mandatory for newly advertised feature
   families, and reopen fuzzy player typo correction only through an explicit
   V2 product policy.
