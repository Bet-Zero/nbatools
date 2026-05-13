# Raw Query Answer QA Harness Plan

## Purpose

Build a lightweight backend/product QA harness for this question:

Can a user ask NBA questions and get accurate, structured answers?

The harness should support manual and ChatGPT review first. Selected objective failures can later be promoted into hard regression tests.

This plan is discovery-backed and intentionally keeps Wave 1 small: run a curated query corpus, capture structured result envelopes, extract the most useful answer-review fields, and write JSONL plus Markdown reports. It should not require browser rendering in the first implementation.

## Existing Infrastructure To Reuse

The strongest existing reuse point is the backend query service:

- `src/nbatools/query_service.py::execute_natural_query(query)` returns a `QueryResult`.
- `src/nbatools/api_handlers.py::query_result_to_payload(qr)` converts that result into the same API envelope used by the React UI.
- The envelope includes route, status, reason, confidence, intent, alternates, notes, caveats, metadata, sections, and section rows.

The strongest existing corpus source is:

- `docs/architecture/parser/examples.md`, extracted by `src/nbatools/parser_examples.py::extract_cases()`.

That corpus is broad but not a correctness corpus. It includes supported examples, coverage-gated examples, stress inputs, intentionally ambiguous examples, and explicit unsupported boundaries.

Existing broad sweep support:

- `tools/parser_examples_full_sweep.py`
- `make parser-examples-sweep`
- ignored generated artifacts under `outputs/parser_examples_full_sweep/`

Existing review UI support:

- `frontend/src/ReviewPage.tsx`
- `GET /api/dev/fixtures`
- live `POST /query` execution
- frontend shape grouping via `classifyResultShape()`

## Key Gap

There is no curated answer-QA corpus with review-oriented expectations.

The existing 402-case parser examples are useful for breadth and route sanity, but they are not shaped around product answer correctness. Existing hard expectations are scattered across tests, usually as route/status/section assertions, with a few exact answer regressions.

## Recommended Architecture

Wave 1 should be a Python script, not an npm script and not a production CLI command.

Recommended files:

- `qa/raw_query_answer_corpus.yaml`
- `tools/raw_query_answer_qa.py`
- `outputs/raw_query_answer_qa/<run_id>/report.jsonl`
- `outputs/raw_query_answer_qa/<run_id>/report.md`
- `outputs/raw_query_answer_qa/<run_id>/summary.json`
- optional Makefile target: `raw-query-answer-qa`

Rationale:

- Python can call `execute_natural_query()` directly and reuse the API payload conversion.
- The harness can run without the frontend.
- Generated artifacts already belong under ignored `outputs/`.
- A `qa/` corpus keeps manual product-review cases separate from hard regression fixtures.
- Once a case becomes objective and stable, promote it into a focused test file instead of making the whole QA corpus a required test suite.

## Shape And Hero Policy

Wave 1 should not import the React renderer.

Shape handling:

- Include `route`, `query_class`, and returned section pattern from the backend.
- Add a best-effort `shape_hint` derived from route plus section presence.
- Mark it as `shape_source: backend_approximation`.
- Do not claim exact visual shape parity with `frontend/src/components/results/resultShapes.ts`.

Hero handling:

- Extract `metadata.count_phrase` and `metadata.answer_phrase` when present.
- Store them as `answer_text` with `answer_text_source: backend_metadata`.
- Leave `answer_text` null when the sentence is frontend-only.
- Do not snapshot exact frontend hero sentences in Wave 1.

Frontend-rendered hero extraction can be added later as a separate JS/headless-render pass if manual review shows it is worth the extra moving parts.

## Corpus Schema

Required now:

- `id`: stable slug
- `query`: natural-language query
- `category`: product family such as `record_when`, `leaderboard`, `unsupported`
- `priority`: `p0`, `p1`, or `p2`
- `expected_status`: string or list of allowed statuses

Optional now:

- `expected_route`
- `expected_reason`
- `expected_shape`
- `expected_filters`
- `expected_sections`
- `expected_row_counts`
- `hard_assertions`
- `review_notes`

Wait until later:

