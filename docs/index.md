# NBA Tools Documentation

This index lists durable source-of-truth documentation and curated audit
snapshots. Task plans, preflights, active review notes, and unpromoted generated
evidence do not belong in the durable documentation map.

## Start Here

0. [`reference/owner_guide.md`](reference/owner_guide.md) - plain-language guide to how the whole system works, written for the human owner
1. [`reference/quick_query_guide.md`](reference/quick_query_guide.md) - quick-start examples
2. [`reference/current_state_guide.md`](reference/current_state_guide.md) - verified shipped behavior
3. [`reference/query_catalog.md`](reference/query_catalog.md) - living catalog of supported query types and phrasing
4. [`reference/query_guide.md`](reference/query_guide.md) - full structured and natural query reference

## Agent Start / Change Impact Matrix

| Change type | Start-here doc | Likely files/areas | Required checks | Optional checks |
| --- | --- | --- | --- | --- |
| Docs-only change | [`operations/working_and_archive_policy.md`](operations/working_and_archive_policy.md) | `docs/`, `README.md`, `AGENTS.md` | `make docs-governance`; `git diff --check` | `make doctor` |
| Parser/routing change | [`operations/parser_routing_growth_guardrails.md`](operations/parser_routing_growth_guardrails.md) | `src/nbatools/commands/natural_query.py`, parser helpers, parser/query tests | `make test-parser`; `make test-query`; `make test-preflight` for high fan-in edits | `make test-smoke-all` |
| Backend route/data change | [`architecture/query_service_layer.md`](architecture/query_service_layer.md) | `src/nbatools/commands/`, `src/nbatools/query_service.py`, `docs/reference/data_contracts.md` | `make test-engine`; `make test-api` when response shape changes | `make test-preflight`; query smoke |
| Frontend render change | [`operations/ui_guide.md`](operations/ui_guide.md) | `frontend/src/`, `frontend/src/api/`, `src/nbatools/ui/dist/` | `npm --prefix frontend run build`; `npm --prefix frontend run lint`; `npm --prefix frontend test` | [`operations/frontend_visual_qa.md`](operations/frontend_visual_qa.md) |
| Corpus-only change | [`operations/raw_query_answer_qa.md`](operations/raw_query_answer_qa.md) | `qa/`, tracked fixtures under `qa/fixtures/` | Run the named corpus/QA slice; inspect generated product review when public acceptance is involved | `make docs-governance` if docs changed |
| Exploratory query review | [`operations/exploratory_query_review.md`](operations/exploratory_query_review.md) | `qa/exploratory/slices/`, `qa/exploratory_query_samples.yaml`, generated review snapshots | Run a 10-query slice with `make exploratory-query-review-slice SLICE=<slice_id>`; inspect `review.md` manually | Promote reviewed cases into Raw QA before treating them as regression coverage |
| Feedback-derived bug fix after future activation | [`operations/query_feedback_review.md`](operations/query_feedback_review.md) | feedback export/review artifacts, parser/route/engine area that owns the bug, QA cases | Follow triage/fix/closure workflow; run tests for touched subsystem | `make query-feedback-export`; Raw QA regression slice |
| New feature/query family promotion | [`operations/feature_promotion_rules.md`](operations/feature_promotion_rules.md) | data contract, route/result contract, parser, Raw QA, frontend when rendered, release docs | Complete promotion gates; run subsystem tests plus required QA and docs checks | `make doctor`; deployment smoke when data-backed |
| Route metadata/CLI diagnostic change | [`architecture/query_service_layer.md`](architecture/query_service_layer.md) | `src/nbatools/route_input_metadata.py`, `src/nbatools/cli_apps/queries.py`, `/routes` docs | Route metadata/CLI tests for touched path; `make test-api` if route list/API behavior changes | `make test-output` |
| Deployment/data-backed change | [`operations/deployment.md`](operations/deployment.md) | data contract docs, R2 sync path, deployment smoke, Vercel/R2 settings | `make doctor`; R2 dry-run/sync or documented head-object evidence; deployment smoke; `make docs-governance` | `make test-preflight` for runtime behavior changes |

## Reference

Current-state documentation, verified behavior, and data contracts.

