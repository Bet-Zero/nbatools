# Raw Query Answer QA Fix Wave 8B: Playoff Phrasing Routing Return Package

## 1. Executive summary

- What was wrong: hyphenated playoff round phrases such as `second-round` were not matched by the playoff round detector, so `best second-round record since 2010` fell through to regular-season `team_record_leaderboard`. `playoff matchup history` also did not count as playoff-history intent, so adjacent Lakers/Celtics team parsing fell through to current-season playoff `team_compare`.
- What changed: normalized hyphens only inside known playoff round phrases before round alias matching; added third-round aliases for round-code parity; expanded playoff-history intent to include `playoff matchup history`, `playoff matchup record`, and matchup-series history variants.
- Production code changed? yes.
- Tests added/updated: parser guardrails in `tests/test_natural_query_parser.py` and `tests/test_playoff_history_queries.py`; data-backed regressions in `tests/test_ui_failure_coverage.py`.
- Corpus updated: yes, the two AQ-029 target cases are now manual-review `pass` with stronger hard assertions.
- Findings updated: yes, AQ-029 is marked fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260516T084330Z/report.md`.
- Remaining risk: low. The change is intentionally limited to playoff route detection. Remaining corpus failures are unrelated record/date/stat-context and product-boundary cases.

## 2. Target behavior before/after

### best_second_round_record_since_2010_wave5

- Before: `team_record_leaderboard` / `ok`, `season_type=Regular Season`, top row OKC regular-season record.
- After: `playoff_round_record` / `ok`, `season_type=Playoffs`, `playoff_round=02`, `start_season=2010-11`, `end_season=2024-25`, `leaderboard` rows labeled `Second Round`.

### lakers_celtics_playoff_matchup_history_wave5

- Before: `team_compare` / `no_result`, LAL/BOS parsed but `playoff_history_intent=false`.
- After: `playoff_matchup_history` / `ok`, `season_type=Playoffs`, LAL/BOS team context, `summary` and `comparison` sections.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_playoff_record_route_utils.py` | production | Normalize playoff-round hyphen phrasing and recognize playoff matchup-history intent. |
| `src/nbatools/commands/playoff_history.py` | production | Add third-round aliases to the existing round alias table. |
| `tests/test_natural_query_parser.py` | tests | Add parser regressions for hyphenated second-round and playoff matchup-history team pairs. |
| `tests/test_playoff_history_queries.py` | tests | Add direct detector and route tests for hyphenated round phrases and matchup-history intent. |
| `tests/test_ui_failure_coverage.py` | tests | Add data-backed target regressions while preserving adjacent and unsupported-boundary guardrails. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Mark AQ-029 target cases pass and add stable hard assertions. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Mark AQ-029 fixed and update latest full-corpus counts. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Add Fix Wave 8B status and validation paths. |
| `docs/reference/query_catalog.md` | docs | Document verified playoff matchup-history and hyphenated second-round examples. |
| `docs/reference/query_guide.md` | docs | Add user-facing examples for the fixed phrasing. |

## 4. Test coverage

- `test_second_round_record_since_routes_to_playoff_round_record`: non-hyphenated and hyphenated `second round` since-year phrasing route to `playoff_round_record`.
- `test_adjacent_playoff_team_phrasing_routes_to_matchup_history`: `Heat Knicks playoff matchup history` and `Lakers Celtics playoff matchup history` route to `playoff_matchup_history`.
- `TestPlayoffHistoryDetection.test_detect_playoff_history_intent`: matchup-history, matchup-record, and matchup-series history phrases count as playoff history.
- `TestPlayoffHistoryDetection.test_detect_playoff_round_filter`: hyphenated first/second/conference-finals and third-round round filters are recognized.
- `TestPlayoffHistoryRouting.test_adjacent_playoff_matchup_history_phrase_routes`: Lakers/Celtics matchup-history route wiring.
- `TestPlayoffHistoryRouting.test_best_second_round_hyphenated_record_since_routes`: hyphenated since-year round-record route wiring.
- `test_best_second_round_hyphenated_since_routes_to_round_record`: data-backed leaderboard has playoff metadata and Second Round rows.
- `test_lakers_celtics_playoff_matchup_history_phrase_executes`: data-backed Lakers/Celtics query returns summary and comparison sections.

