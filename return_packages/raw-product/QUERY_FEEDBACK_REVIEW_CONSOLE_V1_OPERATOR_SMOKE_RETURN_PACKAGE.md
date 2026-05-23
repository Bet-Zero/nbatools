# Query Feedback Review Console V1 Operator Smoke Return Package

## What Was Checked

- Production-like direct load of `/admin/feedback` through the local FastAPI UI shell.
- Disabled state when `NBATOOLS_ADMIN_FEEDBACK_ENABLED` is not enabled.
- Unauthorized/token-required state when `NBATOOLS_ADMIN_FEEDBACK_ENABLED=true`
  and `NBATOOLS_ADMIN_TOKEN` is configured.
- Fixture-backed grouped feedback list rendering in the browser.
- Selecting a feedback group loads detail and handoff summary.
- Triage form save sends the mutable overlay payload and reports that original
  feedback records are unchanged.
- Backend targeted admin feedback API/review/export behavior.
- Frontend targeted admin feedback page and API client behavior.
- `make query-feedback-export` fallback workflow.
- `git diff --check`.

## Local Setup And Env Used

Repo: `/Users/brenthibbitts/nba_tools`

Disabled shell smoke:

```bash
PYTHONPATH=src .venv/bin/python -m uvicorn nbatools.api:app --host 127.0.0.1 --port 8020
```

Enabled/token shell smoke:

```bash
NBATOOLS_ADMIN_FEEDBACK_ENABLED=true \
NBATOOLS_ADMIN_TOKEN=secret \
PYTHONPATH=src .venv/bin/python -m uvicorn nbatools.api:app --host 127.0.0.1 --port 8021
```

Browser smoke used Playwright from `frontend/` against the built FastAPI-served
UI shell. Fixture-backed feedback API responses were mocked in the browser for
the grouped-list/detail/save operator flow.

## Console Load Result

Passed.

`/admin/feedback` loaded through the local production shell and rendered:

- `Query Feedback Review Console`
- admin token input
- feedback filters
- grouped feedback/detail layout

## Disabled Behavior

Passed.

With admin feedback disabled, the page loaded and showed:

`The admin feedback API is disabled. Enable NBATOOLS_ADMIN_FEEDBACK_ENABLED before using this console.`

The list settled to `0 groups loaded.`

## Unauthorized / Token Behavior

Passed.

With admin feedback enabled and `NBATOOLS_ADMIN_TOKEN=secret`, the page showed:

`The admin feedback API requires a token. Paste the token above to retry with X-NBATools-Admin-Token.`

After entering `secret`, mocked fixture-backed requests rendered the grouped
feedback workflow.

## Fixture-Backed Grouped Feedback Result

Passed.

Browser fixture smoke rendered two groups, including:

- `Jokic personal fouls leaderboard`
- `Celtics bench scoring leaders`

Selecting `Celtics bench scoring leaders` loaded detail and a handoff summary
containing:

- `group_id: qfg_456`
- `representative_query: Celtics bench scoring leaders`

## Triage Save Result

Passed.

The browser smoke saved this overlay payload:

```json
{
  "review_status": "reviewed",
  "triage_decision": "bug",
  "review_notes": "Create regression test.",
  "linked_case_or_issue": "RAW-123",
  "reviewer_source": "admin_feedback_console"
}
```

The UI then showed:

`Triage overlay saved. Original feedback records were not changed.`

Backend coverage also passed the immutable-source round trip:
`test_triage_overlay_write_and_read_round_trip_without_mutating_sources`.

## Handoff Summary Result

Passed.

The selected-group handoff summary was visible, copyable, and contained the
selected group id, representative query, unsupported filters, suggested triage,
current saved decision, review notes, and linked case/issue fields.

## Export Fallback Result

Passed with environment notes.

Initial command:

```bash
make query-feedback-export
```

failed because this shell did not have `python` on `PATH`.

Rerun command:

```bash
make query-feedback-export PYTHON=.venv/bin/python
```

initially failed in the sandbox with R2 DNS/network restriction. After rerun
with network approval, the fallback export passed:

- output: `outputs/query_feedback_exports/20260523T111814Z`
- records exported: `5`
- groups: `3`
- excluded smoke records: `6`

## Validation Commands

Passed:

```bash
npm test -- src/test/AdminFeedbackPage.test.tsx src/test/client.test.ts
```

Result: 2 files passed, 24 tests passed.

Passed:

```bash
.venv/bin/pytest tests/test_admin_feedback_api.py tests/test_query_feedback_review.py tests/test_export_query_feedback.py -n0
```

Result: 19 tests passed.

Passed:

```bash
git diff --check
```

Initial frontend test command with `--runInBand` failed because Vitest does not
support that Jest option. The corrected targeted Vitest command passed.

## Docs

No docs were changed. The operator workflow was understandable during smoke,
and the existing runbook/UI guide already describe the console, admin env, token
header, immutable overlay model, and export fallback.

## Blocking Issues

None found.

## Next Recommended Action

Keep `/admin/feedback` as an internal operator-only workflow and proceed to a
real R2-backed operator review when actual feedback volume justifies triage.
V2 candidates remain individual source-record expansion, date/smoke filters in
the UI, and bulk triage actions.
