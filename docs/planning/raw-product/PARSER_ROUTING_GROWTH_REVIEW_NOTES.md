# Parser/Routing Growth Review Notes

## 1. Purpose

This is a working notes document for the current product-level review of NBA
Tools parser/routing growth risk.

The goal is not to declare the current release broken. The current Raw Product
release candidate remains technically strong and launch-ready with notes. The
goal is to capture a known future-growth risk now, while it is fresh, so the
project is not relying on memory to revisit it later.

This document should be updated as the review continues. When the review is
complete, use it as source material for a concrete parser/routing hardening plan.

## 2. Current understanding

NBA Tools is a query-first NBA stats product. The user types a normal-language
basketball stats question, the system interprets it, chooses the correct route,
executes the query, and renders a structured answer.

A simplified chain:

```text
User query
  -> parser interprets text
  -> router chooses the query route
  -> backend executes the route
  -> structured result is returned
  -> frontend renders the answer
```

Examples:

```text
"Who leads the NBA in points per game this season?"
  -> season_leaders

"Lakers road record last season"
  -> team_record

"Jokic home vs away this season"
  -> player_split_summary

"Curry longest streak with at least 3 threes"
  -> player_streak_finder

"Lakers playoff history"
  -> playoff_history
```

## 3. Product user model

The intended user is not someone asking completely vague or subjective prompts.
The product is for users who ask reasonably stat-shaped basketball questions in
normal language.

Target query style:

```text
Who had the best defensive rating on the Celtics this year?
What are the Cavs players' plus-minuses in the playoffs this year?
How many times did Luka Doncic score 40 points and have 10 assists since joining the Lakers?
Which centers have the most rebounds this season?
Jokic home vs away this season
Lakers record against the West last season
```

The system should be forgiving about phrasing, but it should not invent meaning
for vague questions.

Working principle:

```text
Forgive phrasing.
Do not invent meaning.
```

Examples:

```text
"best defensive rating on Celtics"
  -> stat-shaped; should work if the data/route supports it

"best defender on Celtics"
  -> subjective unless a metric is chosen; guide or no-result rather than fake certainty

"cooled off lately"
  -> too vague unless a defined trend metric exists
```

The product promise should not be "ask any NBA question." A better promise is:

```text
Ask stat-shaped NBA questions in normal language.
```

## 4. What parser and routing mean

### Parser

The parser reads the user's text and extracts meaning.

Example:

```text
Celtics record against the East this season
```

The parser should identify:

```text
team = Celtics
query type = team record
opponent filter = Eastern Conference teams
season = this season
```

### Routing

Routing chooses the backend route/function that should answer the parsed query.

Example:

```text
team = Celtics
opponent_conference = East
season = 2025-26
  -> route = team_record
```

### Execution/rendering

After routing, the backend executes the selected route and the frontend renders
the structured result. The frontend should not be responsible for deciding NBA
facts or fixing parser mistakes.

## 5. Why this area is a future risk

The current system works for the tested release boundary, but natural-language
query support can become fragile as more query families are added.

The main risk is not a crash. The main risk is a wrong route.

A wrong route means the product answers a different question than the user asked.
That is worse than a clean unsupported/no-result response because it can look
credible while being wrong.

Example risk:

```text
User asks: Warriors net rating this season
Current boundary: single-team advanced-stat scalar summaries are unsupported
Bad future behavior: route to league-wide team advanced leaderboard and show a broad table
Correct behavior: no_result/filter_not_supported or a guided unsupported response
```

Natural language has overlapping phrases. Adding support for one phrase can
accidentally affect another.

Example collision risk:

```text
Celtics record against the East
  -> opponent-conference team_record filter

Celtics conference finals record
  -> playoff/round concept, not opponent-conference filter

Celtics record against east coast teams
  -> geography phrase; currently unsupported
```

## 6. `natural_query.py` concern

The existing architecture audit identified `natural_query.py` as a major
maintainability risk because it is very large and contains many parsing/routing
rules. The concern is not simply line count. The concern is that a large natural
query module tends to accumulate:

- phrase rules
- aliases
- exceptions
- unsupported-boundary checks
- route ordering decisions
- embedded business logic
- side effects such as notes/caveats during routing

This makes future changes harder to reason about. A new rule can accidentally
change behavior for an old query unless route collisions and unsupported
boundaries are guarded by tests.

Important framing:

```text
Do not panic-rewrite the parser.
Do not casually keep growing one giant parser file forever.
Add parser-growth guardrails now.
Refactor/extract gradually and safely.
```

## 7. Desired long-term parser shape

The preferred conceptual model is bucket-first routing:

```text
User query
  -> broad intent bucket
  -> route-specific parser rules
  -> structured route
  -> execution
  -> result renderer
```

Possible broad buckets:

- player_subject
- team_subject
- comparison
- leaderboard
- finder
- record
- split
- streak
- playoff
- unsupported_or_ambiguous

This reduces collisions because every query is not competing against every
possible phrase rule at once.

Example:

```text
"Celtics record against the East"
  -> team_subject + record
  -> team_record rules

"LeBron vs Durant comparison"
  -> comparison
  -> player_compare rules

"players with most personal fouls"
  -> leaderboard intent + unsupported metric
  -> no_result/filter_not_supported
```

## 8. Optional guided UI modes

A pre-query selector could help some users and can reduce ambiguity, but it
should not be required for the main product experience.

Possible optional guided modes:

- Ask freely
- Player question
- Team question
- Compare
- Find games
- Leaderboards
- Playoffs

Recommendation:

```text
Do not force a category selector before every query.
Consider optional guided modes later.
The backend parser should still be able to classify intent without relying on user selection.
```

If a user chooses "Team," the parser can prefer team routes. If a user chooses
"Comparison," the parser can prefer compare/matchup routes. But the selector is
only a helper, not a substitute for safe parser architecture.

## 9. Immediate guardrails to consider

Before adding more supported query families, create a parser/routing growth
process.

Every new support area should define:

- accepted phrases
- rejected/guarded phrases
- expected route
- expected no-result/unsupported behavior
- required data contract
- result contract expectations
- frontend rendering expectations
- raw QA cases
- frontend-copy cases when copy changes
- visual QA cases when UI/layout changes
- deployment/R2 checks if new data files are required

Example for opponent-conference filters:

```text
Accepted:
- Celtics record against the East
- Lakers record vs Western Conference teams

Rejected/guarded:
- east coast teams
- conference finals
- divisions
- historical conference coverage outside trusted seasons

Expected route:
- team_record

Expected unsupported behavior:
- no broad fallback
- no_result/filter_not_supported or conference_coverage when data is unavailable
```

## 10. Possible first hardening work

These are candidate changes to evaluate after the review is complete.

### A. Parser/routing growth rules doc

Create a permanent policy doc that says how future natural-query support gets
promoted.

Likely contents:

- accepted phrase requirements
- rejected phrase requirements
- route collision checks
- unsupported-boundary regression rules
- data-contract requirement
- no broad fallback rule
- QA/corpus requirements
- release-doc update requirement

### B. Parser decision map

Document current high-level route decision order in plain language.

Goal: make it easier to see where a new feature would collide before code is
changed.

### C. Collision test strategy

Add or document targeted tests that make sure nearby phrases do not accidentally
route to the wrong family.

Example groups:

```text
opponent conference vs conference finals vs geography phrases
team record vs team comparison vs team matchup
player comparison vs player-vs-opponent summary
leaderboard vs top single-game performances
subjective/trend phrases vs supported stat metrics
```

### D. Gradual `natural_query.py` extraction plan

Do not do one massive rewrite. Extract stable pieces gradually:

- stat aliases/constants
- player/team aliases if duplicated
- date parsing helpers
- unsupported-boundary definitions
- route-family-specific helpers
- note/caveat construction helpers

### E. Intent bucket preflight

Investigate how much of bucket-first routing already exists and whether a light
classification layer can be added without changing behavior.

## 11. Non-goals

These are explicitly not the goal right now:

- Do not rewrite the entire parser in one pass.
- Do not force users into a category selector before every query.
- Do not loosen unsupported boundaries to make the product appear smarter.
- Do not add broad fallback answers when route confidence is low.
- Do not automatically turn vague subjective prompts into stat answers unless
  the metric is explicit or the UI clearly asks the user to choose a metric.
- Do not expand query support without data and QA contracts.

## 12. Open questions from review

Use this section as we continue the product review.

1. Should the product have a permanent "Parser Growth Rules" doc before any
   next feature promotion?
2. Should current parser/routing behavior be documented as a decision map before
   code changes?
3. Which route collision groups are highest risk?
4. Which `natural_query.py` extractions are safest and highest value?
5. Should optional guided query modes be part of onboarding later, or remain a
   deferred UX idea?
6. What is the right beta cadence for reviewing query feedback and converting it
   into parser/corpus work?

## 13. Current working recommendation

The current working recommendation is:

```text
After this product review discussion is complete, start with a parser/routing
growth guardrails preflight. Do not begin with a parser rewrite. First define the
rules, collision strategy, and safe extraction plan. Then execute the smallest
hardening wave that prevents casual parser growth from becoming a future
maintainability problem.
```
