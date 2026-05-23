# Visual QA Screenshot Automation Preflight Return Package

## Status

- Mode: preflight only.
- Preflight date: 2026-05-22.
- Production code changed: no.
- Frontend rendering changed: no.
- Backend/parser/result contracts changed: no.
- QA corpus changed: no.
- Screenshot automation added: no.

## What was created

- `docs/planning/raw-product/VISUAL_QA_SCREENSHOT_AUTOMATION_PREFLIGHT.md`
- `return_packages/raw-product/VISUAL_QA_SCREENSHOT_AUTOMATION_PREFLIGHT_RETURN_PACKAGE.md`
- `docs/index.md` entry for the new planning doc

## Recommendation

The first automation wave should add a repo-owned Node capture command using
Playwright as the headless browser driver against the existing production-like
local FastAPI `/visual-qa` shell.

It should generate artifacts only. Do not start with screenshot diffs,
committed PNG baselines, or a PR CI gate.

Why:

- The expanded 20-case manual baseline passed at desktop and mobile on
  2026-05-22, so there is now a reviewed surface worth repeating.
- `/visual-qa` already owns live `/query` loading, public result rendering,
  stable `data-visual-case-id` card selectors, and the approved case metadata.
- The existing browser ZIP helper is useful for manual current-viewport
  screenshots, but it is not a repeatable run command with output manifests,
  page metrics, fixed viewport control, or full-page screenshots.
- The repo does not currently have direct Playwright tooling or CI browser
  orchestration, so artifact capture is a tighter first step than snapshot
  tests or full diffing.

## Investigation Findings

| Area | Finding |
| --- | --- |
| Visual QA page | `frontend/src/VisualQaPage.tsx` loads all 20 live cases with a concurrency limit of 3 and renders stable case cards at `data-visual-case-id="<case_id>"`. |
| Corpus | `qa/frontend_visual_qa_corpus.json` is the runtime source consumed by `frontend/src/visualQaCases.ts`; the YAML companion carries the same case shape. |
| Existing screenshots | `/visual-qa` and `/review` reuse `frontend/src/lib/reviewScreenshots.ts` for browser-side `html-to-image` PNG ZIP downloads. |
| Browser harness | No repo-owned Playwright, Cypress, CDP, or headless screenshot capture command was found under current frontend/tools/tests/Makefile/CI paths. |
| Dependencies | `frontend/package.json` has `html-to-image` and `jszip`, not a direct Playwright dependency. `frontend/package-lock.json` only mentions optional Vitest browser Playwright metadata. |
| CI | `.github/workflows/ci.yml` currently runs Python lint and pytest targets. It does not install Node, build the frontend, install browsers, start the API shell, or upload visual artifacts. |
| Artifact policy | `.gitignore` ignores `outputs/`, so screenshot runs can be generated locally without committing PNGs or run manifests. |
| Manual evidence | `EXPANDED_VISUAL_QA_MANUAL_BASELINE_RETURN_PACKAGE.md` records 20/20 desktop and 20/20 mobile passes, request errors 0, and no measured document-level horizontal overflow. |

## Capture Scope Decision

| Question | Decision |
| --- | --- |
| Full-page screenshots | Capture one per viewport. |
| Per-card screenshots | Capture all case cards; these are the primary evidence. |
| Desktop viewport | Capture `1280x900` as `desktop_1280`. |
| Mobile viewport | Capture `390x844` as `mobile_390`. |
| All 20 cases | Yes for the canonical first run. |
| Expansion-only five-case subset | Do not make it a separate canonical suite. An optional case filter is acceptable for local reruns. |

## Artifact Contract

Use:

```text
outputs/visual_qa_screenshots/<run_id>/
```

First-wave artifact tree:

```text
outputs/visual_qa_screenshots/<run_id>/
  manifest.json
  desktop_1280/
    metrics.json
    page.png
    cards/<case_id>.png
  mobile_390/
    metrics.json
    page.png
    cards/<case_id>.png
```

The first canonical run should produce 42 PNG files: 40 card captures and 2
page captures.

## Command Surface Recommendation

- Node tool:
  `frontend/tools/captureVisualQaScreenshots.mjs`
- Frontend script:
  `npm --prefix frontend run qa:visual-screenshots -- --base-url http://127.0.0.1:8000 --run-id <run_id>`
- Top-level alias:
  `make visual-qa-screenshots VISUAL_QA_BASE_URL=http://127.0.0.1:8000 VISUAL_QA_RUN_ID=<run_id>`

The Makefile target should delegate to the npm script. The script should accept
explicit base URL, run ID, output root, and optional repeated case filters. The
canonical default should capture both accepted viewports and all rendered case
cards.

## First Executable Wave

In scope:

1. Add explicit Playwright-backed Node capture tooling under `frontend/`.
2. Add the npm script and thin Makefile target above.
3. Capture page and card PNGs, `manifest.json`, and per-viewport metrics.
4. Fail capture for incomplete case loading, request errors, missing or
   duplicate case IDs, count drift from the 20-case baseline, or measured
   document-level horizontal overflow.
5. Document local prerequisites: build the frontend, start the local
   production API shell, then run the screenshot command.

Out of scope:

- screenshot diffs and snapshot thresholds
- committed PNG baselines
- CI workflow changes
- Visual QA corpus edits
- frontend result/page rendering changes
- backend/parser/result-contract changes

## Validation

| Check | Result |
| --- | --- |
| `git diff --check` | passed |
| Markdown lint | not run; no repo-local Markdown lint target was found in the inspected scripts, and `markdownlint` plus `markdownlint-cli2` were not on PATH |

## Files Reviewed

- `docs/planning/raw-product/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md`
- `qa/frontend_visual_qa_corpus.json`
- `qa/frontend_visual_qa_corpus.yaml`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `frontend/package.json`
- `Makefile`
- `docs/operations/ui_guide.md`
- `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- `return_packages/raw-product/VISUAL_QA_CORPUS_EXPANSION_RETURN_PACKAGE.md`
- `return_packages/raw-product/EXPANDED_VISUAL_QA_MANUAL_BASELINE_RETURN_PACKAGE.md`
- `frontend/src/visualQaCases.ts`
- `frontend/src/main.tsx`
- `frontend/src/lib/reviewScreenshots.ts`
- `frontend/src/test/reviewScreenshots.test.ts`
- `frontend/src/ReviewPage.tsx`
- `frontend/package-lock.json`
- `.gitignore`
- `.github/workflows/ci.yml`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `return_packages/raw-product/FRONTEND_SCREENSHOT_VISUAL_QA_PREFLIGHT_RETURN_PACKAGE.md`
