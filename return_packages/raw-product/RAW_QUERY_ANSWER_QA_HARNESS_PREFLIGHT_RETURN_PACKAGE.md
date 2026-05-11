# Raw Query Answer QA Harness Preflight Return Package

## 1. Executive summary

- Existing infrastructure found: `docs/architecture/parser/examples.md` is the review-query source; `src/nbatools/parser_examples.py` extracts 402 cases; `/review` fetches only case IDs/query text from `/api/dev/fixtures` and runs live `/query` calls; `tools/parser_examples_full_sweep.py` can run the same broad corpus through the CLI and write ignored reports.
- Biggest useful reuse: call `execute_natural_query()` and convert with `query_result_to_payload()` to get the same structured API envelope the UI consumes.
- Biggest gap: there is no curated answer-correctness corpus or report format. Existing expectations are route/status-oriented, generated/heuristic, or scattered as test assertions.
- Recommended next step: implement a small Python harness over a curated YAML corpus, writing JSONL and Markdown reports under `outputs/raw_query_answer_qa/`.
- Production code changed? no
- Tests changed? no

## 2. Existing query/example sources

| File/path | Type | Contains | Useful for harness? | Notes |
|---|---|---|---|---|
| `docs/architecture/parser/examples.md` | Hand-authored parser example library | 100 canonical examples, 100 paired question/search examples, capability clusters, stress inputs, worked examples, equivalence groups, expansion boundaries | Yes, as broad seed material | This is the source for the 402 review fixtures. It is not a correctness corpus; it intentionally includes unsupported, ambiguous, and stress cases. |
| `src/nbatools/parser_examples.py` | Extractor | `extract_cases()` parses `examples.md` into `Case` objects with stable IDs, query text, source section, kind, expected behavior category, and notes | Yes | `/review` uses the IDs/query text only. Expected categories are heuristic, derived from source section and keywords. |
| `src/nbatools/api_handlers.py` | API payload helper | `dev_fixtures_payload()` returns `source_path` and fixture `{case_id, query}` from `extract_cases()` | Yes | This is the backend source for `/api/dev/fixtures`; expected fields are intentionally stripped. |
| `src/nbatools/api.py` | FastAPI layer | `GET /api/dev/fixtures`, `POST /query`, `POST /structured-query` | Yes | Local `/review` and app UI use these paths. |
| `api/dev/fixtures.py` | Vercel function | Vercel wrapper for `dev_fixtures_response()` | Limited | Same fixture list for preview deployments. |
| `frontend/src/ReviewPage.tsx` | Review UI | Fetches fixtures, executes live queries, groups loaded results by frontend shape | Yes, for flow/shape reuse | Caches results in browser `localStorage`; no static result fixture file. |
| `tools/parser_examples_full_sweep.py` | Generated sweep runner | Runs all extracted cases through `nbatools-cli ask --json`, writes CSV/report/raw JSON, grades broad expected behavior | Yes, as prior art | The scoring is useful but duplicated with `parser_examples.py`; output is ignored under `outputs/`. |
| `outputs/parser_examples_full_sweep/` | Ignored generated artifacts | `results.csv`, `report.md`, `manifest.json`, and 402 raw JSON captures from a prior sweep | Useful evidence, not source of truth | `outputs/` is gitignored. Current local report is dated `2026-05-10T08:05:05Z` and shows 401/402 passing under broad parser-sweep rules. |
| `docs/operations/parser_examples_full_sweep_protocol.md` | Operations protocol | Defines full parser-example sweep scope, artifact paths, expected categories, and pass/fail rules | Yes | Good template for report structure, but answer QA needs richer row/metadata/answer extraction. |
| `tests/_query_smoke.py` | Curated smoke corpus | Stable and phase query cases with expected route, query class, status, intent, and note fragments | Yes | Good seed for durable product cases. Marked `needs_data` through consuming tests. |
| `tests/test_query_smoke_stable.py` | Smoke tests | Runs stable cases through CLI and API | Yes, for hard-test pattern | Partial expectations only. |
| `tests/test_query_smoke_phase.py` | Smoke tests | Runs phase cases through CLI and API | Yes, for hard-test pattern | Broader than stable smoke but still route/status focused. |
| `docs/reference/query_catalog.md` | Current-state reference | Supported query types and common phrasing patterns | Yes, for selecting corpus categories | Reference doc, not executable fixture source. |
| `docs/reference/query_guide.md` | User/reference guide | Structured and natural query examples | Some | Useful for seed examples, but not expectation storage. |
| `docs/reference/quick_query_guide.md` | User guide | Quick examples for trying queries | Some | Useful for high-confidence manual-review cases. |
| `README.md` | User overview | High-level usage examples | Some | Good sanity cases, not a harness source. |
| `docs/planning/raw-product/RAW_QUERY_PRODUCT_MAP.md` | Product map | Route inventory, route-to-shape mapping, display pattern inventory | Yes | Strong shape/report context for harness planning. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Result/table contract | Route/shape/table contract examples and expected section families | Yes | Best reference for section and table summaries. |
| `docs/output_shapes.md` | Shape taxonomy snapshot | Shape-level renderer taxonomy and old sweep counts | Some | Counts are from an older ignored sweep; useful as context, not current truth. |
| `tests/test_ui_failure_coverage.py` | Regression tests | Exact needs-data regressions for known product failures, including Denver/Jokic `24-10` | Yes, for promotion targets | Good model for future hard backend answer tests. |
| `tests/test_query_service.py` | Service tests | QueryResult envelope, metadata preservation, no-result/error behavior, export/render paths | Yes | Contains both data-free and needs-data tests. |
| `tests/test_core_result_table_contracts.py` | Contract tests | Structured result section keys by result class/route family | Yes | Fast output-marker tests; no live query execution. |
| `tests/test_result_contract.py` and `tests/test_result_contracts.py` | Contract/output tests | Result status, raw output, natural query contract behavior | Yes | Some tests are broad/needs-data and better as regression backstops than QA-harness code. |
| `frontend/src/test/ResultRenderer.test.tsx` | Frontend renderer fixtures | Mocked API payloads and exact rendered hero/table assertions | Yes, later | Best place for promoted frontend hero regressions; not a live backend corpus. |
| `frontend/src/test/resultShapes.test.ts` | Shape tests | Mocked API payloads classified by frontend shape | Yes, for exact shape logic | Shape classification is frontend-only today. |
| `frontend/src/test/ReviewPage.test.tsx` | Review-page tests | Fixture loading, manual execution, concurrency, cache version, screenshot target behavior | Yes | Good coverage of review flow and cache behavior. |
| `frontend/src/test/LayoutPrimitives.test.tsx` | Layout/chip tests | Applied-filter chip rendering, including `Special Event: Triple Double` | Yes, later | Useful when promoting metadata/chip regressions. |

