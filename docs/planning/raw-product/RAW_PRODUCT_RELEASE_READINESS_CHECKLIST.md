# Raw Product Release Readiness Checklist

## 1. Overall status

- Checklist status: `PREVIEW_BLOCKER_FIXED_PENDING_REDEPLOY`.
- Checklist date: 2026-05-17.
- Scope: current supported and explicitly unsupported Raw Product QA boundary.
- Production query behavior changed: no.
- Frontend rendering changed: no in the frontend-copy expansion wave; previous
  `/visual-qa` mobile wrapper/layout-only fix remains the latest production
  rendering change.
- Corpus expectations changed: no.
- New frontend-copy corpus cases added: yes, selected rendered-copy coverage
  expanded from 59 to 125 cases across Wave 1 and Wave 2.
- Release posture: local fix is ready for redeploy; preview manual QA must be
  rerun against the next preview before this boundary is marked preview-ready.

Known limitations:

- Frontend-copy QA covers a selected 125-case corpus from the latest clean
  243-case backend run, not all 243 backend cases.
- Frontend-copy QA is DOM-copy QA, not visual layout or screenshot QA.
- Visual QA is a manual 15-case baseline, not Playwright or screenshot diffing.
- Deployed preview validation on 2026-05-16 found a mobile `/visual-qa`
  horizontal-overflow blocker. The local wrapper fix is validated; preview
  rerun remains required after redeploy.
- Unsupported product families are guarded and documented, but not promoted
  into execution-backed support.

## 2. Backend Raw QA

| Item | Status |
|---|---|
| Corpus | `qa/raw_query_answer_corpus.yaml` |
| Case count | 243 |
| Latest checkpoint run | `outputs/raw_query_answer_qa/20260516T221654Z/report.md` |
| Latest checklist run | `outputs/raw_query_answer_qa/20260516T230058Z/report.md` |
| Result statuses | `ok: 202`, `no_result: 32`, `error: 9` |
| Expectation cases | `pass: 243` |
| Expectation checks | `pass: 1368` |
| Failed case IDs | none |
| Suspicious flags | 0 |
| Informational flags | `frontend_hero_expected: 149` |
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
| Configured source backend run | `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl` |
| Latest checkpoint run | `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md` |
| Latest checklist run | `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md` |
| Rendered successfully | 125 |
| Render failures | 0 |
| Missing backend records | 0 |
| Soft checks | `pass: 475`, `fail: 0`, `not_checked: 0` |
| Gating | `qa:frontend-copy` fails on render failures, missing backend records, soft-check failures, or unchecked soft checks |

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the selected rendered-copy corpus is clean and now sources the
latest clean 243-case backend run. Wave 2 added streak tables, rolling
stretches, finder/count outputs, game-summary logs, team splits,
record-by-decade shapes, top-performance variants, and on/off plus lineup
unsupported no-result boundaries. The remaining limitation is coverage breadth:
this is selected DOM-copy coverage, not full 243-case rendered-copy or visual
layout coverage.

## 4. Visual QA

| Item | Status |
|---|---|
| Corpus | `qa/frontend_visual_qa_corpus.yaml` |
| Baseline size | 15 cases |
| Manual checklist | `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` |
| Desktop baseline | completed for the approved 15-case set |
| Mobile baseline | completed for the approved 15-case set |
| Fixed finding | mobile dense table clipping for top performance, comparison, and playoff matchup tables |
| Fixed finding | filtered leaderboard hero context for guard and center examples |
| Fixed finding | preview mobile `/visual-qa` wrapper/card overflow clipped result content at ~390px; local production shell now measures `pageWidth 390` at a 390px viewport |
| Accepted baseline | no-result card baseline |
| Automation limitation | no Playwright or screenshot diffing in this wave |

Release verdict: `PREVIEW_RERUN_REQUIRED`.

Rationale: the deployed preview found a mobile wrapper overflow defect after the
manual baseline. The local production route has been fixed and rechecked at
390px and 1280px, but the deployed preview must be rerun after redeploy.

## 5. Deploy / Preview Readiness

| Item | Status |
|---|---|
| `/review` route | local API and Vercel rewrite path preserved |
| `/visual-qa` route | implemented locally and in Vercel rewrite config |
| Vercel rewrite | `/visual-qa` rewrites to `/api/review` |
| Local production API parity | validated in the deploy-parity wave |
| Preview validation | blocked on 2026-05-16 preview by mobile `/visual-qa` overflow; local fix validated and redeploy/rerun required |

Release verdict: `PREVIEW_RERUN_REQUIRED`.

Rationale: route parity remains implemented. The preview blocker has a local
frontend-only fix, but the deployed preview result is still blocked until the
next preview validates `/visual-qa` at mobile width.

## 6. Unsupported Boundaries

These boundaries are expected unsupported behavior for the current product
surface. They must return clear no-result or unsupported-filter responses
instead of broad plausible answers.

- Personal-foul leaderboards.
- Single-team advanced-stat scalar summaries.
- Rookie leaderboards.
- League-wide starter/bench role leaderboards.
- Team bench scoring summaries.
- Opponent-conference filters.
- Single-team playoff round records.
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
| Release checkpoint | `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` |
| Findings inventory | `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` |
| Harness plan | `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` |

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
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T230058Z
Cases: 243
Result statuses: {'error': 9, 'no_result': 32, 'ok': 202}
Expectation cases: {'pass': 243}
Suspicious flag cases: 0
Informational flag cases: 149
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
Run ID: 20260517T054758Z
Selected cases: 125
Rendered successfully: 125
Render failures: 0
Missing backend records: 0
Soft check pass/fail/not checked: 475/0/0
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

### Preview mobile `/visual-qa` overflow fix

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
Preview rerun required after redeploy.
```

### Parser smoke

Command:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result:

```text
747 passed in 142.20s (0:02:22)
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

When a deployed preview URL exists, validate these routes:

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

Preview verdict before redeploy/rerun: `BLOCKED_PENDING_REDEPLOY`.

Preview verdict once those checks pass: `READY_FOR_PREVIEW_REVIEW`.

## 11. Final Classification

Final readiness status: `PREVIEW_BLOCKER_FIXED_PENDING_REDEPLOY`.

Backend, frontend-copy, docs, and data-quality findings remain clean for the
current boundary. The previous preview is blocked by the mobile `/visual-qa`
overflow finding; the frontend-only local fix is validated and must be redeployed
before rerunning preview manual QA.
