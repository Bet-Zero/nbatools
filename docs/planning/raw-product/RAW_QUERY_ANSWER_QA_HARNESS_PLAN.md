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
{
  "id": "record_when_jokic_triple_double",
  "query": "What is Denver's record when Nikola Jokic has a triple-double?",
  "route": "player_game_summary",
  "intent": "summary",
  "query_class": "summary",
  "result_status": "ok",
  "result_reason": null,
  "answer_text": null,
  "answer_text_source": null,
  "shape_hint": "entity_summary",
  "shape_source": "backend_approximation",
  "applied_filters": [
    {
      "label": "Special Event",
      "value": "Triple Double",
      "kind": "special_event"
    }
  ],
  "section_summaries": {
    "summary": {
      "row_count": 1,
      "columns": ["player_name", "games", "wins", "losses", "win_pct"],
      "top_rows": [
        {
          "player_name": "Nikola Jokic",
          "games": 34,
          "wins": 24,
          "losses": 10,
          "win_pct": 0.706
        }
      ]
    },
    "game_log": {
      "row_count": 34,
      "columns": [
        "game_date",
        "team_abbr",
        "opp_abbr",
        "wl",
        "pts",
        "reb",
        "ast"
      ],
      "top_rows": [
        { "team_abbr": "DEN", "wl": "W", "pts": 32, "reb": 14, "ast": 10 }
      ]
    }
  },
  "expectation_results": {
    "status": "pass",
    "checks": [
      { "name": "expected_route", "status": "pass" },
      { "name": "summary.games", "status": "pass" }
    ]
  }
}
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

| player_name  | games | wins | losses | win_pct |
| ------------ | ----: | ---: | -----: | ------: |
| Nikola Jokic |    34 |   24 |     10 |   0.706 |
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

## Fix Wave 5 Top-Performance Outlier Status

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

## Fix Wave 6 Status

Top-performance routing and the team rolling-stretch product boundary are fixed.

- Target cases: `most_assists_single_game`, `most_rebounds_single_game`, and
  `team_5_game_scoring_stretch`
- AQ-006 support: non-scoring single-game top-performance wording such as
  `most assists in a game` and `single-game rebound leaders` now routes to
  `top_player_games` with `stat=ast` / `stat=reb` and keeps the existing
  `top_performances` shape.
- AQ-008 unsupported boundary: team-scoped rolling-stretch wording such as
  `best 5-game team scoring stretch` returns `no_result` /
  `filter_not_supported` with
  `unsupported_filters=["team_rolling_stretch"]` instead of player rolling
  windows.
- Latest targeted harness output:
  `outputs/raw_query_answer_qa/20260513T040756Z/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260513T040809Z/report.md`
- Latest full run summary: 80 cases; result statuses `ok: 70`,
  `no_result: 6`, `error: 4`; expectation cases `pass: 80`; expectation
  checks `pass: 409`; failed case IDs `[]`; suspicious flag cases `22`;
  suspicious flags `missing_backend_answer_text: 22`; verified outlier cases
  `1`; verified outliers `top_performance_high_points: 1`.
- Remaining family: frontend answer extraction / backend answer text limitation.

## Fix Wave 7A Status

Answer-text QA classification is now policy-aware. This wave did not change
production query behavior, frontend rendering, route behavior, or backend answer
metadata generation.

- Corpus policy: `qa/raw_query_answer_corpus.yaml` supports
  `answer_text_policy` with these values:
  `requires_backend_answer_text`, `frontend_hero_expected`, and
  `no_answer_text_expected`.
- Reclassification: the 22 previously suspicious AQ-003
  `missing_backend_answer_text` cases are marked `frontend_hero_expected`.
  Missing backend metadata for those cases is now reported as informational
  because the React result components are expected to build the hero/final
  answer.
- Required backend text: current backend `answer_phrase` / `count_phrase`
  cases are marked `requires_backend_answer_text`; those still produce an open
  `missing_backend_answer_text` suspicious flag if the phrase disappears.
