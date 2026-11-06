# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Application baseline: merged **[PR586](https://github.com/Bet-Zero/nbatools/pull/586)**,
main `9a01942c61042946d1ffe1d4e1118399230f8117`. Agent1 continues the owner's
multi-club membership/absence objective. **K12 stays parked.** This is a scoped
application checkpoint; the ordinary combined full-season NBA positive remains
unfinished because required native tenure evidence is unavailable.

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent1 `/root`, [PR587](https://github.com/Bet-Zero/nbatools/pull/587), `codex/multi-team-absence-20261106`. Runtime `a93aa4b8eaeb1d9e2c00765d9349d2bc1205d9c6`; subsequent receipt/checkpoint-only descendants preserve it. Final exact-head CI, safe landing and post-merge receipts belong in PR587. |
| General application functionality | Ordinary missed-game questions and structured `game_finder(membership_player=...)` can combine qualified club-game populations through PR586's shared classifier. Per-team/combined results preserve season/type, date, opponent, venue and supported team-stat filters. Positive intervals or explicit DNP observations expose an original club even with zero appearances. No player/team/trade exceptions. |
| Unknowns / scope | Candidate game/team rows preserve played, explicit DNP, verified nonmember and unknown separately. Unknown member games stay eligible and unknown chronology dates remain visible; verified totals are withheld. Both sides of one club matchup remain auditable. `complete` is the requested observed candidate-club population, never full historical NBA certification. Full interval/club chronology requires separate source qualification. |
| Native NBA answers actually verified | Staged Poeltl2022-23: Spurs throughFeb8 has55exactgameobservations=46played+9DNP; Raptors Feb10-Apr9 has26=26played+0DNP. Natural/structured/HTTP exactIDs/counts/labels pass. Independent original replay verifies all9DNPs,6home/3away and970PTS across endpoint structures. Looney single-club control has82exactappearances/0missed. No native dated tenure intervals were adopted;81=72+9 fullseason arithmetic remains conditional. |
| Required hosted checking | [R2 run42185414036](https://github.com/Bet-Zero/nbatools/actions/runs/42185414036), source `580cc61099a462918175fdb4881cfcb4fb1608be`, sole-parent request `25b806517c8a086d5cdc9d5c4e58e51f19b9bca3`:3selected/3executed/3passed/0skips/failures/errors/xfails. New native scoped consumers plus preserved Tatum staged population and LeBron compact absence passed. RawQA compact-home1case/7checks passed. Immutable base `availability-lebron-season-v1-20261031`, manifest `3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`. This is staged/API acceptance, not data publication/live Poeltl acceptance. |
| Review / software evidence | Separate `/root/multi_team_checker` reviewed source/runtime and independently checked originals and arithmetic.12held-out controls passed; one valid noun-style team-stat shorthand remains unfinished and safely withheld. Fictional multi-club populations verify combined/per-team IDs and totals, unknowns, boundaries and filters; they do not qualify NBA tenure. Final explicit-observation club-discovery delta has10author controls and separate review/applicability receipt. Detailed records in [the evidence package](source-evidence/multi-team-absence-20261106/). |
| Broad / exact-head distinction | Initial broad working-tree preflight:10177passed/1863unavailable-data skips/1failed new label assertion (`at least100` vs existing`100+`). Assertion repaired and focused delta passed; this initial run is not final-head proof. Final exact-head blocking CI must pass before landing; receipts are in PR587. Existing frontend development-security advisories remain informational; production security remains blocking. |
| Genuine dependency | [DQ-004](data-quality/DQ-004.json): approved native tenure HTML capture [run42183017232](https://github.com/Bet-Zero/nbatools/actions/runs/42183017232) returned403 on first article; no native body retained, other2unattempted. No unchanged cloud retry. Extracted web text/one transaction/first-last appearance cannot replace required originals. The [three-source acquisition packet](collection-requests/poeltl-membership-capture.zip) is ready for the existing acquisition laptop; return its ZIP including failures. |
| Source discrepancies / preserve | [DQ-005](data-quality/DQ-005.json) records2022-23 reported PLUS_MINUS discrepancies at0022200138/0022200749; values unchanged and margins unqualified. They do not affect selected DNP identities/counts. All20successful archive originals retained/reused. Prior484unknowns/20groups and accepted K08 evidence remain unchanged; no Agent2 cleanup worker was launched. |
| Preserved safeguards | All46positive obligations and prior qualified behavior remain required. No full historical coverage, fullseason Poeltl acceptance, Core-1 completion, current freshness or production acceptance claim. No production data writes, pointer changes, credentials, permission/spend expansion or schedules. |

**Next application action:** capture and independently qualify the3native tenure
originals through the existing acquisition-laptop packet, establish the inclusive
membership intervals and exact81-game population, then execute the ordinary
combined-season Poeltl positive plus per-team/filter controls through natural,
structured and HTTP paths. The sources may establish or change that proposed
population; do not stamp81/9accepted in advance. Reuse all20archive bodies and
PR587's unchanged engine/accepted bounded evidence. Obtain affected review and
required checks for the new qualified version; publication still needs separate
authority. The noun-style `with80+team points` positive also remains open; its
safe withholding is containment, not delivery. Do not start a bulk backfill or K12.

Stop is a verified scoped application checkpoint with a genuine source-provenance
dependency. Owner acquisition-laptop execution is the only remaining owner action;
no product decision, coding, source selection, new credentials or spending is
requested. No agent/service/schedule continues in the background after the turn.

### Foundation acceptance contract

1. Verify live main and concurrent branches; read only the relevant current docs,
   PR582 receipts and the retained product bindings. Preserve all prior work.
2. Use the existing portable snapshot/fixtures and validators. Implement or verify
   explicit local/isolated development selection, pinned input version, visible
   provisional status and safe API/export/aggregate propagation. Add production
   rejection/isolation tests; do not disable strict validators or change Vercel/R2.
3. Make failed initial validation produce durable, deduplicated exception entries
   with exact scope/evidence and dependent-field impacts. Reuse existing reports,
   not a new database/framework. Keep 484 null values unknown; do not invent data.
4. Verify app semantics with independent fixtures/known-good cases. Provisional
   source outputs demonstrate flow only. Distinguish implementation, fixture
   correctness, real-NBA qualification and deployed acceptance in the receipt.
5. Demonstrate a reviewed correction producing a new immutable snapshot with
   affected derived values recalculated, originals preserved, stale correction
   preconditions rejected, and a concurrent reader retaining its pinned old version.
6. Deliver one concrete app improvement. First inspect the documented compact
   date/absence-clause defect (`miss in2025-26`) in the preserved carry-forward
   scope; repair it if it still exists. If already fixed, select the highest-value
   unfinished Core-1/K08 obligation and state the reason without a broad re-audit.
7. Review and merge coherent, passing changes. At the first isolation/ownership
   handoff, make Agent 2 launch-ready without waiting for the app task to finish.
   Stop at a meaningful verified product checkpoint or a genuine execution limit;
   data-only exceptions do not stop unrelated authorized app work.

### Agent 2 next milestone and launch timing

Use [its launch prompt](data-quality/agent-2-prompt.md), not the old readiness-only
prompt. It may run concurrently on another branch or later. Claim exact groups;
consume immutable inputs; update only its worklist/evidence/correction candidates.
If methodology/rulings remain unavailable, record the specific next evidence and
stop those tasks rather than rereading the same sources. A parked data worker does
not park Agent 1. No owner source research or new capture is needed merely to
start product development.

### Handoffs, ownership and stop boundaries

Agent 1 owns this main checkpoint and shared app/loader contracts. Agent 2 owns
claimed data-quality entries and its own branch/handoff. Both verify current
heads before writes/merges and preserve newer work; no force-reset of another
worker. Independent review remains separate from authorship. Corrections create
new data versions; consumers adopt at a safe boundary with affected regressions,
never by mutating a running test's inputs. Shared validator/schema defects are
integration tasks, not concurrent edits or disguised data repairs.

The owner explicitly permits routine code/evidence updates and safe merges under
existing checks. Production publication, purchases, expanded credentials/access,
destruction and weaker safeguards remain separately gated. No unattended service,
worker, refresh timer, new paid model or hosting migration has been created.

## Preserved acceptance scope and earlier work

The complete pre-change queue is retained **byte-for-byte** in
[acceptance-baseline-pr582.md](acceptance-baseline-pr582.md), original Git blob
`23f1981b3d458c2c5e951da1eda663e77117f2fd`. It is an acceptance/history reference,
**not an active queue**: its old NEXT, readiness-only stops, K08 pause and October4
acquisition pause are superseded by this policy. No positive obligation, numerical
threshold, failed receipt, historical evidence or saved branch is deleted.
Read only the relevant scope section when selecting a product task.

## 1. Preserved product and starting evidence

1996-97 onward, prioritizing the 21st century; earlier history remains optional.
Retain the [original product scope and helper guidance](acceptance-baseline-pr582.md#1-preserved-product-and-starting-evidence).
Salary/trade-rule work belongs to another project, not NBA Tools.

## 2. Execution order and work ownership

Agent 1 handles app work plus bounded acquisition and intake. Agent 2 handles
exception cleanup independently. The existing P0/P1/P2/P3/O product sequence and
finite milestones survive, but complete current-season data readiness is not a
blanket prerequisite for development. K08 app work may resume; K12 cold chasing is
still parked. At most two non-overlapping makers plus an independent checker.

## 3. P0 - Secure existing work

Keep [all P0 requirements](acceptance-baseline-pr582.md#3-p0---secure-existing-work),
including participation/medical distinctions and real required numerical failures.
Prior completed P0 repairs are not restarted. Missing NBA source qualification
remains missing evidence, not a passing numerical gate.

## 4. P1 - Deliver shared interpretation, not a new engine

Retain [S1-S5 and every original condition](acceptance-baseline-pr582.md#4-p1---deliver-shared-interpretation-not-a-new-engine).
No phrase-patch treadmill or universal-engine prerequisite. Develop against stable
contracts/fixtures while linked data exceptions are investigated independently.

## 5. P2 - Bounded input-layer comparison

[PR478's decision and complete contract](acceptance-baseline-pr582.md#5-p2---bounded-input-layer-comparison)
remain intact; no new paid/model comparison or benchmark rerun is implied.

## 6. Core-1 acceptance scope (P3 starts during P1, closes after P2 decision)

[All 12 K01-K12 rows, exact combinations, I/N/L/D evidence and release thresholds](acceptance-baseline-pr582.md#6-core-1-acceptance-scope-p3-starts-during-p1-closes-after-p2-decision)
remain required. Preserve all 46 PR462 positive obligations and current later
receipts. A provisional demonstration or software-fixture pass is not completion
of N, D, Core-1, the current-season snapshot or production readiness. No denominator
shrinks and no unavailable required answer becomes a completed refusal.

## 7. O - Independent snapshot/runtime work

[Accepted O1 and remaining O2/O3](acceptance-baseline-pr582.md#7-o---independent-snapshotruntime-work)
remain. Routine bounded acquisition is authorized; unattended refresh is not.
Do not reopen completed setup or migrate hosting without a demonstrated need.

## 8. Carry-forward scope (not silently completed by Core-1)

[Every retained carry-forward row and saved-work pointer](acceptance-baseline-pr582.md#8-carry-forward-scope-not-silently-completed-by-core-1)
remains open unless actual later evidence closes it. Use these to select the next
app task; data failures move into the subordinate exception worklist. Preserve
unreviewed Tatum work at `b835874e7c31dc29c38d62fcda263af404c881fe`; do not treat that
branch as accepted implementation or overwrite it.

## 9. Evidence, validation and durable continuation

Use AGENTS' focused tests, real independent review, source/fixture distinctions,
evidence-reuse rules and exact-candidate blocking CI. Keep detailed receipts in
PRs and source evidence, not repeated across every handoff. The docs-only process
change is not new numerical validation. Existing strict 11 raw / 5 processed,
R2, 24-hour freshness, protected publication, live checks and backup remain.
Report actual workers running/stopped and concrete next work; no implied background
execution and no owner coordination of routine technical tasks.
