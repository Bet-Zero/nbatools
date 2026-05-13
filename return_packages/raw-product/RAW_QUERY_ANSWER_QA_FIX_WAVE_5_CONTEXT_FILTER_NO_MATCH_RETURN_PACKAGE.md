# Raw Query Answer QA Fix Wave 5: Context / Filter Preservation + No-Match Diagnostics Return Package

## 1. Executive summary

- What was wrong: `Anthony Edwards` full-name queries resolved to Carmelo Anthony; `last season` stayed on the default 2025-26 season; `top defenses` was not mapped to the existing top-10 defense opponent-quality bucket; `KD TS% vs top defenses` returned a finder and dropped the quality context.
- What changed: data-backed full-name player matches now beat same-span nickname aliases; relative `last season` resolves to the previous latest season; `top defenses` maps to `top-10 defenses` only in explicit opponent context; player + stat + opponent-quality context now defaults to summary unless finder/count wording is explicit.
- Production code changed? yes.
- Tests added/updated: entity resolution, parser, metadata, and data-backed query regressions.
- Corpus updated: yes, all four target cases now have pass review status and hard assertions.
- Findings updated: yes, AQ-009, AQ-010, and AQ-012 are fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`
- Remaining risk: low. Full-name resolution now uses earliest entity precedence in full queries to avoid stealing later opponent names; preflight caught and validated that guard.

## 2. Behavior before/after

### Anthony Edwards full-name resolution

- Before: `Anthony Edwards last 10 games summary` and `How does Anthony Edwards shoot in wins versus losses?` resolved player as Carmelo Anthony and returned `no_result`.
- After: both resolve as Anthony Edwards. Last-10 returns a 10-game `player_game_summary`; wins/losses returns a `player_split_summary` with wins and losses buckets.

### Lakers road record last season

- Before: route was `team_record`, road filter was preserved, but season stayed `2025-26`, returning 25-16 away.
- After: `last season` resolves to `2024-25`; Lakers road record returns 41 games, 19 wins, and 22 losses with an explicit relative-season filter.

### KD TS% vs top defenses

- Before: `TS%` mapped to `ts_pct`, but `top defenses` was dropped; route was `player_game_finder`.
- After: route is `player_game_summary`; `stat=ts_pct` and `opponent_quality=top-10 defenses` are preserved; result is a 23-game Kevin Durant sample.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/entity_resolution.py` | production | Added data-backed full-name index and earliest-entity precedence with full-name priority at the same span. |
| `src/nbatools/commands/_matchup_utils.py` | production | Uses the resolver before legacy alias fallback so full names are honored consistently. |
| `src/nbatools/commands/_seasons.py` | production | Added previous-season helper. |
| `src/nbatools/commands/_parse_helpers.py` | production | Added singular relative-season parsing and `top defenses` opponent-context shorthand. |
| `src/nbatools/commands/_default_rules.py` | production | Added narrow player stat + opponent-quality summary default. |
| `src/nbatools/commands/natural_query.py` | production | Wired relative season, explicit relative-season metadata, and the new summary default. |
| `src/nbatools/query_service.py` | production | Exposes explicit relative-season applied filters and adds a team-abbreviation identity fallback. |
| `tests/test_entity_resolution.py` | tests | Full-name and single-token Anthony alias guardrails. |
| `tests/test_natural_query_parser.py` | tests | Parser coverage for Anthony Edwards, last season, top defenses, KD route, and guardrails. |
| `tests/test_backend_apply_patterns.py` | tests | Relative-season applied-filter metadata coverage. |
| `tests/test_ui_failure_coverage.py` | tests | Data-backed target case regressions. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Target expectations, row counts, hard assertions, and manual review statuses. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Closed AQ-009, AQ-010, AQ-012 and recorded latest 145/145 run. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Added Wave 5 context/filter status and latest harness outputs. |
| `docs/reference/query_catalog.md` | docs | Documented `last season`, `top defenses`, and full-name summary/split examples. |
| `docs/reference/query_guide.md` | docs | Added user-facing examples for target query forms. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | docs | Updated representative route examples. |

## 4. Behavior after change

- Anthony Edwards summary: `player_game_summary`, status `ok`, summary player Anthony Edwards, 10 games, `game_log` 10 rows.
- Anthony Edwards win/loss split: `player_split_summary`, status `ok`, summary player Anthony Edwards, `games_total=61`, split buckets `wins` and `losses`.
- Lakers road record last season: `team_record`, status `ok`, season `2024-25`, away filter, 41 games, 19-22.
- KD TS% vs top defenses: `player_game_summary`, status `ok`, player Kevin Durant, `ts_pct`, opponent quality `top-10 defenses`, 23 games.
- Nearby/guardrail cases: `Ant Edwards last 10 games`, explicit `2024-25` road record, `KD TS% vs top 10 defenses`, and player-vs-player opponent filters remain valid; free-standing `best defenses this season` is not converted into opponent quality.

