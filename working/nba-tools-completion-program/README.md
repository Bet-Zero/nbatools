# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Baseline checked: merged **[PR #582](https://github.com/Bet-Zero/nbatools/pull/582)**,
main `fca90ab50ddb446d1247a80c8bfe4efda269e8e4`. Its final review/CI receipts remain
in that PR. This owner direction supersedes the earlier readiness-only stop and
blanket K08 pause. **Resume app development; keep K12 cold-start chasing parked.**
Full data validation and production publication remain separate and unfinished.

| Field | Current handoff |
| --- | --- |
| Agent 1 / product | Next implement the smallest safe development-data path and exception intake using existing loaders, validators, fixtures and cache. Explicitly provisional development may proceed while data QA is incomplete. Then deliver one named unfinished app behavior from the retained Core-1/K08/carry-forward obligations; do not make statistical cleanup the primary workstream again. |
| Agent 2 / data quality | Separate on-demand worker; not currently launched by this plan. Own claimed data-quality entries, source research and versioned corrections. Start when there is an actionable group and isolated snapshot/ownership. Existing external-evidence blocks do not require constant retries. |
| Data baseline | PR582's portable normalized snapshot: **647/647** historical windows; **953/1,365** original rates qualified, **412** original unknowns plus **72** newly withheld = **484** unknown values in **20** groups. All 16 structural checks passed; not full numerical, current-freshness, R2 or production acceptance. |
| Resolved / do not reopen | 0142 Q3/H2 fully qualified in staging, including scorer-supported correction. 0138's 104 REB/USG values and 0009's 38 AST values restored. 0091 flagrant attempt ordinals documented. The original PDFs are retained; independent upstream generation is **unproven**, while field-specific scorer authority and independent numerical checks support the accepted changes. |
| Exact inputs | [Official-gamebook evidence](source-evidence/rollover-2026-27/official-gamebooks-20261105/README.md); [exact remaining keys](source-evidence/rollover-2026-27/official-gamebooks-20261105/remaining-dependencies.json). Normalized ZIP SHA256 `b43546c6e911b98b303a81bc23072d5ea08c2cd71a6175f48959c25886f8d8b2`; original capture `8ff6e2052f89cf6e0070aee22c5fcee4c83edc7a285a6d7f4c6209135e8b7190`; verification `86a49bde57b2b7263736de1bab019375b323180ef0cab7691a44336332b9fc9e`. Reuse all 1,537 prior successful direct requests. |
| Remaining data tasks | Exceptional FT trip/use/exposure methodology for 0091/0118/0121; 0118 incomplete-award/violation ruling; 0009 Eason Q1 2:15 FG / 2:06 FT association. These are seeded in data-quality, with exact keys linked rather than copied. Do not request 484 downloads or repeat unchanged PDF/PBP investigations. |
| Snapshot / freshness | Historical validation population: 107 due games at `2026-11-05T06:59:31.715470Z`, not current production freshness. Pin development/tests; refresh authenticated schedule and exact 24-hour due IDs for final data acceptance. Source/cache invalidation is explicit. |
| Production preserve | Last recorded active generation `availability-lebron-season-v1-20261031`, manifest `3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`. Existing LeBron live checks and backup/restore are retained. Production's missing-new-season incident is still open; no current runtime claim or pointer change is made by this plan. Do not repeat old recovery or publish provisional data. |
| Architecture | PR582 exports ordinary portable CSVs, separate originals and keyed versioned correction/provenance records. No historical game-specific app runtime branch. Existing preparation-package coupling is documented technical debt, not an automatic rewrite requirement. |
| Implementation status | Policy/backlog/launch instructions are planning artifacts. Development-only opt-in/status propagation and automatic exception intake must be verified or implemented by Agent 1; this edit does not claim those runtime controls already exist. |

### Agent 1 next milestone

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
