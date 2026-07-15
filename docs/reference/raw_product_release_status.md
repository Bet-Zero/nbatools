# Raw Product Release Status

## Current Status

Snapshot: 2026-06-08.

Raw Product QA is machine-clean for the current corpus and the current public
acceptance slice. The current public-acceptance human product review is closed
for the run recorded in the validation map. Machine results, product review,
and rendered UI review are separate evidence layers and must not be inferred
from one another.

| Evidence layer | Current status | Durable evidence pointer |
| --- | --- | --- |
| Full Raw QA corpus | Current inventory is 349 cases; a current machine run is required | The retained 314/314 run predates the current corpus and is historical only. [`query_validation_map.md`](../operations/query_validation_map.md#current-evidence) records the boundary. |
| `public_query_acceptance` slice | Current inventory is 134 cases; a current machine run is required | The retained 127/127 run predates the current slice and is historical only. [`query_validation_map.md`](../operations/query_validation_map.md#current-evidence) records the boundary. |
| Human product review | `human_review_pending` | The historical closure was not bound to the current commit, corpus content, output, data generation, reviewer, and representative rows. |
| Representative rendered UI review | Selected representative rendered-output queries passed; the slice 007 promotion reused existing top-performance and leaderboard renderers and required no new frontend layout spot check | [`query_validation_map.md`](../operations/query_validation_map.md#current-evidence) records the current rendered-review summary and slice evidence. |

The generated artifacts linked from the validation map are evidence snapshots.
They do not replace the durable workflow and support-boundary docs listed
below.

## Remaining Release Work

The following product-launch items remain open:

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
