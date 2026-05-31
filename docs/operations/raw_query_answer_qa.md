# Raw Query Answer QA Operations

## Purpose

Raw Query Answer QA uses one curated corpus for two separate jobs:

1. machine regression checks
2. human + ChatGPT product review

A passing machine run does not mean feature-family coverage is complete,
representative outputs were reviewed, or a family is public accepted.

## Run The Public Acceptance Slice

From the repo root:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --fail-on-expectation-failure
```

The existing full-corpus command remains:

```bash
make raw-query-answer-qa
```

## Generated Artifacts

Each run writes:

```text
outputs/raw_query_answer_qa/<run_id>/report.jsonl
outputs/raw_query_answer_qa/<run_id>/report.md
outputs/raw_query_answer_qa/<run_id>/summary.json
outputs/raw_query_answer_qa/<run_id>/product_review.md
outputs/raw_query_answer_qa/<run_id>/product_review.json
```

Use `report.md` and `report.jsonl` for case-level regression drill-down. Use
`product_review.md` for feature-family product review.

## Product-Review Inputs

The family registry is:

```text
qa/raw_query_answer_acceptance_families.yaml
```

Cases opt into product review through the optional `acceptance` mapping in:

```text
qa/raw_query_answer_corpus.yaml
```

Validated fields:

| Field | Purpose |
| --- | --- |
| `acceptance.family` | Stable feature-family registry ID |
| `acceptance.variant` | Coverage-grid role |
| `acceptance.concept` | Narrow capability or boundary |
| `acceptance.review_required` | Includes the case as a representative review card |
| `acceptance.review_role` | `representative`, `supporting`, `boundary`, or `decision` |
| `acceptance.public_surface` | Marks a public-surface case during metadata rollout |
| `acceptance.no_broad_fallback` | Requires explicit machine proof that scope was not widened |
| `acceptance.sibling_of` | Links an inverse or adjacent case |
| `acceptance.intent_model` | Product-level intent expected from the phrase |
| `acceptance.qualifier_model` | Product-level qualifiers preserved or rejected |

Existing `family`, `variant`, and `no_broad_fallback` tags remain valid during
the staged metadata migration.

## No-Broad-Fallback Enforcement

`acceptance.no_broad_fallback: true` is an enforced metadata contract.

Supported cases must pin an exact `expected_status`, an `expected_route`, and
at least one scoped contract such as filters, sections, row counts, or hard
assertions.

Unsupported cases must pin an exact non-`ok` status, an explicit
`expected_route` including `null` for unrouted cases, and an explicit boundary
contract such as `expected_reason`, empty sections, filters, or hard
assertions. When a route exposes `metadata.unsupported_filters`, keep that hard
assertion.

Descriptive-only metadata fails before query execution.

## Status Meanings

| Status | Meaning |
| --- | --- |
| `machine_passed` | Selected case expectations passed. |
| `human_reviewed` | A person reviewed representative outputs and coverage questions. |
| `public_accepted` | Machine checks pass, the variant matrix is resolved, no product decision blocks the family, and representative outputs were human-reviewed. |

These statuses are independent. Do not infer `human_reviewed` or
`public_accepted` from a clean machine run.

## Human + ChatGPT Review

After running the public slice, send ChatGPT:

```text
outputs/raw_query_answer_qa/<run_id>/product_review.md
```

The artifact ends with an exact prompt block. Use it as written. ChatGPT helps
identify corpus gaps, suspicious outputs, and product decisions. The user owns
the final product decision. Agents execute approved follow-up only.

## Corpus-Wave Return Packages

Every public corpus-wave return package must state whether the corpus itself
was reviewed or only the machine expectations passed. Use exactly one:

```text
machine_only
human_review_pending
human_review_complete
human_review_complete_with_followup
```

Include:

- feature-family coverage changes
- cases added, reused, or retagged
- representative outputs reviewed
- gaps intentionally left
- product decisions needed
- behavior failures found
- validation commands and generated `product_review.md` path