- [`reference/owner_guide.md`](reference/owner_guide.md) - plain-language system overview for the human owner
- [`reference/current_state_guide.md`](reference/current_state_guide.md) - verified shipped behavior
- [`reference/quick_query_guide.md`](reference/quick_query_guide.md) - shortest path to trying queries
- [`reference/query_catalog.md`](reference/query_catalog.md) - supported query inventory and explicit boundaries
- [`reference/query_guide.md`](reference/query_guide.md) - comprehensive structured and natural query reference
- [`reference/natural_search_and_deep_tools_boundary.md`](reference/natural_search_and_deep_tools_boundary.md) - natural-search product boundary
- [`reference/raw_product_release_status.md`](reference/raw_product_release_status.md) - current Raw Product QA, review, and release-cutover status
- [`reference/data_catalog.md`](reference/data_catalog.md) - dataset inventory
- [`reference/data_contracts.md`](reference/data_contracts.md) - dataset-level contracts and source boundaries
- [`reference/result_contracts.md`](reference/result_contracts.md) - target engine result contracts
- [`reference/result_contracts/core_result_table_contracts.md`](reference/result_contracts/core_result_table_contracts.md) - locked route/result/table display contracts
- [`reference/system_conventions.md`](reference/system_conventions.md) - data format and naming conventions

## Architecture

Long-lived engineering conventions and internal layer design.

- [`architecture/project_conventions.md`](architecture/project_conventions.md) - engineering and documentation rules
- [`architecture/api_layer.md`](architecture/api_layer.md) - FastAPI HTTP layer
- [`architecture/query_service_layer.md`](architecture/query_service_layer.md) - query service interface
- [`architecture/structured_result_layer.md`](architecture/structured_result_layer.md) - structured result object design
- [`architecture/design_system.md`](architecture/design_system.md) - visual foundation reference
- [`architecture/parser/overview.md`](architecture/parser/overview.md) - parser framing and principles
- [`architecture/parser/specification.md`](architecture/parser/specification.md) - parser component specification
- [`architecture/parser/examples.md`](architecture/parser/examples.md) - parser example library

## Operations

Runbooks and durable workflow policies.

- [`operations/pipeline_runbook.md`](operations/pipeline_runbook.md) - data pipeline operations
- [`operations/deployment.md`](operations/deployment.md) - Cloudflare R2 and Vercel deployment
- [`operations/query_feedback_privacy.md`](operations/query_feedback_privacy.md) - deferred manual-feedback release boundary and future privacy, retention, activation, and deletion contract
- [`operations/query_feedback_review.md`](operations/query_feedback_review.md) - dormant query-feedback review workflow for a future approved activation
- [`operations/exploratory_query_review.md`](operations/exploratory_query_review.md) - input-only natural-query review workflow
- [`operations/query_smoke_workflow.md`](operations/query_smoke_workflow.md) - natural-query smoke workflow
- [`operations/raw_query_answer_qa.md`](operations/raw_query_answer_qa.md) - Raw QA operations
- [`operations/query_validation_map.md`](operations/query_validation_map.md) - validation-layer map and generated-evidence scoreboard
- [`operations/frontend_visual_qa.md`](operations/frontend_visual_qa.md) - frontend Visual QA workflow
- [`operations/working_and_archive_policy.md`](operations/working_and_archive_policy.md) - task-artifact lifecycle policy
- [`operations/feature_promotion_rules.md`](operations/feature_promotion_rules.md) - product-capability promotion rules
- [`operations/parser_routing_growth_guardrails.md`](operations/parser_routing_growth_guardrails.md) - parser/routing growth guardrails
- [`operations/parser_examples_full_sweep_protocol.md`](operations/parser_examples_full_sweep_protocol.md) - parser example sweep protocol
- [`operations/ui_guide.md`](operations/ui_guide.md) - web UI setup and component reference

## Audits

Curated audit snapshots preserve bounded historical evidence. They do not
replace current-state references, release decisions, or repeatable runbooks.

- [`audits/2026-07-15-browser-release-review/README.md`](audits/2026-07-15-browser-release-review/README.md) - retained desktop/mobile browser release review; execution complete, acceptance blocked, human review pending
- [`audits/2026-07-19-browser-release-review/README.md`](audits/2026-07-19-browser-release-review/README.md) - exact clean-current-main D-11 browser package; machine pass and explicit owner UI approval, with final Queue D acceptance still separate

## Documentation Rules

- Keep stable product behavior and contracts in `reference/`.
- Keep long-lived engineering decisions in `architecture/`.
- Keep repeatable workflows and policies in `operations/`.
- Keep temporary task artifacts outside the durable docs tree according to
  [`operations/working_and_archive_policy.md`](operations/working_and_archive_policy.md).
- Treat generated reports, screenshots, and manifests as evidence artifacts,
  not durable source of truth.
- Run `make docs-governance` after documentation changes.
