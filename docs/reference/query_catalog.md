# NBA Tools — Query Catalog

> **Role: living capability catalog.**
> This file is the repo’s running inventory of the shipped query surface: what kinds
> of questions NBA Tools can answer, the main ways to ask them, and the common
> formatting pieces that can be combined together.
>
> Use this as the closest thing to a searchable “database” of supported question
> types. For verified behavior boundaries, see
> [current_state_guide.md](current_state_guide.md). For a broader narrative guide,
> see [query_guide.md](query_guide.md). For quick examples, see
> [quick_query_guide.md](quick_query_guide.md).
>
> **Maintenance rule:** when a meaningful shipped query capability is added,
> expanded, renamed, or intentionally restricted, update this file in the same pass.
> Every advertised feature family also needs coverage in the
> `public_query_acceptance` phrasing gate, a generated family matrix, and reviewed
> representative outputs from `product_review.md`; raw QA case count alone is not
> enough public-readiness evidence.

When this catalog marks a family as parser-recognized but still unfiltered,
placeholder-backed, or explicitly deferred, that note reflects current shipped
behavior only. This catalog and
[current_state_guide.md](current_state_guide.md) are the durable shipped
boundary.

---

## 1. How to use this file

This catalog is organized around three questions:

1. **What kind of thing are you asking for?**
  - finder
  - count
  - summary
  - comparison
  - split
  - leaderboard
  - streak
  - on/off
  - lineup
  - record
  - playoff history / era history

2. **What entity is the query about?**
   - player
   - team
   - player vs player
   - team vs team
   - league-wide ranking

3. **What context or filters are you adding?**
   - season / season range / career
   - regular season vs playoffs
   - opponent / matchup / head-to-head
   - home / away
   - wins / losses
   - stat thresholds
   - grouped boolean logic
   - date windows / recent form

If a feature is not reflected here, it should not be assumed shipped.

---

## 2. Common building blocks you can combine

### 2.1 Entities

- player name: `Jokic`, `Nikola Jokić`, `LeBron`, `SGA`, `Bronny`
- player typo correction is not supported in V1: misspelled multi-word names such as
  `Kevn Durant` or `Stephn Curry` return `no_result` / `filter_not_supported`
  with `metadata.unsupported_filters=["unresolved_player"]` instead of silently
  correcting via last-name/nickname aliases; exact aliases like `durant`, `steph`,
  and `curry` still resolve normally
- team name/alias: `Lakers`, `LAL`, `Celtics`, `Sixers`, `Wolves`
- player comparison wording: `Compare Jokic and Embiid`, `Jokic vs Embiid recent form`
  (bare `PLAYER vs PLAYER` phrasing such as `Jokic vs Embiid` returns an
  ambiguous/no-result boundary until clarification UI exists)
- team vs team: `Celtics vs Bucks`
- awards and award-winner questions such as `who won MVP this season`,
  `MVP winner this season`, and `nba award winners this season` are explicit
  unsupported boundaries; they return `no_result` / `filter_not_supported`
  with `metadata.unsupported_filters=["award_query"]` and do not infer winners
  from stat leaderboards

### 2.2 Time/context filters

- explicit season: `2025-26`
- season range: `from 2021-22 to 2023-24`
- since season/year: `since 2020`, `since 2020-21`
- last N seasons: `last 3 seasons`
- career / all-time: `career`, `all-time`
- last N games: `last 10 games`
- rolling windows: `3-game stretch`, `5-game scoring stretch`, `rolling 10-game stretch`
- month / date windows: `in March`, `since January`, `since January 1`, `since All-Star break`, `last 30 days`
- explicit calendar dates: `January 1 2026`, `Jan. 1, 2026`
- fuzzy time words: `lately`, `recently` (→ last 10 games), `past month`, `last month` (→ rolling 30 days), `last couple weeks`, `past 2 weeks` (→ rolling 14 days)
- single-day: `last night`, `yesterday`, `today`, `tonight`
- season type: `playoffs`, `postseason`

### 2.3 Sample filters

- opponent (team): `vs Lakers`, `against Celtics`
- opponent (player): `vs Kevin Durant`, `against Stephen Curry` (when used with context words like "stats", "averages", "record")
- without player: `without LeBron`, `w/o LeBron`, `when LeBron out`, `when LeBron was out`, `when LeBron didn't play`, `no LeBron`, `sans LeBron`, `minus LeBron`
- whole-game player presence for team records: `Lakers record with Luka`, `Lakers record w/ Luka`, `How many games did the Lakers win with Reaves available?`
- on/off presence: `on/off`, `on off`, `on-off`, `with Jokic on the floor`, `without Jokic on the floor`, `Jokic sitting`
  (routes to `player_on_off`; executes against trusted `team_player_on_off_summary`
  rows when coverage exists, otherwise returns an explicit unsupported-data
  response. Whole-game `with_player` / `without_player` availability remains
  separate.)
