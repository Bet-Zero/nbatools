# Raw Product Release Candidate Handoff

## 1. Executive summary

- Release status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- Query feedback status: `FEEDBACK_READY_WITH_NOTES`.
- What is ready: the current Raw Product supported and explicitly unsupported
  boundary is ready for handoff. Backend Raw QA is clean at 246/246 cases,
  selected frontend-copy QA rendered 125/125 cases with soft checks `480/0/0`,
  required R2 data is available, deployment smoke passed, and the latest
  preview `/visual-qa` request-health check loaded 15/15 cases with request
  errors 0. Query Feedback + Diagnostic Logging V1 is included in the current
  release candidate and passed R2 record inspection with notes.
- What remains as known notes: frontend-copy QA is selected coverage, visual QA
  is manual rather than screenshot-diff automation, opponent-conference support
  is limited to trusted seasons `2024-25` and `2025-26`, existing frontend
  build/lint warnings remain non-blocking, feedback export/admin workflow and
  full dedupe/rate limiting are not built yet, the dedicated feedback bucket is
  unavailable so preview uses an isolated feedback prefix in `nbatools-data`,
  and explicitly unsupported boundaries must continue to return guarded
  no-result or unsupported behavior.
- Recommended handoff decision: ship or hand off the current release candidate
  with notes. Query feedback is no longer a preview blocker. Missing required
  R2 data remains a release blocker.

## 2. Validation evidence

| Area | Status | Evidence |
|---|---|---|
| Raw QA | `PASS` | `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases; expectation cases `pass: 246`; expectation checks `pass: 1421`; failed IDs none; suspicious flags 0. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125 selected cases rendered; render failures 0; missing backend records 0; soft checks `480/0/0`. |
| Preview smoke | `PASS_WITH_NOTES` | `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`; four supported opponent-conference preview checks passed, two guardrails passed, and `/visual-qa` request errors were 0. |
| R2 data availability | `PASS` | `raw/teams/team_conference_membership.csv` exists in R2; dry-run, sync, and `head_object` evidence passed with `ContentLength=4999`, `LastModified=2026-05-17T09:03:29+00:00`, and `nbatools-md5=f9cc9a60c8f659651723a55640966d73`. |
| Deployment smoke | `PASS` | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `case_count: 7`, `failure_count: 0`, and the R2-sensitive opponent-conference team-record check returned 15 East opponents. |
| Visual QA | `PASS_WITH_MANUAL_LIMITATION` | Manual 15-case baseline remains accepted; latest preview `/visual-qa` loaded 15/15 cases with request errors 0; no screenshot-diff automation exists yet. |
| Query Feedback + Diagnostic Logging V1 | `FEEDBACK_READY_WITH_NOTES` | `return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`; R2 list/get passed under `nbatools-data` prefix `query_feedback/preview`, user-submitted feedback records were found, automatic diagnostics were found, sanitizer/privacy checks passed, and `/review` plus `/visual-qa` suppression passed. |
| Build/lint/test evidence | `PASS_WITH_EXISTING_WARNINGS` | Latest readiness docs record frontend build passing with the existing Vite large-chunk warning, frontend lint passing with 0 errors and the existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning, team conference data tests passing 15 tests, parser smoke passing 751 tests, and query smoke passing 752 tests. |

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

Remaining feedback notes are operational follow-ups, not preview blockers:

- No admin dashboard/export workflow yet.
- No full dedupe/rate limiting beyond normalized query hash.
- Dedicated feedback bucket/token should be provisioned later if the isolated
  prefix is not kept.
- Frontend network/non-JSON failure logging path was not live-tested during the
  R2 inspection.

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
- Divisions.
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

- Frontend-copy QA is selected coverage, not all 246 raw cases.
- Visual QA is manual, not screenshot-diff automation.
- Opponent-conference support is limited to trusted seasons `2024-25` and
  `2025-26`.
- Query feedback is ready with notes: no admin dashboard/export workflow yet,
  no full dedupe/rate limiting beyond hash, dedicated feedback bucket
  provisioning remains a later operational task, and the frontend
  network/non-JSON failure path was not live-tested in the R2 inspection.
- Frontend lint still has the existing
  `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` warning in the
  latest readiness evidence.
- Frontend build still has the existing Vite large-chunk warning in the latest
  readiness evidence.
- External NBA CDN image/logo request failures may occur. They are non-query
  blockers unless they affect the primary user experience.

## 8. Final release checklist

- [ ] Run the full Raw QA corpus:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- [ ] Run frontend-copy QA: `cd frontend && npm run qa:frontend-copy`
- [ ] Run deployment smoke against the target preview or production URL.
- [ ] Confirm R2 `head_object` availability for required new data files,
  including `raw/teams/team_conference_membership.csv`.
- [ ] Confirm feedback storage status if feedback env changes; latest accepted
  preview evidence is `FEEDBACK_READY_WITH_NOTES` under
  `query_feedback/preview`.
- [ ] Open preview `/`, `/review`, and `/visual-qa`.
- [ ] Run supported and unsupported smoke queries.
- [ ] Mobile spot-check primary result readability.
- [ ] Confirm there is no broad fallback for unsupported boundaries.

## 9. Recommended next roadmap

1. Visual QA automation preflight.
2. Query feedback export/review script.
3. Next unsupported-family promotion preflight.
4. CI/release artifact packaging.
5. Frontend-copy Wave 3 only after fresh gap analysis.
6. Harness tag/category filters if workflow pain returns.
