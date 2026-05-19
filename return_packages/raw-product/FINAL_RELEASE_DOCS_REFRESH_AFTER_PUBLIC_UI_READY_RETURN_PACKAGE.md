# Final Release Docs Refresh After Public UI Ready Return Package

## 1. What changed

- Refreshed final release-candidate docs after
  `return_packages/raw-product/FINAL_PUBLIC_UI_RELEASE_REVIEW_RETURN_PACKAGE.md`
  classified the public UI as `PUBLIC_UI_READY_WITH_NOTES`.
- Recorded that the Final Public UI Release Review passed on the live main
  preview with route checks for `/`, `/?debug=1`, `/review`, and `/visual-qa`,
  14 desktop public query checks, 13 mobile 390px family checks, debug/details
  preservation, feedback preservation, and no blocking issues.
- Updated release language so broad public launch is no longer blocked by a
  debug-heavy default UI.
- Moved remaining UI items into post-launch polish: screenshot automation,
  visual QA corpus expansion, unsupported/no-result copy taxonomy refinement,
  existing `ReviewPage` lint hook warning, and accepted internal horizontal
  scrolling for wide tables.
- Preserved current backend/parser/result-contract/corpus boundaries; this was
  docs-only.

## 2. Files changed

| File | Change type | Notes |
|---|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | release status refresh | Added public UI status, final public UI review evidence, post-launch UI notes, and updated next-roadmap ordering. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | release package refresh | Added public UI status, final public UI review validation row, launch-blocker resolution language, and future deployment checks. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | readiness refresh | Added public UI status, final public UI review evidence, preview/readiness table row, and final classification update. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | checkpoint refresh | Added final public UI review status/evidence and updated remaining notes and next options. |
| `docs/operations/ui_guide.md` | operations/current behavior note | Recorded that the public answer-first display-mode boundary is `PUBLIC_UI_READY_WITH_NOTES`. |
| `docs/index.md` | documentation index refresh | Updated release-doc descriptions to mention public UI readiness evidence/status. |
| `return_packages/raw-product/FINAL_RELEASE_DOCS_REFRESH_AFTER_PUBLIC_UI_READY_RETURN_PACKAGE.md` | return package | Summarizes this docs-only refresh. |

## 3. Current release status

- Release status: `RELEASE_CANDIDATE_WITH_NOTES`
- Preview status: `PREVIEW_READY_WITH_NOTES`
- Feedback status: `FEEDBACK_READY_WITH_NOTES`
- Feedback review/export workflow: implemented with notes
- Public UI status: `PUBLIC_UI_READY_WITH_NOTES`

## 4. Public UI status

The public UI is ready with notes. The final release review verified:

- `/` is public and answer-first by default.
- `/?debug=1` preserves debug-rich diagnostics.
- `/review` remains debug-rich and suppresses public feedback buttons.
- `/visual-qa` preserves internal case metadata/capture wrappers and suppresses
  public feedback buttons.
- Desktop public query review passed across 14 representative queries.
- Mobile 390px review passed across 13 major families.
- Feedback UI remains available on `/` for successful answers and no-result
  states.
- Blocking issues: none.

## 5. Remaining notes

- Frontend-copy QA remains selected coverage, not all 246 backend cases.
- Visual QA remains manual; no screenshot-diff automation exists yet.
- Visual QA corpus expansion remains post-launch polish.
- Broad unsupported/no-result public-copy taxonomy refinement remains
  post-launch polish.
- Existing frontend warnings remain non-blocking: Vite large-chunk warning and
  `ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- Wide tables still use internal horizontal scrolling.
- Feedback review remains operational tooling rather than an admin dashboard or
  mutable triage overlay.

## 6. Validation result

Command:

```bash
git diff --check
```

Result: passed with no output.

## 7. Final recommendation

Ship or hand off the current release candidate with notes. Public launch is no
longer blocked by the default UI presentation; remaining UI work is post-launch
polish.