- exact frontend hero snapshots
- exact full-table snapshots
- broad per-column exact expected rows
- browser-only shape assertions

Example:

```yaml
version: 1
cases:
  - id: record_when_jokic_triple_double
    query: "What is Denver's record when Nikola Jokic has a triple-double?"
    category: record_when_player_condition
    priority: p0
    expected_status: ok
    expected_route: player_game_summary
    expected_shape: entity_summary
    expected_filters:
      - kind: special_event
        label: Special Event
        value: Triple Double
    expected_sections:
      - summary
      - game_log
    expected_row_counts:
      summary: 1
      game_log: 34
    hard_assertions:
      - path: result.sections.summary.0.games
        equals: 34
      - path: result.sections.summary.0.wins
        equals: 24
      - path: result.sections.summary.0.losses
        equals: 10
    review_notes: "Regression guard for stale unfiltered 65-game, 43-22 answer."

  - id: top_scorers_this_season
    query: "Who leads the NBA in points per game this season?"
    category: leaderboard
    priority: p1
    expected_status: ok
    expected_route: season_leaders
    expected_shape: leaderboard_table
    expected_sections:
      - leaderboard

  - id: cooled_off_unsupported
    query: "Which scorers have cooled off over their last 10 games?"
    category: unsupported_boundary
    priority: p2
    expected_status:
      - no_result
      - error
    expected_reason:
      - unsupported
      - unrouted
    review_notes: "Intentional semantic boundary until trend/drop-off definitions exist."
```

## Report Schema

Each JSONL row should include:

- `id`
- `query`
- `category`
- `priority`
- `route`
- `intent`
- `family` or `query_class`
- `result_status`
- `result_reason`
- `ok`
- `answer_text`
- `answer_text_source`
- `shape_hint`
- `shape_source`
- `metadata`
- `applied_filters`
- `sections`
- `section_summaries`
- `notes`
- `caveats`
- `errors`
- `expectation_results`

Section summaries should include:

- row count
- columns
- top rows, capped to 3 by default
- summary row, when section is single-row `summary`

Example JSONL row:

```json
{"id":"record_when_jokic_triple_double","query":"What is Denver's record when Nikola Jokic has a triple-double?","route":"player_game_summary","intent":"summary","query_class":"summary","result_status":"ok","result_reason":null,"answer_text":null,"answer_text_source":null,"shape_hint":"entity_summary","shape_source":"backend_approximation","applied_filters":[{"label":"Special Event","value":"Triple Double","kind":"special_event"}],"section_summaries":{"summary":{"row_count":1,"columns":["player_name","games","wins","losses","win_pct"],"top_rows":[{"player_name":"Nikola Jokic","games":34,"wins":24,"losses":10,"win_pct":0.706}]},"game_log":{"row_count":34,"columns":["game_date","team_abbr","opp_abbr","wl","pts","reb","ast"],"top_rows":[{"team_abbr":"DEN","wl":"W","pts":32,"reb":14,"ast":10}]}},"expectation_results":{"status":"pass","checks":[{"name":"expected_route","status":"pass"},{"name":"summary.games","status":"pass"}]}}
```

Markdown report should include:

- run metadata
- status/route/category summary
- failed expectation summary
- one review card per query
- compact section summaries and top rows
- notes/caveats/errors

Example Markdown card:

```md
### record_when_jokic_triple_double

- Query: `What is Denver's record when Nikola Jokic has a triple-double?`
- Category: `record_when_player_condition`
- Status: `ok`
- Route: `player_game_summary`
- Shape hint: `entity_summary`
- Answer text: _not backend-provided_
- Filters: `Special Event=Triple Double`
- Sections: `summary` 1 row, `game_log` 34 rows
- Expectations: pass

Summary row:

| player_name | games | wins | losses | win_pct |
|---|---:|---:|---:|---:|
| Nikola Jokic | 34 | 24 | 10 | 0.706 |
```

## Execution Wave 1

Create:

- `qa/raw_query_answer_corpus.yaml`
- `tools/raw_query_answer_qa.py`

Modify:

- `Makefile` with `raw-query-answer-qa`
- optionally `docs/operations/query_smoke_workflow.md` only if the workflow is formalized in Wave 1

Do not modify:

- production query behavior
- frontend renderer behavior
- existing parser examples
- existing hard tests

Acceptance criteria:

- The script reads the YAML corpus.
- The script runs each case through `execute_natural_query()`.
- The script converts each result through `query_result_to_payload()`.
- The script writes JSONL, Markdown, and summary JSON under `outputs/raw_query_answer_qa/<run_id>/`.
- Each report row includes route, intent, query class, status, reason, answer text when backend-provided, metadata, applied filters, sections, row counts, columns, top rows, notes, caveats, and expectation results.
- Expectations support status, route, reason, section presence, row counts, applied filters, and simple path equality checks.
- The initial corpus includes at least 10 curated cases covering record-when, entity summary, leaderboard, finder/count, team record, playoff/history, no-result, and unsupported boundary examples.
- The harness catches per-query exceptions and records them as query-level errors without aborting the whole run.
- No frontend runtime is required.

Validation commands:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --limit 5
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
git diff --check
```

If a Makefile target is added:

```bash
make raw-query-answer-qa
git diff --check
```

## Wave 1 Implementation Status

Implemented files:

- `qa/raw_query_answer_corpus.yaml`
- `tools/raw_query_answer_qa.py`
- `Makefile` target `raw-query-answer-qa`

Output location:

- `outputs/raw_query_answer_qa/<run_id>/report.jsonl`
- `outputs/raw_query_answer_qa/<run_id>/report.md`
- `outputs/raw_query_answer_qa/<run_id>/summary.json`