Answers:

- Current review queries are sourced from `docs/architecture/parser/examples.md` through `extract_cases()`.
- There is an `examples.md` file, at `docs/architecture/parser/examples.md`; there is no root-level `examples.md`.
- The repo does not contain a tracked literal list of 402 review fixtures. The 402 cases are generated deterministically from the Markdown file.
- The 402 fixtures are hand-authored as examples in Markdown, then generated/parameterized by the extractor into cases.
- Expected results are not centrally stored. Existing expectations are heuristic categories in `parser_examples.py`, partial route/status expectations in tests, exact assertions inside targeted tests, and ignored generated sweep captures under `outputs/`.
- Expected results are mostly partial or implicit. Exact values exist only in specific regression tests, not in a corpus.
- The current local ignored sweep does not show exactly 25 no-result and 86 error/unsupported fixtures. It shows 73 `no_result`, 38 `error`, and 85 `error` or unsupported-like results (`error`, `unsupported`, or `filter_not_supported`). These are mixed but mostly intentional under the parser-sweep scoring: 401/402 pass. They include honest no-match cases for supported queries, coverage-gated no-results, expected ambiguous/unsupported cases, and expected unrouted stress failures.

## 3. Review page / fixture flow

- Query source: `frontend/src/ReviewPage.tsx` calls `fetchDevFixtures()`, which requests `/api/dev/fixtures`; FastAPI and Vercel both route that to `dev_fixtures_payload()`, which calls `extract_cases()`.
- Execution path: `/review` does not read static result fixtures. It posts each fixture query to live `/query` through `postQuery()`.
- Cache behavior: browser `localStorage` cache only. Keys are `nbatools.review:v2:<case_id>:<query>`. Cached values are either `{data: QueryResponse}` or `{error: string}`. Cache clearing removes keys under the current `v2` prefix.
- Shape grouping: after each query returns, `ReviewPage` calls `classifyResultShape(result.data)` and groups entries by `shape.key`; groups are sorted by `RESULT_SHAPE_ORDER`.
- Shape count: the displayed shape count is `sortedShapeGroups.length`, computed client-side from currently loaded live/cached results. "19 shapes" is not persisted as a backend fact.
- Reuse recommendation: reuse the fixture source and backend execution idea, but avoid relying on browser `localStorage` or React rendering for Wave 1. A backend report can include `shape_hint`; exact visual shape/hero can be a later frontend pass.

## 4. Backend execution path

