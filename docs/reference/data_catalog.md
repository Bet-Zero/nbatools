# NBA Tools — Data Catalog

This document describes the data structure of the NBA Tools project.

It is the primary reference for:
- what tables exist
- where they live
- what each table represents
- what their grain is
- how they are built
- what they are used for

---

# 1. Directory Structure

## Raw tables
Raw tables live in:

- `data/raw/games/`
- `data/raw/schedule/`
- `data/raw/rosters/`
- `data/raw/standings_snapshots/`
- `data/raw/team_game_stats/`
- `data/raw/player_game_stats/`
- `data/raw/team_season_advanced/`
- `data/raw/player_season_advanced/`
- `data/raw/teams/`

## Processed tables
Processed tables live in:

- `data/processed/team_game_features/`
- `data/processed/game_features/`
- `data/processed/player_game_features/`
- `data/processed/league_season_stats/`

## Metadata
Metadata lives in:

- `data/metadata/backfill_manifest.csv`

---

# 2. Raw Tables

## teams

### Path
`data/raw/teams/teams_reference.csv`

### Type
Reference table

### Grain
One row per team/franchise reference entry

### Purpose
Basic team reference data.

### Notes
This is not the main historical naming source.
Historical naming is handled by `team_history_reference.csv`.

---

## team_history_reference

### Path
`data/raw/teams/team_history_reference.csv`

### Type
Reference table

### Grain
One row per historical team identity range

### Purpose
Provides historical team branding and identity by season range.

### Key columns
- `team_id`
- `season_start`
- `season_end`
- `team_abbr`
- `team_name`
- `city`
- `franchise_label`

### Purpose in system
Used to preserve historical team naming across franchise changes, relocations, and rebrands.

### Important note
`team_id` is the canonical identity key.  
Names and abbreviations are presentation/history fields.

---

## games

### Path
`data/raw/games/<season>_<season_type>.csv`

### Grain
One row per game

### Purpose
Canonical game-level truth table for played games.

### Important columns
- `game_id`
- `season`
- `season_type`
- `game_date`
- `game_datetime`
- `status`
- `is_final`
- `home_team_id`
- `away_team_id`
- `home_team_abbr`
- `away_team_abbr`
- `home_team_name`
- `away_team_name`
- `arena`
- `city`
- `attendance`
- `overtime_periods`
- `is_playoff`
- `playoff_round`
- `series_id`
- `series_game_number`

### Notes
This is the canonical source of truth for game identity and played-game metadata.

---

## schedule

### Path
`data/raw/schedule/<season>_<season_type>.csv`

### Grain
One row per game

### Purpose
Calendar / schedule layer.

### Important columns
- `game_id`
- `season`
- `season_type`
- `game_date`
- `game_datetime`
- `status`
- `home_team_id`
- `away_team_id`
- `home_team_abbr`
- `away_team_abbr`
- `home_team_name`
- `away_team_name`
- `arena`
- `city`
- `national_tv`

### Notes
If `games` and `schedule` disagree, `games` wins.

---

## rosters

### Path
`data/raw/rosters/<season>.csv`

### Grain
One row per player-team-season-stint

### Purpose
Season-level roster identity table.

### Important columns
- `season`
- `team_id`
- `team_abbr`
- `player_id`
- `player_name`
- `jersey_number`
- `position`
- `height`
- `weight`
- `birth_date`
- `experience_years`
- `school`
- `stint`

### Notes
Roster files are season-only, not season-type-specific.

---

## standings_snapshots

### Path
`data/raw/standings_snapshots/<season>_<season_type>.csv`

### Grain
One row per team per snapshot date

### Purpose
Standings state at a defined point in time.

### Important columns
- `snapshot_date`
- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `wins`
- `losses`
- `win_pct`
- `conference_rank`
- `division_rank`
- `games_back`
- `streak`

### Notes
Standings exist for regular season only.
Playoffs do not use standings snapshots.

---

## team_game_stats

### Path
`data/raw/team_game_stats/<season>_<season_type>.csv`

### Grain
One row per team per game

### Purpose
Team box score source truth.

### Important columns
- `game_id`
- `season`
- `season_type`
- `game_date`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `wl`
- `minutes`
- `pts`
- `fgm`
- `fga`
- `fg_pct`
- `fg3m`
- `fg3a`
- `fg3_pct`
- `ftm`
- `fta`
- `ft_pct`
- `oreb`
- `dreb`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `pf`
- `plus_minus`

---

## player_game_stats

### Path
`data/raw/player_game_stats/<season>_<season_type>.csv`

### Grain
One row per player per game

### Purpose
Player box score source truth.

### Important columns
- `game_id`
- `season`
- `season_type`
- `game_date`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `player_id`
- `player_name`
- `starter_flag`
- `start_position`
- `minutes`
- `pts`
- `fgm`
- `fga`
- `fg_pct`
- `fg3m`
- `fg3a`
- `fg3_pct`
- `ftm`
- `fta`
- `ft_pct`
- `oreb`
- `dreb`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `pf`
- `plus_minus`
- `comment`

