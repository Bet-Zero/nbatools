# Raw Query Answer QA Fix Wave 8D: Product Boundary Finalization Return Package

## 1. Executive summary

- What was wrong:
  - `players with most personal fouls this season` was unrouted because the personal-foul unsupported boundary depended on supported leaderboard stat alias detection.
  - `Warriors net rating this season` fell through to `game_finder` and returned a generic unsupported stat error.
- Product decision:
  - Personal-foul leaderboards remain unsupported.
  - Single-team advanced-stat scalar summaries remain unsupported until a route/result contract is approved.
  - League-wide team advanced-stat leaderboards remain supported.
- What changed:
  - Decoupled personal-foul boundary detection from supported stat aliases.
  - Added a guarded single-team advanced-stat summary boundary for `off_rating`, `def_rating`, `net_rating`, and `pace`.
  - Added `single_team_advanced_stat_summary` no-result guidance.
- Production code changed? yes
- Tests added/updated: parser and data-backed guardrails for both targets plus turnover/steal/block and league-wide team advanced leaderboard preservation.
- Corpus updated: yes, `warriors_net_rating_single_team_wave5` is now expected unsupported; `players_personal_fouls_wave5` has stronger `metadata.stat=pf` assertion.
- Findings updated: yes, AQ-030 and AQ-031 are marked `fixed_as_expected_unsupported`.
- Latest harness run: `outputs/raw_query_answer_qa/20260516T221654Z/report.md`.
- Remaining risk: low. The single-team advanced boundary is intentionally narrow and guarded against player, comparison, finder/count, threshold, split, streak, and lineup/on-off contexts.
- Validation efficiency note: used focused parser/data tests, target/adjacent/full QA harnesses, ruff, `make test-parser`, and diff checks. Skipped broader query/preflight suites because execution changes were limited to unsupported boundary routing/notes and the full corpus showed no drift.

## 2. Target behavior before/after

### players_personal_fouls_wave5

- Before:
  - Query: `players with most personal fouls this season`
  - Parse: `ValueError`, no route.
  - Execution: route `<none>`, status `error`, reason `unrouted`.
  - Metadata: `stat=null`, `unsupported_filters=null`.
  - Failed expectations: status, route, reason, shape, and missing `result.metadata.unsupported_filters.0`.
- After:
  - Route: `season_leaders`
  - Status/reason: `no_result` / `filter_not_supported`
  - Metadata: `stat=pf`, `unsupported_filters=["personal_foul_leaderboard"]`
  - Sections: none
  - No PF leaderboard support was added.

### warriors_net_rating_single_team_wave5

- Before:
  - Query: `Warriors net rating this season`
  - Parse route/status: `game_finder`; route kwargs included `team=GSW`, `stat=net_rating`, `sort_by=stat`.
  - Execution: `no_result` / `unsupported`
  - Metadata: `team=GSW`, `stat=net_rating`, `unsupported_filters=null`
  - Note: `Unsupported stat: net_rating`
  - Failed expectations: expected supported `season_team_leaders` leaderboard rows.
- After:
  - Route: `game_summary` only as a context-preserving unsupported boundary route.
  - Status/reason: `no_result` / `filter_not_supported`
  - Metadata: `team=GSW`, `stat=net_rating`, `unsupported_filters=["single_team_advanced_stat_summary"]`
  - Sections: none
  - No broad team advanced leaderboard fallback was returned.

## 3. Product-boundary decisions

- Personal-foul leaderboards:
  - Unsupported. Clear leaderboard variants such as `personal fouls leaders this season`, `players with most personal fouls this season`, and `most personal fouls this season` now share one explicit no-result boundary.
- Single-team advanced-stat summaries:
  - Unsupported for now. `Warriors net rating this season`, `Warriors offensive rating this season`, `Warriors defensive rating this season`, and `Warriors pace this season` return `single_team_advanced_stat_summary`.
- League-wide advanced-stat leaderboards:
  - Still supported through `season_team_leaders` for net rating, offensive rating, defensive rating, and pace.
- Future support path:
  - Add a dedicated route/result contract for single-team season advanced scalar summaries, or a rank-preserving team advanced lookup contract. Add PF leaderboard support only after approving a fouls-committed stat contract.

