# Raw Product Release Evidence Summary

## 1. Purpose

This is the durable evidence summary for the current Raw Product release
candidate boundary. It promotes release/readiness evidence facts that were
previously cited through exact return-package paths into a source-of-truth doc
under `docs/`.

Return packages remain handoff receipts. They are useful provenance, but this
summary is the durable place to read current release evidence.

This summary is documentation only. It does not change product behavior,
release status, tests, QA corpus files, generated outputs, return packages, or
deployment state.

## 2. Current Status

| Area | Status |
| --- | --- |
| Release status | `RELEASE_CANDIDATE_WITH_NOTES` |
| Preview status | `PREVIEW_READY_WITH_NOTES` |
| Query feedback status | `FEEDBACK_READY_WITH_NOTES` |
| Public UI status | `PUBLIC_UI_READY_WITH_NOTES` |
| Post-review hardening | `COMPLETE_WITH_NOTES` |
| Division boundary cleanup | `PASS` |
| Production-ready posture | Ready after human acceptance of the notes in the release package and handoff |

Durable release docs:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`

## 3. Backend Raw QA Evidence

| Item | Evidence |
| --- | --- |
| Corpus | `qa/raw_query_answer_corpus.yaml` |
| Current corpus size | 253 cases after division-boundary guard additions |
| Latest full release run | `outputs/raw_query_answer_qa/20260517T070422Z/report.md` |
| JSONL source run | `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl` |
| Full-run covered cases | 246 |
| Expectation cases | `pass: 246` |
| Expectation checks | `pass: 1421` |
| Failed case IDs | none |
| Suspicious flags | 0 |
| Result statuses | `ok: 206`, `no_result: 31`, `error: 9` |
| Verified outlier bucket | `top_performance_high_points: 1` |
| Division-boundary targeted slices | `natural_query_route_priority` passed 35/35; `product_boundaries` passed 18/18 |

The nine `error` statuses in the latest full release run are expected corpus
outcomes, not failed expectations. The current corpus contains seven added
division-boundary guard cases; those were validated through targeted route
priority and product-boundary slices after the full 246-case run.

## 4. Frontend-Copy QA Evidence

| Item | Evidence |
| --- | --- |
| Corpus | `qa/frontend_copy_corpus.yaml` |
| Selected rendered-copy cases | 125 |
| Source backend run | `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl` |
| Latest report | `outputs/frontend_copy_qa/20260518T175548Z/frontend_copy_report.md` |
| Rendered successfully | 125 |
| Render failures | 0 |
| Missing backend records | 0 |
| Soft checks | `pass: 480`, `fail: 0`, `not_checked: 0` |

Frontend-copy QA is selected DOM/rendered-copy coverage. It is not a full
render of every backend raw QA case, and it is not screenshot/layout QA.

## 5. Visual QA Evidence

| Item | Evidence |
| --- | --- |
| Corpus | `qa/frontend_visual_qa_corpus.yaml` |
| Manual checklist | `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` |
| Expanded local baseline | 20/20 cases reviewed at desktop and mobile; 40 viewport reviews total |
| Desktop viewport | `1280px`; document/body widths `1280px`; statuses `ok: 15`, `no_result: 5`, `error: 0` |
| Mobile viewport | `390px`; document/body widths `390px`; statuses `ok: 15`, `no_result: 5`, `error: 0` |
| Request errors | 0 |
| Blocking visual issues | none in the expanded local baseline |
| Fixed visual finding | mobile dense table clipping for top performance, comparison, and playoff matchup tables |
| Fixed visual finding | filtered leaderboard hero context for guard and center examples |
| Fixed visual finding | preview mobile `/visual-qa` wrapper/card overflow at roughly 390px |
| Deployed preview request-health baseline | original 15-case set loaded 15/15 cases with request errors 0 before the five-case expansion |
| Limitation | manually reviewed; no screenshot diffing, committed PNG baselines, or CI gate |

Visual QA remains `READY_WITH_MANUAL_LIMITATION`: the expanded local baseline
is clean, but screenshot diffing and CI gating are still deferred.

## 6. Screenshot Artifact Evidence

| Item | Evidence |
| --- | --- |
| Canonical local artifact run id | `visual_qa_20_case_baseline` |
| Capture shape | 20 desktop card screenshots plus 20 mobile card screenshots |
| Extra captures | 2 full-page screenshots |
| Expected PNG total | 42 |
| Status counts | `ok: 15`, `no_result: 5`, `error: 0` |
| Request errors | 0 |
| Overflow check | false |
| Limitation | non-diffing capture only; no committed PNG baseline and no CI gate |

The artifact run proves repeatable local screenshot capture for the expanded
20-case corpus. It does not promote screenshot diffing or visual CI gating into
the release boundary.

## 7. Query Feedback Evidence

| Item | Evidence |
| --- | --- |
| Feedback status | `FEEDBACK_READY_WITH_NOTES` |
| Preview bucket/prefix | `nbatools-data` / `query_feedback/preview` |
| User-submitted records | verified present |
| Automatic diagnostics | verified present for no-result/unsupported and unrouted/error paths |
| Sanitization/privacy | passed; no disallowed PII fields found |
| Payload minimization | passed; no raw result rows/tables found in inspected records |
| Review/QA suppression | `/review` and `/visual-qa` feedback suppression passed |
| Runbook | `docs/operations/query_feedback_review.md` |

Query feedback is a launch-ready operational workflow with notes. Remaining
limitations are operational follow-ups: no admin dashboard, no mutable triage
overlay, heuristic suggestions only, and manual corpus conversion after review.

## 8. Query Feedback Export Workflow Evidence

| Item | Evidence |
| --- | --- |
| Workflow status | `IMPLEMENTED_WITH_NOTES` |
| Canonical command | `make query-feedback-export` |
| Export script | `tools/export_query_feedback.py` |
| Output base | `outputs/query_feedback_exports/<run_id>/` |
| Primary review artifact | `feedback_review.md` |
| Structured records | `feedback_records.csv`, `feedback_records.jsonl` |
| Summary artifact | `summary.json` |
| Review worksheet | `triage_decisions_template.csv` |

The exporter is read-only. Feedback triage remains human + ChatGPT product
judgment; agents execute follow-up only after triage is complete.

## 9. Parser/Routing And Hardening Evidence

Post-review hardening completed Waves 1-6 with notes.

| Wave | Durable outcome |
| --- | --- |
| Wave 1 | Parser/routing growth guardrails and feature promotion rules were documented in `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md` and `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`. |
| Wave 2 | Data-backed feature promotion discipline was added to `docs/operations/deployment.md` and linked from feature promotion rules. |
| Wave 3 | Weekly beta feedback review cadence and ownership were added to `docs/operations/query_feedback_review.md`. |
| Wave 4 | Return-package taxonomy rules were added to `docs/index.md`. |
| Wave 5 | README product positioning was refreshed to present NBA Tools as a public answer-first NBA stats product. |
| Wave 6 | Homepage/product promise and public answer-context de-duplication work completed for the release boundary. |

The hardening cycle did not change release classification. Remaining hardening
notes are deferred/post-launch work, not blockers.

## 10. Division Boundary Cleanup Evidence

| Item | Evidence |
| --- | --- |
| Behavior status | `PASS` |
| Product behavior | explicit NBA division opponent phrases return `no_result` / `filter_not_supported` |
| Metadata | `metadata.unsupported_filters=["opponent_division"]` |
| Route preservation | named-team division record phrases preserve `team_record`; no-subject division record phrases preserve `team_record_leaderboard` |
| Broad fallback prevention | division phrases no longer fall back to broad full-season, record-leaderboard, or conference-only answers |
| Division support added | no |
| Targeted snapshot tests | 65 passed |
| Parser slice | `make PYTEST=.venv/bin/pytest test-parser` passed 776 tests |
| Query slice | `make PYTEST=.venv/bin/pytest test-query` passed 776 tests |
| Raw QA route-priority slice | 35/35 passed |
| Raw QA product-boundary slice | 18/18 passed |
| Preflight suite | `make test-preflight` passed 2978 with 1 xpassed |
| Static check | `git diff --check` passed |

Conference Finals record phrasing remains a playoff-round surface, not an
opponent-conference filter. Division filtering itself remains unsupported.

## 11. Data/R2 Deployment Evidence

| Item | Evidence |
| --- | --- |
| Deployment data source | preview uses `DATA_SOURCE=r2` |
| Required key | `raw/teams/team_conference_membership.csv` |
| R2 availability | dry-run, sync, and `head_object` checks passed |
| Object size | `ContentLength=4999` |
| Last modified | `2026-05-17T09:03:29+00:00` |
| MD5 metadata | `nbatools-md5=f9cc9a60c8f659651723a55640966d73` |
| Deployment smoke artifact | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json` |
| Deployment smoke result | `ok: true`, `case_count: 7`, `failure_count: 0` |
| R2-sensitive smoke case | Celtics vs East returned `team_record` / `ok` with 15 East opponents |
| Team conference data test | `.venv/bin/pytest tests/test_team_conference_membership_data.py -q` passed 15 tests |

