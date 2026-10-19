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

When this catalog marks a family as parser-recognized but execution-limited,
coverage-gated, or explicitly deferred, that note reflects current shipped
behavior only. Role/experience filters and the explicit fail-closed combinations
documented below return typed `no_result` / `filter_not_supported` responses
instead of silently dropping the filter. This catalog and
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
- Historical `Seattle SuperSonics`, `SuperSonics`, and `Sonics` select the Seattle
  era. Current `Thunder` retains the franchise's Seattle seasons with a caveat.
- player comparison wording: `Compare Jokic and Embiid`, `Jokic vs Embiid recent form`
  (bare `PLAYER vs PLAYER` phrasing such as `Jokic vs Embiid` returns an
  ambiguous/no-result boundary until clarification UI exists)
- team vs team: `Celtics vs Bucks`
- awards and award-winner questions such as `who won MVP this season`,
  `MVP winner this season`, and `nba award winners this season` are explicit
  unsupported boundaries; they return `no_result` / `filter_not_supported`
  with `metadata.unsupported_filters=["award_query"]` and do not infer winners
  from stat leaderboards

### Ranked game conditions

The candidate game-list path keeps a ranking metric separate from an exact-zero
condition: `best scoring games by Nuggets vs Warriors without turnovers` ranks
points only after filtering the owner's turnovers to zero. `with no`, `with zero`
and bare `with 0` have the same equality meaning, including signed plus/minus;
`0+`, `at least 0` and `0 or more` remain lower bounds. Named owner/opponent and
row-count clauses retain their roles. Fixture checks cover these combinations;
required real-data and deployed acceptance remain pending.

### 2.2 Time/context filters

- explicit season: `2025-26`
- lone year: `in 2024`, `2024 record`, `Lakers record 2024` (a year closing the question) all
  name the 2023-24 season, the one that ended in that year; a number a stat word owns
  (`how many players scored 2000`) is not read as a year
- season range: `from 2021-22 to 2023-24`
- since season/year: `since 2020`, `since 2020-21`
- last N seasons: `last 3 seasons`
- career / all-time: `career`, `all-time`
- last N games: `last 10 games`, `last ten games`, `previous 8 games`, `his 5 most recent games`, `final 8 games`, `final 9 appearances`
  - explicit original participation window: the bounded two-player team-record slice below uses `last_n_scope=original_window` to select the original matchup window before testing both played predicates. Existing `window`, `outcome_window`, defaults and qualifying samples retain their cohort-first participation ordering.
  - window vs qualifying: `how many 30 point games in his last 10 games` counts inside his 10 most recent games;
    `last 5 games where he scored 30` and `last 10 wins` return the most recent qualifying games. Opponent,
    home/away, role and schedule context choose the games in play first; legacy scopes also apply teammate availability before their last-N selection
  - Summary responses retain a `Sample selection` badge distinguishing conditions
    checked within the last N games from the last N games matching conditions.
    Outcome windows name wins/losses only when that outcome was requested.
  - Numbered appearances mean player games. An unspecified recent-game count or ambiguous
    playoff appearances asks for clarification rather than silently widening the sample.
- last N meetings: `last 3 meetings with the Warriors`, `last meeting with the Celtics` (games vs that opponent)
- rolling windows: `3-game stretch`, `5-game scoring stretch`, `rolling 10-game stretch`
- month / date windows: `in March`, `since January`, `since January 1`, `since All-Star break`, `last 30 days`
- explicit calendar dates: `January 1 2026`, `Jan. 1, 2026`
- fuzzy time words: `lately`, `recently` (→ last 10 games), `past month`, `last month` (→ rolling 30 days), `last couple weeks`, `past 2 weeks` (→ rolling 14 days)
- single-day: `last night`, `yesterday`, `today`, `tonight`
- season type: `playoffs`, `postseason`

### 2.3 Sample filters

