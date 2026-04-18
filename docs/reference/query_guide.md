# NBA Tools — Query Guide

> **Role: comprehensive query reference.**
> This is the full reference for structured CLI commands and natural query
> patterns. For a shorter quick-start, see
> [quick_query_guide.md](quick_query_guide.md). For the verified shipped
> behavior spec, see [current_state_guide.md](current_state_guide.md).

This guide describes the current shipped query surface of NBA Tools.

It covers:

- structured CLI commands
- natural query patterns
- route types
- examples by use case

---

# 1. Query Layers

NBA Tools currently supports these query layers.

## Leaderboards

Use these to rank single-game or season-level performance.

Structured commands:

- `nbatools-cli query top-player-games`
- `nbatools-cli query top-team-games`
- `nbatools-cli query season-leaders`
- `nbatools-cli query season-team-leaders`

Natural examples:

- `top scorers this season`
- `highest ts% among players`
- `most 30 point games`
- `best offensive teams`
- `teams with best efg%`
- `teams with most threes`
- `best 3 point percentage` (stat alias → fg3_pct)
- `best field goal percentage` (stat alias → fg_pct)
- `team ft%` (stat alias → ft_pct)

## Finders

Use these to return filtered game rows.

Structured commands:

- `nbatools-cli query player-game-finder`
- `nbatools-cli query game-finder`

Natural examples:

- `Jokic under 20 points`
- `Jokic between 20 and 30 points`
- `Celtics wins vs Bucks over 120 points`
- `Cade Cunningham season high` (routes to top single games)
- `highest scoring games this season` (routes to top_player_games, not ppg leaderboard)

## Summaries

Use these to aggregate filtered results.

Structured commands:

- `nbatools-cli query player-game-summary`
- `nbatools-cli query game-summary`

Natural examples:

- `Jokic recent form`
- `Celtics last 15 games summary`
- `Jokic summary vs Lakers`
- `LeBron stats vs Kevin Durant` (player-vs-player as opponent filter)
- `Jokic averages against Stephen Curry`

## Comparisons

Use these to compare players or teams over a selected sample.

Structured commands:

- `nbatools-cli query player-compare`
- `nbatools-cli query team-compare`

Natural examples:

- `Jokic vs Embiid recent form`
- `Kobe vs LeBron playoffs in 2008-09`
- `Celtics vs Bucks from 2021-22 to 2023-24`

## Splits

Use these for home/away or wins/losses breakdowns.

Natural examples:

- `Jokic home vs away in 2025-26`
- `Jokic home away split last 20 games`
- `Celtics wins vs losses`

## Streaks

Streaks are currently exposed through natural queries.

Natural examples:

- `Jokic 5 straight games with 20+ points`
- `Jokic longest streak of 30 point games`
- `Jokic longest triple-double streak`
- `longest Lakers winning streak`
- `Celtics 5 straight games scoring 120+`

---

# 2. Structured CLI Examples

## top-player-games

    nbatools-cli query top-player-games --season 2005-06 --stat pts --limit 10

## top-team-games

    nbatools-cli query top-team-games --season 2015-16 --stat fg3m --limit 10

## season-leaders

    nbatools-cli query season-leaders --season 2025-26 --stat pts --limit 10 --min-games 20
    nbatools-cli query season-leaders --season 2025-26 --stat ts_pct --limit 10 --min-games 20
    nbatools-cli query season-leaders --season 2025-26 --stat "30 point games" --limit 10

## season-team-leaders

    nbatools-cli query season-team-leaders --season 2025-26 --stat pts --limit 10
    nbatools-cli query season-team-leaders --season 2025-26 --stat efg_pct --limit 10
    nbatools-cli query season-team-leaders --season 2025-26 --stat fg3m --limit 10

## player-game-finder

    nbatools-cli query player-game-finder --season 2005-06 --player "Kobe Bryant" --stat pts --min-value 40 --sort-by stat
    nbatools-cli query player-game-finder --season 2025-26 --player "Nikola Jokić" --opponent LAL
    nbatools-cli query player-game-finder --season 2025-26 --player "LeBron James" --away-only --wins-only

## game-finder

    nbatools-cli query game-finder --season 2025-26 --team BOS --home-only --wins-only
    nbatools-cli query game-finder --season 2025-26 --team LAL --stat pts --min-value 120 --sort-by stat

