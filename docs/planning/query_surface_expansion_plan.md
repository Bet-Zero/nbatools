# Query Surface Expansion Plan

> **Role: active planning doc.**
> This file synthesizes the user-supplied parser example sets and notes into a
> practical plan for expanding the natural query surface.
>
> Source inputs synthesized here:
>
> - `NBAToolParserExamples.md` — 100 example questions
> - `NBAToolParserMixedExamples.md` — 50 paired question/search-form examples
> - `NBAToolParserNotes.md` — parser behavior notes and shorthand guidance

---

## 1. Why this doc exists

The current engine already supports a broad set of NBA queries, but real manual
usage showed an important product truth:

- the app works
- the UI is real
- many shipped routes are useful
- but the natural-language surface still feels too brittle outside curated examples

The three parser docs are valuable because they do **not** just list more query
ideas. They reveal the bigger product requirement:

> The parser must support **question form, search form, and compressed shorthand**
> as first-class input styles.

This doc turns that insight into a concrete expansion plan.

---

## 2. Core parser/product principle

The parser should be designed around **intent + slots**, not around whether the
input is a grammatically complete question.

That means these should often map to the same underlying parse target:

- `Who has the most points over the last 10 games?`
- `most points last 10 games`
- `points leaders last 10`

Likewise:

- `How has Luka played when Kyrie didn't play?`
- `Luka when Kyrie out`
- `Luka w/o Kyrie`

And:

- `What is the Celtics' record against teams over .500?`
- `Celtics record vs teams over .500`
- `Celtics vs contenders`

The long-term parser should treat all three styles as normal.

---

## 3. Input styles that must be treated as first-class

## 3.1 Full question form

Examples:

- `Who leads the NBA in points per game this season?`
- `What is the Bucks' record when Giannis Antetokounmpo was out?`
- `How often has Stephen Curry made 5 or more threes this year?`

## 3.2 Search phrase form

Examples:

- `points per game leaders this season`
- `Bucks record when Giannis out`
- `Curry 5+ threes this year`

## 3.3 Compressed shorthand form

Examples:

- `points leaders last 10`
- `Luka w/o Kyrie last 5`
- `Knicks clutch`
- `SGA vs winning teams`
- `Jokic td this season`

These should be treated as normal supported input shapes, not edge cases.

---

## 4. Slot model to optimize for

Most desired queries in the example docs decompose into a stable set of slots.

| Slot | Meaning |
| --- | --- |
| `subject` | player, team, league, position group, lineup |
| `metric` | points, rebounds, TS%, record, net rating, frequency, etc. |
| `aggregation` | per game, total, average, max, count, rate, record |
| `timeframe` | this season, last 10, since Jan 1, past month, career |
| `filter_opponent` | team opponent, opponent strength, defense rank, contender class |
| `filter_teammate_status` | when X was out, with X, without X |
| `filter_threshold` | 30+ points, under 110 points, 5+ threes |
| `context` | home, away, wins, losses, clutch, quarter, starter/bench, B2B |
| `comparison_type` | leader, best, hottest, most efficient, frequency, record |

The parser should prefer extracting these slots over relying on sentence grammar.

---

## 5. High-value feature families surfaced by the example docs

## 5.1 Leaders and rankings

Examples from the input docs:

- points-per-game leaders
- total rebounds leaders
- best offensive rating team
- best true shooting percentage
- best field goal percentage among guards
- best net rating team

### Already partly aligned
The current engine already supports many leaderboard shapes.

### Remaining expansion themes
- broader phrase coverage for stat names
- broader phrase coverage for ranking language (`best`, `hottest`, `most efficient`)
- more support for context-constrained leaderboards

---

## 5.2 Recent / lately / over the past month

Examples:

- `Who scored the most points last night?`
- `Which players have been the hottest from three lately?`
- `What teams have the best record over the past month?`
- `Who has had the most steals lately?`

### Product significance
This is one of the biggest “normal user” phrasing families.

### Implication
The parser should support fuzzy recency wording such as:

- `last night`
- `lately`
- `recently`
- `over the past month`
- `past 2 weeks`

These may need explicit date/window normalization rules.

---

## 5.3 Last-N / since-date / over-span

Examples:

- `last 5 games`
- `last 10 games`
- `since January 1`
- `since March 1`
- `over the last 15 games`

### Product significance
This is now a core natural-query expectation, not an extra feature.

### Implication
The parser should normalize all of these cleanly into the same timeframe model.

---

## 5.4 Best games / biggest games / hottest stretch

Examples:

- `biggest scoring games this season`
- `best games by Game Score`
- `hottest 3-game scoring stretch`
- `best two-way games this season`

### Product significance
Users naturally ask for:
- best single games
- best short stretches
- most dominant or most efficient performances

### Implication
This is a major query family and should not be collapsed into generic season leaders.

---

## 5.5 Against good teams / contenders / opponent-strength buckets

Examples:

- `against teams over .500`
- `against contenders`
- `against top-10 defenses`
- `against playoff teams`
- `against elite frontcourts`

### Product significance
This is a big missing family in most simple parsers.

### Implication
Some of these are directly grounded today (`teams over .500`), while others need a
clear product definition (`contenders`, `elite frontcourts`, `good teams`).

The important rule is:

> do not fake these labels.

If `contenders` or `good teams` are supported, define them explicitly.
If not, do not pretend they are interpretable.

---

## 5.6 When a teammate didn't play / was out

Examples:

- `Bucks record when Giannis was out`
- `Luka when Kyrie out`
- `Austin Reaves stats without LeBron`
- `Which players see the biggest usage increase when their star teammate is out?`

### Product significance
This is one of the most important user-facing contexts.

### Current state
With/without-player support is now part of the shipped surface in meaningful cases.

