# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Baseline main `fc595139` (PR629).**
[PR630](https://github.com/Bet-Zero/nbatools/pull/630), branch
`codex/cleveland-two-game-closeout`, closes the authorized two-game follow-up.
Source/data revision `22f4a16f`; only the checkpoint follows. Qualified staging
version **`cleveland-full-boxscore-2024-v2`**, ZIP SHA256
`a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298`.
The accepted PR629 v1 ZIP `6be56cee…` and every original remain unchanged.

**Now answers in staging:** Cleveland **10 → 14 complete /21 candidate cases**;
expanded cohort still 21. New: Tristan Thompson, Luke Travers, Craig Porter Jr.
and Jaylon Tyson. Both with/without answers cover all 82 games; no league-wide
completion or Core-1 acceptance upgrade. **Seven Cleveland cases /318 player-game
cells remain unknown**; missing rows never establish DNP or nonmembership.

**Bounded work closed:** two official one-page Final Box PDFs, 52,597 bytes,
qualified through the existing cached-report importer. Merrill is 20:00, but
Robinson is 28:59: blindly carrying 28:60 to 29:00 would be wrong. Both malformed
JSON originals stay quarantined. Accepted 52 report rows cover CLE on both dates
and MIA on 0022400893; BKN on 0022400199 stays unqualified for the existing
Cui identity conflict. No alias, clock normalization or new parser/infrastructure.
All 3,119 parent cells/90 imports and the seven prior disputed observations survive.
Source originals, independent arithmetic and the reusable staging overlay are in
[source-evidence/cleveland-two-game-2024](source-evidence/cleveland-two-game-2024/).
Exact review and focused execution/CI evidence are in PR630; reuse PR629 proof.

**Historical participation expansion is stopped.** Preserve v2 for an appropriate
later combined release. Do not prepare a standalone Cleveland production package,
collect more seasons, refresh automatically, spend money or reopen player/PDF
research. No production activation occurred; any future activation needs exact
protected approval. Existing production 0abc, 69 complete 2024-25 cases and 93 prior 2023-24 cases,
its independent verification/backup and failed-readiness receipt remain intact.

**Core-1 reassessment / next:** return to the original question-to-web-answer
flows on held qualified data. Prioritize the shared Davis/default-season and
cross-team applicability family, rather than more game collection or another
audit. Most of the 26 MISSING DATA labels share the Davis 2025-26 Lakers membership gap;
Tatum/Knicks dates are the other explicit dependency. The membership engine
exists; missing dated source proof is not a parser defect or permission to infer
tenure. Keep that shared blocker explicit while closing other original consumer
and delivery gaps. Do not change original questions or count refusals as passes.

Core-1 K08 limited status remains **16 PASS /26 MISSING DATA /4 LIVE**. Current
2026-27 freshness/readiness stays separate. K12 cold, DQ-005 and 484-rate hunts stay
parked; preserve their requirements. The existing development-security advisory
remains informational red; all blocking safeguards remain required. No owner
publication approval is requested for this small staging gain.

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