## player-game-summary

    nbatools-cli query player-game-summary --season 2005-06 --player "Kobe Bryant" --stat pts --min-value 40
    nbatools-cli query player-game-summary --season 2025-26 --player "Nikola Jokić" --opponent LAL

## game-summary

    nbatools-cli query game-summary --season 2025-26 --team BOS --home-only --wins-only
    nbatools-cli query game-summary --start-season 2021-22 --end-season 2023-24 --team BOS

---

# 3. Natural Query Patterns

## Leaderboards

- `top scorers this season`
- `highest ts% among players`
- `most 30 point games`
- `best offensive teams`
- `teams with best efg%`
- `teams with best ts%`
- `teams with most threes`
- `best 3 point percentage`
- `best field goal percentage`
- `team fg%`

## Matchups and head-to-head

- `Jokic vs Lakers`
- `Jokic last 10 vs Lakers`
- `Jokic summary vs Lakers`
- `Embiid head-to-head vs Jokic`
- `Jokic h2h vs Embiid`
- `Lakers head-to-head vs Celtics`
- `Celtics h2h vs Bucks home`
- `LeBron stats vs Kevin Durant` (player-vs-player as opponent filter)
- `Jokic averages against Stephen Curry`

## Without-player queries

- `Lakers record without LeBron`
- `Warriors wins without Stephen Curry`
- `Celtics summary without Jaylen Brown`

## Season-high / best-game queries

- `Cade Cunningham season high`
- `LeBron best game this season`
- `highest scoring games this season` (routes to top_player_games)

## Distinct count queries

- `how many players scored 40 points this season`
- `number of players with 10 assists this season`

## Date-aware queries

- `top scorers in March`
- `best offensive teams in March`
- `teams with best efg% in March`
- `best offensive teams since January`
- `Jokic since All-Star break`
- `best offensive teams since All-Star break`

## Streaks

- `Jokic 5 straight games with 20+ points`
- `Jokic longest streak of 30 point games`
- `Jokic consecutive games with a made three`
- `Jokic longest triple-double streak`
- `longest Lakers winning streak`
- `longest Bucks streak with 15+ threes`
- `Thunder consecutive games with 110+ points`
- `Celtics 5 straight games scoring 120+`

## Splits

- `Jokic home vs away in 2025-26`
- `Jokic home away split last 20 games`
- `Celtics wins vs losses`

---

# 4. Boolean Query Support

## Threshold language

Supported:

- `over`
- `under`
- `between`

Examples:

- `Jokic over 25 points`
- `Jokic under 20 points`
- `Jokic between 20 and 30 points`

## Multi-condition chaining

Supported:

- `and`
- `or`
- parentheses

Examples:

- `Jokic over 25 points and over 10 rebounds`
- `Jokic over 30 points or over 12 assists`
- `Jokic (over 25 points and over 10 rebounds) or over 15 assists`

## Current grouped boolean coverage

Grouped boolean logic currently works across:

- player finder queries
- team finder queries
- player summaries
- team summaries
- player split summaries
- team split summaries

Examples:

- `Jokic (over 25 points and over 10 rebounds) or over 15 assists`
- `Celtics (over 120 points and over 15 threes) or under 10 turnovers`
- `Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists`

Not currently documented as supported for:

- player comparisons
- team comparisons

---

# 5. Date and Window Support

Natural queries currently support:

- explicit season
- season range
- `last N games`
- `in <month>`
- `since <month>`
- `last <N> days`
- `since All-Star break`

Examples:

- `Jokic recent form`
- `Jokic last 8 games summary`
- `top scorers in March`
- `best offensive teams since January`
- `Jokic since All-Star break`

---

# 6. Metrics

## Common natural-query stats

- points / pts
- rebounds / reb
- assists / ast
- steals / stl
- blocks / blk
- threes / fg3m
- turnovers / tov

## Advanced metrics shown in summaries / comparisons / splits

- eFG%
- TS%
- USG%
- AST%
- REB%

USG%, AST%, and REB% are recomputed from the filtered player sample.

---

# 7. Exports

Natural query exports:
nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

Structured query exports:
nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --json outputs/player_summary.json

---

# 8. Current Tested State

Current tested state:

- full suite: **1650+ passing tests** across 41+ test files
