# Browser Release Review — 2026-07-15

## Review State

This retained Queue D review is an evidence snapshot, not a release approval.

| Field | Value |
| --- | --- |
| Reviewed source commit | `090022f978ddf9097c1cda8daa21977ec9ee5a9b` |
| Source tree | clean |
| Browser | Chromium `148.0.7778.96` |
| Viewports | `1280x900` and `390x844` |
| Receipt execution | `complete` |
| Acceptance | `blocked` |
| Human review | `pending` |
| Visual corpus SHA-256 | `500e235b74206bd55cbde5f96dab8da58b9ae8f0201040414f2d5e6442797683` |

The retained [receipt](public_states_090022f/receipt.json) contains the exact
source metadata, 20 screenshot hashes, axe details, dialog probes,
result-announcement probe, reduced-motion probe, and internal-route request
counts. The adjacent `desktop_1280/` and `mobile_390/` folders retain ten public
state images per viewport.

## Scope And Fixture Boundary

The live local API shell supplied freshness, loading, success, and idle
`/visual-qa` states. Deterministic fixtures supplied zero-result, unsupported
no-result, backend-error, and transport-error states. The fixtures verify
presentation boundaries only; they are not query-engine acceptance evidence.

A separate canonical visual-corpus run exercised all 20 live cases at both
viewports. It completed with 19 `ok` responses, one expected `no_result`, zero
request errors, and no document-level horizontal overflow at each viewport.
The manifest covered 44 hashed artifacts and had SHA-256
`0cec06c1cfccf7b949ffd029d559c61e393c951ea6856a6483f4af1a9054c329`.
The full generated corpus remains local output; the durable conclusions and
compact public-state receipt are retained here.

## Blocking Findings

The automated release review found the same blockers at desktop and mobile:

- 13 serious/critical state-rule results from `color-contrast` and
  `aria-prohibited-attr`
- no live-region owner for the completed query result
- save dialog does not close on Escape, wrap Tab focus, or restore trigger
  focus
- feedback dialog lacks initial focus and does not close on Escape, wrap Tab
  focus, or restore trigger focus
- 21 animated elements remain active with reduced motion requested

Opening `/visual-qa` produced zero `POST /query` requests at both viewports.
This preserves the deliberate-run boundary.

## Visual Inspection Notes

An agent inspected representative retained desktop and mobile images for
success, loading, unsupported no-result, backend error, save, and feedback
states. The answer-first hierarchy, state differentiation, responsive
single-column mobile composition, and desktop two-column composition are
coherent. The visible muted labels corroborate the contrast findings. The
mobile full-page feedback capture also has a heavily darkened, segmented
backdrop, so a human reviewer must distinguish capture composition from actual
viewport behavior before certifying the dialog presentation.

This representative inspection does not change `humanReview` from `pending`.
Release acceptance remains blocked until the accessibility primitives are
remediated and an owner records the human review decision. That remediation is
the next queue boundary and is outside Queue D.
