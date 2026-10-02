# Exploratory Query Review

## Purpose

Use sample questions to discover missing or incorrect capabilities, then build
and verify those capabilities. Agents own this loop under the 2026-10-02 owner
direction in [AGENTS.md](../../AGENTS.md). Owner examples are optional input,
not an obligation to write or grade batches.

The existing exploratory runner captures what the engine returned. It does not
verify correctness. Backend `ok`, zero suspicious flags, and an apparently
reasonable table are not acceptance evidence by themselves.

## How It Differs From Raw QA

| Workflow | Input | Meaning |
| --- | --- | --- |
| Exploratory review | Sample questions without encoded expectations | Observe output and discover gaps. |
| Raw QA | Explicit status, scope, shape and numerical assertions | Check known regression contracts. |
| Capability delivery | Desired questions plus independently verified answers | Establish that useful functionality actually works. |

An existing Raw QA refusal can be a valid safety regression while the same
question remains an unfinished desired capability. Do not merge those outcomes
into one 'pass' or claim the rejection implemented the request.

## Run

Reuse existing samples/slices rather than ask for a new owner battery.
Ten questions is a convenient optional review size, not a required owner
session or a limit on agent execution. Choose a bounded batch that covers the
active capability; stop gathering examples once the defect is clear enough to
fix. A single concrete wrong-answer bug does not need three duplicates before
it can be repaired.

```bash
make exploratory-query-review-slice SLICE=001_player_last_n
make exploratory-query-review
```

The first runs one existing named slice; the second runs the full default input.
Direct equivalents and a named local scratch run:

```bash
.venv/bin/python tools/exploratory_query_review.py --slice 001_player_last_n
.venv/bin/python tools/exploratory_query_review.py --input qa/exploratory_query_samples.yaml
.venv/bin/python tools/exploratory_query_review.py --input qa/exploratory_query_samples.yaml --run-id latest_exploratory --overwrite-run-id
```

Use `--limit` for a prefix and `--top-rows` for displayed rows. Without `--slice`,
the runner uses the input file; `--all` is an explicit full-run marker. The
existing `--organize-existing-outputs` option organizes local outputs and is
not a prerequisite to delivery.

## Input Format

The runner's schema is unchanged. YAML/JSON inputs contain samples, not
acceptance expectations. A sample can also be a plain string.

```yaml
version: 1
samples:
  - id: lakers_road_record
    query: "Lakers road record last season"
    category: fragment_form
    priority: p2
    notes: "Inspect ordinary phrasing."
```

Do not put `expected_status`, `expected_route`, `hard_assertions`, Raw QA
acceptance metadata, or manual-review metadata into exploratory inputs.
The desired behavior belongs in the active delivery item; verified regression
expectations belong in the Raw QA corpus or appropriate existing tests.

## Slice Format

Existing slices live in `qa/exploratory/slices/`:

```yaml
id: 001_player_last_n
description: Player recent-game questions
review_goal: Inspect scope, computed values and displayed answers.
samples:
  - id: luka_recent
    query: "Luka stats last 10 games"
```

This is a schema example, not a request to overwrite the existing slice. The
optional `qa/exploratory/manifest.yaml` tracks slices for navigation; it is not
an expectation file. If an ID is absent from the manifest, the runner checks
the corresponding slice file. Reuse the existing organization, without
creating another parallel query framework.

## Generated Artifacts

Runs write generated snapshots beneath
`outputs/exploratory_query_review/<run_id>/`:

- `review.md`: compact query, answer and table presentation.
- `report.md`: diagnostics and supporting context.
- `report.jsonl`: structured query/result snapshots.
- `summary.json`: execution-status, route, display-flag and timing counts,
  not verified correctness counts.

The generated README/index and latest/slice navigation locate runs. Scratch
run names such as smoke, codex, debug, tmp, or audit are excluded from normal
recent-run navigation. Mutable named runs are local scratch, not immutable
acceptance receipts. Neither the compact preview nor its generated answer line
is proof that the browser rendered the same output; inspect actual rendering
when accepting a changed user-facing result.

## Reading The Search-Box Preview

The agent reads `review.md`, then uses diagnostics where needed. For each case:

1. Determine the intended subject, statistic/operation, time scope and
   conditions from the question and established product definitions.
2. Check the returned identity, sample, calculation, ordering, and presentation
   against qualified data or an independently calculated expectation.
3. Record whether a desired answer is verified, incorrect, missing, or blocked.
   Keep genuine ambiguity and intentionally negative inputs separate.
4. Group related gaps by cause and implement a reusable fix. Add unfamiliar
   wording and positive controls to check that the fix generalizes.

A legitimate missing feature is not classified as good because it refuses.
Do not relabel it as invalid, erase it from the delivery list, or wait for the
owner to approve the obvious need to make it answer. A real zero/empty answer
is valid only after confirming coverage and correct computation.

Useful compact working note:

```text
Question and intended answer:
Actual output:
Independent verification or specific missing evidence:
Missing/broken capability:
Next implementation action:
```

The existing report fields include the original query, search-box answer line,
public result sections, display shape, renderer patterns, scope/filter metadata,
and display flags. Use them to diagnose; do not treat them as an oracle.
Some report answer lines are report-only summaries of the backend payload.

## Promotion Path

An agent deliberately writes regression expectations after verification; do
not automatically copy current outputs into the corpus. Reuse
[Raw QA operations](raw_query_answer_qa.md) for commands and schema, and
[feature delivery rules](feature_promotion_rules.md) for completion.

- For a correct desired answer, add/extend relevant numeric, scope, shape,
  identity and condition assertions.
- For a bug/missing capability, implement it and verify the corrected answer,
  then retain those regressions.
- Preserve appropriate invalid-input, ambiguity and missing-data safety checks.
  When a temporary refusal becomes implemented support, update its old contract
  deliberately alongside evidence; never mass-relabel cases to make CI pass.
- Record independent agent review honestly in the PR/active queue. Do not set
  historical human-acceptance fields for work the owner did not review. Routine
  execution does not stop at a legacy human-review label.

After a verified delivery unit, merge/deploy under the existing rules and
continue to the next unfinished capability. Report useful answers gained and
remaining work, not the number of refusals the harness accepted.
