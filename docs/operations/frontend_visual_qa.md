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
3. Open `http://127.0.0.1:8000/visual-qa`, or use the frontend dev server during
   active UI iteration.
4. Wait for all requested cases to finish loading through the live query path.
5. Review the desktop pass at approximately `1280px`.
6. Review the mobile pass at approximately `390px`.
7. Record pass/fail notes, blocking findings, and deferred polish with the
   active task materials according to
   [`working_and_archive_policy.md`](working_and_archive_policy.md).
8. Promote durable conclusions into `docs/` when the review changes a
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

The manifest is the run checklist: use it to confirm the run ID, base URL,
capture timestamp, viewport dimensions, observed case IDs, capture order, and
output files. Use each viewport's `metrics.json` to confirm completion, loaded
response count, request error count, backend status counts, viewport and page
widths, and document-level overflow verdict.

Capture must fail rather than report a misleading pass when case loading is
incomplete, request errors are present, case IDs are missing or duplicated, the
expected card set drifts, horizontal overflow is measured, or screenshot
capture fails.

Repeated case filters are appropriate for local iteration. They are not a
replacement for a canonical full-corpus review.

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
unless their relevant conclusions are summarized in `docs/`.

## Deferred Decisions

Screenshot diffing, committed PNG baselines, baseline ownership, threshold
policy, masking rules, and CI gating remain deferred until a separate review
approves them.
