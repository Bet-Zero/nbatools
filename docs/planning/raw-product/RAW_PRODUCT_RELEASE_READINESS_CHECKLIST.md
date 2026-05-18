# Raw Product Release Readiness Checklist

## 1. Overall status

- Checklist status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Checklist date: 2026-05-17.
- Latest feedback readiness refresh: 2026-05-18.
- Query feedback status: `FEEDBACK_READY_WITH_NOTES`.
- Scope: current supported and explicitly unsupported Raw Product QA boundary.
- Release package:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`.
- Release-candidate handoff:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`;
  handoff complete with notes.
- Production query behavior changed: yes; current-era opponent-conference
  `team_record` filters now execute for trusted seasons `2024-25` and `2025-26`.
- Frontend rendering changed: no in the frontend-copy expansion wave; previous
  `/visual-qa` mobile wrapper/layout-only fix remains the latest production
  rendering change.
- Corpus expectations changed: yes; opponent-conference backend and
  frontend-copy cases were migrated from unsupported to supported expectations.
- New frontend-copy corpus cases added: yes, selected rendered-copy coverage
  expanded from 59 to 125 cases across Wave 1 and Wave 2.
- Release posture: release-candidate ready with notes; the latest preview manual
  QA rerun passed `/`, `/review`, `/visual-qa`, the six-query smoke set, and the
  five mobile blocker rechecks. The later opponent-conference preview R2
  blocker is also resolved: R2 now contains
  `raw/teams/team_conference_membership.csv`, supported opponent-conference
  preview smoke passed, deployment smoke includes the membership-data check,
  and `/visual-qa` loaded 15/15 cases with request errors 0. Query Feedback +
  Diagnostic Logging V1 is also included in the release candidate and is no
  longer a preview blocker after R2 record inspection verified user-submitted
  records, automatic diagnostics, sanitization/privacy, and `/review` plus
  `/visual-qa` suppression.
- Latest refresh type: docs/release packaging only; no production code, parser,
  frontend rendering, test, or corpus changes.

Known limitations:

- Frontend-copy QA covers a selected 125-case corpus from the latest clean
  246-case backend run, not all 246 backend cases.
- Frontend-copy QA is DOM-copy QA, not visual layout or screenshot QA.
- Visual QA is a manual 15-case baseline, not Playwright or screenshot diffing.
- Deployed preview validation on 2026-05-16 found a mobile `/visual-qa`
  horizontal-overflow blocker. The local wrapper fix was validated and the
  latest preview manual rerun is `PREVIEW_READY_WITH_NOTES`.
- Deployed preview validation later found an opponent-conference `no_data`
  blocker caused by missing R2 membership data. The R2 sync fix resolved this;
  future missing required R2 files remain deploy blockers.
- Unsupported product families are guarded and documented; opponent-conference
  team-record filters are now supported only inside the trusted current-era
  conference coverage boundary.
- Query feedback is `FEEDBACK_READY_WITH_NOTES`; remaining feedback limitations
  are operational follow-ups: no admin/export workflow, no full dedupe/rate
  limiting beyond hash, dedicated feedback bucket unavailable so preview uses
  isolated prefix `query_feedback/preview`, and frontend network/non-JSON
  failure logging was not live-tested.

## 2. Backend Raw QA

| Item | Status |
|---|---|
| Corpus | `qa/raw_query_answer_corpus.yaml` |
| Case count | 246 |
| Latest checkpoint run | `outputs/raw_query_answer_qa/20260517T070422Z/report.md` |
| Latest release-package run | `outputs/raw_query_answer_qa/20260517T070422Z/report.md` |
| Result statuses | `ok: 206`, `no_result: 31`, `error: 9` |
| Expectation cases | `pass: 246` |
| Expectation checks | `pass: 1421` |
| Failed case IDs | none |
| Suspicious flags | 0 |
| Informational flags | `frontend_hero_expected: 153` |
| Verified outlier | `top_performance_high_points: 1` |

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the full current corpus passed with no failed IDs and no suspicious
flags. The nine `error` statuses are expected corpus outcomes, not failed
expectations.

## 3. Frontend-Copy QA

