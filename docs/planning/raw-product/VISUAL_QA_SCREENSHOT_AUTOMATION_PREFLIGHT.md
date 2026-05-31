# Visual QA Screenshot Automation Preflight

## 1. Purpose

This preflight records the first screenshot automation decision for the expanded
20-case Visual QA corpus. The preflight itself was documentation-only: it did
not change production code, frontend rendering, backend behavior,
parser/routing behavior, result contracts, QA corpus files, or screenshot
automation code. The first executable non-diffing artifact wave described below
is now implemented and locally validated.

The automation decision point is now valid:

- `working/raw-product-post-launch/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
  ranks screenshot automation after Visual QA corpus expansion.
- The runtime corpus is now 20 cases.
- The expanded manual baseline passed on 2026-05-22:
  - desktop: 20/20 cases at `1280px`
  - mobile: 20/20 cases at `390px`
  - request errors: 0
  - document-level horizontal overflow: none measured
  - status: `PASS_WITH_MANUAL_LIMITATION`

The selected investment makes screenshot evidence repeatable without
prematurely turning live visual output into a brittle pixel-diff gate.

## 2. Evidence Reviewed

Primary requested sources:

- `working/raw-product-post-launch/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md`
- `qa/frontend_visual_qa_corpus.json`
- `qa/frontend_visual_qa_corpus.yaml`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `frontend/package.json`
- `Makefile`
- `docs/operations/ui_guide.md`
- `docs/operations/frontend_visual_qa.md`
- `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`

Supporting implementation and tooling sources:

- `frontend/src/visualQaCases.ts`
- `frontend/src/main.tsx`
- `frontend/src/lib/reviewScreenshots.ts`
- `frontend/src/test/reviewScreenshots.test.ts`
- `frontend/src/ReviewPage.tsx`
- `frontend/package-lock.json`
- `.gitignore`
- `.github/workflows/ci.yml`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/operations/frontend_visual_qa.md`

## 3. Current Visual QA Target

### 3.1 Corpus shape

The visual corpus has one runtime JSON source and one YAML companion. The typed
frontend adapter in `frontend/src/visualQaCases.ts` imports the JSON file and
expects:

| Level | Fields |
| --- | --- |
| Corpus | `version`, `source_raw_run`, `source_frontend_copy_run`, `cases` |
| Case | `id`, `category`, `query`, `viewports`, `visual_focus`, `desktop_focus`, `mobile_focus`, `expected_primary_visual_concerns` |

The 20 cases all request both viewport labels already used by the manual
baseline:

- `desktop_1280`
- `mobile_390`

Automation should target the rendered `/visual-qa` surface rather than add a
second corpus parser or a second case manifest. The existing page is the
current runtime contract for case order, case IDs, queries, and loaded result
cards.

### 3.2 `/visual-qa` implementation

`/visual-qa` is already the correct automation target:

- `frontend/src/main.tsx` routes `/visual-qa` to `VisualQaPage`.
- `VisualQaPage` loads all `VISUAL_QA_CASES` with live `postQuery` calls and a
  concurrency limit of 3.
- Loaded cards render the public result composition through `ResultRenderer`
  plus `ResultEnvelope` for successful responses.
- Every case card has a stable selector:
  `data-visual-case-id="<case_id>"`.
- The page exposes run progress, loaded response count, backend status counts,
  request error count, the current manual capture workflow, and each case's
  desktop/mobile review focus.

The stable card selector is sufficient for a first automated capture pass. The
capture tool should wait for the page to complete all 20 live requests, fail if
request errors are present, and then capture cards from the DOM in page order.

## 4. Existing Screenshot and Browser Infrastructure

### 4.1 Present in the repo

| Area | Current state | Implication |
| --- | --- | --- |
| Browser-side screenshot helper | `frontend/src/lib/reviewScreenshots.ts` uses `html-to-image` and `JSZip` to download PNG ZIPs from DOM elements. | Manual current-viewport screenshots already exist. |
| `/visual-qa` ZIP button | `VisualQaPage` passes every loaded case card to the screenshot helper. | Reviewers can capture per-card DOM images now, but the browser download path is not an artifact-producing command. |
| `/review` ZIP button | `ReviewPage` captures one hidden representative per renderer shape. | Useful prior art, but it is shape-based rather than the 20 case-targeted corpus. |
| Unit coverage | `reviewScreenshots.test.ts` covers helper fallback/options, and `VisualQaPage.test.tsx` covers 20-case page and capture-button plumbing. | Existing tests cover UI wiring, not real browser layout evidence. |
| Output policy | `.gitignore` ignores `outputs/`. | Generated screenshot runs can live under `outputs/` without becoming committed assets. |