- lineup membership: `lineups with LeBron and AD`, `with Tatum and Brown together`, `best 3-man units`
  (routes to `lineup_summary` / `lineup_leaderboard`; executes against trusted
  `league_lineup_viz` rows when coverage exists, otherwise returns an explicit
  unsupported-data response. Roster membership remains separate.)
- rolling-window phrasing: `hottest 3-game stretch`, `best 5-game stretch by Game Score`, `rolling 10-game stretch`
- head-to-head: `head-to-head`, `h2h`
- home / away: `home`, `away`, `road`
- wins / losses: `wins`, `losses`, `won`, `lost`
- clutch context: `clutch`, `in the clutch`, `clutch time`, `late-game`
  (parser-recognized and route-propagated; current query engine returns unfiltered
  results with an explicit note. A future `PlayByPlayV3` plus score-state source
  path is approved, but execution is not shipped yet.)
- period context: `1st quarter`, `4th quarter`, `first half`, `second half`, `overtime`, `OT`
  (parser-recognized and engine-accepted; `player_game_finder` and `team_record`
  execute these filters when `player_game_period_stats` / `team_game_period_stats`
  coverage exists for the requested slice, otherwise they fall back with an
  explicit unfiltered-results note. Other routes still remain unfiltered and are
  out of scope for the core finish line unless a future product queue reopens
  period route expansion.)
- schedule context: `back-to-back`, `b2b`, `rest advantage`, `rest disadvantage`, `2 days rest`, `one-possession games`, `nationally televised`, `on national TV`
  (parser-recognized and engine-accepted; `team_record` and `player_game_summary`
  execute these filters when trusted `schedule_context_features` coverage exists
  for the requested slice, otherwise they fall back with an explicit
  unfiltered-results note. Other routes still remain unfiltered and are out of
  scope for the core finish line unless a future product queue reopens
  schedule-context route expansion.)
- role context: `as a starter`, `starting`, `off the bench`, `bench`, `reserve`
  (parser-recognized and engine-executed for player summary/finder queries when trusted
  `player_game_starter_roles` coverage exists for the requested slice; otherwise execution
  appends an explicit unfiltered-results note. Team-only phrases like
  `Celtics bench scoring` and league-wide role leaderboards are explicit
  unsupported boundaries unless a future product queue reopens role route
  expansion)
- opponent-quality context: `against contenders`, `against good teams`, `vs top teams`, `against playoff teams`, `against postseason teams`, `against teams that made the playoffs`, `against teams over .500`, `against top-10 defenses`
  (resolved to concrete opponent buckets on the supported single-entity summary/finder/record
  routes using the latest regular-season standings or team-advanced data for the selected season;
  unsupported routes append an explicit note and remain unfiltered)
- opponent-conference context for team records: `against the East`, `against East teams`, `against Eastern Conference teams`, `vs the West`, `versus Western Conference opponents`
  (resolved through trusted `team_conference_membership` coverage for `2024-25`
  and `2025-26`; missing or untrusted coverage returns `no_result` /
  `filter_not_supported`, not a broad full-season record)
- opponent-division context for team records: `vs Atlantic Division`,
  `against Pacific Division`, `against Northwest Division teams`
  (resolved through trusted `team_conference_membership` division coverage for
  named-team regular-season `team_record` queries in `2024-25` and `2025-26`;
  missing or untrusted coverage returns `no_result` / `filter_not_supported`,
  not a broad full-season record)
- split views: `home vs away`, `home versus away`, `wins vs losses`, `wins versus losses`, `in wins and losses`

### 2.4 Threshold language

- `over 25 points`
- `under 10 turnovers`
- `between 20 and 30 points`
- `25+ points`
- `5+ threes`
- reverse phrasing for some stats: `ts% over .600`, `efg% under .500`
- opponent-points defensive thresholds: `held opponents under 100 points`, `held teams under 100`, `held teams to under 100 points`, `held them to under 100 points`, `limited opponents to under 100 points`, `kept the other team below 100 points`, `allowed under 100 points`, `allow fewer than 110 points`, `points allowed under 110`, `opponent points under 110`, `opp pts under 110`, `gave up under 100`, `gave up fewer than 100 points`
- clear shooting percentage thresholds normalize to the stored 0.xx scale: `shoots under 40%`, `shoots below 40 percent`, `FG% under 40%`, `field goal percentage below 40%`, `shoots under .400`, `3PT% over 40%`, `from three over 40%`, `FT% under 80%`

### 2.6 Stat name aliases

Every recognized stat phrasing grouped by canonical stat name. Both standard names and verbal forms (e.g., `scored`, `rebounding`) are first-class.