| Item | Status |
|---|---|
| Corpus | `qa/frontend_copy_corpus.yaml` |
| Selected case count | 125 |
| Configured source backend run | `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl` |
| Latest checkpoint run | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md` |
| Latest checklist run | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md` |
| Rendered successfully | 125 |
| Render failures | 0 |
| Missing backend records | 0 |
| Soft checks | `pass: 480`, `fail: 0`, `not_checked: 0` |
| Gating | `qa:frontend-copy` fails on render failures, missing backend records, soft-check failures, or unchecked soft checks |

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the selected rendered-copy corpus is clean and now sources the
latest clean 246-case backend run. Wave 2 added streak tables, rolling
stretches, finder/count outputs, game-summary logs, team splits,
record-by-decade shapes, top-performance variants, and on/off plus lineup
unsupported no-result boundaries. The refreshed source run also covers the
promoted opponent-conference record cases as supported rendered-copy examples.
The remaining limitation is coverage breadth: this is selected DOM-copy
coverage, not full 246-case rendered-copy or visual layout coverage.

## 4. Visual QA

| Item | Status |
|---|---|
| Corpus | `qa/frontend_visual_qa_corpus.yaml` |
| Baseline size | 15 cases |
| Manual checklist | `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` |
| Preview rerun | `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md` |
| Desktop baseline | completed for the approved 15-case set |
| Mobile baseline | completed for the approved 15-case set |
| Fixed finding | mobile dense table clipping for top performance, comparison, and playoff matchup tables |
| Fixed finding | filtered leaderboard hero context for guard and center examples |
| Fixed finding | preview mobile `/visual-qa` wrapper/card overflow clipped result content at ~390px; local production shell now measures `pageWidth 390` at a 390px viewport and the latest preview rerun passed the five mobile blocker cases |
| Latest preview `/visual-qa` request health | `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`; loaded 15/15 cases with request errors 0 |
| Accepted baseline | no-result card baseline |
| Automation limitation | no Playwright or screenshot diffing in this wave |

Release verdict: `READY_WITH_MANUAL_LIMITATION`.

Rationale: the deployed preview found a mobile wrapper overflow defect after the
manual baseline. The local production route was fixed and the latest preview
manual rerun rechecked the five mobile blocker cases successfully. The remaining
limitation is that visual QA is manual, not screenshot-diff automation.

## 5. Deploy / Preview Readiness

| Item | Status |
|---|---|
| `/review` route | local API and Vercel rewrite path preserved |
| `/visual-qa` route | implemented locally and in Vercel rewrite config |
| Vercel rewrite | `/visual-qa` rewrites to `/api/review` |
| Local production API parity | validated in the deploy-parity wave |
| Preview validation | `PREVIEW_READY_WITH_NOTES`; `/`, `/review`, `/visual-qa`, six smoke queries, and five mobile blocker rechecks passed |
| R2 opponent-conference data | `raw/teams/team_conference_membership.csv` exists in R2; `head_object` passed with `ContentLength=4999` and `LastModified=2026-05-17T09:03:29+00:00` |
| Latest deployment smoke | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `case_count: 7`, `failure_count: 0`, and opponent-conference membership-data case passed |
| Latest opponent-conference preview smoke | `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`; four supported checks passed, two guardrails passed, `/visual-qa` request errors 0 |
| Query feedback and diagnostic logging | `FEEDBACK_READY_WITH_NOTES`; `return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`; user-submitted R2 records, automatic diagnostics, sanitization/privacy, and `/review` plus `/visual-qa` suppression verified under `query_feedback/preview` |

Release verdict: `PREVIEW_READY_WITH_NOTES`.

Rationale: route parity remains implemented. The mobile preview blocker was
fixed, and the later R2 data blocker for opponent-conference support was
resolved by syncing the required membership CSV. The latest deployed preview
checks passed the route, smoke, deployment-smoke, `/visual-qa`, and
opponent-conference data-path checks with non-blocking notes. Query feedback is
ready with notes and is not a preview blocker.

## 6. Unsupported Boundaries

These boundaries are expected unsupported behavior for the current product
surface. They must return clear no-result or unsupported-filter responses
instead of broad plausible answers.

- Personal-foul leaderboards.
- Single-team advanced-stat scalar summaries.
- Rookie leaderboards.
- League-wide starter/bench role leaderboards.
- Team bench scoring summaries.
- Opponent-conference seasons outside trusted coverage, geography phrases such
  as `east coast teams`, and division requests.
- Single-team playoff round records, including Conference Finals phrasing as
  playoff-round phrasing rather than opponent-conference filtering.
- Subjective/trend queries such as clutch, cooled off, best defender, MVP
  candidate, and best player lately.
- Multi-player availability, on/off, and lineup membership.
- Team rolling-stretch leaderboards.
- Minutes leaderboards.
- Team single-game threes.

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the latest raw QA run keeps these families guarded through explicit
expected unsupported outcomes. Broad fake answers are not allowed for these
surfaces.

## 7. Data-Quality / Outlier Policy

