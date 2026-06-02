# NBA Tools Documentation

This index lists durable source-of-truth documentation only. Task plans,
preflights, review notes, generated evidence, and historical receipts do not
belong in the durable documentation map.

## Start Here

1. [`reference/quick_query_guide.md`](reference/quick_query_guide.md) - quick-start examples
2. [`reference/current_state_guide.md`](reference/current_state_guide.md) - verified shipped behavior
3. [`reference/query_catalog.md`](reference/query_catalog.md) - living catalog of supported query types and phrasing
4. [`reference/query_guide.md`](reference/query_guide.md) - full structured and natural query reference

## Reference

Current-state documentation, verified behavior, and data contracts.

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
- [`operations/query_feedback_review.md`](operations/query_feedback_review.md) - query feedback review workflow
- [`operations/query_smoke_workflow.md`](operations/query_smoke_workflow.md) - natural-query smoke workflow
- [`operations/raw_query_answer_qa.md`](operations/raw_query_answer_qa.md) - Raw QA operations
- [`operations/query_validation_map.md`](operations/query_validation_map.md) - validation-layer map and generated-evidence scoreboard
- [`operations/frontend_visual_qa.md`](operations/frontend_visual_qa.md) - frontend Visual QA workflow
- [`operations/working_and_archive_policy.md`](operations/working_and_archive_policy.md) - task-artifact lifecycle policy
- [`operations/feature_promotion_rules.md`](operations/feature_promotion_rules.md) - product-capability promotion rules
- [`operations/parser_routing_growth_guardrails.md`](operations/parser_routing_growth_guardrails.md) - parser/routing growth guardrails
- [`operations/parser_examples_full_sweep_protocol.md`](operations/parser_examples_full_sweep_protocol.md) - parser example sweep protocol
- [`operations/ui_guide.md`](operations/ui_guide.md) - web UI setup and component reference

## Documentation Rules

- Keep stable product behavior and contracts in `reference/`.
- Keep long-lived engineering decisions in `architecture/`.
- Keep repeatable workflows and policies in `operations/`.
- Keep temporary task artifacts outside the durable docs tree according to
  [`operations/working_and_archive_policy.md`](operations/working_and_archive_policy.md).
- Treat generated reports, screenshots, and manifests as evidence artifacts,
  not durable source of truth.
- Run `make docs-governance` after documentation changes.
