# Natural Query Extraction Preflight

## 1. Executive summary

This is a preflight only. It does not change parser, routing, backend,
frontend, result-contract, test, or QA-corpus behavior.

Current finding: `src/nbatools/commands/natural_query.py` is materially cleaner
than the older architecture audit snapshot, but it remains the main
parser/routing maintainability risk. The file is now 2,404 lines, with many
helpers already extracted into `_constants.py`, `_date_utils.py`,
`_parse_helpers.py`, `_leaderboard_utils.py`, `_matchup_utils.py`,
`_occurrence_route_utils.py`, `_playoff_record_route_utils.py`, and
`_natural_query_execution.py`.

The remaining risk is not raw line count alone. The risk is that
`_build_parse_state()` and `_finalize_route()` still coordinate many slots,
route-priority rules, unsupported boundaries, route kwargs, and parser notes in
one high-fan-in file. Future feature work can still create wrong-route behavior
if extraction starts with a broad rewrite or if route priority changes without
strong collision coverage.

Recommendation: the first executable wave should be docs-only: preserve the
current route decision map and unsupported-boundary inventory before any code
extraction. If a code wave follows, keep it to pure constants or a narrow helper
extraction with explicit before/after parser snapshots and raw QA boundary
coverage. Do not start with bucket-first routing, a dispatch-table rewrite, or
route-family extraction.

Launch blocker found: no. This is a highest-priority deferred maintainability
item before major new query-family expansion, not a current release blocker.

## 2. Inputs inspected

Required inputs inspected:

- `docs/planning/raw-product/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_REVIEW_NOTES.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md`
- `docs/audits/architecture_hygiene_audit.md`
- `src/nbatools/commands/natural_query.py`
- `src/nbatools/query_service.py`
- parser/query tests under `tests/`
- `qa/raw_query_answer_corpus.yaml`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

Additional context inspected:

- `docs/index.md`
- `docs/planning/natural_query_cleanup_plan.md`
- `src/nbatools/commands/_constants.py`
- `src/nbatools/commands/_date_utils.py`
- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/_leaderboard_utils.py`
- `src/nbatools/commands/_matchup_utils.py`
- `src/nbatools/commands/entity_resolution.py`
- `qa/harness_slices/*.yaml`
- `Makefile`
- representative prior raw-product preflight return packages

## 3. Current `natural_query.py` structure map

Current file size:

- `natural_query.py`: 2,404 lines
- `query_service.py`: 1,484 lines
- `qa/raw_query_answer_corpus.yaml`: 5,143 lines

Major `natural_query.py` sections:

| Lines | Section | Current responsibility | Extraction status |
|---|---|---|---|
| 1-247 | Imports from helper modules | Pulls normalization, date, defaults, leaderboard, matchup, occurrence, playoff, parser helper, execution, and result metadata helpers into this module. | Many former helpers are already externalized. Import surface is large. |
| 249-281 | Local unsupported and stat constants | `_UNSUPPORTED_BOUNDARY_PHRASES`, `_TEAM_SEASON_ADVANCED_STATS`. | Still local. |
| 284-424 | Small boundary / intent helpers | Unsupported-boundary note, single-team advanced-stat boundary, multi-player availability boundary, ambiguous fragments, stretch mode, date top-scorer intent, Washington/WAS guards, placeholder-template note. | Mixed: some are stable local helpers, some could become a boundary helper module later. |
| 427-504 | `__all__` compatibility export list | Re-exports many helpers imported from other modules. | Should not be disturbed casually; tests or downstream imports may rely on it. |
| 507-918 | `_build_parse_state(query)` | Normalizes text; extracts season/range/date, stat, entities, contexts, thresholds, route-intent flags, unsupported-boundary slots, staleness-aware date anchors, and returns the parse-state dict. | Main parse assembly concentration. |
| 921-968 | Route condition attachment helpers | Builds canonical condition lists and mutates route kwargs / parsed state for compound conditions. | Small and isolated, but stateful. |
| 971-2300 | `_finalize_route(parsed)` | Applies route-priority chain, builds route kwargs, attaches unsupported filters, appends notes, normalizes intent/confidence/alternates. | Primary routing-risk concentration. |
| 2303-2304 | `parse_query(query)` | Thin wrapper over `_build_parse_state()` then `_finalize_route()`. | Good current public parser API. |
| 2307-2383 | `_merge_inherited_context(base, clause)` | Used for boolean/OR context inheritance through execution helpers. | Behavior-sensitive helper, not first-wave extraction. |
| 2386-2404 | `run(...)` | Thin CLI-facing wrapper that calls `execute_natural_query()` and renders/export results. | Structured-first path is canonical. |

## 4. Route decision flow

The route decision still lives in a procedural priority chain inside
`_finalize_route()`. Current high-level order:

1. Propagate occurrence event stat/minimum slots.
2. Short-circuit unresolved entity ambiguity.
3. Short-circuit ambiguous fragment templates and placeholder templates.
4. Route on/off and lineup queries.
5. Route rolling-stretch queries, including team rolling-stretch unsupported
   boundary handling.
6. Route player or league season-high / single-game-best queries.
7. Route distinct player count queries.
8. Route team streak queries.
9. Delegate playoff / record / decade routing to
   `try_playoff_record_route()`.
10. Route player and team splits.
11. Route player comparisons.
12. Route team matchup records or team comparisons.
13. Route player streaks.
14. Route top player games and top team games.
15. Delegate compound occurrence and record-leaderboard routing.
16. Route explicit unsupported leaderboard boundaries:
   personal fouls, rookies, league role leaderboards, and team bench scoring.
17. Route opponent-conference geography and opponent-conference team records.
18. Route single-team advanced-stat scalar unsupported boundary.
19. Route explicit-date top-scorer questions.
20. Route context-only boundary fragments to a broad fallback with a note.
21. Route metric-only player/team leaderboard defaults.
22. Delegate occurrence count routing.
23. Route explicit finder/count queries for players or teams.
24. Route multi-player availability unsupported boundary.
25. Route player summaries.
26. Route single-team records.
27. Route team summaries.
28. Fall back to player finder, then team finder.
29. Raise unrouted `ValueError` if no route is selected.

After the route is selected, the function appends shared context kwargs,
applies compound route conditions, derives intent, adds parser notes/caveats,
adds confidence and alternates, and returns the final parse dict.

Important implication: route order is behavior. Any extraction that moves a
branch, changes a helper's truthiness, or changes when notes are appended can
change product behavior even if result contracts are untouched.

## 5. Current constants, aliases, and helpers

Already extracted or centralized:

- Stat aliases: `STAT_ALIASES` and `STAT_PATTERN` in
  `src/nbatools/commands/_constants.py`.
- Leaderboard-only and team leaderboard stat aliases:
  `src/nbatools/commands/_leaderboard_utils.py`.
- Date parsing helpers, including All-Star break and fuzzy windows:
  `src/nbatools/commands/_date_utils.py`.
- Player/team aliases and resolution:
  `src/nbatools/commands/entity_resolution.py`.
- Matchup, opponent, and without-player extraction:
  `src/nbatools/commands/_matchup_utils.py`.
- Streak, season, context, threshold, role, lineup, and notes helpers:
  `src/nbatools/commands/_parse_helpers.py`.
- Occurrence and playoff routing helpers:
  `_occurrence_route_utils.py` and `_playoff_record_route_utils.py`.
- Natural-query execution helpers:
  `_natural_query_execution.py`.

Still local to `natural_query.py`:

- `_UNSUPPORTED_BOUNDARY_PHRASES`
- `_TEAM_SEASON_ADVANCED_STATS`
- `_AMBIGUOUS_FRAGMENT_PATTERNS`
- `_unsupported_boundary_note()`
- `_single_team_advanced_stat_summary_boundary()`
- `_multi_player_availability_boundary()`
- `_stretch_display_mode()`
- `_specific_date_top_scorer_intent()`
- `_team_how_did_do_record_intent()`
- `_explicit_washington_reference()`
- `_was_team_alias_is_auxiliary()`
- `_ambiguous_fragment_note()`
- `_placeholder_template_note()`
- local stat availability sets inside `_finalize_route()`:
  `_lower_is_better_stats`, `_team_season_only`, and `_player_season_only`

## 6. Unsupported-boundary handling

Unsupported boundaries are intentionally part of the product contract. Current
boundary handling is split across parser helpers, local `natural_query.py`
helpers, route kwargs, execution helpers, and raw QA assertions.

Representative boundaries observed:

- broad phrase note only: `_UNSUPPORTED_BOUNDARY_PHRASES`
- team rolling-stretch leaderboard: `team_rolling_stretch`
- personal-foul leaderboard: `personal_foul_leaderboard`
- rookie leaderboard: `rookie_leaderboard`
- league-wide starter/bench leaderboard: `role_leaderboard`
- team bench scoring: `team_bench_scoring`
- opponent-conference geography phrases: `opponent_conference`
- single-team advanced-stat scalar summaries:
  `single_team_advanced_stat_summary`
- multi-player availability team record filters:
  `multi_player_availability`
- single-team playoff round records:
  `single_team_playoff_round_record`
- on/off and lineup coverage gaps, handled by route execution when trusted data
  is unavailable

The safest near-term improvement is to document this boundary map and tie each
boundary to tests and raw QA case IDs. Moving the definitions into a code helper
module is possible later, but it is not the safest first wave because the route,
notes, and result reasons are coupled.

## 7. Business logic embedded in parser/routing

The following logic is currently embedded in parse assembly or route selection:

- default season and season-span resolution
- staleness-aware date-window anchoring via `compute_current_through()`
- fallback promotion from leaderboard wording to stat slots
- route-specific default limits
- lower-is-better leaderboard sort semantics
- player/team advanced-stat availability fallbacks
- route-specific unsupported-filter selection
- broad fallback notes for some unsupported phrase families
- parser note/caveat construction
- condition propagation and duplicate post-filter clearing

Do not extract these first. They are behavior-sensitive and should be handled
only after the route decision map and boundary tests are pinned.

## 8. Extraction candidate ranking

| Rank | Candidate | Value | Risk | Coverage needed | Behavior unchanged? | Disposition |
|---|---|---|---|---|---|---|
| 1 | Route decision map and unsupported-boundary inventory | High | Very low | `git diff --check`; markdown lint if available | Yes | First executable wave, docs-only |
| 2 | Test matrix for extraction guardrails | High | Low | Identify existing parser/query/raw QA coverage and missing collision cases | Yes | First wave companion, docs-only |
| 3 | Pure local stat constants: `_TEAM_SEASON_ADVANCED_STATS`, duplicated `_team_season_only`, `_player_season_only`, `_lower_is_better_stats` | Medium | Low-medium | `make test-parser`, `make test-query`, product-boundary raw QA slices, `make test-preflight` because `natural_query.py` is high fan-in | Yes, if moved without value changes | Earliest possible code wave after docs map |
| 4 | Date helper extraction | Low now | Low | Date parser tests, date leaderboard tests, raw date cases | Mostly yes | Already largely done in `_date_utils.py`; no first-wave value |
| 5 | Player/team alias cleanup | Low-medium now | Medium | Entity resolution tests, parser equivalence groups, comparison/opponent tests | Maybe | Mostly centralized already; do not touch first |
| 6 | Unsupported-boundary helper module | Medium-high | Medium | Parser boundary tests, query-service no-result tests, raw QA product-boundary slice, no-broad-fallback checks | Possible, but string/order-sensitive | Later helper extraction |
| 7 | Note/caveat construction helper consolidation | Medium | Medium | Parser note tests, query-service metadata tests, frontend-copy-sensitive checks, raw QA no-result cases | Possible, but exact strings matter | Later helper extraction |
| 8 | Route-family helper extraction from `_finalize_route()` | High | High | Full parser/query slices, raw QA corpus, collision phrase groups, smoke suites | Possible, but route order is fragile | Later architecture work |
| 9 | Parse-state object/dataclass or typed slots | Medium-high | High | Broad parser and query tests plus raw QA | Risky | Later architecture work only |
| 10 | Bucket-first intent classification | High long-term | Very high | Separate preflight, golden route snapshots, broad collision corpus | Not as first implementation | Deferred preflight only |

## 9. Dangerous work and non-goals

Do not do these in the first extraction wave:

- one-pass parser rewrite
- dispatch-table rewrite of `_finalize_route()`
- bucket-first routing implementation
- new query support
- broad phrase expansion
- route-priority changes
- weakening unsupported boundaries
- broad fallback answers for low-confidence or unsupported queries
- changes to result contracts or API/frontend rendering
- QA corpus expectation changes to make a refactor pass
- import cleanup that removes compatibility exports without checking callers

## 10. Test and validation strategy

Existing coverage to rely on before any code extraction:

- Parser route tests: `tests/test_natural_query_parser.py`
- Parser equivalence and word-order tests:
  `tests/test_parser_equivalence_groups.py`, `tests/test_word_order_equivalence.py`
- Entity/stat alias tests: `tests/test_entity_resolution.py`,
  `tests/test_stat_nickname_aliases.py`,
  `tests/test_expanded_stat_coverage.py`
- Date tests: `tests/test_natural_date_queries.py`,
  `tests/test_natural_date_compare_leaderboard_queries.py`,
  `tests/test_fuzzy_weeks_date_range.py`
- Query orchestration and service tests:
  `tests/test_query_service.py`, `tests/test_structured_first_orchestration.py`,
  `tests/test_backend_apply_patterns.py`
- Route-family tests:
  `tests/test_record_queries.py`, `tests/test_occurrence_queries.py`,
  `tests/test_compound_occurrence_queries.py`,
  `tests/test_natural_streak_queries.py`,
  `tests/test_natural_team_streak_queries.py`,
  `tests/test_natural_leaderboard_queries.py`,
  `tests/test_natural_team_leaderboard_queries.py`,
  `tests/test_natural_matchup_queries.py`
- Context filter tests:
  `tests/test_phase_e_*`, `tests/test_phase_g_*`,
  `tests/test_phase_h_schedule_context_execution.py`
- Smoke and corpus tests:
  `tests/test_query_smoke_stable.py`, `tests/test_query_smoke_phase.py`,
  `qa/raw_query_answer_corpus.yaml`

Raw QA slices that matter most for extraction:

- `qa/harness_slices/product_boundaries.yaml`
- `qa/harness_slices/playoff_phrasing.yaml`
- `qa/harness_slices/team_date_context.yaml`
- `qa/harness_slices/player_entity_stat_context.yaml`
- `qa/harness_slices/defensive_aliases.yaml`

New or expanded tests needed before code extraction:

- route-priority snapshot cases for every branch group in the decision map
- unsupported-boundary regression cases that assert route, result reason, and
  `metadata.unsupported_filters`
- collision phrase groups:
  - opponent conference vs conference finals vs east/west geography
  - team record vs team comparison vs team matchup
  - player comparison vs player-vs-opponent summary/finder
  - leaderboard vs top single-game performances
  - subjective/trend phrases vs explicit stat metrics
  - on/off presence vs whole-game absence
  - team rolling stretch boundary vs player rolling stretch support
  - single-team advanced scalar boundary vs league-wide team advanced
    leaderboards
- no-broad-fallback tests for unsupported filters with empty sections and
  `filter_not_supported`

Recommended validation for any code extraction touching `natural_query.py`:

```text
make test-parser
make test-query
make raw-query-answer-qa
make test-preflight
```

Use `make test-preflight` rather than `make test-impacted` for
`natural_query.py` route or parse-state changes because it is a high-fan-in
module.

Docs-only validation:

```text
git diff --check
markdown lint if available
```

## 11. Recommended first extraction wave

Recommended Wave 1: docs-only decision map and extraction guardrail matrix.

Scope:

- Keep production code unchanged.
- Keep tests unchanged.
- Keep QA corpus expectations unchanged.
- Add or expand a durable route decision map that records the current
  `_finalize_route()` branch order in product language.
- Add an unsupported-boundary inventory that maps boundary names to the parser
  branch, execution behavior, existing tests, and raw QA cases.
- Add a small extraction-readiness table showing which code candidates require
  which tests before they can move.

Acceptance criteria:

- A future agent can identify where a new feature would collide before editing
  `natural_query.py`.
- The decision map names the current route priority order without proposing a
  new routing architecture.
- Unsupported boundaries are explicitly treated as behavior to preserve.
- No behavior, test, corpus, frontend, backend, or result-contract changes.

Why this should come first:

- It gives immediate maintainability value with almost no regression risk.
- It reduces the chance that the first code extraction accidentally changes
  route order.
- It creates the checklist needed to review later helper extraction.

Optional Wave 2 after Wave 1:

- Extract only local stat-availability constants if the decision map and tests
  make the move mechanical:
  `_TEAM_SEASON_ADVANCED_STATS`, `_team_season_only`,
  `_player_season_only`, and `_lower_is_better_stats`.
- Do not change values, route branches, notes, or result reasons.
- Validate with parser/query slices, raw QA, and preflight.

## 12. Stop conditions

Stop and re-plan if any extraction attempt:

- changes the route selected for an existing QA case
- changes `result_status`, `result_reason`, or `unsupported_filters`
- changes parser notes that frontend-copy or QA depends on
- makes an unsupported query return an `ok` broad fallback
- turns a broad fallback note into a supported claim
- requires adding support for a new phrase family
- requires a new data or result contract
- requires frontend changes
- requires changing raw QA expectations just to preserve a refactor
- makes route ordering harder to explain than it is today

## 13. Blocker verdict

No launch blocker was found. The current release posture remains launch-ready
with notes as recorded by the raw-product planning docs.

The extraction work is still important before major new query-family expansion.
The safe path is documentation, boundary inventory, and then narrow
behavior-preserving helper extraction with strong parser/query/raw QA coverage.
