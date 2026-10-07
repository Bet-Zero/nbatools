# NBA Tools capability delivery: execution plan

Revised 2026-10-02. This is the single active queue. Read `AGENTS.md` and
`ROADMAP.md`; the source review and architectural alternatives are recorded in
[review-2026-10-02.md](review-2026-10-02.md). The Q1-Q6 order from PR #312 is
superseded. The owner's sample-query idea is not a mandated workflow.

## Start now

**First implementation: A1, correct player identity. Next: A2, consistent game
sample selection. Start O1, data/runtime verification, alongside A1 when a
second execution environment is available, otherwise interleave it.** Recent
team records remain an early deliverable within A2, not an isolated strategy.

Issue #314 (2026-10-03) launched execution and is folded in here rather than
tracked separately: the working scope below, the foundation map in section 2a,
the A1 result in section 4 and the continuation record in section 7.

Preserve existing work and inspect live main/open PRs before branching. At the
review boundary, main was `6a02fccb729206dd381653769f8a59adc90bdb26`, PR #312
was merged, and no PRs were open. No product implementation is claimed by this
plan change. All work packages below remain open until proven otherwise.

Do not turn this into another general audit phase. Establish the small execution
baseline while implementing A1/A2. Evidence unavailable in this review is
explicitly unknown; do not invent numeric results or repeat completed setup.

## 1. Why the work is grouped this way

The engine already has separate natural and structured entry points, 30
registered routes, shared data loaders and metric utilities, and established
renderers. The gaps are not all parsing gaps. Filter capability declarations are
split across parser allowlists and execution transport sets; route modules have
different sample filters; data contracts do not prove datasets are populated;
and operation/season freshness cannot wait until a final UI pass.

Sequence work by dependency, user value and observed correctness risk:

`identity + qualified rows -> time/sample -> operation/basis -> combinations`

`source feasibility + refresh/runtime ----------------------------------->`

Use examples to detect and validate gaps, but derive scope from the capability
map below. A failing phrase can be one symptom of an entire missing operation.
A passing phrase does not prove its siblings or the numeric answer.

## 2. Capability map and scope