| Item | Status |
|---|---|
| Verified outlier config | `qa/verified_outliers.yaml` |
| Current verified outlier | `bam_adebayo_83_points_2026_03_10` |
| Outlier category | `top_performance_high_points` |
| Latest suspicious flags | 0 |
| New unverified high-point rows | should trigger suspicious data-quality review |

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the known high-point outlier is allowlisted and remains displayed as
source data. New high-point rows remain reviewable through the suspicious-flag
path.

## 8. Docs / User Expectation Alignment

| Item | Status |
|---|---|
| Query catalog | updated for current supported and unsupported boundaries |
| Query guide | updated for current supported and unsupported boundaries |
| Release-candidate handoff | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`; handoff complete with notes |
| Release checkpoint | `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` |
| Findings inventory | `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` |
| Harness plan | `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` |
| Query feedback review runbook | `docs/operations/query_feedback_review.md`; updated for verified preview prefix/status |

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the public-facing query docs describe the current supported examples
and explicitly unsupported boundaries. This checklist does not broaden product
claims.

## 9. Validation Results

### Backend raw QA full corpus

Command:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
```

Result:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260517T070422Z
Cases: 246
Result statuses: {'error': 9, 'no_result': 31, 'ok': 206}
Expectation cases: {'pass': 246}
Suspicious flag cases: 0
Informational flag cases: 153
Verified outlier cases: 1
Failed case IDs: none
```

### Frontend-copy QA

Command:

```bash
cd frontend && npm run qa:frontend-copy
```

Result:

```text
Test Files  1 passed (1)
Tests  4 passed (4)
Duration  7.68s
```

Report summary:

```text
Run ID: 20260517T071053Z
Selected cases: 125
Rendered successfully: 125
Render failures: 0
Missing backend records: 0
Soft check pass/fail/not checked: 480/0/0
```

Gating behavior: `qa:frontend-copy` now asserts 125 selected cases, 125
rendered successes, 0 render failures, 0 missing backend records, 0 soft-check
failures, and 0 unchecked soft checks.

### Frontend build

Command:

```bash
cd frontend && npm run build
```

Result:

```text
136 modules transformed.
index.html 0.77 kB
assets/index-C-OtNn3G.css 72.22 kB
assets/index-DhFSwvX9.js 543.51 kB
built in 806ms
```

Note: Vite emitted the existing large-chunk warning for the 543.51 kB JS
bundle.

### Frontend lint

Command:

```bash
cd frontend && npm run lint
```

Result:

```text
0 errors, 1 warning
frontend/src/ReviewPage.tsx react-hooks/exhaustive-deps warning at 159:27
```

The warning is pre-existing and was also recorded in the deploy-parity wave.

### Preview mobile `/visual-qa` overflow fix and rerun

Preview blocker:

```text
2026-05-16 preview manual QA found mobile /visual-qa result cards overflowing
horizontally at ~390px, clipping primary result content for:
biggest_scoring_games, lebron_durant_comparison_wave4,
heat_knicks_playoff_series_record_wave4, guards_fg_percentage_leaders, and
centers_rebound_leaders_wave4.
```

Local fix:

```text
Changed only the /visual-qa wrapper/container CSS so QA page grids, cards,
metadata, checklist text, and result columns shrink within the mobile viewport.
No backend/query behavior or corpus expectations changed.
```

Local production-shell validation:

```text
Before fix at mobile width: viewportWidth 375, pageWidth 632, case cards ~528px.
After fix at 390px: viewportWidth 390, pageWidth 390, bodyWidth 390,
blocker case cards 378px.
Required result text present:
- biggest_scoring_games: 83 and PTS
- lebron_durant_comparison_wave4: Edge / Difference
- heat_knicks_playoff_series_record_wave4: Series Result
- guards_fg_percentage_leaders: guards and FG%
- centers_rebound_leaders_wave4: centers and RPG
Desktop spot-check at 1280px: pageWidth 1280 for biggest_scoring_games and
lebron_durant_comparison_wave4; required result text remained present.
```

Preview status:

```text
PREVIEW_READY_WITH_NOTES.
Latest rerun: return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md.
Routes checked: /, /review, /visual-qa.
Smoke queries checked: 6.
Mobile blocker cases rechecked: 5.
Blocking issues: none.
```

### Team conference data validation

Command:

```bash
.venv/bin/pytest tests/test_team_conference_membership_data.py -q
```

Result:

```text
15 passed
```

### Parser smoke

Command:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result:

```text
751 passed
```

### Query smoke

Command:

```bash
make PYTEST=.venv/bin/pytest test-query
```

Result:

```text
752 passed
```

### Opponent-conference R2 sync and preview smoke

R2 sync evidence:

```text
.venv/bin/nbatools-cli pipeline sync-r2 --dry-run
[661/663] would-upload raw/teams/team_conference_membership.csv (4999 bytes)