- Best function/CLI to call: call `src/nbatools/query_service.py::execute_natural_query(query)` in process, then pass the `QueryResult` to `src/nbatools/api_handlers.py::query_result_to_payload(qr)`.
- Metadata available: route, query class, season/date context, player/team/opponent identity context, applied filters, count/answer phrase metadata where present, confidence, intent, alternates, notes, caveats, and section rows.
- Hero/answer source: mostly frontend-side in pattern components such as `EntitySummaryResult`, `LeaderboardResult`, `RecordResult`, `GameLogResult`, and others. Backend metadata sometimes provides `count_phrase` and `answer_phrase`; CLI pretty output is separate and not the UI hero contract.
- Shape availability: exact shape is frontend-side via `classifyResultShape()` and `routeToPattern()`. Backend can provide a route/section-based approximation only.
- Batch safety concerns: in-process sequential calls are appropriate. The service reads local data and uses caches such as identity lookups; it should not mutate production data. Avoid concurrent execution in Wave 1 because the value is report quality, not throughput, and the 402-case sweep is already expensive.

Fields a QA report should extract from the backend result:

- query ID and query text
- route, intent, query class/family, confidence, alternates
- top-level status/reason/ok/current_through
- backend answer text if present (`count_phrase`, `answer_phrase`)
- metadata, especially identity context, applied filters, occurrence event, thresholds, timeframe, and notes
- sections returned
- row counts per section
- columns per section
- top rows per section, capped
- single summary rows
- notes, caveats, errors
- expectation check results

## 5. Existing tests

| File/path | What it checks | Useful for future hard tests? | Notes |
|---|---|---|---|
| `tests/_query_smoke.py` | Shared stable/phase query cases and assertion helpers for CLI/API smoke | Yes | Best current curated query list. Partial route/status/query_class/intent expectations. |
| `tests/test_query_smoke_stable.py` | Runs stable smoke queries through real CLI and API | Yes | `needs_data`; frequent enough for product-sanity, not answer-detail QA. |
| `tests/test_query_smoke_phase.py` | Runs phase smoke queries through real CLI and API | Yes | `needs_data`; broader and phase-focused. |
| `tests/test_ui_failure_coverage.py` | Known parser/product failure regressions, including exact W-L and row-count checks | Yes | Strong model for promoted hard correctness tests. |
| `tests/test_query_service.py` | QueryResult envelope, metadata, identity context, notes, no-result/error behavior, exports | Yes | Some tests are data-free; many natural-query cases need data. |
| `tests/test_core_result_table_contracts.py` | Structured result section keys and route/result/table contracts | Yes | Fast, output-marker, does not execute live queries. |
| `tests/test_result_contract.py` | Structured result status/envelope behavior and no-data status behavior | Yes | Good for status contract regressions. |
| `tests/test_result_contracts.py` | Natural-query raw output/result contract behavior across many route families | Yes, selectively | Broad and `needs_data`; better for route-contract promotion than harness runtime. |
| `tests/test_natural_query_parser.py` | Parser slot/routing behavior | Some | Parser-only; not answer correctness. |
| `tests/test_parser_equivalence_groups.py` | Equivalence groups from `examples.md` | Some | Parser parity, not backend answer correctness. |
| `tests/test_query_intent.py` and `tests/test_parse_confidence.py` | Intent/confidence behavior | Some | Data-free parser confidence checks. |
| `tests/test_*_queries.py` route-family files | Many natural query and route-family assertions | Yes, selectively | Hard expectations are spread across files; future promoted tests should live near their route family. |
| `frontend/src/test/ResultRenderer.test.tsx` | Mocked result rendering, heroes, tables, exact visual text regressions | Yes | Best home for exact frontend hero tests. |
| `frontend/src/test/resultShapes.test.ts` | Frontend result-shape classification over mocked API responses | Yes | Use when exact shape classification becomes a hard requirement. |
| `frontend/src/test/ReviewPage.test.tsx` | Review flow, cache namespace, concurrency, screenshots | Some | Protects review UI, not answer correctness. |
| `frontend/src/test/LayoutPrimitives.test.tsx` | Envelope chips and layout primitives | Yes | Good home for applied-filter chip rendering regressions. |

Test answers:

- Tests that already run example queries: `test_query_smoke_*`, many route-family `tests/test_*_queries.py`, `test_query_service.py`, `test_ui_failure_coverage.py`, `test_result_contracts.py`, and the full-sweep script outside pytest.
- Exact outputs: targeted tests such as the Denver/Jokic `24-10` regression and frontend renderer hero tests.
- Structure/sections/routes only: smoke tests, core result table contracts, many query-service/API tests.
- Need data access: smoke tests and most live `execute_natural_query()` route-family tests are marked `needs_data`.
- Fast enough for frequent use: data-free parser tests, `test_core_result_table_contracts.py`, focused query-service unit tests, frontend component tests.
- Too broad/slow for QA harness runtime: `make test-query`, full `test_result_contracts.py`, full parser example sweep, and broad route-family suites.
- Known failure/no-result tests: no-result/error status tests in `test_query_service.py`, `test_result_contract.py`, `test_ui_failure_coverage.py`, frontend no-result tests, and expected unsupported/ambiguous cases in parser-example sweep scoring.
- Future hard regression tests should live near the behavior: backend route/data tests for answer correctness, `test_query_service.py`/`test_api.py` for envelope metadata, and `frontend/src/test/ResultRenderer.test.tsx` for rendered heroes.