## 5. Test coverage

- `tests/test_entity_resolution.py`: proves Anthony Edwards full names resolve before the `anthony` nickname alias, `Ant Edwards` remains supported through existing coverage, and single-token `anthony` still resolves to Carmelo Anthony.
- `tests/test_natural_query_parser.py`: proves target parses for Anthony Edwards, `last season`, KD TS/top defenses, exact top-10 variants, and no `last 10 games` / free-standing top-defense regressions.
- `tests/test_backend_apply_patterns.py`: proves explicit relative `last season` exposes a season applied filter while plain explicit season behavior remains unchanged.
- `tests/test_ui_failure_coverage.py`: proves the four target queries return data-backed rows and exact counts.

## 6. QA harness validation

- Targeted command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T093000Z_wave5_targeted --case anthony_edwards_last_10_summary_no_match --case kd_ts_top_defenses_missing_filters --case lakers_road_record_last_season --case anthony_edwards_wins_losses_split_no_match`
  - Result: 4 cases; result statuses `ok: 4`; expectation cases `pass: 4`; expectation checks `pass: 41`; failed IDs none; suspicious flags 0.
- Adjacent command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T093500Z_wave5_adjacent --case luka_last_5_summary --case tatum_playoff_teams_summary --case jokic_home_away_split --case celtics_wins_losses_split --case knicks_road_record --case lakers_held_opponents_under_100_record --case celtics_scored_over_120_record`
  - Result: 7 cases; result statuses `ok: 7`; expectation cases `pass: 7`; expectation checks `pass: 39`; failed IDs none; suspicious flags 0.
- Full command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T094000Z_wave5_full`
  - Result: 145 cases; result statuses `ok: 129`, `no_result: 10`, `error: 6`; expectation cases `pass: 145`; expectation checks `pass: 746`; failed IDs none.
  - Latest output path: `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`
  - Remaining failed case IDs: none.
  - Suspicious / informational / verified counts: suspicious flag cases `0`; informational flag cases `76` (`frontend_hero_expected: 76`); verified outlier cases `1` (`top_performance_high_points: 1`).

## 7. Standard validation

Backend:

- `.venv/bin/pytest tests/test_entity_resolution.py -n0`: 119 passed in 35.54s.
- `.venv/bin/pytest tests/test_natural_query_parser.py -n0`: 149 passed in 100.30s.
- `.venv/bin/pytest tests/test_backend_apply_patterns.py tests/test_ui_failure_coverage.py -k "team_context or RawQueryAnswerWave5Coverage or relative_last_season_filter_present" -n0`: 5 passed, 128 deselected in 14.25s.
- `.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_record_when_player_special_event_filters_summary_and_game_log tests/test_query_service.py::TestMetadataPreservation::test_structured_team_metadata_has_team_context tests/test_query_service.py::TestMetadataPreservation::test_structured_team_comparison_metadata_has_teams_context -n0`: 3 passed in 6.07s.
- `make PYTEST=.venv/bin/pytest test-parser`: 673 passed in 128.45s.
- `make PYTEST=.venv/bin/pytest test-query`: 706 passed in 204.52s.
- `make PYTEST=.venv/bin/pytest test-preflight`: final rerun passed with 2749 passed, 1 xpassed in 554.83s. An earlier preflight run exposed a team identity metadata edge case; the final run above is after the fix.

Harness:

- Targeted run: `outputs/raw_query_answer_qa/20260513T093000Z_wave5_targeted/report.md`
- Adjacent run: `outputs/raw_query_answer_qa/20260513T093500Z_wave5_adjacent/report.md`
- Full corpus run: `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`

Always:

- `git diff --check`: passed with no output.

Optional:

- `.venv/bin/ruff check src/nbatools/commands/entity_resolution.py src/nbatools/commands/_matchup_utils.py src/nbatools/commands/_parse_helpers.py src/nbatools/commands/_seasons.py src/nbatools/commands/_default_rules.py src/nbatools/commands/natural_query.py src/nbatools/query_service.py tests/test_entity_resolution.py tests/test_natural_query_parser.py tests/test_backend_apply_patterns.py tests/test_ui_failure_coverage.py`: `All checks passed!`

## 8. Updated findings / next recommendation

- AQ-009 status: fixed.
- AQ-010 status: fixed.
- AQ-012 status: fixed.
- Remaining failed IDs: none.
- Recommended next phase: because the corpus is now 145/145 with zero suspicious flags, choose explicitly between another corpus expansion wave, frontend hero/copy QA, targeted backend answer phrase enrichment, or a P2 product-boundary family such as position-filtered leaderboards / count phrase quality.