| Canonical stat | Recognized aliases                                                                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `pts`          | `pts`, `point`, `points`, `scored`, `scores`, `scoring`                                                                                                                              |
| `reb`          | `reb`, `rebound`, `rebounds`, `rebounded`, `rebounding`, `boards`                                                                                                                    |
| `ast`          | `ast`, `assist`, `assists`, `assisted`, `dimes`                                                                                                                                      |
| `stl`          | `stl`, `steal`, `steals`, `swipes`                                                                                                                                                   |
| `blk`          | `blk`, `block`, `blocks`, `swats`                                                                                                                                                    |
| `fg3m`         | `3s`, `3pm`, `fg3m`, `threes`, `threes made`, `three-point makes`, `three pointers made`                                                                                             |
| `pf`           | `pf`, `foul`, `fouls`, `personal foul`, `personal fouls`                                                                                                                             |
| `tov`          | `tov`, `turnover`, `turnovers`                                                                                                                                                       |
| `minutes`      | `min`, `minutes`                                                                                                                                                                     |
| `fgm`          | `fgm`, `field goal made`, `field goals made`                                                                                                                                         |
| `fga`          | `fga`, `field goal attempted`, `field goal attempts`, `field goals attempted`                                                                                                         |
| `fg3a`         | `3pa`, `fg3a`, `threes attempted`, `three attempts`, `three pointer attempted`, `three pointer attempts`, `three pointers attempted`, `three-pointer attempted`, `three-pointer attempts`, `three-pointers attempted` |
| `ftm`          | `ftm`, `free throw made`, `free throws made`                                                                                                                                         |
| `fta`          | `fta`, `free throw attempted`, `free throw attempts`, `free throws attempted`                                                                                                         |
| `fg_pct`       | `fg%`, `fg_pct`, `field goal %`, `field goal percentage`                                                                                                                             |
| `fg3_pct`      | `3p%`, `3pt%`, `fg3_pct`, `3 point %`, `3-point %`, `three point %`, `three-point %`, `3 point percentage`, `3-point percentage`, `three point percentage`, `three-point percentage` |
| `ft_pct`       | `ft%`, `ft_pct`, `free throw %`, `free throw percentage`                                                                                                                             |
| `efg_pct`      | `efg%`, `efg_pct`, `effective fg`, `effective fg %`, `effective field goal`, `effective field goal %`, `effective field goal percentage`                                             |
| `ts_pct`       | `ts%`, `ts_pct`, `true shooting`, `true shooting %`, `true shooting percentage`                                                                                                      |
| `plus_minus`   | `+/-`, `plus minus`, `plus/minus`, `plus_minus`                                                                                                                                      |
| `usg_pct`      | `usg`, `usg%`, `usage`, `usage %`, `usg_pct`, `usage rate`, `usage percentage`                                                                                                       |
| `ast_pct`      | `ast%`, `ast_pct`, `assist %`, `assist percentage`                                                                                                                                   |
| `reb_pct`      | `reb%`, `reb_pct`, `rebound %`, `rebound percentage`                                                                                                                                 |
| `tov_pct`      | `tov%`, `tov_pct`, `turnover %`, `turnover rate`, `turnover percentage`                                                                                                              |
| `off_rating`   | `off rating`, `off_rating`, `offensive rating`                                                                                                                                       |
| `def_rating`   | `def rating`, `def_rating`, `defensive rating`                                                                                                                                       |
| `net_rating`   | `net rating`, `net_rating`                                                                                                                                                           |
| `pace`         | `pace`                                                                                                                                                                               |

> **Source of truth:** `STAT_ALIASES` in `src/nbatools/commands/_constants.py`. `STAT_PATTERN` is auto-generated from this dict.
> Standalone `from three` is additionally recognized as `fg3m` only for guarded
> player last-N summary stat context; percentage thresholds such as
> `from three over 40%` remain `fg3_pct`.

### 2.5 Boolean logic

- `and`
- `or`
- parentheses

Examples:

- `Jokic over 25 points and over 10 rebounds`
- `Jokic over 30 points or over 12 assists`
- `Jokic (over 25 points and over 10 rebounds) or over 15 assists`

---

## 3. Query classes and example phrasings

## 3.1 Finder queries — return matching game rows

### Player finder

Examples:

- `Jokic under 20 points`
- `Jokic between 20 and 30 points`
- `Jokic last 10 games over 25 points`
- `show me Jokic games vs Lakers`
- `find LeBron away wins`
- `Jokic games with 30 points and 10 assists`
- `what games did Tatum have over 35 points and 5+ threes`
- `Cade Cunningham season high` (routes to top single games for the player)
- `LeBron best game this season`

### Team finder

Examples:

- `Celtics wins vs Bucks over 120 points`
- `Celtics games with 120+ points and 15+ threes`
- `show me Lakers home losses`
- `list Thunder games with 15+ threes`
- `find Knicks games vs Heat since 2021`
- `Lakers held opponents under 100 points this season`

### Finder + grouped boolean

Examples:

- `Jokic (over 25 points and over 10 rebounds) or over 15 assists`
- `Celtics (over 120 points and over 15 threes) or under 10 turnovers`

---

## 3.2 Count queries — return counts rather than rows

### Player count

Examples:

