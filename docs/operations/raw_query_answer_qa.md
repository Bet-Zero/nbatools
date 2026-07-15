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

## Output Modes

Default runs use timestamped UTC run IDs and write durable evidence-shaped
artifacts under:

```text
outputs/raw_query_answer_qa/<run_id>/
```

Use timestamped runs for handoffs, historical evidence, comparison baselines,
and any path that may be cited outside the immediate local review loop.

For repeated local review of the public acceptance slice, use a named latest
folder with explicit overwrite:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --run-id latest_public_query_acceptance \
  --overwrite-run-id \
  --fail-on-expectation-failure
```

This writes to:

```text
outputs/raw_query_answer_qa/latest_public_query_acceptance/
```

`--overwrite-run-id` is only for direct child folders under
`outputs/raw_query_answer_qa/`. It deletes and recreates that named run folder
before writing the new artifacts. Do not use latest folders as durable source
of truth, product evidence, or long-lived doc references; they are mutable
local review scratch paths.

## Run Variants

Use the direct harness command when selecting a specific scope or when a
non-zero exit is required for expectation failures.

Full corpus:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --fail-on-expectation-failure
```

Named slice:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice product_boundaries \
  --fail-on-expectation-failure
```

Single case or a small case set:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --case record_when_jokic_triple_double \
  --fail-on-expectation-failure
```

Prior failed cases:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --failed-from outputs/raw_query_answer_qa/<prior_run_id>/summary.json \
  --fail-on-expectation-failure
```

`--failed-from` also accepts a prior `report.jsonl`. It selects failed
expectation cases from the prior artifact.

Non-gating comparison against a prior run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --case record_when_jokic_triple_double \
  --compare-to outputs/raw_query_answer_qa/<prior_run_id>/report.jsonl \
  --fail-on-expectation-failure
```

`--compare-to` also accepts a prior `summary.json`. It adds comparison metadata
to `summary.json` and a concise comparison section to `report.md`. Comparison
metadata does not change the harness exit status.

### Selection And Failure Behavior

- `--case`, `--slice`, and `--failed-from` may be repeated and compose as a
  union.
- Slice names resolve from `qa/harness_slices/<name>.yaml`; direct slice YAML
  paths are also accepted.
- Selected case IDs are deduplicated and run in corpus order.
- Unknown case IDs fail loudly.
- `--limit` applies after selection.
- With no selection option, the full corpus runs.
- If `--failed-from` selects zero failed cases and no other selection is
  supplied, the harness writes a zero-case report instead of broadening to the
  full corpus.
- Every run writes its artifacts before exit. With
  `--fail-on-expectation-failure`, failed expectations produce a non-zero exit.
  Without that flag, failed IDs remain visible in the artifacts but do not make
  the command exit non-zero.
- Use `--run-id <label>` when a stable human-facing artifact path is useful.
  The label must be a folder name, not a path. Existing named run directories
  are refused unless `--overwrite-run-id` is also supplied.

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

`product_review.md` is a human-readable review artifact generated from the
scope of that specific harness run. It helps inspect family coverage,
representative answers, suspicious rows, and product decisions. It is not a
separate corpus or a broader validation result.

Each `report.jsonl` row records `duration_seconds`. `summary.json` includes
`slowest_cases`, and `report.md` includes a slowest-case table.

For the current corpus and slice scoreboard, latest known artifact paths, and
precise reporting terminology, use:

```text
docs/operations/query_validation_map.md
```

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

## Tracked Review Closure

The public acceptance family registry
(`qa/raw_query_answer_acceptance_families.yaml`) may include top-level
`review_closure` metadata for an approved run or slice. The Raw QA harness uses
that tracked metadata only when the generated run matches every closure binding:

- exact run ID and scope
- full source commit with a clean tracked worktree
- corpus SHA-256, ordered case IDs, and selected-case-content SHA-256
- deterministic review-output SHA-256
- one request-pinned immutable data generation (`legacy` cannot close review)
- named reviewer and the exact reviewed representative-case IDs
- a passed or explicitly not-applicable UI spot check

A complete closure with any mismatch fails the harness even when machine
expectations pass. Changed same-count corpora and overwritten mutable run aliases
therefore cannot inherit an older closure. `human_review_pending` is the only
valid state when no exact artifact has been certified. This preserves the
distinction between machine passing, coverage complete, human-review complete,
and UI-review status.

Because adding a tracked closure changes the repository commit, validate a newly
reviewed clean artifact with a separate receipt rather than editing the source
tree before rerunning it:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --run-id <reviewed_run_id> \
  --out <separate_validation_output_root> \
  --review-closure <review_closure_receipt.yaml> \
  --fail-on-expectation-failure
```

The receipt may be the closure mapping itself or wrap it under
`review_closure:`. Keep the reviewed artifact immutable. The validation rerun
must use the same clean commit, run ID, corpus, case selection, data generation,
and deterministic answers; otherwise closure integrity fails.

## Human + ChatGPT Review

After running the public slice, send ChatGPT:

```text
outputs/raw_query_answer_qa/<run_id>/product_review.md
```

The artifact ends with an exact prompt block. Use it as written. ChatGPT helps
identify corpus gaps, suspicious outputs, and product decisions. The user owns
the final product decision. Agents execute approved follow-up only.

## Corpus-Wave Handoff Receipts

When a public corpus-wave task needs a handoff receipt, keep it task-scoped
and follow [`working_and_archive_policy.md`](working_and_archive_policy.md).
Do not create a standalone top-level return-package folder. The receipt must
state whether the corpus itself was reviewed or only the machine expectations
passed. Use exactly one:

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
