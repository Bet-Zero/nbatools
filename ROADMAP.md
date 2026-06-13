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

## Phase 2 — Kill the lying answers first ✅ (closed 2026-06-12)

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

**Closed 2026-06-12:** battery liars fixed (sessions 1–2), then rings and
schedule refuse-shapes, the playoff year substitution, and day-window
data-currency notes (session 3). The core promise — right answer or
honest refusal — now holds across the fan battery and the audit list.
Known leftover (low priority): the multi-player availability boundary
message ("mavs when luka and kyrie both play") is honest but muddled.

## Phase 3 — Widen what answers

Work the battery slice by slice. Most failures will be phrasings that
should map to an existing answer type — cheap parser fixes like "per game".
Lock each into the corpus. Coverage climbs session by session.

**Done when:** owner is satisfied with the battery coverage number.

## Phase 4 — New answer types, deliberately

The battery surfaces genuinely missing answer kinds (championships/"rings",
rookie leaderboards, bench scoring, team defensive rating and pace, clutch
record, league-wide threshold windows like "who dropped 40 this week").

Built so far (2026-06-12): single-team advanced-stat scalars (defensive/
offensive/net rating, pace — answered with league rank), league-wide
threshold game lists ("who dropped 40 this week"), rookie leaderboards
(roster experience_years == 0 per season, coverage from 1996-97), and
league-wide starter/bench player leaderboards (trusted per-game starter
flags; seasons without coverage refuse honestly).

Deferred after data checks (2026-06-12), with the reason each is parked:

- **Clutch record/filters** — no clutch dataset exists on disk (schema
  stubs only). Needs a new NBA API pull through the pipeline and a data
  contract before any clutch answer is possible.
- **Championships/"rings" answers** — playoff data starts at 1996-97, so
  a derived rings count would confidently lie about earlier history
  (Jordan would get 2, not 6). Needs a curated champions reference table
  added through the data-contract path; until then the explicit refusal
  stays.
- **Team bench scoring** ("Celtics bench scoring") — the trusted
  starter-role data exists, but a team-level answer needs a new
  per-game bench-points aggregation contract; parked as a clean,
  well-scoped future build.

Fan battery 2 (2026-06-13) — comparisons, career, playoffs, matchups,
multi-condition, subjective traps. Fixed flagship comparison bugs
(season/stat modifiers no longer block "jokic vs embiid this season";
"lebron vs jordan career" refuses instead of silently answering for one
player). Built team-scoped player leaders ("Lakers leading scorer",
"who scores the most for the Celtics", "Celtics leader in assists") and
sophomore leaderboards (experience_years == 1). Refused subjective "best
player on X" and two-player "combined" totals. Confirmed already-honest:
"mj/wilt career" and "most improved player" (friendly refusal card),
bare "jokic vs embiid" (deliberate ambiguity prompt).

Owner's standing call: every legitimate NBA query/stat gets built
eventually — refusals are temporary boundaries, not permanent decisions.
The list is a prioritized build queue. Two rules keep it sane: build
smartly (each through the existing promotion rules, refusing honestly
until its turn), and never let coverage expansion become the only thing
being worked on — trust, honesty, data, and product quality advance
alongside it.

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