- `how many Jokic games with 30+ points and 10+ rebounds since 2021`
- `count LeBron triple doubles since 2020`
- `how many playoff games did Tatum have over 35 points`

### Team count

Examples:

- `how many Celtics games with 120+ points and 15+ threes since 2022`
- `count Lakers home wins vs Warriors since 2021`
- `how often have the Lakers held opponents under 100 points this year`

### Count intent phrases

Common triggers:

- `how many`
- `how often`
- `count`
- `number of`
- `total games`

### Distinct player/team count

Counts distinct players (or teams) meeting a threshold condition, rather than counting games for one entity.

Examples:

- `how many players scored 40 points this season`
- `number of players with 10 assists this season`

Routes to `player_occurrence_leaders` with `limit=None` and a note indicating distinct-count semantics.

**Limitation:** requires a stat + threshold (e.g., "scored 40 points"). Phrasing without an explicit threshold (e.g., "how many players played this season") is not supported.

---

## 3.3 Summary queries — aggregate one player or one team over a sample

### Player summary

Examples:

- `Jokic recent form`
- `Jokic last 15 games summary`
- `Jokic summary vs Lakers`
- `Jokic since 2021`
- `LeBron career`
- `Jokic last 10` / `Jokic last 10 games` (player + timeframe shorthand → summary per spec §15.3)
- `Jokic this season` (player + implicit season → summary)
- `Anthony Edwards last 10 games summary`
- `How has Jayson Tatum played against winning teams this season?` (verb-phrase question form → summary)
- `KD TS% vs top defenses` (stat + opponent-quality context → summary; `top defenses` maps to `top-10 defenses`)
- `Curry last 20 games from three` (last-N summary with made-threes stat context)
- `Jokic playoff stats vs Suns since 2021`
- `LeBron stats vs Kevin Durant` (player-vs-player as opponent filter)
- `Jokic averages against Stephen Curry` (summary filtered to games where opponent played)

### Team summary

Examples:

- `Celtics last 15 games summary`
- `Knicks playoff summary vs Heat since 1999`
- `Lakers since 2020`
- `Warriors career vs Celtics`

### Summary context support

Common combinations:

- opponent team filters
- opponent player filters (`vs Kevin Durant`, `against Stephen Curry`) — filters to games where the specified opponent player appeared on the opposing team
- without player filters (`without LeBron`, `without Steph Curry`) — excludes games where the specified player played; clears the player from entity detection so the query routes to the team path
- with player filters for team records (`with Luka`, `w/ Luka`, `with Austin Reaves available`) — filters to team games where the specified player played for that team and keeps the answer subject as the team record
- home / away
- wins / losses
- season ranges
- career / all-time
- playoff-only spans
- date windows / recent form

### On/off summaries

Examples:

- `Jokic on/off`
- `Jokic on off`
- `Nikola Jokic on-off`
- `Nuggets with and without Jokic`
- `with Curry on the floor`
- `without Giannis on the floor`

Current behavior:

- parser routes to `player_on_off` and preserves `lineup_members` and `presence_state`
- execution uses trusted `team_player_on_off_summary` rows when both `on` and `off` coverage exists for the requested single-player slice
- missing or untrusted coverage, unsupported multi-player on/off, and slices outside the source contract return explicit unsupported/no-result responses
- whole-game `with_player` / `without_player` availability is not an on/off substitute
- compound or multi-player availability record phrasing such as `Lakers record when LeBron and AD both play` or `Lakers record with Reaves without Luka` is outside the current lineup/availability boundary and returns an explicit unsupported/no-result response rather than an unfiltered team record or player summary

### Specific lineup summaries

Examples:

- `lineups with LeBron and AD`
- `lineup with Tatum and Brown together`
- `2-man combos with Brunson and Hart`

Current behavior:

- parser routes to `lineup_summary` and preserves `lineup_members`, `unit_size`, and `minute_minimum`
- execution uses trusted `league_lineup_viz` rows normalized from upstream `leaguelineupviz` via `nba_api.stats.endpoints.LeagueLineupViz`
- missing or untrusted coverage, unsupported unit sizes, and slices outside the source contract return explicit unsupported/no-result responses
- roster membership is not a lineup-unit substitute

---

## 3.4 Comparison queries — compare two players or two teams

### Player comparison

Examples:

- `Jokic vs Embiid recent form`
- `Compare Jokic and Embiid since 2021`
- `LeBron James vs Kevin Durant comparison`
- `Compare LeBron James and Kevin Durant`
- `How do LeBron James and Kevin Durant compare this season?`
- `Jokic head-to-head vs Embiid since 2021`
- `Kobe vs LeBron playoffs in 2008-09`

### Team comparison

Examples:

- `Celtics vs Bucks from 2021-22 to 2023-24`
- `Lakers vs Celtics since 2010`
- `Knicks head-to-head vs Heat since 1999`
- `Celtics vs Bucks home`

### Comparison support notes