- No-answer boundaries: unsupported/no-result/product-boundary cases are marked
  `no_answer_text_expected` where no backend answer or frontend hero is needed.
- Report output: JSONL, summary JSON, and Markdown now include
  `answer_text_policy`, `answer_text_status`, informational flag counts, and
  suspicious flag counts that exclude expected frontend-only heroes.
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260513T044523Z/report.md`
- Latest full run summary: 80 cases; result statuses `ok: 70`,
  `no_result: 6`, `error: 4`; expectation cases `pass: 80`; expectation
  checks `pass: 409`; failed case IDs `[]`; suspicious flag cases `0`;
  informational flag cases `22`; informational flags
  `frontend_hero_expected: 22`; verified outlier cases `1`; verified outliers
  `top_performance_high_points: 1`.
- Next optional wave: targeted backend `answer_phrase` enrichment for
  high-value record-style routes such as `team_record`, player-condition
  record summaries, and selected postseason direct-answer routes.

## Corpus Expansion Wave 3 Status

Expansion Wave 3 broadened the manual QA corpus from 80 to 145 curated cases.
This was a corpus/reporting/review wave only: no production query behavior,
frontend rendering, backend answer metadata, or source data was changed.

Coverage strategy:

- Core surfaces/stat coverage: expanded player leaderboards, team leaderboards,
  top performances, player summaries, team records, count/finder queries,
  streaks, rolling stretches, playoff/history routes, comparisons, and splits.
- Phrasing variation: added question-form, search-bar shorthand, compressed
  threshold forms, `who leads`, `most`, `best`, `highest`, `how often`,
  `record when`, `against`, `without`, `single-game`, and current-season
  variants.
- Context/filter assumptions: added this-season defaults, `last season`, March,
  since All-Star break, road/home, opponent quality, top defenses, playoff
  teams, season ranges, and decade/era contexts.
- Moderate complexity: added player-threshold record-when cases, team threshold
  records, player count/finder thresholds, compound team counts, and compact
  multi-stat player finders.
- Unsupported boundaries: added or reinforced minutes leaderboard support
  boundaries, team rolling stretches, lineup/on-off unsupported data, subjective
  duo ranking, and team single-game threes routing.

Harness/reporting update:

- JSONL and Markdown rows now include QA-only `answer_summary` compact fact
  lines, derived from returned rows. This does not change production backend
  `answer_phrase` / `count_phrase` metadata.

Latest run:

- Run ID: `20260513T060001Z`
- Output path: `outputs/raw_query_answer_qa/20260513T060001Z/report.md`
- Cases: 145
- Result statuses: `ok: 126`, `no_result: 13`, `error: 6`
- Expectation cases: `pass: 137`, `fail: 8`
- Expectation checks: `pass: 695`, `fail: 17`
- Suspicious flag cases: 3
- Suspicious flags: `expected_ok_returned_non_ok: 3`
- Informational flag cases: 73
- Informational flags: `frontend_hero_expected: 73`
- Verified outlier cases: 1
- Verified outliers: `top_performance_high_points: 1`

New finding families:

- player summary/split no-match diagnostics
- abbreviation-heavy stat/context route and filter drops
- defensive/opponent-points stat mapping
- relative season filter preservation
- percentage threshold parsing/execution
- compound threshold parsing/execution
- position-filtered leaderboard support
- backend count phrase quality
- product-boundary decisions for documented stats and team top-game variants

Recommended next phase:

- Do not fix one case at a time. Group the Wave 3 findings into fix families:
  defensive stat mapping, compound/percentage threshold parsing, context-filter
  preservation, summary/split no-match diagnostics, and count phrase quality.
- Promote only objective, stable fixes into focused tests near the relevant
  parser, route, or command behavior.
- Keep frontend hero extraction and broad backend answer enrichment deferred
  unless a focused answer-text wave is explicitly scheduled.

## Fix Wave 4A Status

Scalar stat and threshold semantics are fixed for the targeted cases. This wave
changed parser/stat mapping, team leaderboard aggregation, tests, docs, and QA
corpus expectations. It did not change frontend rendering, backend answer
phrase enrichment, source data, or compound-threshold representation.

- Defensive/opponent-points scalar mapping: phrases such as
  `allow fewer than 110 points`, `points allowed under 110`, `opponent points
