# Raw Query Answer QA Fix Wave 8C2: Player Entity + Stat-Context Routing Return Package

## 1. Executive summary

- What was wrong: auxiliary `was` in `What was Jokic's...` resolved as Washington (`team=WAS`), causing a no-match; standalone `Curry last 20 games from three` kept the right summary sample but dropped structured `fg3m` stat context.
- What changed: added a context-sensitive guard that clears `WAS` only for auxiliary question-word `was` without explicit Washington/Wizards/WAS text; added a narrow last-N player summary stat-context detector for standalone `from three` -> `fg3m`.
- Production code changed? yes.
- Tests added/updated: parser guardrails in `tests/test_natural_query_parser.py`; data-backed target regressions in `tests/test_ui_failure_coverage.py`.
- Corpus updated: yes, only the two Wave 8C2 target cases were marked pass and strengthened with stable assertions.
- Findings updated: yes, AQ-026 and AQ-028 are marked fixed; AQ-030 and AQ-031 remain open.
- Latest harness run: `outputs/raw_query_answer_qa/20260516T112341Z/report.md`.
- Remaining risk: low. The WAS guard is limited to auxiliary question phrasing and preserves explicit Washington references; the `from three` stat context only applies to no-threshold last-N player summaries.
- Validation efficiency note: used focused parser/data tests, targeted and adjacent harnesses, then full corpus. Skipped broader query/preflight suites because execution logic and query-service contracts were not changed and all targeted/adjacent/full harness results matched expectations.

## 2. Target behavior before/after

### jokic_possessive_triple_double_record_wave5

- Before: query `What was Jokic's record in games with a triple-double?`; parse route `player_game_summary`; route kwargs had `player=Nikola Jokić`, `team=WAS`, `special_event=triple_double`; execution `player_game_summary` / `no_result` / `no_match`; filters only `Special Event=Triple Double`; no sections. Failed expectations: expected `ok`, `entity_summary`, and missing `summary` / `game_log`.
- After: route `player_game_summary`; `player=Nikola Jokić`; `team=None`; `special_event=triple_double`; status `ok`; sections `summary`, `by_season`, `game_log`; summary 34 games, 24 wins, 10 losses; game_log rows 34.

### curry_last_20_from_three_wave5

- Before: query `Curry last 20 games from three`; route `player_game_summary`; status `ok`; `player=Stephen Curry`; `last_n=20`; sections `summary`, `by_season`, `game_log`; summary already had `fg3m_avg=4.05`, `fg3m_sum=81`; metadata/stat was `null`. Failed expectation: `result.metadata.stat` expected `fg3m`.
- After: route `player_game_summary`; status `ok`; `player=Stephen Curry`; `last_n=20`; `stat=fg3m`; no threshold min/max; sections unchanged; game_log rows 20; summary `fg3m_avg=4.05`, `fg3m_sum=81`.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | production | Add narrow standalone player summary stat-context detector for `from three`. |
| `src/nbatools/commands/natural_query.py` | production | Clear auxiliary `was` from WAS team context and preserve last-N `from three` summaries as summaries with `fg3m` metadata. |
| `tests/test_natural_query_parser.py` | tests | Add parser guardrails for auxiliary `was`, Washington references, `was out`, last-N `from three`, threes thresholds, and percentage thresholds. |
| `tests/test_ui_failure_coverage.py` | tests | Add data-backed Jokic and Curry target regressions. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Mark the two target cases pass and add stable hard assertions. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Update latest full-corpus counts and mark AQ-026/AQ-028 fixed. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Add Fix Wave 8C2 status and validation artifacts. |
| `docs/reference/query_catalog.md` | docs | Document verified player summary `from three` and possessive Jokic record examples. |
| `docs/reference/query_guide.md` | docs | Add user-facing examples for the fixed phrasing. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8C2_PLAYER_ENTITY_STAT_CONTEXT_RETURN_PACKAGE.md` | docs | This return package. |

## 4. Test coverage

- `test_auxiliary_was_does_not_resolve_washington_for_player_record`: target parser route, Jokic, triple-double event, and no `team=WAS`.
- `test_current_tense_jokic_triple_double_record_still_routes`: existing `What is...` variant still routes.
- `test_clear_washington_team_references_still_resolve`: `WAS`, Washington, and Wizards references still resolve to `WAS`.
- `test_was_out_guard_still_preserves_without_player_context`: availability phrasing still preserves `without_player`.
- `test_from_three_last_n_player_summary_sets_made_threes_context`: target Curry parser route keeps summary, `last_n=20`, `stat=fg3m`, and no thresholds.
- `test_single_stat_threshold_still_uses_scalar_route_kwargs`: `Curry 5+ threes` remains threshold/finder behavior.
- `test_player_from_three_percentage_threshold_stays_fg3_pct_finder` and existing percentage test: `from three over 40%` remains `fg3_pct`.
- `test_possessive_jokic_triple_double_record_ignores_auxiliary_was`: data-backed target returns 34 games, 24-10, 34 triple-double game-log rows.
- `test_curry_last_20_from_three_preserves_summary_stat_context`: data-backed target returns 20 game-log rows and `metadata.stat=fg3m`.

## 5. QA harness validation

Targeted 8C2 command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case jokic_possessive_triple_double_record_wave5 --case curry_last_20_from_three_wave5

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T112238Z
Cases: 2
Result statuses: {'ok': 2}
Expectation cases: {'pass': 2}
Suspicious flag cases: 0
Informational flag cases: 2
Verified outlier cases: 0
Failed case IDs: none
```

