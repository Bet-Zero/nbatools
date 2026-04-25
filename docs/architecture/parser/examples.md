# Parser Examples

> **Purpose of this doc:** The example library. Use this for test inputs, equivalence verification, and to see how real user language maps to the parser's canonical parse state. For framing, see [`overview.md`](./overview.md). For component specs, see [`specification.md`](./specification.md). For the living inventory of currently-shipped query shapes, see [`docs/reference/query_catalog.md`](../../reference/query_catalog.md).

When an example below carries an explicit unfiltered-results, coverage-gated, placeholder, or deferral note, that note describes current shipped behavior only. Part 2 execution/data closure is tracked in [`parser_execution_completion_plan.md`](../../planning/parser_execution_completion_plan.md).

---

## Table of contents

1. [How to use this doc](#1-how-to-use-this-doc)
2. [Canonical example set (100 queries)](#2-canonical-example-set-100-queries)
3. [Paired examples: question form vs search form](#3-paired-examples-question-form-vs-search-form)
4. [Examples by capability cluster](#4-examples-by-capability-cluster)
5. [Stress test inputs](#5-stress-test-inputs)
6. [End-to-end worked examples](#6-end-to-end-worked-examples)
7. [Equivalence groups](#7-equivalence-groups)
8. [Expansion patterns and explicit boundaries](#8-expansion-patterns-and-explicit-boundaries)

---

## 1. How to use this doc

This file serves three purposes:

- **Reference** — look up realistic query phrasings for a given intent category
- **Test inputs** — feed these directly into the parser's evaluation harness
- **Equivalence verification** — confirm that semantically identical queries produce identical parse states

### Sections 2 and 3 (baseline + pairs)

The 10 headings in §2 and §3 group queries by user-facing intent family. Each family maps to one or more of the repo's query classes (`finder`, `count`, `summary`, `comparison`, `split`, `leaderboard`, `streak`, `record`, `playoff`, `occurrence` — see [`specification.md` §4.1](./specification.md#41-query-classes)). The mapping isn't 1:1 because several user intent families (e.g., "best games") can route to multiple classes depending on modifiers.

### Section 4 (capability clusters)

Examples organized by repo query class — useful when you want to see a concentrated set of queries for a single class (all streaks, all occurrences, etc.).

### Section 5 (stress tests) and §7 (equivalence groups)

Direct inputs for the parser evaluation harness.

### Section 6 (worked examples)

Shows the full trace from raw text → parse state → route for representative queries.

---

## 2. Canonical example set (100 queries)

Baseline natural-language examples grouped by user-facing intent family.

### 2.1 Basic leaders and rankings

Primary class: `leaderboard`

1. Who leads the NBA in points per game this season?
2. Which players have the most total rebounds this year?
3. What team has the highest offensive rating this season?
4. Who is averaging the most assists per game right now?
5. Which centers have the most blocks this season?
6. What players have the best field goal percentage among guards?
7. Who has the most steals per game this year?
8. Which team has allowed the fewest points per game this season?
9. Who has the highest true shooting percentage this season?
10. What teams have the best net rating this year?

### 2.2 Recent / lately / last night / past month

Primary class: `leaderboard` or `summary` with fuzzy timeframe

1. Who scored the most points last night?
2. Which players have been the hottest from three lately?
3. Who has the most assists over the past month?
4. What team has played the best defense recently?
5. Who is averaging the most rebounds in the last 2 weeks?
6. Which players have been the most efficient recently?
7. What teams have the best record over the past month?
8. Who has had the most steals lately?
9. Which scorers have cooled off over their last 10 games?
10. What players have the most double-doubles recently?

### 2.3 Last N games / since date / over span

Primary class: `leaderboard` or `summary` with explicit windowed timeframe

1. Who is averaging the most points in his last 5 games?
2. Which team has the best net rating in its last 10 games?
3. Who has the most made threes in the last 7 games?
4. What players have averaged a double-double over their last 15 games?
5. Who has been the best rebounder since January 1?
6. Which teams have the best record since the All-Star break?
7. What players have the highest usage rate over their last 8 games?
8. Who is shooting the best from three since February 1 with at least 4 attempts per game?
9. What team has allowed the fewest paint points in its last 12 games?
10. Who has the most blocks since March 1?

### 2.4 Best games / biggest games / most efficient

Primary class: `leaderboard` (season-high variant) or `occurrence`

1. What were the biggest scoring games this season?
2. Which players had the best games by Game Score this year?
3. What are the highest assist games by a point guard this season?
4. Who has had the most efficient 30-point games this year?
5. What were the best rebounding games by a center this season?
6. Which players have the hottest 3-game scoring stretch this year?
7. What are the biggest triple-double games this season?
8. Who has the best shooting games with at least 25 points this year?
9. What are the most dominant games by plus-minus this season?
10. Which players have had the best two-way games this season?

### 2.5 Against good teams / top teams / contenders

Primary class: `summary` or `record` with opponent-quality filter _(shipped for the core single-entity summary/finder/record routes; unsupported routes carry an explicit note — see [`specification.md` §9](./specification.md#9-opponent-quality-filters))_

1. Who scores the most against teams over .500 this season?
2. Which team has the best record against contenders this year?
3. What players have the highest true shooting percentage against top-10 defenses?
4. How has Jayson Tatum played against good teams this season?
5. What is the Celtics' record against playoff teams?
6. Which players average the most assists against teams over .500?
7. What team has the best record against top teams this year?
8. Who rebounds the best against contenders?
9. Which scorers have the biggest drop-off against top-10 defenses?
10. What players have the most 30-point games against good teams this season?

### 2.6 When a teammate didn't play / was out

Primary class: `summary` or `record` with `without_player` filter

1. How do the Suns perform when Devin Booker didn't play?
2. What is the Bucks' record when Giannis Antetokounmpo was out?
3. Who averages the most points when their co-star didn't play this season?
4. How has Anthony Davis rebounded when LeBron James was out?
5. What is the Mavericks' offensive rating when Luka Dončić didn't play?
6. How does Jamal Murray score when Nikola Jokić is out?
7. What is the Knicks' record when Jalen Brunson doesn't play?
8. Which players see the biggest usage increase when their star teammate is out?
9. How has Tyrese Maxey played when Joel Embiid didn't play this season?
10. What team has stayed afloat best when its leading scorer was out?

### 2.7 "Who's been the best at **_ over _**"

Primary class: `leaderboard` with timeframe + skill filter

1. Who's been the best scorer over the last 10 games?
2. Who's been the best rebounder since January 1?
3. Who's been the best rim protector over the past month?
4. Who's been the best playmaker in the last 15 games?
5. Who's been the best catch-and-shoot shooter this season?
6. Who's been the best at drawing fouls over the past 20 games?
7. Who's been the best transition scorer this year?
8. Who's been the best isolation defender over the past month?
9. Who's been the best shot creator in clutch time this season?
10. Who's been the best offensive rebounder lately?

### 2.8 Frequency / how often

Primary class: `count` or `occurrence`

1. How often has Nikola Jokić recorded a triple-double this season?
2. How often has Stephen Curry made 5 or more threes this year?
3. How often has a team won when trailing after 3 quarters this season?
4. How often has Luka Dončić scored 40 or more this year?
5. How often has a player had 10+ assists and 0 turnovers this season?
6. How often have the Lakers held opponents under 100 points this year?
7. How often has Victor Wembanyama had 5+ blocks this season?
8. How often has a team scored 140 or more points this year?
9. How often has Jalen Brunson scored 30+ in his last 20 games?
10. How often has a road team won by 20+ this season?

### 2.9 Record when \_\_\_

Primary class: `record` with conditional filter

1. What's the Mavericks' record when Luka Dončić scores 35 or more?
2. What is the Knicks' record when they allow fewer than 110 points?
3. What is Denver's record when Nikola Jokić has a triple-double?
4. What's Boston's record when Jayson Tatum shoots under 40%?
5. What is the Lakers' record when LeBron James and Anthony Davis both play?
6. What's the Thunder's record when Shai Gilgeous-Alexander scores 30+?
7. What is Milwaukee's record when it wins the rebounding battle?
8. What's the Warriors' record when Stephen Curry makes at least 6 threes?
9. What is the Suns' record when Kevin Durant leads the team in scoring?
10. What's the Cavaliers' record when they score fewer than 105 points?

### 2.10 Splits and context filters

Primary class: `split` or context-filtered variants

1. Who scores the most at home this season?
2. Which teams have the best road record this year?
3. How does Anthony Edwards shoot in wins vs losses?
4. Who averages the most points in the first half this season?
5. Which players score the most in the 4th quarter?
6. What is the Lakers' record on back-to-backs this season?
7. Who has the best clutch field goal percentage this year?
8. What team has the best record in one-possession games this season?
9. Which players average the most points as a starter vs off the bench?
10. What is the Nuggets' net rating with Nikola Jokić on the floor vs off the floor?

---

## 3. Paired examples: question form vs search form

These pairs verify that the parser maps both phrasings to the same parse state. The 10 groups mirror the categories above.

### 3.1 Leaders and rankings

| #   | Question form                                             | Search / shorthand form                   |
| --- | --------------------------------------------------------- | ----------------------------------------- |
| 1   | Who leads the NBA in points per game this season?         | points per game leaders this season       |
| 2   | Which players have the most rebounds this year?           | most rebounds this year                   |
| 3   | Who has the highest true shooting percentage this season? | best true shooting percentage this season |
| 4   | Which team has the best offensive rating this year?       | best offensive rating team this year      |
| 5   | Who has the most assists over the last 10 games?          | most assists last 10 games                |

### 3.2 Recent / lately / past month

| #   | Question form                                          | Search / shorthand form    |
| --- | ------------------------------------------------------ | -------------------------- |
| 6   | Who scored the most points last night?                 | most points last night     |
| 7   | Which players have been the hottest from three lately? | hottest from 3 lately      |
| 8   | Who has been the best scorer over the past month?      | best scorers past month    |
| 9   | What team has played the best defense recently?        | best defense recently      |
| 10  | Who has the most double-doubles lately?                | most double doubles lately |

### 3.3 Last N games / since date

| #   | Question form                                                                              | Search / shorthand form                       |
| --- | ------------------------------------------------------------------------------------------ | --------------------------------------------- |
| 11  | Who is averaging the most points in his last 5 games?                                      | most points last 5 games                      |
| 12  | Which team has the best net rating in its last 15 games?                                   | best net rating last 15 games                 |
| 13  | Who has made the most threes since January 1?                                              | most threes since January 1                   |
| 14  | Which players have averaged a double-double over their last 10 games?                      | double double average last 10 games           |
| 15  | Who is shooting the best from three over the last month with at least 5 attempts per game? | best 3pt percentage last month min 5 attempts |

### 3.4 Best games / biggest games / most efficient

| #   | Question form                                                       | Search / shorthand form                 |
| --- | ------------------------------------------------------------------- | --------------------------------------- |
| 16  | What were the biggest scoring games this season?                    | biggest scoring games this season       |
| 17  | Which players have had the most efficient 30-point games this year? | most efficient 30 point games this year |
| 18  | What are the best rebounding games by centers this season?          | best rebounding games by centers        |
| 19  | Who has had the best all-around games this year?                    | best all around games this year         |
| 20  | What were the highest assist games by point guards this season?     | highest assist games by point guards    |

### 3.5 Against good teams / contenders

_Opponent-quality filters are shipped on the core single-entity summary/finder/record routes — see [`specification.md` §9](./specification.md#9-opponent-quality-filters)._

| #   | Question form                                                  | Search / shorthand form            |
| --- | -------------------------------------------------------------- | ---------------------------------- |
| 21  | Who scores the most against teams over .500 this season?       | most points vs teams over .500     |
| 22  | What team has the best record against contenders this year?    | best record vs contenders          |
| 23  | Which players shoot the best against top-10 defenses?          | best shooting vs top 10 defenses   |
| 24  | How has Jayson Tatum played against good teams this season?    | Tatum against good teams this season |
| 25  | What is the Celtics' record against playoff teams?             | Celtics record vs playoff teams    |

### 3.6 When a teammate didn't play

| #   | Question form                                                         | Search / shorthand form                 |
| --- | --------------------------------------------------------------------- | --------------------------------------- |
| 26  | How do the Suns perform when Devin Booker didn't play?                | Suns when Booker out                    |
| 27  | What is the Bucks' record when Giannis Antetokounmpo was out?         | Bucks record when Giannis out           |
| 28  | How has Anthony Davis rebounded when LeBron James didn't play?        | Anthony Davis rebounds when LeBron out  |
| 29  | What is the Mavericks' offensive rating when Luka Dončić didn't play? | Mavericks offensive rating without Luka |
| 30  | How has Tyrese Maxey played when Joel Embiid was out this season?     | Maxey when Embiid out this season       |

### 3.7 "Who's been the best at **_ over _**"

| #   | Question form                                           | Search / shorthand form                 |
| --- | ------------------------------------------------------- | --------------------------------------- |
| 31  | Who's been the best rebounder over the past month?      | best rebounder past month               |
| 32  | Who's been the best shot blocker in the last 10 games?  | best shot blocker last 10 games         |
| 33  | Who's been the best playmaker since the All-Star break? | best playmaker since all star break     |
| 34  | Who's been the best catch-and-shoot player this season? | best catch and shoot player this season |
| 35  | Who's been the best transition scorer lately?           | best transition scorer lately           |

### 3.8 Frequency / how often

| #   | Question form                                                        | Search / shorthand form              |
| --- | -------------------------------------------------------------------- | ------------------------------------ |
| 36  | How often has Nikola Jokić recorded a triple-double this season?     | Jokic triple doubles this season     |
| 37  | How often has Stephen Curry made 5 or more threes this year?         | Curry 5+ threes this year            |
| 38  | How often has Luka Dončić scored 40 or more this season?             | Luka 40+ point games this season     |
| 39  | How often have the Lakers held opponents under 100 points this year? | Lakers opponents under 100 this year |
| 40  | How often has Victor Wembanyama had 5 or more blocks this season?    | Wembanyama 5+ blocks this season     |

### 3.9 Record when \_\_\_

| #   | Question form                                                             | Search / shorthand form                    |
| --- | ------------------------------------------------------------------------- | ------------------------------------------ |
| 41  | What's the Mavericks' record when Luka Dončić scores 35 or more?          | Mavericks record when Luka scores 35+      |
| 42  | What is the Knicks' record when they allow fewer than 110 points?         | Knicks record when allowing under 110      |
| 43  | What is Denver's record when Nikola Jokić has a triple-double?            | Denver record when Jokic triple double     |
| 44  | What is the Warriors' record when Stephen Curry makes at least 6 threes?  | Warriors record when Curry makes 6+ threes |
| 45  | What is the Lakers' record when LeBron James and Anthony Davis both play? | Lakers record when LeBron and AD both play |

### 3.10 Splits / context / shorthand search style

| #   | Question form                                                                        | Search / shorthand form                    |
| --- | ------------------------------------------------------------------------------------ | ------------------------------------------ |
| 46  | Who scores the most at home this season?                                             | most points at home this season            |
| 47  | Which teams have the best road record this year?                                     | best road record this year                 |
| 48  | How does Anthony Edwards shoot in wins versus losses?                                | Anthony Edwards shooting in wins vs losses |
| 49  | Which players score the most in the 4th quarter this season?                         | most 4th quarter points this season        |
| 50  | What is the Nuggets' net rating with Nikola Jokić on the floor versus off the floor? | Nuggets net rating Jokic on off            |

---

## 4. Examples by capability cluster

These are organized by the repo's query classes, to match the specification's taxonomy. Useful when you want concentrated examples of a specific class (e.g., all streaks, all occurrences).

### 4.1 Streak queries

Class: `streak`

Player streaks:

- `Jokic 5 straight games with 20+ points`
- `Jokic longest streak of 30 point games`
- `Jokic consecutive games with a made three`
- `Jokic longest triple-double streak`
- `LeBron current 20+ point streak`
- `Curry longest streak with at least 3 threes`

Team streaks:

- `longest Lakers winning streak`
- `Celtics 5 straight games scoring 120+`
- `longest Bucks streak with 15+ threes`
- `Thunder consecutive games with 110+ points`
- `longest Warriors home winning streak`

### 4.2 Occurrence queries

Class: `occurrence` / `count`

Single-event:

- `most 40 point games since 2020`
- `most 15+ rebound games`
- `most triple doubles since 2020`
- `most double doubles last 3 seasons`
- `most 5+ three games vs Lakers`

Compound:

- `most games with 25+ points and 10+ assists since 2020`
- `how many Jokic games with 30+ points and 10+ rebounds in playoffs since 2021`
- `teams with the most games scoring 120+ and making 15+ threes since 2020`
- `most games with 3+ steals and 2+ blocks`

Distinct-entity:

- `how many players scored 40 points this season`
- `number of players with 10 assists this season`
- `how many teams scored 120+ this season`

### 4.3 Compound boolean threshold queries

Class: `finder` or `count` with AND/OR/grouped expressions

- `Jokic over 25 points and over 10 rebounds`
- `Jokic over 25 points or over 10 rebounds`
- `Jokic (over 25 points and over 10 rebounds) or over 15 assists`
- `Celtics (over 120 points and over 15 threes) or under 10 turnovers`

### 4.4 Playoff / historical queries

Class: `playoff`

Playoff history:

- `Lakers playoff history`
- `Celtics finals record`
- `Heat vs Knicks playoff history`
- `Lakers playoff series record vs Celtics`

Appearances / rounds:

- `finals appearances`
- `Warriors conference finals appearances`
- `most Finals appearances since 1980`
- `best finals record since 1980`
- `best second round record`
- `LeBron record in the Finals`

By decade:

- `Warriors record by decade`
- `winningest team of the 2010s`
- `Lakers vs Celtics by decade`

### 4.5 Comparison queries

Class: `comparison`

Player comparison:

- `Jokic vs Embiid recent form`
- `Jokic vs Embiid since 2021`
- `Jokic head-to-head vs Embiid since 2021`
- `Kobe vs LeBron playoffs in 2008-09`

Team comparison:

- `Celtics vs Bucks from 2021-22 to 2023-24`
- `Lakers vs Celtics since 2010`
- `Knicks head-to-head vs Heat since 1999`
- `Celtics vs Bucks home`

---

## 5. Stress test inputs

Inputs most likely to break a parser. Include all in the evaluation harness.

### 5.1 Compressed shorthand

Noun phrases, no verbs, minimal glue words.

- `Luka last 5`
- `Tatum vs contenders`
- `Knicks clutch`
- `Curry from 3 lately`
- `Jokic td this season`
- `Celtics drtg last 10`
- `Bucks ortg w/o Giannis`
- `SGA 30+ games`
- `Brunson without Randle`
- `best Booker games`

### 5.2 Abbreviation-heavy

- `SGA 30+ games`
- `Jokic td this season`
- `Bucks ortg w/o Giannis`
- `Celtics drtg last 10`
- `AD boards this month`
- `KD TS% vs top defenses`
- `CP3 assists no Harden`
- `JJJ blocks`

### 5.3 Alternate operators

Every threshold phrasing should normalize to the same canonical operator per [`specification.md` §7.1](./specification.md#71-operator-normalization).

- `over 30 / at least 30 / 30+ / 30 or more / 30 plus`
- `under 110 / less than 110 / fewer than 110 / at most 110`
- `since / after / before`
- `with / without / when out / when inactive / w/ / w/o`

### 5.4 Word-order swaps

Same semantic request, different word order. All should produce the same parse state.

- `best scorers last month`
- `last month best scorers`
- `scorers best last month`
- `most points last 10 games`
- `last 10 games most points`
- `points leaders last 10`

### 5.5 Missing metric or operator

Underspecified queries that rely on defaults (see [`specification.md` §15](./specification.md#15-defaults-for-underspecified-queries)).

- `Jokic last 10` → default: summary
- `Celtics recently` → default: recent record + team summary
- `SGA vs Nuggets` → default: head-to-head summary
- `Bucks when Giannis out` → default: record when out
- `LeBron best games` → default: ranked game logs by Game Score
- `Curry from 3 lately` → default: recent 3-point shooting stats

### 5.6 Typo / informal spelling

- `jokic` / `doncic` / `wemby` / `anteto`
- `shai points last 10`
- `celtics record vs .500`
- `steph 5+ 3s lately`
- `luka w/o kyrie last 5`

### 5.7 Ambiguous references

Queries where entity resolution alone is not enough.

- `Brown last 10` — Jaylen Brown? Bruce Brown?
- `Williams clutch stats` — which Williams?
- `Johnson defense` — which Johnson?
- `Jackson blocks` — which Jackson?

These need context-based disambiguation or confidence-scored resolution.

### 5.8 Ambiguous intent

Queries with multiple reasonable parses. See [`specification.md` §16.3](./specification.md#163-common-ambiguous-inputs).

- `Celtics recently` — record? team summary? recent games?
- `Tatum vs Knicks` — head-to-head career? recent game? season vs NYK?
- `Jokic triple doubles` — count? list? recent? career?
- `best games Booker` — by what metric?
- `Thunder clutch` — record? team stats? player stats?

---

## 6. End-to-end worked examples

These trace four representative queries through the full pipeline. Each shows:

1. raw input
2. normalized form
3. resolved entities
4. detected intent flags / query class
5. extracted slots
6. defaults applied
7. final parse state and route

Use these as reference for how the stages connect. Slot names match [`specification.md` §5](./specification.md#5-slot-extraction).

---

### 6.1 Worked example: full question, all slots filled

**Raw input:** `how many Jokic games with 30+ points and 10+ rebounds since 2021`

**Stage 1 — Normalized:**

```
how many jokic games with 30+ points and 10+ rebounds since 2021
```

**Stage 2 — Resolved entities:**

- `jokic` → player: Nikola Jokic (id: `NIKOLA_JOKIC`, accent-insensitive match)

**Stage 3 — Intent flags / class:**

- `count_intent: true` (signal: `how many`)
- Primary class: `count` (with compound threshold)

**Stage 4 — Slots extracted:**

- player: `NIKOLA_JOKIC`
- stat: `pts` (from primary threshold)
- min_value: 30
- threshold_conditions: `[{ stat: "pts", min_value: 30, text: "30+ points" }]`
- extra_conditions: `[{ stat: "reb", min_value: 10, text: "10+ rebounds" }]`
- start_season: `2020-21`
- end_season: `2025-26` (default end)
- since_season detected: 2020-21

**Stage 5 — Defaults applied:** End season defaulted to current; season_type defaulted to regular.

**Stage 6 — Parse state + route:**

```json
{
  "route": "player_game_finder",
  "normalized_query": "how many jokic games with 30+ points and 10+ rebounds since 2021",
  "player": "NIKOLA_JOKIC",
  "count_intent": true,
  "stat": "pts",
  "min_value": 30,
  "max_value": null,
  "threshold_conditions": [
    { "stat": "pts", "min_value": 30, "max_value": null, "text": "30+ points" }
  ],
  "extra_conditions": [
    {
      "stat": "reb",
      "min_value": 10,
      "max_value": null,
      "text": "10+ rebounds"
    }
  ],
  "start_season": "2020-21",
  "end_season": "2025-26",
  "season_type": "regular",
  "route_kwargs": {
    "mode": "count",
    "player": "NIKOLA_JOKIC",
    "stat": "pts",
    "min_value": 30,
    "extra_conditions": [{ "stat": "reb", "min_value": 10 }],
    "start_season": "2020-21",
    "end_season": "2025-26"
  }
}
```

---

### 6.2 Worked example: compressed shorthand, same parse state

**Raw input:** `jokic 30+ pts 10+ reb since 2021 count`

**Stage 1 — Normalized:**

```
jokic 30+ pts 10+ reb since 2021 count
```

**Stage 2 — Resolved entities:**

- `jokic` → player: Nikola Jokic

**Stage 3 — Intent flags / class:**

- `count_intent: true` (signal: `count` token)
- Primary class: `count`

**Stage 4 — Slots extracted:**

- player: `NIKOLA_JOKIC`
- stat: `pts`
- threshold_conditions: `[{ stat: "pts", min_value: 30, text: "30+ pts" }]`
- extra_conditions: `[{ stat: "reb", min_value: 10, text: "10+ reb" }]`
- start_season: `2020-21`

**Stages 5–6:** Identical route and route_kwargs to §6.1.

**Key point:** The full-question form (§6.1) and the compressed form here produce the **same route + route_kwargs** — the contract the stats engine sees. That's the equivalence guarantee.

---

### 6.3 Worked example: underspecified query relying on defaults

**Raw input:** `Jokic last 10`

**Stage 1 — Normalized:**

```
jokic last 10 games
```

(`last 10` → `last 10 games` via alias mapping.)

**Stage 2 — Resolved entities:**

- `jokic` → player: Nikola Jokic

**Stage 3 — Intent flags / class:**

- No operator word, no threshold, no `how many` → no explicit intent flag
- Default rule matches: `<player> + <timeframe>` → `summary`
- `summary_intent` set by default logic

**Stage 4 — Slots extracted:**

- player: `NIKOLA_JOKIC`
- last_n: 10
- season: defaulted to current (`2025-26`)
- stat: none specified

**Stage 5 — Defaults applied:**

- No season + any stat/filter signal → `default_season_for_context(season_type)` triggers
- `recent form` signal implicit → `last_n = 10` (explicit here)

**Stage 6 — Parse state + route:**

```json
{
  "route": "player_game_summary",
  "normalized_query": "jokic last 10 games",
  "player": "NIKOLA_JOKIC",
  "last_n": 10,
  "season": "2025-26",
  "season_type": "regular",
  "summary_intent": true,
  "stat": null,
  "route_kwargs": {
    "player": "NIKOLA_JOKIC",
    "season": "2025-26",
    "last_n": 10
  }
}
```

**Key point:** Underspecified queries still produce complete parse state — defaults fill the gaps. Without the default-application stage, this query would either fail or produce inconsistent results.

---

### 6.4 Worked example: shipped opponent-quality record query

**Raw input:** `Lakers record against top-10 defenses 2024-25`

**Stage 1 — Normalized:**

```
lakers record against top-10 defenses 2024-25
```

**Stage 2 — Resolved entities:**

- `lakers` → team: Los Angeles Lakers (id: `LAL`)
- `top-10 defenses` → opponent-quality bucket resolved per [`specification.md` §9.1](./specification.md#91-product-policy-definitions)

**Stage 3 — Intent flags / class:**

- Team subject + explicit `record` phrasing
- `record_intent` is set directly from the surface form
- Broad intent bucket: `summary`

**Stage 4 — Slots extracted:**

- team: `LAL`
- season: `2024-25`
- opponent_quality: `{ surface_term: "top-10 defenses", definition: { metric: "def_rating_rank", operator: "top_n", value: 10 } }`

**Stage 5 — Route + execution notes:**

- Route selected: `team_record`
- On supported routes, execution resolves `opponent_quality` to a concrete opponent-team list before running the command
- Notes include: `opponent_quality: top-10 defenses -> top 10 by defensive rating`

**Stage 6 — Parse state + route:**

```json
{
  "route": "team_record",
  "team": "LAL",
  "record_intent": true,
  "opponent_quality": {
    "type": "opponent_quality",
    "surface_term": "top-10 defenses",
    "definition": {
      "metric": "def_rating_rank",
      "operator": "top_n",
      "snapshot": "latest_regular_season",
      "source": "team_season_advanced",
      "value": 10
    }
  },
  "season": "2024-25",
  "confidence": 0.90,
  "alternates": [],
  "notes": [
    "opponent_quality: top-10 defenses -> top 10 by defensive rating"
  ],
  "route_kwargs": {
    "team": "LAL",
    "season": "2024-25",
    "season_type": "Regular Season",
    "opponent_quality": {
      "type": "opponent_quality",
      "surface_term": "top-10 defenses",
      "definition": {
        "metric": "def_rating_rank",
        "operator": "top_n",
        "snapshot": "latest_regular_season",
        "source": "team_season_advanced",
        "value": 10
      }
    }
  }
}
```

**Key point:** Core opponent-quality routes are no longer just a design target. The parser now carries a structured `opponent_quality` definition into supported summary/finder/record routes, and execution resolves that bucket to concrete opponent team lists.

---

## 7. Equivalence groups

Queries within a group must produce identical parse states (modulo confidence). The evaluation harness should verify this explicitly — this is the main guarantee that question form, search form, and shorthand are all first-class.

### 7.1 Leaderboard — points leaders last 10 games

- `Who has the most points in the last 10 games?`
- `most points last 10 games`
- `points leaders last 10`
- `last 10 scoring leaders`
- `top scorers last 10 games`
- `highest scorers last 10`

### 7.2 Count (compound) — Jokic 30+/10+ since 2021

- `How many Jokic games with 30+ points and 10+ rebounds since 2021?`
- `how many jokic 30+ 10+ since 2021`
- `jokic 30+ pts 10+ reb since 2021 count`
- `count Jokic games 30 points 10 rebounds since 2021`

### 7.3 Summary (default) — Jokic recent

- `How has Jokic played in his last 10 games?`
- `Jokic last 10`
- `Jokic last 10 games`
- `Jokic recent form`
- `Jokic recent stats`

### 7.4 Teammate absence — Bucks without Giannis

- `What is the Bucks' record when Giannis was out?`
- `Bucks record when Giannis out`
- `Bucks without Giannis`
- `Bucks w/o Giannis`
- `Milwaukee record Giannis out`

### 7.5 Occurrence — Curry 5+ threes

- `How often has Stephen Curry made 5 or more threes this year?`
- `Curry 5+ threes this year`
- `Curry 5+ 3s this season`
- `Steph 5+ threes`
- `games Curry made at least 5 threes`

### 7.6 Streak — Jokic 30-point streak

- `Jokic longest streak of 30 point games`
- `Jokic longest 30+ point streak`
- `longest Jokic 30 point streak`
- `Jokic consecutive 30 point games longest`

### 7.7 Clutch recognition — Tatum clutch stats

- `How has Tatum played in the clutch this season?`
- `Tatum clutch stats`
- `Tatum clutch time stats`
- `late-game Tatum stats`
- _Current execution note:_ all variants set `clutch=True`; results remain unfiltered until play-by-play clutch splits land._

### 7.8 Period context — 4th quarter scoring leaders

- `Which players score the most in the 4th quarter this season?`
- `most 4th quarter points this season`
- `4th quarter scoring leaders this season`
- _Current execution note:_ all variants set `quarter="4"`. Period execution is now
  coverage-gated on `player_game_finder` / `team_record` when period backfills exist
  for the requested slice, but these leaderboard variants still remain unfiltered
  because the current period-backed route boundary does not include `season_leaders`._

### 7.9 Schedule context — Lakers back-to-back record

- `What is the Lakers' record on back-to-backs this season?`
- `Lakers on back-to-backs record`
- `Lakers b2b record`
- `Lakers second of a back-to-back record`
- _Execution note:_ all variants set `back_to_back=True`; `team_record` executes the filter when trusted `schedule_context_features` coverage exists, otherwise it keeps the explicit unfiltered-results note._

### 7.10 Role filter — LeBron as a starter

- `How has LeBron played as a starter this season?`
- `LeBron as a starter stats`
- `LeBron starting stats`
- _Current execution note:_ all variants set `role="starter"` for player-context queries; `player_game_summary` / `player_game_finder` apply the filter only when trusted `player_game_starter_roles` coverage exists for the requested slice, otherwise they keep the explicit unfiltered-results note._

### 7.11 Opponent-quality — Jokic against contenders

- `How has Jokic played against contenders this season?`
- `Jokic against contenders this season`
- `Jokic vs contenders this season`
- _Execution note:_ all variants set the same structured `opponent_quality` definition and route through the supported single-entity summary path._

### 7.12 Rest filter — Jokic with rest advantage

- `How has Jokic played with rest advantage this season?`
- `Jokic with rest advantage this season`
- `Jokic rest advantage stats`
- _Execution note:_ all variants set `rest_days="advantage"`; `player_game_summary` executes the filter when trusted `schedule_context_features` coverage exists, otherwise it keeps the explicit unfiltered-results note._

### 7.13 One-possession filter — Celtics one-possession record

- `What is the Celtics' record in one-possession games this season?`
- `Celtics one-possession record this season`
- `Celtics record in one-possession games`
- _Execution note:_ all variants set `one_possession=True`; `team_record` executes the filter when trusted `schedule_context_features` coverage exists, otherwise it keeps the explicit unfiltered-results note._

### 7.14 National-TV filter — Lakers national-TV record

- `What is the Lakers' record on national TV this season?`
- `Lakers national TV record`
- `Lakers nationally televised record`
- _Execution note:_ all variants set `nationally_televised=True`; `team_record` executes the filter only when trusted national-TV source coverage exists. Placeholder schedule pulls keep the explicit unfiltered-results note for this filter._

### 7.15 On/off placeholder — Jokic on/off

- `Jokic on/off`
- `Jokic on off`
- `Nikola Jokic on-off`
- _Current execution note:_ all variants route to `player_on_off`. Execution returns trusted `team_player_on_off_summary` rows when coverage exists for the requested single-player slice; missing or untrusted coverage keeps the honest unsupported-data response._

### 7.16 Lineup leaderboard — best 5-man lineups

- `best 5-man lineups`
- `best 5 man lineups`
- `top 5-man units`
- _Execution note:_ all variants set `unit_size=5` and route to `lineup_leaderboard`. Execution uses trusted `league_lineup_viz` rows when coverage exists; missing or untrusted coverage returns an honest unsupported/no-result response._

### 7.17 Specific lineup — LeBron and AD together

- `lineups with LeBron and AD`
- `lineup with LeBron and AD`
- `LeBron and AD together lineups`
- _Execution note:_ all variants route to `lineup_summary` with `lineup_members` populated. Execution uses trusted `league_lineup_viz` rows when coverage exists; missing or untrusted coverage returns an honest unsupported/no-result response._

### 7.18 Stretch leaderboard — hottest 3-game scoring stretch

- `Who has the hottest 3-game scoring stretch this year?`
- `hottest 3-game scoring stretch this year`
- `3-game scoring stretch leaders this year`
- `top 3-game scoring stretches this year`
- _Execution note:_ all variants route to `player_stretch_leaderboard` with `window_size=3` and `stretch_metric="pts"`._

---

## 8. Expansion patterns and explicit boundaries

Patterns beyond the original core surface. Some now ship in Phase E; others
remain future work or are explicitly outside the core finish line unless a
future product queue reopens them.

### 8.1 Additional opponent-quality buckets (future expansion)

- `against top-5 offenses`
- `against elite frontcourts`
- `against winning teams`
- `best record vs teams above .600`
- _Core opponent-quality buckets shipped in Phase E. These remaining variants need new glossary definitions or new data sources._

### 8.2 On/off and lineup queries (Phase E shipped surface)

- `Jokic on/off`
- `Nuggets with and without Jokic`
- `best 5-man lineups`
- `net rating with Tatum and Brown together`
- `best 3-man units with at least 200 minutes`
- _See equivalence groups §7.15-§7.17 for canonical paraphrase sets._
- _Single-player on/off phrasing routes to coverage-gated `player_on_off` execution. Lineup/unit phrasing routes to coverage-gated `lineup_summary` or `lineup_leaderboard` execution backed by trusted `league_lineup_viz` rows._
- _See [`specification.md` §11](./specification.md#11-onoff-lineup-and-stretch-support)._

### 8.3 Context filtering boundaries

- `in clutch time` with true play-by-play clutch filtering
- schedule-context route expansion beyond `team_record` / `player_game_summary`
  is out of scope for the core finish line unless a future product queue reopens it
- starter / bench route expansion beyond the current `player_game_summary` /
  `player_game_finder` trusted-role boundary, including team-level bench
  semantics, is out of scope for the core finish line unless a future product
  queue reopens it
- broader trusted national-TV source coverage remains part of the
  schedule-context coverage gate, not a reason to silently filter untrusted data
- period execution beyond the current `player_game_finder` / `team_record`
  boundary is out of scope for the core finish line unless a future product queue
  reopens it

### 8.4 Stretch / rolling-window queries (Phase E shipped surface)

- `hottest 3-game scoring stretch this year`
- `best 5-game stretch by Game Score`
- `most efficient 10-game rolling stretch`
- _See equivalence group §7.18 for canonical paraphrase sets._
- _These queries route to `player_stretch_leaderboard` with real rolling-window execution over player game logs._

### 8.5 Career / historical splits

- `What is ___ averaging in wins this season?`
- `Who has the most ___ since becoming a starter?`
- `How has ___ played against the Lakers in his career?`
- `What is ___ record in overtime games this season?`

### 8.6 Triplet dataset pattern (for robustness testing)

For each intent, maintain three paraphrases:

1. **Full question** — `Who has the most points in the last 10 games?`
2. **Search phrase** — `most points last 10 games`
3. **Compressed shorthand** — `points leaders last 10`

A parser that maps all three to the same parse state is robust to most real-world input variation. Building this triplet set across all intents is the strongest robustness benchmark.

---

> **Related**: [`overview.md`](./overview.md) (framing & principles) · [`specification.md`](./specification.md) (component spec) · [`docs/reference/query_catalog.md`](../../reference/query_catalog.md) (living shipped inventory) · [`docs/planning/query_surface_expansion_plan.md`](../../planning/query_surface_expansion_plan.md) (active expansion plan)
