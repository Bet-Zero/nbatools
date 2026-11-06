# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Live main is `cbf46c7d08c5e41f4bf87a4000d6fee4d698bd3a`, after merged PR590/591.
Active Agent1 package: `codex/distinct-player-grouped-or-20261106`, shared grouped
OR distinct-player counts. This closes the named unfinished K03 obligation.
Meaning frozen before implementation: evaluate both branches against one complete,
appropriately scoped player-game base; union overlaps rowwise; then project player
identity exactly once. AND applies within a game, never across different games.
The retained seven-row K03 oracle has4matching player-games/3NBA fixtures/3players,
with both branch-only sides, overlap and repeated appearances. Complete2023-24
league totals remain unaccepted until the actual pinned R2 raw-row oracle executes.
Separate checker has frozen27unfamiliar cases before implementation; no new source
acquisition, Agent2 action or production publication is needed. Next: reuse the
boolean parser and occurrence/count engine, verify IDs/grain/filters/unknowns and
structured/HTTP/rendered consumers, obtain independent review and safe integration.
K12 stays parked. The table below retains the previous accepted equality/source
checkpoint while this bounded package is implemented.

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent1 `/root`, `codex/shared-stat-equality-20261106`. The sole active checkpoint is this file; [equality evidence](source-evidence/stat-equality-20261106/) contains the frozen meaning/oracle, actual failed iterations, independent verdict and hosted numerical/rendering receipts. No pending acquisition or Agent2 action is needed to continue product work. |
| Now answers | Explicit `exactly N`, `equal to N`, `equals N` and standalone `= N` preserve matching inclusive endpoints through existing count-stat finder/count, summary/split, rank and team/opponent consumers. Predicates apply before aggregation/limit, preserve owner and grain, and render as equality. Exact0/0+ and strict/inclusive neighbors remain distinct. Unread combined operators, conflicting bounds and negated statistical governors withhold answers. No phrase/player/season runtime exception. |
| Equality numerical acceptance | Pinned 2023-24 raw keys independently discriminate Jokic30:2games(22300226,22301009),23AST/11.5average; Edwards35:3games(22300050,22300451,22300471),12AST/4average. Retained qualified 2022-23 originals select Poeltl3played games at110teamPTS/38REB and2explicitDNPs at112teamPTS. Natural, structured and HTTP consumers verify exact IDs/arithmetic; raw selection is the oracle. Synthetic fixture facts stay separately classified. |
| Full-season participation accepted | Authenticated owner ZIP and unchanged receipt/all3original NBA.com bodies remain in [the PR590 evidence package](source-evidence/poeltl-full-season-20261106/). Finite SASOct18..Feb8 and TORFeb10..Apr9 tenure qualifies81eligible=72played+9explicitDNP,unknown0;SAS55=46+9,TOR26=26+0;83club-game rows excluded. All IDs and explicit inactive proofs were independently replayed. Date-onlyFeb9 stays unknown but neither club played. No missing-row absence or medical-cause inference. |
| Independent review | Separate `/root/poeltl_source_checker` approved742:69checkgroups/130query invocations passed,zero skips/failures, covering all27pre-author heldouts plus repaired failure classes, actual raw fixture/native IDs, ownership/grain, other summary metrics, before-rank selection, equality labels and missing-participation unknowns. Actual backend model is not exposed; no human/Claude/cross-model approval is claimed. Portable oracle SHA`52c21ee2d0b27160f8b6bdd8f2eead5850e6b6f532384c6887350085b18acbbd` is unchanged. |
| Required hosted acceptance | [Read-only run42215938578](https://github.com/Bet-Zero/nbatools/actions/runs/42215938578), request`49caeb315b10ab79751f0e552997422549df0134` sole-parent742:21selected/21executed/21passed,zero skips/failures/errors/xfails. Selection includes all12frozen K03 cases,3new equality cases,4qualified Poeltl/safety cases and preserved source-only/team-noun controls. BaseRawQA3cases/19checks and stagedqualifiedRawQA4cases/27checks pass. Immutable base`availability-lebron-season-v1-20261031`, manifest`3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`; no data/pointer writes. |
| Software verification / reuse | Stable broadf401 finished10220pass/1863unavailable-data skips/2fail(margin wording,stale inventory), preserved literally. Both repaired;199affected controls pass on unchangedc7positive paths and122final742delta/legacy controls pass. Independent review explicitly bounds reuse of unaffected broad evidence; no false final-head full-suite claim. Required exact-head blocking CI remains a landing gate recorded in PR591. PR590postmerge full Python3.11/3.12/3.13 and other blocking jobs passed; development-only audit remains informational. |
| Unfinished / next | Next is generalized grouped OR for distinct-player counts: evaluate every branch on the same complete base, deduplicate by declared player grain, and prove both branch-only populations plus overlap using independent fixtures/qualified rows through natural, structured and HTTP consumers. Rate/exact-time precision expansion, remaining K08/Core-1/deployed/freshness acceptance and full historical coverage remain unfinished; safe containment is not positive completion. |
| Safeguards / independence | All46K08positive obligations, unknowns, source/production/security/freshness gates and prior484unknowns/20groups remain required. DQ-004 is resolved only for the qualified finite historical version. DQ-005/PR588 remains untouched: no Agent2 launch, assignment, coordination, monitoring or wait. No production publication, active data/pointer, credentials/access/permissions, spending, schedule or K12 change. No background worker/future execution is implied by this handoff. |

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