- opponent (team): `vs Lakers`, `against Celtics`, `over the Celtics` after a subject (`who led the Lakers in scoring over the Celtics`, `LeBron points over the Celtics`; a number after `over` is a threshold)
- a city after a team subject: `Lakers record in Boston`, `which Laker scored the most points in Boston` (road games there; the team's own city is home; a player `in Miami` is left as it was)
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
  (parser-recognized and route-propagated; supported player finder/summary and
  team-record routes execute only against trusted play-by-play-derived clutch
  coverage. Missing coverage returns `no_result` / `filter_not_supported`
  rather than unfiltered rows. Other routes remain explicit unsupported
  boundaries.)
- period context: `1st quarter`, `4th quarter`, `first half`, `second half`, `overtime`, `OT`
  (parser-recognized and engine-accepted; `player_game_finder` and `team_record`
  execute these filters when `player_game_period_stats` / `team_game_period_stats`
  contains every requested entity-game key for the exact window; otherwise they
  return `no_result` / `filter_not_supported` with exact missing key/window detail.
  Other routes return the same typed refusal and are
  out of scope for the core finish line unless a future product queue reopens
  period route expansion.)
- schedule context: `back-to-back`, `b2b`, `rest advantage`, `rest disadvantage`, `2 days rest`, `one-possession games`, `nationally televised`, `on national TV`
  (parser-recognized and engine-accepted; `team_record` and `player_game_summary`
  execute these filters when trusted `schedule_context_features` coverage exists
  for the requested slice. Missing/untrusted coverage or other routes return
  `no_result` / `filter_not_supported`; broader route expansion is out of scope
  for the core finish line unless a future product queue reopens it.)
- role context: `as a starter`, `starting`, `off the bench`, `bench`, `reserve`
  (parser-recognized and engine-executed for player summary/finder queries when trusted
  `player_game_starter_roles` coverage exists for every requested player-game;
  otherwise execution returns `no_result` / `filter_not_supported` with exact
  missing or untrusted key detail. `season_leaders` uses the same exact gate.
  Team-only phrases like `Celtics bench scoring` remain an explicit unsupported
  boundary and return `no_result` / `filter_not_supported` rather than a team
  total or an unfiltered leaderboard.)
- opponent-quality context: `against contenders`, `against good teams`, `vs top teams`, `against top 10 teams`, `against top 5 teams`, `against top seeded teams`, `against playoff teams`, `against non-playoff teams`, `against postseason teams`, `against teams that made the playoffs`, `against winning teams`, `against losing teams`, `against teams over .500`, `against teams under .500`, `vs .500 teams` / `teams .500 or better` (the winning-teams bar), `teams .500 or below` / `.500 or worse` (win% at or under .500), `against bad teams`, `against top-10 defenses`
  (resolved to concrete opponent buckets on the supported single-entity summary/finder/record
  routes using the latest regular-season standings or team-advanced data for the selected season;
  unsupported routes return `no_result` / `filter_not_supported` and never
  execute an unfiltered substitute)
- opponent-conference context for team records: `against the East`, `against East teams`, `against Eastern Conference teams`, `vs the West`, `versus Western Conference opponents`
  (resolved through trusted `team_conference_membership` coverage for `2024-25`
  and `2025-26`; missing or untrusted coverage returns `no_result` /
  `filter_not_supported`, not a broad full-season record)
- opponent-division context for team records: `vs Atlantic Division`,
  `against Pacific Division`, `against Northwest Division teams`
  (resolved through trusted `team_conference_membership` division coverage for
  named-team regular-season `team_record` queries and no-subject
  `team_record_leaderboard` queries in `2024-25` and `2025-26`; missing or
  untrusted coverage returns `no_result` / `filter_not_supported`, not a broad
  full-season record)
- ranked three-point games with a named player or team: `LeBron top 3 three point games`, `Lakers top 3 3 point games`, `Curry best 5 3pt games` rank games by threes made (the league form `top 5 three point games` reads as before)
- point differential: `Lakers point differential`, `scoring margin`, `average margin`, `net points` (the team's average final margin; `games with a point differential over 20` and `biggest point differential` stay game lists, `which team has the best point differential` is the team board)
- month ranges without days: `from January to March`, `between Nov and Jan`, `January through March`, `Jan-Mar`, `in January and February`, `in January, February and March`, `before March`, `after March`, `through February` (years from the season, or one named year: `from March 2025 to January` spans 2024-25 and 2025-26); `in January and March`, a backwards span and a range named for two seasons refuse, as does a yearless cut over several seasons (`before March in the last 3 seasons`); `in / for / over the month of March` is `in March`; `in March vs April` / `in March or April` refuse, as do landmarks the dates do not place (`after Christmas`, `before the All-Star break`, `since the trade deadline`, `after Thanksgiving`, `since New Year's`; `since / after the All-Star break` reads as before)
- split views: `home vs away`, `home versus away`, `home vs road`, `home and away record`, `wins vs losses`, `wins versus losses`, `in wins and losses`, `by month`, `month by month`, `monthly`, `best month`, `worst month`, `best scoring / shooting / 3 point shooting month`, `which month did he score the most`, `this season vs last season`, `2023-24 vs 2024-25` (season split)

### 2.4 Threshold language

- `over 25 points`
- `under 10 turnovers`
- `between 20 and 30 points`
- `25+ points`
- `5+ threes`
- reverse phrasing for some stats: `ts% over .600`, `efg% under .500`
- opponent shooting on team game lists and counts: `games where the opponent shot under 45 percent`, `opponents shot over 50% from three`, `under 75 percent from the line / the stripe`, `held opponents to under 47.5 percent shooting` (no operator after `held` is a ceiling); team records and player game lists refuse, as do a second clause with no new subject (`... and scored under 100`, `..., 35 percent from three`) and an unknown area (`from the corner`)
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

A league-wide count of `player games` counts player-game rows, while `distinct players`
counts identities. Strict `above` and `exceeded` exclude equality, as `over` does.
A leading season scope is also accepted for grouped OR lists; the display limit
is applied after evaluating the complete condition, rather than cutting the base sample.

### Team count

Examples:

- `how many Celtics games with 120+ points and 15+ threes since 2022`
- `count Lakers home wins vs Warriors since 2021`
- `how often have the Lakers held opponents under 100 points this year`
- `how many times did the Lakers win by 20` (a bare margin of 10 or more is a
  floor: every 20+ win; `won by 1` and `won by exactly 20` stay exact)
- `how many times did the Lakers beat the Celtics by 20`,
  `how many times did the Celtics lose to the Knicks by 10 or more`

### Boolean count

Top-level and parenthesized boolean finder conditions preserve count intent and
return the same count envelope for equivalent expressions.

Examples:

- `how many LeBron games over 20 points or over 10 assists in 2024-25`
- `how many LeBron games (over 20 points or over 10 assists) in 2024-25`

### Count intent phrases

Common triggers:

- `how many`
- `how often`
- `count`
- `number of`
- `total games`

A count of zero is returned only after the requested route and filters were
fully evaluated and produced an explicit `no_match`. Missing data, unavailable
filter coverage, unsupported concepts, ambiguity, routing failures, and engine
errors remain non-success results with their original reason and no count
section. In particular, adding count phrasing never turns an unsupported
clutch filter into zero or into a broad unfiltered count.

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
- explicit-matchup two-player played conjunctions for team records: `Lakers record against Celtics with Jayson Tatum playing while Austin Reaves plays in 2023-24`; AND/shared-playing and comma forms preserve both predicates. Each player may be on the subject or opponent team, independently qualified by the same game's team/date identity. Every original candidate game needs qualified evidence for both players, including a genuine empty answer. A missing observation is unavailable, not proof of DNP or nonmembership. Player-owned stat/status clauses, mixed polarity and broader boolean compositions remain separate unfinished requirements.
- explicit last-N played-pair team records distinguish original and qualifying samples: `Lakers record against Celtics within their last 1 game with Jayson Tatum playing while Anthony Davis plays in 2023-24` selects the original meeting first, then qualifies both players; `among` and `of` window forms are equivalent; singular `within their last game` / `among their last meeting` means one original meeting, as does the explicit `in their last 1 original game`. `in their last 1 qualifying game` qualifies both players before selecting the most recent matching meeting. This bounded slice requires one explicit season, a whole-game matchup and exactly two resolved played predicates. Opponent/venue/date context chooses the candidate games before either selection. Other consumers/compositions remain unfinished. Bare new separate-predicate last-N requests retain their containment; default native cooperative and legacy structured window behavior remain cohort-first.
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
- `player_on_off` is a shipped coverage-gated route, not an execution placeholder
- whole-game `with_player` / `without_player` availability is not an on/off substitute
- qualified original-matchup minutes: `Did Anthony Davis play at least 30 minutes in the Lakers last game against Celtics in 2023-24?` answers No because Davis did not play on February 1, retaining that original team game. `Did Tatum play fewer than 37 minutes in the Celtics last game against Lakers in 2023-24?` answers Yes using the report's 36:37 rather than rounded 37; `Did Brown play over 27 minutes` in that same scope uses 27:24. One complete player/time check and explicit latest named matchup are supported; the table is team-game evidence and the Minutes check names the athlete separately. Precise report time or game-day qualification missing means unavailable, not player zero or an older appearance. Broader original stat compositions remain unfinished; native bare statistical minutes and AND/OR/outcome paths are preserved.
- qualified original-matchup minutes AND count: `Did Payton Pritchard play at least 21 minutes and have at least 1 assist in the Celtics last game against Lakers in 2023-24?` answers Yes on February 1 using official21:18 and recordedAST1; changing the count to fewer than1 answers No, while at most0rebounds is Yes from recordedREB0. Reversed predicate order, RECORD/HAVE verbs and one count range retain both same-player checks. Davis's explicit DNP on that original game means No without player zeros or a Christmas substitute. Both required played fields must be known even if another predicate fails; the displayed row remains team evidence with separate Minutes check and Count check labels. Original OR, outcomes, additional owners, periods and broader compositions remain unfinished. Native bare MIN-first complete HAVE/RECORD AND checks use their existing appearance-stat contract; count-first native bare questions remain a valid unfinished ordering case.
- scalar latest-original played checks: `Did Jayson Tatum play in the Celtics last game against Lakers in 2023-24?` answers Yes on February 1; `Did Anthony Davis play in the Lakers last game against Celtics in 2023-24?` answers No on that original game. The target identity remains separate from the displayed team-game evidence; DNP does not fabricate player zeros. Missing observations are unavailable, not omission-based No. Bare legacy positive answers remain qualified by exact same-game identity, and a team inferred from a previous appearance is only a candidate rather than known current membership. No new last-night/freshness, medical, on-court, qualifying or multi-game meaning is claimed.
- latest original matchup BOTH-played checks: `Of the Lakers last game against Celtics in 2023-24, did BOTH Jayson Tatum and Anthony Davis play?` answers No for February 1; replacing Davis with Austin Reaves answers Yes. `Did both Tatum and Reaves play in the Lakers latest game against Boston in 2023-24?` keeps the same original game. Both names are qualified on that game's canonical side/date before rendering; A No answer means at least one player did not play; it does not imply that neither played. One explicit regular season, subject/opponent and two whole-game PLAYED checks are required; playoff wording remains unfinished. Missing evidence is unavailable, not No. Latest-qualifying Boolean, multiple games, health/on-court/status and additional unread conditions remain unfinished; scalar participation checks use the same qualified original-game selection at one-name arity.
- whole-game two-teammate conjunctions support `with A and B`, `without A and B`, and explicit participation suffixes `both out`, `not playing`, `DNP` or `both playing`; a stat bound on the primary team/player may accompany the pair. Each absence predicate needs qualified evidence across the original candidate sample; an unrelated omitted player row is insufficient. Mixed with/without predicates, OR scopes, medical/status meaning and on-court presence are separate unfinished capabilities, not a broad unfiltered fallback

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

A shared historical team sample is supported with two resolved players, one
explicit regular season and optionally one scalar opponent. For example,
`Compare Luka Doncic and Anthony Davis for the Lakers against the Warriors in
2024-25` compares Dončić's one Lakers appearance (19PTS/8REB/7AST) with Davis's
two (18PTS/7.5REB/1.5AST per game). `How did ... compare for the Lakers ...?`,
reversed names and complete playing-for wording preserve both subjects. These
are independent appearance samples, not games where both played together.
A conditional medical/status owner does not replace the primary subject:
`Boston record against Lakers in 2025-26 when Derrick White is medically cleared`
retains the Boston record request and reports unavailable qualified status data.
The same condition on an Embiid/Jokic comparison retains both players. No medical
filter is delivered, no reduced unfiltered answer runs, and participation never
establishes clearance/health or an absence reason. Existing played/unfiltered
questions keep their source-backed answers.

Historical `Playing for` and `Opponent` labels keep the sample visible. Complete
common date/venue and integer-count filters apply before summarizing; decimal
count cutoffs keep exact strictness with explicitly labeled equivalent integer
execution. Unknown/ambiguous operands or unread clauses cannot become a
single-player result. Different team filters per player, shared-team opponent
unions and rate/time filtering in this new scope remain unfinished; the existing
unfiltered comparison families retain their tested semantics.

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
- `LeBron points per game by month`, `Curry 3 point shooting by month`
- `best month for LeBron` (most points per game), `LeBron best 3 point shooting month`,
  `which month did LeBron have the most 30 point games`

A month split has one row per calendar month of one year (`March 2026`), so a
span keeps each year's months apart. Rates are the month's totals (makes over
attempts); counting stats show the per-game average and the month's total. A
ranked month ("best month") answers with the top month and names every tie;
months with none of the filtered games are not rows, so "fewest" qualifying
games is not read off the split. "which month did he score the most points" ranks the
month's total ("average the most" ranks per game). Comparisons (`LeBron vs
Curry by month`), leaders (`Lakers leading scorer by month`) and a team asked
about in a player's games refuse rather than drop the month.

### Team split

Examples:

- `Celtics home vs away`
- `Celtics wins vs losses`
- `Lakers playoff home vs away since 2020`
- `Lakers home vs road`, `Lakers home and away record`
- `Lakers record by month`, `Lakers best month` / `worst month` (by record;
  ties on percentage go to more wins / more losses), `Lakers highest scoring
  month`, `which month did the Lakers win the most games` (every game counts)

### Season splits

Examples:

- `Lakers record this season vs last season`, `LeBron stats this season compared to last season`
- `Lakers record 2025-26 vs 2024-25`, `LeBron 2015-16 vs 2017-18`
- `Lakers record in 2016 and 2020`, `Celtics record in 2023-24, 2024-25 and 2025-26`
- `how many 30 point games did LeBron have this season vs last season`

Two or more named seasons (explicit seasons, bare years read as the season
ending in them, "this / last season", joined by vs, versus, compared to,
than, and, or, commas) split one player's or one team's sample one row per
season; seasons between them are left out ("2023-24 vs 2025-26" skips
2024-25). Two consecutive bare years joined by "and" ("in 2024 and 2025") stay
the span they read as. Comparisons, leaderboards, game lists, a second split
or a last-N window with named seasons refuse rather than pool the seasons or
answer one of them; months or playoff rounds named for two seasons keep their
refusals.

---

## 3.6 Leaderboard queries — rank players or teams league-wide

### Player leaderboards

Examples:

- `top scorers this season`
- `highest ts% among players`
- `best three point shooters`, `best free throw shooters`, `Lakers best three point shooters`: 3P% / FT% with the attempt floor (a bare `best shooters` is not guessed)
- `most 30 point games`
- player season boards need 20 games for a per-game average or rate (capped at half the most games anyone has played, so early-season boards are not empty); season totals (`most total points this season`) need one game
- `how many players scored 2000 points`, `players with 1,000 points this season`,
  `players with 500 rebounds`, `how many Lakers players have 1000 points`,
  `players with 2000 points in a season since 2010`: every player whose season
  total (or combined total over a named span) reaches a number no single game
  has; `how many` counts players and lists them
- `players with 25 points and 10 rebounds` / `players with 30 point games` / `players with a triple double` (every player with a qualifying game, most often first, no top-10 cut; a bare `players with 30 points` is not read as games)
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
- `personal foul` / `PF` means personal fouls committed, while `minutes` means
  total minutes played; both execute as their named leaderboard stat and never
  fall back to points
- existing public per-game semantics remain unchanged for aliases such as
  points per game, rebounds per game, assists per game, steals per game,
  blocks per game, turnovers per game, plus-minus per game, and made threes
- over a span of seasons, "most" a counting stat (points, rebounds, assists,
  threes, steals, blocks, turnovers) ranks the total: `most career points`,
  `most playoff points all time`, `most rebounds in the 2010s`, `all time
  scoring leaders`; "per game" or "average" keeps the rate, and one-season
  questions and single-season boards are unchanged

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
- `teams with the best 3 point percentage minimum 3000 attempts` / `best team free throw percentage minimum 25 attempts per game` (a stated attempt minimum, season total or per game, replaces the default attempt floor; caveat `qualified: at least ...`; a minimum on a non-rate team stat still refuses)
- `team fg%` (team stat alias → fg_pct)
- `team ft%` (team stat alias → ft_pct)
- `What teams have the best net rating this year?`
- `What team has the highest offensive rating this season?`
- `best defensive rating teams this season`
- `fastest pace teams this season`
- `which teams beat the Lakers this season` (every team with a win against
  them), `which teams beat the Lakers twice`, `who did the Celtics beat in 2024-25`,
  `teams the Lakers lost to`, `which teams have beaten the Celtics the most`

Leaderboard no-match behavior:

- if data exists but the requested date/context/sample filters leave no games in scope, leaderboard routes return `no_match` rather than falling back to a broader leaderboard
- rolling/date-window team advanced rating leaderboards and undefined skill concepts
  such as catch-and-shoot, drawing fouls, transition scoring, isolation defense,
  shot creation, salary/contract questions, multi-player co-occurrence, and
  attempt minimums on anything but a shooting-rate leaderboard are unsupported
  boundaries; they return a typed
  `no_result` / `filter_not_supported` response with
  `metadata.unsupported_filters=["unsupported_concept"]` and no answer rows
- rookie leaderboards (`rookie scoring leaders`, `rookie assist leaders this
  season`) are supported **when the question names a stat**: players are
  filtered to roster experience of 0 years in each season, with roster coverage
  from 1996-97. A rookie ranking that names no stat (`top rookies this season`,
  `rookie leaders this season`) returns `no_result` / `filter_not_supported`
  with `metadata.unsupported_filters=["leaderboard_metric_required"]` — a
  population says who to rank, never what to rank them by, and there is no
  default metric. The same holds for sophomore, starter and bench
  leaderboards. Seasons without roster
  data return `no_result` / `filter_not_supported` rather than an unfiltered
  leaderboard
- sophomore leaderboards (`sophomore scoring leaders`, `second-year
  assist leaders`) are supported the same way, filtered to roster
  experience of 1 year per season
- team-scoped player leaders (`Lakers leading scorer`, `who scores the
  most for the Celtics`, `Celtics leader in assists`, `who has the best
  plus minus on the Lakers`, `who has the highest ppg on the Lakers`,
  `top 3 Lakers players in rebounds`) are supported: they rank that
  team's players for the stat per game, leader first ("best" a game:
  `which Lakers player had the highest scoring game` lists player games;
  `best scoring season by a Lakers player` is not this board). The
  subjective `best player on the Lakers` is not supported (no objective
  metric) and refuses
- two-player combined totals (`luka and kyrie combined points`) are not
  supported and refuse rather than answer for one player
- league-wide starter/bench player leaderboards (`most points off the
  bench`, `top scorers among starters`) are supported using trusted
  per-game starter-role data; seasons without trusted coverage return
  `no_result` / `filter_not_supported` rather than an unfiltered
  leaderboard
- fouls-drawn wording is not mapped to personal fouls committed; drawing-foul
  queries remain unsupported until a fouls-drawn data contract exists
- league-wide team advanced-stat leaderboards for net rating, offensive rating,
  defensive rating, and pace are supported
- single-team season advanced-stat scalar asks (`Warriors net rating this
  season`, `wolves defensive rating`, `kings pace`) are supported: they route
  to the full team leaderboard and the backend answer phrase pinpoints the
  team's value and league rank. Date-windowed, season-range, opponent, and
  home/away/wins/losses variants remain unsupported boundaries
- league-wide threshold game lists (`who dropped 40 this week`, `who scored
  50+ points this season`) are supported through `top_player_games` with a
  minimum-value filter; every qualifying game is listed

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
- `Celtics longest streak holding opponents under 100`
- `Lakers winning streaks of 5 or more games` (every run that long)

### Streak counts

A stated length with "how many" counts every separate run at least that
long (a 12-game streak is one 10+ game streak). Without a team or player it
counts the teams or players who had a run that long. "how many games was
the longest streak" stays a streak answer. A stated span ("since 2024")
replaces the three-season default.

- `how many 10 game winning streaks do the Celtics have`
- `how many times did the Lakers win 5 straight this season`
- `how many times has Curry had 5 straight games with a three`
- `how many players have had 5 straight 20 point games this season`
- `how many teams have had a 10 game winning streak this season`

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
- `record against Northwest Division teams`
- `best record against Atlantic Division teams`
- `team records vs Pacific Division`
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
- `LeBron playoff series record`, `how many playoff series has LeBron won`,
  `LeBron Finals series record`, `LeBron series wins against the Celtics`: the
  series his teams played in which he appeared, every playoff season served
  (since 1996-97) unless a span is named; game records are the team's
  (one player at a time; a single-game condition such as "when he scores 30"
  is refused rather than dropped)

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

- `how many times have the Lakers made the playoffs since 2000`
- `did the Celtics make the playoffs this season`
- `when did the Knicks last make the conference finals`
- `Lakers consecutive playoff appearances` / `Kings playoff drought`
- `most consecutive playoff appearances`
- `how many Finals appearances does LeBron have` / `which player has the most Finals appearances`

An appearance is a season with at least one game at that stage (play-in games
excluded). Teams count per franchise (Seattle seasons count for the Thunder).
A player's appearance needs a game he played (minutes > 0). Runs and droughts
count the seasons the franchise played, up to the latest postseason in range,
from 1996-97 where the data starts. "against teams that made the playoffs"
stays an opponent filter.

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
shipped support covers single-team playoff history, team playoff appearances,
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
- `teams with most games scoring 120+ and making 15+ threes since 2020`
- `most games with 3+ steals and 2+ blocks`
- `how many Celtics games vs Bucks with 120+ points and under 10 turnovers`

A verb can carry the stat with the noun left out, so `scoring 120+` and
`grabbing 10+` state a condition just as `120+ points` does.

These rank by a **count of matching games**, published as
`metadata.ranking_key="occurrence_count"`. No threshold metric is published as
`metadata.stat`: every threshold here is a condition being counted, not the key
the rows are ordered by.

Compound no-match behavior:

- a compound/event request the selected route cannot execute in full returns
  `no_result` / `filter_not_supported` with
  `metadata.unsupported_filters=["compound_event_request_unexecutable"]`, no
  answer rows, and no executed `stat`. The refusal carries what was asked for
  in `metadata.requested_event_conditions` (whole or not at all),
  `metadata.requested_stat`, and `metadata.unsupported_availability`
- `most efficient 30-point games` refuses this way: "efficient" resolves to the
  documented `ts_pct` alias, and no route ranks individual games by it. It does
  not become a 30-point-game count, a points leaderboard, or another efficiency
  metric
- `most 40-point games while the player was injured` refuses this way: the
  40-point condition is preserved and injury status is named as unavailable.
  Injury is never inferred from missed games or any other proxy
- `Lakers leading scorer while LeBron was out` refuses with the Lakers still the
  subject and LeBron's absence preserved in
  `metadata.unsupported_availability`. It does not return a LeBron summary or an
  unfiltered Lakers scoring leaderboard

See [`../architecture/parser/compound_event_routing.md`](../architecture/parser/compound_event_routing.md).

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
  only when raw play-by-play covers every requested base game and every
  qualifying event key has the exact derived clutch window
- one missing/untrusted PBP game or derived clutch key returns `no_result` /
  `filter_not_supported` with exact coverage detail rather than a partial answer
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
  requested slice; one missing entity-game key for the requested window returns
  `no_result` / `filter_not_supported` with exact key/window detail
- other routes, such as period leaderboard phrasing, return typed
  `no_result` / `filter_not_supported` because the current period-backed route
  boundary does not extend beyond `player_game_finder` / `team_record`
- broader period route expansion is out of scope for the core finish line unless
  a future product queue reopens it

### Back-to-back filter

Examples:

- `Lakers on back-to-backs record`
- `Lakers b2b record`

Current behavior:

- parser sets `back_to_back=True` and preserves the filter in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter through `schedule_context_features` when coverage exists
- unsupported routes or missing coverage return typed `no_result` /
  `filter_not_supported`
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### Rest filter

Examples:

- `Jokic with rest advantage`
- `Jokic on 2 days rest`

Current behavior:

- parser sets `rest_days` to `advantage`, `disadvantage`, or an integer day count and preserves it in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter through normalized `schedule_context_features.rest_days` / `rest_advantage` when coverage exists
- unsupported routes or missing coverage return typed `no_result` /
  `filter_not_supported`
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### One-possession filter

Examples:

- `Celtics one-possession record`
- `Thunder one-possession games`

Current behavior:

- "one-possession games", "games (decided) within one possession" and
  "one-possession wins / losses / record" read a final margin of 3 or fewer
  from the score, like "close games" (5 or fewer), so every season and every
  route that reads a margin answers: records, game lists and counts, player
  summaries, comparisons, splits, streaks and team record boards
- "excluding / outside of / non- one-possession games" are decided by 4+;
  "excluding close games" by 6+ and "non-blowout games" by 14 or fewer
- a bare "within one possession", a score during the game ("... in the final
  minute", "in the 4th quarter"), a team after "losses to" and a comparison
  with another margin ("one possession games vs close games") keep
  `one_possession=True`, as does a question whose stat bound or number the
  margin reading would drop ("with 10 reb", "when LeBron gets 30"), which `team_record` and `player_game_summary` execute
  through `schedule_context_features.one_possession` when coverage exists;
  other routes or missing coverage return typed `no_result` /
  `filter_not_supported`
- the schedule-context build derives `one_possession` from the two rows'
  points, not the stored team plus-minus

### National-TV filter

Examples:

- `Knicks on national TV record`
- `Lakers nationally televised games`

Current behavior:

- parser sets `nationally_televised=True` and preserves the filter in `route_kwargs`
- `team_record` and `player_game_summary` execute the filter only when `schedule_context_features.national_tv_source_trusted=1`
- current schedule pulls can still leave national-TV coverage untrusted; in that
  case execution returns typed `no_result` / `filter_not_supported`
- broader schedule-context route expansion is out of scope for the core finish
  line unless a future product queue reopens it

### Starter / bench role

Examples:

- `LeBron as a starter stats`
- `Brunson off the bench`

Current behavior:

- parser sets `role` for player-context queries only
- `player_game_summary` and `player_game_finder` apply starter / bench filtering only when the requested slice has complete trusted coverage in `player_game_starter_roles`
- if trusted starter-role coverage is missing or untrusted for any row in the
  requested slice, execution returns `no_result` / `filter_not_supported` with
  exact key detail instead of partially filtering
- `season_leaders` uses the same exact trusted player-game gate; team-level
  bench scoring remains an explicit unsupported boundary that returns
  `no_result` / `filter_not_supported`

### Opponent-quality filter

Examples:

- `Jokic against contenders 2024-25`
- `Lakers record against top-10 defenses 2024-25`
- `KD TS% vs top defenses`
- `Celtics record against playoff teams`
- `Celtics record against teams that made the playoffs`
- `Thunder record vs top 10 teams`
- `Celtics record vs top 5 teams`
- `Bucks record against losing teams`
- `Suns record vs bad teams`
- `Mavericks record against West playoff teams`

Current behavior:

- parser sets a structured `opponent_quality` slot containing the surface term and resolved bucket definition
- execution resolves that bucket to a concrete opponent-team list on the supported single-entity summary/finder/record routes
- team-record opponent-quality filters cover `top 10 teams`, `top 5 teams`,
  `top seeded teams`, `winning teams`, `losing teams`, `teams over .500`,
  `teams under .500`, `teams .500 or worse`, `playoff teams`, `non-playoff teams`,
  `good teams`, and `bad teams`
- conference-plus-quality team-record filters such as `West playoff teams`,
  `Eastern Conference playoff teams`, and `East top 10 teams` are supported by
  intersecting the conference and quality opponent-team sets
- `top defenses` is accepted as shorthand for `top-10 defenses` only in explicit opponent context such as `against`, `vs`, or `versus`
- `playoff teams` includes postseason-team phrasings such as `postseason
  teams` and `teams that made the playoffs`; `non-playoff teams` includes
  `non playoff teams` / `non-playoff teams`; both remain regular-season
  opponent-quality contexts unless the query also explicitly asks for playoff
  competition
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
- no-subject opponent-division record leaderboard filters such as `record
  against Northwest Division teams`, `best record against Atlantic Division
  teams`, and `team records vs Pacific Division` are supported for
  regular-season `team_record_leaderboard` queries in trusted seasons `2024-25`
  and `2025-26`
- the resolved division list keeps all five division members, including the
  subject team when applicable; this has no effect because teams do not play
  themselves
- east/west geography phrases such as `east coast teams` and seasons outside
  trusted conference or division coverage remain unsupported and return
  `no_result` / `filter_not_supported` instead of broad full-season records
- mixed conference plus division text does not return a broader
  conference-only or division-only answer
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
