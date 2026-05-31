# Raw Product QA Release Readiness Checkpoint

## 1. Executive summary

- Backend raw QA status: latest full run is clean for the 246-case release
  corpus; the current corpus has 294 cases observed at the public-query
  acceptance closure docs refresh, with later targeted raw QA slice evidence.
- Frontend-copy QA status: clean for the selected 125-case rendered-copy corpus
  sourced from the latest clean full backend run.
- Visual QA status: the expanded local manual corpus baseline completed 20 cases
  and 40 desktop/mobile viewport reviews on 2026-05-22 with request errors 0
  and no blocking visual issue; the earlier deployed preview request-health
  evidence still covers the original 15-case set. Canonical local non-diffing
  screenshot artifact run `visual_qa_20_case_baseline` also passed for the
  expanded 20-case corpus.
- Deploy parity status: `/visual-qa` now follows the same local and deployed SPA
  shell routing path as `/review`; the latest preview manual rerun is
  `PREVIEW_READY_WITH_NOTES`.
- Release package:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`.
- Release-readiness checklist:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`.
- Release-candidate handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`;
  handoff complete with notes.
- Latest checklist status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Release package status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Supported boundary update: current-era opponent-conference `team_record`
  filters are supported for trusted seasons `2024-25` and `2025-26`; missing
  coverage, geography, divisions, and single-team playoff-round phrasing remain
  guarded unsupported boundaries. Explicit NBA division opponent phrases now
  return `opponent_division` no-results instead of broad team-record,
  record-leaderboard, or conference-only answers; division support was not
  added.
- R2 preview blocker status: resolved. R2 now contains
  `raw/teams/team_conference_membership.csv`; dry-run, sync, and `head_object`
  evidence passed; the latest preview opponent-conference smoke passed on
  `https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app`.
- Latest deployment smoke:
  `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`;
  `ok: true`, `case_count: 7`, `failure_count: 0`, and the
  opponent-conference membership-data check returned 15 East opponents.
- Latest `/visual-qa` preview status: loaded 15/15 cases with request errors 0.
- Query feedback status: `FEEDBACK_READY_WITH_NOTES`. Query Feedback +
  Diagnostic Logging V1 is included in the release candidate and is no longer a
  preview blocker after R2 inspection verified user-submitted records,
  automatic diagnostics, sanitization/privacy, and `/review` plus `/visual-qa`
  suppression. Query Feedback Review Workflow V1 is implemented as a read-only
  launch review/export path.
- Public UI status: `PUBLIC_UI_READY_WITH_NOTES`. The final Public UI Release
  Review passed on the live main preview with route checks for `/`,
  `/?debug=1`, `/review`, and `/visual-qa`, 14 desktop public query checks, 13
  mobile 390px family checks, debug/details preservation, feedback preservation,
  and no blocking issues.
- Post-review hardening closure status: Raw Product Post-Review Hardening Waves
  1–6 are complete with notes. The follow-up AppTheming test drift fix resolved
  the pre-existing full-suite drift surfaced during Wave 6 validation.
- Full frontend test suite status: clean after the AppTheming test drift fix;
  25/25 files and 352/352 tests passing.
- Public-query acceptance coverage status: `PASS`. Waves 1, 2A, 2B, 2C, and
  2D are complete. `public_query_acceptance` is now the public phrasing
  acceptance gate and passed 67/67 cases; `basic_public_availability` passed
  7/7; `natural_query_route_priority` plus `product_boundaries` passed 49/49.
  Raw QA corpus size alone is not sufficient public-readiness evidence; every
  advertised feature family needs acceptance-family coverage.
- Release-readiness verdict: backend product QA is release-ready for the
  currently supported and intentionally unsupported corpus boundaries. The
  release checklist completed with current raw QA, frontend-copy QA, frontend
  build/lint, parser smoke, diff-check validation, preview manual QA, R2 data
  availability, deployment smoke, opponent-conference preview smoke, and query
  feedback R2 inspection, the implemented feedback review/export workflow, and
  final public UI release review. Broad public launch is no longer blocked by a
  debug-heavy default UI. The remaining notes are selected frontend-copy
  coverage, manually reviewed visual QA with local non-diffing artifacts,
  trusted-season limits for opponent-conference support, guarded unsupported
  boundaries, feedback operational follow-ups, and public UI post-launch
  polish:
  screenshot diffing/baseline/CI decisions after local artifact capture,
  unsupported/no-result copy taxonomy refinement, `natural_query.py`
  extraction, return-package archive sweep, branding/name change, and
  continued internal horizontal scrolling for wide tables.

## 2. Backend Raw Query Answer QA

- Corpus size: 294 cases observed at the public-query acceptance closure docs
  refresh.
- Latest run:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.md`.
- Latest release-package run:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.md`.
- Pass/fail: latest full run expectation cases `pass: 246`; failed case IDs:
  none. Latest division-boundary targeted slices passed 35/35
  `natural_query_route_priority` cases and 18/18 `product_boundaries` cases.
- Result statuses: `ok: 206`, `no_result: 31`, `error: 9`.
- Expectation checks: `pass: 1421`.
- Suspicious flags: 0.
- Informational flags: `frontend_hero_expected: 153`.
- Verified outliers: `top_performance_high_points: 1`.
- Manual review statuses: `pass: 35`, `expected_unsupported: 26`,
  `verified_outlier: 1`, `unreviewed: 184`.

Main coverage areas:

- player/entity summaries
- team records and team record leaderboards
- record-when player/team conditions
- without-player conditions
- player and team leaderboards
- top performances
- splits, comparisons, matchup records, and head-to-head summaries
- rolling stretches and streaks
- playoff history, playoff matchup history, playoff appearances, and playoff
  round/appearance leaderboards
- date/window filters, including last-N, month windows, explicit seasons,
  since-date windows, and since All-Star context
- opponent-quality, opponent-conference, position, role, stat alias, and
  defensive/opponent-points phrasing guardrails
- explicit unsupported-boundary behavior

Recent fix waves:

- Corpus Expansion Wave 5: 195 to 243 cases.
- Fix Wave 8A: defensive/opponent-points alias variants.
- Fix Wave 8B: playoff phrasing routing.
- Fix Wave 8C1: team record intent and since-date windows.
- Fix Wave 8C2: player entity and stat-context routing.
- Fix Wave 8D: product-boundary finalization.
- Opponent-Conference Promotion: current-era East/West `team_record` filters
  promoted to supported behavior; corpus grew from 243 to 246 cases.

## 2.1 Public Query Acceptance Coverage

- Status: `PASS`.
- Gate: `qa/harness_slices/public_query_acceptance.yaml`.
- Gate role: public phrasing acceptance gate. Raw QA count alone does not
  establish public readiness.
- Coverage rule: every advertised feature family needs acceptance-family
  coverage.
- Completed waves: Wave 1 seed; Wave 2A no-broad-fallback guards; Wave 2B
  availability shorthand/synonyms; Wave 2C route priority; Wave 2D typo-player
  decision.
- Latest public gate report:
  `outputs/raw_query_answer_qa/20260528T225801Z/report.md`; 67/67 passed.
- Basic availability report:
  `outputs/raw_query_answer_qa/20260528T224636Z/report.md`; 7/7 passed.
- Route-priority and product-boundary report:
  `outputs/raw_query_answer_qa/20260528T225437Z/report.md`; 49/49 passed.
- Parser slice: `make PYTEST=.venv/bin/pytest test-parser`; 788 passed.
- Query slice follow-up: prior false positives fixed; final targeted prior
  failures passed.
- Static diff check: `git diff --check`; clean.

Closure notes:

- Team-record availability basic failures are fixed.
- No-broad-fallback guards are strengthened.
- Fuzzy player typo correction is intentionally deferred to V2.
- Unsupported or misspelled player fragments return clean no-result behavior
  instead of silently correcting.

## 3. Coverage map

Supported/query-covered areas:

- Player/entity summaries: current-season, career, last-N, opponent-quality,
  home/away, wins/losses, role context, availability context, and selected stat
  contexts.
- Team records: overall, home/away, road, date windows, explicit seasons,
  opponent-quality, opponent-conference filters for trusted current-era seasons,
  scoring thresholds, opponent-points thresholds, and `how did TEAM do` W/L
  summary phrasing.
- Record-when conditions: player stat thresholds, special events such as
  triple-doubles, player shooting thresholds, team scoring thresholds, and team
  opponent-points thresholds.
- Without-player conditions: single-player absence record and player summary
  contexts where source coverage exists.
- Leaderboards: standard player stats, percentage/advanced aliases that are
  execution-backed, position-filtered player leaderboards, team stat
  leaderboards, team advanced leaderboards, and team record leaderboards.
- Team advanced leaderboards: league-wide net rating, offensive rating,
  defensive rating, and pace leaderboards are supported.
- Top performances: player single-game points, assists, rebounds, threes,
  blocks, steals, plus-minus, team scoring games, and named-player best-game
  phrasing.
- Splits: player/team home-away and wins-losses splits, player comparisons,
  team comparisons, and matchup record/comparison routes.
- Rolling stretches/streaks: player rolling stretch leaderboards and player/team
  streak queries covered by existing route contracts.
- Playoff history: single-team playoff history, appearances, finals/conference
  finals appearance leaderboards, round-record leaderboards, and era/decade
  records.
- Playoff matchup history: explicit team-pair playoff history, series history,
  matchup history, and Finals matchup history phrasing.
- Playoff round/appearance leaderboards: best round records and most round or
  Finals appearances, including since-year filters.
- Comparisons: full-name player comparisons, recent player comparisons, team
  comparisons, and guarded game-log/stat-vs-player interpretations.
- Date/window filters: explicit dates, closed month windows, since-date windows,
  latest-season defaults, last season, 2024-25 explicit season, last-N windows,
  and since All-Star.
- Opponent-quality/defensive-stat aliases: playoff-team/good-team buckets,
  top-defense context, points allowed, opponent PPG, `gave up`, `allowing`, and
  `held teams/opponents under` variants.
- Unsupported boundaries: unsupported surfaces are expected to return explicit
  `no_result` / `filter_not_supported` or otherwise expected corpus statuses
  instead of broad plausible answers.

## 4. Explicit unsupported boundaries

These surfaces are intentionally guarded by the corpus as unsupported behavior.
They are not current product failures.

- Personal-foul leaderboards:
  - Current behavior: returns `no_result` / `filter_not_supported` with
    `unsupported_filters=["personal_foul_leaderboard"]`; variants preserve
    `metadata.stat=pf` where parsed.
  - Why unsupported: personal fouls committed need an approved leaderboard stat
    contract before being exposed as a supported ranking.
  - Future support path: approve the stat contract, add execution-backed PF
    leaderboard behavior, then promote the current boundary cases into support
    expectations.
- Single-team advanced-stat scalar summaries:
  - Current behavior: single-team net/offensive/defensive rating and pace
    summary phrasing returns `single_team_advanced_stat_summary` unsupported
    metadata; league-wide team advanced leaderboards remain supported.
  - Why unsupported: there is no approved route/result contract for a single
    team advanced-stat scalar answer or rank-preserving lookup.
  - Future support path: add a dedicated summary or team-advanced lookup
    contract with stable sections, metadata, and frontend rendering.
- Rookie leaderboards:
  - Current behavior: returns an explicit unsupported-filter no-result.
  - Why unsupported: rookie status is not part of the trusted current
    leaderboard filter contract.
  - Future support path: add trusted rookie metadata, parser slots, execution
    filtering, and docs/tests.
- League-wide starter/bench leaderboards:
  - Current behavior: returns explicit unsupported-filter no-results for
    starter/bench leaderboard phrasing.
  - Why unsupported: league-wide role filters need source-backed role
    classification and a route contract.
  - Future support path: define role coverage, minimums, and stat contracts,
    then add execution-backed filters.
- Team bench scoring summaries:
  - Current behavior: returns explicit unsupported-filter no-results for team
    bench scoring/points.
  - Why unsupported: team bench scoring requires role-scoped team aggregation
    that is not part of the current team summary contract.
  - Future support path: define a team bench/unit scoring dataset or derived
    aggregation and expose stable summary sections.
- Opponent-conference coverage gaps, divisions, and geography phrases:
  - Current behavior: `team_record` queries support East/West opponent
    conference filters for trusted seasons `2024-25` and `2025-26`.
    Missing/untrusted seasons return `conference_coverage` no-result, and
    geography phrases such as `east coast teams` remain unsupported as
    `opponent_conference`. Explicit NBA division requests such as
    `Celtics record vs Atlantic Division` remain unsupported as
    `opponent_division`, preserving the closest record route and returning
    empty sections instead of broad fallback rows.
  - Why limited: historical conference membership, divisions, and geography
    semantics are not part of the approved current-era data contract.
  - Future support path: add trusted historical conference membership or a
    dedicated division/geography contract before expanding the boundary.
- Single-team playoff round records:
  - Current behavior: single-team Finals/conference-finals record phrasing
    returns explicit unsupported-filter no-results. Conference Finals wording is
    playoff-round phrasing, not opponent-conference filtering.
  - Why unsupported: current route/result contracts support round leaderboards
    and matchup history, but not single-team round records; pre-2001 round
    labels are also unreliable for some historical cases.
  - Future support path: approve single-team playoff round-record semantics,
    coverage requirements, and fallback behavior for unreliable round labels.
- Subjective queries such as clutch, cooled-off, best defender, MVP candidate,
  best player lately, and similar opinion/trend requests:
  - Current behavior: returns unsupported or no-result responses rather than
    inventing metric definitions.
  - Why unsupported: these require product-approved definitions and source
    coverage before becoming answerable.
  - Future support path: define metric-backed semantics and source coverage for
    each family, then add parser, execution, and copy contracts.
- Multi-player availability and on/off or lineup membership:
  - Current behavior: multi-player availability, on/off, and lineup membership
    forms return explicit unsupported/no-result responses.
  - Why unsupported: trusted stint/lineup data and multi-player availability
    semantics are outside the current product contract.
  - Future support path: add a dedicated lineup/stint dataset with documented
    grain, join keys, trust fields, and fallback behavior.
- Fuzzy player typo correction:
  - Current behavior: unsupported or misspelled player fragments return clean
    no-result behavior instead of silently correcting through last-name or
    nickname aliases.
  - Why unsupported: V1 does not ship edit-distance or phonetic player
    matching.
  - Future support path: define an explicit V2 intentional-correction policy,
    confidence thresholds, user-visible correction notes, and acceptance
    corpus assertions before enabling fuzzy resolution.
- Team rolling-stretch leaderboards:
  - Current behavior: team-scoped rolling-stretch wording returns explicit
    unsupported-filter no-results.
  - Why unsupported: current rolling-stretch support is player-oriented and no
    team route/result contract has been approved.
  - Future support path: define team rolling-window metrics, sections, and
    route behavior.
- Minutes leaderboards and team single-game threes:
  - Current behavior: guarded as product-boundary/stat-coverage decisions rather
    than current failures.
  - Why unsupported: these need explicit stat/route coverage decisions before
    being promoted.
  - Future support path: approve the stat contracts and add targeted route,
    output, frontend, and corpus coverage.

## 5. Verified outliers / data-quality notes

- The current verified outlier is `top_performance_high_points`.
- The specific allowlisted row is Bam Adebayo's 83-point game on
  2026-03-10, tracked in `qa/verified_outliers.yaml` as
  `bam_adebayo_83_points_2026_03_10`.
- The QA harness still detects high-point top-performance rows. Rows matching
  the allowlist move into the verified-outlier bucket; new high-point rows that
  are not allowlisted remain suspicious flags.
- A future data-quality review is triggered when a new extreme top-performance
  row appears, the allowlisted row no longer matches local source data, official
  source evidence changes, or a suspected impossible/statistically inconsistent
  row appears in QA output.
- Verified outliers are displayed as source data, not suppressed or capped.

## 6. Frontend-copy QA status

- Selected case count: 125.
- Configured source backend run:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl`.
- Latest clean run path:
  `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`.
