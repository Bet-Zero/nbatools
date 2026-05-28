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
- `fewest points allowed per game` (team stat alias → opponent_pts_per_game)
- `gave up the fewest points per game`
- `teams allowing the fewest points`
- `most points allowed per game`
- `opponent PPG leaders` (points allowed / opponent points, not defensive rating)
- `best 3 point percentage` (stat alias → fg3_pct)
- `best field goal percentage` (stat alias → fg_pct)
- `team ft%` (stat alias → ft_pct)
- `What teams have the best net rating this year?`
- `What team has the highest offensive rating this season?`
- `best defensive rating teams this season`
- `fastest pace teams this season`
- `Which centers have the most rebounds this season?` (position-filtered leaderboard)
- `What players have the best field goal percentage among guards?` (position-filtered leaderboard)
- `guard scoring leaders this season` (position-filtered leaderboard)
- `forwards FG% leaders this season` (position-filtered leaderboard)

Unsupported leaderboard boundaries currently return `no_result` /
`filter_not_supported` rather than broad fallback leaderboards:

- rookie leaderboards, such as `rookie scoring leaders this season`
- league-wide starter/bench leaderboards, such as `starter assist leaders this season`
- personal-foul leaderboards, such as `personal fouls leaders this season` and `players with most personal fouls`
- team bench scoring, such as `Celtics bench scoring this season`
- single-team advanced-stat summaries, such as `Warriors net rating this season`
  (league-wide team advanced-stat leaderboards remain supported)

## Finders

Use these to return filtered game rows.

Structured commands:

- `nbatools-cli query player-game-finder`
- `nbatools-cli query game-finder`

Natural examples:

- `Jokic under 20 points`
- `Jokic between 20 and 30 points`
- `Jokic games with 30 points and 10 assists`
- `Celtics games with 120+ points and 15+ threes`
- `Celtics wins vs Bucks over 120 points`
- `Knicks record when they allow fewer than 110 points` (points allowed → opponent points)
- `Cade Cunningham season high` (routes to top single games)
- `highest scoring games this season` (routes to top_player_games, not ppg leaderboard)
- `most assists in a game this season` (routes to top_player_games, not assist-per-game leaders)

## Summaries

Use these to aggregate filtered results.

Structured commands:

- `nbatools-cli query player-game-summary`
- `nbatools-cli query game-summary`

Natural examples:

- `Jokic recent form`
- `Celtics last 15 games summary`
- `Jokic summary vs Lakers`
- `Anthony Edwards last 10 games summary`
- `KD TS% vs top defenses` (uses the `top-10 defenses` opponent-quality bucket)
- `Curry last 20 games from three` (last-N summary with made-threes stat context)
- `LeBron stats vs Kevin Durant` (player-vs-player as opponent filter)
- `Jokic averages against Stephen Curry`

## Comparisons

Use these to compare players or teams over a selected sample.

Structured commands:

- `nbatools-cli query player-compare`
- `nbatools-cli query team-compare`

Natural examples:

- `Jokic vs Embiid recent form`
- `LeBron James vs Kevin Durant comparison`
- `Compare LeBron James and Kevin Durant`
- `Kobe vs LeBron playoffs in 2008-09`
- `Celtics vs Bucks from 2021-22 to 2023-24`

## Splits

Use these for home/away or wins/losses breakdowns.

Natural examples:

- `Jokic home vs away in 2025-26`
- `Jokic home away split last 20 games`
- `Celtics wins vs losses`
- `How does Anthony Edwards shoot in wins versus losses?`

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
    nbatools-cli query top-player-games --season 2025-26 --stat ast --limit 10
    nbatools-cli query top-player-games --season 2025-26 --stat reb --limit 10

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
- `fewest points allowed per game`
- `gave up the fewest points per game`
- `teams allowing the fewest points`
- `most points allowed per game`
- `opponent PPG leaders`
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
- `LeBron James vs Kevin Durant comparison` (player comparison)

## Player availability team records