## 5. QA harness validation

Targeted AQ-029 command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case best_second_round_record_since_2010_wave5 --case lakers_celtics_playoff_matchup_history_wave5

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T084243Z
Cases: 2
Result statuses: {'ok': 2}
Expectation cases: {'pass': 2}
Suspicious flag cases: 0
Informational flag cases: 2
Verified outlier cases: 0
Failed case IDs: none
```

Adjacent playoff command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case heat_knicks_playoff_series_record_wave4 --case heat_knicks_playoff_history_no_vs_wave5 --case lakers_celtics_playoff_history --case lakers_celtics_playoff_series_history_wave5 --case best_second_round_record --case best_finals_record_since_1980 --case most_finals_appearances_since_1980 --case bulls_finals_record_wave4 --case warriors_finals_record_since_2015_wave4 --case celtics_conference_finals_record_wave4

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T084257Z
Cases: 10
Result statuses: {'no_result': 3, 'ok': 7}
Expectation cases: {'pass': 10}
Suspicious flag cases: 0
Informational flag cases: 5
Verified outlier cases: 0
Failed case IDs: none
```

Full corpus command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T084330Z
Cases: 243
Result statuses: {'error': 10, 'no_result': 32, 'ok': 201}
Expectation cases: {'fail': 6, 'pass': 237}
Suspicious flag cases: 2
Informational flag cases: 148
Verified outlier cases: 1
Failed case IDs: lakers_how_did_road_last_season_wave5, jokic_possessive_triple_double_record_wave5, curry_last_20_from_three_wave5, celtics_road_record_since_jan_1_wave5, players_personal_fouls_wave5, warriors_net_rating_single_team_wave5
```

- Latest output path: `outputs/raw_query_answer_qa/20260516T084330Z/report.md`
- Expectation counts: cases `pass: 237`, `fail: 6`; checks `pass: 1332`, `fail: 18`.
- Remaining failed IDs: `lakers_how_did_road_last_season_wave5`, `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `celtics_road_record_since_jan_1_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`.

## 6. Standard validation

Focused parser/playoff tests:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "second_round_record_since or adjacent_playoff_team_phrasing or single_team_playoff_round_records or adjacent_team_parsing_does_not_apply" -n0
12 passed, 178 deselected in 16.45s

.venv/bin/pytest tests/test_playoff_history_queries.py -k "playoff_history_intent or playoff_round_filter or adjacent_playoff_matchup_history or second_round" -n0
8 passed, 78 deselected in 11.87s

.venv/bin/pytest tests/test_ui_failure_coverage.py -k "second_round_hyphenated or lakers_celtics_playoff_matchup_history_phrase or adjacent_heat_knicks or single_team_round_records" -n0
6 passed, 112 deselected in 10.01s
```

Required parser/query/preflight targets:

```text
make PYTEST=.venv/bin/pytest test-parser
714 passed in 183.66s (0:03:03)

make PYTEST=.venv/bin/pytest test-query
731 passed in 251.18s (0:04:11)

make PYTEST=.venv/bin/pytest test-preflight
2820 passed, 1 xpassed in 745.12s (0:12:25)
```

Static/diff checks:

```text
.venv/bin/ruff check src/nbatools/commands/_playoff_record_route_utils.py src/nbatools/commands/playoff_history.py tests/test_natural_query_parser.py tests/test_playoff_history_queries.py tests/test_ui_failure_coverage.py
All checks passed!

git diff --check
passed with no output
```

## 7. Updated findings / next recommendation

- AQ-029 status: fixed.
- Remaining failed IDs: `lakers_how_did_road_last_season_wave5`, `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `celtics_road_record_since_jan_1_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`.
- Recommended next phase: handle the record/date/stat-context group, likely AQ-025 through AQ-028, then resolve AQ-030/AQ-031 as product-boundary cleanup/decision work.
