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

- player name: `Jokic`, `Nikola Jokić`, `LeBron`, `SGA`
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
- month / date windows: `in March`, `since January`, `since All-Star break`, `last 30 days`
- season type: `playoffs`, `postseason`

### 2.3 Sample filters

- opponent: `vs Lakers`, `against Celtics`
- head-to-head: `head-to-head`, `h2h`
- home / away: `home`, `away`, `road`
- wins / losses: `wins`, `losses`, `won`, `lost`
- split views: `home vs away`, `wins vs losses`

### 2.4 Threshold language

- `over 25 points`
- `under 10 turnovers`
- `between 20 and 30 points`
- `25+ points`
- `5+ threes`
- reverse phrasing for some stats: `ts% over .600`, `efg% under .500`

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

---

## 3.3 Summary queries — aggregate one player or one team over a sample

### Player summary

Examples:

- `Jokic recent form`
- `Jokic last 15 games summary`
- `Jokic summary vs Lakers`
- `Jokic since 2021`
- `LeBron career`
- `Jokic playoff stats vs Suns since 2021`

### Team summary

Examples:

- `Celtics last 15 games summary`
- `Knicks playoff summary vs Heat since 1999`
- `Lakers since 2020`
- `Warriors career vs Celtics`

### Summary context support

Common combinations:

- opponent filters
- home / away
- wins / losses
- season ranges
- career / all-time
- playoff-only spans
- date windows / recent form

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

### Team leaderboards

Examples:

- `best offensive teams`
- `teams with best efg%`
- `teams with most threes`
- `most wins since 2015`
- `best record since 2015`
- `worst away record since 2020`
- `best scoring teams vs Lakers since 2018`

### Position-filtered leaderboards

Examples:

- `best ts% among centers this season`
- `top scorers among guards since 2021`
- `best rebounders among big men`

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
- `Jokic consecutive games with a made three`
- `Jokic longest triple-double streak`

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

## 4. Structured CLI surface (high-level catalog)

NBA Tools also supports structured CLI queries through:

- `nbatools-cli query ...`

Representative structured routes include:

- `top-player-games`
- `top-team-games`
- `season-leaders`
- `season-team-leaders`
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
