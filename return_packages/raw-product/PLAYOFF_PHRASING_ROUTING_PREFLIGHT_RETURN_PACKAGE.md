# Playoff Phrasing Routing Preflight Return Package

## 1. Executive summary

- Main root-cause families:
  - Hyphenated playoff round phrase parsing: `second-round` is not recognized by the existing round-alias matcher, so `best second-round record since 2010` falls through to a regular-season record leaderboard.
  - Playoff matchup-history intent detection: `playoff matchup history` does not set `playoff_history_intent`, so adjacent team parsing finds LAL/BOS but the playoff matchup-history route is skipped.
- Which cases are true bugs:
  - `best_second_round_record_since_2010_wave5` is a true routing bug. League-wide playoff round-record leaderboards are already supported and documented.
  - `lakers_celtics_playoff_matchup_history_wave5` is a true routing bug. Adjacent playoff team-team history phrasing is already supported, and Lakers/Celtics data exists.
- Which cases are product-boundary decisions:
  - Neither target AQ-029 case should be reclassified as unsupported. The existing unsupported boundary is single-team playoff round records such as `Bulls Finals record`, not league-wide round leaderboards or team-vs-team playoff history.
- Recommended next execution:
  - Option A: fix both AQ-029 cases in one execution wave. Both are small parser/routing changes backed by existing routes, data, contracts, and nearby passing cases.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `best_second_round_record_since_2010_wave5` | `best second-round record since 2010` | `team_record_leaderboard` / `ok` | Returns a regular-season multi-season leaderboard, `season_type=Regular Season`, `start_season=2010-11`, `end_season=2025-26`, top row OKC. | Route to `playoff_round_record`, `season_type=Playoffs`, `playoff_round=02`, `start_season=2010-11`, `end_season=2024-25`, `leaderboard` section. | `detect_playoff_round_filter()` matches `second round` but not `second-round`. Because no playoff round is detected, season type remains regular season and the generic record leaderboard route wins. |
| `lakers_celtics_playoff_matchup_history_wave5` | `Lakers Celtics playoff matchup history` | `team_compare` / `no_result` | Parses LAL/BOS and `season_type=Playoffs`, but routes to current-season playoff `team_compare`; no 2024-25 LAL/BOS playoff matchup exists, so it returns `no_match` with no sections. | Route to `playoff_matchup_history`, `season_type=Playoffs`, teams LAL/BOS, with `summary` and `comparison` sections. | Adjacent playoff team extraction returns LAL/BOS, but `detect_playoff_history_intent()` only recognizes `playoff history` / `playoff series`, not `playoff matchup history`. `try_playoff_record_route()` therefore skips the playoff matchup route. |

Report evidence from `outputs/raw_query_answer_qa/20260516T075849Z/report.jsonl`:

- `best_second_round_record_since_2010_wave5` failed `expected_route`, `expected_shape`, and `result.metadata.season_type`.
- `lakers_celtics_playoff_matchup_history_wave5` failed `expected_status`, `expected_route`, `expected_shape`, and `expected_sections`.

Direct probe evidence:

- `best second round record since 2010` already routes correctly to `playoff_round_record`, `playoff_round=02`, `season_type=Playoffs`, `start_season=2010-11`, `end_season=2024-25`, with 10 leaderboard rows.
- `Lakers Celtics playoff history` and `Lakers Celtics playoff series history` already route correctly to `playoff_matchup_history`, with 2 summary rows and 2 comparison rows.

## 3. Nearby working cases

