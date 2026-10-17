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

Replace this checkpoint as work advances; do not append another active diary.
This is a verified 2026-10-17 snapshot, not a frozen head to reset to. The
latest PR discussion/branch may be ahead of this main-branch record; check it.

| Field | Current handoff |
| --- | --- |
| Program state | #468 merged as `cb88329c65032df33a9781b6b3e62d40eab91b3e`; post-merge full/fast CI39003446595 all passed. Official source acquisition and publication validator accepted; permanent R2 publication still awaits existing operator operation. Qualified absence consumer implementation is next, not yet merged or accepted. |
| Main / owner | Live main `cb88329c65032df33a9781b6b3e62d40eab91b3e`. Lead Codex /root owns shared consumers in `codex/qualified-absence-consumer`; independent checker /root/availability_checker. Local worktree `/workspace/work/qualified-absence`; this checkpoint is its candidate. Source PR468 complete; PR462 preserved separately. |
| Verification | Source runtime631b passed required official report run39002683645 (1selected/executed/passed0skip) and independent34identity/20played/14DNP arithmetic. PR468 finalCI39003199664 and postmerge39003446595 allapplicablepass. Consumer firstpreflight:9failed7896passed1460skipped; all9 failures addressed without changing desired outputs,230targetedpass. Bounded checker side/conjunction/missing/date/duplicate probes passed; latest positive-minute supplement review and broad rerun pending. |
| Source/storage NEXT | Review final consumer and run `tests/test_pipeline_player_game_availability_real_data.py::test_official_opening_report_qualified_absence_consumers` via bounded reviewed R2 request on pinned base `queue-d-production-0574735-20260716`. It must retain newly acquired source evidence and verify exact source-derived LAL109/GSW119 samples. Then normalCI and independent finalacceptance; do not merge on fixture totals alone. |
| Permanent-storage gate | CI artifacts are temporary staging only. Retain source URI/retrieval date/hash and bind CSV rows with `source_sha256`; stage against the pinned existing generation, validate coverage and lineage, publish only with existing write authority, verify object sizes/checksums and active pointer/runtime. Never use read-only validation credentials for writes. Request owner action only if the actual publication operation lacks available authority. |
| Independent #467 | Candidate `26f10cde368b7efe8cabd1c716166f259a72e087` on `codex/p1-three-team-scope-independent-20261016` fixes final three-team subject retention. CI [39000450859](https://github.com/Bet-Zero/nbatools/actions/runs/39000450859) passed. Independent checker: 39 scoped tests plus raw-fixture March arithmetic and unfamiliar entity/clause probes. Maker: 66 focused tests. |
| #467 NBA evidence | R2 [39000485209](https://github.com/Bet-Zero/nbatools/actions/runs/39000485209), request `48147b039e8416e17633efddb059b67f9e65c672`, reviewed parent `26f10cde368b7efe8cabd1c716166f259a72e087`: **2 selected/executed/passed, 0 skipped/failed/errors/xfails**, pinned generation above. Artifact 12088766782, ZIP SHA256 `819b7cf7eda43cb0a119cfa8506b94914b9922b47eba0b5ed8a73bb7656a68e9`. Raw QA/sweep unselected, not full-corpus acceptance. |
| #467 operational verification | Merged `cf0910b6812b192f1c10faee7d44c41c65c478ab`; post-merge CI39002110136 full/fast all passed; Vercel commit status success. Public API numerical run [39002625543](https://github.com/Bet-Zero/nbatools/actions/runs/39002625543): 1 selected/executed/passed, 0 skip. Test-only candidate355ff78c712e9c126f9a9abf2008cd16840418bb on `r2-validation/deployed-three-team-355ff78c` verifies all three names/counts/WL/PPG against raw March2024 rows and pinned readiness. Artifact12089443479 ZIP SHA256 `98edd408d3f8c90d5bacb57b1b8f311a19c229c084d77c49f57bb4a1cd14f26e`. Rendering not visually checked; no per-response generation provenance claim. |
| Preserved requirements | #462 head13df00fb84f142a0f4803ac196ebe9ff3a1355db retains all 46 positive absence obligations. Next independent implementation: shared qualified absence filter; bounded real case Lakers without LeBron on2025-10-21 = 1 game, 0–1,109PPG; Warriors without Moody = 1–0,119PPG. Require explicit game/team/player observations for every candidate predicate; missing rows remain unknown. Synthetic test seasons are not acquisition targets. S1/S2 and K01-K12 remain open. |
| Runtime / owner direction | Owner confirmed persistent Goal activation is unavailable; do not request it again or claim background continuation. Use existing GitHub Actions runners for NBA scorer reports and R2 read-only validation despite Codex Cloud proxy failure. Do not request additional R2 credentials. Continue authorized tasks within the active session and update this same checkpoint. |
| Needed from owner | Actual publication operation requested using the checked [operator handoff](opening-availability-publication.md); no response/receipt yet. Existing separately controlled write authority is unavailable in this session. Do not request new credentials. Consumer implementation and CI proceed independently. |

