# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Agent 1 has verified [PR594](https://github.com/Bet-Zero/nbatools/pull/594): shared paired whole-game “missing” interpretation and finite participation-retaining S4 integration, starting from live main after PR593 (`477c7f13b81290ad1e291118d170e7300b630e0b`). No production data, pointer, publication, access or cost changes; K12 cold chasing remains parked. [Detailed source, review and numerical receipts](source-evidence/paired-missing-20261107/README.md) retain exact candidate/data bindings and the failed attempts as well as the accepted results.

| Field | Current application handoff |
| --- | --- |
| New functionality | Paired whole-game “missing” uses the existing absence contract, preserving both identities, team, sample and supported filters. Shared stat-bound/tail handling preserves actors and refuses checked unread medical/on-court/role clauses. Explicit played/DNP/nonmember/unknown rules remain unchanged. Structured team/player splits now accept typed participation filters and display exact nonadjacent seasons. |
| Qualified NBA results | BOS2025 Tatum/Brown: **8 games, 7–1, 898 points**. LAL2023 Davis/Reaves: **qualified zero** from complete82-game coverage; legitimate record no-match and separate numeric count0, not unavailable data. Reaves game22300684 with LeBron/Davis explicit DNP vsBOS: **32PTS/2REB/3AST**. Unfamiliar Miami controls are synthetic, separately labeled. |
| Finite Core-1 evidence | Same authenticated composed root preserves8 cohorts/21 prior answers and adds paired checks plus all4 S4 team/player with/without branches vsLAL across2023–24/2025–26. Across the retained K07 run and corrected composed run, K07numerical12 plus composed1 passed without required skips/errors/xfails; staged RawQA8/50 and retained K07RawQA12/308 passed. Actual desktop/mobile browser checks cover paired outputs and S4 team labels/results. Independent source/meaning and hosted-artifact reviews approved; failed attempts remain literal in the receipts. |
| Acceptance limits | ID12's I and finite historical N/L advance; current/default-season and deployed D do not. All12 Core rows/46 original K08 IDs remain required. S4 stage proof does not close served-generation P3/deployed acceptance. Other exact source/wording/integrated scopes remain unverified; source-reported Rest is separate from generic DNP or medical cause. Historical baseline and prior accepted proofs retain their stated scopes. |
| Next application action | Close original ID44's earlier-franchise/Durant participation source/N gap using original game-day and membership/franchise evidence, then verify the exact shared query within existing46-positive integration. Never derive DNP by subtracting appearance rows. If evidence is insufficient, record the precise intake dependency and advance another required positive. No owner action is needed for routine work. |

### Current Core-1 acceptance view