under 110`, and `opp pts under 110` now bind to `opponent_pts` rather than
  team `pts`; team scoring forms such as `score fewer than 110 points` remain
  team `pts`.
- Points-allowed leaderboard support: `Which team has allowed the fewest points
per game this season?` routes to `season_team_leaders` with
  `opponent_pts_per_game`, derived from team game rows, and ranks ascending.
  The current dataset top row is Boston at about 107.159 opponent PPG.
- Percentage threshold normalization: clear shooting contexts such as
  `shoots under 40%`, `FG% under 40%`, `shoots under .400`, and
  `from three over 40%` normalize to the stored 0.xx scale and preserve the
  right shooting stat (`fg_pct`, `fg3_pct`, or `ft_pct`).
- Compound thresholds deferred: `celtics_120_15_threes_count_missing_filter`
  and `jokic_30_points_10_assists_finder_misparsed` remain open for the next
  compound-threshold representation/execution wave.
- Latest targeted scalar harness output:
  `outputs/raw_query_answer_qa/20260513T071000Z_wave4a_targeted/report.md`
- Latest adjacent regression harness output:
  `outputs/raw_query_answer_qa/20260513T071100Z_wave4a_adjacent/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`
- Latest full run summary: 145 cases; result statuses `ok: 126`,
  `no_result: 13`, `error: 6`; expectation cases `pass: 139`, `fail: 6`;
  expectation checks `pass: 705`, `fail: 15`; failed case IDs
  `anthony_edwards_last_10_summary_no_match`,
  `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`,
  `celtics_120_15_threes_count_missing_filter`,
  `jokic_30_points_10_assists_finder_misparsed`, and
  `anthony_edwards_wins_losses_split_no_match`.
- Recommended next phase: compound threshold representation/execution for
  count/finder routes.

## Fix Wave 4B Status

Compound threshold representation/execution is fixed for the targeted count and
finder failures. This wave added a shared stat-threshold condition helper,
route-consumed `conditions` for compound finder/occurrence routes, pre-limit
finder filtering for compound thresholds, metadata/applied-filter coverage for
all route-consumed conditions, tests, corpus expectations, and docs. It did not
change frontend rendering, source data, scalar Wave 4A stat mapping, or broad
compact shorthand such as `25/10/10`.

- `celtics_120_15_threes_count_missing_filter`: fixed. The query now routes to
  `team_occurrence_leaders`, consumes `conditions=[pts>=120, fg3m>=15]`, does
  not post-filter the aggregate row via duplicate `extra_conditions`, and
  returns count `125`.
- `jokic_30_points_10_assists_finder_misparsed`: fixed. The compact finder now
  consumes `conditions=[pts>=30, ast>=10]`, keeps `stat=pts` for sorting, and
  returns 14 rows satisfying both thresholds instead of filtering `ast>=30`.
- Latest targeted compound harness output:
  `outputs/raw_query_answer_qa/20260513T083000Z_wave4b_targeted/report.md`
- Latest adjacent regression harness output:
  `outputs/raw_query_answer_qa/20260513T083500Z_wave4b_adjacent/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`
- Latest full run summary: 145 cases; result statuses `ok: 127`,
  `no_result: 12`, `error: 6`; expectation cases `pass: 141`, `fail: 4`;
  expectation checks `pass: 716`, `fail: 10`; failed case IDs
  `anthony_edwards_last_10_summary_no_match`,
  `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, and
  `anthony_edwards_wins_losses_split_no_match`.
- Recommended next phase: context/filter preservation and no-match diagnostics,
  with `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`,
  and the Anthony Edwards no-match cases as the highest-priority remaining
  failures.

