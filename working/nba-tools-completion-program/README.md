# NBA Tools execution queue

Owner-approved process update: **2026-11-05**. Read `AGENTS.md`, `ROADMAP.md` and
[product/data workflow](../../docs/operations/product_data_workflow.md).
This file is the **product/integration checkpoint**. The separate
[data-quality worklist](data-quality/README.md) is for asynchronous exception
cleanup, not a competing product roadmap. No worker is launched by this document.

## Resume checkpoint

Agent1 delivers generalized grouped OR distinct-player counts in
[PR592](https://github.com/Bet-Zero/nbatools/pull/592), from live main
`cbf46c7d08c5e41f4bf87a4000d6fee4d698bd3a` after merged PR590/591.
Reviewed runtime is `9fda883a5fd66f58f1cbd80150a363af5d0c71dd`;
receipt/checkpoint-only descendants retain its runtime and executable inputs.
Final exact-head CI, independent hosted review and landing receipts belong in
PR592. **K12 stays parked.** Next task is shared team/opponent-owned boolean predicates.

| Field | Current application handoff |
| --- | --- |
| Package / owner | Agent1 `/root`, `codex/distinct-player-grouped-or-20261106`. [Evidence package](source-evidence/distinct-player-or-20261106/) preserves frozen meaning/raw oracles, the original scope failure, independent review, exact raw IDs and actual hosted/rendering receipts. No owner acquisition or Agent2 action is needed for continuation. |
| New questions answered | Ordinary `How many different players had a game with over 40 points OR over 12 assists in 2023-24?`, parenthesized/reversed forms and supported nested AND/OR now execute through the shared occurrence/count engine. Structured `player_occurrence_leaders` accepts `condition_expression`, returning all identities/qualifying appearance counts with `limit=None`; natural/HTTP count finalization projects player ID once. Common team, opponent (including qualified lists), date, venue and outcome filters scope the base before either branch. |
| OR / identity / grain | Both branches evaluate rowwise against the same complete scoped player-game frame. Overlap contributes one appearance; repeated appearances and alternate names do not create extra player identities. AND holds within one game. The retained K03 control proves4player-games/3NBAfixtures/3players. Player-game counts retain row grain; distinct counts carry an ID-bearing Player/Matching Games leaderboard and explicit player labels, with no leaderboard-limit truncation. Global unique-NBA-fixture projection is not advertised as a supported query. |
| Real NBA acceptance | Pinned complete2023-24 raw selection establishes76players from276qualifying player-games across254NBAfixtures; branches125/155 with4overlap (121left-only/151right-only),8896PTS/2881AST. Every selected key, player ID and per-ID occurrence vector is reconciled independently of interpretation. Retained original2022-23 data and pinned rows agree exactly:77players/295player-games/266fixtures,169/128branches/2overlap,10051PTS/2676AST. Nested GSW predicate selects12players/176appearances/80fixtures. Natural, structured, HTTP and rendered outputs are verified; fixture facts remain separately classified. |
| Independent evidence | Separate `/root/poeltl_source_checker` approved9fda:56checkgroups/100query calls,zero failures/skips, plus4controlled RawQA cases/24checks and10unchanged default-list comparisons. All27pre-author heldouts plus2wordings assessed:26positive wordings and3owned-stat compositions safely withheld and retained unfinished. Portable source replay reproduces oracleSHA`9915885cc7afa1ba96cb47e8d38aa621c808a41ed3146b6c35ad96aeb596afd6`. Actual backend model is not exposed; no human/Claude/cross-model approval is claimed. Actual hosted-receipt review is preserved in PR592. |
| Required hosted gate | [Read-only run42231041230](https://github.com/Bet-Zero/nbatools/actions/runs/42231041230), request`6a6c7099013648913a87d81eab6a311717fa5de3` sole-parent reviewed9fda:23selected/23executed/23passed,zero skips/failures/errors/xfails. This includes3new numericals,all12K03,4qualified Poeltl/safety,3equality and1team-noun control. BaseRawQA5cases/28checks passed; existing qualified-stage4cases/27checks remain passed. Base`availability-lebron-season-v1-20261031`, manifest`3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`. No R2 writes. |
| Software / corrected finding | Stable d13preflight10271passed/1863unavailable-data skips/0failed. A real common-opponent-scope error (opponent becoming subjectteam and falsezero) was found independently, preserved and repaired through the existing list reader's opt-in scope handling; no phrase/player exception. The repair passes116focused controls with2data skips, plus independent9groups/17calls. Reviewer explicitly bounds reuse of unchanged broad/native evidence. CI42229669017 passed all blocking jobs on9fda; final receipt-head CI/landing belongs in PR592. Existing development-only audit remains advisory. |
| Preserved acceptance / unknowns | PR590's authenticated originals/unchanged receipt and finite qualified Poeltl tenure retain81eligible=72played+9explicitDNP,unknown0; SAS55=46+9,TOR26=26+0. DQ004 is resolved only for that finite historical version. Missing source/requested season, identity, predicate or applicable scope coverage withholds the new boolean count; explicit covered no-match yields zero. No absent-row DNP, injury or on-court inference. PR591 equality and all46K08positive obligations remain required. |
| Unfinished / next | Next highest general task: carry explicit team/opponent statistic ownership through shared boolean predicates and their existing player-game/distinct-count consumers, closing the confirmed P1/S3/K03 compositions currently withheld. Use the3retained frozen owned-stat oracles and qualified team/player rows. Branch-specific scopes, ranked/windowed distinct boolean counts, global unique-NBA-fixture projection, rate/exact-time precision and remaining K08/Core-1/deployed/freshness/full-history acceptance remain unfinished. No production or whole-product acceptance is claimed. |
| Safeguards / stop | Normal bounded application checkpoint completion; no owner action needed. Production data/pointers, publication/security/freshness gates, credentials/access/permissions, costs, schedules and K12 are unchanged. DQ005's nonblocking evidence state/PR588 remains untouched; no Agent2 launch/assignment/coordination/monitoring/wait. Prior484unknowns/20groups stay required. No source was reacquired and no background coding worker/future task execution is implied. |

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