---

## team_season_advanced

### Path
`data/raw/team_season_advanced/<season>_<season_type>.csv`

### Grain
One row per team per as-of date

### Purpose
Season-level team advanced metrics snapshot.

### Important columns
- `season`
- `season_type`
- `as_of_date`
- `team_id`
- `team_abbr`
- `games_played`
- `wins`
- `losses`
- `win_pct`
- `off_rating`
- `def_rating`
- `net_rating`
- `pace`

---

## player_season_advanced

### Path
`data/raw/player_season_advanced/<season>_<season_type>.csv`

### Grain
One row per player per as-of date

### Purpose
Season-level player advanced metrics snapshot.

### Important columns
- `season`
- `season_type`
- `as_of_date`
- `player_id`
- `player_name`
- `team_id`
- `games_played`
- `minutes_per_game`
- `off_rating`
- `def_rating`
- `net_rating`
- `usage_rate`
- `ts_pct`
- `ast_pct`
- `reb_pct`
- `oreb_pct`
- `dreb_pct`
- `pie`

---

# 3. Processed Tables

## team_game_features

### Path
`data/processed/team_game_features/<season>_<season_type>.csv`

### Grain
One row per team per game

### Purpose
Rolling and contextual team features entering a game.

### Important columns
- `team_id`
- `game_id`
- `game_date`
- `season`
- `season_type`
- `opponent_team_id`
- `is_home`
- `days_rest`
- `is_back_to_back`
- `pts_last_5`
- `pts_last_10`
- `fg3m_last_5`
- `fg3a_last_5`
- `fg3_pct_last_5`
- `reb_last_5`
- `tov_last_5`
- `games_in_window_last_5`
- `games_in_window_last_10`
- `has_full_last_5_window`
- `has_full_last_10_window`

### Notes
All rolling features are based only on games before the current game.

---

## game_features

### Path
`data/processed/game_features/<season>_<season_type>.csv`

### Grain
One row per game

### Purpose
Merged matchup-level feature table for home vs away comparisons.

### Important columns
- `game_id`
- `game_date`
- `season`
- `season_type`
- `home_team_id`
- `away_team_id`
- `home_days_rest`
- `away_days_rest`
- `home_is_back_to_back`
- `away_is_back_to_back`
- `rest_diff`
- `rest_advantage`
- `home_pts_last_5`
- `away_pts_last_5`
- `pts_last_5_diff`
- `home_fg3m_last_5`
- `away_fg3m_last_5`
- `fg3m_last_5_diff`
- `fg3m_battle_winner`
- `home_fg3_pct_last_5`
- `away_fg3_pct_last_5`
- `fg3_pct_last_5_diff`
- `fg3_pct_battle_winner`
- `home_reb_last_5`
- `away_reb_last_5`
- `reb_last_5_diff`
- `reb_battle_winner`
- `home_tov_last_5`
- `away_tov_last_5`
- `tov_last_5_diff`
- `tov_battle_winner`

---

## player_game_features

### Path
`data/processed/player_game_features/<season>_<season_type>.csv`

### Grain
One row per player per game

### Purpose
Rolling player form features entering a game.

### Important columns
- `player_id`
- `game_id`
- `team_id`
- `game_date`
- `season`
- `season_type`
- `minutes_last_5`
- `minutes_last_10`
- `pts_last_5`
- `pts_last_10`
- `reb_last_5`
- `ast_last_5`
- `fga_last_5`
- `fg3a_last_5`
- `fta_last_5`
- `fg_pct_last_5`
- `fg3_pct_last_5`
- `games_in_window_last_5`
- `games_in_window_last_10`
- `has_full_last_5_window`
- `has_full_last_10_window`

---

## league_season_stats

### Path
`data/processed/league_season_stats/<season>_<season_type>.csv`

### Grain
One row per season per season_type

### Purpose
League-wide seasonal environment context.

### Important columns
- `season`
- `season_type`
- `games`
- `avg_pts`
- `avg_fg3m`
- `avg_fg3a`
- `avg_fg3_pct`
- `avg_reb`
- `avg_tov`

---

# 4. Metadata Tables

## backfill_manifest

### Path
`data/metadata/backfill_manifest.csv`

### Grain
One row per season and season_type

### Purpose
Control-layer record of backfill completeness.

### Important columns
- `season`
- `season_type`
- `raw_complete`
- `processed_complete`
- `loaded_at`

---

# 5. Source of Truth Rules

## Team identity
- `team_id` is canonical
- names/abbreviations are presentation/history attributes

## Game identity
- `games` is canonical for played games
- `schedule` is the planning/calendar layer

## Historical naming
- historical branding should come from `team_history_reference`
- static fallback team mappings are not the final historical authority

## Standings
- standings are regular-season-only
- playoffs do not use standings snapshots

---

# 6. Coverage Status

Current known coverage:

- `1996-97` through `2024-25`: Regular Season + Playoffs
- `2025-26`: Regular Season only

This should be updated if coverage expands further back or when current-season playoffs are loaded.