## Fix Wave 5 Context / Filter Status

Context/filter preservation and no-match diagnostics are fixed for the four
remaining Wave 4B failures. This wave changed entity resolution,
relative-season parsing, opponent-quality shorthand parsing, a narrow
player-stat-context route default, explicit relative-season metadata/filter
coverage, tests, QA corpus expectations, and docs. It did not change frontend
rendering, backend answer phrase enrichment, source data, or the previously
fixed scalar/compound threshold behavior.

- Anthony Edwards full-name resolution: fixed. Data-backed exact full-name
  matches now run before broad nickname aliases, so full queries containing
  `Anthony Edwards` resolve to Anthony Edwards instead of Carmelo Anthony.
  The single-token `anthony` alias remains Carmelo Anthony.
- Singular `last season`: fixed. `last season` / `previous season` resolves to
  the season before the latest season for the detected season type. With latest
  regular-season data set to `2025-26`, `Lakers road record last season`
  resolves to `2024-25` and returns 41 games, 19 wins, and 22 losses.
- `top defenses` shorthand: fixed for explicit opponent context. `against top
defenses`, `vs top defenses`, and `versus top defenses` map to the existing
  `top-10 defenses` opponent-quality bucket without turning free-standing team
  defense leaderboard wording into opponent-quality context.
- KD stat/context routing: fixed. `KD TS% vs top defenses` preserves
  `stat=ts_pct`, preserves `opponent_quality=top-10 defenses`, routes to
  `player_game_summary`, and returns a 23-game sample.
- Latest targeted Wave 5 harness output:
  `outputs/raw_query_answer_qa/20260513T093000Z_wave5_targeted/report.md`
- Latest adjacent regression harness output:
  `outputs/raw_query_answer_qa/20260513T093500Z_wave5_adjacent/report.md`
- Latest full harness output:
  `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`
- Latest full run summary: 145 cases; result statuses `ok: 129`,
  `no_result: 10`, `error: 6`; expectation cases `pass: 145`;
  expectation checks `pass: 746`; failed case IDs none; suspicious flag cases
  `0`; informational flag cases `76` (`frontend_hero_expected: 76`);
  verified outlier cases `1` (`top_performance_high_points: 1`).
- Recommended next phase: the corpus is now 145/145. Choose the next raw
  product direction explicitly: another corpus expansion wave, frontend
  hero/copy QA, targeted backend answer phrase enrichment, or one of the
  remaining P2 product-boundary families such as position-filtered
  leaderboards / count phrase quality.

## Corpus Expansion Wave 4 Status

Corpus Expansion Wave 4 broadened the manual QA corpus from 145 to 195 curated
cases. This was a corpus/docs/review wave only: no production query behavior,
frontend rendering, backend answer metadata, harness logic, or source data was
changed.

Coverage strategy:

- Position/role/context aliases: position-filtered leaderboards, rookie/bench/
  starter leaderboard boundaries, and named-player starter/bench role contexts.
- Splits/comparisons: player and team home-away/wins-losses splits, player/team
  comparisons, head-to-head matchup records, and on/off unsupported behavior.
- Playoff/history/era: Finals/conference-finals record phrasing, playoff
  appearances/history, series-record phrasing, since-year and decade queries,
  and regular-season vs playoff-team guardrails.
- Stat aliases/advanced metrics: eFG%, turnovers, personal fouls, pace,
  defensive rating, points allowed/opponent PPG, AST%, and turnover rate.
- Context/filter combinations: explicit road season records, East/West-style
  opponent context, opponent-quality last season, since All-Star plus stat, and
  explicit-date no-match behavior.
- Unsupported boundaries: subjective defensive ranking, MVP/award opinion, and
  lineup membership without trusted lineup coverage.

Latest run:

- Run ID: `20260513T214500Z_wave4_full`
- Output path:
  `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.md`