- `Lakers record without LeBron`
- `Warriors wins without Stephen Curry`
- `Celtics summary without Jaylen Brown`
- `Lakers record with Luka`
- `Lakers record w/ Luka`
- `Lakers record with Austin Reaves`
- `How many games did the Lakers win with Reaves available?`

Single-player whole-game presence and absence filters return the team record
for games where that player did or did not play for the team. Compound
multi-player availability remains unsupported and returns a clean no-result
instead of a broad fallback.

## Team records

- `Lakers road record last season` (`last season` resolves to `2024-25` when the latest regular season is `2025-26`)
- `How did the Lakers do on the road last season?`
- `Lakers 2024-25 road record`
- `Celtics road record since January 1`
- `Celtics record against playoff teams`
- `Celtics record against the East this season`
- `Lakers record against Western Conference teams`
- `Lakers road record against West last season`
- `Knicks record against Eastern Conference teams since January 1`

Opponent-conference team-record filters are supported for trusted current-era
conference coverage (`2024-25` and `2025-26`). Supported phrases include
`against the East`, `against East teams`, `against Eastern Conference teams`,
`vs the West`, `vs West teams`, and `versus Western Conference opponents`.
Missing/untrusted seasons, division requests, and geography phrases such as
`east coast teams` remain unsupported and return `no_result` /
`filter_not_supported` instead of broad full-season records. The resolved
conference opponent list keeps all 15 conference members, including the subject
team when applicable; this has no effect because teams do not play themselves.
Explicit NBA division requests such as `Celtics record vs Atlantic Division`
return `metadata.unsupported_filters=["opponent_division"]`.
Named-team division record phrases preserve the `team_record` route; no-subject
division record phrases such as `record against Northwest Division teams`
preserve `team_record_leaderboard`. These are guarded unsupported responses,
not division-filter support. Mixed conference-plus-division phrasing such as
`Lakers record against Western Conference Pacific Division teams` does not
return a broader conference-only answer. `conference finals` record phrasing
remains a playoff-round unsupported boundary.

## Playoff history and rounds

- `Lakers playoff history`
- `Heat vs Knicks playoff history`
- `Heat Knicks playoff series record`
- `Lakers Celtics playoff matchup history`
- `Lakers playoff series record vs Celtics`
- `Lakers Finals appearances`
- `most Finals appearances since 1980`
- `best Finals record since 1980`
- `best second-round record since 2010`

Adjacent team names are only treated as a matchup in explicit playoff
series/history contexts. Single-team round-record phrasing such as
`Warriors Finals record since 2015`, `Celtics conference finals record`, and
`Bulls Finals record` is currently unsupported and returns
`no_result` / `filter_not_supported` rather than a broad regular-season record.
Bulls Finals-era round labels are not reliable in the current pre-2001 data.

## Season-high / best-game queries

- `Cade Cunningham season high`
- `LeBron best game this season`
- `highest scoring games this season` (routes to top_player_games)
- `most assists in a game this season` (routes to top_player_games)
- `single-game rebound leaders this season` (routes to top_player_games)

## Distinct count queries

- `how many players scored 40 points this season`
- `number of players with 10 assists this season`

## Date-aware queries

- `top scorers in March`
- `best offensive teams in March`
- `teams with best efg% in March`
- `best offensive teams since January`
- `Celtics road record since January 1`
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

## Rolling stretches

- `hottest 3-game scoring stretch this year`
- `Jokic best 5-game rebounding stretch this season`
- `Booker hottest 4-game scoring stretch`

Team rolling-stretch leaderboards, such as `best 5-game team scoring stretch`,
are not currently supported. They return `no_result` / `filter_not_supported`
until a team rolling-stretch route and result contract exist.

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
- `Knicks record when they allow fewer than 110 points` (uses opponent points / points allowed)
- `Lakers record when they held teams under 100` (uses opponent points / points allowed)
- `Lakers record when they held opponents under 100`
- `Boston record when Tatum shoots under 40%` (uses FG% on the 0.xx scale)
- `Warriors record when Curry shoots over 40% from three` (uses 3PT% on the 0.xx scale)
- `What was Jokic's record in games with a triple-double?`

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
- `Celtics road record since January 1`
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