| Case/query | Behavior | Why it matters |
|---|---|---|
| `best_second_round_record` / `best second round record` | `playoff_round_record` / `ok`; top rows include GSW, LAL, MIA; `round=Second Round`, `season_type=Playoffs`. | Confirms the route, contract, and round-record execution already exist for non-hyphenated wording. |
| Direct probe `best second round record since 2010` | `playoff_round_record` / `ok`; `start_season=2010-11`, `end_season=2024-25`; top rows GSW 5-1 and PHI 3-1. | Confirms `since 2010` works when round detection succeeds. |
| `best_finals_record_since_1980` | `playoff_round_record` / `ok`; `round=Finals`, `season_type=Playoffs`, season filter applied. | Confirms since-year round-record leaderboards are supported. |
| `most_finals_appearances_since_1980` | `playoff_appearances` / `ok`; season filter applied. | Confirms since-year playoff appearance leaderboards are supported. |
| `most_conference_finals_appearances_wave4` | `playoff_appearances` / `ok`; `round=Conference Finals`. | Confirms round phrase detection works for non-hyphenated conference-finals wording. |
| `bulls_finals_record_wave4` | `playoff_history` / `no_result`, `filter_not_supported`, `unsupported_filters=["single_team_playoff_round_record"]`. | Confirms the unsupported boundary is single-team round records, not league-wide round leaderboards. |
| `warriors_finals_record_since_2015_wave4` | Same unsupported single-team boundary; preserves `start_season=2015-16`. | Confirms since-year context is preserved for unsupported single-team round records. |
| `celtics_conference_finals_record_wave4` | Same unsupported single-team boundary. | Confirms single-team conference-finals records should not fall through to regular-season records. |
| `heat_knicks_playoff_history` | `playoff_matchup_history` / `ok`; 2 summary rows, 6 comparison rows. | Confirms explicit `vs` playoff history route. |
| `heat_knicks_playoff_history_no_vs_wave5` | `playoff_matchup_history` / `ok`; adjacent Heat/Knicks without `vs`. | Confirms adjacent team-team parsing is already intentionally supported in playoff history context. |
| `heat_knicks_playoff_series_record_wave4` | `playoff_matchup_history` / `ok`; adjacent team-team plus `playoff series record`. | Confirms adjacent playoff series-record wording is supported. |
| `lakers_celtics_playoff_history` | `playoff_matchup_history` / `ok`; LAL 6-7, BOS 7-6 over 13 games, 2 comparison rows. | Confirms Lakers/Celtics historical matchup data exists. |
| `lakers_celtics_playoff_series_history_wave5` | `playoff_matchup_history` / `ok`; 2 summary rows, 2 comparison rows. | Confirms adjacent Lakers/Celtics works when `series history` sets history intent. |
| `lakers_celtics_by_decade` | `matchup_by_decade` / `ok`; regular-season matchup-by-decade comparison. | Confirms team-pair parsing and historical comparison route are healthy outside playoff history. |
| `warriors_lakers_by_decade_wave4` | `matchup_by_decade` / `ok`; 2 summary rows, 4 comparison rows. | Confirms matchup-by-decade behavior is not affected by playoff matchup-history routing. |

## 4. Root-cause analysis

### Second-round / playoff round phrasing

- Findings:
  - Exact failing query: `best second-round record since 2010`.
  - Current parse: `route=team_record_leaderboard`, `record_intent=True`, `season_type=Regular Season`, `playoff_round_filter=None`, `start_season=2010-11`, `end_season=2025-26`.
  - Current execution: `ok`, but wrong semantic surface: regular-season leaderboard with OKC as top row.
  - Helper probe: `detect_playoff_round_filter("best second-round record since 2010")` returns `None`.
  - Helper probe: `detect_playoff_round_filter("best second round record since 2010")` returns `02`.
  - `since 2010` is preserved as `start_season=2010-11`; the bad end season is a consequence of the wrong regular-season route.
- Existing support:
  - `ROUND_ALIASES` supports `second round`, `2nd round`, `round 2`, `round two`, `semifinals`, and related non-hyphenated forms.
  - `try_record_leaderboard_route()` already redirects generic record leaderboards to `playoff_round_record` when `playoff_round_filter` is present.
  - `build_playoff_round_record_result()` already returns the needed leaderboard contract.
- Gaps:
  - Hyphenated round forms like `second-round` are not normalized or aliased.
  - No product-boundary issue was found. The shipped surface explicitly covers league-wide playoff-round record leaderboards.

### Lakers-Celtics playoff matchup phrasing

- Findings:
  - Exact failing query: `Lakers Celtics playoff matchup history`.
  - Current parse: `team_a=LAL`, `team_b=BOS`, `season_type=Playoffs`, `head_to_head=True`, `playoff_history_intent=False`, `record_intent=False`, `route=team_compare`.
  - Current execution: `no_result`, `reason=no_match`, because it searches only the current 2024-25 playoffs for a generic team comparison.
  - Helper probe: `extract_adjacent_playoff_team_comparison()` returns `("LAL", "BOS")` for the failing query.
  - Helper probe: `detect_playoff_history_intent()` returns `False` for `playoff matchup history`, but `True` for `playoff history` and `playoff series record`.
