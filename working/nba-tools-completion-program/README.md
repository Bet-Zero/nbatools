# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Reviewed merged main `d9a96865` (PR630).** Core-1
reconciliation is closed: no confirmed remaining software or web-delivery defect
in the original acceptance scope was found that held evidence can correct.
**STOP on missing factual evidence; no further investigation or test campaign.**

**What works:** identity, explicit seasons/windows, summaries/records, find/count,
rankings, owned conditions, comparisons, splits, sequences, history/populations
and functional delivery have retained independent numerical/language/browser
proof within their bindings. PR615's [R2 43582685873](https://github.com/Bet-Zero/nbatools/actions/runs/43582685873)
passed all 126 non-K08 checks. PR617's final
[22-question desktop/mobile run 43602403345](https://github.com/Bet-Zero/nbatools/actions/runs/43602403345)
and [50-query K08 desktop/mobile run 43602584850](https://github.com/Bet-Zero/nbatools/actions/runs/43602584850)
passed. Its earlier failed team-cell expectation was already corrected; it is
not an open application defect. Older K03/K05 delivery notes are superseded by
that proof and retained PR593–605 evidence, not a new work queue.
PR618's shared interpretation repairs passed [17 focused real-data checks](https://github.com/Bet-Zero/nbatools/actions/runs/43658225359),
with the original 22 historical parser inputs unchanged and applicability resealed.
These are reused results at their stated revisions, not fresh runs on PR630.

**Core-1 is not fully accepted:** K08 remains **16 PASS /26 MISSING DATA /4 LIVE**.
Twenty-five mapped Davis-family cases need dated official Davis club membership
(or complete official game-day evidence) for every selected **2025-26 Lakers**
date under the served default. His DAL appearances and a season-end WAS roster
do not establish those dates. ID26 needs Tatum's Knicks-side membership or
nonmembership on every selected Knicks date; Boston observations cannot supply it.
ID40 also contains a literal-current variant; retain its mapping and all original
questions. No refusal, absent row, first/last appearance or season roster is a pass.
The existing membership engine cannot create these missing facts.

**Live / other boundaries:** literal-current IDs4/5/19/38 and current40,
24-hour freshness/readiness, current cross-club membership/current publication
(owner Nov11), and K12 cold timing (owner Nov14) belong to Live. The 484 unknown
USG%/TOV% cells remain labeled unavailable and do not block the release (Nov14).
No new code fix or broad test rerun was warranted. The supported snapshot is
otherwise supported by the existing release evidence; it is not full Core-1
acceptance or an all-green historical real-data suite. Existing stale-generation,
source-acquisition and readiness failures are not silently closed. Development
security remains informational red; blocking safeguards are unchanged.

**Next product decision:** recommend an explicitly limited snapshot milestone
with documented participation coverage, followed by Live. Only B can defer the
26 unmet original positives; until that scope decision, Core-1 stays blocked.
Do not invent implementation work, resume source hunts or begin Live refresh.
No publication, spending, backfill, automatic refresh or scope approval is assumed.

**Preserve completed data work:** Cleveland staging **`cleveland-full-boxscore-2024-v2`**,
ZIP SHA256 `a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298`,
remains **14 complete /21 cases**, with seven cases /318 unknown player-game cells.
Keep all originals, v1, quarantines and disputes unchanged for a future combined
release. Historical expansion is closed; no standalone Cleveland publication.
Production **0abc** (69 complete 2024-25 cases plus 93 prior 2023-24 cases), its
verified backup/restore and original failed-readiness receipt are unchanged.
DQ-005 and 484-rate source hunts stay parked. No background work continues.

## Preserved scope

- **Acceptance contract:** [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md),
  byte-exact, SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`.
  Its status cells are historical; its requirements still apply, as revised only by
  B's scope decisions recorded above.
- **Bindings per group:** [K01](k01-binding.md), [K02](k02-binding.md),
  [K03](k03-binding.md), [K04](k04-binding.md), [K05](k05-binding.md),
  [K06](k06-binding.md), [K07](k07-binding.md), [K09](k09-binding.md),
  [K10](k10-binding.md), [K11](k11-binding.md), [K12](k12-binding.md). K08 uses the
  [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622).
- **Carry-forward scope:** section 8 of the baseline lists the work Core-1 does
  not complete (wider combinations, roles/context data, play-by-play/lineups,
  unattended freshness, guided tools). Pick the next task from it after Core-1.
- **Saved unreviewed work:** Tatum branch at
  `b835874e7c31dc29c38d62fcda263af404c881fe`. Don't treat it as accepted or
  overwrite it.
- **Agent 2 launch prompt**, if it's ever restarted:
  [data-quality/agent-2-prompt.md](data-quality/agent-2-prompt.md).