### 4.2 Not present in the repo

At preflight time, the inspected frontend package and repo harnesses did not
provide:

- a direct Playwright or Cypress dependency
- a Playwright test config or screenshot snapshot suite
- a repo-owned headless browser capture command for `/visual-qa`
- a CDP/Chrome screenshot tool under `tools/` or `frontend/`
- CI jobs that install Node, build the frontend, install a browser, start the
  API shell, and publish screenshot artifacts

`frontend/package-lock.json` contains optional Vitest metadata for
`@vitest/browser-playwright`, but that is not an installed screenshot harness.
The expanded manual baseline return package says its headless capture script was
temporary and wrote artifacts outside the repo.

## 5. Approach Decision

### 5.1 Options

| Option | Strength | Limitation | Decision |
| --- | --- | --- | --- |
| Keep using the in-browser ZIP download only | Already available and case-targeted on `/visual-qa`. | Manual download flow, current viewport only, no run manifest, no page metrics, no consistent output directory. | Keep as manual fallback. |
| Hand-roll a local Chrome/CDP capture script | The latest manual baseline proved a headless browser script can capture this surface. | Duplicates browser orchestration and waiting logic that Playwright already owns. | Do not make this the repo harness. |
| Playwright screenshot tests with snapshot assertions | Good future path for browser lifecycle, viewports, selectors, and optional comparisons. | Starts with test semantics and baseline management before pixel stability policy exists. | Defer snapshot tests. |
| Playwright artifact capture command against the production-like local shell | Repeatable viewports, full-page and per-card screenshots, metrics, exit codes, and output paths without pixel-diff policy. | Adds browser dependency/setup and still depends on a live local API shell. | Recommended first wave. |
| Full screenshot diffing | Can catch visual drift after baselines and review policy exist. | Live NBA data, images, fonts, table width, and intentional UI iteration can create noisy diffs. | Defer. |

### 5.2 Recommendation

Add a repo-owned Node capture command using Playwright as the browser driver.
Run it against the existing production-like local FastAPI shell at
`/visual-qa`. The command should generate review artifacts and hard capture
integrity checks, not screenshot diffs.

This recommendation uses each existing boundary for the job it already does:

- `/visual-qa` remains the case manifest, live query path, public renderer
  composition, and stable card-selector surface.
- The local production shell remains the preferred route under capture because
  it serves the built UI with the API used by the manual baseline.
- Playwright owns viewport setup, page waiting, DOM selection, page
  screenshots, element screenshots, and headless CI portability.
- `outputs/` owns generated evidence.

The existing `html-to-image` ZIP button should remain available for manual
review. It should not be the first automated artifact command because it writes
through a browser download action and does not produce page-level metrics or
full-page evidence.

## 6. Capture Scope

| Capture question | First automation wave |
| --- | --- |
| Full page screenshots | Yes. Capture one `page.png` per viewport for run context, page-level overflow review, and overall hierarchy scanning. |
| Per-card screenshots | Yes. Capture every `data-visual-case-id` card per viewport. These are the primary review artifacts. |
| Desktop width | Yes. Use `1280x900` and name it `desktop_1280` to match the accepted manual baseline. |
| Mobile width | Yes. Use `390x844` and name it `mobile_390` to match the accepted manual baseline. |
| All 20 cases | Yes. The canonical run captures the complete corpus at both viewports: 40 card screenshots plus two page screenshots. |
| Expansion-only subset | Not as the canonical first wave. Optional case filters are acceptable for iteration, but do not create a second hard-coded five-case manifest. |

Per-card capture should use the existing case card selector first. That keeps
the review focus text, live status, and rendered result together. Result-only
screenshots can be evaluated later if card-level captures become too tall for
review.

## 7. Artifact Contract

Use the requested artifact root:

```text
outputs/visual_qa_screenshots/<run_id>/
```

