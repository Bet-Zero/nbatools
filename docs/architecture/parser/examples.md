# Parser Examples

> **Purpose of this doc:** The example library. Use this for test inputs, equivalence verification, and to see how real user language maps to the parser's canonical parse state. For framing, see [`overview.md`](./overview.md). For component specs, see [`specification.md`](./specification.md). For the living inventory of currently-shipped query shapes, see [`docs/reference/query_catalog.md`](../../reference/query_catalog.md).

---

## Table of contents

1. [How to use this doc](#1-how-to-use-this-doc)
2. [Canonical example set (100 queries)](#2-canonical-example-set-100-queries)
3. [Paired examples: question form vs search form](#3-paired-examples-question-form-vs-search-form)
4. [Examples by capability cluster](#4-examples-by-capability-cluster)
5. [Stress test inputs](#5-stress-test-inputs)
6. [End-to-end worked examples](#6-end-to-end-worked-examples)
7. [Equivalence groups](#7-equivalence-groups)
8. [Next-wave patterns (future expansion)](#8-next-wave-patterns-future-expansion)

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

11. Who scored the most points last night?
12. Which players have been the hottest from three lately?
13. Who has the most assists over the past month?
14. What team has played the best defense recently?
15. Who is averaging the most rebounds in the last 2 weeks?
16. Which players have been the most efficient recently?
17. What teams have the best record over the past month?
18. Who has had the most steals lately?
19. Which scorers have cooled off over their last 10 games?
20. What players have the most double-doubles recently?

### 2.3 Last N games / since date / over span

Primary class: `leaderboard` or `summary` with explicit windowed timeframe

21. Who is averaging the most points in his last 5 games?
22. Which team has the best net rating in its last 10 games?
23. Who has the most made threes in the last 7 games?
24. What players have averaged a double-double over their last 15 games?
25. Who has been the best rebounder since January 1?
26. Which teams have the best record since the All-Star break?
27. What players have the highest usage rate over their last 8 games?
28. Who is shooting the best from three since February 1 with at least 4 attempts per game?
29. What team has allowed the fewest paint points in its last 12 games?
30. Who has the most blocks since March 1?

### 2.4 Best games / biggest games / most efficient

Primary class: `leaderboard` (season-high variant) or `occurrence`

31. What were the biggest scoring games this season?
32. Which players had the best games by Game Score this year?
33. What are the highest assist games by a point guard this season?
34. Who has had the most efficient 30-point games this year?
35. What were the best rebounding games by a center this season?
36. Which players have the hottest 3-game scoring stretch this year?
37. What are the biggest triple-double games this season?
38. Who has the best shooting games with at least 25 points this year?
39. What are the most dominant games by plus-minus this season?
40. Which players have had the best two-way games this season?

### 2.5 Against good teams / top teams / contenders

Primary class: `summary` or `record` with opponent-quality filter *(opponent-quality filter not yet shipped — see [`specification.md` §9](./specification.md#9-opponent-quality-filters))*

41. Who scores the most against teams over .500 this season?
42. Which team has the best record against contenders this year?
43. What players have the highest true shooting percentage against top-10 defenses?
44. How has Jayson Tatum played against good teams this season?
45. What is the Celtics' record against teams above .600?
46. Which players average the most assists against playoff teams?
47. What team has the best defense against top-5 offenses this year?
48. Who rebounds the best against elite frontcourts?
49. Which scorers have the biggest drop-off against winning teams?
50. What players have the most 30-point games against contenders this season?

### 2.6 When a teammate didn't play / was out

Primary class: `summary` or `record` with `without_player` filter

51. How do the Suns perform when Devin Booker didn't play?
52. What is the Bucks' record when Giannis Antetokounmpo was out?
53. Who averages the most points when their co-star didn't play this season?
54. How has Anthony Davis rebounded when LeBron James was out?
55. What is the Mavericks' offensive rating when Luka Dončić didn't play?
56. How does Jamal Murray score when Nikola Jokić is out?
57. What is the Knicks' record when Jalen Brunson doesn't play?
58. Which players see the biggest usage increase when their star teammate is out?
59. How has Tyrese Maxey played when Joel Embiid didn't play this season?
60. What team has stayed afloat best when its leading scorer was out?

### 2.7 "Who's been the best at ___ over ___"

Primary class: `leaderboard` with timeframe + skill filter

61. Who's been the best scorer over the last 10 games?
62. Who's been the best rebounder since January 1?
63. Who's been the best rim protector over the past month?
64. Who's been the best playmaker in the last 15 games?
65. Who's been the best catch-and-shoot shooter this season?
66. Who's been the best at drawing fouls over the past 20 games?
67. Who's been the best transition scorer this year?
68. Who's been the best isolation defender over the past month?
69. Who's been the best shot creator in clutch time this season?
70. Who's been the best offensive rebounder lately?

### 2.8 Frequency / how often

Primary class: `count` or `occurrence`

71. How often has Nikola Jokić recorded a triple-double this season?
72. How often has Stephen Curry made 5 or more threes this year?
73. How often has a team won when trailing after 3 quarters this season?
74. How often has Luka Dončić scored 40 or more this year?
75. How often has a player had 10+ assists and 0 turnovers this season?
76. How often have the Lakers held opponents under 100 points this year?
77. How often has Victor Wembanyama had 5+ blocks this season?
78. How often has a team scored 140 or more points this year?
79. How often has Jalen Brunson scored 30+ in his last 20 games?
80. How often has a road team won by 20+ this season?

### 2.9 Record when ___

Primary class: `record` with conditional filter

81. What's the Mavericks' record when Luka Dončić scores 35 or more?
82. What is the Knicks' record when they allow fewer than 110 points?
83. What is Denver's record when Nikola Jokić has a triple-double?
84. What's Boston's record when Jayson Tatum shoots under 40%?
85. What is the Lakers' record when LeBron James and Anthony Davis both play?
86. What's the Thunder's record when Shai Gilgeous-Alexander scores 30+?
87. What is Milwaukee's record when it wins the rebounding battle?
88. What's the Warriors' record when Stephen Curry makes at least 6 threes?
89. What is the Suns' record when Kevin Durant leads the team in scoring?
90. What's the Cavaliers' record when they score fewer than 105 points?

### 2.10 Splits and context filters

Primary class: `split` or context-filtered variants

91. Who scores the most at home this season?
92. Which teams have the best road record this year?
93. How does Anthony Edwards shoot in wins vs losses?
94. Who averages the most points in the first half this season?
95. Which players score the most in the 4th quarter?
96. What is the Lakers' record on back-to-backs this season?
97. Who has the best clutch field goal percentage this year?
98. What team has the best record in one-possession games this season?
99. Which players average the most points as a starter vs off the bench?
100. What is the Nuggets' net rating with Nikola Jokić on the floor vs off the floor?

---

## 3. Paired examples: question form vs search form

These pairs verify that the parser maps both phrasings to the same parse state. The 10 groups mirror the categories above.

### 3.1 Leaders and rankings

| #  | Question form                                             | Search / shorthand form                    |
| -- | --------------------------------------------------------- | ------------------------------------------ |
| 1  | Who leads the NBA in points per game this season?         | points per game leaders this season        |
| 2  | Which players have the most rebounds this year?           | most rebounds this year                    |
| 3  | Who has the highest true shooting percentage this season? | best true shooting percentage this season  |
| 4  | Which team has the best offensive rating this year?       | best offensive rating team this year       |
| 5  | Who has the most assists over the last 10 games?          | most assists last 10 games                 |

### 3.2 Recent / lately / past month

| #  | Question form                                          | Search / shorthand form       |
| -- | ------------------------------------------------------ | ----------------------------- |
| 6  | Who scored the most points last night?                 | most points last night        |
| 7  | Which players have been the hottest from three lately? | hottest from 3 lately         |
| 8  | Who has been the best scorer over the past month?      | best scorers past month       |
| 9  | What team has played the best defense recently?        | best defense recently         |
| 10 | Who has the most double-doubles lately?                | most double doubles lately    |

### 3.3 Last N games / since date

| #  | Question form                                                                              | Search / shorthand form                         |
| -- | ------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| 11 | Who is averaging the most points in his last 5 games?                                      | most points last 5 games                        |
| 12 | Which team has the best net rating in its last 15 games?                                   | best net rating last 15 games                   |
| 13 | Who has made the most threes since January 1?                                              | most threes since January 1                     |
| 14 | Which players have averaged a double-double over their last 10 games?                      | double double average last 10 games             |
| 15 | Who is shooting the best from three over the last month with at least 5 attempts per game? | best 3pt percentage last month min 5 attempts   |

### 3.4 Best games / biggest games / most efficient

| #  | Question form                                                       | Search / shorthand form                 |
| -- | ------------------------------------------------------------------- | --------------------------------------- |
| 16 | What were the biggest scoring games this season?                    | biggest scoring games this season       |
| 17 | Which players have had the most efficient 30-point games this year? | most efficient 30 point games this year |
| 18 | What are the best rebounding games by centers this season?          | best rebounding games by centers        |
| 19 | Who has had the best all-around games this year?                    | best all around games this year         |
| 20 | What were the highest assist games by point guards this season?     | highest assist games by point guards    |

### 3.5 Against good teams / contenders

*Opponent-quality filters are not yet shipped — see [`specification.md` §9](./specification.md#9-opponent-quality-filters).*

| #  | Question form                                                  | Search / shorthand form            |
| -- | -------------------------------------------------------------- | ---------------------------------- |
| 21 | Who scores the most against teams over .500 this season?       | most points vs teams over .500     |
| 22 | What team has the best record against contenders this year?    | best record vs contenders          |
| 23 | Which players shoot the best against top-10 defenses?          | best shooting vs top 10 defenses   |
| 24 | How has Jayson Tatum played against winning teams this season? | Tatum vs winning teams this season |
| 25 | What is the Celtics' record against teams above .600?          | Celtics record vs teams above .600 |

### 3.6 When a teammate didn't play

| #  | Question form                                                         | Search / shorthand form                 |
| -- | --------------------------------------------------------------------- | --------------------------------------- |
| 26 | How do the Suns perform when Devin Booker didn't play?                | Suns when Booker out                    |
| 27 | What is the Bucks' record when Giannis Antetokounmpo was out?         | Bucks record when Giannis out           |
| 28 | How has Anthony Davis rebounded when LeBron James didn't play?        | Anthony Davis rebounds when LeBron out  |
| 29 | What is the Mavericks' offensive rating when Luka Dončić didn't play? | Mavericks offensive rating without Luka |
| 30 | How has Tyrese Maxey played when Joel Embiid was out this season?     | Maxey when Embiid out this season       |

### 3.7 "Who's been the best at ___ over ___"

| #  | Question form                                           | Search / shorthand form                 |
| -- | ------------------------------------------------------- | --------------------------------------- |
| 31 | Who's been the best rebounder over the past month?      | best rebounder past month               |
| 32 | Who's been the best shot blocker in the last 10 games?  | best shot blocker last 10 games         |
| 33 | Who's been the best playmaker since the All-Star break? | best playmaker since all star break     |
| 34 | Who's been the best catch-and-shoot player this season? | best catch and shoot player this season |
| 35 | Who's been the best transition scorer lately?           | best transition scorer lately           |

### 3.8 Frequency / how often

| #  | Question form                                                        | Search / shorthand form              |
| -- | -------------------------------------------------------------------- | ------------------------------------ |
| 36 | How often has Nikola Jokić recorded a triple-double this season?     | Jokic triple doubles this season     |
| 37 | How often has Stephen Curry made 5 or more threes this year?         | Curry 5+ threes this year            |
| 38 | How often has Luka Dončić scored 40 or more this season?             | Luka 40+ point games this season     |
| 39 | How often have the Lakers held opponents under 100 points this year? | Lakers opponents under 100 this year |
| 40 | How often has Victor Wembanyama had 5 or more blocks this season?    | Wembanyama 5+ blocks this season     |

### 3.9 Record when ___

| #  | Question form                                                             | Search / shorthand form                    |
| -- | ------------------------------------------------------------------------- | ------------------------------------------ |
| 41 | What's the Mavericks' record when Luka Dončić scores 35 or more?          | Mavericks record when Luka scores 35+      |
| 42 | What is the Knicks' record when they allow fewer than 110 points?         | Knicks record when allowing under 110      |
| 43 | What is Denver's record when Nikola Jokić has a triple-double?            | Denver record when Jokic triple double     |
| 44 | What is the Warriors' record when Stephen Curry makes at least 6 threes?  | Warriors record when Curry makes 6+ threes |
| 45 | What is the Lakers' record when LeBron James and Anthony Davis both play? | Lakers record when LeBron and AD both play |

### 3.10 Splits / context / shorthand search style

| #  | Question form                                                                        | Search / shorthand form                    |
| -- | ------------------------------------------------------------------------------------ | ------------------------------------------ |
| 46 | Who scores the most at home this season?                                             | most points at home this season            |
| 47 | Which teams have the best road record this year?                                     | best road record this year                 |
| 48 | How does Anthony Edwards shoot in wins versus losses?                                | Anthony Edwards shooting in wins vs losses |
| 49 | Which players score the most in the 4th quarter this season?                         | most 4th quarter points this season        |
| 50 | What is the Nuggets' net rating with Nikola Jokić on the floor versus off the floor? | Nuggets net rating Jokic on off            |

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
    { "stat": "reb", "min_value": 10, "max_value": null, "text": "10+ rebounds" }
  ],
  "start_season": "2020-21",
  "end_season": "2025-26",
  "season_type": "regular",
  "route_kwargs": {
    "mode": "count",
    "player": "NIKOLA_JOKIC",
    "stat": "pts",
    "min_value": 30,
    "extra_conditions": [
      { "stat": "reb", "min_value": 10 }
    ],
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

### 6.4 Worked example: ambiguous query with expansion target

**Raw input:** `Celtics vs contenders`

*Note: Opponent-quality filters (`contenders`, `good teams`, etc.) are not yet shipped. This trace shows the target state once Phase E of the expansion plan lands.*

**Stage 1 — Normalized:**
```
celtics against contenders
```

**Stage 2 — Resolved entities:**
- `celtics` → team: Boston Celtics (id: `BOS`)
- `contenders` → opponent quality (policy-resolved per [`specification.md` §18.2](./specification.md#182-opponent-quality-definitions-proposed--not-yet-shipped))

**Stage 3 — Intent flags / class:**
- Team subject + opponent-quality filter + no explicit metric
- Default rule matches: `<team> + <opponent-quality>` → `record`
- `record_intent` set by default logic
- Alternate parse: `summary` (team stats vs opponent group) — surfaced if confidence medium

**Stage 4 — Slots extracted:**
- team: `BOS`
- record_intent: true (default)
- opponent_quality filter: `{ surface_term: "contenders", definition: { metric: "net_rating_rank", operator: "top_n", value: 6 } }`
- season: defaulted to current

**Stage 5 — Defaults applied:**
- Missing timeframe → season default
- Missing metric → record
- Alternate surfaced (summary vs contenders)

**Stage 6 — Parse state + route (target):**

```json
{
  "route": "team_record_vs_quality",
  "normalized_query": "celtics against contenders",
  "team": "BOS",
  "record_intent": true,
  "opponent_quality_filter": {
    "surface_term": "contenders",
    "definition": { "metric": "net_rating_rank", "operator": "top_n", "value": 6 }
  },
  "season": "2025-26",
  "confidence": 0.71,
  "alternates": [
    {
      "route": "team_summary_vs_quality",
      "confidence": 0.58
    }
  ]
}
```

**Key point:** Medium-confidence parses execute the primary interpretation but surface the alternate so the user can pivot without re-typing. Confidence and alternates are proposed additions (see [`specification.md` §17.2](./specification.md#172-proposed-additions)).

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

---

## 8. Next-wave patterns (future expansion)

Patterns not required for the current shipped surface but flagged as targets in [`docs/planning/query_surface_expansion_plan.md`](../../planning/query_surface_expansion_plan.md).

### 8.1 Opponent-quality buckets (Phase E)

- `against good teams`
- `against contenders`
- `against top-10 defenses`
- `best record vs winning teams`
- *Requires policy definitions — see [`specification.md` §18.2](./specification.md#182-opponent-quality-definitions-proposed--not-yet-shipped).*

### 8.2 On/off and lineup queries (Phase E)

- `Jokic on/off`
- `Nuggets with and without Jokic`
- `best 5-man lineups`
- `net rating with Tatum and Brown together`
- `best 3-man units with at least 200 minutes`
- *See [`specification.md` §11](./specification.md#11-onoff-and-lineup-support).*

### 8.3 Expanded context filters (Phase E)

- `in clutch time`
- `back-to-backs`
- `as starter vs bench`
- `nationally televised games`
- `in overtime`
- `in one-possession games`

### 8.4 Stretch / rolling-window queries (Phase E)

- `hottest 3-game scoring stretch this year`
- `best 5-game stretch by Game Score`
- `most efficient 10-game rolling stretch`

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
