# Parser Overview

> **Purpose of this doc:** High-level framing for anyone (or any agent) working on the natural-query parser in `nbatools`. Read this first to understand *the approach*. For implementation detail, see [`specification.md`](./specification.md). For test inputs and worked examples, see [`examples.md`](./examples.md). For active expansion work, see [`docs/planning/query_surface_expansion_plan.md`](../../planning/query_surface_expansion_plan.md).

---

## 1. The core problem

The goal is a system that can answer any NBA stat question. The hard part is **not** the stats — it's the input.

Users won't type clean questions. They'll type search fragments, shorthand, abbreviations, typos, and commands. A parser that only accepts question format will fail on a large share of real usage.

Instead of:

> Who has the most points over the last 10 games?

Users will type:

- `most points last 10 games`
- `points leaders last 10`
- `top scorers recently`
- `Jokic when Murray out`
- `Celtics record when Tatum scores 30+`
- `SGA vs winning teams`
- `best TS% this month`
- `triple doubles this season`
- `Luka last 5`
- `Knicks defensive rating lately`

All of those are valid intents. They just omit question words, verbs, and stopwords.

**Treat non-question phrasing as a first-class input style, not edge-case cleanup.**

This principle is already codified in `AGENTS.md`:

> *"For parser work, treat all of these as first-class input styles: full question form, search-bar / fragment form, compressed shorthand form. Do not assume users will type full grammatical questions. Favor intent + slots over sentence grammar."*

This doc and its companions make that principle explicit and lay out how to operationalize it.

---

## 2. The design principle

### Do not key off sentence type

Don't make "is this a question?" part of the decision logic. Sentence structure is a weak signal in this domain.

### Key off content words and structure

Every query — question or not — carries the same underlying structure:

- **entity** — player, team, opponent, teammate, lineup, position group
- **metric** — points, rebounds, TS%, record, net rating, frequency
- **aggregation** — per game, total, average, count, record
- **timeframe** — season, last N games, since date, career, playoffs
- **filters** — opponent, teammate status (with / without), threshold conditions, context (home/away, wins/losses, clutch, etc.)
- **ranking / operator** — top, most, best, hottest, longest

Two very different-looking queries can carry the same structure:

| Input                                                | Query class     | Entity    | Stat   | Window      |
| ---------------------------------------------------- | --------------- | --------- | ------ | ----------- |
| `Who has the most points over the last 10 games?`    | `leaderboard`   | league    | points | `last_n=10` |
| `most points last 10 games`                          | `leaderboard`   | league    | points | `last_n=10` |
| `points leaders last 10`                             | `leaderboard`   | league    | points | `last_n=10` |

**If the parser maps all three to the same parse state, the rest of the system only has to handle one thing.**

---

## 3. The canonical parse state

The current parser already builds a structured parse state in `_build_parse_state()` (see `src/nbatools/commands/natural_query.py`) and uses it to route to a specific query engine route. This doc treats that parse state as the **canonical intermediate representation**: the contract between the parser and the stats engine.

Example: `how many Jokic games with 30+ points and 10+ rebounds since 2021`

The parser routes this to `player_game_finder` in count mode with a parse state like:

```json
{
  "route": "player_game_finder",
  "normalized_query": "how many jokic games with 30+ points and 10+ rebounds since 2021",
  "player": "NIKOLA_JOKIC",
  "count_intent": true,
  "stat": "pts",
  "min_value": 30,
  "threshold_conditions": [
    { "stat": "pts", "min_value": 30, "max_value": null, "text": "30+ points" }
  ],
  "extra_conditions": [
    { "stat": "reb", "min_value": 10, "max_value": null, "text": "10+ rebounds" }
  ],
  "start_season": "2020-21",
  "end_season": "2025-26"
}
```

The parse state gives you:

- easier debugging (you can inspect the parse, not just the final answer)
- easier evaluation (you can score parses slot-by-slot, not just by end result)
- easier expansion (new intents plug into the same state shape)
- clean handling of question vs. shorthand equivalence (both forms produce identical parse states)

> **See [`specification.md`](./specification.md) §17 for the full parse-state schema, including slots not shown above and proposed additions (parse-level `confidence`, `alternates`, explicit `intent` enum).**