- Cases: 195
- Result statuses: `ok: 172`, `no_result: 15`, `error: 8`
- Expectation cases: `pass: 181`, `fail: 14`
- Expectation checks: `pass: 953`, `fail: 48`
- Suspicious flag cases: 8
- Suspicious flags: `expected_ok_returned_non_ok: 2`,
  `expected_unsupported_returned_ok: 6`
- Informational flag cases: 113
- Informational flags: `frontend_hero_expected: 113`
- Verified outlier cases: 1
- Verified outliers: `top_performance_high_points: 1`

New finding summary:

- AQ-018: position/role-filtered leaderboards and role/team-scope broad
  fallbacks
- AQ-019: explicit player comparison wording routing to a player-game finder
- AQ-020: playoff round-record and playoff matchup-record phrasing gaps
- AQ-021: defensive/opponent-points alias gaps
- AQ-022: unsupported personal-foul stat alias fallback
- AQ-023: opponent-conference context filters falling back to full-season
  records

Recommended next phase:

- Do not start frontend hero/copy QA yet if product-answer correctness is the
  priority. Group the Wave 4 failures into fix families first, with P1 attention
  on playoff round/matchup routing and defensive/opponent-points aliases.
- Then triage P2 boundaries for position/role leaderboards, unsupported stat
  aliases, player comparison intent, and East/West opponent-conference filters.
- After those fixes or product decisions, rerun the 195-case corpus before
  starting frontend hero/copy QA.

## Fix Wave 6A Status

Fix Wave 6A resolved the defensive/opponent-points alias gap from AQ-021. This
was a focused alias/routing completion wave only: no playoff routing, frontend
rendering, backend answer-phrase enrichment, source data, or opponent-points
execution semantics changed.

Target cases:

- `most_points_allowed_team_leaders_wave4`
- `opponent_ppg_leaders_wave4`

Behavior now verified:

- `which teams allow the most points per game this season` routes to
  `season_team_leaders`, uses `opponent_pts_per_game`, sorts descending, and
  returns Utah as the current highest opponent-PPG team.
- `opponent PPG leaders this season` routes to `season_team_leaders`, uses
  `opponent_pts_per_game`, and returns team rows rather than player scoring
  leaders.
- `fewest_points_allowed_team_leader` still ranks `opponent_pts_per_game`
  ascending with Boston first.
- `def_rating_team_leaders_wave4` still maps to defensive rating rather than
  opponent points allowed.

Latest harness outputs:

- Targeted run:
  `outputs/raw_query_answer_qa/20260514T050605Z/report.md`
- Full corpus run:
  `outputs/raw_query_answer_qa/20260514T050631Z/report.md`

Full corpus result after Wave 6A:

- Cases: 195
- Result statuses: `ok: 172`, `no_result: 15`, `error: 8`
- Expectation cases: `pass: 183`, `fail: 12`
- Expectation checks: `pass: 964`, `fail: 45`
- Remaining failed case IDs: `centers_rebound_leaders_wave4`,
  `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`,
  `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`,
  `lebron_durant_comparison_wave4`, `bulls_finals_record_wave4`,
  `warriors_finals_record_since_2015_wave4`,
  `celtics_conference_finals_record_wave4`,
  `heat_knicks_playoff_series_record_wave4`,
  `personal_foul_leaders_wave4`, `celtics_against_east_record_wave4`

Remaining families:

- AQ-020 playoff round/matchup routing remains open.
- P2 position/role leaderboards, player comparison routing, personal-foul
  stat boundary, and opponent-conference filters remain open.

## Fix Wave 6B Status

Fix Wave 6B resolved AQ-020 as a focused playoff routing and product-boundary
wave. It did not change defensive/opponent-points aliases, frontend rendering,
backend answer-phrase enrichment, source data, or playoff round-record
execution.

Target cases:

- `heat_knicks_playoff_series_record_wave4`
- `bulls_finals_record_wave4`
- `warriors_finals_record_since_2015_wave4`
- `celtics_conference_finals_record_wave4`

Behavior now verified:

- `Heat Knicks playoff series record` routes to `playoff_matchup_history` with
  `team_a=MIA` and `team_b=NYK`, matching the existing
  `Heat vs Knicks playoff history` result family.
- `Bulls Finals record`, `Warriors Finals record since 2015`, and
  `Celtics conference finals record` no longer return broad regular-season
  `team_record` answers.
- Single-team playoff round records are an explicit unsupported boundary for
  now: these queries return `no_result` / `filter_not_supported` with
  `unsupported_filters=["single_team_playoff_round_record"]`.
- Bulls Finals remains unsupported because current Bulls Finals-era rows are
  pre-2001 and do not have reliable round labels in the current dataset.

Latest harness outputs:

- Targeted AQ-020 run:
  `outputs/raw_query_answer_qa/20260514T113039Z_wave6b_aq020_targeted/report.md`
- Adjacent playoff regression run:
  `outputs/raw_query_answer_qa/20260514T113039Z_wave6b_playoff_regression/report.md`
- Full corpus run:
  `outputs/raw_query_answer_qa/20260514T113039Z_wave6b_full/report.md`

Full corpus result after Wave 6B:

- Cases: 195
- Result statuses: `ok: 171`, `no_result: 16`, `error: 8`
- Expectation cases: `pass: 187`, `fail: 8`
- Expectation checks: `pass: 990`, `fail: 28`
- Remaining failed case IDs: `centers_rebound_leaders_wave4`,
  `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`,
  `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`,
  `lebron_durant_comparison_wave4`, `personal_foul_leaders_wave4`,
  `celtics_against_east_record_wave4`

Remaining families:

- AQ-018 position/role-filtered leaderboards and role/team-scope boundaries.
- AQ-019 explicit player comparison routing.
- AQ-022 personal-foul stat boundary.
- AQ-023 opponent-conference filters.

## Fix Wave 7A P2 Boundary / Routing Cleanup Status

Fix Wave 7A resolved the eight remaining Wave 6B expectation failures as a
focused P2 parser/routing and product-boundary cleanup. It did not change
frontend rendering, backend answer-phrase enrichment, source data, rookie
leaderboard execution, league-wide role leaderboard execution, team bench
scoring execution, personal-foul leaderboard execution, or opponent-conference
filter execution.

Behavior now verified:

- Position noun-prefix/question-form leaderboards such as
  `Which centers have the most rebounds this season?`, `guard scoring leaders
this season`, and `forwards FG% leaders this season` route to
  `season_leaders` with the canonical `position_filter` preserved.
- Full-name player comparisons such as
  `LeBron James vs Kevin Durant comparison` and
  `Compare LeBron James and Kevin Durant` route to `player_compare`.
- Player-game/opponent-player guardrails such as `Jokic game log vs Embiid`
  remain player finder queries.
- Rookie leaderboards, league-wide starter/bench leaderboards, team bench
  scoring, personal-foul leaderboards, and opponent-conference record filters
  now return `no_result` / `filter_not_supported` with explicit
  `unsupported_filters` instead of broad plausible answers.

Latest harness outputs:

- Targeted eight-case run:
  `outputs/raw_query_answer_qa/20260514T125005Z/report.md`
- Adjacent regression run:
  `outputs/raw_query_answer_qa/20260514T125038Z/report.md`
- Full corpus run:
  `outputs/raw_query_answer_qa/20260514T125056Z/report.md`

Full corpus result after Wave 7A:

- Cases: 195
- Result statuses: `ok: 165`, `no_result: 22`, `error: 8`
- Expectation cases: `pass: 195`
- Expectation checks: `pass: 1037`
- Suspicious flag cases: 0
- Informational flag cases: 112
- Verified outlier cases: 1
- Remaining failed case IDs: none

Current status:

- AQ-018: position noun-prefix support fixed; rookie/role/team-bench cases fixed
  as expected unsupported boundaries.
- AQ-019: fixed.
- AQ-022: fixed as expected unsupported.
- AQ-023: fixed as expected unsupported.

