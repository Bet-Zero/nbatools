# NBA Tools Completion Program — Plan

Task-coordination artifact. Not durable documentation. Durable facts belong in
`docs/` per [`working_and_archive_policy.md`](../../docs/operations/working_and_archive_policy.md).

## Owner-level objective

NBA Tools must never discard a meaningful part of a question and then answer a
different, easier question confidently.

For every meaningful requested condition the product must do exactly one of:

1. execute it,
2. refuse it clearly, or
3. request clarification.

Silently dropping a condition and substituting another answer is forbidden.

## Baselines

| Phase | What it established | State |
| --- | --- | --- |
| Phase 0A | Cloud baseline | completed machine baseline |
| Phase 0B | Local full-data baseline | completed machine baseline |

- Baseline commit: `5554a3affd0f112315938d684b4025a688b922fb` (`main`)
- Data generation (pinned, immutable): `queue-d-local-7e55c810-20260715`
- Raw QA corpus at baseline: 351 cases

### Machine-passing is not human acceptance

Phase 0A/0B recorded **351/351 machine-passing** on the Raw QA corpus. That is a
machine result only. The public acceptance family registry
(`qa/raw_query_answer_acceptance_families.yaml`) still declares
`review_closure.state: human_review_pending`. Do not infer `human_reviewed` or
`public_accepted` from a clean machine run, and do not treat 351/351 as owner
acceptance of the answers.

## Phase structure

- **Phase 0** — baselines (complete).
- **Phase 1** — trust repair. Ordered queue in
  [`PHASE_1_TRUST_QUEUE.md`](PHASE_1_TRUST_QUEUE.md). Each item is one bounded PR.
- Later phases are not drafted yet. Phase 1's final queue item must draft the
  next queue or write an explicit review-handoff.

## Guardrails for every Phase 1 item

- One bounded PR per queue item. No dependency updates, CI restructuring,
  branch cleanup, season refresh work, unrelated parser expansion, or general
  refactoring mixed in.
- Concept-level guards, never phrase blacklists.
- Never invent a metric to satisfy an unresolved question.
- Requested-but-unexecuted filters must never render as applied filters.
- Concept-level test assertions, not snapshots of whatever the app emits today.
- Follow AGENTS.md test selection. High-fan-in natural-query routing changes do
  not rely on testmon alone.

## Completion rule

The program is not finished when one queue item merges. Phase 1 is complete only
when every item in `PHASE_1_TRUST_QUEUE.md` is checked and the queue's final item
has drafted the continuation path.