- Latest release-checklist run path:
  `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`.
- Status: 125 rendered successfully, 0 render failures, 0 missing backend
  records, soft checks `pass: 480`, `fail: 0`, `not_checked: 0`.
- Earlier semantic-copy clean run:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`.
- Gating behavior: `qa:frontend-copy` now fails on render failures, missing
  backend records, soft-check failures, or unchecked soft checks.

Fixed findings:

- Shape coverage breadth: Wave 2 added selected DOM-copy coverage for streak
  tables, rolling stretches, count/finder outputs, successful team finder
  tables, game-summary logs, team split summaries, record-by-decade tables,
  record-by-decade leaderboards, and top-performance variants.
- Unsupported boundary coverage: Wave 2 added on/off and lineup no-result
  surfaces only. It does not promote on/off or lineup execution-backed support.
- Position filter visibility/source: guard-filtered leaderboard phrasing now
  carries `position_filter=guards` and renders the applied Position filter.
- Opponent-points hero wording: fewest/most allowed-points leaderboards render
  according to executed direction instead of implying best defense incorrectly.
- Unsupported no-result guidance: personal-foul, rookie, league-wide
  starter/bench, and team bench-scoring unsupported filters have specific
  no-result copy.
- Filtered leaderboard hero context: position-filtered heroes use guard/center
  context instead of generic `led the NBA` wording.

Remaining limitations:

- The frontend-copy corpus is selected, not the full backend corpus.
- The harness uses DOM text extraction from rendered components; it is not a
  full visual review.
- Exact frontend copy should become hard assertions only for targeted,
  stable regressions.

## 7. Visual QA status

- The expanded 20-case manual visual corpus baseline completed for `/visual-qa`
  on 2026-05-22 with 40 desktop/mobile viewport reviews.
- Desktop `1280px` and mobile `390px` local passes loaded 20/20 cases with
  request errors 0, statuses `ok: 15`, `no_result: 5`, `error: 0`, no
  document-level horizontal overflow, and no blocking visual issue.
- Expanded baseline evidence:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`.
- Canonical local screenshot artifact run `visual_qa_20_case_baseline` passed:
  `desktop_1280` and `mobile_390` each captured 20/20 cases with request
  errors 0, statuses `ok: 15`, `no_result: 5`, `error: 0`, and document/body
  overflow `false`.
