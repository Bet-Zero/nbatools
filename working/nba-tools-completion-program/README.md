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
| Playoff/history/career | Present within the configured 1996-97 onward span | Distinguish games/series/appearances/rounds/franchises; partial coverage is not a full-career claim; C2/D1 |
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

### A1 - Identity integrity (open; first implementation)

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
for players who played earlier; link missing coverage to D1 rather than declaring
full-career completion from a partial answer.

Acceptance: boundary/continuity examples, traded players and franchise changes,
regular/playoff separation, explicit coverage, and independent sequences/counts.

### D1 - Low-dependency dataset and reference expansion (open; feasibility starts in O1)

Default order: extend needed roster/role/conference/division coverage and team
bench scoring; historical team/playoff/championship reference; player championship
membership and older career coverage. These are different datasets/claims, not
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
| A1 | Open; next | Reproduce identity cases and implement the smallest general correction |
| A2 | Open | Inspect sample semantics; recent records plus related summary parity |
| B1 | Open | Reuse A sample contract; complete operation/basis and compound counts |
| C1 / C2 | Open | Apply A/B behavior to combinations, splits/comparisons and sequences/history |
| D1 / D2 | Open | O1 feasibility first; each source-backed slice then delivers independently |
| O1 | Open; parallel | Existing R2 validation, actual coverage and deployed measurements |
| O2 | Open | Act on O1; calendar/refresh and measured performance repairs |
| E | Open | Integrated acceptance, without replacing per-feature delivery checks |

Update these rows as work lands. Keep this one queue; no new phase tracker.
