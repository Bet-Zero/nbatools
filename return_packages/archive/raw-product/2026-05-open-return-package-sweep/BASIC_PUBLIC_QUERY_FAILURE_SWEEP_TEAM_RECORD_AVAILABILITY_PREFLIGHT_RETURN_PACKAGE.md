# Basic Public Query Failure Sweep: Team Record Availability Preflight Return Package

## What Was Done

- Investigated seven user-discovered public queries through the natural-query
  engine and API payload helper.
- Captured CLI pretty-output answer subjects for the availability variants.
- Reviewed current docs, tests, raw QA corpus, and data helpers for
  without-player, with-player, compound availability, typo/partial names, and
  single-game rebound leaderboards.
- Created the planning preflight:
  `docs/planning/raw-product/BASIC_PUBLIC_QUERY_FAILURE_SWEEP_TEAM_RECORD_AVAILABILITY_PREFLIGHT.md`

No production code, parser/routing behavior, QA corpus expectations, frontend
rendering, or release status changed.

## Current Behavior Summary

| Query | Current result | Classification |
|---|---|---|
| `Luka stats this season` | `player_game_summary` / `ok`; Luka Dončić 64 games, 43-21, 33.484 PPG | Supported and working |
| `Lakers record without Luka` | `team_record` / `ok`; Lakers 18 games, 10-8; game log included | Supported baseline and working |
| `Lakers record with Luka` | `player_game_summary` / `ok`; Luka subject, 64 games, 43-21 | Wrong-scope / public copy issue for team-record intent |
| `Lakers record with Reaves` | `player_game_summary` / `ok`; Reaves subject, 51 games, 36-15 | Wrong-scope / public copy issue for team-record intent |
| `Lakers record with Reaves without Luka` | `player_game_summary` / `ok`; Reaves subject, 10 games, 6-4, without Luka applied | Unsupported compound availability currently returns plausible wrong-scope answer |
| `Lakers record without Luk` | `team_record` / `ok`; full Lakers 82-game record, no absence filter | Typo/unresolved-player broad fallback |
| `Who had the most rebounds in a game this year?` | `top_player_games` / `ok`; Scottie Barnes top row with 25 rebounds | Supported and working |

`metadata.unsupported_filters` was null for all seven current probes. That is
correct for the supported cases but is a gap for the compound and typo cases.

## Support Boundary Findings

- `team record without PLAYER` is shipped and tested. `Lakers record without
  Luka` is the supported baseline.
- `team record with PLAYER` is data-capable but not currently shipped as a
  `team_record` surface. Current behavior returns player-summary rows with
  record fields, which is plausible but wrong-scope for the public query.
- Multi-player availability is an explicit unsupported boundary, but mixed
  `with PLAYER without PLAYER` phrasing is not covered and currently escapes to
  player summary.
- Partial/typo names such as `Luk` are not supported and should not silently
  drop the requested availability filter.
- Top single-game rebound wording is working; the exact `this year` variant
  resolves to the loaded current regular season.

## Coverage Gaps

- Raw QA has multiple without-player team-record cases and the unsupported
  `lakers_lebron_ad_both_play` case.
- Raw QA does not have single-player `team record with PLAYER` cases.
- Raw QA does not have mixed compound availability such as
  `with Reaves without Luka`.
- Raw QA does not have a typo/partial unresolved availability case such as
  `without Luk`.
- Tests cover existing multi-player availability forms like `with LeBron and
  AD`, but not mixed with/without availability.

## Recommended Next Execution

1. Promote single-player whole-game presence team records:
   - `Lakers record with Luka` -> `team_record` / `ok`
   - `Lakers record with Reaves` -> `team_record` / `ok`
   - add a `with_player` slot, applied filter, caveat, and game-log section.
2. Keep compound availability unsupported until a dedicated product contract
   exists:
   - `Lakers record with Reaves without Luka` -> `team_record` /
     `no_result` / `filter_not_supported`
   - `metadata.unsupported_filters=["multi_player_availability"]`
3. Fix unresolved availability names to no-result/clarify:
   - `Lakers record without Luk` must not return the full Lakers record.
4. Add raw QA and parser/query tests for these exact cases before changing
   docs that advertise new support.

## Validation Run

Read-only query probes:

```bash
.venv/bin/python - <<'PY'
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
from nbatools.api_handlers import query_result_to_payload
PY
```

CLI answer spot checks:

```bash
.venv/bin/nbatools-cli ask "Lakers record without Luka"
.venv/bin/nbatools-cli ask "Lakers record with Luka"
.venv/bin/nbatools-cli ask "Lakers record with Reaves without Luka"
.venv/bin/nbatools-cli ask "Lakers record without Luk"
.venv/bin/nbatools-cli ask "Luka stats this season"
.venv/bin/nbatools-cli ask "Who had the most rebounds in a game this year?"
```

Markdown lint availability checked:

- `markdownlint`: not found
- `markdownlint-cli2`: not found
- `mdl`: not found
- `mdformat`: not found

Passed:

```bash
git diff --check
```

Because both files are new and untracked, direct `--no-index` whitespace checks
were also run against each file. They produced no whitespace diagnostics; the
nonzero exit code is expected for `--no-index` when comparing `/dev/null` to a
new file.

## Blocking Issues

None for preflight. The next wave needs a product decision on whether to ship
single-player `with_player` team records now or to guard them as unsupported.
This preflight recommends shipping them because the data is already available
and the public intent is basic.