- Artifact manifest evidence lists 20 desktop card screenshots and 20 mobile
  card screenshots; expected PNG total is 42 including two full-page captures.
- Artifact validation evidence:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`.
- Mobile dense table clipping was fixed for top performances, comparisons, and
  playoff matchup tables.
- Filtered leaderboard hero wording was fixed for guard/center examples.
- The current no-result card baseline was accepted.
- `/visual-qa` route status: implemented locally and in Vercel rewrite config
  with parity to `/review`.
- Latest preview manual rerun:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  status `PREVIEW_READY_WITH_NOTES`.
- Latest preview request-health rerun:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  `/visual-qa` loaded 15/15 cases with request errors 0.

Remaining limitations:

- Playwright-backed non-diffing screenshot artifact capture is implemented and
  locally validated. Screenshot diffing, committed PNG baselines, and CI gating
  remain deferred.
- Preview manual QA is accepted with notes, but it remains manual and
  measurement/spot-check based.
- The expanded 20-case evidence is local baseline capture; the older deployed
  preview request-health evidence still covers the pre-expansion 15-case route.

## 8. Query Feedback + Diagnostic Logging V1

Status: `FEEDBACK_READY_WITH_NOTES`.

Evidence:

- Latest inspection:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`.
- R2 list/get passed for bucket `nbatools-data` under isolated prefix
  `query_feedback/preview/2026/05/18/`.
