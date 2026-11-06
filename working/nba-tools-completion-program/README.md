# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Agent 1 delivers shared team/opponent-owned Boolean predicates and the current Core-1 acceptance reconciliation in [PR593](https://github.com/Bet-Zero/nbatools/pull/593), from verified live main `b6edb9e3b14268c92bfab91fec4129252bfb94b7` after PR592. Reviewed runtime is `736b3d0df63d86a06983fd2d765a1a000e063d8d`; receipt/checkpoint-only descendants preserve its runtime and executable inputs. Exact-head CI, independent hosted receipt review and landing receipts are in PR593. This advances P1/S3 and existing K03/K05 consumers; the original Core-1 denominator is unchanged. **K12 cold chasing stays parked.**

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent 1 `/root`, `codex/owned-boolean-core-acceptance-20261106`. [Durable evidence](source-evidence/owned-boolean-20261106/) preserves the independent frozen source/fixture oracles, original failures, exact selected keys/identities/occurrence vectors, 12-row/46-positive reconciliation and actual hosted/rendering receipts. |
| Newly answered | Explicit player, own-team and opposing-team predicates compose in the same shared AND/OR tree through existing player-game finder and distinct-player occurrence/count consumers. For example, `(over 37 points OR over 10 assists) with at least 125 team points` in 2022–23 returns 82 distinct players; changing the common owned condition to `when opponents scored under 110 points` returns 63. Structured routes accept `condition_expression`; natural, HTTP and rendered count/detail consumers are verified. Named-player appearances retain their actual same-game club, including traded-player rows. |
| Meaning / grain / unknowns | Existing exact game/team context joins occur before either branch, after common scope selection. Each leaf retains ownership, grouping and equality/bounds. OR unions matching appearances once; distinct counts project `player_id` once with per-player matching-game details. AND stays within one appearance. Missing requested player season, ID/stat/scope coverage, source, join, reciprocal/date consistency or ambiguous keys withholds the result; covered empty selections yield zero. No display-limit truncation, absent-row DNP, medical-status or on-court inference. |
| Qualified NBA arithmetic | Retained originals and pinned 2022–23 rows independently match: own-team case 263 player-games / 195 NBA fixtures / 82 players, 8,219 PTS and 2,466 AST; opponent case 176 / 164 / 63, 4,540 PTS and 1,734 AST. Every key/player/occurrence vector matches. Fixture with exactly 100 team points independently selects 2 appearances / 2 players; fixture facts are not NBA qualification. NBA fixture totals are diagnostic, not a new global unique-game query projection. |
| Independent review | Separate Codex checker `/root/poeltl_source_checker`, exact backend model unavailable. Final 29 controlled groups / 57 calls and 15 governor controls pass; explicitly applicable native 15 groups / 39 successful calls plus repaired identity/headline/scope/join 14 controls / 28 calls retained. All 28 pre-author language cases assessed; revealed failures remain regressions. Independent bounded 12-row/46-ID inspection is separate from numerical execution. No human/Claude/cross-model approval invented. |
| Actual required gate | [Read-only run 42245902610](https://github.com/Bet-Zero/nbatools/actions/runs/42245902610), request `65077c7c6441c40fb56196cb82e4919d4107e12b` sole parent reviewed 736b: **33 selected / 33 executed / 33 passed**, zero skips/failures/errors/xfails. Includes new owned 2, original K03 12, K05 8, Poeltl 4, equality 3, distinct OR 3 and team-noun 1. RawQA **9 cases / 52 checks**, zero suspicious; qualified Poeltl stage 4 cases / 27 checks also pass. Base `availability-lebron-season-v1-20261031`, manifest `3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`. Required and rendered artifacts authenticated and preserved. No R2 writes. |
| Software / corrected findings | Final focus 240 passed / 94 unavailable-data skips. Initial stable 3f3 broad: 10,307 passed / 1,863 unavailable-data skips / **1 failed existing grouped-base positive**; failed outer run remains failed evidence. Original own-only base+mask path restored without changing its assertion. Independent review bounds reuse of unchanged breadth with affected focused checks and actual required gates. Blocking runtime CI42245312310 passes on Python 3.11/3.12/3.13; final receipt-head CI/landing in PR593. Existing development-only audit remains informational. Full-name, count-headline and context integrity findings are repaired generally. |
| Preserved / unfinished | Required execution preserves PR591 equality, PR592 grouped OR (76 players/276 appearances in 2023–24, 77/295 in 2022–23), PR590 qualified Poeltl (81 eligible = 72 played + 9 explicit DNP, unknown 0), and original K03/K05 positives. DQ-004 is resolved only for that finite historical version; DQ-005 remains nonblocking and untouched. Elided owned verbal stat lists are contained and unfinished, not silently player-owned. Branch-specific scopes, ranked/windowed combinations, global unique-game projection, broader rate/time precision and the remaining original Core-1/K08/source/deployed/operational obligations remain open. |
| NEXT / stop / safeguards | Normal bounded application checkpoint completion; no owner action needed. **Next highest-impact product action: close original K08 ID12 paired “missing” wording using generalized interpretation and explicit qualified participation, then bind all 46 IDs and missing S4/P3 integration evidence.** This precedes adjacent Boolean expansion because it repairs an original required positive. Source exceptions do not stop independent app work. No production publication/data/pointer, gate, credentials/access/permissions, cost, schedules, separate cleanup-worker or K12 operation. No future background coding execution implied. |

### Current Core-1 acceptance view

Reconciled from live main after PR592 and the [product assessment](https://github.com/Bet-Zero/nbatools/pull/592#issuecomment-6687557050), not by rerunning old suites. The twelve rows and all original positives remain the denominator. [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md) stays byte-exact (SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`). Its status cells are historical. The original bindings/receipts below establish their stated code/data scopes; they do not certify changed consumers or a new integrated deployment. Missing current evidence is not evidence of missing implementation.

| Row | Implemented and verified scope retained | What still prevents current Core-1 acceptance |
| --- | --- | --- |
| K01 identity/coverage | [Binding](k01-binding.md), PR483: 14 qualified cases, independent language and historical desktop/mobile identity checks. | No newly confirmed missing finite-binding behavior. Current integrated identity/partial-career labels need applicable evidence on the P3 candidate; unavailable career/classification coverage stays disclosed. |
| K02 summaries/records and windows | [Binding](k02-binding.md), PR486/490/508: 13 numerical/QA cases, unfamiliar wording, historical deployed date/opponent/window checks. | Preserve original-window versus qualifying-window meaning. Fixed-candidate integration and live evidence remain incomplete; do not infer missing code from that. |
| K03 find/count and grain | [Binding](k03-binding.md): original 12 cases; PR591 adds explicit nonzero equality; PR592 adds grouped OR distinct-player projection with qualified exact identities and 23/23 required validation. | This package verifies owned-Boolean composition on finder/count consumers. Changed paths require new numerical/language/API/rendering evidence. Current deployed integration is open. Global fixture projection and wider combinations remain follow-ons, not new original prerequisites. |
| K04 ranking/basis/ties | [Binding](k04-binding.md), PR485/490: 20 numerical/QA cases, independent ratios/order/floors/ties and historical deployed checks. | No newly confirmed missing finite-binding behavior. Check applicability at fixed-candidate integration; historical latency/rendering cannot certify current operational performance. |
| K05 ownership + venue | [Binding](k05-binding.md), PR488/492: 8 owned-stat controls, primary/unfamiliar wording and historical deployed answers. | Existing bounded behavior is retained. Shared owned Boolean composition in this package advances P1/S3 with K03/K05 consumers; it does not replace the original own/opponent/home-road controls. Changed-path and integrated deployed proof remain required. |
| K06 comparisons | [Binding](k06-binding.md), PR491/492/532: all 12 original samples/bases checked within 93 required cases, independent language/rows and historical deployed answers. | Fixed-candidate integrated evidence remains open. Different per-player clubs/shared-team unions are additional unfinished combinations, not automatic original-binding prerequisites. |
| K07 splits | [Binding](k07-binding.md), PR493/494: 12 split cases, held-outs and historical threshold/season deployed checks; qualified four-game S4 participation evidence retained. | Explicit integrated P3 evidence for participation-retaining S4 splits is not established by threshold-only deployed cases. This is an evidence gap, not proof of absent split implementation. |
| K08 participation/absence | Single/pair/mixed played/DNP, bounds and named-opponent behavior already work on qualified populations. Later retained LAL/BOS/historical/reported-Rest/original-window/composed-stage evidence supersedes stale blanket labels. PR583–587/590 add isolation/intake, compact absence, dated and multi-club membership; Poeltl's finite 2022–23 population is 81 eligible = 72 played + 9 explicit DNP, zero unknown. | All [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622) remain required, not 46 assumed missing functions or failing tests. Original ID12, “Lakers record with Davis and Reaves missing,” is a confirmed currently refused positive and remains missing application behavior. Source-qualified subsets and prior mapped controls do not establish one complete 46-positive integration run. Generic dated membership is implemented; other historical tenures require evidence. Medical-status/on-court meaning remains distinct from participation and source gaps. PR586 supersedes the old Tatum 2023–24 eight-unknown limitation only for its observed 82-game cohort (74 played/8 DNP/0 unknown), not general dated tenure. Fixed 2025–26 stages do not accept literal current “this season” questions or 2026–27 freshness. Staged cohorts are not automatically production coverage. |
| K09 streaks/stretches | [Binding](k09-binding.md), PR541: finite 12 controls + 8 source tests + 12 QA, independent language and 24 historical deployed answers. | Finite row accepted on its recorded revision/generation; current integration still needs applicable proof. Filtered rolling-window combinations stay follow-on work, not new Core-1 prerequisites. |
| K10 playoff/history | [Binding](k10-binding.md), PR542: 10 source/QA cases, independent language and 20 historical deployed answers. | Finite historical acceptance retained; fixed-candidate P3 integration not established by the old receipt alone. |
| K11 population/roster ownership | [Binding](k11-binding.md), PR543: 11 source/QA cases, independent language and 22 historical deployed answers. | Finite historical acceptance retained; incomplete historical roster classifications remain source limitations. Current integrated proof remains separate. |
| K12 delivery/operations | [Binding](k12-binding.md), PR544/537: functional labels/rendering and first-request repair accepted historically; 64 deployed answers, 40 primed repeats, genuine Cold S1/R1 observations retained. | B1/M1/H1 genuine cold observations remain against unchanged budgets. K12 cold chasing stays parked. Current integrated desktop/mobile, served generation, readiness/freshness and representative performance acceptance remain open; no threshold is raised. |

**Concrete milestone blockers.** After this bounded owned-Boolean delivery, the next highest-impact product action is to close original K08 ID12 through generalized paired “missing” interpretation using explicit qualified observations, then bind all 46 IDs to actual implementation/source/integration evidence and complete pinned P3 checks, including S4. This directly advances an original required positive; adjacent broader Boolean features do not take precedence. Complete the bound K08 positives with explicit source applicability and missing behavior distinguished; obtain the missing integrated numerical/language/rendering evidence (including S4 participation splits) on one pinned P3 candidate and served generation, reusing unchanged proofs deliberately; complete remaining deployment/operational requirements, with K12 cold chasing parked. A safe refusal, fixture pass, staged fact or old deployed receipt does not close a required positive. Branch-specific Boolean scopes, ranked/windowed combinations and global unique-game projection are retained follow-ons unless an original bound case actually requires them.

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