How to run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
make raw-query-answer-qa
```

Current limitations:

- The harness uses backend-provided `metadata.answer_phrase` or
  `metadata.count_phrase` only. Frontend-only hero sentences are not fabricated.
- `shape_hint` is a route/section-based backend approximation and is marked with
  `shape_source: backend_approximation`.
- Exact frontend hero text and exact frontend visual shape parity are deferred to
  a future rendered-output harness.
- The corpus is a curated manual-review set, not a replacement for focused hard
  regression tests.

## Promotion To Hard Tests

Use the report to decide which failures are objective.

Good promotion candidates:

- wrong route for a clearly supported query
- wrong result status or reason
- wrong record/count fields
- missing applied filter
- section row count mismatch for deterministic fixtures
- summary/game-log disagreement

Poor initial hard-test candidates:

- exact frontend hero sentence snapshots
- arbitrary top leaderboard ordering for live/current data
- broad 402-case pass/fail expectations
- subjective semantic boundaries such as "cooled off" before product definitions exist

Future hard tests should live near the behavior they protect:

- backend answer/data correctness: focused `tests/test_*` file, often `needs_data`
- API envelope shape: `tests/test_api.py` or `tests/test_query_service.py`
- frontend rendering/hero regressions: `frontend/src/test/ResultRenderer.test.tsx`
- corpus-level smoke: a small test around a promoted fixture subset, not the whole manual QA corpus

## Wave 2 Status

Wave 2 expanded the corpus and added triage-oriented review metadata. It did not
change production query behavior, frontend rendering behavior, or hard tests.

Status:

- Corpus expanded from 12 to 78 curated cases.
- Optional `manual_review` metadata is supported in the corpus and emitted into
  JSONL, Markdown, and summary reports.
- Triage fields are supported:
  - manual review status, tags, and notes
  - suggested review tags
  - suspicious flags for missing backend answer text on P0/P1 summary routes,
    ok results with no sections, unusually high player top-performance point
    totals, `playoff teams` queries returning `season_type=Playoffs`, expected
    unsupported/error-like cases returning ok, and expected-ok cases returning
    no-result/error.
- Findings inventory created:
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
- Latest output path:
  - `outputs/raw_query_answer_qa/20260512T085014Z/report.md`

Latest run summary:

- Run ID: `20260512T085014Z`
- Cases: 78
- Result statuses: `ok: 68`, `no_result: 4`, `error: 6`
- Expectation cases: `pass: 78`
- Expectation checks: `pass: 379`
- Failed case IDs: `[]`
- Suspicious flag cases: 22

Current limitations:

- The harness still uses backend-provided `metadata.answer_phrase` or
  `metadata.count_phrase` only. Frontend-only hero sentences are not extracted.
- `shape_hint` remains a backend approximation.
- Suspicious flags are review aids only; they do not fail expectations unless
  the corpus encodes a hard expectation.
- Several corpus cases intentionally encode current production behavior while
  marking manual-review concerns, so the report can group fix families before
  targeted implementation.

Next recommended phase:

- Review `RAW_QUERY_ANSWER_QA_FINDINGS.md` and group fixes by family before
  changing query behavior:
  - opponent-quality / playoff-team semantics
  - top-performance data quality
  - record-when condition filtering (AQ-004 fixed in Fix Wave 1)
  - unsupported/no-result policy for missing filters and product boundaries
  - frontend-rendered answer extraction
  - date handling

## Fix Wave 1 Status

Filtered team-record aggregation is fixed for the first correctness wave.

- Target case: `lakers_held_opponents_under_100_record`
- Fix: `team_record` now applies supported threshold filters before aggregating
  record summaries and by-season rows; opponent-points thresholds derive
  `opponent_pts` from team points and margin when the source table does not
  carry an explicit opponent-points column.
- Tests added: focused team-record engine coverage plus data-backed natural
  query regressions for the Lakers opponent-points case and the nearby Celtics
  team-points threshold case.
- Corpus update: the Lakers case now has hard assertions for `games=7`,
  `wins=7`, and `losses=0`.
- Latest targeted harness output:
  `outputs/raw_query_answer_qa/20260512T085005Z/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260512T085014Z/report.md`
- Remaining fix families: opponent-quality / playoff-team semantics, top
  performance data quality, unsupported/no-result policy for missing filters
  and product boundaries, frontend-rendered answer extraction, and date
  handling.

## Fix Wave 2 Status

Unsupported/missing filter policy is tightened for multi-player availability
record queries.

- Target case: `lakers_lebron_ad_both_play`
- Fix: multi-player availability record phrasing such as `Lakers record when
  LeBron and AD both play` now carries an explicit unsupported-filter marker
  and returns `no_result` / `filter_not_supported` before `team_record`
  execution, instead of returning an unfiltered full-season record.
- Single-player availability preserved: `Suns without Booker`, `Bucks record
  when Giannis was out`, `Knicks record when Jalen Brunson does not play`, and
  `Lakers record without LeBron` still execute as filtered `team_record`
  results with `Without player` applied filters.
- Latest targeted harness output:
  `outputs/raw_query_answer_qa/20260512T100432Z/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260512T100442Z/report.md`
- Latest full run summary: 78 cases; result statuses `ok: 67`,
  `no_result: 5`, `error: 6`; expectation cases `pass: 78`; expectation
  checks `pass: 381`; failed case IDs `[]`; suspicious flag cases `21`.
- Remaining fix families: opponent-quality / playoff-team semantics, top
  performance data quality, unsupported/no-result policy for other product
  boundaries, frontend-rendered answer extraction, and date handling.

## Fix Wave 3 Status

Date-filter drop prevention is fixed for explicit single-date top-scorer
queries.

- Target case: `specific_date_jan_1`
- Fix: explicit calendar dates such as `January 1 2026` now parse into a
  single-day date range. `Who scored the most points on January 1 2026?`
  routes to date-filtered game-level `top_player_games` instead of broad
  season `season_leaders`.
- Working date-window cases preserved: `top scorers in March` still returns a
  date-window `season_leaders` leaderboard, `Jokic since All-Star break` still
  returns filtered `player_game_finder` rows, and `Who scored the most points
  last night?` still returns `no_result` / `no_match` with its single-day date
  filter.
- Latest targeted harness output:
  `outputs/raw_query_answer_qa/20260512T105137Z/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260512T105201Z/report.md`
- Latest full run summary: 78 cases; result statuses `ok: 67`,
  `no_result: 5`, `error: 6`; expectation cases `pass: 78`; expectation
  checks `pass: 384`; failed case IDs `[]`; suspicious flag cases `21`.
- Remaining fix families: opponent-quality / playoff-team semantics, top
  performance data quality, unsupported/no-result policy for other product
  boundaries, frontend-rendered answer extraction, non-scoring top-performance
  product decisions, and team-scoped rolling-stretch product decisions.

## Fix Wave 4 Status

Opponent-quality playoff-team semantics are fixed.

- Target case: `celtics_record_playoff_teams`
- Fix: opponent-quality phrases such as `against playoff teams`, `against
  postseason teams`, and `against teams that made the playoffs` now keep
  `season_type=Regular Season` and resolve the existing `playoff teams`
  opponent bucket. Explicit playoff-competition phrases such as `playoff
  record`, `in the playoffs`, and `playoff history` still use Playoffs
  semantics or dedicated playoff routes.
- Corpus additions: `celtics_record_teams_made_playoffs` covers a phrase
  variant, and `celtics_playoff_record` protects explicit playoff-record
  wording.
- Latest targeted harness output:
  `outputs/raw_query_answer_qa/20260512T124856Z/report.md`
- Latest phrase-variant/guard harness output:
  `outputs/raw_query_answer_qa/20260512T124905Z/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260512T124917Z/report.md`
- Latest full run summary: 80 cases; result statuses `ok: 69`,
  `no_result: 5`, `error: 6`; expectation cases `pass: 80`; expectation
  checks `pass: 401`; failed case IDs `[]`; suspicious flag cases `23`.
  The previous `playoff_teams_playoff_season_type` suspicious flag is gone;
  remaining flags are `missing_backend_answer_text: 22` and
  `top_performance_high_points: 1`.
- Remaining fix families: top-performance data quality, unsupported/no-result
  policy for other product boundaries, frontend-rendered answer extraction,
  non-scoring top-performance product decisions, and team-scoped
  rolling-stretch product decisions.

## Fix Wave 5 Status

Verified top-performance outlier policy is added for QA reporting.

- Target case: `biggest_scoring_games`
- Policy: official-source-backed rare outliers are displayed as-is and recorded
  as verified outliers; hard impossibilities remain validation failures or
  review flags; suspicious-but-possible outliers remain open review flags until
  verified.
- Allowlist: `qa/verified_outliers.yaml`
- Fix: Bam Adebayo's 83-point game on 2026-03-10 is classified as a verified
  official outlier instead of an open suspicious data-quality issue. The
  `top_player_games` route and production output are unchanged.
- Harness behavior: high-point top-performance rows are still detected. Rows
  matching the allowlist move into `verified_outliers`; rows not matching the
  allowlist remain in `suspicious_flags`.
- Tests added: focused harness-unit coverage for verified high-point
  classification, unverified high-point classification, and leading-zero /
  zero-stripped `game_id` matching.
- Latest targeted harness output:
  `outputs/raw_query_answer_qa/20260513T025121Z/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260513T025137Z/report.md`
- Latest full run summary: 80 cases; result statuses `ok: 69`,
  `no_result: 5`, `error: 6`; expectation cases `pass: 80`; expectation
  checks `pass: 401`; failed case IDs `[]`; suspicious flag cases `22`;
  suspicious flags `missing_backend_answer_text: 22`; verified outlier cases
  `1`; verified outliers `top_performance_high_points: 1`.
- Remaining fix families: unsupported/no-result policy for other product
  boundaries, frontend-rendered answer extraction, non-scoring top-performance
  product decisions, and team-scoped rolling-stretch product decisions.

## Open Questions

- Should Wave 1 seed from `tests/_query_smoke.py`, the recent visual QA failures, or a hand-curated raw-product list? Recommendation: hand-curate the first 10-15 cases, then optionally import smoke cases later.
- Should frontend shape classification be reproduced in Python or extracted by Node? Recommendation: backend approximation in Wave 1; defer exact frontend classification.
- Should exact hero sentences ever become hard assertions? Recommendation: only after a separate rendered-output harness exists and only for targeted regressions.