Adjacent player/entity/stat command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case record_when_jokic_triple_double --case jokic_triple_double_count --case curry_5_threes_finder --case curry_5_threes_count --case most_threes_single_game --case curry_home_away_last_20_split_wave4 --case jokic_assists_since_all_star_wave4

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T112300Z
Cases: 7
Result statuses: {'ok': 7}
Expectation cases: {'pass': 7}
Suspicious flag cases: 0
Informational flag cases: 4
Verified outlier cases: 0
Failed case IDs: none
```

Full corpus command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T112341Z
Cases: 243
Result statuses: {'error': 10, 'no_result': 31, 'ok': 202}
Expectation cases: {'fail': 2, 'pass': 241}
Suspicious flag cases: 1
Informational flag cases: 149
Verified outlier cases: 1
Failed case IDs: players_personal_fouls_wave5, warriors_net_rating_single_team_wave5
```

- Latest output path: `outputs/raw_query_answer_qa/20260516T112341Z/report.md`
- Expectation counts: cases `pass: 241`, `fail: 2`; checks `pass: 1355`, `fail: 9`
- Remaining failed IDs: `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`

## 6. Tiered standard validation

Tier 1 results:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "auxiliary_was or current_tense_jokic or clear_washington or was_out_guard or from_three_last_n or single_stat_threshold_still or from_three_percentage_threshold" -n0
11 passed, 196 deselected in 75.58s

.venv/bin/pytest tests/test_ui_failure_coverage.py -k "possessive_jokic_triple_double or curry_last_20_from_three or record_when_player_special_event" -n0
3 passed, 123 deselected in 31.99s

.venv/bin/ruff check src/nbatools/commands/_parse_helpers.py src/nbatools/commands/natural_query.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py
All checks passed!
```

Tier 2 result:

```text
make test-parser
failed because bare `pytest` is not on PATH in this environment.

make PYTEST=.venv/bin/pytest test-parser
731 passed in 131.76s (0:02:11)
```

Tier 3 decision:

- `make test-query` skipped. Rationale: no `player_game_summary` execution logic or query-service response contract changed; focused data-backed query tests, targeted/adjacent harnesses, and the full corpus all passed the expected player/entity/stat-context behavior with no related drift.

Tier 4 decision:

- `make test-preflight` skipped. Rationale: the change was narrowly scoped to parser/entity/stat-context routing, and full corpus validation showed only the two pre-existing product-boundary failures.

Final static check:

```text
git diff --check
passed with no output
```

## 7. Updated findings / next recommendation

- AQ-026 status: fixed.
- AQ-028 status: fixed.
- Remaining failed IDs: `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`.
- Recommended next phase: AQ-030/AQ-031 product-boundary cleanup/decision work.
