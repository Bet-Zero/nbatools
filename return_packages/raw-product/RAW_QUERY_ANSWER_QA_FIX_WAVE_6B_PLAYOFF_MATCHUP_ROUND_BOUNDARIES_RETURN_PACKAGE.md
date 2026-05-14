# Raw Query Answer QA Fix Wave 6B: Playoff Matchup Routing + Round-Record Boundaries Return Package

## 1. Executive summary

- What was wrong: adjacent playoff matchup phrasing such as `Heat Knicks playoff series record` collapsed to single-team Knicks playoff history; single-team Finals/conference-finals record phrasing could fall through to broad regular-season `team_record`.
- Product/data decision: single-team playoff round records are not shipped in this wave. They return explicit `no_result` / `filter_not_supported` until the route/shape contract and round extraction/data coverage are approved.
- What changed: added a playoff-only adjacent team-pair parser, blocked single-team round-record phrases with `unsupported_filters=["single_team_playoff_round_record"]`, updated corpus expectations/docs/findings, and added regressions.
- Production code changed? yes
- Tests added/updated: parser route tests, playoff route tests, and data-backed query-service regressions.
- Corpus updated: yes
- Findings updated: yes
- Latest harness run: `outputs/raw_query_answer_qa/20260514T113039Z_wave6b_full/report.md`
- Remaining risk: round labels in existing playoff history rows still rely on current extraction behavior; round extraction was intentionally not changed because single-team round-record execution remains unsupported.

## 2. Behavior before/after

### Heat Knicks playoff series record

- Before: `playoff_history`, `ok`, detected only `team=NYK`, returned Knicks single-team history.
- After: `playoff_matchup_history`, `ok`, detects `team_a=MIA`, `team_b=NYK`, returns `summary` and `comparison` like `Heat vs Knicks playoff history`.

### Single-team Finals/conference-finals records

- Before: `Warriors Finals record since 2015` returned broad regular-season Warriors record; Bulls/Celtics round-record phrasing routed through unsafe regular-season `team_record` paths.
- After: `Bulls Finals record`, `Warriors Finals record since 2015`, and `Celtics conference finals record` route to the playoff-history boundary and return `no_result` / `filter_not_supported`.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_matchup_utils.py` | production | Added narrow adjacent team-team extraction for explicit playoff series/history contexts. |
| `src/nbatools/commands/natural_query.py` | production | Wires adjacent playoff pair extraction; normalizes round-filter queries to playoff semantics; adds unsupported-boundary parser note. |
| `src/nbatools/commands/_playoff_record_route_utils.py` | production | Routes team+round+record/history phrasing to an unsupported playoff-history boundary instead of regular-season records. |
| `src/nbatools/commands/_natural_query_execution.py` | production | Adds user-facing unsupported-filter guidance for single-team playoff round records. |
| `tests/test_natural_query_parser.py` | tests | Parser regressions for adjacency, explicit `vs`, non-playoff adjacency guardrail, and unsupported single-team round records. |
| `tests/test_playoff_history_queries.py` | tests | Playoff route regressions for adjacency and unsupported single-team Finals record. |
| `tests/test_ui_failure_coverage.py` | tests | Data-backed regressions for Heat/Knicks matchup and unsupported round-record boundaries. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Updates AQ-020 expectations to passing matchup and expected unsupported boundary. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Marks AQ-020 fixed/fixed-as-unsupported with latest run. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Adds Wave 6B status, outputs, and remaining failures. |
| `docs/reference/query_catalog.md` | docs | Documents adjacent playoff matchup examples and single-team round-record boundary. |
| `docs/reference/query_guide.md` | docs | Adds playoff history/round examples and unsupported boundary notes. |

## 4. Product/data boundary decision

- Single-team round records: unsupported for now; blocked with `single_team_playoff_round_record`.
- Bulls Finals data: not marked supported because Bulls Finals-era rows are pre-2001 and lack reliable round labels in the current dataset.
- Round extraction: not changed in this wave.
- Future support path: fix zero-padded round extraction, approve a route/shape contract for entity-specific round records, add hard data tests for modern GSW/BOS counts, and document pre-2001 fallback/coverage semantics.

## 5. Behavior after change

- Heat/Knicks adjacency matchup: `Heat Knicks playoff series record` returns matchup sections.
- Existing vs matchup queries: `Heat vs Knicks playoff history` still passes.
- Warriors Finals since 2015: `no_result` / `filter_not_supported`, not a regular-season record; start season is preserved as `2015-16`.
- Celtics conference-finals record: `no_result` / `filter_not_supported`, not a regular-season record.
- Bulls Finals record: `no_result` / `filter_not_supported`; no false support for Bulls Finals-era data.
- Nearby playoff history/appearance routes: targeted regression harness passed for Lakers, Spurs, Finals appearances, and round-record leaderboards.

## 6. Test coverage

- `test_adjacent_playoff_team_phrasing_routes_to_matchup_history`: adjacent playoff team phrasing maps to `playoff_matchup_history`.
- `test_explicit_vs_playoff_matchup_still_routes_to_matchup_history`: existing `vs` route remains intact.
- `test_single_team_playoff_series_record_vs_opponent_preserves_opponent_filter`: `Lakers playoff series record vs Celtics` keeps the existing single-team/opponent-filter behavior.
- `test_adjacent_team_parsing_does_not_apply_without_playoff_context`: adjacency does not generalize to ordinary non-playoff text.
- `test_single_team_playoff_round_records_are_unsupported_boundary`: Bulls/Warriors/Celtics round-record phrases are blocked.
- `test_single_team_playoff_round_record_since_preserves_start_season`: Warriors since-year context remains `2015-16`.
- `test_adjacent_heat_knicks_series_record_matches_vs_family`: data-backed Heat/Knicks adjacency returns the same section family/counts as the explicit `vs` query.
- `test_single_team_round_records_return_unsupported_not_team_record`: data-backed single-team round phrases return clean unsupported/no-result responses.

## 7. QA harness validation

Targeted AQ-020:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260514T113039Z_wave6b_aq020_targeted --case heat_knicks_playoff_series_record_wave4 --case bulls_finals_record_wave4 --case warriors_finals_record_since_2015_wave4 --case celtics_conference_finals_record_wave4

Cases: 4
Result statuses: {'no_result': 3, 'ok': 1}
Expectation cases: {'pass': 4}
Failed case IDs: none
```