- bare player-vs-player phrasing such as `LeBron vs KD` is treated as
  ambiguous in V1 and returns `no_result` / `ambiguous_query`; add words such as
  `compare`, `comparison`, `recent form`, `head-to-head`, `stats`, or
  `game log` to choose an intent
- head-to-head / h2h phrasing is supported where the sample can be resolved
- if there are no shared head-to-head games in the resolved sample, the result can be `no_match`

---

## 3.5 Split summary queries — aggregate one entity across split buckets

### Player split

Examples:

- `Jokic home vs away in 2025-26`
- `Jokic home away split last 20 games`
- `Jokic wins vs losses`
- `How does Anthony Edwards shoot in wins versus losses?`

### Team split

Examples:

- `Celtics home vs away`
- `Celtics wins vs losses`
- `Lakers playoff home vs away since 2020`

---

## 3.6 Leaderboard queries — rank players or teams league-wide

### Player leaderboards

Examples:

- `top scorers this season`
- `highest ts% among players`
- `most 30 point games`
- `best rebounders last 3 seasons`
- `top scorers since 2020`
- `best ts% vs Celtics last 3 seasons`
- `highest plus minus vs Celtics since 2021`
- `most steals in playoffs since 2010`
- `best 3 point percentage` (recognized stat alias → fg3_pct)
- `best field goal percentage` (recognized stat alias → fg_pct)
- `best free throw percentage` (recognized stat alias → ft_pct)
- `personal fouls leaders this season` / `PF leaders this season` (basic box-score total leaderboard → pf)
- `Who played the most minutes this season?` (basic box-score total leaderboard → minutes)
- `3PA leaders this season` (basic box-score total leaderboard → fg3a)
- `highest scoring games this season` (routes to top_player_games, not ppg leaderboard)
- `biggest scoring games this season` / `most dominant games by plus-minus this season` (single-game leaderboard variants)
- `most assists in a game this season` / `single-game rebound leaders this season` (non-scoring single-game leaderboard variants)
- `Who scored the most points on January 1 2026?` (explicit-date top-scorer question → date-filtered `top_player_games`)
- `who leads the NBA in points per game` / `who leads the league in assists` (question form; routes to leaderboard)
- `points leaders last 10`, `last 10 scoring leaders`, `top scorers last 10 games` (shorthand → `season_leaders`, stat=pts, last_n=10)
- `Who scores the most at home this season?` / `most points at home this season` (leaderboard + home filter)
- `hottest from three lately`, `hottest from 3 lately`, `best shot blocker last 10 games`, `best rim protector over the past month`, `best offensive rebounder lately` (skill phrasing mapped to supported leaderboard stats)

Ranking semantics:

- box-score volume aliases promoted for `season_leaders` (`pf`, `minutes`,
  `fgm`, `fga`, `fg3a`, `ftm`, `fta`) rank season totals
- existing public per-game semantics remain unchanged for aliases such as
  points per game, rebounds per game, assists per game, steals per game,
  blocks per game, turnovers per game, plus-minus per game, and made threes

### Team leaderboards

Examples:

- `best offensive teams`
- `teams with best efg%`
- `teams with most threes`
- `most wins since 2015`
- `best record since 2015`
- `worst away record since 2020`
- `best scoring teams vs Lakers since 2018`
- `Which team has allowed the fewest points per game this season?`
- `Which team gave up the fewest points per game?`
- `teams allowing the fewest points`
- `which teams allow the most points per game this season`
- `opponent PPG leaders this season`
- `opponent points per game leaders`
- points allowed / opponent PPG leaderboards rank opponent scoring allowed, not defensive rating
- `best team 3 point percentage` (team stat alias → fg3_pct)
- `team fg%` (team stat alias → fg_pct)
- `team ft%` (team stat alias → ft_pct)
- `What teams have the best net rating this year?`
- `What team has the highest offensive rating this season?`
- `best defensive rating teams this season`
- `fastest pace teams this season`

Leaderboard no-match behavior:

- if data exists but the requested date/context/sample filters leave no games in scope, leaderboard routes return `no_match` rather than falling back to a broader leaderboard
- rolling/date-window team advanced rating leaderboards and undefined skill concepts
  such as catch-and-shoot, drawing fouls, transition scoring, isolation defense,
  shot creation, and per-game attempt minimums are unsupported boundaries; routed
  fallbacks include an explicit `unsupported_boundary` note
- rookie leaderboards and league-wide starter/bench leaderboards are
  unsupported boundaries; these return
  `no_result` / `filter_not_supported` rather than broad points/assist
  leaderboards
- fouls-drawn wording is not mapped to personal fouls committed; drawing-foul
  queries remain unsupported until a fouls-drawn data contract exists
- league-wide team advanced-stat leaderboards for net rating, offensive rating,
  defensive rating, and pace are supported, but single-team scalar summaries
  such as `Warriors net rating this season` return `no_result` /
  `filter_not_supported` until a single-team advanced-stat result contract is
  approved

