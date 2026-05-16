# Raw Product Release Readiness Checklist Return Package

## 1. Executive summary

- What changed: created the Raw Product release-readiness checklist, updated the
  checkpoint and harness plan with current validation evidence, and indexed the
  new checklist doc.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.
- Checklist doc:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`.
- Final readiness status: `READY_WITH_KNOWN_LIMITATIONS`.
- Backend Raw QA: fresh 243-case run passed 243/243 expectations with no failed
  case IDs, no suspicious flags, and one verified outlier.
- Frontend-copy QA: fresh selected 59-case run rendered 59/59 from the
  configured frontend-copy source backend run with 0 render failures and 0
  soft-check failures.
- Visual QA: 15-case manual baseline remains accepted; fixed mobile dense table
  and filtered leaderboard hero findings remain the current baseline state.
- Deploy/preview status: `/review` and `/visual-qa` route parity is implemented;
  deployed preview validation is pending until a live preview URL exists.
- Recommended next step: release/preview manual QA on the next live preview URL.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Added | Defines the release-readiness checklist, current verdicts, validation results, and preview manual QA steps for the current Raw Product boundary. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | Updated | Adds the checklist pointer, current checklist status, latest validation run paths, and next preview/manual QA direction. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Updated | Records release-readiness checklist status, validation command results, and next options after the checklist. |
| `docs/index.md` | Updated | Adds the release-readiness checklist to the planning documentation index. |
| `return_packages/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST_RETURN_PACKAGE.md` | Added | Records this validation/checklist wave. |

## 3. Checklist verdict

| Area | Status | Evidence | Notes |
|---|---|---|---|
| Backend Raw QA | `READY_FOR_PREVIEW_REVIEW` | `outputs/raw_query_answer_qa/20260516T230058Z/report.md`; 243 cases; expectations `pass: 243`; failed IDs none; suspicious flags 0 | `error: 9` and `no_result: 32` are expected corpus outcomes. |
| Frontend-copy QA | `READY_FOR_PREVIEW_REVIEW` | `outputs/frontend_copy_qa/20260516T230102Z/frontend_copy_report.md`; 59 selected cases; render failures 0; soft-check failures 0 | Selected coverage from configured source run `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`, not full 243-case rendered-copy coverage. |
| Visual QA | `READY_WITH_KNOWN_LIMITATIONS` | 15-case manual baseline; mobile dense table and filtered leaderboard hero fixes verified locally | Manual baseline only; no Playwright or screenshot diffing in this wave. |
| Deploy/preview | `READY_WITH_KNOWN_LIMITATIONS` | `/review` preserved; `/visual-qa` local/API/Vercel rewrite parity implemented | Preview validation pending until a live URL exists. |
| Unsupported boundaries | `READY_FOR_PREVIEW_REVIEW` | Current raw corpus keeps unsupported-family cases guarded as no-result or unsupported-filter outcomes | No broad fake answers are allowed for guarded boundaries. |
| Data/outliers | `READY_FOR_PREVIEW_REVIEW` | `qa/verified_outliers.yaml`; verified `top_performance_high_points`; suspicious flags 0 | New unverified high-point rows should still trigger suspicious review. |
| Docs/user expectations | `READY_FOR_PREVIEW_REVIEW` | Query catalog and query guide already describe current supported and unsupported boundaries | This wave did not broaden shipped claims. |

## 4. Validation results

### Raw QA full corpus

Command:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
```

Output summary:

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

```text
cd frontend && npm run qa:frontend-copy
```

Output summary:

```text
Test Files  1 passed (1)
Tests  4 passed (4)
Duration  7.68s
```

Report summary:

```text
Run ID: 20260516T230102Z
Source backend run: outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl
Selected cases: 59
Rendered successfully: 59
Render failures: 0
Missing backend records: 0
Soft check pass/fail/not checked: 160/0/0
```

### Frontend build

Command:

```text
cd frontend && npm run build
```

Output summary:

```text
136 modules transformed.
../src/nbatools/ui/dist/index.html 0.77 kB
../src/nbatools/ui/dist/assets/index-C-OtNn3G.css 72.22 kB
../src/nbatools/ui/dist/assets/index-DhFSwvX9.js 543.51 kB
built in 806ms
```

Note: Vite emitted the existing large-chunk warning for the JS bundle.

### Frontend lint

Command:

```text
cd frontend && npm run lint
```

Output summary:

```text
0 errors, 1 warning
frontend/src/ReviewPage.tsx 159:27 react-hooks/exhaustive-deps
```

The warning is pre-existing.

### Parser smoke

Command:

```text
make PYTEST=.venv/bin/pytest test-parser
```

Output summary:

```text
747 passed in 142.20s (0:02:22)
```

### Git diff check

Command:

```text
git diff --check
```

Output summary:

```text
passed with no output
```

### Preview validation

Not run. No live preview URL was available in this execution wave.

When a preview URL exists, validate:

- `https://<preview-url>/`
- `https://<preview-url>/review`
- `https://<preview-url>/visual-qa`

For `/visual-qa`, confirm no 404, the page loads, all 15 cases begin running,
the page is not blank gray, and no YAML/JSON parse error appears.

## 5. Known limitations

- Frontend-copy corpus is selected coverage from its configured source backend
  run, not all 243 cases from the latest raw run.
- Visual QA is manual, not automated through Playwright or screenshot diffing.
- Preview validation is pending until a live preview URL exists.
- Unsupported product families are guarded and documented, but not supported.

## 6. Next recommendation

Recommended next step: release/preview manual QA.

Run the checklist's preview route checks and six-query smoke set against the
next live preview URL before treating the current boundary as preview-reviewed.
