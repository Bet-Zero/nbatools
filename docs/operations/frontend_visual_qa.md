# Frontend Visual QA

## Purpose

Frontend Visual QA verifies that rendered query results remain readable,
answer-first, and contained at the supported desktop and mobile widths. It
reviews the real `/visual-qa` page, which loads live `POST /query` responses and
renders the public result composition.

This runbook covers manual review and repeatable non-diffing screenshot
capture. Generated screenshot artifacts support review; they are not durable
source-of-truth documentation.

## When To Run It

Run frontend Visual QA when:

- a frontend result renderer, result layout, or no-result presentation changes
- a visual corpus case is added or changed
- a mobile overflow or dense-table issue is fixed
- release or deployment evidence needs a rendered UI review refresh
- a targeted visual regression needs reproducible desktop/mobile screenshots

Use focused case reruns while iterating. Use the full corpus for canonical
review evidence.

## Review Surface And Viewports

- Internal review route: `/visual-qa`
- Availability boundary: local development and Vercel preview only; public
  production returns `404 internal_route_unavailable`
- Live render path: `POST /query` through the public result composition
- Stable card selector: `data-visual-case-id="<case_id>"`
- Desktop viewport: approximately `1280px` wide
- Mobile viewport: approximately `390px` wide
- Automated viewport labels: `desktop_1280` and `mobile_390`
- Automated dimensions: `1280x900` and `390x844`

The accepted review pattern checks every visual corpus case at both viewports.
Wide tables may scroll inside their table frame, but the page itself must not
have document-level horizontal overflow.

## Manual Review Workflow

1. Build the frontend when reviewing the production-like shell:

   ```bash
   npm --prefix frontend run build
   ```

2. Start the local API shell that serves `/query` and the built frontend.
3. Open `http://127.0.0.1:8000/visual-qa`, or use an explicitly identified
   Vercel preview during active UI iteration. Never use the public production
   deployment for this internal corpus surface.
4. Confirm that opening the route has sent no query requests, then choose
   **Run live cases** to start the deliberate corpus run.
5. Wait for all requested cases to finish loading through the live query path.
6. Review the desktop pass at approximately `1280px`.
7. Review the mobile pass at approximately `390px`.
8. Record pass/fail notes, blocking findings, and deferred polish with the
   active task materials according to
   [`working_and_archive_policy.md`](working_and_archive_policy.md).
9. Promote durable conclusions into `docs/` when the review changes a
   long-lived runbook, contract, or verified current-state statement.

Use the `/visual-qa` page's in-browser ZIP capture as a manual fallback when a
reviewer needs current-viewport card images without a full artifact run.

## Repeatable Screenshot Workflow

For reproducible non-diffing screenshots and metrics, run:

```bash
make visual-qa-screenshots \
  VISUAL_QA_BASE_URL=http://127.0.0.1:8000 \
  VISUAL_QA_RUN_ID=<run_id>
```

Equivalent frontend command:

```bash
npm --prefix frontend run qa:visual-screenshots -- \
  --base-url http://127.0.0.1:8000 \
  --run-id <run_id>
```

The canonical run captures every corpus card and one full-page image at each
viewport under:

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

The capture command opens the route and deliberately activates **Run live
cases** before waiting for completion. Merely mounting `/visual-qa` must issue
zero `POST /query` requests.

The manifest is the run checklist: use it to confirm the run ID, base URL,
capture timestamp, exact source commit and clean-tree state, browser version,
visual-corpus hash, viewport dimensions, observed case IDs, capture order,
artifact SHA-256 values, and output files. Use each viewport's `metrics.json` to confirm completion, loaded
response count, request error count, backend status counts, viewport and page
widths, and document-level overflow verdict.

Capture must fail rather than report a misleading pass when case loading is
incomplete, request errors are present, case IDs are missing or duplicated, the
expected card set drifts, horizontal overflow is measured, or screenshot
capture fails.

Repeated case filters are appropriate for local iteration. They are not a
replacement for a canonical full-corpus review.

## Browser Release Review Receipt

For one desktop/mobile receipt covering public loading, summary success,
representative game-table success, zero-result, unsupported no-result,
backend-error, transport-error, freshness, save-dialog, and idle internal-route
states, run:

```bash
make browser-release-review \
  BROWSER_REVIEW_BASE_URL=http://127.0.0.1:8000 \
  BROWSER_REVIEW_RUN_ID=<run_id>
```

Equivalent frontend command:

```bash
npm --prefix frontend run qa:browser-release-review -- \
  --base-url http://127.0.0.1:8000 \
  --run-id <run_id>
```

