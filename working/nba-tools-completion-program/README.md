# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Application baseline is merged [PR587](https://github.com/Bet-Zero/nbatools/pull/587),
`4bd2f799ddeb06544ef2223e56449ec609318dec`. Agent1 now delivers the shared team-stat
noun-threshold capability in [PR589](https://github.com/Bet-Zero/nbatools/pull/589).
The pending full-season Poeltl acceptance is independent of application progress;
DQ-004's owner acquisition packet remains separate. **K12 stays parked.**

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent1 `/root`, PR589 remote branch `codex/team-stat-shorthand-20261106`; final integration worktree branch `codex/team-stat-shorthand-final-20261106`. Independently approved runtime `3105fee4dabfe8826d10151cbe932699800b2af9`; receipt/test/checkpoint descendants preserve its recorded source hashes. Final-head and landing receipts belong in PR589. |
| Now implemented | Explicit noun thresholds such as `with 80+ team points`, strict/inclusive ceilings, supported team box-score counts and repeated bounds retain team ownership across existing player finders/summaries/splits and team consumers. Qualified missed-game counts use the same spans/bounds. Separate own-player and opponent predicates survive, including a named opponent within an explicit opponent set. Bare zero is exact zero; explicit zero-plus is a floor. No player/phrase/season exceptions. |
| Verified NBA scope | Retained PR587 originals: Poeltl Spurs throughFeb8 has55exactobservations/9DNP; five team-stat filtered natural/structured/HTTP consumers independently check exact IDs/counts. Looney/Warriors2022-23 below110teamPTS:14games,113LooneyREB,GSW3W/11L; inclusive110:17games/143REB. Existing Raptors26played/0DNP and Looney82played/0DNP controls remain. This is scoped staging/API plus qualified historical rows, not full-season Poeltl or fresh-data acceptance. |
| Review / software | Separate `/root/team_threshold_checker` approved runtime3105fee4:19independent controls passed with zero skips/failures. Two discovered ownership findings were repaired; an additional independent ranked-opponent positive checks an obsolete refusal. Broad3e38cbe2 actually had10201passes/1863unavailable-data skips/2failures: stale generated inventory and obsolete refusal. Inventory regenerated; positive support independently verified; affected60test run and exact-owner2test rerun pass. Broad evidence is reused only for unaffected paths; it is not relabeled an exact-final-head pass. [Durable evidence](source-evidence/team-stat-shorthand-20261106/) retains original failures, raw oracles and reviewed source hashes. |
| Hosted checking / acceptance | Read-only [run42202957484](https://github.com/Bet-Zero/nbatools/actions/runs/42202957484), reviewed3105fee4, sole-parent request `be1fde1b054c139c248092fad1d935924a079e5a`, pinned base `availability-lebron-season-v1-20261031` / manifest `3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`. Actual numerical4selected/4executed/4passed, zero skips/failures/errors/xfails; R2RawQA4cases/33checks passed with zero suspicious flags. [Structured summaries](source-evidence/team-stat-shorthand-20261106/) preserve the original execution identity. Final exact-head blocking CI and landing receipts belong in PR589, not a duplicate checkpoint-only merge. |
| Still unfinished / preserved | DQ-004 original complete-tenure bodies remain pending; proposed81=72+9full-season Poeltl arithmetic is unaccepted. Do not retry the unchanged403cloud route or wait for the separate acquisition packet. DQ-005 reported margins remain unqualified/unused. Prior484unknowns/20groups, all46positive obligations, wider comparison/condition composition, current freshness, integrated Core-1 and production acceptance remain open. |
| Safeguards / workers | No Agent2 launch, coordination, monitoring or wait. No new source acquisition, production data publication/pointer change, access/spending/schedule changes or K12 work. Existing data qualifiers, unknown handling, clinical/participation distinction, required positives, security and publication gates remain intact. |

**Next general-purpose application task:** reproduce and implement explicit nonzero
stat equality (for example `exactly 20 points`) through shared finder/count and
summary predicates, as retained in the [K03 binding](k03-binding.md). Freeze meaning
and independent raw-row expectations first; preserve equality versus floor/ceiling,
condition ownership and grain. This is a named unfinished product obligation that
can proceed with qualified retained data/independent fixtures while DQ-004 remains
pending. No owner intervention is needed for that application task. Unsupported
composition remains unfinished, not completed by a guard.

This is a substantive independently verified application checkpoint; safe integration
requires final exact-head blocking CI. Normal landing/post-merge receipts are
recorded in PR589. No
background service or future worker execution is implied by a saved checkpoint.

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
