# Parser Examples Full-Sweep Protocol

## Purpose

This protocol defines how to run a **full end-to-end sweep** over every runnable example in [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md), record the actual outputs, and present the results in durable repo-visible artifacts.

This is intentionally broader than the smoke harness:

- the smoke harness protects a compact durable subset of real queries
- this protocol audits the much larger parser example library
- the goal is not only regression detection, but also an honest map of which examples are fully supported, partially supported, coverage-gated, ambiguous, unsupported, or mismatched

## Important expectation

Do **not** assume that every example in `examples.md` must return a fully execution-backed happy-path answer.

That file is an **example library / parser evaluation input source**, not the sole source of truth for shipped support. It explicitly says:

- use it for reference, test inputs, and equivalence verification
- explicit unfiltered-results, coverage-gated, placeholder, or deferral notes describe current shipped behavior
- the living inventory of currently shipped query shapes is `docs/reference/query_catalog.md`

Therefore, this full sweep is graded against the repo's documented behavior, not a blanket assumption that every example must produce a fully supported result.

## Source docs to read before running

Required:

- `docs/architecture/parser/examples.md`
- `docs/reference/query_catalog.md`
- `docs/reference/current_state_guide.md`
- `docs/architecture/parser/specification.md`
- `docs/planning/master_completion_plan.md`
- `docs/operations/query_smoke_workflow.md`

Use those docs to classify whether each example is:

- fully supported
- supported with coverage-gated / fallback behavior
- intentionally ambiguous
- intentionally unsupported / out of scope
- a parser stress test where honest failure is acceptable

## Scope: what counts as a test case

Include every runnable natural-language or shorthand input in `examples.md`, including:

- every numbered example in section 2
- every question-form and search-form entry in section 3 (both sides are separate test cases)
- every runnable bullet example in section 4
- every runnable stress-test input in section 5
- every worked-example raw input in section 6
- every query-like member of equivalence groups in section 7
- any explicit natural-language expansion-pattern example in section 8

Do **not** count as test cases:

- prose explanations
- JSON parse-state examples
- route kwargs
- code blocks that are not user-entered query text
- headings / labels / intent-family descriptions

## Output artifacts

A full sweep run must create all of these artifacts:

### 1. Machine-readable results

`outputs/parser_examples_full_sweep/results.csv`

Required columns:

- `case_id`
- `source_section`
- `source_subsection`
- `case_kind`
- `query_text`
- `expected_behavior_category`
- `expected_notes`
- `cli_exit_code`
- `result_status`
- `result_reason`
- `route`
- `query_class`
- `intent`
- `confidence`
- `has_alternates`
- `notes`
- `caveats`
- `pass_fail`
- `pass_fail_reason`
- `raw_json_path`

### 2. Per-query raw output captures

`outputs/parser_examples_full_sweep/raw/<case_id>.json`

Store the raw structured output for every executed case so future review can inspect exact envelopes without rerunning the sweep.

### 3. Human-readable report

`outputs/parser_examples_full_sweep/report.md`

This must contain:

- run date/time
- git commit SHA if available
- total case count
- counts by `expected_behavior_category`
- counts by actual `result_status`
- counts by `pass_fail`
- grouped failure table
- grouped ambiguity table
- grouped unsupported / out-of-scope table
- grouped coverage-gated / fallback table
- top recurring mismatch patterns
- specific examples that appear wrong enough to merit follow-up work

### 4. Optional manifest

`outputs/parser_examples_full_sweep/manifest.json`

Recommended contents:

- source file path
- source commit SHA if available
- extraction timestamp
- case count by section
- artifact paths

## Case ID format

Use stable IDs so reruns are diffable.

Recommended format:

- section 2 numbered examples: `S2_2_1_01`
- section 3 paired examples, question form: `S3_3_1_01_Q`
- section 3 paired examples, search form: `S3_3_1_01_S`
- section 4 bullets: `S4_4_1_01`
- section 5 stress cases: `S5_5_1_01`
- section 6 worked-example raw inputs: `S6_6_1_01`
- section 7 equivalence members: `S7_<group>_<member>`
- section 8 expansion examples: `S8_<group>_<member>`

The exact naming scheme may differ, but IDs must be:

- deterministic
- stable across reruns unless the source example text itself changes
- traceable back to the exact source location in `examples.md`

## Execution method

### Primary execution path

Run each case through the **real CLI path** using structured JSON export.

Recommended pattern:

```bash
nbatools-cli ask "<query>" --json outputs/parser_examples_full_sweep/raw/<case_id>.json
```

This is the primary source of truth for the sweep because it exercises the shipped natural-query product path.

### Optional secondary verification

If desired, the same query may also be sent through the API path (`/query`) to verify envelope consistency, but the protocol does not require duplicate API execution unless the sweep owner is specifically auditing transport parity.

## Classification model

Every case must be assigned an **expected behavior category** before scoring pass/fail.

Allowed categories:

1. `supported_exact`
   - the example is documented as a shipped supported query shape and should return a meaningful structured result

2. `supported_with_fallback`
   - the example is expected to return an honest coverage-gated, fallback-note, or partially filtered result according to current docs

3. `ambiguous_expected`
   - the example is intentionally ambiguous and should surface ambiguity / alternates / no-result honestly rather than guessing silently

4. `unsupported_expected`
   - the example is explicitly out of scope or unsupported by current documented behavior

5. `stress_clean_failure_ok`
   - the example is a stress test where clean no-result / unsupported / ambiguity behavior is acceptable and often preferable to a wrong answer

## Pass/fail rules

A case is **pass** when the actual behavior matches the expected category honestly.

Examples:

- `supported_exact` + real structured result on the documented route boundary -> pass
- `supported_with_fallback` + explicit honest fallback note -> pass
- `ambiguous_expected` + ambiguity / alternates / honest non-guessing behavior -> pass
- `unsupported_expected` + unsupported/no-result with honest reason -> pass
- stress input that fails cleanly instead of hallucinating -> pass

A case is **fail** when:

- it routes to the wrong capability family
- it silently guesses a wrong interpretation
- it returns a contradictory route vs documented support boundary
- it returns placeholder / fallback behavior for a case that should be fully supported
- it claims support for something the repo docs mark out of scope
- it crashes or produces malformed structured output

## Special handling by section

### Section 2 canonical examples

Treat as the highest-value baseline set.

- each example should be explicitly categorized against current docs
- these should be highlighted first in the final report

### Section 3 paired examples

Run both sides separately and also compare them.

Additional pair-level checks:

- route should match
- query class should match
- result status category should match
- intent should match when present
- large confidence gaps should be flagged
- if one side works and the paired phrasing fails, mark the pair as a phrasing mismatch

Record pair-level issues in the report separately from single-case failures.

### Section 4 capability clusters

Good for concentrated coverage by query class. Report failures by cluster.

### Section 5 stress tests

Do **not** over-penalize these for not returning a happy-path answer.
The key question is whether the behavior is honest and stable.

### Section 6 worked examples

In addition to normal execution, compare against the intended route/slot story when the worked example explicitly documents it.

### Section 7 equivalence groups

In addition to running each member separately, add a group-level comparison pass:

- group members that are intended equivalent should not diverge materially in route / query class / status category without a documented reason
- group-level mismatches should be summarized separately in the final report

### Section 8 expansion patterns and boundaries

Treat these as boundary tests.
Do not collapse them into simple supported/unsupported counts without preserving the explicit boundary semantics.

## Required report sections

`report.md` must include these headings:

1. `Run summary`
2. `Case counts by source section`
3. `Case counts by expected behavior`
4. `Actual result-status distribution`
5. `Overall pass/fail summary`
6. `Phrasing-pair mismatches`
7. `Equivalence-group mismatches`
8. `Supported examples that failed`
9. `Fallback / coverage-gated examples behaving as documented`
10. `Ambiguous examples`
11. `Unsupported / out-of-scope examples`
12. `Top follow-up candidates`
13. `Appendix: artifact locations`

## Suggested follow-up thresholds

Flag these automatically in the report:

- any canonical section 2 example that fails
- any paired section 3 example where only one phrasing works
- any equivalence group with inconsistent routes or inconsistent result classes
- any stress case that produces an obviously wrong confident answer
- any case where docs say supported but the product returns unsupported/no-result
- any case where docs say unsupported/deferred but the product appears to claim support

## Required discipline

- Do not rewrite docs just to make the sweep pass.
- Do not weaken the grading by calling everything “stress.”
- Do not mark a case pass just because some output came back.
- Do not use exact pretty-text matching as the success criterion.
- Do not treat fallback behavior as failure if the docs explicitly say fallback behavior is the current shipped boundary.
- Do not ignore mismatches between `examples.md` and `query_catalog.md`; record them explicitly.

## Operator checklist

Before running:

- confirm local data is present
- confirm build/test environment is healthy
- read the current docs named above
- create the output directory tree

During run:

- execute every extracted case once through the CLI JSON path
- save every raw JSON envelope
- fill one CSV row per case
- record any execution failure instead of skipping silently

After run:

- generate the markdown report
- review canonical-example failures manually
- review pair mismatches manually
- review any cases that appear to contradict the docs

## Completion condition

This protocol is complete only when:

- every runnable example input from `examples.md` has a case ID
- every case has a raw JSON artifact or explicit execution-failure record
- `results.csv` exists and is filled
- `report.md` exists and summarizes the run honestly
- the report clearly distinguishes supported behavior, fallback behavior, ambiguity, unsupported boundaries, and true mismatches

## Recommended execution note

This full sweep is large enough that it should usually be run as a dedicated audit pass, not casually during ordinary feature work.

It complements:

- parser tests
- query tests
- engine tests
- smoke queries

It does **not** replace them.