---

## 4. The biggest risk

The biggest risk is **not** that the parser fails on weird grammar.

The biggest risk is that it returns **confident but inconsistent interpretations** for short, vague sports-style queries.

That is what users notice fastest. "Why did the same kind of question give a different answer yesterday?" kills trust faster than "I don't understand this query."

The parser problem is **less about understanding English** and **more about making consistent product decisions for vague sports language.**

---

## 5. Product-policy decisions to lock down early

These are not parser questions — they're product questions. But they have to be decided before the parser can behave consistently.

| Term / situation                | Needs a defined answer                                                   |
| ------------------------------- | ------------------------------------------------------------------------ |
| `recently` / `lately`           | Last 5 games? Last 10? Last 30 days? Current month?                      |
| `past month`                    | Rolling 30 days or current calendar month?                               |
| `this year`                     | Current season or calendar year?                                         |
| `last 10`                       | Games (default) or days?                                                 |
| `good teams`                    | Above .500? Above .600? Net rating threshold?                            |
| `contenders`                    | Top 6 by record? Title odds? Playoff teams? Custom label?                |
| `top defenses`                  | By defensive rating, season-long or as of query time?                    |
| `best games`                    | By points? Game Score? TS%? Composite?                                   |
| `hottest`                       | By recent scoring? Shooting %? Composite?                                |
| `efficient`                     | By TS%? eFG%? Points per shot?                                           |
| Default for `player + timeframe`                 | Stat line summary                                       |
| Default for `team + opponent filter`             | Record                                                  |
| Default for `player + threshold event`           | Count/frequency                                         |
| Default for `best games`                         | Ranked game logs                                        |
| When to ask for clarification                    | Confidence threshold                                    |
| How many alternate interpretations to surface    | 0? 1? 2?                                                |

**If these are vague, parser quality will look worse than it actually is.**

> **See [`specification.md`](./specification.md) §18 for the consolidated glossary, including defaults already assumed in the codebase and those proposed.**

---

## 6. The three input styles to support

For nearly every intent, the system should handle three phrasings that mean the same thing:

| Style                 | Example                                                |
| --------------------- | ------------------------------------------------------ |
| Full question         | `Who has the most points over the last 10 games?`      |
| Search phrase         | `most points last 10 games`                            |
| Compressed shorthand  | `points leaders last 10`                               |

If the parser handles all three consistently, it will feel fast and smart. If it only handles one, users will quickly learn which magic phrasing it wants — and then leave.

> **See [`examples.md`](./examples.md) for complete example sets in all three styles, plus equivalence groups used for testing.**

---

## 7. The golden rule

Design it so that:

- **question format is optional**
- **word order is flexible**
- **missing glue words are okay**
- **intent comes from content words, not grammar**

If the system enforces none of those four things, it will feel like a search engine that happens to answer questions — which is exactly what users want from a sports stat tool.

---

## 8. How these docs fit together

| Doc                                                 | Role                                                                        |
| --------------------------------------------------- | --------------------------------------------------------------------------- |
| **`overview.md`** (this file)                       | Framing, principles, product-policy decisions                               |
| [`specification.md`](./specification.md)            | Component-by-component technical reference: pipeline, slots, canonical shape, evaluation |
| [`examples.md`](./examples.md)                      | Query examples by category, paired/shorthand variants, end-to-end traces, stress tests |

### Related repo docs

| Doc                                                                                    | Role                                                |
| -------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [`AGENTS.md`](../../../AGENTS.md)                                                      | Repo-wide agent conventions, working style, testing |
| [`docs/reference/query_catalog.md`](../../reference/query_catalog.md)                  | Living inventory of shipped query capabilities      |
| [`docs/reference/current_state_guide.md`](../../reference/current_state_guide.md)      | Strict verified current behavior                    |
| [`docs/planning/query_surface_expansion_plan.md`](../../planning/query_surface_expansion_plan.md) | Active plan for expanding the natural-query surface |

Read this doc for the *why*. Read the spec for the *what*. Read the examples for *how it shows up in real user language*. Read the expansion plan for *what's being built next*.