The receipt is written to
`outputs/browser_release_review/<run_id>/receipt.json`. It records the exact
source commit and clean-tree state, browser version, corpus hash, screenshot
hashes, axe results, dialog keyboard/focus probes, result-announcement probe,
reduced-motion probe, and `/visual-qa` mount request count at `1280x900` and
`390x844`.

The runner separates `executionStatus` from `acceptanceStatus`. A complete
capture may legitimately report blocked acceptance when axe, keyboard, focus,
announcement, contrast, or reduced-motion checks expose a release issue.
`humanReview` stays `pending` until a person inspects and certifies the retained
images. The deterministic zero/no-result/error fixtures test presentation
states; the freshness, loading, summary success, representative table success,
and idle internal route use the live local API shell. The receipt requires the
summary player image to load, requires all ten representative game rows, and
records document-overflow and NBA-asset-proxy evidence. The Node-side asset
proxy works around headless Chromium's CDN HTTP/2 transport failure without
changing application behavior; upstream asset failures still block the run.
Run the canonical visual corpus separately for broader live result coverage.
Historical receipts may include the formerly public feedback dialog. The
current release runner omits that state because manual feedback persistence and
its public controls are deferred.

### Retained Release Audit Snapshots

Generated browser artifacts remain under `outputs/` by default. When an
explicit release-review task requires evidence to survive generated-output
cleanup, retain only the curated receipt and representative images under a
dated `docs/audits/` folder. The audit summary must record the exact source
commit and clean-tree state, browser, viewports, live-versus-fixture boundary,
artifact integrity, acceptance status, human-review status, and blocking
findings. A retained snapshot must not become a runtime fixture, screenshot
baseline, or substitute for a current review.

The retained pre-remediation example is the
[2026-07-15 browser release review](../audits/2026-07-15-browser-release-review/README.md).
Its execution completed and accurately preserved the original blockers. PR
#269 subsequently merged the E-05 fixes, and a real exact-worktree candidate
rerun passed at both viewports with zero blockers. Clean current-main rerun
`d11_clean_306cbb9_20260716` now retains the same zero-blocker result, exact
commit/tree binding, 20 artifact hashes, and all accessibility probes in that
audit. That historical receipt remained human-review pending and did not imply
human or release acceptance.

The superseding [2026-07-19 browser release
review](../audits/2026-07-19-browser-release-review/README.md) retains the clean
post-feedback-deferral machine receipt and all 20 hashed state images. John
Matthew approved the exact four-image desktop/mobile summary-and-table package
on 2026-07-19. The generated receipt remains unmodified; a separate owner
receipt binds the explicit decision to the machine-receipt and image hashes.
That closes D-11 human UI review only. It does not imply final Queue D or
broader release acceptance.

## Text Snapshots And Render Review Outputs

Use text snapshots or rendered-review notes when a reviewer needs compact
evidence for copy, hierarchy, or representative public results. Generated
review artifacts may live under:

```text
outputs/frontend_visual_qa/<run_id>/
outputs/public_ui_render_review/<run_id>/
```

`outputs/visual_qa_screenshots/` is the screenshot-capture artifact root.
`outputs/public_ui_render_review/` is complementary rendered UI review evidence,
not a replacement for the `/visual-qa` screenshot manifest or manual checklist.

Generated files under `outputs/` are evidence artifacts only. They are not
durable source-of-truth documentation.

Tracked visual QA corpus metadata may name generated `outputs/` runs only as
provenance. The visual QA page and tests must not read those generated paths as
runtime input; any stable test fixture belongs under a tracked fixture path
outside `outputs/`.

## What Counts As UI-Reviewed

A scope is `UI-reviewed` only when a reviewer actually inspects the rendered
browser output for the stated cases and viewports. A successful screenshot
capture proves artifact integrity; it does not prove that a human reviewed the
images or accepted the visual result.

Record:

- reviewed cases and viewports
- whether the pass used local, preview, or production-like rendering
- blocking findings
- deferred polish
- the relevant generated run ID when artifacts were captured

## File Placement

- Put durable workflow rules and verified long-lived conclusions in `docs/`.
- Put active checklists, triage notes, screenshot notes, and handoff notes with
  the active task materials according to
  [`working_and_archive_policy.md`](working_and_archive_policy.md).
- Keep generated screenshots, metrics, manifests, and rendered-review artifacts
  under `outputs/`.

Generated screenshots and output artifacts are not durable source of truth
unless an explicit release-review task curates the bounded evidence into a
dated audit snapshot and summarizes its relevant conclusions in `docs/`.

## Deferred Decisions

Screenshot diffing, committed PNG baselines, baseline ownership, threshold
policy, masking rules, and CI gating remain deferred until a separate review
approves them.