## Frontend Hero / Copy QA Wave 1 Status

Frontend hero/copy QA now has a report-first harness that renders selected
backend QA results through the actual React result components. This is a
separate frontend review layer; it does not change backend query behavior,
backend answer phrases, corpus expectations, or production frontend copy.

Approach:

- Selected corpus/config:
  `qa/frontend_copy_corpus.yaml`
- Source backend run:
  `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- Runner:
  `frontend/src/test/frontendCopyQaReport.test.tsx`
- Harness helper:
  `frontend/src/test/frontendCopyQaHarness.tsx`
- Intentional report command:
  `cd frontend && npm run qa:frontend-copy`
- Output path pattern:
  `outputs/frontend_copy_qa/<run_id>/`

The harness rehydrates backend QA JSONL rows into the frontend
`QueryResponse` envelope, renders `ResultEnvelope` plus `ResultRenderer`, and
extracts review-oriented visible copy:

- result shape/pattern
- hero/headline text
- supporting/context text
- applied filter chips
- result headings/titles
- table headers and first-row text
- no-result title/message/details/suggestions
- rendered notes/caveats
- report-only soft checks from the selected corpus config

Latest run:

- Run ID: `20260515T024718Z`
- Markdown report:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- JSONL report:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl`
- Summary:
  `outputs/frontend_copy_qa/20260515T024718Z/summary.json`
- Selected cases: 59
- Rendered successfully: 59
- Render failures: 0
- Missing backend records: 0
- Soft checks: `pass: 156`, `fail: 0`, `not_checked: 0`

Frontend Copy QA Fix Wave 1: Semantic Copy Cleanup status:

- FCQ-001 fixed at the source/backend layer. `guards_fg_percentage_leaders`
  now parses and executes with `position_filter=guards`, exposes a Position
  applied filter, and renders as a guard-filtered FG% leaderboard rather than
  a broad unfiltered leaderboard.
- FCQ-002 fixed in frontend leaderboard copy using structured
  `metadata.ascending`. Fewest-points-allowed leaderboards render
  `allowed the fewest points per game`; most-points-allowed/opponent-PPG
  leaderboards render high opponent scoring as `allowed the most points per
game`, not as best defense.
- FCQ-003 fixed in no-result primary guidance. Unsupported filters for
  personal-foul, rookie, league-wide starter/bench, and team bench-scoring
  boundaries now use boundary-specific human-readable messages instead of
  generic stat-unavailable copy such as `Pf is not available for this query`.
- Raw QA source run:
  `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- Frontend-copy run:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`

Review process:

1. Review the Markdown report by family, starting with the five report-only soft
   check misses and the high-risk categories: team defensive leaderboards,
   unsupported/no-result guidance, record-when conditions, playoff matchup
   phrasing, and comparison labels.
2. Record confirmed frontend-copy defects as frontend findings grouped by
   family. Do not treat a soft-check miss as a defect until reviewed.
3. Promote only stable, high-risk semantic failures into hard frontend tests
   near the component behavior they protect.
4. Keep screenshots/manual visual review separate for hierarchy, wrapping,
   layout, and visual emphasis.

## Frontend Screenshot / Visual QA Wave 1 Status

Frontend screenshot / visual QA Wave 1 now has a case-targeted manual baseline
surface for the 15 approved review cases. This is an internal QA layer only: it
does not change backend query behavior, production result rendering, or add any
Playwright/screenshot diff automation.

Artifacts and entry points:

- Visual corpus:
  `qa/frontend_visual_qa_corpus.yaml`
- Internal route/page:
  `/visual-qa`
- Page implementation:
  `frontend/src/VisualQaPage.tsx`
- Route wiring:
  `frontend/src/main.tsx`
- Screenshot helper reuse:
  `frontend/src/lib/reviewScreenshots.ts`
