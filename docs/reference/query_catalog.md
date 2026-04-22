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

When this catalog marks a family as parser-recognized but still unfiltered or placeholder-backed, that note reflects current shipped behavior only. The active execution/data continuation for those families is tracked in [parser_execution_completion_plan.md](../planning/parser_execution_completion_plan.md) and [phase_g_work_queue.md](../planning/phase_g_work_queue.md).

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
- team name/alias: `Lakers`, `LAL`, `Celtics`, `Sixers`, `Wolves`
- player vs player: `Jokic vs Embiid`
- team vs team: `Celtics vs Bucks`

### 2.2 Time/context filters

- explicit season: `2025-26`
- season range: `from 2021-22 to 2023-24`
- since season/year: `since 2020`, `since 2020-21`
- last N seasons: `last 3 seasons`
- career / all-time: `career`, `all-time`
- last N games: `last 10 games`
- rolling windows: `3-game stretch`, `5-game scoring stretch`, `rolling 10-game stretch`
- month / date windows: `in March`, `since January`, `since All-Star break`, `last 30 days`
- fuzzy time words: `lately`, `recently` (→ last 10 games), `past month`, `last month` (→ rolling 30 days), `last couple weeks`, `past 2 weeks` (→ rolling 14 days)
- single-day: `last night`, `yesterday`, `today`, `tonight`
- season type: `playoffs`, `postseason`

### 2.3 Sample filters

- opponent (team): `vs Lakers`, `against Celtics`
- opponent (player): `vs Kevin Durant`, `against Stephen Curry` (when used with context words like "stats", "averages", "record")
- without player: `without LeBron`, `w/o LeBron`, `when LeBron out`, `when LeBron was out`, `when LeBron didn't play`, `no LeBron`, `sans LeBron`, `minus LeBron`
- on/off presence: `on/off`, `with Jokic on the floor`, `without Jokic on the floor`, `Jokic sitting`
- lineup membership: `lineups with LeBron and AD`, `with Tatum and Brown together`, `best 3-man units`
- rolling-window phrasing: `hottest 3-game stretch`, `best 5-game stretch by Game Score`, `rolling 10-game stretch`
- head-to-head: `head-to-head`, `h2h`
- home / away: `home`, `away`, `road`
- wins / losses: `wins`, `losses`, `won`, `lost`
- clutch context: `clutch`, `in the clutch`, `clutch time`, `late-game`
  (parser-recognized and route-propagated; current query engine returns unfiltered
  results with an explicit note because play-by-play clutch splits are not available yet)
- period context: `1st quarter`, `4th quarter`, `first half`, `second half`, `overtime`, `OT`
  (parser-recognized and engine-accepted; current game-log data returns unfiltered
  full-game results with an explicit note because period splits are not available yet)
- schedule context: `back-to-back`, `b2b`, `rest advantage`, `rest disadvantage`, `2 days rest`, `one-possession games`, `nationally televised`, `on national TV`
  (parser-recognized and engine-accepted; current query engine returns unfiltered
  results with an explicit note because schedule/context feature tables are not yet joined)
- role context: `as a starter`, `starting`, `off the bench`, `bench`, `reserve`
  (parser-recognized and engine-accepted for player queries; current query engine returns
  unfiltered results with an explicit note because starter/bench filtering is not yet wired in;
  team-only phrases like `Celtics bench scoring` are intentionally ignored)
- opponent-quality context: `against contenders`, `against good teams`, `vs top teams`, `against playoff teams`, `against teams over .500`, `against top-10 defenses`
  (resolved to concrete opponent buckets on the supported single-entity summary/finder/record
  routes using the latest regular-season standings or team-advanced data for the selected season;
  unsupported routes append an explicit note and remain unfiltered)
- split views: `home vs away`, `home versus away`, `wins vs losses`, `wins versus losses`, `in wins and losses`

### 2.4 Threshold language

- `over 25 points`
- `under 10 turnovers`
- `between 20 and 30 points`
- `25+ points`
- `5+ threes`
- reverse phrasing for some stats: `ts% over .600`, `efg% under .500`

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
| `tov`          | `tov`, `turnover`, `turnovers`                                                                                                                                                       |
| `minutes`      | `minutes`                                                                                                                                                                            |
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
- `what games did Tatum have over 35 points and 5+ threes`
- `Cade Cunningham season high` (routes to top single games for the player)
- `LeBron best game this season`

### Team finder

Examples:

- `Celtics wins vs Bucks over 120 points`
- `show me Lakers home losses`
- `list Thunder games with 15+ threes`
- `find Knicks games vs Heat since 2021`

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

### Count intent phrases

Common triggers:

- `how many`
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
- `How has Jayson Tatum played against winning teams this season?` (verb-phrase question form → summary)
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
- home / away
- wins / losses
- season ranges
- career / all-time
- playoff-only spans
- date windows / recent form

### On/off placeholder summaries

Examples:

- `Jokic on/off`
- `Nuggets with and without Jokic`
- `with Curry on the floor`
- `without Giannis on the floor`

Current behavior:

- parser routes to `player_on_off`, preserves `lineup_members` and `presence_state`, and returns an explicit unsupported-data note until play-by-play or stint-level on/off tables are available

### Specific lineup summaries

Examples:

- `lineups with LeBron and AD`
- `lineup with Tatum and Brown together`
- `2-man combos with Brunson and Hart`

Current behavior:

- parser routes to `lineup_summary`, preserves `lineup_members`, `presence_state`, `unit_size`, and `minute_minimum`, and returns an explicit unsupported-data note until lineup tables are available

---

## 3.4 Comparison queries — compare two players or two teams

### Player comparison

Examples:

- `Jokic vs Embiid recent form`
- `Jokic vs Embiid since 2021`
- `Jokic head-to-head vs Embiid since 2021`
- `Kobe vs LeBron playoffs in 2008-09`

### Team comparison

Examples:

- `Celtics vs Bucks from 2021-22 to 2023-24`
- `Lakers vs Celtics since 2010`
- `Knicks head-to-head vs Heat since 1999`
- `Celtics vs Bucks home`

### Comparison support notes

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
- `highest scoring games this season` (routes to top_player_games, not ppg leaderboard)
- `who leads the NBA in points per game` / `who leads the league in assists` (question form; routes to leaderboard)
- `points leaders last 10`, `last 10 scoring leaders`, `top scorers last 10 games` (shorthand → `season_leaders`, stat=pts, last_n=10)
- `Who scores the most at home this season?` / `most points at home this season` (leaderboard + home filter)

### Team leaderboards

Examples:

- `best offensive teams`
- `teams with best efg%`
- `teams with most threes`
- `most wins since 2015`
- `best record since 2015`
- `worst away record since 2020`
- `best scoring teams vs Lakers since 2018`
- `best team 3 point percentage` (team stat alias → fg3_pct)
- `team fg%` (team stat alias → fg_pct)
- `team ft%` (team stat alias → ft_pct)

Leaderboard no-match behavior:

- if data exists but the requested date/context/sample filters leave no games in scope, leaderboard routes return `no_match` rather than falling back to a broader leaderboard

### Position-filtered leaderboards

Examples:

- `best ts% among centers this season`
- `top scorers among guards since 2021`
- `best rebounders among big men`

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

### Lineup leaderboards

Examples:

- `best 5-man lineups`
- `best 3-man units with at least 200 minutes`
- `top 2-man combos`

Current behavior:

- parser routes to `lineup_leaderboard`, preserves `unit_size` and `minute_minimum`, and returns an explicit unsupported-data note until lineup tables are available

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
- `best home record over the last 5 seasons`
- `worst away record since 2020`
- `Celtics record when scoring 120+ since 2022`
- `Lakers record without LeBron James`
- `Warriors wins without Stephen Curry`

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

---

## 3.9 Playoff / era-history queries

### Playoff history

Examples:

- `Lakers playoff history`
- `Celtics finals record`
- `Heat vs Knicks playoff history`
- `Lakers playoff series record vs Celtics`

### Playoff appearances / rounds

Examples:

- `finals appearances`
- `Warriors conference finals appearances`
- `most Finals appearances since 1980`
- `most conference finals appearances since 2000`
- `best finals record since 1980`
- `best second round record`
- `LeBron record in the Finals`

### By-decade / era-bucket queries

Examples:

- `Warriors record by decade`
- `winningest team of the 2010s`
- `Lakers vs Celtics by decade`

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

- parser sets `clutch=True`, routes normally, and appends an explicit unfiltered-results note because play-by-play clutch splits are not available yet

### Quarter / half / overtime context

Examples:

- `LeBron 4th quarter scoring`
- `Celtics first half record`

Current behavior:

- parser sets `quarter` / `half`, routes normally, and appends an explicit unfiltered-results note because current game-log data does not expose period splits

### Back-to-back filter

Examples:

- `Lakers on back-to-backs record`
- `Lakers b2b record`

Current behavior:

- parser sets `back_to_back=True`, preserves the filter in `route_kwargs`, and execution appends an explicit unfiltered-results note until schedule/context joins land

### Rest filter

Examples:

- `Jokic with rest advantage`
- `Jokic on 2 days rest`

Current behavior:

- parser sets `rest_days` to `advantage`, `disadvantage`, or an integer day count, preserves it in `route_kwargs`, and execution appends an explicit unfiltered-results note

### One-possession filter

Examples:

- `Celtics one-possession record`
- `Thunder one-possession games`

Current behavior:

- parser sets `one_possession=True`, preserves the filter in `route_kwargs`, and execution appends an explicit unfiltered-results note

### National-TV filter

Examples:

- `Knicks on national TV record`
- `Lakers nationally televised games`

Current behavior:

- parser sets `nationally_televised=True`, preserves the filter in `route_kwargs`, and execution appends an explicit unfiltered-results note

### Starter / bench role

Examples:

- `LeBron as a starter stats`
- `Brunson off the bench`

Current behavior:

- parser sets `role` for player-context queries only and appends an explicit unfiltered-results note until starter/bench filtering is wired through execution

### Opponent-quality filter

Examples:

- `Jokic against contenders 2024-25`
- `Lakers record against top-10 defenses 2024-25`

Current behavior:

- parser sets a structured `opponent_quality` slot containing the surface term and resolved bucket definition
- execution resolves that bucket to a concrete opponent-team list on the supported single-entity summary/finder/record routes
- unsupported routes append an explicit note and remain unfiltered

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
