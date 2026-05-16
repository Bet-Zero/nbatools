# Raw Product Release Readiness Checklist

## 1. Overall status

- Checklist status: `READY_WITH_KNOWN_LIMITATIONS`.
- Checklist date: 2026-05-16.
- Scope: current supported and explicitly unsupported Raw Product QA boundary.
- Production query behavior changed: no.
- Frontend rendering changed: no.
- Corpus expectations changed: no.
- New corpus cases added: no.
- Release posture: ready for preview review after a live preview URL is
  available for the manual route checks below.

Known limitations:

- Frontend-copy QA covers a selected 59-case corpus from its configured source
  backend run, not all 243 backend cases from the latest raw run.
- Visual QA is a manual 15-case baseline, not Playwright or screenshot diffing.
- Deployed preview validation for `/visual-qa` remains pending until a preview
  URL exists.
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
| Selected case count | 59 |
| Configured source backend run | `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl` |
| Latest checkpoint run | `outputs/frontend_copy_qa/20260515T224620Z/frontend_copy_report.md` |
| Latest checklist run | `outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.md` |
| Rendered successfully | 59 |
| Render failures | 0 |
| Missing backend records | 0 |
| Soft checks | `pass: 160`, `fail: 0`, `not_checked: 0` |

Release verdict: `READY_FOR_PREVIEW_REVIEW`.

Rationale: the selected rendered-copy corpus is clean. The limitations are
coverage breadth and source freshness: this is selected frontend-copy coverage
from the configured frontend-copy source run, not full 243-case rendered-copy
coverage from the latest raw run.

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
| Accepted baseline | no-result card baseline |
| Automation limitation | no Playwright or screenshot diffing in this wave |

Release verdict: `READY_WITH_KNOWN_LIMITATIONS`.

Rationale: the manual baseline and targeted rechecks are complete for the
current 15 cases. The remaining limitation is process maturity, not a known
release-blocking visual defect.

## 5. Deploy / Preview Readiness

| Item | Status |
|---|---|
| `/review` route | local API and Vercel rewrite path preserved |
| `/visual-qa` route | implemented locally and in Vercel rewrite config |
| Vercel rewrite | `/visual-qa` rewrites to `/api/review` |
| Local production API parity | validated in the deploy-parity wave |
| Preview validation | pending until a live preview URL exists |

Release verdict: `READY_WITH_KNOWN_LIMITATIONS`.

Rationale: route parity is implemented, and local checks passed in the
deploy-parity wave. The only open item is deployed preview validation on an
actual preview URL.

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
Run ID: 20260516T230102Z
Selected cases: 59
Rendered successfully: 59
Render failures: 0
Missing backend records: 0
Soft check pass/fail/not checked: 160/0/0
```

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

Preview verdict before URL exists: `PENDING`.

Preview verdict once those checks pass: `READY_FOR_PREVIEW_REVIEW`.

## 11. Final Classification

Final readiness status: `READY_WITH_KNOWN_LIMITATIONS`.

Release is not blocked by current backend, frontend-copy, visual baseline, docs,
or data-quality findings. The remaining checklist item is preview manual QA on
a live preview URL.
