# Filter Execution Sweep Operations

## Purpose

The filter execution sweep answers one narrow question: when the app accepts a
filter phrase, does the filter actually change the answer?

It asks every configured question twice — once with the filter phrase appended,
once without — and compares the data that comes back. It needs no
hand-verified answer, so it covers far more phrasings than
`qa/raw_query_answer_corpus.yaml`. That corpus remains the stronger check: it
verifies the numbers are *correct*, not merely that filtering happened.

Implementation: `tools/filter_execution_sweep.py`.
Configured matrix: `qa/filter_execution_sweep.yaml`.

## Run It

```bash
.venv/bin/python tools/filter_execution_sweep.py
```

Narrow to specific filters, and write machine-readable evidence:

```bash
.venv/bin/python tools/filter_execution_sweep.py \
  --only position_guards,last_n \
  --json <evidence_path>.json
```

## What Makes A Comparison Comparable

The unfiltered question is the *control*. The filtered question can only be
judged against a control that actually produced an answer to compare with.

A control is **comparable** when all of these hold:

- the query did not raise;
- `result_status` is `ok`;
- at least one result frame carries at least one row.

Anything else leaves nothing to compare against: a refusal, a typed error,
missing local data, uncovered season coverage, or an empty answer. Two
unpopulated answers fingerprint identically no matter what the filter did, so
treating that as evidence would manufacture a clean verdict out of missing
data.

Comparison uses a stable fingerprint of the returned data frames (`games`,
`leaders`, `streaks`, `summary`, `splits`, `comparison`) — shape plus a digest
of the CSV rendering.

## Row Classifications

Every configured pair lands in exactly one bucket.

| Verdict | Meaning | Comparable |
| --- | --- | --- |
| `APPLIED` | The control was populated and the filtered answer's data differed. The filter did something. | yes |
| `REFUSED` | The control was populated and the filtered question came back non-`ok` (a typed `no_result` or a typed `error`). The app declined, honestly. | yes |
| `LIED` | The control was populated, the filtered data was identical to it, **and** a badge claimed *this* filter was applied. | yes |
| `DROPPED` | The control was populated, the filtered data was identical to it, and nothing was claimed. The words were silently ignored. | yes |
| `NO_SIGNAL` | The control was not comparable. Nothing about this filter was tested. | **no** |
| `ERROR` | The filtered query or the control query raised an exception. `error_source` names the side. | **no** |

A badge only counts when it names the filter under test. An unrelated badge
from a threshold in the same query does not make an unchanged answer a lie.

### NO_SIGNAL semantics

`NO_SIGNAL` is not a soft pass and not a refusal. It is the absence of
evidence. A `NO_SIGNAL` row proves nothing about whether that filter is honest,
and it is excluded from the comparable counts and from the run verdict.

Each `NO_SIGNAL` row records why, as `no_signal_reason`:

| Reason | Cause |
| --- | --- |
| `control_no_result:<reason>` | The control refused; `<reason>` is the typed result reason, such as `no_data` or `unsupported`. |
| `control_error:<reason>` | The control returned a typed `error` status. |
| `control_empty_result` | The control returned `ok` with no populated rows. |
| `control_execution_error` | Reserved; a control that raises is classified `ERROR`, not `NO_SIGNAL`. |

The most common cause is a data gap rather than a code gap. Season coverage
matters: a filter that reads a dataset which does not cover the seed's season
produces an unpopulated control. Re-run against a covered season before
concluding anything about the filter itself.

### DROPPED policy is unchanged

`DROPPED` rows are reported in full and do not fail the run. That is the same
policy the sweep has always had; this document records it rather than changing
it. Whether silent drops should block acceptance is a separate product
decision.

## Run-Level Status And Exit Codes

| Status | Condition | Exit |
| --- | --- | ---: |
| `PASS` | At least one comparable row, no `LIED`, no `ERROR`, no `NO_SIGNAL`. | 0 |
| `PASS_WITH_GAPS` | At least one comparable row, no `LIED`, no `ERROR`, and one or more `NO_SIGNAL` rows. | 0 |
| `FAIL` | One or more `LIED` rows, or one or more `ERROR` rows. | 1 |
| `NO_SIGNAL` | Zero comparable rows. No verdict about filters was earned. | 2 |

`FAIL` outranks `NO_SIGNAL`: an execution error is a verified defect worth
surfacing even in a run that compared nothing.

`PASS_WITH_GAPS` exits zero, and the terminal summary states explicitly that
the verdict covers the comparable rows only — never the full configured
matrix. Partial coverage is reported, not rounded up.

A `NO_SIGNAL` run prints a prominent no-signal result, lists why each
comparison was not meaningful, and does **not** print `APPLIED` / `REFUSED` /
`LIED` / `DROPPED` counts as headline results. In such a run those counts are
zero only because nothing was measured; presenting them as verified zeroes
would be the exact false-green this contract exists to prevent.

### Why an all-no-data run is not a pass

Before this contract, a sweep against an empty data root classified every
comparison as an honest refusal and exited zero — "no lies found" from a run
that had compared nothing at all. A run with no populated control has not
tested filter execution. It now exits 2.

## Machine-Readable Evidence

`--json` writes a versioned object. Schema version 2 replaced the bare rows
list; consumers should read `schema_version` and then `summary` / `rows`.

```json
{
  "schema_version": 2,
  "summary": { "...": "run-level counts and identity" },
  "rows": [ { "...": "one entry per configured comparison" } ]
}
```

`summary` records:

| Field | Meaning |
| --- | --- |
| `status` | `PASS`, `PASS_WITH_GAPS`, `FAIL`, or `NO_SIGNAL` |
| `exit_code` | The process exit code for that status |
| `configured_comparisons` | Size of the configured matrix |
| `executed_comparisons` | Rows actually run |
| `comparable_comparisons` | Rows with a populated control — the only rows the verdict covers |
| `no_signal_comparisons` | Rows that tested nothing |
| `verdict_counts` | Count per row classification |
| `no_signal_reason_counts` | Why the untested rows were untested |
| `data_generation` | The immutable data generation pinned for the whole run |
| `config`, `config_sha256` | The exact configured matrix |
| `only` | Filter selection, when narrowed |
| `started_at`, `completed_at` | UTC run bounds |

Each row records `seed`, `filter`, `query`, `control_query`, `verdict`,
`comparable`, `no_signal_reason`, `error_source`, `route`, `badges`, `error`,
`fingerprint_match`, and nested `filtered` / `control` objects carrying
`status`, `reason`, `route`, `badges`, `populated`, and `error`.

The `error` field carries the message from whichever side raised;
`error_source` names that side.

## Data Generation Requirements

The whole run is pinned to one immutable data generation, recorded as
`summary.data_generation`. Cite that generation with any sweep result.

A generation of `legacy` means no immutable generation pointer was resolved.
Results from an unpopulated root are reported as `NO_SIGNAL` and are not
evidence about filter behavior.

Do not add the data-backed sweep to ordinary GitHub CI: the runners do not
carry the local NBA dataset, so every row there would be `NO_SIGNAL`.
`tests/test_qa_gate_integrity.py` guards the tool's classification and exit
semantics without any NBA data.

## Relationship To Other Layers

The sweep proves *that* filtering happened, not that the resulting numbers are
right. For correctness, use the Raw QA corpus described in
[`raw_query_answer_qa.md`](raw_query_answer_qa.md), and see
[`query_validation_map.md`](query_validation_map.md) for how the validation
layers differ.