- Known user-submitted records were found and inspected, including direct
  endpoint smoke, successful-answer feedback, and no-result feedback.
- Automatic diagnostics were found for unsupported/no-result and unrouted/error
  cases.
- Sanitization/privacy checks passed: no disallowed PII fields and no raw
  result rows/tables were found in inspected records.
- Suppression checks passed: inspected records did not come from `/review` or
  `/visual-qa`; the only automatic successful `ok` record was above the
  slow-query threshold.

Query Feedback Review Workflow V1 is now implemented as the launch review path:

- Durable workflow runbook:
  `docs/operations/query_feedback_review.md`.
- Export script: `tools/export_query_feedback.py`.
- Make target: `make query-feedback-export`.
- Output artifacts: `feedback_review.md`, `feedback_records.csv`,
  `feedback_records.jsonl`, `summary.json`, and
  `triage_decisions_template.csv`.

Remaining feedback limitations are operational notes, not release blockers:

- Triage suggestions are heuristic and reviewer-owned decisions remain manual.
- Corpus conversion remains manual after review.
- Review decisions do not automatically mutate parser behavior, QA corpus
  files, or GitHub issues.

## 9. Validation strategy going forward

Latest release-readiness checklist validation:

- Checklist doc:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- Release package doc:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- Release-candidate handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`;
  handoff complete with notes.
- Status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Raw QA full corpus:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases;
  expectation cases `pass: 246`; failed case IDs none; suspicious flags 0.
- Frontend-copy QA:
  `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125
  selected cases from configured source backend run
  `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl`; rendered
  successfully 125; render failures 0; missing backend records 0; soft checks
  `480/0/0`.
