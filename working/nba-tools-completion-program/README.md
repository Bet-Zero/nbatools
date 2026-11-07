# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Agent1 continues verified clean live main `28d3302fb512f9c5ee841cf576dbeddf2cf74770` (merged PR600). **The PR600 Mac capture failed environment admission before any NBA request:0/196attempts,0successes,196unattempted.** The [reviewed replacement Mac package](source-evidence/period-mac-repair-20261107/README.md) repairs runtime discovery and metadata/SDK preflight while preserving the original collector and exact request byte-for-byte. No period data was collected here. Agent2 stays stopped; DQ-005/K12cold stay parked.

| Field | Current application handoff |
| --- | --- |
| Owner / revision | Agent1 `/root`, `codex/mac-capture-environment-20261107`, [PR601](https://github.com/Bet-Zero/nbatools/pull/601), continuing PR600. Independent checker `/root/mac_environment_checker`; exact frozen artifact approval and final-head CI recorded with the repair PR. |
| Diagnosed laptop failure | Owner report and retained PR600 inspection receipt: PackageNotFoundError before metadata version was available, ZIP2f4f6cc1 valid, zero requests. Independently reproduced importable namespace passing old import-only probe then failing distribution metadata. PR600 also omitted prior local/parent venv discovery. No NBA route retry is justified by this environment issue. |
| Replacement / safeguards | New Mac-fixed ZIP SHA256 `b6f4d4f156608008bd04b0573f13c1b8223b3bf75ddc2cc5dbad013e9f859e40`; original ZIP5156e94b and collector97bb73b6 retained. Compatible Python3.11–3.13 existing environments are searched and checked with installed metadata plus all196offlineSDK identities. If needed, bounded isolated PyPI installation of pinned nba_api1.11.4 occurs only inside the extracted package. No global installation/manual command/admin action. Setup failures return portable zero-attempt receipts; prior output is never reset. Original one-attempt/no-retry/30sec/2MB/1secpace/1050sec collection and output/integrity limits remain unchanged. |
| Executed checks / reuse |66focused controls, actual clean private-venv dependency installation plus196offlineSDK checks, Mac POSIX shell execution and bootstrap3.8 grammar pass with zero NBA calls. Native macOS execution is not claimed. Independent frozen review and normal exact-head CI remain merge requirements. Unchanged PR598/599 application/data/numerical/source/natural/structured/HTTP/rendered proof and all46original K08/all12bindings are reused; no new source numerical acceptance is claimed. |
| Exact open population / current data |745requiredwindows=647acceptedold+98missingnew; all196newrequests for173–188 remain missing,196team-period keys,2208standard-player keys plus actual source-listed179/186OTplayers. Retained catalog/cache reconciliation and original107game successes stay accepted. Current123-v3 manifest5fb3326f, ID18 Rest0/other1/unknown0 fullLAL9, roles2781, Advanced452 and all retained source bytes survive. Whole snapshot completeness remains **false**; DQ-006 and old484rateunknowns are separate requirements. |
| Route / remaining release | Known Actions173Q1 timeout remains zero responsebytes/195unattempted; unchanged cloud/archive route is not retried. New Mac environment preparation addresses the actual returned failure. Missing period source/numerical/current-freshness checks, DQ-006/484unknownconsumer impacts and served-generation/deployed P3 remain open. No complete publication candidate is ready; production approval remains separate. |
| NEXT / smallest owner action | Download the single replacement ZIP, extract into a **new** folder, double-click **Run Capture.command** once, and return **readiness-capture/collection.zip even after failure**. Keep old/output folders. No Python diagnosis, terminal commands or manual installation. On return Agent1 verifies original request/bytes/receipts, qualifies actual period/OTparticipation/clocks/numbers through existing staging and immutable versions, then runs affected consumers. No production data/pointer/protection/cost/credentials/permissions/automatic refresh change. |

### Current Core-1 acceptance view

Reuses PR593’s twelve-row reconciliation and the [product assessment](https://github.com/Bet-Zero/nbatools/pull/592#issuecomment-6687557050), with PR594 updating affected K07/K08 evidence, PR595 supplying the finite historical numerical delta, PR596 supplying the precisely bound22-case historical live-delivery delta, and PR598/599 advancing source-qualified current ID18 and required data-family integration. The twelve rows and all original positives remain the denominator. [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md) stays byte-exact (SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`). Its status cells are historical. The original bindings/receipts below establish their stated code/data scopes; they do not certify changed consumers or a new integrated deployment. Missing current evidence is not evidence of missing implementation.

| Row | Implemented and verified scope retained | What still prevents current Core-1 acceptance |
| --- | --- | --- |
| K01 identity/coverage | [Binding](k01-binding.md), PR483: 14 qualified cases, independent language and historical desktop/mobile identity checks. | PR595 verifies all14finite numerical cases on reviewed2f0b and pinned base; functional identity/covered-career delivery is rechecked separately. Current served-generation/deployed P3 labels remain open; unavailable career/classification coverage stays disclosed. |
| K02 summaries/records and windows | [Binding](k02-binding.md), PR486/490/508: 13 numerical/QA cases, unfamiliar wording, historical deployed date/opponent/window checks. | Preserve original-window versus qualifying-window meaning. PR595 rechecks all13finite numerical cases on the pinned candidate/base; served-generation/live P3 evidence remains incomplete. |
| K03 find/count and grain | [Binding](k03-binding.md): original 12 cases; PR591 adds explicit nonzero equality; PR592 adds grouped OR distinct-player projection with qualified exact identities and 23/23 required validation. | PR593 verifies owned-Boolean composition on finder/count consumers; PR595 carries forward its independently applicable proof. Changed paths require new numerical/language/API/rendering evidence. Current deployed integration is open. Global fixture projection and wider combinations remain follow-ons, not new original prerequisites. |
| K04 ranking/basis/ties | [Binding](k04-binding.md), PR485/490: 20 numerical/QA cases, independent ratios/order/floors/ties and historical deployed checks. | PR595 rechecks all20finite numerical cases on the pinned candidate/base. Current served-generation/deployed integration remains open; historical latency/rendering cannot certify current operational performance. |
| K05 ownership + venue | [Binding](k05-binding.md), PR488/492: 8 owned-stat controls, primary/unfamiliar wording and historical deployed answers. | Existing bounded behavior is retained. PR593 shared owned Boolean composition advances P1/S3 with K03/K05 consumers; PR595 carries forward that independently applicable proof without replacing original own/opponent/home-road controls. Changed-path and integrated deployed proof remain required. |
| K06 comparisons | [Binding](k06-binding.md), PR491/492/532: all 12 original samples/bases checked within 93 required cases, independent language/rows and historical deployed answers. | PR595 rechecks all12original numerical samples/bases on the pinned candidate/base. Served-generation/deployed integration remains open. Different per-player clubs/shared-team unions remain additional unfinished combinations, not new original-binding prerequisites. |
| K07 splits | [Binding](k07-binding.md), PR493/494: 12 split cases, held-outs and historical threshold/season deployed checks; qualified four-game S4 participation evidence retained. | PR594 adds finite pinned-stage S4 team/player participation-retaining numerical/language/structured-HTTP/rendered proof and rechecks original K07 numerical12/QA12. PR596 now supplies actual historical desktop/mobile proof for all4S4participation-retaining splits on the published generation. Complete current served-generation/P3 integration remains open; bounded historical S4 does not certify the new current snapshot. |
| K08 participation/absence | Single/pair/mixed played/DNP, bounds and named-opponent behavior already work on qualified populations. Later retained LAL/BOS/historical/reported-Rest/original-window/composed-stage evidence supersedes stale blanket labels. PR583–587/590 add isolation/intake, compact absence, dated and multi-club membership; Poeltl's finite 2022–23 population is 81 eligible = 72 played + 9 explicit DNP, zero unknown. | All [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622) remain required, not 46 assumed missing functions or failing tests. PR594 repairs original ID12, “Lakers record with Davis and Reaves missing,” through generalized whole-game paired absence, with qualified historical zero and nonempty independent N/L controls. Its default/current-season and deployed scope remains unqualified. Source-qualified subsets and the [affected-ID delta](source-evidence/paired-missing-20261107/k08-affected-delta.json) do not establish one complete46-positive integration run. PR595 closes original ID44's full82Seattle/Durant historical source/N/L gap through80positive played and2explicit same-game nonparticipants, with both with/without exact keys/results; its overlay is unpublished and deployedD remains open. No additional missing behavior is inferred merely from unexecuted historical IDs. Generic dated membership is implemented; other historical tenures require evidence. Medical-status/on-court meaning remains distinct from participation and source gaps. PR586 supersedes the old Tatum 2023–24 eight-unknown limitation only for its observed 82-game cohort (74 played/8 DNP/0 unknown), not general dated tenure. Fixed 2025–26 stages do not accept literal current “this season” questions or 2026–27 freshness. Staged cohorts are not automatically production coverage. |
| K09 streaks/stretches | [Binding](k09-binding.md), PR541: finite 12 controls + 8 source tests + 12 QA, independent language and 24 historical deployed answers. | PR595 rechecks all12bound numerical query/control cases on the pinned candidate/base, carrying forward unchanged8source controls. Current served-generation/deployed integration remains separate. Filtered rolling-window combinations stay follow-on work, not new Core-1 prerequisites. |
| K10 playoff/history | [Binding](k10-binding.md), PR542: 10 source/QA cases, independent language and 20 historical deployed answers. | PR595 rechecks all10bound historical numerical cases on the pinned candidate/base; current served-generation/deployed P3 integration remains open. |
| K11 population/roster ownership | [Binding](k11-binding.md), PR543: 11 source/QA cases, independent language and 22 historical deployed answers. | PR595 rechecks all11bound numerical cases on the pinned candidate/base; incomplete historical roster classifications remain source limitations. Current served-generation/deployed proof remains separate. |
| K12 delivery/operations | [Binding](k12-binding.md), PR544/537: functional labels/rendering and first-request repair accepted historically; 64 deployed answers, 40 primed repeats, genuine Cold S1/R1 observations retained. | PR595 rechecks all12original functional-delivery cases on the pinned candidate/base, with no cold/timing operation. B1/M1/H1 genuine cold observations remain against unchanged budgets. K12 cold chasing stays parked. Current integrated desktop/mobile, served generation, readiness/freshness and representative performance acceptance remain open; no threshold is raised. |

**Concrete milestone blockers.** Current ID18 source/N/L/HTTP/local rendering and required roles/season-family integration now pass within their precise provisional scopes. Missing new period sources, DQ-006 membership and old484rate source facts remain distinct. ID12 interpretation and finite S4 stage integration remain verified; PR595 now closes ID44's full historical source/N/L gap and executes missing pinned-candidate historical numerical/functional-delivery groups. Reuse unchanged accepted evidence within its actual scope. Core-1 is still not accepted: exact current/default-season K08 populations need qualified2026–27 game-day/membership/participation and complete requested coverage; original multi-opponent applicability cannot borrow a single-opponent subset or infer nonmembership from absent rows. All46positives/all12bindings remain required. Then complete the strict snapshot/source/readiness/freshness checks and separately approved publication plus served-generation/deployed P3 integration. No further app defect was demonstrated by this assignment. K12cold remains parked. Branch-specific Boolean scopes, ranked/windowed combinations, global unique-game projection and rate/time expansion remain follow-ons unless an original bound case depends on them.

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