### Remaining expansion themes
- broaden phrasing coverage
- improve reliability on shorthand (`w/o`, `out`, `didn't play`)
- eventually expand to richer “with star off” style questions where the data model supports it

---

## 5.7 Frequency / how-often queries

Examples:

- `How often has Jokic recorded a triple-double this season?`
- `How often has Curry made 5+ threes this year?`
- `How often has a team scored 140+ this year?`

### Product significance
This is a core mental model for sports users.

### Implication
These should cleanly map to:
- count of games
- count of distinct players/teams
- count over a specified sample

Distinct-entity count should be treated as its own supported subfamily.

---

## 5.8 Record when ___

Examples:

- `Mavericks record when Luka scores 35+`
- `Knicks record when allowing under 110`
- `Warriors record when Curry makes 6+ threes`
- `Lakers record when LeBron and AD both play`

### Product significance
This is an extremely natural and valuable sports-query family.

### Implication
Record-under-condition support should be treated as a first-class route family,
not just a side effect of other team-summary routes.

---

## 5.9 Splits and contexts

Examples:

- home / road
- wins / losses
- first half / fourth quarter
- clutch
- one-possession games
- back-to-backs
- starter vs bench
- on/off

### Product significance
These are normal sports contexts, not niche analyst-only questions.

### Implication
They should be modeled as explicit context slots rather than ad hoc phrasing.

---

## 6. Query families that are especially important for future expansion

From the three input docs, these are the highest-value future parser/product families:

1. **Search-form support**
   - `most points last 10 games`
   - `best road record this year`
   - `Curry 5+ threes this season`

2. **Compressed shorthand support**
   - `Luka last 5`
   - `SGA 30+ games`
   - `Bucks ortg w/o Giannis`
   - `Celtics drtg last 10`

3. **Word-order flexibility**
   - `best scorers last month`
   - `last month best scorers`
   - `scorers best last month`

4. **Normalization rules**
   - `vs` → against
   - `w/` → with
   - `w/o` → without / when X did not play
   - `last 10` → last 10 games
   - `this month` → current month window

5. **Implicit intent defaults**
   Examples from the notes doc:
   - `Giannis last 10 games` → default to summary
   - `Curry 5+ threes this season` → default to frequency/count
   - `LeBron best games` → default to best game outputs
   - `Celtics vs contenders` → default likely record unless another metric is made explicit

---

## 7. Recommended parser rules from the notes doc

## 7.1 Question form should be optional

Do not make “is this a full question?” part of the main routing decision.

## 7.2 Non-question phrasing should be first-class

Search-bar phrasing is normal product usage, not sloppy input.

## 7.3 Missing verbs should be tolerated

Examples:

- `Giannis last 10 games`
- `Lakers against above .500 teams`
- `Thunder in clutch games`

These need defaults, not failure.

## 7.4 Intent should come from content words, not grammar

Prefer parsing around:
- entity nouns
- stat names
- ranking words
- context words
- timeframe phrases
- threshold operators

## 7.5 Defaults should be explicit and documented

Examples worth formalizing:

- player + timeframe only → summary
- team + opponent-strength only → likely record
- player + threshold event only → frequency/count
- `best games` → game-level ranking

Defaults should not be accidental.

---

## 8. Suggested parser-training/test-data strategy

The paired examples doc suggests a good robustness strategy.

For many important intents, maintain three forms:

1. **Full question**
   - `Who has the most points over the last 10 games?`
2. **Search phrase**
   - `most points last 10 games`
3. **Compressed shorthand**
   - `points leaders last 10`

This is a better parser benchmark than question-only examples.

### Recommended test-data tiers

#### Tier 1 — canonical examples
Clean, high-signal examples for each supported intent.

#### Tier 2 — paired search-form variants
Question + non-question variants that should parse the same way.

#### Tier 3 — shorthand variants
Compressed inputs that should still resolve acceptably.

#### Tier 4 — ambiguity/unsupported boundaries
Inputs that should fail clearly instead of guessing.

---

## 9. Recommended implementation order

### Phase A — search-form parity on existing capabilities
Focus on making already-shipped capabilities easier to access.

Examples:

- `most points last 10 games`
- `best road record this year`
- `Curry 5+ threes this season`
- `Bucks record when Giannis out`

### Phase B — shorthand normalization layer
Support common compressed forms:

- `vs`
- `w/`
- `w/o`
- omitted `games`
- abbreviated stat names where already grounded

### Phase C — explicit default-intent rules
Document and implement sane defaults for short queries.

### Phase D — new capability families
Only after phrasing coverage improves, expand into bigger missing families such as:

- opponent-strength buckets
- stretch queries (`hottest 3-game scoring stretch`)
- richer context filters (`clutch`, `back-to-back`, `starter vs bench`, `on/off`)

---

## 10. Guardrails

1. Do not treat vague labels like `good teams` or `contenders` as supported unless they are explicitly defined.
2. Do not rely on embedding/semantic luck for search-form support — add explicit test coverage.
3. Do not broaden docs claims beyond what is actually shipped and tested.
4. Prefer honest unsupported responses over silently wrong route guesses.
5. Use real user phrasing as the roadmap driver whenever possible.

---

## 11. Immediate practical use

This doc should guide the next parser/product passes in three ways:

1. **Backlog source** — use its query families as the next-wave roadmap
2. **Test-data source** — convert the examples into parser/routing regression tests
3. **Design guardrail** — keep search-form and shorthand support in scope, not as afterthoughts

---

## 12. Relationship to other docs

- `docs/reference/query_catalog.md` = living shipped inventory of what users can ask now
- `docs/reference/current_state_guide.md` = strict verified current behavior
- `docs/reference/query_guide.md` = broader reference/examples doc
- **this file** = planning doc for expanding the query surface based on real example sets and parser notes
