# Scripts Retirement

**Date:** 2026-04-16

## Summary

The `/scripts/` directory contained standalone analysis scripts that predated the canonical engine/pipeline/CLI architecture. All four scripts have been retired. Their functionality is now covered by canonical command modules, the CLI, the query service, and the API.

`/scripts/` remains in `.gitignore` — the files were never tracked in git. This document records the retirement decision so future contributors know the status.

## Scripts audited

### `nba_3pt_battle_records/` — Retired

**What it did:** Fetched team game logs directly from `nba_api`, compared FG3M and FG3_PCT between the two teams in each game, and tallied whether the "3-point battle winner" also won the game. Wrote CSV/JSON to `outputs/nba_3pt_battle_records/`.

**Why retired:** Fully replaced by the canonical engine.

**Canonical replacements:**

- `commands/analyze_3pt_battles.py` — same analysis using local pipeline data
- `commands/battle_summary.py` — generalized battle metric support (fg3m, fg3_pct, reb, tov, rest)
- CLI: `nbatools-cli analysis battle-summary --battle fg3m`

### `top10_h2h/` — Retired

**What it did:** Fetched standings and team game logs from `nba_api`, identified the top 10 teams by win%, built a head-to-head wins matrix, and wrote CSV to `outputs/top10_h2h/`.

**Why retired:** The building blocks exist in the canonical engine. Team-vs-team records, matchup filtering, and team comparisons are all available through structured commands.

**Canonical replacements:**

- `commands/team_compare.py` — head-to-head team comparison with filters
- `commands/team_record.py` — team record aggregation, team-vs-team matchup records
- `commands/season_team_leaders.py` — team rankings by stat
- CLI: `nbatools-cli query team-compare`, `nbatools-cli ask "celtics vs bucks record"`

### `top10_h2h_required_players/` — Retired

**What it did:** Extended the top-10 H2H script by filtering out games where specified "required players" (e.g., LeBron, Jokic, Wembanyama) did not play. Fetched both team and player game logs from `nba_api`.

**Why retired:** The core matchup logic is covered by canonical commands. The unique "required player participation" filter is a niche feature that can be composed from existing building blocks (player game finder to identify games played, then team game finder/compare with date filtering).

**Canonical replacements:**

- `commands/team_compare.py` + `commands/player_game_finder.py` — composable for similar analysis
- CLI: `nbatools-cli ask "celtics vs nuggets record"`, `nbatools-cli query player-game-finder`

**Note:** The exact "exclude games where player X did not play" filter is not a single CLI command today. If this specific analysis is needed again, it should be built as a proper command module rather than resurrected as a standalone script.

### `top10_pointdiff/` — Retired

**What it did:** Fetched standings and team game logs from `nba_api`, built a point differential matrix among the top 10 teams, and wrote CSV to `outputs/top10_pointdiff/`.

**Why retired:** Team point differential rankings are available through the canonical leaderboard system.

**Canonical replacements:**

- `commands/season_team_leaders.py` — supports `plus_minus` stat for team rankings
- `commands/team_compare.py` — point differential in head-to-head comparisons
- CLI: `nbatools-cli ask "team point differential leaders"`, `nbatools-cli query season-team-leaders`

## Common reasons for retirement

All four scripts shared these issues:

1. **Bypassed the pipeline.** They called `nba_api.stats.endpoints` directly instead of using local pipeline data, making them fragile and slow (network-dependent with custom retry logic).
2. **Duplicated infrastructure.** Each had its own HTTP headers, timeout/retry logic, and column-name resolution — all of which the pipeline handles canonically.
3. **No structured results.** They printed to stdout and wrote ad-hoc CSV files instead of returning structured result objects consumable by the CLI, API, and frontend.
4. **No tests.** None were covered by the test suite.

## What changed in the repo

| Change                                | File                                 |
| ------------------------------------- | ------------------------------------ |
| Removed stale `scripts/*` lint rule   | `pyproject.toml`                     |
| Added retirement note to `.gitignore` | `.gitignore`                         |
| Marked cleanup item #6 as resolved    | `docs/audits/architecture_hygiene_audit.md` |
| Created this document                 | `docs/audits/scripts_retirement.md`         |

## Local cleanup (optional)

If you have a local `/scripts/` directory, you can safely delete it:

```bash
rm -rf scripts/
```

The `outputs/` directory (also gitignored) contains leftover output files from manual script runs and can also be cleaned up at your discretion.
