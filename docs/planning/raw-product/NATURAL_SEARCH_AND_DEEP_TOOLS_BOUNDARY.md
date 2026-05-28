# Natural Search and Deep Tools Boundary

## Purpose

This note records the current product boundary between the default natural-language search box and future deeper guided tools / modes.

The default search box remains the front door of the product. It should answer normal NBA-stats-shaped questions directly when the user intent is clear.

Future guided tools should exist for workflows that are too ambiguous, customizable, or exploratory for a single natural-language answer.

## Core product rule

Natural search answers one clear NBA stats intent at a time:

- stat lookup
- team or player record
- leaderboard
- split
- streak
- rolling stretch
- finder / count query
- top performance
- simple comparison

Natural search may attach supported qualifiers and filters to that main intent.

Examples:

```text
Lakers record with Luka
Who had the most rebounds in a game this year?
Jokic this season
Celtics record vs Eastern Conference teams
Curry longest streak with 3+ threes
```

The parser/product contract is:

```text
Find the main intent.
Find the main subject.
Attach supported qualifiers.
If supported, answer.
If unsupported or ambiguous, fail cleanly or clarify.
Never answer a different question just because part of the query matched.
```

## Main intent and qualifier model

The expected behavior is concept-based, not one-off phrase matching.

Example:

```text
Lakers record with Luka without Reaves
```

Conceptual parse:

```text
main intent: team record
main subject: Lakers
qualifier: with Luka
qualifier: without Reaves
```

If the product supports that qualifier combination, it should answer. If the product does not support compound player availability yet, it should return a clean unsupported/no-result response while preserving the understood main intent.

It should not reroute to a Luka or Reaves player-summary answer.

## What natural search should handle

### Direct stat lookups

```text
Luka stats this season
Jokic rebounds last 10 games
Curry threes in the playoffs
```

Goal: quick player/team answer.

### Records and supported filters

```text
Lakers record this season
Lakers record with Luka
Lakers record without Luka
Celtics record vs Eastern Conference teams
```

Goal: answer a record question with clear supported filters.

### Leaderboards

```text
Who leads rookies in scoring?
Centers with the most rebounds this season
Who has the highest FG% among guards?
```

Goal: ranked table.

### Single-game highs, finders, and count questions

```text
Who had the most rebounds in a game this year?
Luka 40-point games this season
How many times did Jokic have a triple-double?
```

Goal: top result, count, or game list.

### Splits, streaks, and rolling stretches

```text
Jokic home vs away this season
Curry longest streak with 3+ threes
Jokic best 5-game rebounding stretch
```

Goal: one specific stat view.

### Simple comparisons

```text
LeBron vs KD this season
Chet vs Myles Turner per 36
```

Goal: basic side-by-side comparison using a default comparison contract.

## Where natural search should stop

Natural search should not try to become every deeper tool in one sentence.

### Deep customizable comparisons

Example:

```text
Compare LeBron and KD by age 25-35, playoffs only, per 100, excluding injured games, show shooting zones and clutch splits.
```

This belongs in a dedicated comparison tool, not the default single-answer search contract.

### Ambiguous short queries

Example:

```text
LeBron vs KD
```

Reasonable interpretations include:

- compare LeBron and KD stats
- LeBron games against KD
- KD games against LeBron
- head-to-head team records
- playoff matchups

Natural search may choose a default, but the better product behavior is clarification or intent options.

### Broad subjective or narrative questions

Examples:

```text
Who is the best defender on the Celtics?
Why did the Celtics lose?
Who is more valuable, Luka or Shai?
```

Unless the product defines a specific stat interpretation, these should be unsupported or guided into measurable options.

### Multi-step research workflows

Example:

```text
Find undervalued guards who improved after the trade deadline and compare them to similar playoff guards.
```

This is research/exploration, not a single natural-search result.

## Planned deeper tools / modes

These are future guided surfaces that can sit behind, next to, or be launched from natural search.

The goal is not to replace natural search. The goal is to give control when a workflow has multiple valid interpretations or adjustable dimensions.

### Player Comparison Tool

Purpose: rich player-vs-player analysis beyond a simple default comparison.

Possible controls:

- career vs season comparison
- regular season vs playoffs
- head-to-head games
- age-season comparison
- per game / per 36 / per 100
- selected date range
- selected stat groups
- add/remove players
- team context
- split filters

Natural search can still answer simple comparisons. The deeper tool handles customization.

### Head-to-Head Tool

Purpose: resolve true “vs” questions that mean games against another player, team, or matchup context.

Possible controls:

- player vs player games
- team vs team games
- playoff matchups
- regular season only
- playoffs only
- player stats in head-to-head games
- team record in head-to-head games

This is especially important because short queries like `LeBron vs KD` are inherently ambiguous.

### Leaderboard Builder

Purpose: customizable ranked tables.

Possible controls:

- stat
- season/date range
- position
- role/starter/bench if supported
- team
- minimum games/minutes/attempts
- per-game/per-36/per-100 basis
- regular season/playoffs

Natural search should handle common leaderboard questions. The builder handles controlled exploration.

### Record / Filter Builder

Purpose: more complex record questions with multiple filters.

Possible controls:

- team
- season/date range
- with/without player
- opponent
- home/away
- playoffs/regular season
- eventual compound availability if the product defines and supports it

Natural search should answer simple supported record filters. The builder handles multiple filters and discoverability.

### Streak / Stretch Builder

Purpose: deeper streak and rolling-window exploration.

Possible controls:

- player/team
- stat
- threshold
- window size
- season/date range
- regular season/playoffs
- longest/current streak
- best/worst rolling stretch

Natural search should answer common streak/stretch questions. The builder handles custom thresholds and windows.

### Player and Team Pages

Purpose: browsable profiles launched from search results.

Possible sections:

- season summary
- game log
- splits
- recent form
- top games
- streaks
- comparison entry points
- related queries

## Product overlap rule

Natural search gives the best quick answer.

Guided tools give control.

Use natural search when the query has one clear intended result. Use a tool, clarification, or mode when the query has multiple valid meanings or many adjustable dimensions.

## Public acceptance implication

Public Query Acceptance Coverage should test concepts, not isolated phrases.

Each case should map to a parser/product concept such as:

- main intent preservation
- qualifier binding
- entity resolution
- stat threshold binding
- time/window binding
- comparison subject binding
- unsupported boundary
- no broad fallback
- result shape contract

Individual queries are examples that prove those concepts. They should not become one-off patches.

## Current working definition

Natural-language search is for quick, specific NBA stat answers.

Dedicated tools are for exploration, customization, ambiguity resolution, and deeper workflows.