- Existing support:
  - Adjacent team-team parsing is intentionally limited to explicit playoff series/history contexts.
  - Lakers/Celtics playoff matchup data exists through `playoff_matchup_history`: 13 games, 2 comparison rows, Finals in 2007-08 and 2009-10.
  - `Heat Knicks playoff history`, `Heat Knicks playoff series record`, `Lakers Celtics playoff history`, and `Lakers Celtics playoff series history` all pass.
- Gaps:
  - `detect_playoff_history_intent()` does not treat `playoff matchup history` as playoff history intent.
  - `try_playoff_record_route()` requires playoff history intent, playoff record intent, or a round/history condition before routing team pairs to `playoff_matchup_history`; adjacent team extraction alone is not enough.

## 5. Product/data support

| Needed behavior | Available? | Source/route | Notes |
|---|---|---|---|
| League-wide second-round record leaderboard since 2010 | Yes | `playoff_round_record` via `build_playoff_round_record_result()` | Direct non-hyphenated probe returns 10 rows, `round=Second Round`, `season_type=Playoffs`, `start_season=2010-11`, `end_season=2024-25`. |
| Hyphenated `second-round` parser support | No | Parser alias/normalization gap | Add hyphen-aware round aliases or normalize round phrases before alias matching. |
| Lakers/Celtics playoff matchup history | Yes | `playoff_matchup_history` via `build_playoff_matchup_history_result()` | Existing nearby cases return LAL/BOS summary and 2 Finals comparison rows. |
| Adjacent team-team playoff history without `vs` | Yes | `extract_adjacent_playoff_team_comparison()` plus `playoff_matchup_history` route | Works for `Heat Knicks playoff history` and `Lakers Celtics playoff series history`. |
| `playoff matchup history` intent phrase | No | `detect_playoff_history_intent()` gap | Needs intent regex expansion, not new execution logic. |
| Single-team Finals/conference-finals records | Yes, as unsupported boundary | `playoff_history` with `unsupported_filters=["single_team_playoff_round_record"]` | This boundary should remain unchanged. |

## 6. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| A | Fix both AQ-029 cases in one execution wave. | One coherent playoff-phrasing wave; both fixes are parser/routing-only; both reuse existing routes and contracts; updates one findings family cleanly. | Touches two detection areas, so tests need to cover both. | Low to medium. Main risk is over-broad regex matching. | Recommended. |
| B | Split into Wave 8B1 matchup adjacency and Wave 8B2 hyphenated round-record phrasing. | Lowest per-PR blast radius and easiest isolate if CI fails. | Extra overhead for two tiny fixes in the same product family; leaves one true bug open. | Low. | Acceptable if execution time is constrained, but not necessary. |
| C | Support matchup phrasing and mark second-round query unsupported. | Avoids round alias work. | Incorrect product semantics: non-hyphenated `best second round record since 2010` already works, and docs/contracts support league-wide playoff round leaderboards. Weakens corpus to hide a bug. | Medium product risk. | Not recommended. |

## 7. Recommended execution scope

- Exact goal:
  - Make AQ-029 playoff phrasing route to existing supported playoff history/round-record surfaces without adding new execution semantics.
- Cases to fix:
  - `best_second_round_record_since_2010_wave5`
  - `lakers_celtics_playoff_matchup_history_wave5`
- Cases to mark unsupported/no-result, if any:
  - None for AQ-029 targets.
  - Preserve existing unsupported single-team round-record cases: `bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, `celtics_conference_finals_record_wave4`, `bulls_finals_record_question_wave5`, `celtics_record_in_conference_finals_wave5`.
- Files to change:
  - Likely `src/nbatools/commands/_playoff_record_route_utils.py` for `detect_playoff_history_intent()` and/or hyphen-aware round detection.
  - Possibly `src/nbatools/commands/playoff_history.py` if adding explicit hyphenated `ROUND_ALIASES` is chosen.
  - Possibly `tests/test_natural_query_parser.py`, `tests/test_playoff_history_queries.py`, and `tests/test_ui_failure_coverage.py` for parser and data-backed regressions.
  - `qa/raw_query_answer_corpus.yaml` after behavior is verified, to mark target cases pass and add stable hard assertions if useful.
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` after validation, to mark AQ-029 fixed.
  - `docs/reference/query_catalog.md` and optionally `docs/reference/query_guide.md` if explicit `playoff matchup history` / hyphenated round examples are added to the shipped surface docs.