- Frontend build: passed; the internal-route lazy split cleared the previous
  Vite large-chunk warning.
- Frontend lint: passed with 0 errors; the internal review-page cleanup cleared
  the previous `frontend/src/ReviewPage.tsx`
  `react-hooks/exhaustive-deps` warning.
- Team conference data validation:
  `.venv/bin/pytest tests/test_team_conference_membership_data.py -q` passed,
  15 tests.
- R2 data availability:
  `raw/teams/team_conference_membership.csv` was included in dry-run, uploaded
  during sync, and verified by `head_object` with `ContentLength=4999`,
  `LastModified=2026-05-17T09:03:29+00:00`, and
  `nbatools-md5=f9cc9a60c8f659651723a55640966d73`.
- Deployment smoke:
  `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`;
  `ok: true`, `case_count: 7`, `failure_count: 0`, and
  `query_celtics_record_against_east_current` returned `team_record` / `ok`
  with `opponent_conference=East` and 15 resolved opponents.
- Opponent-conference preview smoke:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  Celtics vs East, Lakers vs West, Lakers road vs West last season, and Knicks
  vs Eastern Conference teams since January 1 passed; east-coast geography and
  Conference Finals guardrails passed.
- Visual-QA request health:
  latest preview `/visual-qa` loaded 15/15 cases with request errors 0.
