# Bare Player Vs Player Ambiguous Boundary V1 Return Package

Date: 2026-05-31

## Objective

Implement the V1 policy from
`docs/planning/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT.md`.

Bare player-vs-player queries such as:

```text
LeBron vs KD
```

now return a clean ambiguity boundary instead of silently executing a player
comparison table.

## Policy Implemented

V1 behavior:

- preserve `player_compare` as the closest recognized route
- return `result_status: no_result`
- return `result_reason: ambiguous_query`
- return empty `sections`
- preserve recognized players in metadata
- expose `metadata.ambiguous_intent: bare_player_vs_player`
- expose `metadata.clarification_options` for future typed clarification UI

Future ideal behavior remains a typed clarification UI. This wave does not
implement clarification UI, deep comparison tooling, head-to-head tooling, or
frontend business logic.

## Files Changed

- `src/nbatools/commands/_matchup_utils.py`
- `src/nbatools/commands/natural_query.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/query_service.py`
- `tests/test_natural_query_parser.py`
- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_ui_failure_coverage.py`
- `tests/test_true_head_to_head.py`
- `tests/test_backend_apply_patterns.py`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/public_query_acceptance.yaml`
- `qa/raw_query_answer_acceptance_families.yaml`
- `docs/planning/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT.md`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `docs/index.md`

## Before And After

| Query | Before | After |
| --- | --- | --- |
| `LeBron vs KD` | `player_compare` / `ok`; `summary: 2`, `comparison: 20`. | `player_compare` / `no_result` / `ambiguous_query`; no sections. |
| `LeBron James vs Kevin Durant` | `player_compare` / `ok`; `summary: 2`, `comparison: 20`. | `player_compare` / `no_result` / `ambiguous_query`; no sections. |
| `Jokic vs Embiid` | `player_compare` / `ok`; `summary: 2`, `comparison: 20`. | `player_compare` / `no_result` / `ambiguous_query`; no sections. |

Exact V1 contract:

```text
route: player_compare
result_status: no_result
result_reason: ambiguous_query
result.sections: {}
result.metadata.ambiguous_intent: bare_player_vs_player
result.metadata.players_context: [player A, player B]
result.metadata.clarification_options: present
```

## Behavior Preserved

Disambiguated comparison still works:

| Query | Route | Status | Proof |
| --- | --- | --- | --- |
| `LeBron James vs Kevin Durant comparison` | `player_compare` | `ok` | `summary: 2`, comparison rows present. |
| `Compare LeBron James and Kevin Durant` | `player_compare` | `ok` | `summary: 2`, comparison rows present. |
| `How do LeBron James and Kevin Durant compare this season?` | `player_compare` | `ok` | preserves both players and comparison rows. |
| `Jokic vs Embiid recent form` | `player_compare` | `ok` | recent-form comparison remains execution-backed. |

Player-opponent finder still works:

| Query | Route | Status | Proof |
| --- | --- | --- | --- |
| `LeBron stats vs KD` | `player_game_finder` | `ok` | returns `finder` rows; no ambiguity marker. |

Team behavior was intentionally untouched:

| Query | Route | Status | Proof |
| --- | --- | --- | --- |
| `Celtics vs Bucks` | `team_compare` | `ok` | team comparison still executes. |
| `Lakers record vs Celtics` | `team_record` | `ok` | opponent filter `BOS` still executes. |
| `Lakers vs Celtics head to head record` | `team_matchup_record` | `ok` | head-to-head matchup record still executes. |
| `Lakers Celtics playoff matchup history` | `playoff_matchup_history` | `ok` | playoff matchup-history sections still execute. |

## Implementation Summary

Parser/routing:

- Added `detect_bare_player_vs_player_query()` in `_matchup_utils.py`.
- The detector only matches exact `PLAYER vs PLAYER` / `PLAYER versus PLAYER`
  queries where both sides are exact player references.
- Qualified forms such as `Jokic vs Embiid recent form`,
  `LeBron James vs Kevin Durant comparison`, `Compare A and B`, question-form
  comparisons, `stats vs`, `game log vs`, `head-to-head`, and team-vs-team
  routes remain outside the boundary.
- `natural_query.py` marks matching parsed queries with
  `bare_player_vs_player` and adds `ambiguous_intent` plus
  `clarification_options` to `route_kwargs`.