Adjacent playoff regression:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260514T113039Z_wave6b_playoff_regression --case heat_knicks_playoff_history --case lakers_playoff_history --case spurs_playoff_history_since_2000_wave4 --case lakers_finals_appearances --case most_finals_appearances_since_1980 --case best_finals_record_since_1980 --case most_conference_finals_appearances_wave4

Cases: 7
Result statuses: {'ok': 7}
Expectation cases: {'pass': 7}
Failed case IDs: none
```

Full corpus:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260514T113039Z_wave6b_full

Cases: 195
Result statuses: {'error': 8, 'no_result': 16, 'ok': 171}
Expectation cases: {'fail': 8, 'pass': 187}
Expectation checks: {'fail': 28, 'pass': 990}
Failed case IDs: centers_rebound_leaders_wave4, rookie_scoring_leaders_wave4, bench_scoring_leaders_wave4, starter_assist_leaders_wave4, celtics_bench_scoring_boundary_wave4, lebron_durant_comparison_wave4, personal_foul_leaders_wave4, celtics_against_east_record_wave4
```

Latest output path: `outputs/raw_query_answer_qa/20260514T113039Z_wave6b_full/report.md`

## 8. Standard validation

Backend:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "adjacent_playoff or single_team_playoff_round or explicit_vs_playoff_matchup or playoff_series_record_vs_opponent" -n0
10 passed, 154 deselected in 21.82s

.venv/bin/pytest tests/test_ui_failure_coverage.py -k "PlayoffRoutingBoundaries" -n0
4 passed, 95 deselected in 19.49s

.venv/bin/pytest tests/test_playoff_history_queries.py -k "adjacent_playoff_matchup_history_routes or single_team_finals_record_is_unsupported_boundary" -n0
2 passed, 82 deselected in 13.82s

make PYTEST=.venv/bin/pytest test-query
712 passed in 346.85s (0:05:46)

make PYTEST=.venv/bin/pytest test-preflight
2772 passed, 1 xpassed in 859.08s (0:14:19)
```

Not run:

```text
make PYTEST=.venv/bin/pytest test-engine
```

Reason: playoff-history execution internals and round extraction were intentionally not changed.

Harness:

```text
targeted AQ-020 run: pass, 4/4 expectation cases
adjacent playoff regression run: pass, 7/7 expectation cases
full corpus run: 187 pass, 8 fail
```

Always:

```text
git diff --check
passed with no output
```

Optional:

```text
.venv/bin/ruff check src/nbatools/commands/_matchup_utils.py src/nbatools/commands/_playoff_record_route_utils.py src/nbatools/commands/natural_query.py src/nbatools/commands/_natural_query_execution.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py tests/test_playoff_history_queries.py
All checks passed!
```

## 9. Updated findings / next recommendation

- AQ-020 status: fixed as matchup support plus expected unsupported boundary for single-team playoff round records.
- Remaining failed IDs: `centers_rebound_leaders_wave4`, `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, `lebron_durant_comparison_wave4`, `personal_foul_leaders_wave4`, `celtics_against_east_record_wave4`
- Remaining highest-priority findings: AQ-018 position/role leaderboards, AQ-019 player comparison routing, AQ-022 personal-foul stat boundary, AQ-023 opponent-conference filters.
- Recommended next phase: P2 position/role leaderboard and product-boundary cleanup, or explicit player comparison routing if comparison intent is the preferred next risk.