- Visual-QA screenshot artifacts:
  canonical local run `visual_qa_20_case_baseline` captured the expanded
  20-case corpus at `desktop_1280` and `mobile_390` with request errors 0,
  overflow false, 20 card screenshots per viewport in the manifest, and 42
  expected PNGs total.
- Query feedback R2 inspection:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  `FEEDBACK_READY_WITH_NOTES`; R2 list/get passed, user-submitted records found,
  automatic diagnostics found, sanitizer/privacy checks passed, and `/review`
  plus `/visual-qa` suppression passed.
- Query feedback review/export workflow:
  `docs/operations/query_feedback_review.md`;
  implemented with notes; launch review can run `make query-feedback-export`.
- Final public UI release review:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  `PUBLIC_UI_READY_WITH_NOTES`; routes `/`, `/?debug=1`, `/review`, and
  `/visual-qa` passed; 14 desktop public queries and 13 mobile 390px family
  checks passed; debug/details and feedback preservation passed; blocking
  issues none.
- Post-review hardening Waves 1–6:
  `docs/operations/parser_routing_growth_guardrails.md`
  through
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  complete with notes.
- AppTheming test drift fix:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  test-only drift fix; full frontend suite passed 25/25 files and 352/352 tests.
- Parser smoke: `make PYTEST=.venv/bin/pytest test-parser` passed, 751 tests.
- Query smoke: `make PYTEST=.venv/bin/pytest test-query` passed, 752 tests.
- Division boundary cleanup:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  targeted snapshot tests passed 65 tests, `make PYTEST=.venv/bin/pytest
  test-parser` passed 776 tests, `make PYTEST=.venv/bin/pytest test-query`
  passed 776 tests, raw QA `natural_query_route_priority` passed 35/35, raw QA
  `product_boundaries` passed 18/18, `make PYTEST=.venv/bin/pytest
  test-preflight` passed 2978 tests with 1 xpassed, and `git diff --check`
  passed.
