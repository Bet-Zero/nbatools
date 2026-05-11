# Raw Query Answer QA Harness Wave 1 Return Package

## 1. Executive summary

- What was built: a Python QA harness that runs a curated natural-language query corpus through the backend query service, converts results through the API payload helper, and writes JSONL, Markdown, and summary reports for answer-quality review.
- Production code changed? no
- Tests changed? no
- Corpus size: 12 cases
- Output files generated: `outputs/raw_query_answer_qa/20260511T035224Z/report.jsonl`, `outputs/raw_query_answer_qa/20260511T035224Z/report.md`, `outputs/raw_query_answer_qa/20260511T035224Z/summary.json`
- Main limitation: Wave 1 captures only backend-provided `answer_phrase` / `count_phrase` and backend-approximate `shape_hint`; exact frontend hero and visual shape rendering are deferred.
- Recommended next step: ChatGPT/manual review of `outputs/raw_query_answer_qa/20260511T035224Z/report.md`.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/raw_query_answer_corpus.yaml` | Added | Curated Wave 1 answer-QA corpus with expected status, route, shape, sections, filters, row counts, and hard path assertions. |
| `tools/raw_query_answer_qa.py` | Added | Backend/product QA harness that executes corpus cases and writes `report.jsonl`, `report.md`, and `summary.json`. |
| `Makefile` | Modified | Added `raw-query-answer-qa` target for the harness. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Modified | Added Wave 1 implementation status, output location, run commands, and limitations. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_WAVE_1_RETURN_PACKAGE.md` | Added | Records implementation details, validation, first-run findings, and next step. |

## 3. Corpus design

- Required fields: `id`, `query`, `category`, `priority`, `expected_status`
- Optional fields: `expected_route`, `expected_reason`, `expected_shape`, `expected_filters`, `expected_sections`, `expected_row_counts`, `hard_assertions`, `review_notes`
- Initial categories covered: record-when player condition, player game-log/count, leaderboard, top performances, team record, without-player condition, rolling stretch, streak, playoff history, playoff matchup history, no-result date, unsupported boundary
- Why these cases were chosen: they cover the product families named in the plan and prompt, include recent visual-QA regressions such as the Denver/Jokic triple-double record, exercise backend metadata phrases, and include both honest no-result and unsupported/unrouted boundary behavior.

## 4. Harness behavior

- Execution path: each case calls `src/nbatools/query_service.py::execute_natural_query(query)` in process.
- Payload conversion: each `QueryResult` is converted through `src/nbatools/api_handlers.py::query_result_to_payload(qr)`, matching the API envelope consumed by the UI.
- Shape hint policy: `shape_hint` is inferred from backend route plus section presence and is always marked `shape_source: backend_approximation`.
- Answer text policy: `answer_text` is populated only from backend `metadata.answer_phrase` or `metadata.count_phrase`; otherwise it is `null`. The harness does not fabricate or import frontend hero text.
- Expectation checks: expected status, route, reason, shape, section presence, section row counts, applied filters, and simple dot-path equality through dict/list payloads.
- Error handling: per-query exceptions produce an error row with failed expectation results and do not abort the run.

## 5. Generated output sample

- Output directory: `outputs/raw_query_answer_qa/20260511T035224Z/`
- Summary counts: 12 cases; statuses `ok: 10`, `no_result: 1`, `error: 1`; expectation cases `pass: 12`; expectation checks `pass: 78`; failed case IDs `[]`.

Sample passing correctness case:

```json
{
  "id": "record_when_jokic_triple_double",
  "query": "What is Denver's record when Nikola Jokic has a triple-double?",
  "route": "player_game_summary",
  "result_status": "ok",
  "shape_hint": "entity_summary",
  "answer_text": null,
  "applied_filters": [{"label": "Special Event", "value": "Triple Double", "kind": "special_event"}],
  "section_summaries": {
    "summary": {"row_count": 1},
    "game_log": {"row_count": 34}
  },
  "expectation_results": {"status": "pass", "pass_count": 10, "fail_count": 0}
}
```

Sample unsupported/no-result boundary case:

```json
{
  "id": "cooled_off_last_10",
  "query": "Which scorers have cooled off over their last 10 games?",
  "route": null,
  "result_status": "error",
  "result_reason": "unrouted",
  "shape_hint": "error",
  "applied_filters": [{"label": "Last N games", "value": "10", "kind": "window"}],
  "section_summaries": {},
  "expectation_results": {"status": "pass", "pass_count": 5, "fail_count": 0}
}
```

## 6. Validation

Command:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --limit 5
```

Output summary:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260511T035157Z
Cases: 5
Result statuses: {'ok': 5}
Expectation cases: {'pass': 5}
Failed case IDs: none
```

Command:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
```

Output summary:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260511T035206Z
Cases: 12
Result statuses: {'error': 1, 'no_result': 1, 'ok': 10}
Expectation cases: {'pass': 12}
Failed case IDs: none
```

Command:

```bash
make raw-query-answer-qa
```

Output summary:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260511T035224Z
Cases: 12
Result statuses: {'error': 1, 'no_result': 1, 'ok': 10}
Expectation cases: {'pass': 12}
Failed case IDs: none
```

Additional check:

```bash
.venv/bin/ruff check tools/raw_query_answer_qa.py
```

Output:

```text
All checks passed!
```

Required final check:

```bash
git diff --check
```

Output:

```text
No whitespace errors.
```

## 7. Findings from first run

- Failed expectations: none. All 12 cases passed their Wave 1 expectations.
- Suspicious outputs:
  - `record_when_jokic_triple_double` returns the correct 34-game, 24-10 filtered sample, but no backend `answer_phrase`; frontend hero exactness remains deferred.
  - `celtics_record_playoff_teams` currently returns a `team_record` payload with playoff-season context and a caveat about filtering to games vs 20 opponents. This should be manually reviewed as a product-semantics question.
  - `biggest_scoring_games` surfaces an 83-point Bam Adebayo row; manual review should decide whether this is expected data or a data-quality outlier worth a hard test or data audit.
  - `cooled_off_last_10` is an expected unsupported/unrouted boundary, but the user-facing severity remains a product-copy question noted in visual QA.
- Cases that should be reviewed manually: all P0/P1 cases in `report.md`, especially `record_when_jokic_triple_double`, `suns_without_booker`, `celtics_record_playoff_teams`, and `biggest_scoring_games`.
- Candidates for promotion to hard tests: Denver/Jokic triple-double record `games=34`, `wins=24`, `losses=10`; Jokic triple-double count `count=34`; Suns without Booker record `games=18`, `wins=8`, `losses=10`; required `Special Event: Triple Double` applied filter metadata.

## 8. Recommended next step

Next step should be ChatGPT/manual review of `outputs/raw_query_answer_qa/20260511T035224Z/report.md`, followed by targeted hard-test promotion for objective correctness cases.
