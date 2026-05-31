# Natural Query Route Priority Snapshot Preflight

Discovery date: 2026-05-21

Scope: documentation-only preflight for the next safety-net wave before any
additional `src/nbatools/commands/natural_query.py` extraction. This preflight
does not change production code, tests, parser/routing behavior, QA corpus
expectations, result contracts, API behavior, or frontend behavior.

## Executive Summary

Existing parser and query coverage is broad, but the extraction-critical
coverage is scattered across `tests/test_natural_query_parser.py`,
`tests/test_ui_failure_coverage.py`, `tests/test_query_service.py`, route-family
tests, and `qa/raw_query_answer_corpus.yaml`. That is enough for regression
confidence, but it is not enough as a compact review tool for route-priority
preservation.

The next safety-net wave should add dedicated snapshots, not behavior changes:

- a new parser-level route-priority snapshot file that pins selected route,
  key route kwargs, unsupported-filter metadata, and note tags for collision
  phrases
- a new query-level unsupported/no-broad-fallback snapshot file that pins
  `result_status`, `result_reason`, empty sections, and
  `metadata.unsupported_filters`
- a new raw QA harness slice that groups existing high-risk route-priority and
  product-boundary corpus cases for cheap reruns during extraction

First executable wave recommendation: add the dedicated parser snapshot file,
the dedicated query unsupported snapshot file, and a harness slice using
existing raw QA case IDs. Do not change `natural_query.py` in that wave. Do not
change existing corpus expectations.

Historical gap found: division-opponent phrasing was policy-documented as a
guarded unsupported boundary, but behavior broad-fell back when this preflight
was written. Division Phrase Boundary Cleanup has since resolved that gap:
explicit NBA division opponent phrases now return `no_result` /
`filter_not_supported` with `unsupported_filters=["opponent_division"]`, while
preserving the closest record route and adding no division support.

## Inputs Inspected

Required inputs:

- `working/natural-query-maintenance/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `working/natural-query-maintenance/NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`
- `docs/operations/parser_routing_growth_guardrails.md`
- `docs/operations/feature_promotion_rules.md`
- `src/nbatools/commands/natural_query.py`
- parser/query tests under `tests/`
- `qa/raw_query_answer_corpus.yaml`

Additional files inspected:

- `qa/harness_slices/*.yaml`
- `Makefile`
- representative raw-product preflight and return package artifacts

Read-only verification performed:

- `parse_query()` checks for candidate collision and boundary phrases
- `execute_natural_query()` checks for candidate route/status/reason/section
  behavior
- markdown-lint binary discovery checks

## Existing Coverage Findings

| Area | Existing coverage | Gap before extraction |
|---|---|---|
| Parser route and slot behavior | `tests/test_natural_query_parser.py`, `tests/test_parser_equivalence_groups.py`, `tests/test_word_order_equivalence.py`, route-family parser tests | Strong but scattered; no compact route-priority snapshot matrix. |
| Unsupported parser boundaries | `test_p2_boundary_queries_set_unsupported_filter`, opponent-conference tests, single-team playoff-round tests, on/off, lineup, stretch, advanced-stat tests | Unsupported filters are not grouped by extraction risk. |
| Execution unsupported/no-broad-fallback | `tests/test_ui_failure_coverage.py`, `tests/test_query_service.py::TestOpponentConferenceTeamRecords`, raw QA no-result cases | Good targeted regressions, but no single matrix asserting no broad rows for all high-risk unsupported filters. |
| Collision phrases | Covered across parser, query, route-family tests, and raw QA | No dedicated collision snapshot file that makes route winner changes obvious. |
| Raw QA corpus | Many high-risk cases exist with route/status/reason/sections and hard assertions | No dedicated `natural_query_route_priority` harness slice; `conference_coverage` is query-service tested but not a raw QA case. |
| Harness slices | Existing slices cover product boundaries, playoff phrasing, team/date context, player/stat context, and defensive aliases | No extraction-era slice that composes route priority, collision, unsupported-boundary, and no-broad-fallback cases. |

## Placement Recommendations

### Parser snapshots

Add:

```text
tests/test_natural_query_route_priority_snapshots.py
```

Mark it `pytestmark = pytest.mark.parser`.

Use this file for behavior that can be pinned without data:

- selected route
- intent when it matters
- route kwargs subset
- unsupported filter list in `route_kwargs`
- absence/presence of collision-prone slots, such as `opponent_player`,
  `opponent_conference`, `without_player`, `team_a`, and `team_b`
- note tag substrings, such as `unsupported_boundary` and `boundary_fragment`

Do not put these snapshots into `tests/test_natural_query_parser.py`; that file
already carries broad parser behavior and is large. A dedicated file makes
future extraction review easier.

### Query unsupported snapshots

Add:

```text
tests/test_natural_query_unsupported_boundary_snapshots.py
```

Mark it `pytestmark = pytest.mark.query`. Use `pytest.mark.needs_data` for
cases that execute against local datasets.

Use this file for execution-level behavior:

- `qr.route`
- `qr.result.result_status`
- `qr.result.result_reason`
- `qr.metadata["unsupported_filters"]`
- `qr.to_dict()["sections"] == {}` for unsupported/no-result cases
- no broad fallback sections for unsupported filters

Prefer a new file over adding more cases to `tests/test_ui_failure_coverage.py`.
The existing file remains valuable, but it mixes multiple raw QA fix waves and
is not shaped as an extraction snapshot matrix.

### Raw QA corpus and harness slices

For the first executable safety-net wave, add a new harness slice:

```text
qa/harness_slices/natural_query_route_priority.yaml
```

The first slice should reference existing `qa/raw_query_answer_corpus.yaml` case
IDs only. That gives extraction reruns without changing corpus expectations.

Add new raw QA cases only in a follow-up wave for true coverage gaps:

- `Celtics record against the East in 2023-24` for the `conference_coverage`
  no-broad-fallback boundary
- division phrasing now has cleanup-wave coverage; see the raw guard cases in
  `qa/harness_slices/natural_query_route_priority.yaml` and
  `qa/harness_slices/product_boundaries.yaml`

## First Executable Test Wave

Recommended first executable wave, in order:

1. Add `tests/test_natural_query_route_priority_snapshots.py`.
2. Add `tests/test_natural_query_unsupported_boundary_snapshots.py`.
3. Add `qa/harness_slices/natural_query_route_priority.yaml` using existing
   raw QA case IDs.
4. Run parser/query/raw QA validation.
5. Stop. Do not extract code in the same wave.

This is intentionally a tests-only wave. It should not change production code,
parser behavior, route behavior, or existing raw QA expectations.

## Parser Snapshot Matrix

These cases belong in `tests/test_natural_query_route_priority_snapshots.py`.
The parser test should assert route and key parse/route-kwargs slots. Execution
status/reason below records current behavior for cross-checking and raw QA
placement.

| Group | Query | Expected route | Parser slots to pin | Status | Reason |
|---|---|---|---|---|---|
| Opponent conference supported | `Celtics record against the East this season` | `team_record` | `team=BOS`, `opponent_conference=East`, no `unsupported_filters` | `ok` |  |
| Conference Finals record boundary | `Celtics conference finals record` | `playoff_history` | `season_type=Playoffs`, `playoff_round=03`, `unsupported_filters=["single_team_playoff_round_record"]` | `no_result` | `filter_not_supported` |
| Geography boundary | `Celtics record against east coast teams` | `team_record` | `team=BOS`, `opponent_conference is None`, `opponent_conference_geography_boundary=True`, `unsupported_filters=["opponent_conference"]` | `no_result` | `filter_not_supported` |
| Conference Finals appearance support | `most conference finals appearances` | `playoff_appearances` | `season_type=Playoffs`, `playoff_round=03` | `ok` |  |
| Single-team record | `Lakers record since 2010` | `team_record` | `team=LAL`, `start_season=2010-11` | `ok` |  |
| Team matchup record | `Warriors vs Lakers record this season` | `team_matchup_record` | `team_a=GSW`, `team_b=LAL` | `ok` |  |
| Team comparison | `Celtics vs Bucks comparison this season` | `team_compare` | `team_a=BOS`, `team_b=MIL`, `head_to_head=False` | `ok` |  |
| Player comparison | `LeBron James vs Kevin Durant comparison` | `player_compare` | `player_a=LeBron James`, `player_b=Kevin Durant`, no `opponent_player` | `ok` |  |
| Player-vs-player opponent finder | `LeBron stats vs Kevin Durant` | `player_game_finder` | `player=LeBron James`, `opponent_player=Kevin Durant` | `ok` |  |
| Player-vs-player game log | `Jokic game log vs Embiid` | `player_game_finder` | `player=Nikola Jokić`, `opponent_player=Joel Embiid` | `no_result` | `no_match` |
| Top single-game performance | `What were the most assists in a game this season?` | `top_player_games` | `stat=ast`, note contains `season_high` | `ok` |  |
| Ordinary leaderboard | `Who leads the NBA in assists this season?` | `season_leaders` | `stat=ast`, no `season_high` note | `ok` |  |
| On/off route | `Nuggets net rating with Nikola Jokic on the floor versus off the floor` | `player_on_off` | `team=DEN`, `lineup_members=["Nikola Jokić"]`, `presence_state=both`, `stat=net_rating`, `without_player is None` | `no_result` | `unsupported` |
| Whole-game absence | `Lakers record without LeBron` | `team_record` | `team=LAL`, `without_player=LeBron James` | `ok` |  |
| Team rolling-stretch boundary | `best 5-game team scoring stretch this season` | `player_stretch_leaderboard` | `window_size=5`, `stretch_metric=pts`, `unsupported_filters=["team_rolling_stretch"]` | `no_result` | `filter_not_supported` |
| Player rolling-stretch support | `Jokic best 5-game rebounding stretch this season` | `player_stretch_leaderboard` | `player=Nikola Jokić`, `window_size=5`, `stretch_metric=reb`, no `unsupported_filters` | `ok` |  |
| Single-team advanced scalar boundary | `Warriors net rating this season` | `game_summary` | `team=GSW`, `stat=net_rating`, `unsupported_filters=["single_team_advanced_stat_summary"]` | `no_result` | `filter_not_supported` |
| League team advanced leaderboard | `best net rating teams this season` | `season_team_leaders` | `stat=net_rating`, no `unsupported_filters` | `ok` |  |

## Unsupported And No-Broad-Fallback Matrix

These cases belong in
`tests/test_natural_query_unsupported_boundary_snapshots.py`. They should assert
`sections == {}` for `no_result` or error cases and should not accept a broad
leaderboard, broad record, or broad finder response.

| Boundary | Query | Expected route | Status | Reason | Unsupported filter |
|---|---|---|---|---|---|
| Team rolling stretch | `best 5-game team scoring stretch this season` | `player_stretch_leaderboard` | `no_result` | `filter_not_supported` | `team_rolling_stretch` |
| Rookie leaderboard | `rookie assist leaders this season` | `season_leaders` | `no_result` | `filter_not_supported` | `rookie_leaderboard` |
| League role leaderboard | `bench rebound leaders this season` | `season_leaders` | `no_result` | `filter_not_supported` | `role_leaderboard` |
| Team bench scoring | `Celtics bench points this season` | `game_finder` | `no_result` | `filter_not_supported` | `team_bench_scoring` |
| Personal fouls | `players with most personal fouls this season` | `season_leaders` | `no_result` | `filter_not_supported` | `personal_foul_leaderboard` |
| Opponent geography | `Celtics record against east coast teams` | `team_record` | `no_result` | `filter_not_supported` | `opponent_conference` |
| Opponent conference coverage | `Celtics record against the East in 2023-24` | `team_record` | `no_result` | `filter_not_supported` | `conference_coverage` |
| Single-team advanced scalar | `Warriors net rating this season` | `game_summary` | `no_result` | `filter_not_supported` | `single_team_advanced_stat_summary` |
| Single-team playoff round record | `Celtics conference finals record` | `playoff_history` | `no_result` | `filter_not_supported` | `single_team_playoff_round_record` |
| Multi-player availability | `What is the Lakers record when LeBron James and Anthony Davis both play?` | `team_record` | `no_result` | `filter_not_supported` | `multi_player_availability` |
| On/off data gap | `Nuggets net rating with Nikola Jokic on the floor versus off the floor` | `player_on_off` | `no_result` | `unsupported` |  |
| Lineup data gap | `best 5-man lineups` | `lineup_leaderboard` | `no_result` | `unsupported` |  |
| Clutch unsupported data | `Tatum clutch stats` | `player_game_summary` | `no_result` | `filter_not_supported` |  |
| Subjective clutch leaderboard | `Who is the most clutch player this season?` | `season_leaders` | `no_result` | `filter_not_supported` |  |
| Subjective trend | `who has cooled off lately` |  | `error` | `unrouted` |  |
| Subjective duo | `Who is the best duo this season?` |  | `error` | `unrouted` |  |
| Existing note-tagged boundary fragment | `in clutch time` | `season_leaders` | `no_result` | `filter_not_supported` |  |

The `in clutch time` case documents current behavior only. It should not be
used as precedent to add new broad fallback branches during extraction.

## Raw QA Harness Slice

Add this slice in the first executable wave:

```text
qa/harness_slices/natural_query_route_priority.yaml
```

Recommended case IDs, all currently present in `qa/raw_query_answer_corpus.yaml`:

```yaml
name: natural_query_route_priority
description: Route-priority, collision, unsupported-boundary, and no-broad-fallback cases before natural_query.py extraction.
case_ids:
  - lakers_record_against_west_wave5
  - celtics_against_east_coast_teams_guard
  - celtics_conference_finals_record_wave4
  - most_conference_finals_appearances_wave4
  - lakers_record_since_2010_wave4
  - warriors_lakers_record_this_season_wave5
  - celtics_bucks_comparison_this_season_wave5
  - lebron_durant_comparison_wave4
  - lebron_stats_vs_durant_wave5
  - jokic_game_log_vs_embiid_wave5
  - most_assists_single_game
  - assist_leaders_this_season
  - nuggets_jokic_on_off_unsupported
  - lakers_without_lebron
  - team_5_game_scoring_stretch
  - jokic_5_game_rebound_stretch
  - warriors_net_rating_single_team_wave5
  - net_rating_team_leaders
  - rookie_assist_leaders_wave5
  - bench_rebound_leaders_wave5
  - celtics_bench_points_wave5
  - players_personal_fouls_wave5
  - lakers_lebron_ad_both_play
  - best_5_man_lineups_unsupported
  - tatum_clutch_stats
  - most_clutch_player_wave5
  - cooled_off_lately_wave5
  - best_duo_unsupported
```

Do not add `Celtics record vs Atlantic Division` to this slice as an
unsupported case until the product boundary is deliberately changed and
implementation follows.

## Raw QA Corpus Gaps

Add or consider these only after the first snapshot wave:

| Gap | Recommended action |
|---|---|
| `conference_coverage` lacks raw QA corpus coverage | Add `Celtics record against the East in 2023-24` with `team_record`, `no_result`, `filter_not_supported`, empty sections, and `metadata.unsupported_filters.0 == conference_coverage`. Existing query-service coverage already pins this. |
| Division phrasing cleanup is complete | Keep the new expected-unsupported raw QA cases in the route-priority and product-boundary slices. Expected behavior is `no_result` / `filter_not_supported`, empty sections, and `metadata.unsupported_filters.0 == opponent_division`, except conference-finals record phrasing which remains `single_team_playoff_round_record`. |
| Existing note-tagged fallback fragments are not separately sliced | If extraction touches boundary-fragment notes, add a narrow parser snapshot for `in clutch time` and `against winning teams`, but do not expand the fallback family. |

## Validation Commands

Docs-only validation for this preflight:

```text
git diff --check
markdown lint if available
```

Recommended validation for the first executable test wave:

```text
make PYTEST=.venv/bin/pytest test-parser
make PYTEST=.venv/bin/pytest test-query
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --fail-on-expectation-failure
git diff --check
```

Recommended validation before any later `natural_query.py` extraction:

```text
make PYTEST=.venv/bin/pytest test-parser
make PYTEST=.venv/bin/pytest test-query
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --fail-on-expectation-failure
make PYTEST=.venv/bin/pytest test-preflight
```

Use `test-preflight`, not `test-impacted`, for route or parse-state changes in
`natural_query.py`; it is a high-fan-in module.

## Stop Conditions

Stop and re-plan if the first executable snapshot wave:

- requires changes to `natural_query.py`
- requires changing existing raw QA expectations
- makes unsupported queries return `ok` broad rows
- accepts broad fallback behavior for a boundary case that should be a
  no-result/error snapshot
- tries to treat division phrasing as already fixed
- adds query support rather than snapshotting current behavior
- changes result contracts, API behavior, frontend rendering, or data
  requirements
- folds route-priority snapshots into a broader parser rewrite
- removes or weakens existing unsupported-boundary tests

Stop and re-plan if a later extraction wave:

- changes selected route, route kwargs, notes, caveats, confidence, or
  alternates for the snapshot matrix
- changes `result_status`, `result_reason`, sections, row shape, or
  `metadata.unsupported_filters`
- changes QA corpus expectations to make an extraction pass
- expands existing note-tagged broad fallback branches
- touches opponent-conference/division parsing before the division boundary is
  explicitly decided