### Position-filtered leaderboards

Examples:

- `best ts% among centers this season`
- `What players have the best field goal percentage among guards?`
- `top scorers among guards since 2021`
- `best rebounders among big men`
- `Which centers have the most rebounds this season?`
- `guard scoring leaders this season`
- `forwards FG% leaders this season`
- `point guard assist leaders this season` (maps to the supported `guards` group)

### Stretch leaderboards

Examples:

- `hottest 3-game scoring stretch this year`
- `best 5-game stretch by Game Score`
- `most efficient 10-game rolling stretch`
- `Booker hottest 4-game scoring stretch`

Current behavior:

- parser routes to `player_stretch_leaderboard`
- `window_size` comes from the `N-game` or `rolling N games` phrase
- named counting stats rank rolling per-game averages; shooting percentages use rolling makes/attempts; `game_score` ranks rolling average Game Score
- team-scoped rolling-stretch leaderboards such as `best 5-game team scoring stretch` are not currently supported; they return `no_result` / `filter_not_supported` instead of player rows

### Lineup leaderboards

Examples:

- `best 5-man lineups`
- `best 3-man units with at least 200 minutes`
- `top 2-man combos`

Current behavior:

- parser routes to `lineup_leaderboard` and preserves `lineup_members`, `unit_size`, and `minute_minimum`
- execution uses trusted `league_lineup_viz` rows normalized from upstream `leaguelineupviz` via `nba_api.stats.endpoints.LeagueLineupViz`
- missing or untrusted coverage, unsupported unit sizes, and slices outside the source contract return explicit unsupported/no-result responses

### Ranking language

Common triggers:

- `top`
- `best`
- `highest`
- `most`
- `lowest`
- `fewest`
- `least`
- `worst`
- `bottom`
- `rank`
- `ranking`

---

## 3.7 Streak queries

### Player streaks

Examples:

- `Jokic 5 straight games with 20+ points`
- `Jokic longest streak of 30 point games`
- `Jokic longest 30-point streak`
- `longest Jokic 30 point streak`
- `Jokic consecutive 30 point games longest`
- `Jokic consecutive games with a made three`
- `Jokic longest triple-double streak`
- `LeBron current 20+ point streak`
- `Curry longest streak with at least 3 threes`

### Team streaks

Examples:

- `longest Lakers winning streak`
- `longest Bucks streak with 15+ threes`
- `Thunder consecutive games with 110+ points`
- `Celtics 5 straight games scoring 120+`

---

## 3.8 Record queries

### Single-team record

Examples:

- `Celtics record since 2020`
- `Lakers playoff record since 2015`
- `Lakers road record last season`
- `How did the Lakers do on the road last season?`
- `Celtics road record since January 1`
- `Celtics record against playoff teams`
- `Celtics record against the East this season`
- `Celtics record vs Atlantic Division`
- `Lakers record against Western Conference teams`
- `Lakers record against Pacific Division`
- `Lakers road record against West last season`
- `Knicks record against Eastern Conference teams since January 1`
- `best home record over the last 5 seasons`
- `worst away record since 2020`
- `Celtics record when scoring 120+ since 2022`
- `What was Jokic's record in games with a triple-double?`
- `Lakers record with Luka`
- `Lakers record with Austin Reaves`
- `Lakers record without LeBron James`
- `Warriors wins without Stephen Curry`

Relative season support:

- `last season` resolves to the season before the latest loaded season for that season type, so with latest regular-season data set to `2025-26`, `last season` resolves to `2024-25`
- `last 10 games` remains a last-N game window, not a season phrase

### Team vs team matchup record

Examples:

- `Lakers vs Celtics all-time record`
- `Celtics record vs Bucks since 2020`
- `Knicks playoff record vs Heat since 1999`

### Record leaderboards

Examples:

- `best record since 2015`
- `which teams had the most wins since 2010`
- `highest win percentage vs Lakers since 2018`

Record no-match behavior:

- if team/opponent/absence/date/context filters leave no matching sample, record routes return `no_match` with an explicit empty-sample note instead of falling back to a full-season result

Playoff wording boundary:

- `against playoff teams`, `against postseason teams`, and `against teams that made the playoffs` are opponent-quality filters over regular-season games by default
- `playoff record`, `postseason record`, `in the playoffs`, `playoff history`, and `playoff series` use playoff-game semantics or dedicated playoff-history routes

---

## 3.9 Playoff / era-history queries

### Playoff history

Examples:

- `Lakers playoff history`
- `Heat vs Knicks playoff history`
- `Heat Knicks playoff history`
- `Lakers Celtics playoff matchup history`
- `Heat Knicks playoff series record`
- `Lakers playoff series record vs Celtics`

Adjacent team-team phrasing is supported only inside explicit playoff
series/history contexts. `Heat Knicks playoff series record` is treated as a
Heat-vs-Knicks playoff matchup-history query; ordinary non-playoff adjacent
team names are not promoted to a matchup.

