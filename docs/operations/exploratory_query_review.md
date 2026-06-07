# Exploratory Query Review

## Purpose

Exploratory query review is an input-only workflow for trying natural-language
NBA query samples and inspecting what the shared query engine returned.

It is useful for:

- reviewing public-search phrasing before deciding whether it belongs in Raw QA
- collecting route/status/result-shape snapshots for manual triage
- spotting no-result, error, or suspicious rows without writing expectations up front

It is not a regression harness and it is not validation evidence.
Backend status values are execution/result statuses only. Backend `ok` means
the query returned a structured backend result; it does not imply semantic
correctness, good query handling, or Raw QA pass/fail status.

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

Single slice:

```bash
make exploratory-query-review-slice SLICE=001_player_last_n
```

Direct command:

```bash
.venv/bin/python tools/exploratory_query_review.py \
  --input qa/exploratory_query_samples.yaml
```

Direct slice command:

```bash
.venv/bin/python tools/exploratory_query_review.py \
  --slice 001_player_last_n
```

Named local review folder:

```bash
.venv/bin/python tools/exploratory_query_review.py \
  --input qa/exploratory_query_samples.yaml \
  --run-id latest_exploratory \
  --overwrite-run-id
```

Organize existing local output folders:

```bash
.venv/bin/python tools/exploratory_query_review.py \
  --organize-existing-outputs
```

Use `--limit` to run a prefix of the input file and `--top-rows` to control
how many section rows are copied into the Markdown review cards.

Without `--slice`, the command runs the full input file. `--all` is accepted as
an explicit full-run marker, but it does not change the behavior.

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

## Slice Format

Small review batches live under:

```text
qa/exploratory/slices/
```

Each slice is input-only and uses the same sample rules as the full exploratory
file:

```yaml
id: 001_player_last_n
description: Player last-N game summaries
review_goal: Check player name parsing, last-N filters, summary shape, and game log rows.
samples:
  - id: luka_last_10
    query: "Luka Doncic stats last 10 games"
  - id: lebron_last_5
    query: "LeBron James stats last 5 games"
```

Slices must not include expected statuses, routes, filters, answer checks, Raw
QA acceptance metadata, or manual-review metadata. A slice is just a small
exploratory input batch.

The optional manifest at `qa/exploratory/manifest.yaml` is for human tracking
only:

```yaml
slices:
  - id: 001_player_last_n
    file: slices/001_player_last_n.yaml
    status: pending_review
```

The manifest is not a QA expectation file. If a requested slice is not listed in
the manifest, the runner falls back to
`qa/exploratory/slices/<slice_id>.yaml`.

## Generated Artifacts

Each run writes `report.jsonl`, `report.md`, and `summary.json` into the
generated exploratory output tree. The generated output root is intentionally
kept to stable navigation entries only; open its generated `README.md` and
`index.md` for the concrete local paths and recent-run list.

Scratch runs whose `--run-id` contains terms such as `smoke`, `codex`,
`debug`, `tmp`, or `audit` are kept out of the normal recent-run index.

- `report.jsonl` contains one structured row per sample, including the
  QueryResponse payload, search-box preview, route/status/query class, inferred
  shape, metadata, applied filters, sections, section summaries, review flags,
  timing, and slice metadata when the run used `--slice`.
- `report.md` is the manual review worksheet. Each case starts with
  `QueryResponse.query`, `ResultHero.sentence` /
  `search_box_preview.answer_line`, and the primary `ResultTable` /
  `result.sections` entry for quick scanning. Supporting details remain
  available below that summary, including display shape, route, result
  status/reason, query class, renderer patterns, filters, notes/caveats,
  section row counts, capped top rows, and blank reviewer fields.
- `summary.json` contains counts by route, result status, query class,
  search-box display shape, category, review flags, display-problem cases,
  no-result cases, error cases, suspicious cases, and slowest cases.
  These are backend execution/result counts, not correctness counts.
  Slice runs also include `slice_id`, `slice_description`, `slice_review_goal`,
  `input_slice_path`, and `slice_sample_count`.
- The latest report navigation entry is refreshed after every run.
- Slice-specific latest navigation is refreshed after every slice run.
- The generated index lists recent normal runs newest-first.
- The generated README explains the output folder layout.

## Reading The Search-Box Preview

Each `report.md` card starts with the existing query/result display terms:

```text
QueryResponse.query
ResultHero.sentence / search_box_preview.answer_line
ResultTable / result.sections
```

This is the part to read when asking "what would the search box show?" If the
compact summary looks wrong or ambiguous, expand the supporting details below
the case.

| Field | Meaning |
| --- | --- |
| `QueryResponse.query` | Original query string returned in the API `QueryResponse` envelope. |
| `ResultHero.sentence` / `search_box_preview.answer_line` | Main answer sentence when the frontend pattern renders a `ResultHero`; the exploratory tool records it as `search_box_preview.answer_line`, using backend `answer_phrase`/`count_phrase` when present and otherwise a compact report-only summary. |
| `ResultTable` / `result.sections` | Primary backend section expected to feed the first main table or section under the answer, such as `result.sections.game_log`, `result.sections.summary`, `result.sections.leaderboard`, or `result.sections.split_comparison`. |
| `Display shape` | Frontend result-shape catalog entry, such as `Entity Summary + Recent Games`, `Player Game Log`, `Team Record`, or `Leaderboard Table`. |
| `Renderer patterns` | Ordered frontend renderer stack, such as an entity summary followed by a game-log table. |
| `Answer line` | Backend answer text when supplied, otherwise the tool's compact summary of the same payload. |
| `Visible sections/tables` | Section names, row counts, and whether the section is a hero/summary, primary table, or detail table. |
| `Display problem flags` | Flags for unclear presentation, such as `fallback_display_shape`, `unclassified_display_shape`, or `ok_without_visible_sections`. |

Example: a player last-N query such as `Luka stats last 10 games` should show
`Entity Summary + Recent Games` with renderer patterns for a summary hero and a
`game_log` table. If a query only gets `Fallback Tables` or `Unclassified`, that
is a review problem to resolve before treating the surface as clean.

Automatically detected flags are limited to structural, display, and
result-shape issues. A zero suspicious/display-problem count does not mean every
answer is semantically correct. Human review should focus on whether the
returned result appears appropriate for the query. Some unsupported or ambiguous
queries are intentionally included, so do not treat every `no_result` as a bug
and do not treat every backend `ok` as correct.

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