- `_natural_query_execution.py` intercepts `ambiguous_intent` before command
  execution and returns `NoResult(reason="ambiguous_query")`.
- `query_service.py` treats `ambiguous_query` as an expected no-result reason
  and exposes `ambiguous_intent` / `clarification_options` in metadata.

No frontend rendering changes were needed.

## Corpus And Tests Added

Raw QA corpus:

- `bare_lebron_kd_ambiguous_boundary_v1`
- `bare_lebron_durant_ambiguous_boundary_v1`
- `bare_jokic_embiid_ambiguous_boundary_v1`

All three are in `public_query_acceptance` as `comparisons` /
`ambiguous_vs_clarification_candidate` / `nearby_unsupported` boundary cases.
They assert:

- expected route `player_compare`
- expected status `no_result`
- expected reason `ambiguous_query`
- expected shape `no_result`
- empty sections
- `metadata.ambiguous_intent == bare_player_vs_player`
- recognized players in `metadata.players_context`
- `clarification_options.0.intent == player_stat_comparison`

Pytest coverage:

- parser boundary tests for the three bare forms
- route-priority snapshots for the three bare forms
- query-level no-broad-fallback tests proving empty sections and no comparison
  rows
- regression tests proving explicit comparison, question-form comparison,
  player-opponent finder, team comparison, team matchup record, and playoff
  matchup history behavior remain intact
- reason/status tests for `ambiguous_query`

## Raw QA Product Review State

Review state: `machine_only`.

Generated public acceptance product-review artifact:

```text
outputs/raw_query_answer_qa/20260531T094037Z/product_review.md
```

The run passed machine expectations for `113` cases, but representative outputs
were not human-reviewed in this wave and no family was marked public accepted.

## Validation Results

Focused validation:

- `.venv/bin/pytest tests/test_natural_query_parser.py::test_bare_player_vs_player_routes_to_ambiguous_boundary tests/test_natural_query_parser.py::test_full_name_player_comparison_route tests/test_natural_query_parser.py::test_compare_full_names_and_route tests/test_natural_query_parser.py::test_question_form_player_comparison_route tests/test_natural_query_parser.py::test_alias_bare_player_vs_player_routes_to_ambiguous_boundary tests/test_natural_query_route_priority_snapshots.py::test_route_priority_collision_snapshot tests/test_ui_failure_coverage.py::TestBarePlayerVsPlayerAmbiguousBoundary -n0 -q`: `44 passed`
- `.venv/bin/pytest tests/test_backend_apply_patterns.py::TestAmbiguousQueryReason tests/test_true_head_to_head.py::test_parse_compare_queries_set_head_to_head_flag -n0 -q`: `4 passed`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case bare_lebron_kd_ambiguous_boundary_v1 --case bare_lebron_durant_ambiguous_boundary_v1 --case bare_jokic_embiid_ambiguous_boundary_v1 --fail-on-expectation-failure`: `3` cases, expectations `pass`; output `outputs/raw_query_answer_qa/20260531T094001Z`

Required validation:

- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure`: `113` cases, expectations `pass`; output `outputs/raw_query_answer_qa/20260531T094037Z`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure`: `49` cases, expectations `pass`; output `outputs/raw_query_answer_qa/20260531T094225Z`
- `make PYTEST=.venv/bin/pytest test-parser`: `800 passed`
- `make PYTEST=.venv/bin/pytest test-query`: `812 passed in 368.86s`
- `git diff --check`: passed
- `git diff --check --no-index /dev/null return_packages/raw-product/BARE_PLAYER_VS_PLAYER_AMBIGUOUS_BOUNDARY_V1_RETURN_PACKAGE.md`: no whitespace warnings; exit code `1` is expected for a `/dev/null` comparison with file content

Markdown lint:

- `markdownlint` was not installed.
- `markdownlint-cli2` was not installed.
- `mdl` was not installed.
- `mdformat` was not installed.
- No repo-local markdown lint target was found in `Makefile`, `pyproject.toml`,
  `frontend/package.json`, or `.github`.

## Next Recommended Action

Keep the V1 ambiguity boundary in place until a typed clarification API payload
and UI rendering contract are approved. A future clarification wave should
replace the no-result boundary with selectable intent options, not with a silent
default comparison table.
