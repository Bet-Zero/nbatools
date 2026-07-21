# Raw Product Release Status

## Current Status

Snapshot: 2026-07-21.

The current public-acceptance slice is machine-clean and its human product
review is closed for the exact run recorded in the validation map. The broader
349-case corpus still requires a current full run. Machine results, product
review, and rendered UI review are separate evidence layers and must not be
inferred from one another.

| Evidence layer | Current status | Durable evidence pointer |
| --- | --- | --- |
| Full Raw QA corpus | Current inventory is 349 cases; a current machine run is required | The retained 314/314 run predates the current corpus and is historical only. [`query_validation_map.md`](../operations/query_validation_map.md#current-evidence) records the boundary. |
| `public_query_acceptance` slice | Current 134/134 machine run passed with zero failed or suspicious cases | [`query_validation_map.md`](../operations/query_validation_map.md#current-evidence) records the exact commit, generation, and generated closure-validation path. |
| Human product review | `human_review_complete` for `d10_final_83889c6` | John Matthew approved the package-level 37-representative-row review on 2026-07-15; exact closure-integrity validation passed with zero errors. |
| Representative rendered UI review | `human_review_complete` for `d11_final_4b894e6_20260719`; machine execution and acceptance passed with zero blockers | John Matthew approved the exact four-image desktop/mobile package on 2026-07-19. The [2026-07-19 browser release review](../audits/2026-07-19-browser-release-review/README.md) binds the decision to the clean source commit, unmodified machine receipt, and image hashes. |

The generated artifacts linked from the validation map are evidence snapshots.
They do not replace the durable workflow and support-boundary docs listed
below.

## Queue D Acceptance And Remaining Release Work

Queue D was accepted by John Matthew on 2026-07-21 for the current documented
product boundary after final current-main CI and the 17-check combined evidence
run passed. The exact decision and evidence binding are retained in the
[Queue D final acceptance audit](../audits/2026-07-21-queue-d-final-acceptance/README.md).

Production data publication, readiness/query smoke, internal-route isolation,
and edge admission proof are complete. Manual feedback persistence is an
optional future capability and remains disabled; its bucket, credentials,
lifecycle, legal/notice process, deletion channel, and SLA are not current
release requirements.

The following broader product-launch work is outside Queue D:

- a current full run of the 349-case Raw QA corpus
- branding and final product name
- final production domain
- custom-domain production cutover

The tracked Track B Phase N4 continuation owns the remaining domain and cutover
work.

## Durable Support Docs

- [`../operations/query_validation_map.md`](../operations/query_validation_map.md)
  - current corpus, slice, generated-artifact scoreboard, and reporting terms
- [`../operations/raw_query_answer_qa.md`](../operations/raw_query_answer_qa.md)
  - machine regression and human product-review workflow
- [`../operations/frontend_visual_qa.md`](../operations/frontend_visual_qa.md)
  - rendered UI and screenshot-review workflow
- [`../operations/query_feedback_review.md`](../operations/query_feedback_review.md)
  - feedback-review cadence and triage workflow
- [`query_catalog.md`](query_catalog.md)
  - supported natural-query inventory and explicit boundaries
- [`query_guide.md`](query_guide.md)
  - structured and natural query reference
- [`natural_search_and_deep_tools_boundary.md`](natural_search_and_deep_tools_boundary.md)
  - public natural-search product boundary

## Historical Count Rule

Older Raw Product QA counts such as `67/67`, `294`, and `246` are historical
snapshots. Do not cite them as the current release status. Use
[`../operations/query_validation_map.md`](../operations/query_validation_map.md)
for the latest verified scoreboard.
