# Natural Query Decision Map and Test Matrix

## 1. Purpose and scope

This document is the first recommended wave from
`NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`. It is documentation only.

It records the current `src/nbatools/commands/natural_query.py` structure,
current `_finalize_route()` decision order, unsupported boundaries, route
collision groups, and extraction test matrix before any code is moved.

This document does not change parser, routing, backend, frontend,
result-contract, test, or QA-corpus behavior. It does not add query support.
The current route order is a behavior contract until a future preflight
explicitly says otherwise.

Core rules for future extraction:

- Wrong-route prevention matters more than making vague queries work.
- Unsupported boundaries are shipped behavior, not gaps to smooth over.
- No broad fallback answers for unsupported or low-confidence queries.
- Do not expand the small number of existing note-tagged fallback branches
  during extraction.
- Extraction must preserve route, route kwargs, notes, caveats,
  `result_status`, `result_reason`, and `metadata.unsupported_filters`.

## 2. Inputs inspected

- `docs/planning/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`
- `return_packages/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT_RETURN_PACKAGE.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`
- `src/nbatools/commands/natural_query.py`
- natural query / parser / routing tests under `tests/`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/*.yaml`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `docs/index.md`
- `Makefile`

## 3. Current `natural_query.py` structure map

| Lines | Section | Current responsibility | Extraction note |
| --- | --- | --- | --- |
| 1-247 | Imports and helper-module surface | Imports normalization, date, defaulting, leaderboard, matchup, occurrence, parser-helper, playoff, execution, confidence, and entity-resolution helpers. | Many helpers are already extracted. The import and `__all__` surface is compatibility-sensitive. |
| 249-281 | Local constants | `_UNSUPPORTED_BOUNDARY_PHRASES`; `_TEAM_SEASON_ADVANCED_STATS`. | Pure constants are the lowest-risk later code candidate, but not in this docs wave. |
| 284-424 | Local boundary / intent helpers | Unsupported-boundary note, single-team advanced-stat boundary, multi-player availability boundary, stretch display mode, specific-date top-scorer intent, team W/L phrasing, Washington/WAS guards, ambiguous-fragment note, placeholder-template note. | Behavior-sensitive because notes, unsupported filters, and route eligibility are coupled. |
| 430-504 | `__all__` compatibility exports | Re-exports local and imported helpers used by tests or downstream modules. | Do not trim during extraction without caller checks. |
| 507-918 | `_build_parse_state(query)` | Normalizes text and extracts season/date/stat/entity/context/threshold/intent/unsupported-boundary slots. | Main parse-state assembly risk. |
| 921-968 | Route condition helpers | Builds canonical condition lists and mutates route kwargs / parsed state for compound conditions. | Small but stateful; not a first extraction target. |
| 971-2300 | `_finalize_route(parsed)` | Procedural route-priority chain, route kwargs, unsupported filters, notes, shared post-processing, confidence, alternates. | Primary wrong-route risk. Current order is contract. |
| 2303-2304 | `parse_query(query)` | Thin public parser wrapper over `_build_parse_state()` then `_finalize_route()`. | Keep thin. |
| 2307-2383 | `_merge_inherited_context(base, clause)` | Inherits context for boolean/OR clause execution and re-finalizes route. | Behavior-sensitive for compound queries. |
| 2386-2404 | `run(...)` | CLI-facing wrapper through `execute_natural_query()` and rendering/export. | Presentation wrapper; do not move business logic here. |

Already extracted helper modules include `_constants.py`, `_date_utils.py`,
`_default_rules.py`, `_leaderboard_utils.py`, `_matchup_utils.py`,
`_occurrence_route_utils.py`, `_parse_helpers.py`,
`_playoff_record_route_utils.py`, `_natural_query_execution.py`, and
`entity_resolution.py`.

## 4. Current `_finalize_route()` decision order

The following order is the current route contract. Later extraction may split
helpers, but it must not reorder these decisions without a separate preflight
and expanded collision coverage.

| Order | Current branch | Route / behavior |
| --- | --- | --- |
| 0 | Propagate occurrence event stat/minimum slots before routing. | Mutates local `stat` / `min_value`; no route selected yet. |
| 1 | Unresolved entity ambiguity short-circuit. | `route=None`, `intent=unsupported`, ambiguity note. |
| 2 | Ambiguous fragment short-circuit. | `route=None`, `intent=unsupported`, `source=ambiguous_fragment`. |
| 3 | Placeholder template short-circuit. | `route=None`, `intent=unsupported`, `source=placeholder_template`. |
| 4 | On/off presence request with lineup members and presence state. | `player_on_off`. |
| 5 | Specific lineup summary request. | `lineup_summary`. |
| 6 | Lineup leaderboard request. | `lineup_leaderboard`. |
| 7 | Team rolling-stretch boundary before player stretch support. | `player_stretch_leaderboard` plus `unsupported_filters=["team_rolling_stretch"]`. |
| 8 | Player / league rolling-stretch support. | `player_stretch_leaderboard`. |
| 9 | Single-player season-high intent. | `player_game_finder`, sorted by selected stat. |
| 10 | League-wide season-high / single-game-best intent. | `top_player_games`. |
| 11 | Distinct player count with occurrence or threshold. | `player_occurrence_leaders`. |
| 12 | Single-team streak request. | `team_streak_finder`. |
| 13 | Playoff / record / decade helper. | `try_playoff_record_route(parsed)`. |
| 14 | Player split request. | `player_split_summary`. |
| 15 | Team split request. | `team_split_summary`. |
| 16 | Two-player comparison. | `player_compare`. |
| 17 | Two-team record / matchup intent. | `team_matchup_record`. |
| 18 | Two-team comparison without record intent. | `team_compare`. |
| 19 | Single-player streak request. | `player_streak_finder`. |
| 20 | Literal top player games branch. | `top_player_games`. |
| 21 | Top team games branch. | `top_team_games`. |
| 22 | Compound occurrence helper. | `try_compound_occurrence_route(parsed)`. |
| 23 | Record-leaderboard helper. | `try_record_leaderboard_route(parsed)`. |
| 24 | Personal-foul leaderboard boundary. | `season_leaders`, `stat="pf"`, `unsupported_filters=["personal_foul_leaderboard"]`. |
| 25 | Rookie leaderboard boundary. | `season_leaders`, `unsupported_filters=["rookie_leaderboard"]`. |
| 26 | League-wide starter/bench leaderboard boundary. | `season_leaders`, `unsupported_filters=["role_leaderboard"]`. |
| 27 | Team bench-scoring boundary. | `game_finder`, `unsupported_filters=["team_bench_scoring"]`. |
| 28 | Opponent-conference geography boundary. | `team_record`, `unsupported_filters=["opponent_conference"]`. |
| 29 | Supported opponent-conference team record. | `team_record` with `opponent_conference`. |
| 30 | Single-team advanced-stat scalar boundary. | `game_summary`, `unsupported_filters=["single_team_advanced_stat_summary"]`. |
| 31 | Explicit-date top-scorer branch. | `top_player_games`, `stat="pts"`. |
| 32 | Context-only boundary fragment. | `season_leaders`, `stat="pts"`, note-tagged broad fallback. |
| 33 | Metric-only leaderboard default. | `season_team_leaders` or `season_leaders`; includes local stat-availability fallback constants. |
| 34 | Single-player special-event occurrence count helper. | `try_occurrence_count_route(parsed)`. |
| 35 | Explicit player finder/count. | `player_game_finder`. |
| 36 | Explicit team finder/count. | `game_finder`. |
| 37 | Multi-player availability boundary for team records. | `team_record`, `unsupported_filters=["multi_player_availability"]`. |
| 38 | Player summary. | `player_game_summary`. |
| 39 | Single-team record. | `team_record`. |
| 40 | Team summary. | `game_summary`. |
| 41 | Player fallback finder. | `player_game_finder`. |
| 42 | Team fallback finder. | `game_finder`. |
| 43 | No route selected. | Raise `ValueError`. |

Shared post-processing then attaches shared context kwargs, applies compound
route conditions, derives intent, appends parser notes, computes confidence,
and generates alternates. That post-processing is also behavior: note order,
unsupported metadata, and confidence/alternate shape must be preserved.

## 5. Unsupported-boundary inventory

These boundaries are current product behavior. Some return explicit
`no_result` / `filter_not_supported`; some intentionally route to an existing
route and rely on execution to report unsupported data; a small number append
an `unsupported_boundary` or `boundary_fragment` note to a broad fallback. Do
not broaden unsupported queries into successful answers during extraction.

| Boundary | Current parser route | Current result / metadata expectation | Existing coverage |
| --- | --- | --- | --- |
| Entity ambiguity | `route=None` | Unsupported intent with ambiguity note and alternates. | Parser behavior is indirectly covered by entity-resolution and parser tests. |
| Ambiguous fragments | `route=None` | Unsupported intent with `source=ambiguous_fragment`. | Raw corpus subjective/unrouted cases such as `best_defender_subjective`, `mvp_candidates_subjective`, `best_player_lately_ambiguous`, `cooled_off_last_10`, `cooled_off_lately_wave5`. |
| Placeholder templates | `route=None` | Unsupported intent with `source=placeholder_template`; no runnable route. | `tests/test_ui_failure_coverage.py::test_placeholder_templates_fail_cleanly`. |
| Broad semantic boundary phrases in `_UNSUPPORTED_BOUNDARY_PHRASES` | Existing route if one matched, otherwise error. | Adds `unsupported_boundary` note; returned rows, when present, are broad fallbacks for the unsupported concept. | `test_unsupported_boundary_note_for_semantic_fallback`, `test_unsupported_boundary_note_for_above_point_six_hundred_record_bucket`; raw cases `cooled_off_last_10`, `cooled_off_lately_wave5`. |
| Context-only boundary fragments | `season_leaders` | Broad points leaderboard fallback with `boundary_fragment` note. | `test_route_context_only_boundary_fragment_with_fallback_note`, `test_route_opponent_quality_boundary_fragment_with_fallback_note`. This is current behavior, not permission to add new broad fallbacks. |
| Team rolling-stretch leaderboards | `player_stretch_leaderboard` | `no_result` / `filter_not_supported`; `unsupported_filters=["team_rolling_stretch"]`; empty sections. | Parser: `test_team_scoped_rolling_stretch_sets_unsupported_filter`; execution: `test_team_scoped_rolling_stretch_returns_unsupported_not_player_rows`; raw cases `team_5_game_scoring_stretch`, `team_net_rating_stretch_unsupported`. |
| Personal-foul leaderboards | `season_leaders`, `stat="pf"` | `no_result` / `filter_not_supported`; `unsupported_filters=["personal_foul_leaderboard"]`; no broad points leaderboard. | Parser: `test_personal_foul_leaderboard_variants_are_unsupported_boundaries`, `test_p2_boundary_queries_set_unsupported_filter`; execution: `test_unsupported_boundary_queries_return_no_result`; raw cases `personal_foul_leaders_wave4`, `players_personal_fouls_wave5`. |
| Rookie leaderboards | `season_leaders` | `no_result` / `filter_not_supported`; `unsupported_filters=["rookie_leaderboard"]`. | Parser and execution P2 boundary tests; raw cases `rookie_scoring_leaders_wave4`, `rookie_assist_leaders_wave5`. |
| League-wide starter/bench leaderboards | `season_leaders` | `no_result` / `filter_not_supported`; `unsupported_filters=["role_leaderboard"]`. | Parser and execution P2 boundary tests; raw cases `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `bench_rebound_leaders_wave5`. |
| Team bench scoring / points | `game_finder` | `no_result` / `filter_not_supported`; `unsupported_filters=["team_bench_scoring"]`. | Parser and execution P2 boundary tests; raw cases `celtics_bench_scoring_boundary_wave4`, `celtics_bench_points_wave5`. |
| Opponent-conference geography | `team_record` | `no_result` / `filter_not_supported`; `unsupported_filters=["opponent_conference"]`; `opponent_conference` remains empty. | Parser: `test_east_coast_teams_does_not_parse_as_opponent_conference`; execution: `test_east_coast_teams_remains_unsupported_without_broad_record`; raw case `celtics_against_east_coast_teams_guard`. |
| Opponent-conference missing/untrusted coverage | `team_record` | `no_result` / `filter_not_supported`; `unsupported_filters=["conference_coverage"]`; no broad full-season record. | `tests/test_query_service.py::TestOpponentConferenceTeamRecords` missing coverage tests; docs in `query_catalog.md` and `query_guide.md`. |
| Division filters near opponent-conference phrasing | Not promoted as supported. | Expected unsupported by policy; no broad team-record fallback. | Documented in `FEATURE_PROMOTION_RULES.md`, `PARSER_ROUTING_GROWTH_GUARDRAILS.md`, `query_catalog.md`, and `query_guide.md`; needs explicit route/corpus cases before any adjacent extraction changes. |
| Single-team advanced-stat scalar summaries | `game_summary` | `no_result` / `filter_not_supported`; `unsupported_filters=["single_team_advanced_stat_summary"]`. League-wide team advanced leaderboards remain supported. | Parser: `test_single_team_advanced_stat_scalar_queries_are_unsupported_boundaries`, `test_league_wide_team_advanced_leaderboards_still_route`; execution: `test_single_team_advanced_stat_summaries_return_unsupported_boundary`; raw case `warriors_net_rating_single_team_wave5`. |
| Single-team playoff round records | `playoff_history` | `no_result` / `filter_not_supported`; `unsupported_filters=["single_team_playoff_round_record"]`; no regular-season `team_record` fallback. | Parser: `test_single_team_playoff_round_records_are_unsupported_boundary`; execution: `test_single_team_round_records_return_unsupported_not_team_record`; raw cases `bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, question-form variants. |
| Multi-player availability records | `team_record` | `no_result` / `filter_not_supported`; `unsupported_filters=["multi_player_availability"]`; no unfiltered record. | Parser/execution: `TestWithoutPlayer` multi-player availability tests; raw case `lakers_lebron_ad_both_play`. |
| On/off data gaps | `player_on_off` | Route exists; execution returns unsupported/no-result when trusted on/off coverage is missing for the slice. Whole-game absence remains separate. | Parser: on/off route tests; raw cases `nuggets_jokic_on_off_unsupported`, `celtics_tatum_on_off_boundary_wave4`; source-backed coverage tests under `test_source_backed_on_off_dataset.py`. |
| Lineup data gaps | `lineup_summary` / `lineup_leaderboard` | Route exists; execution returns unsupported/no-result when trusted lineup coverage is missing or outside contract. | Parser: lineup tests; raw cases `best_5_man_lineups_unsupported`, `lineups_edwards_gobert_wave4`; source-backed coverage tests under `test_source_backed_lineup_dataset.py`. |
| Clutch data gaps / subjective clutch leaderboard | Route depends on phrasing, often `player_game_summary` or `season_leaders`. | Missing clutch coverage or subjective clutch phrasing returns unsupported/no-result; no broad points answer for subjective clutch leaderboard. | Parser/context tests; raw cases `tatum_clutch_stats`, `most_clutch_player_wave5`; context transport tests under `test_phase_g_context_transport.py`. |
| Period / schedule / role unsupported route combinations | Route-specific. | Supported routes execute when trusted coverage exists; unsupported routes keep explicit unfiltered-results notes or no-result depending on route/data. | `test_phase_g_period_execution.py`, `test_phase_h_schedule_context_execution.py`, `test_phase_g_role_execution.py`, `test_phase_g_context_transport.py`, `test_natural_query_parser.py` parser-note tests. |
| Subjective/award/trend concepts | Usually `route=None` or explicit unsupported boundary route if a concrete supported context is also detected. | Error/unrouted or no-result unsupported; no metric invented by parser. | Raw cases `best_defender_subjective`, `mvp_candidates_subjective`, `best_player_lately_ambiguous`, `cooled_off_last_10`, `cooled_off_lately_wave5`. |

## 6. Route collision groups

These groups are the main wrong-route risks. Extraction must preserve the
winner in each current collision unless a future preflight explicitly changes
the contract.

| Collision group | Current expected separation | Existing coverage |
| --- | --- | --- |
| On/off vs whole-game absence | `without Jokic on the floor` is on/off; `Lakers record without LeBron` is whole-game absence. | `test_on_off_query_does_not_set_without_player_absence_slot`; `TestWithoutPlayer`; raw without-player cases. |
| Lineup vs player/team summary or comparison | `lineup with Tatum and Brown` stays lineup; roster/duo subjective phrasing is not a supported lineup substitute. | Lineup parser tests; raw `best_duo_unsupported`, `lineups_edwards_gobert_wave4`. |
| Team rolling stretch vs player rolling stretch | Team-scoped rolling stretch is unsupported; player/named-player stretch remains supported. | Parser and execution rolling-stretch tests; raw team/player stretch cases. |
| Season high / top games vs season leaderboard | Single-game wording routes to `top_player_games`; ordinary leader wording routes to `season_leaders`. | `test_non_scoring_single_game_top_performance_routes_to_top_player_games`, `test_ordinary_assist_leaderboards_stay_season_leaders`, UI failure top-performance tests, raw top-performance cases. |
| Player occurrence count vs finder/count vs occurrence leaderboard | Distinct-player count, special-event count, and player finder/count have separate routes. | `test_parser_equivalence_groups.py`, `test_occurrence_queries.py`, `test_compound_occurrence_queries.py`, raw occurrence cases. |
| Playoff opponent-quality vs actual playoff games | `against playoff teams` is regular-season opponent quality; `playoff record/history` is playoff competition. | `test_team_record_against_playoff_teams_stays_regular_season`, `test_actual_playoff_record_phrases_still_use_playoffs`, UI failure opponent-quality tests. |
| Opponent conference vs conference finals vs geography/division | `against the East/West` can be supported team-record filtering; `conference finals` is playoff round; `east coast teams` and divisions are unsupported. | Opponent-conference parser/query-service tests; playoff round tests; raw `celtics_against_east_coast_teams_guard`; division coverage is documented but needs explicit extraction-era cases before nearby changes. |
| Player comparison vs player-as-opponent context | `LeBron James vs Kevin Durant comparison` is `player_compare`; `LeBron stats vs Kevin Durant` is opponent-player context. | `test_player_game_log_vs_player_stays_finder`, `test_full_name_lebron_durant_comparison_executes_as_comparison`, raw wave 5 comparison/finder cases. |
| Team record vs team comparison vs team matchup record | Two teams plus record intent routes to `team_matchup_record`; two teams without record intent routes to `team_compare`; single-team record stays `team_record`. | `test_natural_matchup_queries.py`, `test_parser_equivalence_groups.py`, raw matchup/comparison cases. |
| Unsupported role/rookie/team-bench boundaries vs supported player role filters | League/team role leaderboards are unsupported; player summary/finder role filters are supported when data coverage exists. | P2 boundary parser/execution tests; `test_phase_g_role_execution.py`; raw role boundary and player-role cases. |
| Single-team advanced scalar vs league-wide team advanced leaderboard | `Warriors net rating` is unsupported scalar summary; `best net rating teams` is supported leaderboard. | Parser/execution tests and raw cases listed above. |
| Context-only fallback vs subjective unsupported query | `in clutch time` currently broad-falls back with a note; `best player lately` remains unsupported. | UI failure fallback-note tests; raw subjective unsupported cases. |

## 7. Existing test coverage map

| Coverage area | Files / artifacts | What it currently protects |
| --- | --- | --- |
| Parser route and slot assertions | `tests/test_natural_query_parser.py` | Most route branches, slots, notes, unsupported filters, date/context parsing, on/off, lineup, top games, stretch, opponent quality, opponent conference, playoff boundaries. |
| Parser equivalence and word order | `tests/test_parser_equivalence_groups.py`, `tests/test_word_order_equivalence.py`, `tests/_parser_equivalence.py` | Same-intent phrasing variants across question, fragment, and shorthand forms. |
| Entity/stat aliases | `tests/test_entity_resolution.py`, `tests/test_stat_nickname_aliases.py`, `tests/test_expanded_stat_coverage.py`, `tests/test_stat_pattern_reconciliation.py` | Player/team/stat recognition that feeds parse state. |
| Route-family parser/execution tests | `tests/test_natural_matchup_queries.py`, `tests/test_natural_leaderboard_queries.py`, `tests/test_natural_team_leaderboard_queries.py`, `tests/test_natural_date_queries.py`, `tests/test_natural_date_compare_leaderboard_queries.py`, `tests/test_natural_streak_queries.py`, `tests/test_natural_team_streak_queries.py`, `tests/test_record_queries.py`, `tests/test_occurrence_queries.py`, `tests/test_compound_occurrence_queries.py` | Family-specific route and execution behavior. |
| Query-service result behavior | `tests/test_query_service.py`, `tests/test_structured_first_orchestration.py`, `tests/test_backend_apply_patterns.py`, `tests/test_leaderboard_filter_contracts.py` | Natural query orchestration, metadata, unsupported filters, no-result behavior, structured-first contract. |
| Regression coverage from Raw QA waves | `tests/test_ui_failure_coverage.py` | High-risk wrong-route fixes, unsupported boundaries, no-broad-fallback regressions, route/result metadata. |
| Context execution and transport | `tests/test_phase_e_*`, `tests/test_phase_g_*`, `tests/test_phase_h_schedule_context_execution.py` | Opponent quality, game context, role, period, clutch, schedule context propagation and data-backed/fallback behavior. |
| Source-backed weak-contract routes | `tests/test_source_backed_on_off_dataset.py`, `tests/test_source_backed_lineup_dataset.py`, `tests/test_source_backed_clutch_pbp_dataset.py` | Trusted coverage gates for on/off, lineup, and clutch sources. |
| Raw QA corpus and harness | `qa/raw_query_answer_corpus.yaml`, `tests/test_raw_query_answer_qa.py`, `qa/harness_slices/*.yaml` | End-to-end expected route/status/shape/metadata for curated product cases. |
| Smoke suites | `tests/test_query_smoke_stable.py`, `tests/test_query_smoke_phase.py`, `tests/test_cli_smoke.py` | CLI/API natural-query smoke behavior and raw output route metadata. |
| Reference docs | `docs/reference/query_catalog.md`, `docs/reference/query_guide.md` | Current shipped query surface and documented unsupported boundaries. |

## 8. Test gaps before code extraction

Do not fill these gaps in this docs-only wave. They are the minimum test
additions or confirmations a future code extraction should handle before it
moves behavior-sensitive code.

| Gap | Why it matters before extraction |
| --- | --- |
| Golden route-priority snapshot for `_finalize_route()` branches. | Current coverage is broad but scattered. A compact snapshot matrix should pin route, key kwargs, notes, and unsupported filters for each branch in the decision order. |
| Unsupported-boundary matrix tied to every boundary in section 5. | Raw corpus has many cases, but not every boundary is represented in a dedicated extraction slice. Unsupported behavior should assert route, result status/reason, empty sections, and metadata. |
| Collision-group fixtures for every group in section 6. | Existing tests cover many collisions, but extraction review needs one named fixture per adjacent family so branch movement is obvious. |
| Explicit no-broad-fallback assertions for all unsupported-filter branches. | Future refactors must prove unsupported filters do not silently return broad rows. |
| Division and historical opponent-conference coverage cases near the supported conference path. | Docs and policy name these boundaries, but extraction near opponent-conference parsing should add explicit route/corpus checks before code movement. |
| Post-processing note/caveat order snapshots. | Shared notes are appended after route selection; helper extraction could change note presence or order without changing route. |
| Import / `__all__` compatibility checks. | `natural_query.py` re-exports many helpers. Extraction should check callers before moving or removing exports. |
| Before/after parser snapshots for candidate queries. | A future extraction should compare `parse_query()` output for selected route/collision/boundary queries before and after code movement. |
| Raw QA slice coverage for all extraction risk families. | Existing slices cover product boundaries, playoff phrasing, team/date context, player entity/stat context, and defensive aliases, but extraction may need a dedicated natural-query extraction slice rather than relying only on full corpus. |

## 9. Required validation commands before any extraction

For docs-only changes like this wave:

```text
git diff --check
markdown lint if available
```

For any future code extraction touching `natural_query.py`, `_parse_helpers.py`,
route helper modules, or natural-query execution boundaries:

```text
make test-parser
make test-query
make raw-query-answer-qa
make test-preflight
```

Use `make test-preflight`, not `make test-impacted`, for
`natural_query.py` route or parse-state changes because it is a high-fan-in
module and testmon can degrade into a large serial run.

For route-family extraction, also run the directly relevant smoke or family
slices, for example:

```text
make test-smoke-all
make test-engine
make test-output
```

Only add broader commands when the future extraction actually touches those
contracts. Frontend commands are not part of a parser-only extraction unless a
future wave changes rendered data or copy, which should itself be a stop
condition for that extraction.

## 10. Stop conditions for future extraction waves

Stop and re-plan if an extraction attempt:

- changes the selected route for an existing query
- changes route kwargs, route metadata, notes, caveats, confidence, or
  alternates
- changes `result_status`, `result_reason`, sections, or row shape
- changes `metadata.unsupported_filters`
- makes an unsupported query return `ok` broad fallback rows
- weakens the no-broad-fallback rule
- removes or broadens an unsupported boundary
- adds support for a new phrase family
- changes QA corpus expectations to make a refactor pass
- requires production-code behavior outside the extraction target
- requires result-contract, API, or frontend changes
- changes data contracts or runtime data requirements
- changes `_finalize_route()` branch order
- implements bucket-first routing, dispatch-table routing, or a parser rewrite
- removes `__all__` compatibility exports without a caller audit
- makes the route order harder to explain than this document

## 11. Recommended first code extraction candidate

The first code extraction candidate remains pure stat-availability constants,
if a future wave chooses to proceed after this documentation pass.

Candidate:

- `_TEAM_SEASON_ADVANCED_STATS`
- local `_team_season_only`
- local `_player_season_only`
- local `_lower_is_better_stats`

Reason:

- These values are duplicated or local constant-like sets.
- They are less coupled to route branch order than boundary helpers, note
  construction, parse-state objects, or route-family extraction.
- The extraction can be mechanical if values, names, route branches, notes,
  and result reasons remain unchanged.

Required constraints:

- Do not change set contents.
- Do not change branch order.
- Do not change stat fallback notes.
- Do not change supported/unsupported behavior for single-team advanced
  summaries or league-wide team advanced leaderboards.
- Validate with the commands in section 9.

Do not extract unsupported-boundary helpers, note/caveat construction,
route-family helpers, parse-state objects, or bucket-first intent
classification as the first code wave. Those areas remain higher risk because
they directly affect wrong-route prevention and unsupported-boundary behavior.
