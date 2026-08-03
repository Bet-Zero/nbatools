# Full Raw QA Package Acceptance — 2026-07-24

## Final Decision

John Matthew, project owner, approved the full Raw QA corpus package on
2026-07-24 with the exact statement `APPROVE FULL RAW QA PACKAGE
20260724T081634Z`.

The [owner acceptance receipt](owner_acceptance.yaml) binds that decision to
run ID `20260724T081634Z`, source commit
`28d73f0fbee1dd708a8cbee16956bd54b910269f` (clean tree at run time), data
generation `queue-d-local-7e55c810-20260715`, and the corpus/case/output
hashes recorded in the receipt.

## What This Closes

This is a package-level human-review gate for the full 351-case Raw QA
corpus:

| Metric | Result |
| --- | ---: |
| Cases | 351 |
| Machine expectations passed | 351 |
| Failed cases | 0 |
| Family coverage | complete |
| Suspicious result flags | 0 |

Per the receipt's own `scope_boundary`: this closes the full Raw QA
package-level human-review gate only. It is a package-level decision, not a
claim that all 351 rows were individually reviewed row-by-row — the same
distinction the [D-10 closure](../../operations/query_validation_map.md)
draws for the `public_query_acceptance` slice. It does not grant broader
release acceptance and does not waive the Queue E live-recovery drill (see
the separate [2026-08-02 Queue E scope decision](../2026-08-02-queue-e-scope-decision/README.md),
which has since made that drill intentionally out of scope rather than
pending).

## Durable Evidence

- [Owner acceptance receipt](owner_acceptance.yaml) (copied from the
  full-system-review working evidence for durable citation)
- Generated run artifacts remain at
  `outputs/raw_query_answer_qa/20260724T081634Z/` (gitignored generated
  evidence, not itself durable — the receipt above is the durable record)