- Tests to add:
  - Parser regression for `best second-round record since 2010`: expected `route=playoff_round_record`, `season_type=Playoffs`, `playoff_round=02`, `start_season=2010-11`, `end_season=2024-25`.
  - Parser regression for `Lakers Celtics playoff matchup history`: expected `route=playoff_matchup_history`, `team_a=LAL`, `team_b=BOS`, `season_type=Playoffs`.
  - Guardrail for `Heat Knicks playoff matchup history` or `Lakers vs Celtics playoff matchup history`, because the same phrase fails with and without `vs`.
  - Data-backed regression for the two corpus targets: second-round returns a leaderboard with `round=Second Round`; Lakers/Celtics returns `summary` and `comparison` rows.
  - Guardrail that single-team round records remain `filter_not_supported`.
- Corpus updates:
  - Only after implementation and validation, update the two AQ-029 target expectations from failing review cases to passing manual-review cases.
  - Add hard assertions for `season_type=Playoffs`, `start_season=2010-11`, `result.sections.leaderboard.0.round=Second Round`, and LAL/BOS summary/team context if stable.
- Findings updates:
  - Mark AQ-029 fixed with the execution run path and latest full-corpus counts.
- Harness validation:
  - First run targeted raw QA:
    - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case best_second_round_record_since_2010_wave5 --case lakers_celtics_playoff_matchup_history_wave5`
  - Then run adjacent playoff cases:
    - `heat_knicks_playoff_series_record_wave4`
    - `heat_knicks_playoff_history_no_vs_wave5`
    - `lakers_celtics_playoff_history`
    - `lakers_celtics_playoff_series_history_wave5`
    - `best_second_round_record`
    - `best_finals_record_since_1980`
    - `most_finals_appearances_since_1980`
    - single-team unsupported round-record cases
  - Finally run the full 243-case raw QA corpus after tests pass.
- Stop conditions:
  - Stop if hyphen normalization changes non-playoff regular-season record queries.
  - Stop if `playoff matchup history` starts promoting ordinary non-playoff adjacent team queries.
  - Stop if any single-team Finals/conference-finals unsupported boundary begins returning regular-season records.
  - Stop if the direct routes return empty data for the target cases after parser routing is fixed.

Recommended local validation for the execution wave:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "playoff and (matchup or round or finals)" -n0
.venv/bin/pytest tests/test_playoff_history_queries.py -k "playoff_matchup or second_round or finals_record or single_team_finals" -n0
.venv/bin/pytest tests/test_ui_failure_coverage.py -k "playoff" -n0
make PYTEST=.venv/bin/pytest test-parser
make PYTEST=.venv/bin/pytest test-query
make PYTEST=.venv/bin/pytest test-preflight
```

## 8. Validation performed

No production code, tests, corpus expectations, frontend rendering, or backend answer-phrase behavior were changed.

Commands/probes run:

```text
git status --short
```

Summary: clean before the return-package edit.

```text
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8A_DEFENSIVE_ALIAS_VARIANTS_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_CORPUS_EXPANSION_WAVE_5_RETURN_PACKAGE.md
sed -n '1,220p' outputs/raw_query_answer_qa/20260516T075849Z/report.md
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
```

Summary: confirmed Fix Wave 8A left 8 failures and AQ-029 is the playoff/history phrasing family.