## 4. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | production | Detect PF leaderboard boundary variants without relying on supported leaderboard aliases. |
| `src/nbatools/commands/natural_query.py` | production | Preserve PF ranked intent/stat metadata and add guarded single-team advanced-stat unsupported routing. |
| `src/nbatools/commands/_natural_query_execution.py` | production | Add no-result guidance for `single_team_advanced_stat_summary` and clarify PF guidance. |
| `tests/test_natural_query_parser.py` | tests | Parser guardrails for PF variants, single-team advanced boundaries, and supported adjacent leaderboards. |
| `tests/test_ui_failure_coverage.py` | tests | Data-backed target regressions and adjacent supported leaderboard guardrails. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Update final two cases to explicit unsupported expectations with hard metadata assertions. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Mark AQ-030/AQ-031 fixed and update latest 243-case run counts. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Add Fix Wave 8D status and validation artifacts. |
| `docs/reference/query_catalog.md` | docs | Document PF unsupported variants, single-team advanced unsupported boundary, and league-wide advanced leaderboard support. |
| `docs/reference/query_guide.md` | docs | Document the same user-facing boundaries and examples. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8D_PRODUCT_BOUNDARY_FINALIZATION_RETURN_PACKAGE.md` | docs | This return package. |

## 5. Test coverage

- `test_personal_foul_leaderboard_variants_are_unsupported_boundaries`: PF phrasing variants route to `season_leaders`, set `stat=pf`, and carry `personal_foul_leaderboard`.
- `test_supported_defensive_and_turnover_leaderboards_still_route`: turnover, steals, and blocks remain supported `season_leaders` queries.
- `test_single_team_advanced_stat_scalar_queries_are_unsupported_boundaries`: Warriors net/offensive/defensive rating and pace route to `game_summary` unsupported boundary, not `game_finder`.
- `test_league_wide_team_advanced_leaderboards_still_route`: league-wide team advanced leaderboards still route to `season_team_leaders`.
- `test_unsupported_boundary_queries_return_no_result`: data-backed PF target and existing unsupported boundaries return no-result/filter-not-supported.
- `test_single_team_advanced_stat_summaries_return_unsupported_boundary`: data-backed single-team advanced target family returns the expected no-result metadata.
- `test_supported_turnover_steal_block_leaderboards_still_execute`: data-backed supported player leaderboards still return rows.
- `test_league_wide_team_advanced_leaderboards_still_execute`: data-backed league-wide advanced team leaderboards still return rows.

## 6. QA harness validation

Targeted 8D command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case players_personal_fouls_wave5 --case warriors_net_rating_single_team_wave5

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T221628Z
Cases: 2
Result statuses: {'no_result': 2}
Expectation cases: {'pass': 2}
Suspicious flag cases: 0
Informational flag cases: 0
Verified outlier cases: 0
Failed case IDs: none
```

Adjacent boundary/advanced command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case personal_foul_leaders_wave4 --case turnover_leaders_wave4 --case steal_leaders_this_season --case block_leaders_this_season --case net_rating_team_leaders --case offensive_rating_team_leader --case def_rating_team_leaders_wave4 --case pace_team_leaders_wave4 --case fastest_pace_teams_wave5

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T221638Z
Cases: 9
Result statuses: {'no_result': 1, 'ok': 8}
Expectation cases: {'pass': 9}
Suspicious flag cases: 0
Informational flag cases: 6
Verified outlier cases: 0
Failed case IDs: none
```

Full corpus command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T221654Z
Cases: 243
Result statuses: {'error': 9, 'no_result': 32, 'ok': 202}
Expectation cases: {'pass': 243}
Suspicious flag cases: 0
Informational flag cases: 149
Verified outlier cases: 1
Failed case IDs: none
```

- Latest output path: `outputs/raw_query_answer_qa/20260516T221654Z/report.md`
- Expectation counts: cases `pass: 243`; checks `pass: 1368`
- Remaining failed IDs: none
- Suspicious flags: none
- Verified outlier: `top_performance_high_points`

## 7. Tiered standard validation

Tier 1 results:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "personal_foul_leaderboard_variants or supported_defensive_and_turnover_leaderboards or single_team_advanced_stat_scalar or league_wide_team_advanced_leaderboards" -n0
16 passed, 207 deselected in 11.52s

.venv/bin/pytest tests/test_ui_failure_coverage.py -k "unsupported_boundary_queries_return_no_result or single_team_advanced_stat_summaries or supported_turnover_steal_block or league_wide_team_advanced_leaderboards" -n0
19 passed, 120 deselected in 15.67s

.venv/bin/ruff check src/nbatools/commands/_parse_helpers.py src/nbatools/commands/natural_query.py src/nbatools/commands/_natural_query_execution.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py
All checks passed!

git diff --check
passed with no output
```

Tier 2 result:

```text
make PYTEST=.venv/bin/pytest test-parser
747 passed in 128.19s (0:02:08)
```

Tier 3 decision:

- `make test-query` skipped. Rationale: no query-service response contract changed, execution changes were limited to unsupported-filter notes and boundary routing, and the target/adjacent/full corpus harnesses showed no related drift.

Tier 4 decision:

- `make test-preflight` skipped. Rationale: the change was a bounded product-boundary cleanup, not a broad routing or contract refactor; `make test-parser` plus the full 243-case product corpus covered the changed surface.

## 8. Updated findings / next recommendation

- AQ-030 status: `fixed_as_expected_unsupported`
- AQ-031 status: `fixed_as_expected_unsupported`
- Remaining failed IDs: none
- Recommended next phase:
  - With the 243-case raw product corpus passing, choose between frontend-copy corpus expansion, a release-readiness checklist, or selecting one unsupported family to promote into real support behind an approved contract.