Missing required R2 data remains a deploy blocker for future previews or
production. Data-backed feature promotion must follow the checklist in
`docs/operations/deployment.md`.

## 12. Public UI Readiness Evidence

| Item | Evidence |
| --- | --- |
| Public UI status | `PUBLIC_UI_READY_WITH_NOTES` |
| Routes checked | `/`, `/?debug=1`, `/review`, `/visual-qa` |
| Desktop public queries | 14 passed |
| Mobile family checks | 13 passed at 390px |
| Public default | `/` renders public result UI by default |
| Debug preservation | `?debug=1`, Details, `/review`, `/visual-qa`, and feedback diagnostics remain preserved |
| Feedback preservation | feedback controls preserved on `/`; suppressed on `/review` and `/visual-qa` |
| Blocking issues | none |

Public result mode is answer-first. Successful public results render the answer
hero before actions, context/caveats sit near the answer, actions are
secondary, dense mobile tables use tighter shared padding and column priorities,
and public no-result diagnostics use one Details disclosure.

## 13. Build, Lint, And Frontend Test Evidence

| Item | Evidence |
| --- | --- |
| Frontend build | `npm --prefix frontend run build` passed after internal route lazy splitting |
| Vite chunk status | previous large-chunk warning cleared by splitting internal `/review` and `/visual-qa` route chunks from the public entry |
| Frontend lint | `npm --prefix frontend run lint` passed after the ReviewPage exhaustive-deps cleanup |
| ReviewPage lint warning | previous `react-hooks/exhaustive-deps` warning cleared |
| Full frontend suite | 25/25 files and 352/352 tests passed after the AppTheming test drift fix |
| AppTheming drift | test-only wait-gate drift fixed in `frontend/src/test/AppTheming.test.tsx` |
| Parser smoke | latest readiness docs record `make PYTEST=.venv/bin/pytest test-parser` passing 751 tests before division cleanup and 776 tests after division cleanup |
| Query smoke | latest readiness docs record `make PYTEST=.venv/bin/pytest test-query` passing 752 tests before division cleanup and 776 tests after division cleanup |

