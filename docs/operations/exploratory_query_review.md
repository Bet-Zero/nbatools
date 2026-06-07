# Exploratory Query Review

## Purpose

Exploratory query review is an input-only workflow for trying natural-language
NBA query samples and inspecting what the shared query engine returned.

It is useful for:

- reviewing public-search phrasing before deciding whether it belongs in Raw QA
- collecting route/status/result-shape snapshots for manual triage
- spotting no-result, error, or suspicious rows without writing expectations up front

It is not a regression harness and it is not validation evidence.

## How It Differs From Raw QA

| Workflow | Source | Requires expectations | Output meaning |
| --- | --- | --- | --- |
| Raw QA corpus | `qa/raw_query_answer_corpus.yaml` | Yes: expected status, route, shape, filters, row counts, or hard assertions | Machine regression and product-review artifacts for curated cases |
| Exploratory query review | `qa/exploratory_query_samples.yaml` or another input-only sample file | No | Human-inspection snapshot only |

Exploratory samples must not contain `expected_status`, `expected_route`,
`hard_assertions`, Raw QA acceptance metadata, or manual-review metadata. Add
those only when a reviewed sample is promoted into the Raw QA corpus.

## Run

Default sample file:

```bash
make exploratory-query-review
```

Direct command:

```bash
.venv/bin/python tools/exploratory_query_review.py \
  --input qa/exploratory_query_samples.yaml
```

Named local review folder:

```bash
.venv/bin/python tools/exploratory_query_review.py \
  --input qa/exploratory_query_samples.yaml \
  --run-id latest_exploratory \
  --overwrite-run-id
```

Use `--limit` to run a prefix of the input file and `--top-rows` to control
how many section rows are copied into the Markdown review cards.

## Input Format

YAML and JSON are both supported. The preferred shape is:

```yaml
version: 1
samples:
  - id: lakers_road_record
    query: "Lakers road record last season"
    category: fragment_form
    priority: p2
    notes: "Inspect fragment phrasing."
```

A sample may also be a plain query string. The tool will assign IDs like
`sample_001`.

## Generated Artifacts

Each run writes:

```text
outputs/exploratory_query_review/<run_id>/report.jsonl
outputs/exploratory_query_review/<run_id>/report.md
outputs/exploratory_query_review/<run_id>/summary.json
```

- `report.jsonl` contains one structured row per sample, including the
  QueryResponse payload, route/status/query class, inferred shape, metadata,
  applied filters, sections, section summaries, review flags, and timing.
- `report.md` is the manual review worksheet. It includes each query, route,
  result status/reason, query class, answer summary, filters, notes/caveats,
  section row counts, capped top rows, and blank reviewer fields.
- `summary.json` contains counts by route, result status, query class,
  category, review flags, no-result cases, error cases, suspicious cases, and
  slowest cases.

Named folders with `--overwrite-run-id` are mutable local scratch paths. Do not
cite them as durable product evidence.

## Promotion Path

Promotion is manual:

1. Review `report.md` and decide whether the behavior is correct, buggy,
   intentionally unsupported, or needs follow-up.
2. For a verified case that should become regression coverage, add a new case
   to `qa/raw_query_answer_corpus.yaml`.
3. Add explicit expectations: status, route, shape, sections, row counts,
   filters, hard assertions, or unsupported-boundary proof as appropriate.
4. Add acceptance-family metadata only when the case belongs in public product
   review.
5. Run the relevant Raw QA command from [`raw_query_answer_qa.md`](raw_query_answer_qa.md).

An exploratory row is not promoted merely because it returned `ok`; the
reviewer must write the Raw QA expectations that define the contract.
