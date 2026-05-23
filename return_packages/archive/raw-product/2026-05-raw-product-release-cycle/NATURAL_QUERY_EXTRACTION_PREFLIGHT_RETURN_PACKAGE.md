# Natural Query Extraction Preflight Return Package

## 1. Executive summary

- Preflight completed as documentation only.
- No production code, tests, frontend, backend, result contracts, or QA corpus
  expectations were changed.
- `natural_query.py` is currently 2,404 lines. It is smaller and more extracted
  than the older architecture audit snapshot, but `_build_parse_state()` and
  `_finalize_route()` still concentrate the main parser/routing risk.
- Many early extraction candidates from older docs are already done: stat
  aliases, date helpers, entity aliases, occurrence routing, playoff routing,
  and execution helpers have dedicated modules.
- The safest first executable wave is docs-only: a durable route decision map,
  unsupported-boundary inventory, and extraction test matrix.
- No launch blocker was found.

## 2. Files inspected

Required files:

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

Additional context:

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

## 3. Natural query structure map

Current `natural_query.py` map:

- imports and helper re-exports: lines 1-504
- `_build_parse_state()`: lines 507-918
- route condition helpers: lines 921-968
- `_finalize_route()`: lines 971-2300
- `parse_query()`: lines 2303-2304
- `_merge_inherited_context()`: lines 2307-2383
- `run()`: lines 2386-2404

Current route decision order inside `_finalize_route()`:

1. ambiguity and template short-circuits
2. on/off and lineup
3. rolling stretch, including team rolling-stretch boundary
4. season-high and top single-game routes
5. distinct player count
6. team streak
7. playoff/record/decade helper routing
8. splits
9. player compare
10. team matchup record or team compare
11. player streak
12. top player/team games
13. compound occurrence and record-leaderboard helpers
14. unsupported leaderboard and team-bench boundaries
15. opponent-conference boundaries
16. single-team advanced-stat scalar boundary
17. date top-scorer route
18. metric-only leaderboard defaults
19. occurrence count
20. explicit finder/count routes
21. multi-player availability boundary
22. player summary
23. team record
24. team summary
25. player finder
26. team finder
27. unrouted error

## 4. Extraction candidate ranking

| Rank | Candidate | Recommendation |
|---|---|---|
| 1 | Route decision map and unsupported-boundary inventory | Do first, docs-only. |
| 2 | Extraction test matrix | Do with the decision map, docs-only. |
| 3 | Pure local stat constants | Earliest possible code extraction after docs map and tests. |
| 4 | Date helpers | Mostly already extracted; no first-wave value. |
| 5 | Player/team aliases | Mostly centralized; do not touch first. |
| 6 | Unsupported-boundary helper module | Useful later, but route/notes/result reasons are coupled. |
| 7 | Note/caveat helper consolidation | Later; exact strings and metadata are behavior-sensitive. |
| 8 | Route-family helper extraction | Later architecture work; high route-priority risk. |
| 9 | Parse-state typed object/dataclass | Later architecture work only. |
| 10 | Bucket-first intent classification | Separate future preflight; not an implementation wave. |

## 5. Recommended first extraction wave

First wave should be docs-only:

- preserve the current route decision map
- inventory unsupported boundaries and raw QA coverage
- list collision groups and required tests before code extraction
- do not change production code, tests, corpus, backend, frontend, or result
  contracts

If a code wave follows, the smallest plausible scope is pure constants:

- `_TEAM_SEASON_ADVANCED_STATS`
- local `_team_season_only`
- local `_player_season_only`
- local `_lower_is_better_stats`

That code wave should not change values, branch order, route kwargs, notes, or
result reasons.

## 6. Tests and validation needed

Before code extraction touching `natural_query.py`:

```text
make test-parser
make test-query
make raw-query-answer-qa
make test-preflight
```

Additional test gaps to close before route-family extraction:

- route-priority snapshot cases
- unsupported-boundary regression cases
- no-broad-fallback cases
- collision phrase groups for opponent conference, playoff rounds, team
  comparison/record/matchup, player comparison/opponent-player, top games vs
  leaderboards, on/off vs absence, team stretch vs player stretch, and
  single-team advanced stat vs league team advanced leaderboard

## 7. Stop conditions

Stop and re-plan if extraction:

- changes existing route selection
- changes status, reason, notes, caveats, or unsupported-filter metadata
- adds new query support
- broadens unsupported queries into `ok` fallback answers
- weakens no-broad-fallback behavior
- needs result-contract or frontend changes
- needs QA corpus expectation changes to make a refactor pass
- implements bucket-first routing or dispatch-table routing

## 8. Files changed

Created:

- `docs/planning/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`
- `return_packages/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT_RETURN_PACKAGE.md`

Updated:

- `docs/index.md`

No code, test, frontend, backend, or QA corpus files were changed.

## 9. Validation

Validation performed:

```text
git diff --check
```

Result: passed.

Additional whitespace checks for the two new untracked markdown files were run
with `git diff --no-index --check /dev/null <file>`; both produced no whitespace
warnings.

Markdown lint availability check found no `markdownlint`, `mdl`, or `mdformat`
binary in the shell path, so no markdown lint command was available to run.
