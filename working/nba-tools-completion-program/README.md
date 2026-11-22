# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Main `b62ba303` (PR628).** Current bounded work is
[PR629](https://github.com/Bet-Zero/nbatools/pull/629), Cleveland 2024-25 full-game
participation. Qualified **staging only**, version `cleveland-full-boxscore-2024-v1`;
no production activation, wider backfill, costs or automatic refresh.

**Now answers in staging:** Cleveland **5 → 10 complete cases** on the frozen
21-player cohort. Expanded cohort: also 21, zero new Cleveland candidates, 10
complete. Both with/without answers account for all 82 games. New cases: Garland,
Wade, Okoro, Merrill and Bates. Opponent gain is separate: Milwaukee/AJ Green,
so the league cohort goes 69 → 75 /707. All previously complete cases survive.
**The majority hypothesis failed: 10/21.** No league-wide completion is claimed.

**Evidence:** all 82 TraditionalV3/SummaryV3 pairs retained at pinned archive
`2e44b7c0`: 164 body reads /3,066,238 bytes, no retries. Existing PR619 qualifier
accepts 80 whole games /2,772 listed rows, both teams. Entire games 0022400199 and
0022400893 are quarantined for literal 19:60 /28:60 clocks; no repair, alternate
source hunt or partial-game promotion. Originals, provenance, immutable baseline,
qualification subset, independent source arithmetic and overlay are under
[source-evidence/cleveland-full-boxscore-2024](source-evidence/cleveland-full-boxscore-2024/).
Exact review, targeted numerical execution and required CI evidence stay in PR629.
Do not repeat the completed production/backup audits. The new overlay has 242 files /
3,978,591 bytes; it remains isolated from production.

**Still unknown:** 11 Cleveland cases /326 player-game cells. Four cases are blocked
only by the two rejected games. Seven also lack dated membership/participation
on dates omitted from qualified full-game sources (310 cells outside those games).
Missing rows are neither DNP nor nonmembership. No first/last-appearance or
season-roster tenure inference; seven existing disputed observations stay excluded.

**Next:** stop this pilot after staging acceptance; do not expand to more seasons.
Full-game recovery is reusable and improves real answers, but cannot establish
membership for players omitted from all game records. A wider batch needs a
measured complete-case benefit and qualified game bodies; resolve the two source
clock failures only if a bounded approved replacement is accessible, without
individual-player/PDF research or new infrastructure. Any future activation needs
exact protected approval; no publication preparation is implied by this checkpoint.

**Production remains separately verified:** active
`availability-season-inactive-2024-v1-20261116`, manifest
`0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc`;
69 complete 2024-25 cases and 93 prior 2023-24 cases. Independent audit44059932340 and
[permanent backup/secret-free restore44062070685](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-44062070685)
passed. The original publication readiness-failure receipt remains unchanged.

**Separate open requirements:** Core-1 limited acceptance (K08:16 PASS /26 MISSING
DATA /4 LIVE), Davis default-season/cross-team cases and 2026-27 freshness/readiness.
No scope/acceptance upgrade. K12, DQ-005 and the 484/PDF membership hunts remain parked.
The existing development-security advisory is informational red; blocking gates
remain required. Preserve prior generations, sources, saved branches and safeguards.

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
