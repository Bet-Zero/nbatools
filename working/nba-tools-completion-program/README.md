# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Live baseline is merged PR590 main `d0744a435e90872e91a7e37b2b56bb59a60f3baa`.
Agent1 now implements shared K03 explicit statistical equality on
`codex/shared-stat-equality-20261106`. K12 stays parked. PR590 closes the bounded
full-season participation acceptance; production data and pointers are unchanged.

**Active meaning freeze:** explicit `exactly N`, `equal to N`, `equals N` and `= N`
mean inclusive min=max on the named stat and owner, applied before aggregation,
ranking, split or count. Player-game, NBA-game and distinct-player grains stay
separate. Negated equality and contradictory equality-plus syntax must not silently
become ordinary bounds. Existing exact zero and strict/inclusive neighbors remain.
Author cases use fixture LeBron20/team110 and retained NBA Jokic30/Edwards35;
a separate checker froze27 unfamiliar cases before implementation. Rate precision,
exact-minute-time expansion and distinct-player grouped OR are separate unfinished
work. Next: implement shared readers, qualify raw-row expectations, replay
natural/structured/HTTP consumers, obtain independent review and required gates.

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent1 `/root`, `codex/poeltl-tenure-acceptance-20261106`. Independently reviewed source/staging candidate `4f0b010e62400818a663acca6a628948065093cf`; receipt/checkpoint-only descendants preserve qualified inputs and all runtime. Exact-head CI and landing receipts belong in PR590. |
| Now answers | Ordinary `How many games did Jakob Poeltl miss in 2022-23?` returns9 in the qualified historical stage through natural, structured and HTTP consumers. Perclub/home/away/opponent/date/team-stat filters preserve membership and exact IDs. PR589's generalized noun thresholds and other existing app behavior remain unchanged. No player-specific runtime exception. |
| Numerical/source acceptance | Three authenticated original NBA.com articles jointly qualify SAS2022-10-18..Feb8 and TORFeb10..Apr9. Complete retained season records establish81eligible=72played+9explicitDNP,unknown0;SAS55=46+9,TOR26=26+0. All81eligibleIDs,72appearances,9explicit inactive proofs and83excludedclub-game rows are independently replayed. Feb9 remains unknown for date-only membership; neither club played then, so no game-population gap. No missing-row absence or medical-cause inference. |
| Evidence/version | Exact owner ZIP111037bytes/SHA`42134b026ae53e9ca3c731815f3290cc79937d14b5768c1f1eda9c9a7547361e` and unchanged capture receipt are preserved in [the evidence package](source-evidence/poeltl-full-season-20261106/), with portable `poeltl-tenure-qualified-v1-20261106` ledger, all supporting hashes, original source verdict, independent consumer review/oracle and actual hosted/rendering receipts. No successful source was downloaded again. |
| Review and required gates | Separate `/root/poeltl_source_checker` approved reviewed4f0b010e:13independent checkgroups/31queries passed, including unfamiliar filters, Looney82/0, finite dates and unknown/hash probes. [Read-only run42209600862](https://github.com/Bet-Zero/nbatools/actions/runs/42209600862), sole-parent request`0fbd7facfcdfb977060fe161a2caacf8cf957124`:5selected/5executed/5passed/0skips/failures/errors/xfails; staged RawQA4cases/27checks and preserved baseRawQA1case/7checks passed. Base`availability-lebron-season-v1-20261031`, manifest`3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`.67focused fixture controls pass. Prior PR589 software/K08 evidence is reused only for unchanged paths; no duplicate full suite or relabeled execution. Final exact-head CI/merge receipts remain in PR590. |
| Unknowns/limits preserved | Missing participation or an actual-game membership gap withholds the total; corrupted originals reject. Date-onlyFeb9 and dates outside finite intervals remain unknown. This is historical staged/API/numerical acceptance, not production publication/current freshness/full-history/Core-1 completion. All existing K08 positives remain required. |
| Independence / safeguards | DQ-004 is resolved only for this source/version. DQ-005/PR588 and all other data-quality work are preserved untouched; no Agent2 launch, assignment, coordination, monitoring or wait. Prior484unknowns/20groups, remaining K08 requirements and security/production gates remain. No active data/pointer, credentials/permissions/spending/schedules, clinical labels or K12 changes. |

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