.venv/bin/nbatools-cli pipeline sync-r2
[661/663] upload raw/teams/team_conference_membership.csv (4999 bytes)

head_object raw/teams/team_conference_membership.csv
ContentLength=4999
LastModified=2026-05-17T09:03:29+00:00
nbatools-md5=f9cc9a60c8f659651723a55640966d73
```

Latest preview smoke:

```text
Preview URL: https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app
Celtics record against the East this season: ok, 52 games, 36-16
Lakers record against the West: ok, 52 games, 33-19
Lakers road record against West last season: ok, 26 games, 14-12
Knicks record against Eastern Conference teams since January 1: ok, 26 games, 17-9
Celtics record against east coast teams: unsupported/no-result guardrail pass
Celtics conference finals record: playoff-round guardrail pass
/visual-qa: loaded 15/15, request errors 0
```

Deployment smoke:

```text
outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json
ok: true
case_count: 7
failure_count: 0
query_celtics_record_against_east_current: team_record / ok
opponent_conference: East
opponent_team_abbrs_count: 15
```

### Query feedback R2 inspection

Evidence:

```text
return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md
Feedback readiness status: FEEDBACK_READY_WITH_NOTES
R2 bucket/prefix: nbatools-data / query_feedback/preview/2026/05/18/
R2 list/get: PASS
Known user-submitted records found: PASS
Automatic diagnostics found: PASS
Sanitization/privacy: PASS
/review and /visual-qa suppression: PASS
Blocking issues: none
```

### Static diff check

Command:

```bash
git diff --check
```

Result:

```text
passed with no output
```

## 10. Preview Manual Validation

Baseline preview rerun status: `PREVIEW_READY_WITH_NOTES`.

Evidence:

- Preview rerun return package:
  `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`
- Preview URL checked:
  `https://nbatools-fuq06rg4y-brents-projects-686e97fc.vercel.app`
- Routes checked: `/`, `/review`, `/visual-qa`
- Smoke queries checked: 6
- Mobile blocker cases checked: 5
- Blocking issues: none

Latest opponent-conference/R2 preview smoke status: `PASS`.

Evidence:

- R2 sync fix return package:
  `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`
- Preview URL checked:
  `https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app`
- Supported opponent-conference checks: 4 passed
- Guardrail checks: 2 passed
- `/visual-qa`: loaded 15/15 cases with request errors 0
- Deployment smoke:
  `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`
  with `ok: true`, `failure_count: 0`, and 15 resolved East opponents for the
  R2-sensitive team-record check

For future previews, validate these routes:

- `https://<preview-url>/`
- `https://<preview-url>/review`
- `https://<preview-url>/visual-qa`

For `/visual-qa`, confirm:

- route does not return 404
- page loads
- 15 cases begin running
- page is not blank gray
- no YAML or JSON parse error appears

For the normal app query path, run this smoke set:

| Query | Expected |
|---|---|
| `Who leads the NBA in points per game this season?` | supported answer |
| `What is Denver's record when Nikola Jokic has a triple-double?` | supported answer |
| `Which team gave up the fewest points per game?` | supported answer |
| `Lakers Celtics playoff matchup history` | supported answer |
| `Warriors net rating this season` | clear unsupported/no-result for single-team advanced-stat scalar summary |
| `players with most personal fouls this season` | clear unsupported/no-result for personal-foul leaderboard |

Preview verdict: `PREVIEW_READY_WITH_NOTES`.

## 11. Final Classification

Final readiness status: `RELEASE_CANDIDATE_WITH_NOTES`.

Backend, frontend-copy, docs, and data-quality findings remain clean for the
current boundary. The previous mobile `/visual-qa` overflow blocker was fixed
and the later opponent-conference preview R2 blocker is resolved. The latest
preview and deployment-smoke evidence passed with notes. Query Feedback +
Diagnostic Logging V1 is `FEEDBACK_READY_WITH_NOTES` and included in the
release candidate. The remaining release notes are selected frontend-copy
coverage, manual visual QA, trusted-season limits for opponent-conference
support, guarded unsupported families, existing frontend build/lint warnings,
and feedback operational follow-ups for export/admin tooling, dedupe/rate
limiting, dedicated bucket provisioning, and frontend network/non-JSON
failure-path live testing. The final release-candidate handoff is complete in
`docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`.