**Working historical scope: 1996-97 onward, with priority on the 21st
century** (owner clarification, issue #314). Earlier history is optional, not a
completion requirement, and pre-1996-97 backfill must not block any package.
Do not delete older data that exists. Never present a partial span as a full
career: label the covered span instead (for example "since 1996-97") when a
player's career started earlier.

Plan data families from the capabilities they serve (section 2a), not one
failed phrase at a time. Stored facts, facts derivable from qualified stored
rows, and genuinely missing source data are different: when existing rows can
produce a statistic, record the formula/join and implement it rather than
planning another scrape. The owner's recollection of past scraping is a lead to
verify, not evidence of complete coverage.

This is a seeded plan, not a measured answer-rate report. "Present" below means
source implementations exist, not that all combinations or data are verified.
Update the evidence/status cells here as the work runs. Reuse the generated
route inventory and Raw QA families; do not create another route registry.

| Capability group | Starting evidence / gap | Required completion / package |
| --- | --- | --- |
| Player/team identity | Data-backed and curated resolution exist; #304 reported partial-alias collisions | Correct canonical identity across full names, aliases, accents, historical contexts and covered-data conditions; A1 |
| Summaries/scalars and team records | Present; record builder lacks last_n, sample filtering differs by route | Same defined sample across compatible views; current/explicit seasons, date ranges and last-N; A2 |
| Finders and counts | Present; generic phrase boundaries and compound gaps remain | All stated conditions, AND/OR/grouping, strict vs inclusive thresholds, games versus distinct entities, valid zeros; B1 |
| Leaderboards and top games | Present; stat vocabulary/basis and route coverage differ | Explicit totals/per-game/rates/count-of-events, eligibility and deterministic tie policy; B1 |
| Comparisons and head-to-head | Present; subjects and sample semantics require parity | Same requested basis/scope, correct matchup rather than accidental subject changes; C1 |
| Splits | Present; restricted filter interfaces | Apply the requested sample first, then the declared split; meaningful additional filters; C1 |
| Streaks and rolling stretches | Present, with route-specific eligibility/window behavior | Defined sequence, continuity, per-entity windows and correct thresholds/ranking; C2 |
| Opponent/context/availability | Partial; transport sets differ; conference/division reference covers only 2024-25/2025-26 | Season-aware joins and meaningful combinations, not cross-season union unless explicitly requested; C1/C2/D1 |
| Advanced metrics | Shared ratio formulas and sample-aware helpers present | Reuse correct formula/denominator at the requested sample grain; no average-of-percentages or invented rating substitutes; B1/D2 |
| Playoff/history/career | Present within the configured 1996-97 onward span (the working scope) | Distinguish games/series/appearances/rounds/franchises; label the covered span for careers that began earlier; C2 (pre-1996-97 backfill optional) |
| Bench/role and period/clutch | Contracts and some implementations exist; publication/coverage must be inspected | Actual source-backed answers at team/player/period grain; D1/D2 |
| Lineups and on/off | Routes/specs exist; prior sweep controls unsupported | Qualify exact source coverage and meaning, activate/complete rather than rebuild blindly; D2 |
| Calendar/factual reference questions | Schedule data path exists; championship/award questions currently bounded | Source-backed schedule and historical-reference answers in the extended queue; D1/D2 as appropriate |
| Browser/API and ongoing operation | Existing UI and R2/Vercel path; monitor passes do not prove all capabilities | Answer/render parity, measured latency, complete source coverage, repeatable refresh and rollover; O1/O2/E |
| Guided builders/profile pages | Explicit future surfaces in existing product boundary | Retained follow-on work after shared engine delivery; not silently deleted, and not a precondition for ordinary search combinations |

Core completion comprises the first ten groups' game-data-backed behavior,
including meaningful cross-family combinations defined during A/B/C. Extended
source-dependent behavior is D, and operation is O/E. This staged scope is not
permission to call the whole product finished when only A/B/C land.

### Bounded baseline, performed by agents

Start from the existing 30-route inventory and 16 acceptance families. For each
family, retain a compact row describing: desired operation, entities, metric and
basis, time/sample, relevant modifiers, required datasets/coverage, current
structured result, natural result, and remaining defect/dependency. Keep detailed
run output in existing generated artifacts, not this plan.

Run representative structured and natural versions over the SAME code/data:

- Structured correct, natural incorrect: binding/parsing/routing gap.
- Structured and natural both wrong: investigate shared computation/data against
  an independently calculated expectation; agreement alone proves nothing.
- Required source/coverage unavailable: data dependency, not a language defect.
- Correct payload, wrong/slow browser experience: presentation/runtime defect.

Cover the selected first packages immediately and extend other map cells during
parallel source reconnaissance. No exhaustive cross-product, arbitrary quota of
owner-written questions, new test runner, or baseline-only multi-session project.
Unknown cases stay unknown. Use a bounded corpus-wide run at integration, not
before every local edit.

## 2a. Foundation map (issue #314, 2026-10-03)

Compact and evidence-labelled. "Doc" means a repository contract or catalog
statement; "verified" names the check. The served generation
`queue-d-production-0574735-20260716` (684 files) was inspected on 2026-10-03
by `tests/test_served_data_coverage_real_data.py` in targeted R2 run
37118094775 (185 passed); its report is in that run's log and is regenerated by
`python -m nbatools.commands.ops.served_coverage`.

**Data view**

| Family | Serves | One row is | Declared coverage | Evidence | Stored / derivable / missing | Next gap |
| --- | --- | --- | --- | --- | --- | --- |
| `player_game_stats`, `team_game_stats`, `games` | Summaries, finders, records, leaders, comparisons, streaks | Player-game / team-game / game | 1996-97 to 2025-26, regular season and playoffs | Verified served: all 60 slices; every regular season has the league's game count (1189/1230, lockout and 2019-20/2020-21 totals); playoffs 66-89 games; every final game has two team rows and player rows for both teams. 57 slices carry only legacy (pre-receipt) manifests, 3 have versioned receipts | Stored | None for the core span; versioned receipts for older slices are optional |
| Player identity | Every named-player answer | Name and `player_id` on each player-game row | Follows game data | Verified: controlled names, fixture and data-free paths (A1 tests); real names await the R2 run | Stored; named-player rows are selected by `player_id` (A1b) | Real data: 12 names are two players each and 5 players have two spellings (listed in A1b); handled by id selection, one display name per id |
| `rosters`, `player_game_starter_roles` | Team membership, starter/bench | Player-season-team / player-game role | Coverage-gated per slice | Verified served: rosters 1996-97..2025-26; starter roles only 2024-25 and 2025-26 | Stored where served | D1: starter roles before 2024-25 |
| `team_conference_membership` | Conference/division opponents | Team-season | 2024-25 and 2025-26 trusted only | Doc (`data_catalog.md`) | Older seasons missing as rows; historical alignment is reference data, not box-score derivable | D1 |
| `schedule`, `standings_snapshots`, `schedule_context_features` | Calendar, rest/back-to-back, standings | Game / team-date / team-game | Standings regular season only | Verified served: schedule and standings 1996-97..2025-26; schedule context features only 2024-25 and 2025-26 | Rest/back-to-back derivable from game dates; standings stored | O2 rollover (done in the stream 4 PR); D1 context features before 2024-25 |
| Playoff series context | Series, rounds, appearances | Derived from playoff team-game rows | Follows playoff game data | Doc; round labelling unverified | Derivable from game rows | C2 |
| `player_season_advanced`, `team_season_advanced` | Advanced metrics | Player/team season snapshot | 1996-97 to 2025-26 | Verified served: all 60 slices | Stored snapshot plus derivable sample metrics | B1/D2 |
| Period, play-by-play/clutch, on/off, lineups | Quarter/half, clutch, on/off, lineup answers | Period window / event / presence split / lineup unit | Coverage-gated; contracts exist | Verified served: player/team period stats only 2024-25 and 2025-26; play-by-play, clutch, on/off and lineup files are not in the served generation | Period stored for two seasons; the rest missing | D2: pull and publish slices; period stats before 2024-25 |
| Awards, championships | Factual reference answers | Reference row | None | Not in game data | Team champions derivable from final-series results; player rings and awards need a qualified reference source | D1 |

**Operations view**

| Operation | Existing implementation | State | Next |
| --- | --- | --- | --- |
| Subject selection (players) | `entity_resolution.py`, called by `_matchup_utils.detect_player*` and comparison extractors | Sound after A1 (spelling/alias collisions) and A1b: rows by `player_id` through `_player_identity.select_player_rows`; lineup members through `resolve_players_in_query`; raw legacy alias fallback removed | Data-free and real-data tests (section 4); lineup answers still need D2 data |
| Subject selection (teams, populations) | `resolve_team*`, opponent quality/conference helpers | Unverified this session | C1 |
| Time/sample selection | `_seasons.py`, `_date_utils.py`, per-route `last_n`/date handling | Inconsistent. Verified on the fixture: "Knicks record last 10 games" refuses (`team_record` parses `last_n` with no execution path) while player last-N summaries answer | A2 |
| Predicates and joins | Condition utilities, finders, opponent/context filters | Parser allowlists and transport sets duplicate declarations (doc) | B1/C1 |
| Group / aggregate / count / rank | `aggregate_metrics.py`, leaderboards, occurrence counts | Present; basis and eligibility differ by route (doc) | B1 |
| Comparison | `player_compare`, team comparisons | Verified on the fixture for named-player pairs, including accented spellings and seasons | C1 parity of filters |
| Sequences | Streak and stretch modules | Present; per-route semantics (doc) | C2 |
| Output | `query_service` metadata/sections, React renderers | Verified for the A1 summaries through `/query` | E |

The map is complete enough for A1 and A2. Unknown cells stay unknown until a
package needs them; they are not a prerequisite for continuing.

## 3. Architecture decisions for implementation

Keep the public query service and result contracts. Reuse `_constants.py`,
`aggregate_metrics.py`, sample-aware metric helpers, `data_utils.py`, condition
utilities and the existing route adapters. `route_input_metadata.py` is currently
DESCRIPTIVE, not proof of execution; a function argument is not proof either.

Make the distinction between entity, sample, predicate, operation, ranking
metric and aggregation basis explicit at the existing parse/execution boundary.
Use existing fields first; add a small typed internal structure only where it
removes an observed ambiguity. Do not build a generic QueryPlan framework as a
prerequisite. Incrementally move repeated sample/filter behavior to shared
helpers while delivering at least two real consumers when that establishes reuse.

Consolidate capability declarations for touched routes where parser allowlists
and transport sets duplicate the same fact. Back them with execution assertions.
Do not merely add a third metadata table or permit a filter without implementing
it. Keep route-specific adapters for genuinely different data grains.

Natural and structured requests should reach the same semantics and calculations.
Output scope labels must describe the executed sample, not raw parse flags. Do
not start a cross-cutting receipt-ledger project unless a demonstrated remaining
failure cannot be fixed with the smaller existing boundary.

No immediate database, frontend, or LLM rewrite. If language-only failures remain
the dominant blocker after engine parity, the lead may run one bounded isolated
comparison of a constrained semantic parser with the current parser, using
held-out inputs, clause preservation, costs and end-to-end latency. No model
selects numeric answers from memory, executes arbitrary generated code/SQL, or
enters production without verified benefit and authorized cost/access. A
schema-valid request can still express the wrong question.

## 4. Delivery packages

Each package may contain small coherent PRs; it is not a demand for a giant PR.
All packages use the common acceptance rules in section 6.

### A1 - Identity integrity (first slice and A1b merged)

**A1b result (#319).** The real data (pinned
generation, all season types) has twelve names shared by two players: Brandon
Williams, Charles Smith, Chris Johnson, Chris Wright, Dee Brown, Glen Rice,
Marcus Williams, Mike James, Patrick Ewing, Reggie Williams, Steven Smith, Tony
Mitchell (four of them overlap inside one season). Five players carry two
spellings under one id: Bobby Portis / Bobby Portis Jr. (renamed during 2024-25),
Jonas Valančiūnas / Valanciunas, Vlatko Čančar / Cancar, Brandon Boston /
Boston Jr., Lester Quinones / Quiñones. Name filters merged the first group
("Mike James career" added two careers) and split the second ("Bobby Portis
2024-25" found no games, all stored as "Jr."; multi-season leaderboards listed
him twice).

- Every named-player filter (summary, finder, streaks, comparison, splits,
  occurrence counts, with/without/opponent-player) selects rows by
  `player_id` through `_player_identity.select_player_rows`, so all spellings
  of one player count.
- A shared name picks the player on the requested team, otherwise the one
  with the most games in the requested scope (Patrick Ewing career = the
  Knicks centre; "Mike James 2018-19" = the only Mike James that season). A
  note names the other player and says to add a team or season.
- Loaded player rows and season leaderboards show one name per id (latest
  spelling, keeping accents).
- Lineup "with X and Y" members resolve through the shared resolver (data
  full names, curated names, aliases; a bare last name only when listed after
  "with"). A listed shared last name ("hart": Josh and Jason) stays as typed,
  so the unit keeps its size and matches nothing rather than answering for
  fewer players; era/team disambiguation for it waits on D2 lineup data. The
  raw legacy alias fallback in `detect_player*` is removed.
- Independent review (separate agent) found three defects, all fixed with
  regression tests: player counts missed renamed spellings, ordinary words
  ("early", "love", "strong") became lineup members, float ids missed the index.
- Not changed: on/off rows (`player_on_off`, a D2 dataset) still match by
  name; with/without/opponent-player filters choose a shared-name player
  without a note. Stream 4 proposed a published `metadata/player_names.csv` to
  skip the cold full scan; it must carry `player_id` for these indexes.

Evidence: `tests/test_player_identity_selection.py` (data-free, controlled
frames with the real ids) and the A1b block of
`tests/test_player_identity_real_data.py` (values from raw rows by id), all
16 real-data identity tests passing in targeted R2 runs 37118187291 and
37130896078 (after the independent review fixes).


**Result of the first slice (branch `claude/issue-314-q0tbff`).** Reproduced,
then fixed in shared resolution, so every consumer (summaries, finders,
comparisons, API) inherits it:

- With covered data, "karl anthony towns" (no hyphen) answered with Carmelo
  Anthony, and "Tim Hardaway Jr" / "Gary Trent Jr" / "Jaren Jackson Jr"
  without the period answered with the father. Names now match regardless of
  hyphens and suffix/initial periods.
- Without the player in the loaded data, "Karl-Anthony Towns" answered with
  Carmelo Anthony; curated canonical names now match in full before shorter
  aliases. An earlier candidate also vetoed an alias whose neighbouring word
  was a known name; the independent checker showed that broke ordinary
  queries ("lebron christmas day games" became Todd Day), so it was removed
  and those cases are now regression tests.
- Names typed with their real diacritics broke comparisons ("Luka Dončić vs
  Nikola Jokić last 10 games" lost its second player); parser input now folds
  accents. "X vs Y 2025-26" no longer reads the season as a name typo.
- The fixture now seeds Karl-Anthony Towns and Nikola Jović instead of avoiding
  them; fixture names must resolve to themselves.

Evidence: `tests/test_player_identity_collisions.py` (controlled names,
data-free, fixture natural/structured/HTTP with values computed from the
fixture CSVs) and `tests/test_player_identity_real_data.py` (`needs_data`,
values from raw rows of the pinned generation). Remaining in A1b: select
players by `player_id` so identical-name players are not merged; route the
lineup/legacy alias scans through the resolver. A player absent from the
loaded data whose name starts with another player's alias (for example
"Anthony Black" with no Anthony Black rows) still falls back to that alias;
with 1996-97+ data present the full name wins. Original scope:


Reproduce the #304 Towns/Carmelo and Jovic/Jokic findings in their actual data
conditions. Full-name precedence already exists with a populated index; do not
assume every deployed query is wrong or solve this by avoiding the names in
fixtures. Review `entity_resolution.py` and the callers that bind query subjects.

Deliver correct named-player answers with covered data. Preserve specificity
when a full name contains another player's alias; handle canonical/ASCII accent
variants and shared-name cases. Use canonical IDs for joins where available;
keep names for presentation/aliases. Reuse a trustworthy identity source rather
than building another curated special-case list. Missing coverage must not select
a different player, but that negative control does not complete the positive task.

Acceptance: Towns, Jovic, their distinct collision players, another independently
chosen collision, single-player and comparison contexts, complete/incomplete
identity inputs, independent ID/value checks, API/render confirmation. This
package does not require a new identity warehouse or historical-data backfill.

### A2 - Time and game sample selection (open; follows A1 or independent edits)

Deliver recent records AND consistent sample behavior for the related summary
path. Inspect `team_record.py`, summary/split modules, `_seasons.py`, `_date_utils.py`
and existing windows before adding helpers. Shared code should unlock a second
consumer in this package, not be a speculative refactor.

Targets include team last-N records, player/team last-N summaries, explicit dates
and season/season-type scopes. Confirm per-entity N for league views. Keep game IDs
as the independent evidence of which rows were selected.

Distinguish "in the last N games" (choose the time sample, then conditions) from
"last N games with condition" (choose qualifying games, then N), and last N
meetings from last N overall games. Preserve an existing interpretation only if
it matches the requested meaning; record intentional compatibility changes and
update tests rather than silently relabeling. Define a default and expose its
scope where normal shorthand is clear; use a focused clarification for genuinely
different plausible meanings, not routine product-owner consultation.

Acceptance: two entity types and two answer families share a validated sample;
N greater than available games, midseason date cutoffs, home/opponent interactions,
regular season/playoffs, game ordering and deterministic same-date ties; summary
and record agree with independent selected game IDs/counts. The former Q1 examples
remain positive targets. Calendar/rollover integration belongs with O1/O2.

### B1 - Core operations and metric basis (open; depends on A sample semantics)

Complete find/count/aggregate/rank behavior over that sample, reusing existing
condition and metric helpers. Separate event conditions from the ranking key.
Support additive totals versus per-game values, shooting rates from appropriate
totals, games played, occurrence counts, and applicable minimum games/minutes/
attempts. Do not sum percentages, average per-game percentages blindly, or label
an approximation as an official advanced metric.

Targets include total rebounds leaders, three-pointer wording, compound player
30-point/10-rebound occurrence rankings, and game-level compound finders. Inspect
the generic phrase blockers (including "10+ assists and 0 turnovers") and replace
relevant ones only with verified support. Normal phrasing is not a new statistic.

Acceptance: independently computed counts/values, qualified zero-match cases,
strict/inclusive/equality and AND/OR/grouped logic, distinct entity versus game
count, ranking/eligibility and stated tie policy, player/team parity where
meaningful, and separate last-N versus top-N operations. Preserve working sibling
queries; do not patch exact sample strings.

### C1 - Meaningful combinations, comparisons and splits (open; after A/B)

Extend shared behavior across family adapters: season/date, location, opponent,
outcome, role/position and single-/multi-player participation where qualified
source data permits. Include comparisons and split views rather than declaring
them finished because their unfiltered example works.

Specify meaningful combinations in the map; use pairwise coverage plus targeted
three-way high-risk cases rather than every syntactic permutation. Prioritize
ordinary requests and shared causes. Inspect the 42 prior sweep flags, but do not
treat unchanged output as automatic proof of an ignored filter or awkward team
"starter" probes as normal desired features.

Use discriminating data and selected-game checks. Distinguish played/not-played
from injury, and game participation from simultaneous court presence. Respect
team membership at the relevant time; absence before joining a team is not the
same question as missing that team's game. Opponent classifications should join
at the stated season/date, not silently union qualifying teams across seasons.
The existing multi-season union is documented behavior, so any correction must
be explicit with before/after regression evidence.

Acceptance: correct joins, no multiplied game rows, qualified availability,
matched scope across comparisons, filter-before-split behavior, all requested
clauses accounted for, result labels consistent with actual execution.

### C2 - Sequences and historical semantics (open; after relevant A/B)

Finish streaks, rolling stretches, playoff round/matchup/appearance/decade views
and historical career queries. Reuse existing modules. Define consecutive team
games versus player appearances, date-filtered sequences, and last-N versus a
rolling best-N window. Do not bridge excluded games accidentally to manufacture
a streak, nor change a documented sequence meaning without explicit evidence.

Differentiate playoff games, series, rounds and appearances. Preserve historical
franchise identity. A configured 1996-97 start is not proof of complete careers
for players who played earlier; label the covered span ("since 1996-97") rather
than claiming a full career. Pre-1996-97 backfill is optional under the working
scope and does not block C2.

Acceptance: boundary/continuity examples, traded players and franchise changes,
regular/playoff separation, explicit coverage, and independent sequences/counts.

### D1 - Low-dependency dataset and reference expansion (open; feasibility starts in O1)

Default order: extend needed roster/role/conference/division coverage and team
bench scoring; historical team/playoff/championship reference; player championship
membership. Pre-1996-97 career coverage is optional under the working scope
(section 2) and is last in this order. These are different datasets/claims, not
one generic "rings" calculation. Retain factual awards/schedule requests in the
extended map where existing examples seek them; subjective opinion is separate.

For each slice: identify the existing reader/puller/contract, probe representative
coverage, qualify the source, implement the missing aggregate/join, verify, publish
under existing authority, and prove the deployed answer. Do not perform a full
historical backfill before a representative slice proves the pipeline works.
Keep incomplete eras open and explicit. Missing files trigger source acquisition
work, not permanent rejection or a new owner build-versus-refuse decision.

Acceptance: source and grain recorded, key/date coverage and values independently
checked, complete enough data for the requested claim, deterministic build and
repeatable update/publication, natural/API/rendered answer. Do not infer player
rings from a team-only champion list.

### D2 - Specialized event/period and on-court data (open; reconnaissance starts in O1)

Period data, play-by-play/clutch, lineup aggregates and on/off are source-distinct
subpackages, not a single serial dependency. Existing contracts/readers and some
route support already exist. Determine what needs activation/backfill versus new
computation before writing replacements. Sequence by usable source coverage and
user value, documenting reorder reasons in this queue.

Use representative slices first. Preserve game/period/stint/event grain, official
versus derived metric definitions, minute denominators and coverage. Team period
win/loss, full-game result within a period-selected sample and clutch record are
different questions. Do not conflate whole-game participation with on-court
on/off. Early source/access blockers stay named and do not stop A/B/C.

Acceptance: qualified source sample -> reconciliation -> reusable pipeline ->
correct calculation -> normal language -> actual deployed answer. Additional
storage/compute/provider cost requires the preserved authorization boundary.

### O1 - Data, verification and runtime baseline (open; parallel from the start)

Use existing remote validation and production tooling; do not add another R2
workflow. Verify the #311 test repair at the next relevant candidate integration,
and inspect actual manifests/key coverage, not the generation's date-like name.
Map essential versus optional datasets to the capability groups. Check a recent
season, a prior season, playoffs, and the earliest requested historical boundary.
A contract/schema existing in the repo is not evidence that its dataset exists.

For new-source feasibility, use one representative supported slice and record
source/access/coverage conclusions; no unbounded full-history download first.
Use the existing inventory/manifest/pipeline commands. Resolve code/data access in
a cloud execution environment, not by restoring the owner's laptop as a runner.

Measure representative deployed summary, ranking, multi-season and history
requests cold and warm, including actual browser-visible behavior. Separate data
read, identity-index construction, computation, serialization and render time.
The whole-corpus test duration is not an individual query latency measurement.
The current 20-second application/platform limit is a ceiling, not a UX target.
Proposed acceptance targets: warm common requests p95 <= 3 seconds, cold common
requests <= 10 seconds, admitted historical requests <= 20 seconds without
unhandled timeouts. Measure on a declared representative run; these are targets,
not current measurements. Do not alter monitoring thresholds to manufacture a pass.

Retain the documented fixed-plan/$0-metered-overage constraint; inspect external
cost enforcement rather than assuming in-process counters enforce a global
serverless quota. Request only genuinely missing provider consent/access. Do not
expand read-only validation/runtime credentials to enable publication.

### O2 - Refresh, calendar and measured runtime repairs (open; follows O1 evidence)

Reuse the staged pull -> validate -> process -> immutable publish path. Prove an
update reaches the served app and that a failed update keeps the last-good
snapshot. Select an authorized cloud scheduler/runtime only if none already does
this; preserve budgets and separate write authority. Automate refresh/rollover
under those boundaries rather than requiring recurring owner operation.

Separate the season implied by today's date from the latest available data; do
not silently substitute an older season. Resolve relative dates at request time
with a controllable test clock rather than relying on import-time "today".
Use sourced season/calendar events, not guessed All-Star dates for unsupported
years. Test season start, midseason, playoffs, offseason and a process crossing
midnight; historical numeric regressions get explicit dates/seasons or a frozen
clock, while freshness tests exercise the live-date contract separately.

Fix measured bottlenecks first: existing file/frame caches and generation keys,
bounded reads, precomputed identity/reference lookup if all-game scanning is the
cause, result size, and execution concurrency. Do not select a database/host
migration before those measurements establish why it is needed. Reuse validated
snapshot caching for CI only if profiling shows network repetition is material;
retain real R2-path integration checks and never cache credentials.

### E - Integrated delivered-product acceptance (open; targeted checks happen earlier)

Run the capability map through the API and actual desktop/mobile interface,
including unfamiliar wording chosen independently, realistic combinations,
empty-but-correct outcomes, numeric references and representative latency.
Check displayed entity/sample/metric/basis, tables, clipping/loading/error states,
query history/saved query behavior when affected, deployed code/data agreement,
refresh/rollover and rollback behavior. No broad visual redesign is required.

Every required core row must be answered and verified, not merely safe. D's
remaining items keep the extended program open. A known external blocker gets
its exact dependency and next action; it is not a completed feature. At the
milestone boundary select the next real capability group, including later guided
builders/profiles when their shared engine/data dependencies are ready. Do not
infer whole-product completion from a clean PR list or closed subsystem queue.

## 5. Work ownership, prioritization and continuity

The lead owns the map, next task, integration and technical choices. The maker
implements; the checker independently reviews meaningful semantics and numbers
using evidence, not agreement. Use at most two non-overlapping maker lanes
(engine and data/runtime); serialize changes to shared parser/service/data
contracts. Do not create a parallel agent swarm that the owner must reconcile.

Within available authorized execution sessions, continue after accepted merges.
At a usage/session limit, retain one exact next action here with branch/PR,
command/evidence and blocker. Do not promise background work without a running
execution service. If no independent checker can be invoked, record an exact
handoff and continue independent tasks; never relabel self-review independent.

Reprioritize when evidence shows higher user impact, wider reuse, a critical
wrong-answer risk, or a source dependency. Do not reprioritize merely because an
easy documentation/test cleanup appeared. Infra work must unlock a named active
capability, prevent material harm, or repair observed operation. Stop optional
refactoring when its targeted user outcome is achieved. Two repair/review rounds
with the same root cause trigger a lead diagnosis of the model/contract, not a
third cosmetic patch or another owner review loop; this is not permission to
merge a known defect. Batch unrelated maintenance outside the critical path.

## 6. Acceptance and evidence without new ceremony

For each unit keep a short semantic contract in its PR: meaning, dependencies,
examples, independent expected values and applicable checks. Do not require
separate preflight/spec/review documents for routine work.

- Deterministic small-data checks prove sample selection, formulas and joins.
  Independent expectations must not call the function under test. Include
  discriminating rows, zero denominators and incomplete coverage where relevant.
- Paired structured/natural tests prove binding and execution parity; explicit
  clause/identity checks prevent two identically wrong outputs from passing.
- Real-data checks use the exact candidate and one immutable generation; verify
  representative numbers against independent raw aggregation/qualified source.
  Neither engine output nor another agent's opinion is the expected answer.
- Select focused tests while editing. Run appropriate broad checks once the
  candidate stabilizes; full Raw QA/filter sweep at meaningful integration
  points. Do not rerun every overlapping suite after docs changes. Keep existing
  blocking CI and disclose skips; the informational needs_data job's failure is
  still relevant evidence for a data-dependent capability's acceptance.
- Preserve successful behavior and historical acceptance provenance. Legitimate
  temporary refusal tests can be replaced only alongside proved functionality;
  negative tests remain separate. Never remove difficult desired cases, mark
  unmeasured ones passing, or manufacture human acceptance.
- The checker supplies some unseen paraphrases/entities/thresholds AFTER the
  maker defines the semantic target. Record failure causes and repair shared
  behavior. Do not build a second permanent corpus solely for holdout management.
- Deployed result checks are part of each runtime/data change. A local pass is
  not a deployment pass. Existing renderer reuse needs a targeted spot-check,
  not another owner screenshot tour.

Owner update: what useful capability now works; what remains; verification
summary; next action; necessary owner action (normally none). Detailed code,
run IDs and numerical evidence belong in the PR/queue.

## 7. Live continuation record

| Package | Status at plan revision | Dependency / next action |
| --- | --- | --- |
| A1 | First slice merged (#315). A1b (id selection, renamed players, lineup member resolution) merged (#319); real-data tests passed (R2 runs 37118187291, 37130896078). #322: cold start builds the name/id indexes from the published `metadata/player_names.csv` (game-ordered `first_seen`; older or id-less lists fall back to the full scan) | Takes effect at the next published generation; deployed check for A1/A1b then. On/off still matches by name and with/without/opponent cross-filters pick a shared-name player without a note (D2); lineup answers wait on D2 lineup data |
| A2 | Team last-N records merged (#316). Explicit date windows merged (#317): from/to, between/and, since/after, before/until/through, lone ISO dates, cross-season ranges; impossible dates refuse (R2 run 37106273170). Samples PR #318: window vs qualifying last N ("30 point games in his last 10" counts inside the 10 most recent games; "last 5 games where he scored 30" and "last 10 wins" pick qualifying games first) on player/team finders, summaries and team records; last N now runs after every filter (teammate availability, special events, role, schedule context); "last N meetings with X" and "last meeting with X" select games vs X; spelled-out and reworded windows ("last ten", "previous 8", "5 most recent") no longer drop silently; count answers name the window and the team; with no season named, "last N" fills from the prior season when the current one has fewer games ("this season" or a named season keeps it inside that season). Real data: targeted R2 runs 37118297245 and 37132664753 (reach-back) passed (10 Raw QA cases incl. 4 new; 17 needs_data tests). Named-player summaries and finders cut each season to that player's candidate ids before combining: career query peak RSS 1.21 GB to 530 MB (R2 run 37156413363). "Past N games", "how many of X's last N games" and "how many of his last 10 wins did he score 30" (outcome window) read as windows; qualifying counts say they are limited to the N most recent. Independent agent review: all findings fixed and re-verified | "Lakers vs Warriors last N games" compares each team's own last N unless "meetings"/"head to head" is said; "last 5 minutes" still reads as last 5 games (period work, D2); window count phrases drop selectors ("last 10 home games" reads "last 10 games") |
| B1 | Totals vs per-game leaderboards in #317. Stream 3 branch `claude/rankings-stream-s8gywm`: condition-count rankings in adjective/shorthand form ("most 30 point 10 rebound games", "30/10 games", three conditions), exact-zero conditions ("10+ assists and 0 turnovers" no longer counts every 10-assist game; missing stats meet no bound), league-wide game lists and counts ("games with 10+ assists and 0 turnovers", "how often has a player had ..."), attempt-qualified shooting-rate leaders ("minimum 300 attempts", "5+ attempts per game"), games-played leaders, "best 3 point percentage" no longer read as top 3. PR #321: fixture checks pass; real data passed in targeted R2 runs 37130674898 (Raw QA 10/10, B1 needs_data tests) and 37131376968 (all needs_data tests in the touched files) | Independent check of #321 done: every claimed count, rate board and games-played board re-derived from raw fixture rows matched; its two findings are fixed in #321 (team "games played" duplicated column; "at most N" / "fewer than N" read as lower bounds) and real data passed again in targeted R2 run 37149301584. #321 merged. C2 streaks merged in #323 (league streak rankings, current streaks, streaks of any game condition, "this season"/career scope kept for streaks, career highs and the "covers 1996-97 onward" career label; targeted R2 run 37157463068). C2 team rolling stretches merged in #325: new `team_stretch_leaderboard` route ("best 10 game stretch for the Celtics", "which team had the best 10 game stretch", worst, scoring, points allowed, point differential, shooting and box-score-estimated ratings; named team lists and opponent lists; windows stay within a season); team "Game Score" stretches and two-team player stretches refuse (targeted R2 run 37173019011, 5 independent check rounds). C2 playoff series on the same branch: rounds before 2001-02 from each team's series order, series tables with Won/Lost/In progress (best-of-5 first rounds through 2001-02), single-team round records ("Celtics conference finals record"), year-named playoffs ("2026 playoffs" is 2025-26), series won/lost, team title counts as Finals series won ("Lakers titles since 2000", "did the Warriors win the title in 2017"); play-in games excluded. C2 league titles on the same branch: "which team has won the most titles since 2000", "top 3 teams with the most titles", "nba champions since 2010" rank every title winner by Finals series won with their title seasons; "who won the title in 2016" names the champion, Finals opponent and score; "champions" wording works for named teams; conference champions still refuse (rings were refused here and are answered since the player-rings slice below). PR #327 merged (league titles; also fixed a team split crash on "against winning teams" and stale round-record expectations found by full R2 run 37175338557). Bare-year and season ranges on the same branch: "from 2010 to 2015", "between 2000-01 and 2009-10", "2015-2017", "1999 through 2003", "since 2010 until 2020" now reach every route as a span (a bare year names the season starting in it, as "since 2010" and "the 2010s" do, except that for playoffs and titles it names the season ending in it, as "the 2016 playoffs" does; "2019-2020" is one season; future end years stop at the latest season; backwards spans are reordered; stat bounds like "between 20 and 30 points" are untouched); title counts over a range answer. PR #328 merged. Two-team stretches on the same branch: "Lakers vs Celtics best 10 game stretch" ranks each team on its own games; head-to-head stretches and "which Lakers vs Celtics player" stretches refuse. PR #329 merged. Stretch defaults on the same branch: "Celtics best stretch" / "LeBron best stretch" with no length rank 10-game windows and say so in a note; shooting wording ranks the rate ("3 point shooting" is 3P%, it was points); league shooting-rate stretches need the NBA season minimum made shots per game; player stretch lists no longer repeat overlapping windows of one hot run and get a headline. PR #331 merged. Lone years on the same branch: "Lakers record in 2019" is 2018-19, the season that ended in it, and a note says so; "in 2024 and 2025" covers both seasons; draft, birth and class years are untouched. PR #336. Series situations on the same branch: game N, elimination, closeout, deciding games and series scores ("when up 3-1", "down 3-1", "tied 2-2") filter team records, team and player summaries, game lists, player leaderboards and the team playoff record board ("who has won the most game 7s"); with no season named they cover every playoff season since 1996-97 and say so; split, compare and streak routes refuse the filter; series comebacks ("came back from 3-1") refused here and are answered since the series-comebacks slice below; "last N years/playoffs/postseasons" is a season window, not N games. PR #340 merged. Top-N game lists on the same branch: "LeBron top 5 scoring games", "best 5", "5 highest" list his five best games (the 5 was read as a 5-point floor and lists held 25 rows); "best 50 point games" stays a floor and "vs top 10 defenses" never sizes the list. PR #341 merged. Player rings on the same branch: "how many rings does LeBron have", "LeBron titles since 2015", "who has the most rings" count Finals titles won while playing at least one playoff game for the champion, with the title seasons and teams (unfinished Finals award none; ties are never cut); rings with a team or teammate, scoring/conference titles and back-to-back titles still refuse; any word beyond ring, question, span or the player's name refuses. PR #343 merged. Series comebacks on the same branch: new `playoff_series_comebacks` route, "teams that came back from 3-1 down", "Warriors blew a 3-1 lead", "have the Celtics ever come back from 3-1" list each series won after trailing (or lost after leading) by that series score, with round, opponent and span filters; player, two-team, home/away and regular-season comeback questions still refuse; counts, rankings, game conditions and span words the parser does not resolve refuse too. PR #346 merged. Stats by playoff round on the same branch: "LeBron stats in the Finals", "LeBron Finals averages", "Jokic stats in the 2023 Finals", "who scored the most points in the first round since 2000", "Lakers record in game 7s in the Finals" filter to that round's games (every playoff season since 1996-97 unless a span is named; "this/last season" kept); team round records keep their playoff routes. PR #350 merged; full R2 run 37337662565 on main 3a8216c passed. Titles, comparisons and single-game lists on the same branch: "won it all" is the title ("how many times have the Spurs won it all", "who won it all in 2016"); "this/last year" in a title question is one season; player and team comparisons take a round or series situation ("LeBron vs Curry in the Finals", "Lakers vs Nuggets in game 4s"); single-game lists rank every game in a named span or round ("most points in a game since 2000", "most points in a finals game", "most points in a game 7"; they ranked only the current season); "ever", "in NBA history" and "of all time" with no season named cover every season since 1996-97; "Lakers record in the first round this season" keeps the season. PR #355 merged. Single-game and single-season records on the same branch: "most points in an elimination/closeout/deciding game" list single games in that series situation; "most threes in a game by a team", "fewest points by a team in a game" rank team games (fewest from the bottom); "most points in a single season since 2000", "most points in a season ever" rank one row per player season (each season with its own games floor); "Lakers and Celtics record in the finals" is their Finals series history; "Celtics vs Heat in the eastern conference finals" refuses instead of comparing whole postseasons. PR #357 merged. Team and player best seasons on the same branch: "most wins in a single season", "worst record in a single season since 2010", "most team points in a single season", "best net rating in a single season" rank one row per team season (regular-season seasons under half the longest season's games left out, with a caveat); "LeBron best scoring season", "LeBron most points in a single season", "Jokic best rebounding seasons" rank that player's own seasons; "most wins"/"fewest losses" rank full records (they counted only won games, so boards showed records like 47-0). PR #358 merged. Record counts and apostrophe years on the same branch: "most road wins", "most home losses", "fewest wins in a single season", "best win % at home" rank the count or rate asked for (they could not be mapped, or "most home losses" ranked win%); "in '16", "the '90s", "'15-16" name seasons as their full years do ("Lakers record in '16" answered the current season). PR #360 merged. Team and shooting seasons on the same branch: "Lakers best scoring season", "Lakers best season", "Lakers most threes in a single season" rank that team's seasons (record or stat); "LeBron best three point shooting season", "Curry best shooting season" rank the shooting rate; "LeBron and Curry best scoring season" ranks both players' seasons; "lowest scoring team games" lists single games; decade boards rank what is asked ("worst record by decade" by win%, ascending; "fewest playoff wins by decade" answers); "most playoff wins" is a record board. PR #361. Team-season wording on the same branch: "Lakers top 3 seasons by wins", "Lakers best season with the most wins", "Lakers seasons ranked by wins", "best scoring season by points per game", "Celtics best defensive seasons" (lowest rating first), "Lakers best offensive rating season" rank that team's seasons; "who won the most games in a season" ranks single-season wins (PR #362). Player game lists: "Curry best 3 point shooting game", "LeBron top 5 games", "worst shooting game", "best shooting game since 2023" rank that player's games by the stat asked; rate lists leave out games under 10 shot / 5 three-point / 5 free-throw attempts, with a caveat (PR #364). Decades and ranges: "most points in a season in the 2010s" ranks single seasons in the decade (it ranked team wins), "this decade" is the current decade, "from 2010 to 2019" / "between 2010 and 2019" pass the leaderboard check, "LeBron best season" ranks his seasons by points per game with a note; "the 90s"/"the '80s" read as four-digit decades with a coverage note (PR #365). Shooting game lists keep "over 50%" / "% from three" / "under 15 points" bounds as conditions with the attempt floor, and "<team/player> season with the most X / best record" ranks seasons (PR #367). Player win and record boards: "most playoff wins by a player" counts games won by each player's team while he played (PR #369); "players with the best record", "rookies with the most wins", "guards with the best record against the Celtics" rank players by win % over their games (at least half the most games played); "Lakers best decade" / "which decade did the Lakers win the most" give the decade record table, while "best decade for points" and a player's best decade refuse (PR #372). League-wide shooting game lists ("best shooting games this season", "worst shooting games under 15 points") rank every player's games with the attempt floor (PR #375). League team-season boards rank each team season since 1996-97 and take wins thresholds ("teams with at least 50 wins ranked by net rating", "50 win teams", "seasons with at least 40 wins ranked by losses", "best defensive seasons by opponent points"); independently re-derived from raw fixture rows, the published stat now names the ranked column instead of the parser's reading (PR #378, targeted R2 runs 37581241206 and 37581988512). "players with 25 points and 10 rebounds", "players with 30 point games", "players with a triple double" list every player with a qualifying game, most often first (it refused or was unrouted; the earlier V1 refusal is replaced by this answer; targeted R2 run 37583404621; PR #380, five independent check rounds). Team shooting boards read a stated attempt minimum ("teams with the best 3 point percentage minimum 3000 attempts", "... 25 attempts per game") in place of the default floor, with a caveat (PR #381). Player season totals ("most total points this season") need one game instead of 20, and the per-game floor is at most half the most games anyone has played, so early-season boards are not empty. Next: C2 remaining gaps. Open: a bare "players with 30 points" (a game or a season total) is not routed; team totals and team per-game floors keep their fixed values |
| C1 | Samples stream. #324 merged: splits select the summary's sample first (wins/losses, dates, opponent, teammates, role, schedule, opponent quality, last N, stat conditions) and then bucket; player home/away buckets fixed for boolean `is_home`; summaries, team records and player/team comparisons apply every stat condition; "scoring N" thresholds (with joined "and N assists"); "compare the Lakers and Celtics" is a team comparison (R2 runs 37158029507, 37158280949). #333 merged (R2 runs 37204163105, 37204551083): conference and division opponents on player/team summaries, game lists, records, splits and comparisons, resolved season by season from 1996-97 (`_nba_alignment.py`, keyed by franchise team id; the served membership table still wins where it covers a season), so New Orleans counts as East through 2003-04 and the 7-team Pacific/Midwest divisions apply before 2004-05; multi-season opponent quality ("vs winning teams since 2015") is also season by season on those routes; "Lakers vs Warriors last 10 games" is their last 10 meetings, reaching back across seasons ("compare the Lakers and Warriors last 10 games" keeps each team's own); playoff records against a division answer; "vs the Pacific" and "vs Pacific teams" name the division and "vs the West coast" refuses; "compare LeBron and the Lakers" asks which reading instead of dropping the team. Fixture checks in `tests/test_opponent_groups.py`; real data in `tests/test_c1_opponent_groups_real_data.py` (alignment checked against how often each pair meets) | A head-to-head comparison with a stat condition refuses. "LeBron top 5 scoring games" lists 25 and reads 5 as a points threshold (sent to the Rankings stream). #337 merged: "Lakers and Warriors last 10 games vs the Celtics" is each team's games against Boston, "Lakers and Warriors record" is each team's record ("Lakers vs Warriors record" stays their meetings), quality bars apply on comparisons and after a division ("Atlantic Division winning teams"); fixture standings carry `team_abbr`/conference rank. #342 merged (R2 runs 37241437228, 37241881124): "Lakers and Nuggets series history" is their playoff history, "Lakers and Celtics leading scorers" ranks both rosters, "the best teams" is an opponent-quality term, "LeBron vs Curry against winning teams/the Celtics/the West" compares both players against that group, and "LeBron vs Curry's Warriors" stays a single-player game list. #344: team, player and league-wide streaks against a conference, division or quality bar ("longest winning streak vs the West"); a second group word refuses. #345 merged: team and player occurrence leaders against a conference, division or quality bar ("which team has the most 120 point games vs the West"); the resolved "vs <group>" phrase is masked before the player scan so "West" is not read as a surname. #347 merged: distinct player counts ("how many players scored 40 vs the Warriors") keep the opponent, special events and a default season. #348 merged (R2 runs 37261597991, 37261998223): distinct counts with two or more conditions ("how many players had 30 and 10"); "Lakers and Warriors playoff record" with no time words is their whole playoff history (4-2 in 2023 on real data) and publishes that range, while "this postseason"/"2026" keep one season. #349 merged (R2 runs 37262919099, 37263735267): comma lists ("25 points, 5 rebounds, 5 assists") and three-way "and" lists keep every condition (one condition was silently dropped, giving 36 instead of 18); distinct player counts apply "off the bench"/"as a starter" (starter roles are served from 2024-25) and their headline counts players. #351 merged (R2 runs 37264170937, 37285651046): "most triple doubles off the bench" filters the occurrence leaderboard by role (only lineup wording; "starting in 2023-24" is time); "between 20 and 30 points and 10 rebounds" is one ranged condition ("20-30" in headlines); player-count headlines name the opponent. Slice 11: "at most 5 points"/"5 points or fewer" are upper bounds (read as 5+), distinct player counts take upper bounds and lists ("under 10 points and 10 rebounds" counted games), "5 assists between 2023 and 2025" is a season span (read as an assist range, 0 instead of 166), and summaries/records/splits apply every condition in a list (dropped the second); thresholded count headlines read "games with 5+ assists". #352/#353 merged: "or fewer", "at most", verb-led and points-allowed bounds ("held opponents to 100 or fewer") are ceilings; points-allowed floors ("allow 110 or more"); "in at least 10 games" repeat counts. #354 merged: opponent box-score bounds ("allow 15+ threes", "opponents had 20 turnovers", "held opponents to 10 threes"; "shot" reads attempts) on records, finders, summaries, compares, splits and team streaks. Slice 14: later list items keep the opponent subject ("gave up 15 threes and 50 rebounds", "held teams to 10 threes and 100 points"); points allowed on team streaks; "best record when opponents made 15+ threes" ranks the matching games; "Lakers record vs Celtics when they have 15+ threes" keeps the Lakers as subject (#356 merged). Slice 15: final margins ("won by 10+" no longer reads as 10+ points; "lost by 20 or more", "decided by 3 or fewer", "within 5 points", "by double digits", bare "won by 1" is exact) on records, finders, summaries, compares and team streaks; player rows use the team margin; outcome streaks keep own bounds ("winning streak with 15+ threes", "streak of 120 point wins") (#359 merged). Slice 16: adjective game lists with a second condition ("LeBron 30 point games with 10 assists", "Lakers record in 120 point games with 15+ threes"); a "with <number> <stat>" bound is never a teammate when only read scope follows it, and "or" alternatives repeat the first clause. Slice 17: separated lists ("30 point games did LeBron have with 5+ threes"), good/bad/winning/losing opponents after a stat bound, record leaderboards keep a bare bound ("best record with 15 threes") and drop teams under a fifth of the leader's sample games. Slice 18: every glossary opponent-quality term ("vs playoff teams", "against teams that made the playoffs", "contenders") is read scope after a stat bound, and a quality term no team meets ("non-playoff teams" when all qualified) gives no games instead of the unfiltered sample. Slice 19: operator words inside a condition list are read ("games with 30 points and 10 or more assists" kept only the assists; a clause it cannot read still refuses), and "more than N" is the same strict floor as "over N" instead of a bare number. Slice 20: "record when LeBron plays at least 35 minutes" applies the minutes bound (it answered with the whole record, and the ceiling form gave no games); negated bounds read the right way round ("no fewer than 10" is a floor, "not over 2" a ceiling), and "record in games with no more than 10 turnovers" no longer reads "no ..." as a missing player. Slice 21: player clauses inside a team-record sample ("when LeBron plays and scores 30" is his 30-point games, not team points; "when Luka sits/rests" is absence; "... but loses" keeps only losses), a second player's clause on a player route refuses instead of being dropped, and "below N" is a ceiling. Slice 22: team and opponent totals on a player's games ("LeBron games when the Lakers score 120", "30 point games when opponents score 120", "when opponents make 15 threes") read the team rows of the same game instead of the player's own stat, the player's own bound beside them is kept, and "opponents score 120" / "below 100" bound the opponent on team records too. Slice 23: "his team / LA / the opposing team scores 120", "the Lakers allow 120" and "commit 20 turnovers" are team or opponent totals; a team named beside "vs <opponent>" restricts to his games for it; a team total beside a player event no longer refuses; and "highest scoring games with 10 assists" ranks by points with the assist bound kept. Slice 24: a rank word names the ranking stat and "with 30 points" / "30 point games" / "a 30 minute game" stay game conditions ("most rebounds in a game with 30 points" refused, "top 5 games by assists with 30 points" dropped the points, "fewest points in a 30 minute game" dropped the minutes). Slice 25: "10 assists at most/max", "30 minutes or under", "no-more-than" and "never more than" are ceilings, "when held to 100" is at most 100, "vs below/above .500 teams" filters opponents, and team "lowest scoring games" run lowest first. Open: "Lakers vs Warriors last 10 games with 120 points" compares each team's own games (stated reading); player "most 30 point games vs the East" goes to season leaders and refuses (Rankings area); "this decade" on a pair playoff record reads one season; conditions are joined across players ("Jokic had 30, Murray had 10 assists"); a single-team opponent shows as its abbreviation in count headlines |
| C2 | Remaining gaps (2026-10-07, stream 3). Streak counts (PR #383): "how many 10 game winning streaks do the Celtics have", "how many times did the Lakers win 5 straight / win 6 games in a row", "how many players have had 5 straight 20 point games", "how many teams won 8 straight last season" count separate runs of that length (a 12-game run is one 10+ run) and list them; "winning streaks of 5 or more games", "streaks of 5+ straight double doubles", "games with a three", an opponent-points-only streak and "since 2024" on streaks (the three-season default overwrote it) answer. Independent check: two rounds, every count re-derived from raw rows; real data targeted R2 runs 37594051110, 37595445876. Franchise identity (PR #384): team and opponent filters match the franchise team_id, so "Nets record in 2002-03" (New Jersey, 49-33), "Thunder playoff appearances" (Seattle seasons), "vs the Thunder" and "Thunder record without Durant" keep earlier names, with a caveat naming them; a historical abbreviation alone stays its era. Independent check: three rounds (with/without player and occurrence-count splits fixed); R2 runs 37597362987, 37598110537. Playoff appearances (PR #385): "how many times have the Lakers made the playoffs" counts seasons (it counted games); "how many Finals appearances does LeBron have" (10; it refused as team-grain) and player boards count seasons with a game played at that stage; last appearance, longest/current runs, droughts and misses for teams and players; "most consecutive playoff appearances" (Spurs 22, 1997-98 to 2018-19), "longest playoff drought" (Kings 16) and "which teams made/missed the playoffs" (latest postseason) boards; "against teams that made the playoffs" stays an opponent filter. Independent check: two rounds (missed/made lists, league droughts, player runs, ties fixed); R2 runs 37599476304 and the follow-up. League boards one row per franchise (PR #386): multi-season record, team-leader, playoff round record, decade (named per decade) and title boards and league occurrence boards merged Seattle/Oklahoma City etc. (R2 runs 37605782216, 37606524832). PR #387: "fewest playoff appearances" ranks from zero and never cuts a tie, "teams that missed the playoffs in 2024-25" answers, plural "winning streaks" list every run of 2+ (a cut list says how many there were) (R2 37607823336). Opponent clauses: "when playing / facing / beating teams that made (missed) the playoffs" and "opponents who ..." filter opponents (they switched to playoff games) | Next: remaining C2 history views. Deployed: production build of #385 verified READY on Vercel (includes #383-#385); #386 onward wait on Vercel's 100-deployments/day free limit (each PR push builds a preview) and the live query cannot be probed from the agent sandbox (proxy 403). Open: a bare "Lakers winning streaks since 2024" (no length) gives the longest only; player run spans name the requested range, not his first season; a final-margin clause on a win or beat count ("how many times did the Lakers win by 20", "beat the Celtics by 20") is dropped (pre-existing); "teams that beat the Lakers" is unrouted; "most conference finals appearances" with no game at that round in range returns no result |
| D1 / D2 | Open; O1 inventory done | The served generation has no play-by-play, clutch, on/off or lineup files, and period stats, starter roles and schedule context only for 2024-25 and 2025-26 (section 2a). New NBA pulls are parked with refresh (no reachable runner, 2026-10-04). Ready for the next refresh: standings keep conference/division and rebuild `team_conference_membership` per season (1996-97 onward once each season is re-pulled; Midwest division accepted) |
| O1 | Served data verified; merged (#320) | Active generation `queue-d-production-0574735-20260716` (684 files): every core slice 1996-97..2025-26 present with the league's exact game counts and consistent box scores (targeted R2 run 37130724578). 57 of 60 slices carry legacy manifests only. `python -m nbatools.commands.ops.served_coverage` reprints it. Deployed latency measured from the production monitor: first query median 16.7 s, 22 of 24 runs over the 15 s limit |
| O2 | Rollover and speed fixes merged (#320); refresh stays manual (parked) | The latest season now follows the served games (2026-27 becomes current at its first final game); refresh pulls the calendar season; readiness flags a missing season from November 1. R2 file-exists checks come from the generation manifest, and compiled patterns stay cached: warm queries 6-7 s to 0.2-0.35 s, a cold career query 75 s to 25 s, top scorers cold 11 s to 3 s (runs 37118449909 vs 37130724578). Publication now writes `metadata/player_names.csv`; the name index reading it (sent to stream 1) removes the 145 MB, 9 s cold-start load at the next published generation. Career queries (after #319): cold 15-23 s, warm 5.8 s; they build 30 full season frames (698 MB) before selecting one player, peak RSS 1.2 GB against 1024 MB production functions (OOM risk inferred, not observed); per-season player filtering before concat sent to stream 2 (run 37133184207). With that filtering (#318 head, run 37156742933): peak RSS 541 MB, cold 15.6 s, warm 5.5 s; warm stays slow because the 128 MB frame cache evicts and reloads the 30 seasons (1.4 s when every season fits); caching the per-player frame was suggested to stream 2. Deployed first query after #320: 13.3 s with no retry, against a 16.7 s median before (monitor run 37156411994); the remaining cold cost is mostly the name index, which waits on the next published generation. Concurrent R2 downloads (#334) cut the cold profile from 40.8 s to 21.4 s: player name index 13.0 s to 2.3 s, cold career 20.6 s to 10.9 s, peak RSS 517 MB to 613 MB (runs 37203557138 main vs 37203555215). A cheaper frame-size estimate (#335) took a warm career query from 5.6 s to 3.3 s. Remembering a published generation's freshness date (#338) removed manifest hashing from every answer: warm "Celtics record last 10 games" 0.27 s to 0.03 s and "Jokic vs Embiid 2024-25" 0.27 s to 0.09 s (runs 37221554495 main vs 37221552704). The follow-up does the same for the manifest rows behind `/freshness` and `/readiness`, which the site calls on every page load. Refresh automation parked 2026-10-04: GitHub-hosted runners cannot reach the NBA (stats.nba.com times out, cdn.nba.com 403; reachability runs 37187347774, 37187608214, 37187843846), and the owner's computer, the chosen fallback, is unavailable; the owner said refresh timing is low priority. Kept for whoever resumes: `download-generation`, `changed-files`, `publish-generation --only-if-changed-from` (stale-base guarded), `prune-generations` (#330), and per-season conference membership rebuilt from standings in every refresh. Resume by running those from a machine the NBA allows (a scheduled-task runner was built and reviewed, then dropped; see PR #332 history) |
| E | Open | Integrated acceptance, without replacing per-feature delivery checks |

Update these rows as work lands. Keep this one queue; no new phase tracker.

Parallel workstreams. The remaining queue splits into four streams that can
run as separate threads. Each owns its modules; a shared file has one owner,
and other streams send changes to that owner rather than editing it.

| Stream | Packages | Owns | Starts |
| --- | --- | --- | --- |
| 1. Identity | A1b (`player_id` selection for identical names, lineup "with X and Y" and legacy alias scans through the resolver) | `entity_resolution.py`, `_matchup_utils.py`, lineup scans | Now |
| 2. Samples and combinations | A2 rest ("in the last N" vs "last N with a condition", last N meetings), then C1 | `_date_utils.py`, `_parse_helpers.py` season/date helpers, `data_utils.select_most_recent_games`, `team_record.py`, summaries/splits | Now; C1 after B1's operation contract |
| 3. Operations and rankings | B1 (compound occurrence rankings, "10+ assists and 0 turnovers", qualified rate leaders, games played), then C2 | `_leaderboard_eligibility.py`, `season_leaders.py`, `season_team_leaders.py`, occurrence leaders, `_compound_event_authorization.py`, finders | Now |
| 4. Data and runtime | O1 (generation manifest, data view in section 2a, deployed checks), O2 (calendar/refresh, performance), then D1/D2 source slices | `data_source.py`, pipelines, workflows, deployment docs | Now; D after O1 |

Shared files and owners: `natural_query.py` routing (stream 3; others keep
their edits to small, separate hunks and rebase often), the Raw QA corpus and
frontend-copy fixtures (append or edit only your own case ids), this queue
(each stream updates only its own rows), and the full R2 run (one at a time;
streams use targeted runs per change). E (integrated acceptance) starts once
streams 2 and 3 land their contracts.

Validation cadence: a full R2 run (Raw QA replay about 30 minutes, serialized) is
not a per-fix wait. Keep building the next fix while one runs, verify each fix
with its focused needs_data tests and relevant Raw QA cases, and run the full
replay once per batch or integration point.
