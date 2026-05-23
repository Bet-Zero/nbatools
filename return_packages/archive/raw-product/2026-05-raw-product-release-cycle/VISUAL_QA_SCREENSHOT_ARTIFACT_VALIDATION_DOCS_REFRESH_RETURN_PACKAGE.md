# Visual QA Screenshot Artifact Validation Docs Refresh Return Package

## 1. Executive Summary

- Refreshed durable Visual QA and Raw Product release/readiness docs after the
  canonical screenshot artifact capture command passed locally for the expanded
  20-case corpus.
- This refresh is docs-only. It does not change production code, frontend
  rendering, backend behavior, parser/routing behavior, result contracts, QA
  corpus files, screenshot diffing, committed PNG baselines, or CI gates.
- Screenshot artifact capture tooling is now recorded as implemented and locally
  validated.
- The remaining deferred work is explicit: screenshot diffing, committed PNG
  baselines, and CI gating.

## 2. Validation Evidence Recorded

Canonical local run:

```bash
make visual-qa-screenshots \
  VISUAL_QA_BASE_URL=http://127.0.0.1:8000 \
  VISUAL_QA_RUN_ID=visual_qa_20_case_baseline
```

Artifact root:

```text
outputs/visual_qa_screenshots/visual_qa_20_case_baseline/
```

Observed validation:

| Viewport | Cases | Request errors | Status counts | Overflow |
|---|---|---|---|---|
| `desktop_1280` | 20/20 | 0 | `ok: 15`, `no_result: 5`, `error: 0` | document/body `false` |
| `mobile_390` | 20/20 | 0 | `ok: 15`, `no_result: 5`, `error: 0` | document/body `false` |

Artifact summary:

- Manifest lists 20 desktop card screenshots.
- Manifest lists 20 mobile card screenshots.
- Expected PNG total is 42, including the two full-page captures.

## 3. Files Changed

Durable docs:

- `docs/operations/ui_guide.md`
- `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- `docs/planning/raw-product/VISUAL_QA_SCREENSHOT_AUTOMATION_PREFLIGHT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/index.md`

Return package:

- `return_packages/raw-product/VISUAL_QA_SCREENSHOT_ARTIFACT_VALIDATION_DOCS_REFRESH_RETURN_PACKAGE.md`

## 4. Durable Status Refresh

The refreshed docs now distinguish three states:

1. The expanded 20-case Visual QA manual baseline passed locally.
2. The non-diffing screenshot artifact command is implemented and locally
   validated for that 20-case corpus.
3. Screenshot diffing, committed PNG baselines, and CI gating remain deferred.

Release/readiness docs keep Visual QA review status manual because the validated
command captures repeatable artifacts and health metrics; it does not compare
pixels or turn screenshots into a gate.

## 5. Validation For This Docs Refresh

```text
git diff --check
passed with no output

git diff --no-index --check /dev/null \
  return_packages/raw-product/VISUAL_QA_SCREENSHOT_ARTIFACT_VALIDATION_DOCS_REFRESH_RETURN_PACKAGE.md
no whitespace warnings; command exits nonzero because the new file differs
from /dev/null
```

Markdown lint availability check:

- No repo-local Markdown lint target or config was found by the inspected repo
  search.
- `markdownlint`, `markdownlint-cli2`, `mdl`, and `mdformat` were not
  available on `PATH`.

Code tests were not run because this refresh changes docs and a return package
only.