- Public-query acceptance coverage closure:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  `public_query_acceptance` passed 67/67, `basic_public_availability` passed
  7/7, `natural_query_route_priority` plus `product_boundaries` passed 49/49,
  `make PYTEST=.venv/bin/pytest test-parser` passed 788, final targeted prior
  `test-query` failures passed after false-positive fixes, and
  `git diff --check` passed.
- Static check: `git diff --check` passed.
- Preview validation:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`;
  `PREVIEW_READY_WITH_NOTES`; `/`, `/review`, `/visual-qa`, six smoke queries,
  and five mobile blocker cases passed.

- Tier 1: targeted tests plus targeted/adjacent harness runs, `ruff`, and
  `git diff --check`.
- Tier 2: `make test-parser` when parser, entity, date, or routing recognition
  changes.
- Tier 3: `make test-query` when execution behavior, query-service contracts,
  route outputs, or structured API payload semantics change.
- Tier 4: `make test-preflight`, frontend-copy QA, and visual QA at release or
  major checkpoint boundaries.
- Full raw corpus: required before closing any corpus expansion wave or fix
  wave that changes query behavior, product boundaries, or expectations.
- Frontend changes: require the relevant frontend tests and `cd frontend &&
  npm run build` so FastAPI-served assets stay current.

## 10. Recommended next options

Completed:

- Option G - Release candidate handoff.
- Query feedback readiness refresh after R2 record inspection.
- Option H - Query feedback export/review script.
- Final Public UI Release Review - `PUBLIC_UI_READY_WITH_NOTES`.
- Raw Product Post-Review Hardening Waves 1–6.
- AppTheming test drift fix; full frontend suite clean at 352/352.
- Public Query Acceptance Coverage Waves 1 and 2A–2D; public phrasing gate
  clean at 67/67.

Recommended order:

1. Proceed with launch/handoff using the current `*_WITH_NOTES` statuses.
2. First launch feedback review using `make query-feedback-export`.
3. Option E - Visual QA screenshot diffing/baseline/CI decision, after launch
   or when non-diffing artifact capture is not enough for the highest-risk gap.
4. Option B - Promote one unsupported family into real support, but only
   through the Wave 1 feature-promotion and Wave 2 Data/R2 guardrails.
5. Option F - Broader release/CI artifact packaging if reproducible release
   bundles become more valuable than the current manual evidence set.
6. Option A - Frontend-copy Wave 3 only after fresh gap analysis.
7. Option D - Harness tag/category filters if iteration cost returns as a
   workflow bottleneck.
8. Keep acceptance-family coverage mandatory for every newly advertised
   feature family; reopen fuzzy player typo correction only through an explicit
   V2 product policy.

### Option A - Frontend-copy Wave 3 gap analysis

- Why: backend QA has a clean latest full release run and targeted
  division-boundary slice evidence, while frontend-copy QA still covers a
  selected 125-case rendered subset.
- Scope: expand only if a follow-up gap analysis identifies remaining
  high-risk route/shape families not represented in the 125-case set.
- When to choose: choose this when the next risk is user-facing interpretation
  and copy quality rather than backend route correctness.

### Option B - Promote one unsupported family into real support

- Candidates:
  - historical opponent-conference expansion beyond trusted current-era seasons
  - rookie leaderboards
  - single-team advanced-stat scalar summaries
  - personal-foul leaderboards
  - bench/starter role leaderboards
- Recommended first candidate: choose between historical opponent-conference
  expansion and another unsupported-family preflight, depending on whether the
  next priority is broader team-record filtering or a new query family.
- Required contract work: document dataset source/coverage, route semantics,
  structured result shape, metadata/applied-filter keys, frontend rendering
  needs, no-match behavior, and migration from `expected_unsupported` corpus
  expectations to supported assertions.

### Option C - Release-readiness checklist

- Status: completed for this boundary and summarized by
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`.
- Reuse this checklist before a future deployment or after any supported
  boundary expands.

