# Natural Query Constants Extraction Wave 1 Return Package

## What changed

- Moved pure natural-query stat availability sets from
  `src/nbatools/commands/natural_query.py` into
  `src/nbatools/commands/_constants.py`.
- Updated `natural_query.py` call sites to import and reference the moved
  constants.
- Added a narrow constants availability/value test in
  `tests/test_advanced_metric_queries.py`.
- Updated `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
  to mark this constants extraction wave complete and keep next-step guidance
  conservative.

## Exact constants moved

| Previous location/name | New location/name | Preserved value |
| --- | --- | --- |
| `natural_query.py::_TEAM_SEASON_ADVANCED_STATS` | `_constants.py::TEAM_SEASON_ADVANCED_STATS` | `{"off_rating", "def_rating", "net_rating", "pace"}` |
| local `_team_season_only` in `_finalize_route()` | `_constants.py::TEAM_SEASON_ONLY_STATS` | `{"off_rating", "def_rating", "net_rating", "pace"}` |
| local `_player_season_only` in `_finalize_route()` | `_constants.py::PLAYER_SEASON_ONLY_STATS` | `{"off_rating", "def_rating", "net_rating"}` |
| local `_lower_is_better_stats` in `_finalize_route()` | `_constants.py::LOWER_IS_BETTER_STATS` | `{"def_rating", "opponent_pts_per_game", "tov", "tov_pct"}` |

## Files changed

- `src/nbatools/commands/_constants.py`
- `src/nbatools/commands/natural_query.py`
- `tests/test_advanced_metric_queries.py`
- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `return_packages/raw-product/NATURAL_QUERY_CONSTANTS_EXTRACTION_WAVE_1_RETURN_PACKAGE.md`

## Preservation proof

- Set contents were copied exactly, including duplicate team-season-only values.
- Only membership checks changed from local/private set names to imported
  constants.
- No `_finalize_route()` branch was moved.
- No route order, route kwargs, status, reason, notes, caveats,
  `unsupported_filters`, metadata, result contracts, frontend code, or QA
  corpus expectations were changed.
- Raw QA passed all expectation cases after the change.

## Validation results

- `make test-parser`
  - Initial direct run failed because `pytest` was not on PATH:
    `make: pytest: No such file or directory`.
  - Closest equivalent target run:
    `make PYTEST=.venv/bin/pytest test-parser`
  - Result: `751 passed in 246.44s (0:04:06)`.
- `make PYTEST=.venv/bin/pytest test-query`
  - Result: `752 passed in 510.39s (0:08:30)`.
- `make raw-query-answer-qa`
  - Result: `246` cases, `246` expectation passes, failed case IDs: `none`.
  - Report: `outputs/raw_query_answer_qa/20260521T063546Z`.
- `make PYTEST=.venv/bin/pytest test-preflight`
  - Result: `2929 passed, 1 xpassed in 552.03s (0:09:12)`.
- `git diff --check`
  - Result: passed.

## Skipped validation

No requested validation was skipped. The parser/query/preflight Make targets
were run with `PYTEST=.venv/bin/pytest` because the shell environment did not
have `pytest` on PATH.

## Release impact

No user-facing release impact expected. This is an internal constants-only
extraction with no behavior, contract, API, CLI, frontend, or corpus
expectation changes.

## Next recommended extraction candidate

Do not proceed directly to unsupported-boundary helpers, note/caveat
construction, route-family helpers, parse-state objects, bucket-first routing,
or dispatch-table routing. The next useful step is coverage hardening from the
decision map: route-priority snapshots and unsupported-boundary snapshots.

If another code extraction is needed before that coverage exists, keep it to a
fresh preflight-approved pure constants/helper move with no route-order, note,
result, or corpus-expectation changes.