## 6. Recommended corpus schema

Required now: `id`, `query`, `category`, `priority`, `expected_status`.

Useful now: `expected_route`, `expected_reason`, `expected_shape`, `expected_filters`, `expected_sections`, `expected_row_counts`, `hard_assertions`, `review_notes`.

Wait: exact frontend hero snapshots and broad row snapshots.

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
    expected_sections: [summary, game_log]
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
    review_notes: "Must not regress to stale 65-game, 43-22 unfiltered answer."

  - id: top_scorers_this_season
    query: "Who leads the NBA in points per game this season?"
    category: leaderboard
    priority: p1
    expected_status: ok
    expected_route: season_leaders
    expected_shape: leaderboard_table
    expected_sections: [leaderboard]

  - id: cooled_off_unsupported
    query: "Which scorers have cooled off over their last 10 games?"
    category: unsupported_boundary
    priority: p2
    expected_status: [no_result, error]
    expected_reason: [unsupported, unrouted]
    review_notes: "Intentional unsupported/trend-definition boundary."
```

## 7. Recommended report format

JSONL row example:

```json
{"id":"record_when_jokic_triple_double","query":"What is Denver's record when Nikola Jokic has a triple-double?","category":"record_when_player_condition","priority":"p0","route":"player_game_summary","intent":"summary","query_class":"summary","result_status":"ok","result_reason":null,"ok":true,"answer_text":null,"answer_text_source":null,"shape_hint":"entity_summary","shape_source":"backend_approximation","applied_filters":[{"label":"Special Event","value":"Triple Double","kind":"special_event"}],"section_summaries":{"summary":{"row_count":1,"columns":["player_name","games","wins","losses","win_pct"],"top_rows":[{"player_name":"Nikola Jokic","games":34,"wins":24,"losses":10,"win_pct":0.706}]},"game_log":{"row_count":34,"columns":["game_date","team_abbr","opp_abbr","wl","pts","reb","ast"],"top_rows":[{"team_abbr":"DEN","wl":"W","pts":32,"reb":14,"ast":10}]}},"notes":[],"caveats":[],"errors":[],"expectation_results":{"status":"pass","checks":[{"name":"expected_status","status":"pass"},{"name":"expected_route","status":"pass"},{"name":"result.sections.summary.0.games","status":"pass"}]}}
```

Markdown example:

```md
## Summary

- Cases: 12
- Passed expectations: 11
- Failed expectations: 1
- Result statuses: ok 9, no_result 2, error 1

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

| Section | Rows | Columns |
|---|---:|---|
| summary | 1 | player_name, games, wins, losses, win_pct |
| game_log | 34 | game_date, team_abbr, opp_abbr, wl, pts, reb, ast |
```

## 8. Recommended Execution Wave 1 scope

Create in the future execution:

- `qa/raw_query_answer_corpus.yaml`
- `tools/raw_query_answer_qa.py`

Modify in the future execution:

- `Makefile` with `raw-query-answer-qa`

Do not modify in Wave 1:

- production query behavior
- frontend rendering behavior
- existing parser examples
- existing hard tests

Acceptance criteria:

- Reads a YAML corpus.
- Runs each query through `execute_natural_query()`.
- Converts each result through `query_result_to_payload()`.
- Writes `report.jsonl`, `report.md`, and `summary.json` under `outputs/raw_query_answer_qa/<run_id>/`.
- Extracts route, intent, query class, status, reason, backend answer text when present, metadata, applied filters, sections, row counts, columns, top rows, notes, caveats, and query errors.
- Supports expectation checks for status, route, reason, sections, row counts, applied filters, and simple path equality.
- Includes at least 10 seed cases spanning record-when, entity summary, leaderboard, finder/count, team record, playoff/history, no-result, and unsupported boundary examples.
- Continues after per-query exceptions and records them in the report.
- Does not require frontend or browser execution.

Validation commands for the future execution:

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

## 9. Open questions / risks

- Exact frontend hero text is not available from the backend for most routes. Wave 1 should store backend-provided phrases only and leave frontend rendering to a later pass.
- Exact frontend shape classification is TypeScript/React-side. Wave 1 should use backend `shape_hint`; exact shape parity can be added later if needed.
- The 402 parser examples include unsupported and stress cases by design. Importing them wholesale would produce noisy answer QA. Start with a curated corpus.
- Some expectations depend on current data freshness. Hard assertions should be limited to deterministic known cases or moved into needs-data regressions with clear ownership.
