# Raw QA Harness Efficiency Wave 1 Return Package

## 1. Executive summary

- What changed:
  - Added saved Raw QA harness slices via `--slice`.
  - Added prior-failure reruns via `--failed-from`.
  - Added non-gating run comparison metadata via `--compare-to`.
  - Added per-case `duration_seconds` and top-10 `slowest_cases` reporting.
  - Added focused query-free harness tests for selection, prior-failure parsing,
    comparison, and timing summary helpers.
- Production code changed? no
- Tests changed: yes, `tests/test_raw_query_answer_qa.py`
- Corpus expectations changed? no
- New CLI options: `--slice`, `--failed-from`, `--compare-to`
- Slice files added:
  - `qa/harness_slices/defensive_aliases.yaml`
  - `qa/harness_slices/playoff_phrasing.yaml`
  - `qa/harness_slices/team_date_context.yaml`
  - `qa/harness_slices/player_entity_stat_context.yaml`
  - `qa/harness_slices/product_boundaries.yaml`
- Latest full corpus run: `outputs/raw_query_answer_qa/20260517T033806Z`
- Main workflow benefit: repeated target/adjacent Raw QA loops can now use
  stable slice names, rerun only prior failures, and compare against a clean run
  without manual case-list or summary diff work.
- Remaining risk: timing is environment-dependent, and comparison count deltas
  are most meaningful when the current run and reference run have similar case
  scopes.

## 2. New harness capabilities

| Capability | Description | Example command |
|---|---|---|
| Saved slices | Selects cases from `qa/harness_slices/<name>.yaml` or a direct YAML path; validates all IDs and preserves corpus order. | `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries` |
| Prior-failure rerun | Reads `failed_case_ids` from `summary.json` or failed `expectation_results` rows from `report.jsonl`. | `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --failed-from outputs/raw_query_answer_qa/20260516T112341Z/summary.json` |
| Run comparison | Writes `comparison` into `summary.json` and a comparison section into `report.md`; does not affect exit status. | `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --compare-to outputs/raw_query_answer_qa/20260516T221654Z/report.jsonl --case record_when_jokic_triple_double` |
| Per-case timing | Adds `duration_seconds` to every `report.jsonl` row. | Included on every run. |
| Slowest cases | Adds top-10 `slowest_cases` to `summary.json` and `report.md`. | Included on every run. |

## 3. Slice inventory

| Slice | Cases | Purpose |
|---|---:|---|
| `defensive_aliases` | 8 | Defensive/opponent-points stat alias and opponent-threshold regression cases. |
| `playoff_phrasing` | 12 | Playoff history, matchup, Finals, and round-record phrasing cases. |
| `team_date_context` | 9 | Team record cases with road, date, month, season, and recent context. |
| `player_entity_stat_context` | 9 | Player entity, stat alias, count/finder, and recent-context cases. |
| `product_boundaries` | 11 | Explicit unsupported/no-result product-boundary and stat-contract cases. |

## 4. Behavior validation

- `--case` validation:
  - Command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case record_when_jokic_triple_double --case points_per_game_leader`
  - Output: `outputs/raw_query_answer_qa/20260517T033603Z`
  - Result: 2 cases; result statuses `ok: 2`; expectation cases `pass: 2`; failed case IDs none.
- `--slice` validation:
  - Command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries`
  - Output: `outputs/raw_query_answer_qa/20260517T033619Z`
  - Result: 11 cases; result statuses `no_result: 3`, `ok: 8`; expectation cases `pass: 11`; failed case IDs none.
- All saved slice ID validation:
  - Command: helper load of all five saved slices through
    `collect_selected_case_ids()` and `filter_cases()`.
  - Result: 49 unique slice IDs; 49 corpus-selected cases; no unknown IDs.
- `--failed-from` validation:
  - Command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --failed-from outputs/raw_query_answer_qa/20260516T112341Z/summary.json`
  - Output: `outputs/raw_query_answer_qa/20260517T033644Z`
  - Result: selected `players_personal_fouls_wave5` and `warriors_net_rating_single_team_wave5`; 2 cases; result statuses `no_result: 2`; expectation cases `pass: 2`; failed case IDs none.
- `--compare-to` validation:
  - Command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --compare-to outputs/raw_query_answer_qa/20260516T221654Z/report.jsonl --case record_when_jokic_triple_double`
  - Output: `outputs/raw_query_answer_qa/20260517T033746Z`
  - Result: 1 case; expectation cases `pass: 1`; `summary.json` includes `comparison`; `report.md` includes the comparison section; failed case IDs none.
- Full corpus validation:
  - Command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
  - Output: `outputs/raw_query_answer_qa/20260517T033806Z`
  - Result: 243 cases; result statuses `error: 9`, `no_result: 32`, `ok: 202`; expectation cases `pass: 243`; failed case IDs none.
- Duration/slowest reporting confirmation:
  - `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl` rows include `duration_seconds`.
  - `outputs/raw_query_answer_qa/20260517T033806Z/summary.json` includes `slowest_cases`.
  - `outputs/raw_query_answer_qa/20260517T033806Z/report.md` includes the slowest-case table.

## 5. Tests/static validation

- Harness unit tests:
  - `.venv/bin/pytest tests/test_raw_query_answer_qa.py -n0`
  - Result: 16 passed.
- Ruff:
  - `.venv/bin/ruff check tools/raw_query_answer_qa.py tests/test_raw_query_answer_qa.py`
  - Result: all checks passed.
- Static whitespace:
  - `git diff --check`
  - Result: passed with no output.

## 6. Files changed

| File | Change type | Why |
|---|---|---|
| `tools/raw_query_answer_qa.py` | Modified | Add slice selection, failed-from parsing, comparison metadata, per-case timing, and slowest-case report sections. |
| `tests/test_raw_query_answer_qa.py` | Modified | Add query-free unit coverage for harness mechanics. |
| `qa/harness_slices/defensive_aliases.yaml` | Added | Saved adjacent slice for defensive/opponent-points alias work. |
| `qa/harness_slices/playoff_phrasing.yaml` | Added | Saved adjacent slice for playoff phrasing work. |
| `qa/harness_slices/team_date_context.yaml` | Added | Saved adjacent slice for team/date context work. |
| `qa/harness_slices/player_entity_stat_context.yaml` | Added | Saved adjacent slice for player/entity/stat context work. |
| `qa/harness_slices/product_boundaries.yaml` | Added | Saved adjacent slice for product-boundary checks. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Modified | Document new options, slice schema, tiered validation flow, and example commands. |
| `return_packages/raw-product/RAW_QA_HARNESS_EFFICIENCY_WAVE_1_RETURN_PACKAGE.md` | Added | Capture implementation and validation evidence for this tooling wave. |

## 7. How to use going forward

Target run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case record_when_jokic_triple_double --case points_per_game_leader
```

Adjacent slice run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries
```

Failed-from rerun:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --failed-from outputs/raw_query_answer_qa/<run_id>/summary.json
```

Compare to prior clean run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --compare-to outputs/raw_query_answer_qa/20260516T221654Z/report.jsonl --case record_when_jokic_triple_double
```

Final full corpus run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
```

## 8. Next recommendation

Next: frontend-copy corpus expansion using the new slice/compare support as the
backend safety loop. Tag/category filters remain useful later, but saved slices
now cover the current target/adjacent workflow with lower overhead.
