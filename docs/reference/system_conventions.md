# NBA Tools — System Conventions

This document defines the project conventions that future commands, tools, and analyses should follow.

These conventions are part of the foundation.

---

# 1. Season Format

## Season string format
Seasons are represented as:

`YYYY-YY`

Examples:
- `2024-25`
- `1996-97`

This is the standard format across:
- file names
- commands
- metadata
- manifests

---

# 2. Season Type Values

Allowed values:

- `Regular Season`
- `Playoffs`

These values must be used exactly in commands and data rows.

---

# 3. File Naming Convention

## Raw season-type files
`<season>_<season_type_normalized>.csv`

Where:
- `Regular Season` → `regular_season`
- `Playoffs` → `playoffs`

Examples:
- `2024-25_regular_season.csv`
- `2024-25_playoffs.csv`

## Season-only files
Some tables are season-only and do not use season_type.

Example:
- `data/raw/rosters/2024-25.csv`

---

# 4. Canonical Keys

## Team identity
`team_id` is the canonical team identity key.

## Player identity
`player_id` is the canonical player identity key.

## Game identity
`game_id` is the canonical game identity key.

Names and abbreviations are not canonical keys.

---

# 5. Historical Team Naming Rule

Historical team branding should come from:

`data/raw/teams/team_history_reference.csv`

Not from current static team mappings.

This matters for:
- Hornets / Pelicans
- Bobcats / Hornets
- Nets branding/location
- SuperSonics / Thunder
- other franchise-era changes

Rule:
- identity = `team_id`
- historical naming = `team_history_reference`

---

# 6. Source-of-Truth Rules

## Games vs schedule
- `games` = canonical played-game truth
- `schedule` = planning/calendar layer

If they differ, `games` wins.

## Raw vs processed
- raw tables are source truth or source snapshots
- processed tables are derived from raw tables
- processed tables must be rebuildable from raw tables

## Team names
- raw game-level data may reflect source-era naming
- fallbacks may not always be historically correct
- historical display work should prefer `team_history_reference`

---

# 7. Feature Policy

## No future leakage
Rolling features must be calculated only from games before the current row’s game.

## Early-season behavior
If insufficient prior games exist:
- rolling fields may be blank/null
- window counts may be less than target size
- `has_full_last_5_window` / `has_full_last_10_window` indicate completeness

## Rest calculation
Rest is based on the team’s or player’s prior game date.

## Season-type separation
Regular season and playoffs remain separate by `season_type`.
Do not mix them in rolling feature calculations unless explicitly building a separate mixed-context tool.

---

# 8. Standings Convention

Standings snapshots are regular-season-only.

There are no playoff standings snapshots.

Any workflow that assumes standings must account for this.

---

# 9. Manifest Convention

Manifest rows are tracked by:
- `season`
- `season_type`

A season-only raw file like `rosters/<season>.csv` does not create a separate manifest type.

---

# 10. Inventory Convention

Inventory distinguishes between:
- raw season-only labels
- raw season-type labels
- processed season-type labels

Manifest alignment should be checked against season-type labels only.

---

# 11. Current Historical Coverage Convention

Current official coverage baseline:

- `1996-97` through `2024-25`: Regular Season + Playoffs
- `2025-26`: Regular Season only

If coverage expands earlier or current playoffs are added, update all relevant docs.

---

# 12. Known Limitations

## Current-season playoffs
May not exist yet if the season is still in progress.

## Older historical seasons
May have more endpoint instability or historical naming quirks.

## Historical naming integration
Reference layer exists, but future query/report commands should explicitly use it when historical display correctness matters.

---

# 13. Design Intent Going Forward

Future tools should build on the current foundation rather than redesign it.

Preferred pattern:
1. use existing raw tables
2. use processed tables when appropriate
3. consult manifest/inventory for coverage
4. consult `team_history_reference` for historical naming
5. preserve no-leakage feature rules

This keeps future work aligned with the foundation.
