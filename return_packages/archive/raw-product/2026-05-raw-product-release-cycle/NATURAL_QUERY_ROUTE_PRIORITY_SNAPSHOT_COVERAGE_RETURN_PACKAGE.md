# Natural Query Route Priority Snapshot Coverage Return Package

## What changed

- Added parser-level route-priority snapshots for the high-risk natural-query
  collision groups named in the preflight.
- Added query-level unsupported-boundary snapshots that assert
  no-broad-fallback behavior with empty result sections.
- Added a raw QA harness slice that composes existing corpus cases for
  extraction-era route-priority checks.
- Did not change production code, parser behavior, backend behavior, frontend
  behavior, result contracts, or existing raw QA corpus expectations.

## Files changed

Created:

- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_natural_query_unsupported_boundary_snapshots.py`
- `qa/harness_slices/natural_query_route_priority.yaml`
- `return_packages/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_COVERAGE_RETURN_PACKAGE.md`

No production source files were changed.

## Coverage added

Parser route-priority snapshots now cover:

- opponent conference vs Conference Finals vs geography phrases
- team record vs team comparison vs team matchup record
- player comparison vs player-vs-opponent finder behavior
- top single-game performances vs ordinary leaderboards
- on/off vs whole-game absence
- team rolling stretch boundary vs player rolling stretch support
- single-team advanced-stat scalar boundary vs league team advanced leaderboard

Query unsupported/no-broad-fallback snapshots now cover:

- `team_rolling_stretch`
- `rookie_leaderboard`
- `role_leaderboard`
- `team_bench_scoring`
- `personal_foul_leaderboard`
- `opponent_conference`
- `conference_coverage`
- `single_team_advanced_stat_summary`
- `single_team_playoff_round_record`
- `multi_player_availability`
- on/off unsupported data
- lineup unsupported data
- clutch unsupported data
- subjective/unrouted concepts

The raw QA slice `natural_query_route_priority` uses existing corpus IDs only
and includes 28 route-priority, collision, unsupported-boundary, and
no-broad-fallback cases.

## Known Atlantic Division cleanup candidate

Per the preflight, `Celtics record vs Atlantic Division` was not included as a
passing expected snapshot. Current behavior broad-falls back to an ordinary
`team_record` `ok` response with no unsupported filter, while the policy docs
describe division phrasing as a guarded opponent-conference-adjacent boundary.

That remains a separate product-boundary cleanup candidate. It should be
handled by a dedicated preflight/behavior-change wave, not by this snapshot
coverage wave.

## Validation results

- `.venv/bin/pytest tests/test_natural_query_route_priority_snapshots.py tests/test_natural_query_unsupported_boundary_snapshots.py -n0`
  - Result: `35 passed in 48.35s`.
- `make PYTEST=.venv/bin/pytest test-parser`
  - Result: `769 passed in 404.58s (0:06:44)`.
- `make PYTEST=.venv/bin/pytest test-query`
  - Result: `769 passed in 485.69s (0:08:05)`.
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --fail-on-expectation-failure`
  - Report: `outputs/raw_query_answer_qa/20260521T073529Z`
  - Cases: `28`
  - Result statuses: `{'error': 2, 'no_result': 14, 'ok': 12}`
  - Expectation cases: `{'pass': 28}`
  - Failed case IDs: `none`
- `git diff --check`
  - Result: passed.
- `git diff --no-index --check /dev/null <new file>` for each new untracked
  file
  - Result: no whitespace warnings. The commands exit nonzero because the files
    differ from `/dev/null`.

## Skipped validation

No requested validation was skipped.

## Release impact

No user-facing release impact expected. This is a test/slice-only safety-net
wave. It does not change routes, answers, output contracts, API responses,
frontend rendering, or data requirements.

## Next recommended action

Use these snapshots as the required safety net before the next
`natural_query.py` extraction. The next extraction should remain behavior
preserving and should stop if it changes route selection, route kwargs, parser
notes, `result_status`, `result_reason`, sections, or
`metadata.unsupported_filters` for any snapshot case.

Handle the Atlantic Division broad-team-record behavior as its own
product-boundary cleanup preflight before touching adjacent
opponent-conference routing.