Recommended first-wave tree:

```text
outputs/visual_qa_screenshots/<run_id>/
  manifest.json
  desktop_1280/
    metrics.json
    page.png
    cards/
      <case_id>.png
  mobile_390/
    metrics.json
    page.png
    cards/
      <case_id>.png
```

`manifest.json` should record enough context to review or reproduce a run:

- run ID
- capture timestamp
- base URL
- viewport names and dimensions
- observed case IDs in capture order
- output files
- script/tool version when practical

Each viewport `metrics.json` should record at least:

- observed card count
- run-progress completion text or equivalent loaded completion state
- loaded response count
- request error count
- backend status counts when the page exposes them
- viewport width and page/body `clientWidth` and `scrollWidth`
- document-level overflow verdict

Capture should fail rather than write a misleading pass artifact when:

- the page does not reach the 20-case completed state within the configured
  timeout
- a required viewport has fewer or more than the expected rendered case cards
- request errors are nonzero
- a card selector is missing or duplicates a case ID
- document-level horizontal overflow is measured at the target viewport

The first wave may still write failure diagnostics before exiting nonzero if
that helps debug failed capture setup.

## 8. Commit Policy

Commit in the first execution wave:

- the Node capture tool
- direct frontend browser dependency and lockfile changes required to run it
- the frontend npm script
- the thin Makefile target
- docs for the capture command and artifact contract
- focused automated tests for any reusable argument or manifest helpers if the
  implementation introduces them

Do not commit in the first execution wave:

- PNG screenshot runs
- generated metrics/manifests under `outputs/`
- pixel baseline images
- screenshot diff snapshots or thresholds
- QA corpus edits
- product UI changes made only to simplify screenshots

This keeps generated evidence local by default and preserves the existing
`outputs/` policy.

## 9. Command Surface

### 9.1 Tool choice

Use a Node tool under the frontend package, for example:

```text
frontend/tools/captureVisualQaScreenshots.mjs
```

The browser automation dependency should be explicit in the frontend package.
For the first non-test artifact runner, a direct Playwright dependency is more
honest than relying on optional Vitest metadata or an ad hoc temporary script.
If the project later promotes pixel diffs into browser tests, evaluate whether
to add Playwright Test then.

Do not add a Python wrapper around browser capture in the first wave. The
frontend package is already the owner of Node/browser dependencies, and the
capture logic needs browser selectors and screenshot APIs.

### 9.2 npm script

Add a frontend script with this intent:

```text
npm --prefix frontend run qa:visual-screenshots -- \
  --base-url http://127.0.0.1:8000 \
  --run-id <run_id>
```

Recommended default behavior:

- default output root:
  `../outputs/visual_qa_screenshots`
- default capture set: all corpus cards rendered on `/visual-qa`
- default viewports: `desktop_1280` and `mobile_390`
- default run ID: UTC timestamp when not supplied

Useful bounded flags:

- `--base-url` so local shell, preview, or future CI server URLs are explicit
- `--run-id` for stable artifact folders in handoff docs
- `--output-root` for test or CI artifact routing
- optional repeated `--case-id` for targeted local reruns without introducing
  an expansion-only manifest

### 9.3 Makefile target

Add a thin Makefile target so the repo has one discoverable top-level command,
for example:

```text
make visual-qa-screenshots \
  VISUAL_QA_BASE_URL=http://127.0.0.1:8000 \
  VISUAL_QA_RUN_ID=<run_id>
```

The Makefile target should delegate to the frontend npm script. It should not
reimplement browser logic or silently start a long-lived API process in the
first wave.

## 10. CI Suitability and Cost

The recommended command is CI-friendly in shape because it is headless, accepts
an explicit base URL, writes a deterministic artifact tree, and can exit
nonzero for capture integrity failures.

It should not be added to the current CI gate in the first wave:

- `.github/workflows/ci.yml` currently runs Python lint and pytest targets,
  not Node frontend builds or browser installs.
- A CI screenshot run would need frontend install/build, Chromium install,
  FastAPI startup, local data readiness, artifact upload, and timeout policy.
- The current need is repeatable evidence generation after a passed manual
  baseline, not a pixel baseline gate.

Local cost for the canonical first wave is bounded:

- one browser dependency/install cost, including a Chromium download if it is
  not already present
- two `/visual-qa` loads, one per viewport
- about 40 card screenshots and two full-page screenshots per run
- the same live `/query` surface already exercised by the manual baseline

If later runs are too slow, optimize after measuring. Do not shrink the
canonical first artifact run to the five expansion cases before one repeatable
20-case capture exists.

## 11. First Executable Automation Wave

### 11.1 Goal

Create a local, repeatable, non-diffing screenshot artifact run for the accepted
20-case `/visual-qa` baseline at `desktop_1280` and `mobile_390`.

### 11.2 In scope

1. Add direct Playwright-backed Node capture tooling owned by `frontend/`.
2. Add `qa:visual-screenshots` in `frontend/package.json`.
3. Add a thin `make visual-qa-screenshots` entry point.
4. Capture one full page plus every case card at both accepted viewports into
   `outputs/visual_qa_screenshots/<run_id>/`.
5. Write run manifest and viewport metrics JSON.
6. Fail the capture command for request errors, missing case cards, incomplete
   live-case loading, duplicate case IDs, or document-level horizontal
   overflow.
7. Document the local run prerequisites: build the frontend, start the local
   production API shell, then run the capture command with the base URL.

### 11.3 Out of scope

- screenshot diffs
- committed PNG baselines
- CI workflow changes
- QA corpus changes
- `/visual-qa` rendering changes
- product rendering changes
- backend/parser/result-contract changes
- a separate expansion-only screenshot suite

### 11.4 Acceptance criteria for that wave

- A local production-shell run creates 42 PNG files for the canonical capture:
  40 case cards and 2 full pages.
- The run creates `manifest.json` and metrics for both viewports.
- The manifest includes all 20 observed Visual QA case IDs.
- Metrics show request errors 0 and no document-level horizontal overflow for
  the accepted viewport pair on the validation run.
- The command exits nonzero for an intentionally unreachable base URL or
  missing page completion state.
- Generated artifacts stay under ignored `outputs/`.

## 12. Deferred Follow-Ups

After the first repeatable artifact run exists:

1. Decide whether CI should run screenshot capture as an on-demand/manual
   workflow that uploads artifacts.
2. Decide whether any page/card artifacts are stable enough for diffing.
3. If diffing is justified, define baseline ownership, update cadence, image
   masking/threshold policy, data freshness assumptions, and failure triage
   before adding snapshot assertions.
4. Consider adding result-only captures or selected targeted rerun presets only
   if card-level evidence is too noisy or slow.

## 13. Execution Status

The first executable automation wave is implemented and locally validated:

- Playwright-backed Node capture tool:
  `frontend/tools/captureVisualQaScreenshots.mjs`
- Frontend command:
  `npm --prefix frontend run qa:visual-screenshots -- --base-url http://127.0.0.1:8000 --run-id <run_id>`
- Top-level command:
  `make visual-qa-screenshots VISUAL_QA_BASE_URL=http://127.0.0.1:8000 VISUAL_QA_RUN_ID=<run_id>`
- Artifact root:
  `outputs/visual_qa_screenshots/<run_id>/`

The implemented wave keeps the preflight boundary: generated screenshots are
ignored artifacts, not committed baselines; screenshot diffing and CI gating
remain deferred.

Canonical local validation passed on 2026-05-22:

- Run ID: `visual_qa_20_case_baseline`.
- Command:
  `make visual-qa-screenshots VISUAL_QA_BASE_URL=http://127.0.0.1:8000 VISUAL_QA_RUN_ID=visual_qa_20_case_baseline`.
- Artifact root:
  `outputs/visual_qa_screenshots/visual_qa_20_case_baseline/`.
- `desktop_1280`: 20/20 cases, request errors 0, statuses `ok: 15`,
  `no_result: 5`, `error: 0`, document/body overflow `false`.
- `mobile_390`: 20/20 cases, request errors 0, statuses `ok: 15`,
  `no_result: 5`, `error: 0`, document/body overflow `false`.
- Manifest evidence: 20 desktop card screenshots and 20 mobile card
  screenshots listed.
- PNG total: 42 expected captures, including the two full-page screenshots.

Committed PNG baselines remain deferred with screenshot diffing and CI gating.