### Playoff appearances / rounds

Examples:

- `finals appearances`
- `Warriors conference finals appearances`
- `most Finals appearances since 1980`
- `most conference finals appearances since 2000`
- `best finals record since 1980`
- `best second round record`
- `best second-round record since 2010`

### By-decade / era-bucket queries

Examples:

- `Warriors record by decade`
- `winningest team of the 2010s`
- `Lakers vs Celtics by decade`

### Historical split boundaries

Examples outside the shipped playoff/era-history surface:

- `Celtics finals record`
- `Warriors Finals record since 2015`
- `Celtics conference finals record`
- `Bulls Finals record`
- `LeBron record in the Finals`

Finals- or conference-finals-specific team/player records require an approved
playoff-round record data contract for the requested entity grain. Current
shipped support covers single-team playoff history, playoff appearances,
playoff matchup history, and league-wide playoff-round record leaderboards; it
does not claim entity-specific Finals or conference-finals record splits.
Single-team round-record phrasing returns `no_result` /
`filter_not_supported` instead of falling back to a broad regular-season record.
The current dataset also does not provide reliable round labels for Bulls
Finals-era pre-2001 rows, so `Bulls Finals record` remains unsupported until a
round backfill or explicit inference contract exists.

---

## 3.10 Occurrence / milestone queries

### Single-event occurrence leaderboards

Examples:

- `most 40 point games since 2020`
- `most 15+ rebound games since 2018`
- `most 5+ three games vs Lakers`
- `most triple doubles since 2020`
- `most double doubles last 3 seasons`

### Compound occurrence queries

Examples:

- `most games with 25+ points and 10+ assists since 2020`
- `how many Jokic games with 30+ points and 10+ rebounds in playoffs since 2021`
- `teams with the most games scoring 120+ and making 15+ threes since 2020`
- `most games with 3+ steals and 2+ blocks`
- `how many Celtics games vs Bucks with 120+ points and under 10 turnovers`

---

## 3.11 Context and opponent-quality filters

### Clutch recognition

Examples:

- `Tatum clutch stats`
- `Lakers clutch record`

Current behavior:

- parser sets `clutch=True` and routes to the supported execution boundary:
  `player_game_summary`, `player_game_finder`, `team_record`, and
  `season_leaders`
- those routes use trusted `player_game_clutch_stats` /
  `team_game_clutch_stats` rows derived from official `PlayByPlayV3` events
  when coverage exists for the requested slice
- missing or untrusted clutch coverage keeps the explicit unfiltered-results
  note rather than fabricating clutch output
- whole-game logs, period-only box-score windows, and season-level clutch
  dashboard aggregates remain rejected as clutch substitutes

### Quarter / half / overtime context

Examples:

- `LeBron 4th quarter scoring`
- `Celtics first half record`

Current behavior:

- parser sets `quarter` / `half` and routes normally
- `player_game_finder` and `team_record` execute period filters when trusted
  `player_game_period_stats` / `team_game_period_stats` coverage exists for the
  requested slice; otherwise they fall back with an explicit unfiltered-results note
- other routes, such as period leaderboard phrasing, still append the explicit
  unfiltered-results note because the current period-backed route boundary does
  not extend beyond `player_game_finder` / `team_record`
- broader period route expansion is out of scope for the core finish line unless
  a future product queue reopens it

### Back-to-back filter

Examples:

- `Lakers on back-to-backs record`
- `Lakers b2b record`

Current behavior:

- parser sets `back_to_back=True` and preserves the filter in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter through `schedule_context_features` when coverage exists
- unsupported routes or missing coverage keep an explicit unfiltered-results note
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### Rest filter

Examples:

- `Jokic with rest advantage`
- `Jokic on 2 days rest`

Current behavior:

- parser sets `rest_days` to `advantage`, `disadvantage`, or an integer day count and preserves it in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter through normalized `schedule_context_features.rest_days` / `rest_advantage` when coverage exists
- unsupported routes or missing coverage keep an explicit unfiltered-results note
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### One-possession filter

Examples:

- `Celtics one-possession record`
- `Thunder one-possession games`

Current behavior:

- parser sets `one_possession=True` and preserves the filter in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter through `schedule_context_features.one_possession` when coverage exists
- unsupported routes or missing coverage keep an explicit unfiltered-results note
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### National-TV filter

Examples:

- `Knicks on national TV record`
- `Lakers nationally televised games`

Current behavior:

- parser sets `nationally_televised=True` and preserves the filter in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter only when `schedule_context_features.national_tv_source_trusted=1`
- current placeholder schedule pulls can still leave national-TV coverage untrusted; in that case execution falls back with an explicit unfiltered-results note
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### Starter / bench role

Examples:

- `LeBron as a starter stats`
- `Brunson off the bench`

Current behavior:

- parser sets `role` for player-context queries only
- `player_game_summary` and `player_game_finder` apply starter / bench filtering only when the requested slice has complete trusted coverage in `player_game_starter_roles`
- if trusted starter-role coverage is missing or untrusted for any row in the requested slice, execution keeps the explicit unfiltered-results note instead of partially filtering
- league-wide starter/bench leaderboards and team-level bench scoring are
  explicit unsupported boundaries and return `no_result` /
  `filter_not_supported`

### Opponent-quality filter

Examples:

- `Jokic against contenders 2024-25`
- `Lakers record against top-10 defenses 2024-25`
- `KD TS% vs top defenses`
- `Celtics record against playoff teams`
- `Celtics record against teams that made the playoffs`

Current behavior:

- parser sets a structured `opponent_quality` slot containing the surface term and resolved bucket definition
- execution resolves that bucket to a concrete opponent-team list on the supported single-entity summary/finder/record routes
- `top defenses` is accepted as shorthand for `top-10 defenses` only in explicit opponent context such as `against`, `vs`, or `versus`
- `playoff teams` includes postseason-team phrasings such as `postseason teams` and `teams that made the playoffs`; this remains a regular-season opponent-quality context unless the query also explicitly asks for playoff competition
- opponent-conference filters such as `Celtics record against the East` or
  `Lakers record against Western Conference teams` are supported for
  `team_record` queries in trusted seasons `2024-25` and `2025-26`; the filter
  composes with home/away and date filters
- the resolved conference list keeps all 15 conference members, including the
  subject team when applicable; this has no effect because teams do not play
  themselves
- named-team opponent-division filters such as `Celtics record vs Atlantic
  Division`, `Lakers record against Pacific Division`, and `Knicks record vs
  Central Division` are supported for regular-season `team_record` queries in
  trusted seasons `2024-25` and `2025-26`
- the resolved division list keeps all five division members, including the
  subject team when applicable; this has no effect because teams do not play
  themselves
- east/west geography phrases such as `east coast teams` and seasons outside
  trusted conference or division coverage remain unsupported and return
  `no_result` / `filter_not_supported` instead of broad full-season records
- mixed conference plus division text does not return a broader
  conference-only or division-only answer
- no-subject division record phrasing, such as
  `record against Northwest Division teams`, preserves the closest
  `team_record_leaderboard` route but still returns unsupported/no-result
- playoff division record phrasing remains unsupported; `conference finals`
  phrasing remains a playoff-round concept, not an opponent-conference or
  opponent-division filter
- unsupported routes append an explicit note or return a clean unsupported
  response instead of silently broadening

---

## 4. Structured CLI surface (high-level catalog)

NBA Tools also supports structured CLI queries through:

- `nbatools-cli query ...`

Representative structured routes include:

- `top-player-games`
- `top-team-games`
- `season-leaders`
- `season-team-leaders`
- `player-on-off`
- `lineup-summary`
- `lineup-leaderboard`
- `player-stretch-leaderboard`
- `player-game-finder`
- `game-finder`
- `player-game-summary`
- `game-summary`
- `player-compare`
- `team-compare`
- `player-split-summary`
- `team-split-summary`

The broader structured route inventory should stay aligned with the current service/API route list and `query_guide.md` examples.

---

## 5. Common formatting advice

### Good natural-query patterns

Good examples:

- `Jokic last 10 games over 25 points`
- `Celtics wins vs Bucks over 120 points`
- `top scorers since 2020`
- `how many Jokic triple doubles since 2021`
- `Lakers vs Celtics all-time record`
- `Warriors record by decade`

### Recommended ingredients when a query is complex

Try to make the query explicit about:

- **entity** — player/team/matchup
- **time window** — season, since year, last N, career, playoffs
- **sample filters** — opponent, home/away, wins/losses
- **query class** — show/list, count, summary, rank, record
- **thresholds** — over, under, between, 25+, 5+ threes

### Examples of useful phrasing signals

- finder/list: `show me`, `list`, `find`, `which games`
- count: `how many`, `count`, `number of`
- summary: `summary`, `recent form`, `averages`, `record`
- leaderboard: `top`, `best`, `most`, `highest`, `rank`
- record: `record`, `win percentage`, `most wins`

---

## 6. Maintenance checklist for this file

Update this catalog whenever shipped behavior changes in a way that affects:

- a new query class
- a new route family
- a new kind of phrasing the parser now supports
- a new context/filter users can combine into queries
- a newly supported record/playoff/occurrence/history shape
- a meaningful restriction or unsupported combination that should be documented

When updating this file, also check whether these should be updated in the same pass:

- `docs/reference/current_state_guide.md`
- `docs/reference/query_guide.md`
- `docs/reference/quick_query_guide.md`
- `AGENTS.md`
- `docs/index.md`

---

## 7. Relationship to other docs

- **This file** = living catalog of question types and query shapes
- `current_state_guide.md` = strict verified behavior / shipped state
- `query_guide.md` = broader narrative reference with structured + natural examples
- `quick_query_guide.md` = shortest path to trying the tool
