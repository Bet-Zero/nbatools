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
- the query did not return a system-error envelope;
- `result_status` is `ok`;
- at least one public answer section carries a real answer.

Anything else leaves nothing to compare against: a refusal, missing local
data, uncovered season coverage, or an empty answer. Two unpopulated answers
fingerprint identically no matter what the filter did, so treating that as
evidence would manufacture a clean verdict out of missing data.

## What Counts As Answer Data

Comparison uses a stable fingerprint of the result's **canonical public answer
sections** — the data under its `to_dict()["sections"]` contract, the same
sections the API and formatters publish. Section names, row order, and cell
values all contribute, so a section appearing, disappearing, reordering, or
changing a value is a change.

| Result type | Public sections compared |
| --- | --- |
| `NoResult` | none |
| `SummaryResult` | `summary`, `by_season`, `game_log`, `top_performers` |
| `ComparisonResult` | `summary`, `comparison` |
| `SplitSummaryResult` | `summary`, `split_comparison` |
| `FinderResult` | `finder` |
| `LeaderboardResult` | `leaderboard` |
| `StreakResult` | `streak` |
| `CountResult` | `count`, `finder` |

Presentation and trust metadata is **excluded** — applied-filter badges,
`notes`, `caveats`, `route` and other `metadata`, `current_through`, and
timestamps. None of it determines whether the answer data changed. Badge claims
are still evaluated separately, by the `LIED` / `DROPPED` logic.

Fingerprinting and the populated-control decision read the *same* normalized
extraction, so they can never disagree about what the answer was.

`count` is the one section needing a value check rather than a row check: a
`CountResult` always publishes a count, including zero. A positive count is
real public answer data even with no games attached; a zero count keeps its
expected-negative meaning and does not create a populated control.

### Why not an attribute list

An earlier revision fingerprinted a hand-maintained attribute list — `games`,
`leaders`, `streaks`, `summary`, `splits`, `comparison`. That list had drifted
from the result classes. It looked for `splits`, which no result class exposes;
`SplitSummaryResult` publishes its displayed table as `split_comparison`, so
every split table was invisible to the comparison. `SummaryResult`'s
`by_season`, `game_log`, and `top_performers` and `CountResult`'s `count` were
missing too.

A filter could therefore change a displayed section that the fingerprint never
looked at, and the sweep would call the answer unchanged — reporting a working
filter as `LIED` when a badge was present, or `DROPPED` when it was not. Reading
the published section contract removes the drift by construction.

### Adding a public section

Evidence extraction is not filtered through any allowlist: **every section a
result actually emits is compared at runtime**, registry or not, so a new
section can never silently drop out of the evidence. A test pins that directly.

`SUPPORTED_RESULT_SECTIONS` is the explicit inventory of the section policies
that have been decided and exercised. The guard tests in
`tests/test_qa_gate_integrity.py` detect a result type being added or removed,
and any section reachable from their fully-populated fixtures.

The guard is bounded, and worth stating plainly: it is fixture-based, not a
source analysis. A future *conditionally* emitted section that no fixture
populates would still be fingerprinted at runtime, but it would not trip the
inventory test until a fixture covers it. When adding a section, add its
registry entry, populate it in the fixture, and decide whether it counts as a
populated answer — a scalar like `count` needs a value rule, a table needs only
rows.

## Row Classifications

Every configured pair lands in exactly one bucket.

| Verdict | Meaning | Comparable |
| --- | --- | --- |
| `APPLIED` | The control was populated and the filtered answer's data differed. The filter did something. | yes |
| `REFUSED` | The control was populated and the filtered question came back `no_result`. The app declined, honestly. | yes |
| `LIED` | The control was populated, the filtered data was identical to it, **and** a badge claimed *this* filter was applied. | yes |
| `DROPPED` | The control was populated, the filtered data was identical to it, and nothing was claimed. The words were silently ignored. | yes |
| `NO_SIGNAL` | The control was not comparable. Nothing about this filter was tested. | **no** |
| `ERROR` | Either side failed at the system level — it raised, or it returned `result_status=error`. `error_source` names the side, `error_kind` names the delivery. | **no** |

A badge only counts when it names the filter under test. An unrelated badge
from a threshold in the same query does not make an unchanged answer a lie.

### Expected negative outcomes versus system failures

The result contract separates the two, and so does the sweep. Getting this
wrong is how a broken route becomes a clean report.

`result_status=no_result` is an **expected negative outcome**: the data or the
query legitimately produced no answer (`no_match`, `no_data`, `unsupported`,
`filter_not_supported`, `ambiguous`, `ambiguous_query`). What it means depends
on which side produced it:

- on the **filtered** side, against a populated control, it is an honest
  `REFUSED`;
- on the **control** side, it is `NO_SIGNAL` — there is no baseline left to
  compare against.

`result_status=error` is a **system-level failure**: the query could not be
parsed or routed (`unrouted`), or an internal failure occurred (`error`). It is
`ERROR` on either side and fails the run. A system error is neither an honest
filter refusal nor a harmless absence of data, and it is never rounded down to
either.

A completed result must also publish a valid public-sections contract. An `ok`
or `no_result` result whose contract is missing or malformed cannot be read as
an answer, so it is a system-level failure too — never `APPLIED`, `REFUSED`,
`DROPPED`, `LIED`, or `NO_SIGNAL`. An empty `sections` mapping is valid
(`NoResult` publishes exactly that) and simply means not populated; that is
different from a missing or malformed contract.

A raised exception, a returned error envelope, and unusable answer evidence are
all the same class of failure; only the delivery differs. `error_kind` records
which:

| `error_kind` | Meaning |
| --- | --- |
| `raised_exception` | The query raised; `error` carries the exception message. |
| `returned_error_status` | The query returned `result_status=error`; the row preserves that side's `status`, `reason`, and `route`. |
| `unknown_result_status` | The query returned a status outside the canonical set (`ok`, `no_result`, `error`). Failed closed rather than guessed at. |
| `missing_public_result_contract` | The result object is absent or publishes no callable `to_dict()`. |
| `non_dict_public_result_payload` | `to_dict()` returned something other than a dict. |
| `missing_public_sections` | The payload has no `sections` mapping. |
| `non_dict_public_sections` | `sections` is not a dict. |
| `malformed_public_section` | A section name is not a string, or a section value is not a list of records. |
| `public_result_contract_exception` | Reading, validating, normalizing, fingerprinting, or scoring the sections raised. |

Every one of those steps runs inside the sweep's protected boundary, alongside
query execution and status inspection. A failure anywhere becomes an `ERROR`
row — the JSON evidence is still written, rather than the process aborting
before it reports anything.

### NO_SIGNAL semantics

`NO_SIGNAL` is not a soft pass and not a refusal. It is the absence of
evidence. A `NO_SIGNAL` row proves nothing about whether that filter is honest,
and it is excluded from the comparable counts and from the run verdict.

Each `NO_SIGNAL` row records why, as `no_signal_reason`:

| Reason | Cause |
| --- | --- |
| `control_no_result:<reason>` | The control refused; `<reason>` is the typed result reason, such as `no_data` or `unsupported`. |
| `control_empty_result` | The control returned `ok` with no populated rows. |

The most common cause is a data gap rather than a code gap. Season coverage
matters: a filter that reads a dataset which does not cover the seed's season
produces an unpopulated control. Re-run against a covered season before
concluding anything about the filter itself.

A control that raised or returned `result_status=error` never appears here: it
is `ERROR`, not a coverage gap.

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

`FAIL` outranks `NO_SIGNAL`: a verified defect or a system-level failure is
worth surfacing even in a run that compared nothing.

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
`comparable`, `no_signal_reason`, `error_source`, `error_kind`, `route`,
`badges`, `error`, `fingerprint_match`, and nested `filtered` / `control`
objects carrying `status`, `reason`, `route`, `badges`, `populated`,
`sections`, `error`, and `error_kind`.

Each side's `sections` lists the public section names that went into its
evidence — enough to audit what was compared, without duplicating the data.

`error_source` names the side that failed and `error_kind` names how. The
`error` field carries the exception message when a side raised, and
`result_status=<status> result_reason=<reason>` when a side returned a
system-error envelope; the exact returned `status`, `reason`, and `route` stay
on that side's nested object either way.

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

`tests/test_filter_execution_integrity.py` is the data-backed companion check:
for a handful of curated filter pairs it asserts the engine either refuses
honestly or changes the complete public answer. It shares this module's
evidence extraction through `tests/_filter_evidence.py`, so both judge "did the
answer change" from the same sections, and a system-level failure on either
side fails that test explicitly instead of passing as a changed answer. It is
marked `needs_data` and `slow`, so it runs locally rather than in ordinary CI.

The sweep proves *that* filtering happened, not that the resulting numbers are
right. For correctness, use the Raw QA corpus described in
[`raw_query_answer_qa.md`](raw_query_answer_qa.md), and see
[`query_validation_map.md`](query_validation_map.md) for how the validation
layers differ.
