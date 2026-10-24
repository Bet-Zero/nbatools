# NBA Tools execution queue

Owner-approved direction: **2026-10-15**. This remains the only active queue.
Read `AGENTS.md` and `ROADMAP.md`. The owner approved the reassessment and asked
for an immediately executable plan with durable agent-to-agent continuation.
Runtime continuation is recorded below; implementation, independent fixture evidence,
real-data acceptance and deployment remain distinct.

The old A1-first start and four-stream execution instructions are superseded.
The A/B/C/D/O/E capabilities and unfinished requirements are retained, not reset.
The full pre-revision queue and detailed PR history remain available at the
[immutable October 15 snapshot](https://github.com/Bet-Zero/nbatools/blob/ce5c0cef2f46cbd086c48535b427df142be4aa8a/working/nba-tools-completion-program/README.md).
`review-2026-10-02.md` is historical rationale, not the current sequence. Do not
require a new agent to read that history before starting the task below.

## Resume checkpoint

Reconciled **2026-10-24** from live main/PRs and the [October 21 pushed stop
checkpoint][saved-stop]. Replace current state here; keep detailed receipts in
existing PRs/bindings. Historical records below are evidence, not restart instructions.

| Field | Current handoff |
| --- | --- |
| Outcome / authority | **Product development remains paused at the owner's October 21 stop.** PR535 completed the planning/handoff cleanup. The current owner authorization covers only bounded CI/deployment-selection efficiency work and its normal landing; product work stays paused. At the saved stop no product worker or public-validation run remained active and deployment watch `6ad58b9b748881919020300facc32fa9` was disabled; this operational assignment starts none. Core-1 is not accepted. No owner technical decision or manual QA is outstanding for this handoff. |
| Operational assignment | [Delivery-efficiency task PR](https://github.com/Bet-Zero/nbatools/pulls?q=is%3Apr+head%3Aci%2Fbounded-delivery-efficiency) contains the diagnosis, independent review, controlled selection cases and landing receipts for narrow planning-document CI, removal of duplicate fast/full matrices, and non-build-input deployment suppression. No application repair, data change or dependency upgrade. Stop after its applicable gates and landing. |
| Main / deployment | Reconciled main `4f77a69d6c189f51539e9da222294b2dad8577fd` includes PR535 and [PR534][pr534]; PR535's blocking PR and full post-main CI passed (development audit remains advisory). Last saved public identity (October 21): `835ad17f9e67d8efdd124c189992de56778e319e`, deployment `dpl_2FXMGuTm3SbWf1L6kRJSctV9PGR8`, asset `index-ClijrUhz.js`. At reconciliation, main's application/API/frontend/config/dependency bytes match that accepted runtime; helper/docs differ. This assignment changes deployment selection only, not application behavior. This reconciliation makes no fresh deployment claim. Follow newer accepted main without resetting preserved work. |
| Accepted / unresolved delivery | PR531/532's bounded consumers passed 26 public desktop/mobile answers and 52 readiness checks in [39389938663][public-531-532]; independent conclusions and hashes are in the [durable receipt](cloud-operations/public-531-532-835.json). The fresh `4aad08d6` deployment then failed [39392363519][failed-first-request]: first comparison HTTP504 `FUNCTION_INVOCATION_TIMEOUT` at 20,233 ms; stat-pair checks passed. The prior deployment was restored. **First-request reliability/cause and K12 cold/warm acceptance remain unresolved**; see [failure/restore][restore] and [final conclusion][restore-final]. A later passing request did not close this defect. |
| Parked repair | [PR533][pr533], `codex/medical-subject-scope`, pushed handoff `39aa65afdf74fc2aba70a54f9eddc1ef22c3779d`; runtime `bb616ed307b5ffa5f8c75d850cd76e1e21421051` is **not accepted**. The [independent check][medical-check] found that coordinated “medically cleared Derrick White and a healthy Jaylen Brown” drops status spans and applies a played cohort (20 pass / 1 role failure). The separate browser WIP is pushed at `codex/medical-subject-production-gate` / `b1aeb0998772cc619547fb1649662d4b69bcc54e`; syntax/lint only, no capture or acceptance. Reconcile it with PR534's helper diagnostics before use. No medical-status capability is delivered. |
| Data / source blocker | Last verified generation `availability-opening-s4-v1-20261017`, manifest SHA256 `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`; [October 18 publication receipt][publication] records 703 objects / 402,749,125 bytes and retained previous generation. Five qualified participation games are not season-wide absence evidence. All **46 original positive absence obligations** on [PR462][pr462] (`13df00fb84f142a0f4803ac196ebe9ff3a1355db`) remain open. PR515's Boston 17 observations are staged only: Tatum explicitly inactive in game `22500702`; other-game membership/tenure/nonmembership remains unaccepted. Reuse the [exact source/identity handoff](collection-requests/tatum-membership-20260201.md), including the remaining Milwaukee identity request. Current medical-owner repair needs no acquisition/provider hunt. |
| Preserve | Keep PR533/462 open and their positive tests, source oracles, revealed/private controls and unpushed integration ports. The [saved stop][saved-stop] names the three remotely preserved `codex/parked-*-20261021` branches, exact original/preservation revisions and equal trees, plus the medical browser WIP. They are preservation copies, not merge candidates. Preserve original worktrees, ignored evidence and the untracked generated-asset symlink; do not reset, prune or force-push. [Preservation record](cloud-operations/preservation.json) records unavailable original-volume `c10936b` work; recovery is not claimed. Local paths in old receipts are provenance, not prerequisites available in this checkout. |
| NEXT / reason | **Stop after this operational assignment lands. On an authorized product resume, qualify/reproduce and repair the saved first-request HTTP504 within the existing 20-second execution budget.** This repairs a confirmed deployed failure and advances K12's reliable answer-delivery obligation; warm/cold milestone goals below remain unchanged. Use PR534's retained evidence, not unchanged public retries. After that dependency is resolved, resume the existing PR533 coordinated medical-owner correctness repair through normal independent/source/CI/deployed gates. Preserve White/BOS–LAL 2–0 and Embiid/Jokic controls; never equate played, active and healthy. No product work starts under this operational authorization. |

### First-session procedure

1. Read AGENTS and ROADMAP, then this checkpoint and the relevant acceptance row.
   Inspect remote, live main, current branch/dirty work and open/recently updated
   PRs without resetting another session's work. The linked task PR is the first
   lead; compare its latest pushed README and discussion with this main copy and
   current owner decisions. A branch name alone is not proof a worker is active.
2. Follow the freshest applicable handoff, preserving newer work. On a blocked
   branch, keep this same README checkpoint on the task branch and link its exact
   revision from the existing PR. A successor can find it through live PRs even
   before main is synchronized; no separate main documentation PR is needed at
   each stop, and failing runtime must never be merged to publish its checkpoint.
3. If product work is authorized, perform NEXT with its recorded reason. If it has
   already succeeded, use its evidence and select the next justified outcome under
   AGENTS. Do not replay historical investigations, source arithmetic or broad
   suites solely to refresh status. An owner stop is not an invitation to select
   independent product work.

### Blocked-branch continuation

Preserve #462's required positives and exact source dependency; do not repeatedly
run known missing-data failures or add unrelated features to its red branch.
Within an authorized product session, a genuinely independent required outcome
may proceed from live main through its own checks and review. Keep the blocked
obligation visible; never replace it with refusal/xfail/skip or relax a gate.
Synchronize a compact main pointer at the next safe independent merge. Turn
completion is not product completion or evidence of a background worker.

Detailed S1–S5 source arithmetic, artifact hashes, prior failed runs, K03 receipts
and earlier PR history remain in the [immutable pre-cleanup queue][prior-queue]
and [latest pushed stop][saved-stop]. Consult only the record needed for the next
action; the acceptance table and carry-forward section below retain live gaps.

## 1. Preserved product and starting evidence

1996-97 onward is the working historical scope, prioritizing the 21st century.
Earlier history is optional. Do not delete existing older rows or call a partial
career complete. Salary/trade-rule work is outside this repository's purpose.

| Area | Evidence retained at the revision boundary | Implication |
| --- | --- | --- |
| Core data | O1 recorded 684 served files and 60 player/team/game season-type slices, 1996-97..2025-26; most older manifests are legacy. Coverage tests/runs are in the immutable prior queue | Reuse the qualified snapshot. This is not exhaustive independent proof of every value or current freshness |
| Identity/sample | A1/A1b and A2 implementations include id-based selection, renamed players, dates and last-N semantics; shared helpers and real-data tests exist | Do not rebuild from scratch; preserve and verify affected behavior |
| Operations/history | B1/C1/C2 delivered substantial counts, rankings, splits, conditions, streaks, franchise/series/history work, most recently #450 season lists | Implemented does not mean every combination or deployment is accepted. Old individual fixes are not the new sequence |
| Participation/period | Starter roles, period rows and schedule-context features were served only for 2024-25/2025-26; rosters and core games span the historical window | Existing-snapshot slices can proceed. Earlier role/period coverage remains an explicit dependency |
| Specialized data | Served play-by-play, clutch, lineup and on/off files were absent; awards/injury/status require qualified reference sources | Missing sources remain unfinished work; do not derive injury or simultaneous presence from participation |
| Runtime | Prior profiling found material read/index/frame costs and useful fixes; the previously pending compact name lookup is now published (O1 below) | Publication does not establish cold/warm performance; follow the current measured defect before suggesting a migration |
| Product acceptance | Existing monitor checks availability and one representative route, not all numeric answers; integrated E remains open | P3 is a real interface/numeric/latency checkpoint, not a monitor screenshot or green-CI claim |

Reuse existing helpers such as `_player_identity.py`, `_condition_utils.py`,
`aggregate_metrics.py`, sample selection in `data_utils.py`, `query_service.py`
and existing route adapters. Locate exact implementations on live main first.
`route_input_metadata.py` is descriptive; accepting a kwarg is not proof it runs.

## 2. Execution order and work ownership

**P0a + P0b -> P0c integration -> P1 -> P2 -> P3**, with **O** independent or
interleaved. P0c can integrate a ready independent candidate sooner; do not wait
idle for unrelated work. P1 implementation can proceed while independent evidence
is pending, but dependent acceptance cannot bypass P0's actual correctness gates.

One lead owns this checkpoint, semantic decisions and integration. At most two
non-overlapping makers plus an independent checker. Only one active writer owns
`natural_query.py` and shared request/parser/service semantics. P0b/workflow or O
work can be a second lane if its files/dependencies truly do not overlap. File
ownership is recorded in the checkpoint, not inferred from the former streams.

P0/P1/P2/P3/O are work-package labels in THIS queue, not new projects, dashboards,
registries or parallel roadmaps. Use coherent PRs. A package may need several
PRs, but each must advance a named outcome; no quota of phrase fixes.

## 3. P0 - Secure existing work

### P0a. Participation is not injury or status

**Original defect on #462 (October 15):** it mapped injured/similar status
words to missing participation and healthy/available/active to playing. Its
fixture removed player rows to justify those readings. The current remaining
medical-owner defect is parked on [PR533][pr533]; see the checkpoint for its exact
failure and preservation state. The source facts do not support that equivalence.
Inspect `docs/reference/data_contracts.md` and the
current participation contract; meaning must be checked before arithmetic.

Preserve real improvements to teammate names/pairs and valid participation
wording. Games in which a player did not play may answer did-not-play/without
questions when coverage and relevant membership are qualified. They cannot be
advertised as injured games or a cause of absence. Likewise played does not mean
healthy, and listed active/available does not prove actual minutes played.

Continue the relevant existing candidate when authorized. Status-specific wording
without a source needs honest unavailable/clarification behavior,
not a converted participation answer. Colloquial 'out' can only use a clearly
stated did-not-play meaning where unambiguous; never imply injury. Do not equate
resting/suspended/sidelined or other causes with all absences without evidence.

Acceptance: independently check one and two teammates, reordered clauses and a
stat bound beside participation; retain positive answers for another team/player.
Use discriminating fixtures with both playing and non-playing games, membership
boundaries and unavailable coverage. Explicit injury/status cases must not pass
using absent/present rows. Check selected game IDs, counts, values and scope text
through natural and structured/API paths, then targeted real data for participation
and affected deployed output. Safety for missing injury data does not complete an
injury-statistics feature. If the bug already landed, repair main via a bounded PR.

### P0b. Required numerical acceptance must actually fail when wrong

**Enforcement delivered in [PR464](https://github.com/Bet-Zero/nbatools/pull/464).**
Do not repeat the original workflow investigation to refresh this queue. Required
feature tests remain non-optional and bound to a resolved SHA and pinned generation;
exploratory checks cannot replace them. Preserve full Raw QA/filter-sweep and
secret-free CI. The acceptance contract below remains controlling.

Acceptance in a controlled test/validation context: a required assertion failure,
a typo or empty required selection, zero executed tests, all-required-skipped run,
missing required data and execution error cannot become a pass. A legitimate
unselected job in targeted mode is not the same as skipped required tests. A valid
positive selection must execute and pass. Report required selected/executed/skipped
counts and underlying job conclusions. A deliberate failure experiment is clearly
labeled, isolated from production data, and leaves no failing test in main.

Use the existing `r2-validation` environment; no credential expansion, duplicate
workflow or branch-protection change. Independent checker verifies enforcement,
not just YAML appearance. Inspect required underlying jobs/counts and block
dependent merges on any real failure or unavailable evidence.

### P0c. Preserve and integrate pending work

**Current disposition:** [PR455][pr455] merged on October 16; [PR462][pr462]
remains blocked with all 46 positive obligations retained. PR533 is a separate
unaccepted correctness repair, not permission to merge #462. Keep useful
population/ownership and participation work. Reconcile shared parser changes,
review the actual combined candidate and its semantics, and run applicable checks.
Do not treat an automated-review invitation as completed independent review.

Close this transition when the two trust defects are fixed/verified, useful
pending work is integrated or remains open with a specific independent dependency,
and the checkpoint names P1. Unrelated blocked work must not create an indefinite
P0 phase. No pending capability is silently discarded or marked complete.

## 4. P1 - Deliver shared interpretation, not a new engine

The contracts below are retained requirements, not a request to restart P1. Use
the Core-1 rows and [retained S1–S5 receipts][prior-queue] for delivered scope and gaps.

**Outcome:** changing a record/summary into a season split does not silently change
who, which games, whose condition, or statistical basis the question asks for.
This is the first bounded replacement/consolidation opportunity, not a demand to
migrate all routes before shipping.

Start with `team_record`, player/team summaries and `player_split_summary` /
`team_split_summary` for named-season splits. Inspect their existing shared sample
helpers and the #450 reparse guard. Reuse or extend the existing boundary so the
request has explicit subject identity, record grain, ordered time/sample selection,
owned conditions, operation, metric/basis and grouping. Structured and natural
entry points should reach the same calculation. Retain working compatibility
adapters while migrating this group. Remove a defensive reparse only when its
invariants are implemented and independently verified, not just to shrink code.

Mandatory first positive contracts (select fixture and real-data entities where
participation/coverage is actually discriminating; names are examples, not rules):

| ID | Shared behavior and required combination |
| --- | --- |
| S1 | Team record/summary and season split: home + named opponent, comparing exactly two explicit non-adjacent seasons; intermediate seasons must not appear |
| S2 | Player summary and season split: own points threshold + named opponent, on the same explicit season set; selected player-game IDs and averages agree with independent expectations |
| S3 | Team record and player summary: own-stat and opponent-stat clauses in the same request stay owned by the correct side; combine with a home/road filter |
| S4 | Team record/player summary and season split: one qualified teammate's played/did-not-play condition + named opponent survives the operation change; no injury/status inference |
| S5 | Records and summaries: explicit date range + opponent; distinguish the last N games with a condition checked inside that window from the last N qualifying games. Keep eligibility/order and labels explicit |

P1 covers these five contracts, not every permutation. For S1-S4 also retain the
corresponding one-season control. Specify behavior of an explicitly named empty
season and missing coverage separately. Do not force date/last-N combinations
into cross-season splits before their meaning and need are established.

In the P1 PR, bind S1-S5 to existing/new focused tests and corpus IDs before
repairing them; update the corresponding Core-1 cells. Expected results come
from independent raw-row selection/aggregation, not parser output. The checker
uses another entity, threshold and wording outside the maker's tuning set.
Test lost clauses, swapped subjects, scope widening, and valid zeros separately.
Assert actual API/result labels and selected IDs, not merely route equality.

Done: these positive contracts work through existing calculations and natural
input, required checks/review pass, deployment is checked, and the relevant
obsolete special handling is removed or explicitly justified. A new class or
file extraction without those answers is not completion. Other families stay
on their working paths. Then start P2; do not finish every engine feature first.

## 5. P2 - Bounded input-layer comparison

**Decision completed in [PR478](https://github.com/Bet-Zero/nbatools/pull/478):**
[the frozen comparison](p2-language/decision.md) found both paths 12/20 correct,
3 wrong accepted and 5 valid refusals; 8 safety controls were separate. The
candidate was not adopted; a model alternative was not evaluated. Preserve those
original outcomes after repairs. The following decision contract is retained,
not a request to repeat the comparison before continuing Core-1.

Use the P1-verified subset and freeze the candidate code/data and semantic truth
before tuning. This is one decision-sized comparison, not a provider tournament.
Reuse existing tests, structured entry point, corpora and reports; no new permanent
benchmark framework or public-input mode.

Compare the incumbent with one bounded improved interpreter. The lead chooses a
feasible deterministic redesign or a constrained AI translator under existing
access/cost authority; when feasible include the other as a small comparison,
not a prerequisite. Models propose validated requests for the same engine, not
NBA answers, missing facts, arbitrary SQL or executable code.

Bind held-out paraphrases to S1-S5 and selected Core-1 cells. The checker establishes
intended semantics independently of the candidate, including alternate word order,
unfamiliar entity names, two conditions with the same number, unsupported extra
clauses and genuine ambiguity. Keep maker examples, held-out valid questions and
safety/ambiguity controls distinguishable. Do not tune on a held-out failure and
continue reporting it as unseen; keep it as regression and add fresh holdouts.

Record denominator, answered-correctly, wrong-answer, refusal and ambiguity counts;
clause/identity/sample preservation; real end-to-end latency (including repeats
for a nondeterministic candidate); and authorized operating cost. Define the
comparison's exact cases and latency/cost limits before running it. An unrun model
alternative is 'not evaluated', not a win/loss. Without authorized model access,
complete the feasible comparison, retain that limitation, and continue core work.

Selection gate: no known wrong accepted answer or lost clause in the required
subset, no required positive regression hidden as refusal, and either more correct
held-out answers or demonstrably simpler reliable interpretation at comparable
coverage, within limits. Schema conformance alone never passes. Keep the incumbent
when the replacement does not show a verified benefit; record why and the next
bounded improvement. Do not keep it by default without measuring the problem.

The result is one short decision in this queue/PR with evidence and the exact
integration step. Integrate a winning bounded replacement behind existing contracts
and normal gates. New cost/credentials or production-model adoption require the
necessary owner decision; prepare a recommendation and continue independent work.

## 6. Core-1 acceptance scope (P3 starts during P1, closes after P2 decision)

This finite **existing-snapshot checkpoint** is not the entire original core or
whole product. The following 12 rows are its fixed capability denominator. Each
row's enumerated obligations is required; examples are not exact phrase templates.
Before tuning a row, bind the obligations to explicit test/corpus IDs and independent
expectations in its PR and the evidence column. Reuse existing tests/evidence where
applicable. Do this while building the selected row, not as a new audit-only phase.

States are separate evidence claims: **I** implemented/merged; **N** independently
checked numerical correctness (qualified real data versus fixtures stated); **L**
checked with unfamiliar wording; **D** verified through the deployed application.
The links bind historical evidence to its code/data; they do not certify newer
integration automatically. Revealed language failures stay regressions, not fresh
held-outs. “Not established” identifies missing evidence, not missing code. No
completion percentage or whole-row pass is inferred from counts.

**Core-1 remains open.** K01–K08 have bounded delivery/checking evidence; K09–K11
lack full integrated acceptance here, and K12 has a confirmed deployed failure.
Closure still requires the complete obligations below on a fixed P3 candidate and
served generation. Reuse valid evidence by checking affected code/data scope;
do not rerun everything merely because a planning document changed.

| ID | Required positive behavior and bounded combinations | I — implemented/merged | N — independent numerical check | L — unfamiliar wording | D — deployed application | Exact remaining obligation / unavailable evidence |
| --- | --- | --- | --- | --- | --- | --- |
| K01 | Correct player/team identity and covered scope: aliases/accent spelling, one same-name collision, one renamed player, historical franchise, partial-career label | [PR483][pr483] merged; identity/span binding in [K01](k01-binding.md). | 14 qualified actual-data cases accepted; independent raw identity/arithmetic review in PR483. | Independent fresh identity wording checked; revealed repairs retained as regressions. | Historical bounded gate and 52 combined K01/K03 desktop/mobile answers passed [39097220860][d-k01-k03]. | Current integrated D not established; carry forward partial-career/ambiguity findings in the binding, without inventing missing career data. |
| K02 | Player summary/team record: explicit season, explicit date range + opponent, last-N window versus qualifying last-N with one threshold | [PR486][pr486]/PR490 merged; [13-case binding](k02-binding.md); PR508 corrected canonical-opponent validation. | 13 required actual cases / 13 QA accepted with independent keys/arithmetic review. | Independent command, polite-summary/list and changed-entity probes checked; original failures retained. | 66 combined K02/K04 answers / 132 readiness checks accepted on the published generation in [39167992465][d-k02-k04]. | Bounded gate accepted; full fixed-candidate P3 acceptance not established. Preserve date/opponent and window-versus-qualifying semantics; K12 reliability remains open. |
| K03 | Find/count: two AND thresholds including exact zero, strict versus inclusive bound, grouped OR, games versus distinct-player count, qualified zero result | [PR481][pr481]/PR487 merged; [12-case binding](k03-binding.md) and count-grain rendering repair. | 12 required actual cases / 12 QA accepted; independent exact keys, grain and arithmetic. | Independent changed-entity strict/inclusive and grouped-OR probes checked. | Historical 52 combined K01/K03 answers passed [39097220860][d-k01-k03]. | Current integrated D not established. Nonzero equality and distinct-player grouped-OR gaps remain in the binding/carry-forward; no general composition closure. |
| K04 | Ranking: totals versus per-game, ratio-of-totals shooting with declared attempts floor, top-N versus last-N, one event-count ranking and tie policy | [PR485][pr485]/PR490 merged; [20-case binding](k04-binding.md). | 20 required actual cases / 20 QA accepted; independent ratios, floors, ordering and ties. | 10 held-out cases plus second independent 9-probe set checked after repairs; revealed cases are regressions, not a fresh score. | 66 combined K02/K04 answers accepted in [39167992465][d-k02-k04], with source/visual review. | Bounded gate accepted; full fixed-candidate P3 acceptance and K12 performance not established. |
| K05 | Cross-subject conditions: own-player/team versus opponent stat in one request, plus home/road; another entity and threshold | [PR488][pr488]/PR492 merged; [8-case binding](k05-binding.md). | 8 required actual cases / 8 QA accepted; independent source/owner review. | 4 primary + 4 unfamiliar cases checked; changed ownership/negation reviewed. | 40 combined K05/K06 answers accepted on the published generation in [39163942659][d-k05-k06]. | Bounded gate accepted; full fixed-candidate P3 acceptance not established. Broader owned-boolean additions are not automatic prerequisites. |
| K06 | Comparisons: two players with same named sample/basis; two teams' independent samples versus explicit head-to-head meetings; opponent filter retained | [PR491][pr491]/PR492 and [PR532][pr532] merged; [original 12-case binding](k06-binding.md). | All 12 original samples/bases rechecked within PR532's 93 required actual cases; independent source identities/rows/values accepted. | Independent comparison wording/entity/date probes and PR532 suffix controls checked; original failures retained. | Original comparison gate in [39163942659][d-k05-k06]; PR532's 16 answers within the accepted [26-answer run][public-531-532]. | Full fixed-candidate P3 acceptance not established; first-request failure remains K12. Different per-player teams/shared-team opponent unions remain additional unfinished combinations, not new original-binding obligations. |
| K07 | Splits: filter before home/away split; team and player named-season splits with non-adjacent seasons; opponent + threshold or participation retained | [PR493][pr493]/PR494 merged; [12-case split binding](k07-binding.md); S4 participation implementation retained. | 12 required actual cases / 12 QA accepted; independent keys/buckets/arithmetic. Qualified four-game S4 source checks retained in [prior receipts][prior-queue]. | Six held-outs and fresh changed-entity/threshold probes checked; revealed failures retained. | 24 answers / 48 readiness checks accepted in [39176663385][d-k07] for the bound threshold/season splits. | Bounded split gate accepted. Explicit integrated D evidence for S4 participation-retaining splits on the P3 candidate is not established here; do not infer it from threshold-only cases. |
| K08 | Participation: one and two qualified teammates played/did-not-play; add one stat bound; show membership/coverage distinction and separate injury-status safety controls | [PR513][pr513] bounded pair support merged; PR515 stages Boston observations only. PR462/533 remain unaccepted. | 8 actual pair-source tests independently accepted; qualified five-game coverage only. All 46 original absence positives remain open. | Independent fresh pair/extra-clause probes checked for the bounded slice; PR533 has a confirmed coordinated medical-owner failure. | Pair played/DNP, bound, qualified-empty and safety consumers accepted in [PR516's 28-answer run][d-k08]; not all absence obligations. | Required but blocked: membership/other-game applicability, the 46 retained positives and PR533 safety repair. Boston 17 is staging; full Milwaukee identity qualification unresolved. No season-wide absence or medical-status capability claimed. |
| K09 | Sequences: team winning streak and player threshold-appearance streak; count distinct runs; best N-game stretch versus last N; excluded-game/season continuity | Prior C2 sequence implementations retained; full bound set not established. | Current integrated numerical acceptance not established. | Current bound unfamiliar-language acceptance not established. | Current integrated deployed acceptance not established. | Bind/accept the listed team/player streak, distinct-run, best-versus-last and continuity obligations using existing code/evidence; no claim that implementation is absent. |
| K10 | Playoff/history: game versus series record versus appearances; one round/series-situation filter; one franchise/title-count query with exact definition and covered span | Prior C2 history implementations retained; full bound set not established. | Current integrated numerical acceptance not established. | Current bound unfamiliar-language acceptance not established. | Current integrated deployed acceptance not established. | Bind/accept game/series/appearance distinctions, the situation filter and exact franchise/title definition/covered span. Missing qualified history must remain explicit. |
| K11 | Population/ownership: league, named team's players, rookie and broad-position game lists; named opponent stays opponent, historical roster slice and missing-roster safety | [PR455][pr455] merged; population/opponent work is no longer pending integration. | PR455: 19 required actual cases plus independent source/row controls accepted; full row not established. | Full row's bound unfamiliar-language evidence not established. | Full row's deployed acceptance not established. | Establish the full listed league/team/rookie/position/historical-roster and missing-roster binding/evidence on P3's candidate; do not infer full K11 closure from PR455. |
| K12 | Answer delivery: actual subject/sample/basis labels; count/list/split/comparison rendering; valid zero versus no-data; snapshot freshness disclosure; representative cold/warm behavior | Rendering/identity/zero-context repairs merged through PR532; PR534 adds diagnostics only. | Independent numerical checks exist for bounded consumers above; full row not established. | Unfamiliar wording checked within those consumers; full delivery set not established. | Multiple bounded desktop/mobile gates passed, including [26 answers][public-531-532]; fresh deployment first request failed [HTTP504][failed-first-request]. | Repair first-request reliability; establish representative warm/cold budgets and complete fixed-candidate labels/rendering/zero-versus-no-data/freshness evidence. A restored alias or passing monitor is insufficient. |

For each statistical row, use controlled discriminating rows AND representative
qualified real-data numeric checks. Exercise a second entity/value and unfamiliar
wording; pairwise modifier coverage plus targeted three-way cases is enough, not
an exhaustive word/number cross-product. Positive obligations may not be replaced
by refusal expectations. Safety controls have separate IDs/results and never
inflate the positive completion rate. New siblings outside these obligations stay
in the carry-forward list rather than continually expanding Core-1 by accident.

P3 acceptance uses a fixed integration candidate and served generation, the chosen
input path, and actual desktop/mobile result rendering. Exercise reused renderers
with representative outputs and changed ones directly; no owner screenshot tour.
Run applicable CI, required real-data tests, broad Raw QA/filter sweep at integration,
plus independent numerical/meaning review. Compare source keys/coverage with the
claims; 'two paths agree' or a changed output fingerprint is not correctness.

Measure common summaries/records/rankings/comparisons and heavier history/career
requests on a declared repeatable sample. Retain goals: warm common p95 <= 3 s,
cold common <= 10 s, admitted historical <= 20 s without unhandled timeout. Report
sample size, first-request versus warm, and p95 only when measurement supports it.
Do not infer these from one monitor run or raise thresholds to claim success.
If unmet, keep K12 operational acceptance open with a specific repair/dependency.

Close Core-1 only with its full bound positive set accepted and I/N/L/D evidence,
no unresolved wrong/unverified required answer, honest coverage, and required
checks/review passed. Record remaining broader scope explicitly. Snapshot acceptance
is NOT unattended-current-data acceptance; do not rename it full release readiness.

## 7. O - Independent snapshot/runtime work

**O1: compact identity metadata is published; performance acceptance is separate.**
[PR482](https://github.com/Bet-Zero/nbatools/pull/482) qualified derived names from
existing rows; the [October 18 publication][publication] includes them. Do not
repeat the former missing-metadata investigation. Preserve source dates, unchanged
statistics, lineage and last-good generation. Metadata is not new NBA coverage;
representative cold/warm improvement remains unestablished. Follow the checkpoint's
observed first-request defect before proposing another metadata publication or
hosting/database migration. Publication still needs its existing separate authority.

**O2: distinguish possible work from source blockers.** Maintain in this section a
short list of stored, derivable, missing and unverified inputs with consumer and
exact next action. Existing period/role slices and derivable game/reference facts
need not wait for missing play-by-play/lineup datasets. Start one representative
qualified slice with a real consumer, not a full-history collection campaign.

**O3: measured deployment repairs.** Profile read/index construction, frame
selection/cache, computation, serialization and render time. Fix observed costs,
including generation-aware caches and bounded reads, before proposing a new DB or
host. Preserve cost/security controls; in-process counters are not evidence of a
global provider spending cap. Product acceptance is not the availability monitor.

**Parked: fresh NBA acquisition and unattended refresh.** October 4 direction remains.
Prior hosted-runner reachability failures and unavailable laptop fallback are leads,
not a reason to retry blindly or a permanent source impossibility claim. Resume
only under the applicable owner priority/access decision. Reuse the staged refresh,
validation, immutable publication and last-good path. The eventual operational gate
requires a reachable authorized runner/source, a successful update reaching the app,
a failed update preserving last-good, live/frozen-clock rollover tests and budgets.
Existing `download-generation`, `changed-files`, conditional publication and pruning
work is retained; verify actual CLI help/runbook before executing consequential steps.

## 8. Carry-forward scope (not silently completed by Core-1)

These preserve the original program and the unfinished boundary; implementation
status must be reconciled before work, not assumed from old examples. Specific
unresolved examples/evidence remain in the [pre-cleanup queue][prior-queue],
bindings and current PRs. This section does not demote required defects or
source-blocked positives: K08/PR462/PR533 remain open above. Additional combinations
may wait; ordinary paraphrases and confirmed defects still follow AGENTS. Before
choosing any follow-up, name the exact obligation/defect/dependency, or explain why
an added capability precedes a named unfinished Core-1 obligation in the existing
PR/checkpoint. Do not create a separate observation tracker.

| Retained area | Next dependency-backed direction |
| --- | --- |
| Remaining A/B/C combinations | Retain broader grouped/cross-window OR, extra/unresolved owners and third-team calculations; bounded atomic OR (#521), self-opponent unions (#524), and original-stat pairs (#531) do not establish general grammar. Record new discretionary combinations here with root cause; selection needs a specific reason |
| Identity/availability edge cases | Shared-name cross-filters, on/off name paths, membership timing and qualified absence; distinguish whole-game from on-court presence |
| Dates/samples and opposing metrics | Remaining selector/window, repeated-month/season, opponent-metric summary and multi-subject cases: reproduce current code first; do not preserve an old wrong-answer workaround |
| Counts, rankings and sequences | [K03 binding](k03-binding.md) retains nonzero equality and distinct-player grouped OR beyond its frozen cases. [PR531](https://github.com/Bet-Zero/nbatools/pull/531) / [saved stop][saved-stop] retain reversed bare-stat and singular-three wording gaps; do not relabel ordinary paraphrases optional. Additional compound/population/eligibility/series combinations remain broader scope |
| Comparison extensions | PR532 delivered bounded shared-team filters; different per-player teams and shared-team opponent unions remain unfinished additions beyond the [original K06 binding](k06-binding.md). Do not reopen the already delivered bounded team-filter repair |
| Historical reference | Remaining playoff/championship membership, awards, calendar/reference facts with qualified sources; participation-based title counts are not an invented official ring roster |
| D1 roles/context | Needed pre-2024-25 starter/bench/period/context coverage, team bench outputs and reference joins; existing qualified slices may ship first |
| D2 specialized inputs | Separate period, play-by-play/clutch, lineup and on/off subpackages with exact grain, denominators, sources and representative validation; no fabricated data |
| Unattended freshness | Parked acquisition/refresh and tested rollover remain open until actual authorized operation is proved |
| Guided tools/profiles | Retained later surfaces on verified shared engine/data, not a substitute for ordinary natural search |

At Core-1 completion, the lead chooses the next coherent row by dependency and
user value, records why here, binds its acceptance and continues under existing
authority. No fresh whole-project plan or owner-written test battery is required.
A genuine new source/cost/product decision is escalated with the smallest action.

## 9. Evidence, validation and durable continuation

For each selected PR record a compact semantic contract, required case IDs,
independent expected meanings/values, base/candidate SHA, one generation, executed
checks/counts, actual checker evidence, deployed result and remaining issues.
Make every requested clause accounted for. Maintain fixture versus real-data,
implementation versus deployment, and safety versus feature-completion distinctions.

Reuse focused commands while editing, `make test-preflight` / `make test` for high
fan-in integration, and the existing targeted/full R2 workflow. CI's data-free or
all-suite selection does not mean required remote data ran. Required assertions,
missing data or all-skipped acceptance remain blockers under delivered P0b enforcement.
A documentation-only plan change runs `make docs-governance` / `git diff --check`,
not a new full remote NBA corpus. Do not fabricate independent or human review.

Update the Resume checkpoint when work start, review, merge, block or session stop
changes the successor's next action or evidence. Keep unchanged detail in its PR.
Add the active package's I/N/L/D evidence to the table or PR pointer;
replace stale next actions and owner/file claims. Preserve unresolved findings.
Minimum successor handoff:

```text
Updated date; controlling package/case IDs; next incomplete stage
Live main checked; task branch and exact candidate SHA; PR
Owner/lane and overlapping work; pushed/unpushed/dirty state
Pinned generation and relevant coverage
Tests: exact command/run, selected/executed/skipped, result and scope
Independent checker: actual session/review, findings fixed/open
Deployment: URL/revision/generation, checked or still pending
Blocker: exact dependency/access and what may proceed independently
NEXT: one concrete action/command and outcome; brief obligation/defect/dependency
      justification, or why an added capability precedes unfinished Core-1 work
```

A PR comment may hold detail while the checkpoint points to it. Keep needed code,
tests and conclusions in tracked repo/PR state; do not depend exclusively on a
private conversation, expiring artifact or local ignored output. Do not commit
credentials or synthetic facts as real data. No new handoff subsystem is needed.

A successor verifies the checkpoint against live state, preserves newer commits,
and performs NEXT. If that action already succeeded, record evidence and advance;
if blocked, state the actual dependency and choose the named independent task
only within current owner authorization.
Do not restart all audits, reconstruct old threads, or ask the owner to choose a
technical task. Report: Now answers; Still unfinished; Verification; Next; Needed
from you (normally nothing). Work continues only within an actual active session.

[saved-stop]: https://github.com/Bet-Zero/nbatools/blob/39aa65afdf74fc2aba70a54f9eddc1ef22c3779d/working/nba-tools-completion-program/README.md#resume-checkpoint
[prior-queue]: https://github.com/Bet-Zero/nbatools/blob/4aad08d69876601ff279d8d110a948769d4a36fc/working/nba-tools-completion-program/README.md
[public-531-532]: https://github.com/Bet-Zero/nbatools/actions/runs/39389938663
[failed-first-request]: https://github.com/Bet-Zero/nbatools/actions/runs/39392363519
[restore]: https://github.com/Bet-Zero/nbatools/pull/534#issuecomment-6286711278
[restore-final]: https://github.com/Bet-Zero/nbatools/pull/534#issuecomment-6286780001
[medical-check]: https://github.com/Bet-Zero/nbatools/pull/533#issuecomment-6262298467
[publication]: https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-39102232398
[d-k01-k03]: https://github.com/Bet-Zero/nbatools/actions/runs/39097220860
[d-k02-k04]: https://github.com/Bet-Zero/nbatools/actions/runs/39167992465
[d-k05-k06]: https://github.com/Bet-Zero/nbatools/actions/runs/39163942659
[d-k07]: https://github.com/Bet-Zero/nbatools/pull/493#issuecomment-6256586688
[d-k08]: https://github.com/Bet-Zero/nbatools/pull/516#issuecomment-6257073563
[pr455]: https://github.com/Bet-Zero/nbatools/pull/455
[pr462]: https://github.com/Bet-Zero/nbatools/pull/462
[pr481]: https://github.com/Bet-Zero/nbatools/pull/481
[pr483]: https://github.com/Bet-Zero/nbatools/pull/483
[pr485]: https://github.com/Bet-Zero/nbatools/pull/485
[pr486]: https://github.com/Bet-Zero/nbatools/pull/486
[pr488]: https://github.com/Bet-Zero/nbatools/pull/488
[pr491]: https://github.com/Bet-Zero/nbatools/pull/491
[pr493]: https://github.com/Bet-Zero/nbatools/pull/493
[pr513]: https://github.com/Bet-Zero/nbatools/pull/513
[pr532]: https://github.com/Bet-Zero/nbatools/pull/532
[pr533]: https://github.com/Bet-Zero/nbatools/pull/533
[pr534]: https://github.com/Bet-Zero/nbatools/pull/534
