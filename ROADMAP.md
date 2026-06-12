# Roadmap

This is the owner's plan for taking the product from "works on its own
catalog" to "answers real fan questions correctly — or refuses honestly."
Written June 2026. Plain language on purpose; see
[docs/reference/owner_guide.md](docs/reference/owner_guide.md) for how the
system works.

## The destination

A product the owner understands and steers, where:

- questions typed the way real fans type them get a right answer or an
  honest refusal — never a confident wrong answer;
- the testing exam reflects real fan language, not just catalog phrasing;
- the data is fresh enough that "this season" means this season;
- launch, whenever the owner chooses it, is just branding and a domain —
  not more engineering.

## The operating rule (how every session works)

One session = one slice of ten queries through this loop:

```text
try it  →  owner judges the output  →  agent fixes  →  lock it in the corpus
```

- **Owner's job:** write queries the way fans type them, judge outputs
  (good / wrong / should-refuse), and make build-vs-refuse calls. No code
  reading required. Judging outputs *is* steering the product.
- **Agent's job:** diagnose, fix, prove with tests, lock with corpus cases.
- **The one number that matters:** every fan-battery query either answers
  correctly or refuses honestly. Confident wrong answers must be zero.
  Coverage (the share that answers rather than refuses) grows over time.

## Phase 1 — Build the real-fan exam

The root cause of the "Shai points per game" failure was the exam, not the
engine: all 314 corpus cases were catalog-polite phrasings. Fix the exam
first.

- Owner brain-dumps 50–100 queries phrased like a fan on a phone
  (lowercase, nicknames, "ppg", "how many rings", typos). Agent adds ~100
  more from the audit findings and common fan patterns.
- Organize into themed ten-query slices under `qa/exploratory/slices/`
  (nicknames, average asks, schedule/future asks, championships, playoff
  "this year" asks, typos).
- Run the baseline so the real pass/fail picture is visible.

**Done when:** the fan battery exists and the baseline number is known.

## Phase 2 — Kill the lying answers first

A wrong answer is worse than a refusal. Fix in order of trust damage:

1. **Unique first names resolve automatically** (the systemic "Shai" fix —
   the code already does this for unique last names; extend the same rule
   so no obvious name ever needs hand-listing again).
2. **Unanswerable question shapes must refuse:** championships/"rings",
   "when do they play next", and similar future/schedule/award shapes
   currently get a confident nearest-match answer. Route them to the
   existing unsupported card.
3. **No silent year substitution:** "playoff stats this year" must not
   quietly answer with last year's playoffs. Refuse or caveat loudly when
   the asked-for season has no data.
4. **Queued guard misfire:** "Jokic scoring average" (exploratory id
   `jokic_scoring_average_guard_misfire`).

Each fix gets corpus cases the same day, like the per-game fix did.

**Done when:** the fan battery contains zero confidently-wrong answers.

## Phase 3 — Widen what answers

Work the battery slice by slice. Most failures will be phrasings that
should map to an existing answer type — cheap parser fixes like "per game".
Lock each into the corpus. Coverage climbs session by session.

**Done when:** owner is satisfied with the battery coverage number.

## Phase 4 — New answer types, deliberately

The battery will surface a short list of genuinely missing answer kinds
(likely candidates: a championships answer for "rings" questions, a yes/no
"did X make the playoffs"). For each one the owner decides: build it, or
refuse it forever. What gets built goes through the existing promotion
rules. Nothing gets built just because someone asked.

## Phase 5 — Wake the data (one session, whenever)

Run the refresh pipeline, add playoffs to the freshness report, decide
whether the current playoffs are in scope. Not urgent by the owner's call,
but it gates truthful "this year" answers.

## Phase 6 — The launch leap (parked)

Name and branding, a friendlier unsupported card that suggests supported
queries, starter experience, and the custom-domain cutover checklist in
[docs/operations/deployment.md](docs/operations/deployment.md). Parked
until the owner says go.

## First three sessions

1. Owner writes ~50 fan queries (30 minutes of their time); agent slices
   them and runs the baseline.
2. First-name auto-resolve + refuse-shapes for championships and schedule
   questions.
3. First battery slice through the loop, end to end.