### Option D - Harness tag/category filters

- Wave tags for targeted corpus selection.
- Harness slices by family/category/manual-review tag.
- Run-new-cases-only mode for corpus expansion waves.
- Saved adjacent case groups for fix waves.
- Validation command presets that line up with the tiered strategy above.
- When to choose: choose this when iteration cost starts slowing future corpus
  or fix waves.

### Option E - Visual QA screenshot follow-up

- Current status: Playwright-backed non-diffing artifact capture is implemented
  and locally validated for the 20-case corpus.
- Decide whether to add screenshot diffing, committed PNG baselines, or a CI
  gate.
- If diffing or layout assertions become justified, start with the five mobile
  blocker cases and no-result boundary cards before broadening automated visual
  scope.

### Option F - Broader release/CI artifact packaging

- Package raw QA reports, frontend-copy reports, preview manual QA evidence, and
  visual QA evidence into repeatable release artifacts.
- Use this when release readiness needs to be reproducible outside manual return
  packages.

### Option G - Release candidate handoff

- Current status: complete with notes; see
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`.
- Release status: `RELEASE_CANDIDATE_WITH_NOTES` with preview status
  `PREVIEW_READY_WITH_NOTES` and query feedback status
  `FEEDBACK_READY_WITH_NOTES`.
- Why: the previous R2 preview blocker is resolved, deployment smoke includes
  the R2-sensitive opponent-conference membership-data check, the latest
  preview `/visual-qa` request-health check is clean, and query feedback R2
  record inspection passed with notes. Post-review hardening Waves 1–6 are
  complete, and the AppTheming test drift fix restored a clean full frontend
  suite.
- Remaining handoff notes: selected frontend-copy coverage, manually reviewed
  visual QA with local non-diffing artifacts,
  opponent-conference support limited to trusted seasons `2024-25` and
  `2025-26`, unsupported divisions/geography/historical coverage, screenshot
  diffing/baseline/CI decisions after local artifact capture, visual QA corpus
  coverage follow-up, `natural_query.py` extraction, return-package archive
  sweep, branding/name change, and remaining feedback operational notes.

### Option H - Query feedback export/review script

- Status: implemented with notes.
- Launch review command: `make query-feedback-export`.
- Script: `tools/export_query_feedback.py`.
- Outputs: `feedback_review.md`, `feedback_records.csv`,
  `feedback_records.jsonl`, `summary.json`, and
  `triage_decisions_template.csv`.
- Remaining notes: heuristic suggestions only, manual corpus conversion, and no
  automatic parser/QA/GitHub issue mutation from review decisions.