Reuses PR593’s twelve-row reconciliation and the [product assessment](https://github.com/Bet-Zero/nbatools/pull/592#issuecomment-6687557050), with PR594 updating only affected K07/K08 evidence. The twelve rows and all original positives remain the denominator. [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md) stays byte-exact (SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`). Its status cells are historical. The original bindings/receipts below establish their stated code/data scopes; they do not certify changed consumers or a new integrated deployment. Missing current evidence is not evidence of missing implementation.

| Row | Implemented and verified scope retained | What still prevents current Core-1 acceptance |
| --- | --- | --- |
| K01 identity/coverage | [Binding](k01-binding.md), PR483: 14 qualified cases, independent language and historical desktop/mobile identity checks. | No newly confirmed missing finite-binding behavior. Current integrated identity/partial-career labels need applicable evidence on the P3 candidate; unavailable career/classification coverage stays disclosed. |
| K02 summaries/records and windows | [Binding](k02-binding.md), PR486/490/508: 13 numerical/QA cases, unfamiliar wording, historical deployed date/opponent/window checks. | Preserve original-window versus qualifying-window meaning. Fixed-candidate integration and live evidence remain incomplete; do not infer missing code from that. |
| K03 find/count and grain | [Binding](k03-binding.md): original 12 cases; PR591 adds explicit nonzero equality; PR592 adds grouped OR distinct-player projection with qualified exact identities and 23/23 required validation. | This package verifies owned-Boolean composition on finder/count consumers. Changed paths require new numerical/language/API/rendering evidence. Current deployed integration is open. Global fixture projection and wider combinations remain follow-ons, not new original prerequisites. |
| K04 ranking/basis/ties | [Binding](k04-binding.md), PR485/490: 20 numerical/QA cases, independent ratios/order/floors/ties and historical deployed checks. | No newly confirmed missing finite-binding behavior. Check applicability at fixed-candidate integration; historical latency/rendering cannot certify current operational performance. |
| K05 ownership + venue | [Binding](k05-binding.md), PR488/492: 8 owned-stat controls, primary/unfamiliar wording and historical deployed answers. | Existing bounded behavior is retained. Shared owned Boolean composition in this package advances P1/S3 with K03/K05 consumers; it does not replace the original own/opponent/home-road controls. Changed-path and integrated deployed proof remain required. |
| K06 comparisons | [Binding](k06-binding.md), PR491/492/532: all 12 original samples/bases checked within 93 required cases, independent language/rows and historical deployed answers. | Fixed-candidate integrated evidence remains open. Different per-player clubs/shared-team unions are additional unfinished combinations, not automatic original-binding prerequisites. |
| K07 splits | [Binding](k07-binding.md), PR493/494: 12 split cases, held-outs and historical threshold/season deployed checks; qualified four-game S4 participation evidence retained. | PR594 adds finite pinned-stage S4 team/player participation-retaining numerical/language/structured-HTTP/rendered proof and rechecks original K07 numerical12/QA12. Complete P3 integration on the served generation and deployed S4 proof remain open; historical threshold-only deployed cases do not close that gap. |
| K08 participation/absence | Single/pair/mixed played/DNP, bounds and named-opponent behavior already work on qualified populations. Later retained LAL/BOS/historical/reported-Rest/original-window/composed-stage evidence supersedes stale blanket labels. PR583–587/590 add isolation/intake, compact absence, dated and multi-club membership; Poeltl's finite 2022–23 population is 81 eligible = 72 played + 9 explicit DNP, zero unknown. | All [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622) remain required, not 46 assumed missing functions or failing tests. PR594 repairs original ID12, “Lakers record with Davis and Reaves missing,” through generalized whole-game paired absence, with qualified historical zero and nonempty independent N/L controls. Its default/current-season and deployed scope remains unqualified. Source-qualified subsets and the [affected-ID delta](source-evidence/paired-missing-20261107/k08-affected-delta.json) do not establish one complete46-positive integration run. Original ID44 earlier-franchise/Durant exact participation source/N proof is still absent from retained acceptance; do not use appearance-row subtraction. No additional missing behavior is inferred merely from unexecuted historical IDs. Generic dated membership is implemented; other historical tenures require evidence. Medical-status/on-court meaning remains distinct from participation and source gaps. PR586 supersedes the old Tatum 2023–24 eight-unknown limitation only for its observed 82-game cohort (74 played/8 DNP/0 unknown), not general dated tenure. Fixed 2025–26 stages do not accept literal current “this season” questions or 2026–27 freshness. Staged cohorts are not automatically production coverage. |
| K09 streaks/stretches | [Binding](k09-binding.md), PR541: finite 12 controls + 8 source tests + 12 QA, independent language and 24 historical deployed answers. | Finite row accepted on its recorded revision/generation; current integration still needs applicable proof. Filtered rolling-window combinations stay follow-on work, not new Core-1 prerequisites. |
| K10 playoff/history | [Binding](k10-binding.md), PR542: 10 source/QA cases, independent language and 20 historical deployed answers. | Finite historical acceptance retained; fixed-candidate P3 integration not established by the old receipt alone. |
| K11 population/roster ownership | [Binding](k11-binding.md), PR543: 11 source/QA cases, independent language and 22 historical deployed answers. | Finite historical acceptance retained; incomplete historical roster classifications remain source limitations. Current integrated proof remains separate. |
| K12 delivery/operations | [Binding](k12-binding.md), PR544/537: functional labels/rendering and first-request repair accepted historically; 64 deployed answers, 40 primed repeats, genuine Cold S1/R1 observations retained. | B1/M1/H1 genuine cold observations remain against unchanged budgets. K12 cold chasing stays parked. Current integrated desktop/mobile, served generation, readiness/freshness and representative performance acceptance remain open; no threshold is raised. |

**Concrete milestone blockers.** ID12 interpretation is repaired and finite S4 stage integration is now verified. Core-1 still needs applicable exact-scope qualified source and integrated numerical/language/rendering proof for the complete original46 and all12 row bindings, followed by served-generation/deployed and operational acceptance. Current relative-season questions cannot borrow fixed historical facts. The next bounded source/N dependency is original ID44's earlier-franchise/Durant participation population; qualify original game-day/membership evidence and its shared query, or record the exact remaining requirement without inventing a total. Reuse unchanged accepted evidence deliberately and execute only invalidated/missing required checks. Medical/status and on-court facts remain distinct; other historical tenures require their own evidence. K12 cold chasing remains parked. Branch-specific Boolean scopes, ranked/windowed combinations, global unique-game projection and rate/time expansion are follow-ons unless an original bound case depends on them; none becomes a new Core-1 prerequisite here.

**Current production readiness is separate.** The last inspected monitor is [42233057719](https://github.com/Bet-Zero/nbatools/actions/runs/42233057719), checked 2026-11-06 14:20:54 UTC: readiness 503, sole reported blocker `new_season_not_loaded`; it stopped before feature probes. It does not establish that historical queries fail. No unchanged production probe is repeated here. Retained staging has 647/647 historical windows at the 107-game cutoff (`2026-11-05T06:59:31.715470Z`), not current 24-hour coverage. Preserve 484 rate unknowns in 20 groups and their [exact external source dependencies](source-evidence/rollover-2026-27/official-gamebooks-20261105/remaining-dependencies.json), strict 11 raw/5 processed contracts, full required numerical/R2 gates, refreshed authenticated schedule/due-game/current-24-hour checks, separate publication approval, last-good protection and deployed acceptance. Historical snapshot qualification cannot supply these current-source/operational facts.


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