- Manual checklist:
  `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- Source raw QA run:
  `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- Source frontend-copy run:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl`

Page behavior:

- Reads the 15-case visual corpus and issues live `POST /query` calls through
  the existing frontend API client.
- Renders each case through the real product result composition:
  `ResultEnvelope` plus `ResultRenderer`.
- Exposes one stable capture target per case via
  `data-visual-case-id="<case_id>"`.
- Shows case metadata, visual-focus notes, desktop/mobile checklist items, and
  live backend route/result status when available.
- Reuses the existing browser-side screenshot ZIP helper for a manual
  current-viewport capture button, without adding Playwright.

Manual capture workflow:

1. Start the local backend that serves `/query`.
2. Start the frontend dev server and open `/visual-qa`.
3. Let all 15 cases load through live `/query` calls.
4. Capture a desktop pass at about `1280px` wide.
5. Capture a mobile pass at about `390px` wide.
6. Record pass/fail notes in the checklist doc and any follow-up review
   package.

Output artifact plan:

- Checklist source of truth:
  `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- Recommended screenshot storage after manual capture:
  `outputs/frontend_visual_qa/<run_id>/screenshots/desktop/<case_id>.png`
  and `outputs/frontend_visual_qa/<run_id>/screenshots/mobile/<case_id>.png`
- Recommended summary/report storage after manual review:
  `outputs/frontend_visual_qa/<run_id>/`

Next step:

- Capture and review the manual desktop/mobile baseline first.
- Do not add Playwright, pixel baselines, or screenshot diffing until the
  manual baseline has been reviewed and accepted.

## Frontend Screenshot / Visual QA Fix Wave 1 Status

Frontend Screenshot / Visual QA Fix Wave 1 targets the confirmed mobile-table
and filtered-leaderboard hero findings from the manual baseline review. It does
not change backend query behavior or raw answer contracts.

Confirmed findings addressed:

- FVQ-001 mobile dense table clipping: `biggest_scoring_games`,
  `lebron_durant_comparison_wave4`, and
  `heat_knicks_playoff_series_record_wave4`.
- FCQ/FVQ-002 filtered leaderboard hero context:
  `guards_fg_percentage_leaders` and `centers_rebound_leaders_wave4`.

Targeted frontend behavior:

- Top-performance mobile tables prioritize Rank, Player, Date, and the requested
  stat column so `PTS` remains visible without relying on horizontal scrolling.
- Comparison mobile tables keep Metric, both compared entities, and
  `Edge / Difference` visible, with long edge copy allowed to wrap.
- Playoff matchup mobile tables keep Season, Round, Winner, and
  `Series Result` visible; lower-priority team record and games columns remain
  desktop-visible.
- Position-filtered player leaderboard heroes use the existing structured
  `position_filter` / applied filter metadata, so guard and center examples say
  `led guards` / `led centers` instead of generic `led the NBA`.

Validation artifacts:

- Frontend-copy QA run:
  `outputs/frontend_copy_qa/20260515T224620Z/frontend_copy_report.md`
- Mobile local visual recheck screenshots:
  `/private/tmp/visualqa_mobile_biggest_scoring_games.png`,
  `/private/tmp/visualqa_mobile_lebron_durant_comparison_wave4_after_wrap.png`,
  `/private/tmp/visualqa_mobile_heat_knicks_playoff_series_record_wave4.png`,
  `/private/tmp/visualqa_mobile_guards_fg_percentage_leaders.png`, and
  `/private/tmp/visualqa_mobile_centers_rebound_leaders_wave4.png`

## Open Questions

- Should future frontend-copy waves expand from the hand-curated 59-case list
  into all 112 `frontend_hero_expected` informational cases? Recommendation:
  review Wave 1 findings first, then expand only the families that need more
  coverage.
- Should the backend QA harness continue using backend shape approximations now
  that frontend-copy QA extracts exact rendered shapes with Vitest? Recommendation:
  yes; keep backend QA transport-agnostic and keep frontend shape extraction in
  the frontend harness.
- Should exact hero sentences ever become hard assertions? Recommendation: only after a separate rendered-output harness exists and only for targeted regressions.
