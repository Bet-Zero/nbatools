# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Application baseline: live main `d730cb133a6f59aadeaee0318cb468fd818cdf63`, after
merged **PR583, PR584 and PR585**. PR585's earlier pending-landing handoff is
superseded. **Agent1 continues application development; K12 cold chasing stays
parked.** Data cleanup is outside this application assignment.

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent1 `/root`, [PR586](https://github.com/Bet-Zero/nbatools/pull/586), `codex/historical-membership-20261106`. Frozen implementation `2a310bdf5c776e905508c8afd1d8decbd1f65e08`; final receipt/checkpoint-only descendant and exact-head CI/landing receipts live in that PR. |
| Product improvement | Shared finite dated membership and exact-game participation distinguish played, explicit DNP, verified nonmember and unknown. Verified nonmembers are excluded from missed samples; membership alone never supplies DNP. Existing natural/structured team/player consumers preserve their scoped filters. Structured `player_membership` and its dedicated result view expose club/date, participation and evidence basis. |
| Generality / limits | No player/game-specific runtime exception. Optional qualified inclusive intervals work across identities/seasons; negative-only facts cannot identify a club, gaps remain unknown and contradictions reject. Native same-game observations support independent Toronto, Detroit and Washington examples. The interval behavior is fixture-verified; no historical tenure population, new natural membership grammar, traded-player multi-team missed total or full historical completeness is claimed. |
| Reused candidate | Saved `b835874e7c31dc29c38d62fcda263af404c881fe` remains preserved. All16original source bodies were reused byte-for-byte; no successful acquisition repeated. Qualification compared278listed cells and173canonical positive appearances before composing with accepted407-path staging; prior597cells/17imports remain preserved. New composed overlay has431paths. |
| NBA acceptance | Read-only [R2 run42177289405](https://github.com/Bet-Zero/nbatools/actions/runs/42177289405) binds reviewed source `fb01080d5e411b0079c98c9bd8dc7847183fe5fd` to sole-parent request `5db1448783efc40f7801956e67c5afc282a8f2f7`, immutable generation `availability-lebron-season-v1-20261031`, manifest `3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`. Required2selected/2executed/2passed/0skips or failures; LeBron RawQA1case/7checks passed. Tatum's observed82games:74played/8DNP/0unknown,5homeDNP, Boston7–1/1030PTS/128.75PPG. Six independent other-player/team HTTP checks passed. Staging/API acceptance is separate from production publication. |
| Independent review | Separate `/root/membership_checker` reviewed source/meaning and independently authored34controls plus7input probes; independently replayed16originals/278facts and source-score arithmetic. No Claude/cross-model identity is invented. Detailed source and final delta/output judgments are retained in [the evidence package](source-evidence/historical-membership-20261106/). |
| Verification / repaired integration | Initial broad preflight:10159passed/1863unavailable-data skips/10failures. Missing route metadata, old report error/identity compatibility and a main-baseline historical-clock test were repaired; focused211passed/17unavailable-data skips. Frontend locked-dependency build/lint and24focused tests passed; rebuilt loopback browser checks distinguish DNP from unknown with explicit fixture labeling. Final exact-head CI supplies the full secret-free regression set; only executed checks are acceptance. Original failures and all repairs remain in the receipt. |
| Data exceptions / production | No unresolved new Tatum source discrepancy was found. Existing484unknown current-season values/20groups and their durable backlog remain unchanged. The historical107-game fixture's Nov5cutoff is pinned only in its test; live/main reproduction found14newer due IDs, so no current freshness is claimed. Production staging/default clock, validators, data, active pointers, credentials and publication gates are unchanged. |
| Scope preserved | All previously accepted K08 behavior and all46positive obligations remain retained in the immutable PR582 baseline below. This package is a bounded shared membership/absence improvement, not closure of Core-1, every historical absence requirement, final numerical readiness or deployment/data acceptance. |

**Next application task:** qualify one bounded traded-player season using dated
membership evidence and extend ordinary missed-game questions across that player's
multiple NBA clubs. This closes the existing multi-team missed-season boundary
without treating pre-joining games as absences. Reuse the shared classifier and
retained source families, acquire only needed routine inputs, and register actual
source discrepancies through the existing exception intake while continuing app
work. Do not start a bulk historical backfill or restart K12.

Stop at the verified PR586 product checkpoint after safe landing and post-merge
checking. No owner action, production publication, new credentials, spending or
schedule is requested. Detailed final-head CI, evidence applicability and landing
receipts belong in PR586; no repeated full-suite or source acquisition is needed
without a specific new dependency or failure.

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