## 14. Docs And Return-Package Taxonomy Evidence

Durable docs own current product, operations, architecture, reference,
planning, and release-readiness facts. Return packages are wave receipts, not
source-of-truth docs.

Current durable taxonomy sources:

- `docs/index.md`
- `AGENTS.md`
- `docs/planning/raw-product/RETURN_PACKAGE_DEPENDENCY_CLEANUP_PREFLIGHT.md`

Policy:

- durable facts must be promoted into `docs/`
- exact return-package path dependencies should be cleared or replaced when a
  workstream closes
- archive sweeps are separate explicit cleanup passes
- return-package files may remain as historical receipts and handoff
  provenance

## 15. Remaining Deferred Items

These are accepted notes or deferred follow-ups, not launch blockers:

- screenshot diffing, committed screenshot baselines, and CI visual gating
- broader unsupported/no-result copy refinement
- admin dashboard or mutable triage overlay for feedback
- manual corpus conversion after feedback review
- dedicated feedback bucket/token as preferred future state
- `natural_query.py` extraction
- bucket-first intent classification investigation
- return-package archive sweep after durable docs no longer depend on exact
  paths
- branding/name change
- custom domain / production cutover work tracked outside the Raw Product
  release-readiness boundary
- continued internal horizontal scrolling for very wide result tables

## 16. Validation Boundary

This summary promotes existing evidence into durable docs. It does not rerun QA,
tests, frontend build, deployment smoke, or visual review. The validation
commands and artifacts listed above are the accepted evidence for the current
release boundary.