```text
rg -n "best_second_round_record_since_2010_wave5|lakers_celtics_playoff_matchup_history_wave5|heat_knicks_playoff_series_record_wave4|heat_knicks_playoff_history|lakers_celtics_playoff_history|lakers_celtics_by_decade|warriors_lakers_by_decade_wave4|best_second_round_record|best_finals_record_since_1980|most_finals_appearances_since_1980|most_conference_finals_appearances_wave4|bulls_finals_record_wave4|warriors_finals_record_since_2015_wave4|celtics_conference_finals_record_wave4" qa/raw_query_answer_corpus.yaml
rg -n "best_second_round_record_since_2010_wave5|lakers_celtics_playoff_matchup_history_wave5|heat_knicks_playoff_series_record_wave4|heat_knicks_playoff_history|lakers_celtics_playoff_history|lakers_celtics_by_decade|warriors_lakers_by_decade_wave4|best_second_round_record|best_finals_record_since_1980|most_finals_appearances_since_1980|most_conference_finals_appearances_wave4|bulls_finals_record_wave4|warriors_finals_record_since_2015_wave4|celtics_conference_finals_record_wave4" outputs/raw_query_answer_qa/20260516T075849Z/report.jsonl
```

Summary: found exact target corpus entries, failed report rows, and nearby passing playoff cases.

```text
rg -n "playoff|Finals|second round|second-round|matchup history|series record|round record" docs/reference/query_catalog.md docs/reference/query_guide.md docs/reference/result_contracts/core_result_table_contracts.md
sed -n '230,265p' docs/reference/query_guide.md
sed -n '580,652p' docs/reference/query_catalog.md
sed -n '88,100p' docs/reference/result_contracts/core_result_table_contracts.md
```

Summary: confirmed shipped docs already cover playoff matchup history, adjacent playoff series/history contexts, league-wide playoff round-record leaderboards, and the single-team round-record unsupported boundary.

```text
.venv/bin/python - <<'PY'
# Read report.jsonl and print compact route/status/metadata/section summaries
# for the two target cases and nearby playoff cases.
PY
```

Summary: confirmed target failures and nearby passing behavior. Notable outputs:

- `best_second_round_record_since_2010_wave5`: `team_record_leaderboard` / `ok`, `season_type=Regular Season`, top row OKC.
- `lakers_celtics_playoff_matchup_history_wave5`: `team_compare` / `no_result`, `reason=no_match`, no sections.
- `best_second_round_record`: `playoff_round_record` / `ok`.
- `lakers_celtics_playoff_history`: `playoff_matchup_history` / `ok`, 2 summary rows and 2 comparison rows.

```text
.venv/bin/python - <<'PY'
# For exact failing queries and variants, call parse_query(),
# execute_natural_query(), and query_result_to_payload().
PY
```

Summary: reproduced the parser/execution mismatch directly.

- `best second-round record since 2010`: parse has `playoff_round_filter=None`, execution is regular-season `team_record_leaderboard`.
- `best second round record since 2010`: parse has `playoff_round_filter=02`, execution is `playoff_round_record`.
- `Lakers Celtics playoff matchup history`: parse has LAL/BOS but `playoff_history_intent=False`, execution is `team_compare` / `no_match`.
- `Lakers Celtics playoff history` and `Lakers Celtics playoff series history`: execution is `playoff_matchup_history` / `ok`.

```text
.venv/bin/python - <<'PY'
# Probe detect_playoff_history_intent(), detect_playoff_round_filter(),
# detect_season_type(), and extract_adjacent_playoff_team_comparison().
PY
```

Summary:

- `detect_playoff_round_filter("best second-round record since 2010")` returns `None`.
- `detect_playoff_round_filter("best second round record since 2010")` returns `02`.
- `detect_playoff_history_intent("lakers celtics playoff matchup history")` returns `False`.
- `extract_adjacent_playoff_team_comparison("lakers celtics playoff matchup history")` returns `("LAL", "BOS")`.

```text
sed -n '240,330p' src/nbatools/commands/_matchup_utils.py
sed -n '1,380p' src/nbatools/commands/_playoff_record_route_utils.py
sed -n '430,620p' src/nbatools/commands/natural_query.py
sed -n '944,1045p' src/nbatools/commands/playoff_history.py
sed -n '920,1070p' tests/test_natural_query_parser.py
sed -n '238,310p' tests/test_playoff_history_queries.py
```

Summary: inspected the current parser helpers, route selection, execution command, and existing playoff tests. The failures are parser/routing gaps, not missing execution/data support.