### First-session procedure

Inspect the repository without resetting or overwriting another agent's work:

```sh
git remote -v
git status --short --branch
git fetch origin
git log -1 --format='%H %s' origin/main
```

Read live PR metadata, changed files, discussion and check results through GitHub
or `gh`. The observed branch names above are resume leads, not proof a worker is
still running. Coordinate on the PR; preserve its author/session evidence. If its
head moved or merged, inspect that actual revision before choosing the next step.
Do not create duplicate repair PRs without explaining why the original cannot be
continued. Never force-push someone else's work to match this handoff.

On the #462 candidate, after the normal editable project installation in an agent
execution environment (not the owner's laptop):

```sh
DATA_SOURCE=local python -m pytest -q \
  tests/test_participation_coverage.py tests/test_played_season_splits.py
```

These are fixture-only checks on #462, not real NBA verification and not a
request to treat the mixed candidate as releasable. The 46 known positive
absence requirements remain open and intentionally fail its normal suite.
When extracting independent work, test the isolated candidate separately and
keep missing-source evidence and regression expectations traceable on #462.

### How to resume execution without an endless red PR

1. Check the current #462 diff/commits and the approved S1/S2 evidence. Find the
   smallest truly independent P1 delivery that does **not** rely on invented
   absences. Start its candidate from live main and carry only necessary code,
   positive tests and corpus cases. If no such slice exists, move to another
   independent package rather than refactoring the blocked P0a all night.
2. Verify that new PR with a real checker, required selected/executed/skipped
   counts on pinned R2 where applicable, broad applicable CI and actual output.
   Merge only green and correctly scoped changes; do not use the status of #462
   as a substitute for the isolated candidate's own evidence.
3. Leave #462's 46 required absence obligations open on their original candidate.
   Don't delete, mark expected failure, weaken, or disguise them as safety passes.
   Investigate source sufficiency separately. A future qualified dataset/contract
   unlocks their implementation. More unrelated P1 commits on #462 only increase
   the unmergeable backlog.
4. After a safe independent merge, publish one concise checkpoint to this same
   queue on main and update #462's PR discussion. If a Codex turn ends, its
   successor uses the latest pushed PR checkpoint and checks whether a scheduled
   thread wake-up is **actually** enabled. Do not claim invisible automation.

The aim is continuous *forward progress*, not removal of legitimate failure gates
or pretending an interactive Codex turn is an always-on service.

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
| Runtime | Prior profiling found material read/index/frame costs and several useful fixes; compact name lookup publication is still to verify | Follow O's bounded measurement/metadata path before suggesting a migration |
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

**Observed defect, not a delivered repair:** #462 maps injured/similar status
words to missing participation and healthy/available/active to playing. Its
fixture removes player rows to justify those readings. The source facts do not
support that equivalence. Inspect `docs/reference/data_contracts.md` and the
current participation contract; meaning must be checked before arithmetic.

Preserve real improvements to teammate names/pairs and valid participation
wording. Games in which a player did not play may answer did-not-play/without
questions when coverage and relevant membership are qualified. They cannot be
advertised as injured games or a cause of absence. Likewise played does not mean
healthy, and listed active/available does not prove actual minutes played.

Repair the existing candidate, not a fresh unrelated parser expansion. Status-
specific wording without a source needs honest unavailable/clarification behavior,
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

Inspect `.github/workflows/r2-real-data-validation.yml`, related harness tests,
`tests/conftest.py` and its `needs_data` skip behavior. The observed workflow sets
`continue-on-error: true` on numerical tests; targeted mode may skip other gates.
The last inspected numerical run passed, but a green workflow alone is insufficient.

Strengthen the EXISTING read-only validation path. Required tests for a feature
must be non-optional and tied to a resolved candidate SHA and one pinned generation.
Avoid a moving branch being independently checked out at different revisions by
separate jobs. If older exploratory checks need to stay informational, identify
and separate them explicitly; never reclassify a failing acceptance test merely
to keep green. Preserve the full Raw QA/filter-sweep backstop and secret-free CI.

Acceptance in a controlled test/validation context: a required assertion failure,
a typo or empty required selection, zero executed tests, all-required-skipped run,
missing required data and execution error cannot become a pass. A legitimate
unselected job in targeted mode is not the same as skipped required tests. A valid
positive selection must execute and pass. Report required selected/executed/skipped
counts and underlying job conclusions. A deliberate failure experiment is clearly
labeled, isolated from production data, and leaves no failing test in main.

Use the existing `r2-validation` environment; no credential expansion, duplicate
workflow or branch-protection change. Independent checker verifies enforcement,
not just YAML appearance. Until this lands, manually inspect required underlying
jobs/counts and block dependent merges on any real failure or unavailable evidence.

### P0c. Preserve and integrate pending work

Refresh #455 and #462. Keep the useful game-list population/owner/opponent work
and participation/composition fixes. Do not merge either solely because it is
mergeable or its PR body lists old green totals. Reconcile shared parser changes,
review the actual combined candidate and its semantics, and run applicable checks.
Do not treat an automated-review invitation as completed independent review.

Close this transition when the two trust defects are fixed/verified, useful
pending work is integrated or remains open with a specific independent dependency,
and the checkpoint names P1. Unrelated blocked work must not create an indefinite
P0 phase. No pending capability is silently discarded or marked complete.

## 4. P1 - Deliver shared interpretation, not a new engine

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

States: **I** implemented/merged; **N** independently numerically verified (fixture
and real-data scope distinguished); **L** held-out language verified; **D** actual
API/rendered/deployed path verified. 'Unassessed' means current integrated acceptance
is not established, not that all underlying code is absent. Never infer a percentage
from PR or test counts. Each row passes only when every bound required case passes.

| ID | Required positive behavior and bounded combinations | State / evidence |
| --- | --- | --- |
| K01 | Correct player/team identity and covered scope: aliases/accent spelling, one same-name collision, one renamed player, historical franchise, partial-career label | I exists in prior A1/C2; N/L/D unassessed for this checkpoint |
| K02 | Player summary/team record: explicit season, explicit date range + opponent, last-N window versus qualifying last-N with one threshold | Prior A2; S5; integrated acceptance unassessed |
| K03 | Find/count: two AND thresholds including exact zero, strict versus inclusive bound, grouped OR, games versus distinct-player count, qualified zero result | Prior B1/C1; integrated acceptance unassessed |
| K04 | Ranking: totals versus per-game, ratio-of-totals shooting with declared attempts floor, top-N versus last-N, one event-count ranking and tie policy | Prior B1/C2; integrated acceptance unassessed |
| K05 | Cross-subject conditions: own-player/team versus opponent stat in one request, plus home/road; another entity and threshold | S3; integrated acceptance unassessed |
| K06 | Comparisons: two players with same named sample/basis; two teams' independent samples versus explicit head-to-head meetings; opponent filter retained | Prior C1/C2; integrated acceptance unassessed |
| K07 | Splits: filter before home/away split; team and player named-season splits with non-adjacent seasons; opponent + threshold or participation retained | S1/S2/S4; #450 is implementation evidence only |
| K08 | Participation: one and two qualified teammates played/did-not-play; add one stat bound; show membership/coverage distinction and separate injury-status safety controls | P0a/S4; integrated acceptance unassessed |
| K09 | Sequences: team winning streak and player threshold-appearance streak; count distinct runs; best N-game stretch versus last N; excluded-game/season continuity | Prior C2; integrated acceptance unassessed |
| K10 | Playoff/history: game versus series record versus appearances; one round/series-situation filter; one franchise/title-count query with exact definition and covered span | Prior C2; integrated acceptance unassessed |
| K11 | Population/ownership: league, named team's players, rookie and broad-position game lists; named opponent stays opponent, historical roster slice and missing-roster safety | #455 pending at revision; integrated acceptance unassessed |
| K12 | Answer delivery: actual subject/sample/basis labels; count/list/split/comparison rendering; valid zero versus no-data; snapshot freshness disclosure; representative cold/warm behavior | P3/O; integrated acceptance unassessed |

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

**O1: inspect compact identity metadata first.** Verify the actual served generation
and whether `metadata/player_names.csv` exists/is used. Inspect
`generation_publication.py` / `_write_player_names` and the reader. The writer can
derive this lookup from staged existing player-game rows; a fresh NBA pull is not
intrinsically needed. Do not assume it is missing or automatically beneficial.

If missing, stage the existing immutable snapshot, derive/validate metadata, compare
identity results and measured cold/warm cost, then publish only under existing
write authority and deployment safeguards. Preserve original NBA data dates,
checksums/lineage, unchanged stats and last-good rollback. A metadata-only generation
is not new coverage. Without publication access, leave that exact gate open, deliver
the validated candidate/evidence, and continue independent work; never widen a
read-only key or ask the owner to restore their laptop as a runner.

October 15 source inspection confirmed `_write_player_names` derives
`metadata/player_names.csv` solely from staged existing player-game rows, and
`_read_published_player_names` consumes it with `first_seen` ordering or falls
back to full scanning. Actual served-generation metadata/access and production
performance remain unverified; no generation was staged/published in this session.

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
unresolved examples/evidence remain in the immutable prior queue and current PRs.

| Retained area | Next dependency-backed direction |
| --- | --- |
| Remaining A/B/C combinations | Transfer newly discovered requested combinations outside K01-K12 here with root cause; use shared request semantics, not another endless phrase stream |
| Identity/availability edge cases | Shared-name cross-filters, on/off name paths, membership timing and qualified absence; distinguish whole-game from on-court presence |
| Dates/samples and opposing metrics | Remaining selector/window, repeated-month/season, opponent-metric summary and multi-subject cases: reproduce current code first; do not preserve an old wrong-answer workaround |
| Counts, rankings and sequences | Additional compound/grouped/population/eligibility/series conditions and meaningful combinations beyond the bound checkpoint |
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
missing data or all-skipped acceptance remain blockers even before P0b enforcement.
A documentation-only plan change runs `make docs-governance` / `git diff --check`,
not a new full remote NBA corpus. Do not fabricate independent or human review.

Update the Resume checkpoint at work start, review-ready, merge, actual block and
session limit. Add the active package's I/N/L/D evidence to the table or PR pointer;
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
NEXT: one concrete action/command, expected outcome, then next package
```

A PR comment may hold detail while the checkpoint points to it. Keep needed code,
tests and conclusions in tracked repo/PR state; do not depend exclusively on a
private conversation, expiring artifact or local ignored output. Do not commit
credentials or synthetic facts as real data. No new handoff subsystem is needed.

A successor verifies the checkpoint against live state, preserves newer commits,
and performs NEXT. If that action already succeeded, record evidence and advance;
if blocked, state the actual dependency and choose the named independent task.
Do not restart all audits, reconstruct old threads, or ask the owner to choose a
technical task. Report: Now answers; Still unfinished; Verification; Next; Needed
from you (normally nothing). Work continues only within an actual active session.
