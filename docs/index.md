# NBA Tools Documentation

Durable behavior, architecture and operational references live here. Active
execution follows [AGENTS.md](../AGENTS.md) and [the roadmap](../ROADMAP.md).
The 2026-10-02 owner delegation makes agents responsible for routine technical
review; historical human-acceptance records retain their original meaning.

## Start Here

1. [Owner's guide](reference/owner_guide.md) - product purpose, owner role and useful progress reporting.
2. [Quick query guide](reference/quick_query_guide.md) - examples to try.
3. [Current state](reference/current_state_guide.md) - verified shipped behavior, not the future scope limit.
4. [Query catalog](reference/query_catalog.md) - current supported phrasing and boundaries.
5. [Full query guide](reference/query_guide.md) - structured/natural query reference.

## Agent Start / Change Impact Matrix

| Change | Start here | Required checks |
| --- | --- | --- |
| Docs only | [Lifecycle policy](operations/working_and_archive_policy.md) | `make docs-governance`; `git diff --check`. |
| Parser/routing | [Parser guardrails](operations/parser_routing_growth_guardrails.md) | Relevant parser/query tests, meaningful positive and collision cases; broad candidate gate for shared/high fan-in changes. |
| Backend calculation/data | [Query service](architecture/query_service_layer.md), [data contracts](reference/data_contracts.md) | Engine tests, independent numerical/scope checks; API checks when affected. |
| Frontend | [UI guide](operations/ui_guide.md) | Build/lint/test; actual rendered checks for changed copy/layout. |
| Corpus | [Raw QA operations](operations/raw_query_answer_qa.md) | Named failing QA cases/slice; independently verify intended answers, not only expected status. |
| Sample-query discovery | [Exploratory review](operations/exploratory_query_review.md) | Agent-managed bounded samples -> diagnosis -> implementation -> verified regressions; no mandatory owner ten-query session. |
| New capability | [Feature delivery rules](operations/feature_promotion_rules.md) | Complete data/calculation/input/output/deployment checks applicable to the change. Refusal cannot complete a desired-answer task. |
| Route metadata/CLI | [Query service](architecture/query_service_layer.md) | Affected route/CLI/API contract tests. |
| Deployment/data publication | [Deployment operations](operations/deployment.md) | Configured generation/data availability and feature-specific deployed verification. |
| Future feedback-derived fix | [Feedback review](operations/query_feedback_review.md) | Activation/privacy rules first, then relevant behavior checks. Feedback persistence remains deferred. |

Use focused checks during iteration and existing integration gates at the
candidate boundary. Machine, independent-agent and actual human review are
separate evidence claims; do not fabricate one from another.

## Reference

- [Owner's guide](reference/owner_guide.md)
- [Current state](reference/current_state_guide.md)
- [Quick query guide](reference/quick_query_guide.md)
- [Query catalog](reference/query_catalog.md)
- [Full query guide](reference/query_guide.md)
- [Natural search versus deep tools](reference/natural_search_and_deep_tools_boundary.md)
- [Raw product release status](reference/raw_product_release_status.md)
- [Known issues](reference/known_issues.md)
- [Data catalog](reference/data_catalog.md)
- [Data contracts](reference/data_contracts.md)
- [Result contracts](reference/result_contracts.md)
- [Core result/table contracts](reference/result_contracts/core_result_table_contracts.md)
- [System conventions](reference/system_conventions.md)

## Architecture

- [Project conventions](architecture/project_conventions.md)
- [API layer](architecture/api_layer.md)
- [Query service](architecture/query_service_layer.md)
- [Structured results](architecture/structured_result_layer.md)
- [Design system](architecture/design_system.md)
- [Parser overview](architecture/parser/overview.md)
- [Parser specification](architecture/parser/specification.md)
- [Parser examples](architecture/parser/examples.md)
- [Leaderboard metric boundary](architecture/parser/leaderboard_metric_boundary.md)
- [Compound-event routing](architecture/parser/compound_event_routing.md)

## Operations

- [Data pipeline](operations/pipeline_runbook.md)
- [Deployment](operations/deployment.md)
- [Observability](operations/observability.md)
- [Recovery](operations/recovery.md)
- [Feedback privacy and activation](operations/query_feedback_privacy.md)
- [Feedback review](operations/query_feedback_review.md)
- [Exploratory query review](operations/exploratory_query_review.md)
- [Query smoke workflow](operations/query_smoke_workflow.md)
- [Raw QA operations](operations/raw_query_answer_qa.md)
- [Validation map and dated evidence](operations/query_validation_map.md)
- [Filter sweep](operations/filter_execution_sweep.md)
- [Committed query fixture](operations/query_fixture_dataset.md)
- [Frontend visual QA](operations/frontend_visual_qa.md)
- [Working and archive policy](operations/working_and_archive_policy.md)
- [Feature delivery rules](operations/feature_promotion_rules.md)
- [Parser guardrails](operations/parser_routing_growth_guardrails.md)
- [Parser example sweep protocol](operations/parser_examples_full_sweep_protocol.md)
- [UI guide](operations/ui_guide.md)

## Audits

These are historical snapshots, not current readiness or new owner assignments.

- [July 15 browser review](audits/2026-07-15-browser-release-review/README.md)
- [July 19 browser review](audits/2026-07-19-browser-release-review/README.md)
- [July 21 Queue D acceptance](audits/2026-07-21-queue-d-final-acceptance/README.md)

## Documentation Rules

Use reference docs for verified behavior, architecture docs for long-lived
engineering decisions, and operations docs for repeatable procedures/policy.
Task plans and handoffs follow the lifecycle policy and are not durable product
truth. Generated artifacts are evidence snapshots. Update this index when
adding/moving durable docs and run `make docs-governance` after docs changes.
