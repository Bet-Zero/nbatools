# Raw Product Release Package Refresh After R2 Sync Fix Return Package

## 1. Executive summary

- What changed: refreshed Raw Product release package, readiness/checkpoint,
  harness, and deployment docs after the opponent-conference R2 sync blocker
  was resolved.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.
- Release status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- R2 sync status: pass; `raw/teams/team_conference_membership.csv` is present
  in R2.
- Latest deployment smoke:
  `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`;
  `ok: true`, `case_count: 7`, `failure_count: 0`.
- Latest visual QA preview status: `/visual-qa` loaded 15/15 cases with request
  errors 0.
- Recommended next step: release candidate handoff.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | release package refresh | Record resolved R2 blocker, R2 membership-file availability, preview smoke pass, deployment smoke evidence, and remaining release notes. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | readiness refresh | Record previous preview blocker resolution, latest R2 sync evidence, preview smoke pass, deployment smoke pass, and `/visual-qa` request errors 0. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | checkpoint refresh | Update current checkpoint evidence and next recommendation after the R2 fix. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | harness-plan refresh | Update release-package status and roadmap options now that opponent-conference preview smoke is complete. |
| `docs/operations/deployment.md` | operations refresh | Document R2 sync requirement for new data files, membership-file head-object verification, and deploy-blocker treatment for missing R2 data. |
| `return_packages/raw-product/RAW_PRODUCT_RELEASE_PACKAGE_REFRESH_AFTER_R2_SYNC_FIX_RETURN_PACKAGE.md` | new return package | Summarize this docs-only refresh and validation. |

## 3. Blocker resolution summary

| Previous blocker | Resolution | Evidence |
|---|---|---|
| Missing R2 membership file | Synced `raw/teams/team_conference_membership.csv` to R2. | Dry-run included the file; sync uploaded it; `head_object` returned `ContentLength=4999`, `LastModified=2026-05-17T09:03:29+00:00`, and `nbatools-md5=f9cc9a60c8f659651723a55640966d73`. |
| Opponent-conference preview `no_data` | Preview now resolves trusted East/West opponent lists. | Celtics vs East returned 52 games, 36-16; Lakers vs West returned 52 games, 33-19; Lakers road vs West last season returned 26 games, 14-12; Knicks vs Eastern Conference teams since January 1 returned 26 games, 17-9. |
| `/visual-qa` request error | Latest preview rerun loaded all visual QA cases without query request errors. | `/visual-qa`: loaded 15/15, request errors 0. |

## 4. Current release evidence

| Area | Status | Evidence |
|---|---|---|
| Raw QA | `PASS` | `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246 cases; expectation cases `pass: 246`; suspicious flags 0. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125 selected cases; rendered 125; render failures 0; soft checks `480/0/0`. |
| Preview smoke | `PASS` | `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`; four supported opponent-conference checks and two guardrails passed. |
| R2 data availability | `PASS` | `raw/teams/team_conference_membership.csv` exists in R2; dry-run, sync, and `head_object` passed. |
| Deployment smoke | `PASS` | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `failure_count: 0`; opponent-conference membership-data case returned 15 East opponents. |
| Visual QA | `PASS_WITH_MANUAL_LIMITATION` | Manual 15-case baseline remains accepted; latest preview `/visual-qa` loaded 15/15 with request errors 0; no screenshot automation. |

## 5. Remaining notes

- Frontend-copy coverage is selected coverage, not all 246 raw cases.
- Visual QA remains manual; no screenshot automation was added.
- Opponent-conference support is limited to trusted seasons `2024-25` and
  `2025-26`.
- Divisions, geography phrases, and historical opponent-conference coverage
  remain unsupported.

## 6. Validation

- `git diff --check`: pass.
- Markdown lint: not run; `markdownlint` and `markdownlint-cli2` were not
  available on PATH.

## 7. Next recommendation

Release candidate handoff.
