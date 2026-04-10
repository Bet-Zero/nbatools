# NBA Tools Current State Guide

This guide describes the current shipped behavior of NBA Tools.

---

## Entry Points

### Natural language
    nbatools-cli ask "Jokic recent form"

### Structured CLI
    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10

---

## Supported Query Types

### Leaderboards
Supported natural leaderboard coverage includes:
- player season leaders
- team season leaders
- top single-game performances

Examples:
    nbatools-cli ask "top scorers this season"
    nbatools-cli ask "highest ts% among players"
    nbatools-cli ask "most 30 point games"
    nbatools-cli ask "best offensive teams"
    nbatools-cli ask "teams with best efg%"
    nbatools-cli ask "teams with most threes"

### Summaries
Supported:
- player summary
- team summary
- filtered summary
- recent form summary
- last-N summary
- matchup summary

Examples:
    nbatools-cli ask "Jokic recent form"
    nbatools-cli ask "Celtics last 15 games summary"
    nbatools-cli ask "Jokic summary vs Lakers"

### Comparisons
Supported:
- player vs player
- team vs team
- recent form comparison
- head-to-head comparison phrasing

Examples:
    nbatools-cli ask "Jokic vs Embiid recent form"
    nbatools-cli ask "Kobe vs LeBron playoffs in 2008-09"
    nbatools-cli ask "Celtics vs Bucks from 2021-22 to 2023-24"
    nbatools-cli ask "Jokic h2h vs Embiid"
    nbatools-cli ask "Lakers head-to-head vs Celtics"

### Split analysis
Supported:
- home vs away
- wins vs losses
- player split summaries
- team split summaries

Examples:
    nbatools-cli ask "Jokic home vs away in 2025-26"
    nbatools-cli ask "Jokic home away split last 20 games"
    nbatools-cli ask "Celtics wins vs losses"

### Finder queries
Supported:
- player game finder
- team game finder
- threshold-based matching games
- recent filtered windows
- grouped boolean filtering across finder-style queries

Examples:
    nbatools-cli ask "Jokic under 20 points"
    nbatools-cli ask "Jokic between 20 and 30 points"
    nbatools-cli ask "Jokic last 10 games over 25 points and under 15 rebounds"
    nbatools-cli ask "Jokic over 25 points or over 10 rebounds"

### Streak queries
Supported:
- player threshold streaks
- longest player streaks
- made-three streaks
- triple-double streaks
- team threshold streaks
- team winning / losing streaks

Examples:
    nbatools-cli ask "Jokic 5 straight games with 20+ points"
    nbatools-cli ask "Jokic longest streak of 30 point games"
    nbatools-cli ask "Jokic consecutive games with a made three"
    nbatools-cli ask "Jokic longest triple-double streak"
    nbatools-cli ask "longest Lakers winning streak"
    nbatools-cli ask "Celtics 5 straight games scoring 120+"
    nbatools-cli ask "longest Bucks streak with 15+ threes"

---

## Query Language Support

### Threshold language
Supported:
- `over`
- `under`
- `between`

Examples:
    Jokic over 25 points
    Jokic under 20 points
    Jokic between 20 and 30 points

### Multi-condition chaining
Supported:
- `and`
- `or`
- parentheses

Examples:
    Jokic last 10 games over 25 points and over 10 rebounds
    Celtics wins vs Bucks over 120 points and over 15 threes
    Jokic over 25 points or over 10 rebounds
    Jokic (over 25 points and over 10 rebounds) or over 15 assists
    Jokic over 25 points and (over 10 rebounds or over 15 assists)

### Grouped boolean coverage
Grouped boolean logic currently works across:
- player finder queries
- team finder queries
- player summaries
- team summaries
- player split summaries
- team split summaries

Examples:
    Jokic (over 25 points and over 10 rebounds) or over 15 assists
    Celtics (over 120 points and over 15 threes) or under 10 turnovers
    Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists

Not currently documented as supported for:
- player comparisons
- team comparisons

---

## Date and Window Support

Supported natural date context includes:
- explicit season
- season range
- `last N games`
- `in <month>`
- `since <month>`
- `last <N> days`
- `since All-Star break`

Examples:
    nbatools-cli ask "top scorers in March"
    nbatools-cli ask "best offensive teams in March"
    nbatools-cli ask "teams with best efg% in March"
    nbatools-cli ask "best offensive teams since January"
    nbatools-cli ask "Jokic since All-Star break"
    nbatools-cli ask "best offensive teams since All-Star break"

---

## Metrics

### Core box score metrics
- points
- rebounds
- assists
- steals
- blocks
- threes
- turnovers
- plus/minus
- minutes
- shooting splits

### Advanced shooting metrics
- eFG%
- TS%

### Advanced player metrics
Current support:
- USG%
- AST%
- REB%

These appear in:
- player summaries
- player comparisons
- player split summaries
- pretty output
- structured output

These player rates are recomputed from the filtered sample.

---

## Export Support

Available on both natural and structured query paths:
- `--csv`
- `--txt`
- `--json`

Examples:
    nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
    nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
    nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

---

## Pretty Output

Current pretty output supports:
- summary headers
- comparison formatting
- split formatting
- section rules
- clearer metric labels
- advanced metric display:
  - eFG%
  - TS%
  - USG%
  - AST%
  - REB%

---

## Current Tested State

- full suite: **206 passing tests**
