# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Main `15a67708` (PR624 merged), all blocking CI passed.**
The owner-approved 2023-24 participation package is **published, independently
verified and backed up**. Source originals, prior generations and saved work remain.

**Now answers:** 93 complete player/team/season cases, versus 18 before publication.
Each covers all 82 regular-season games and both with/without questions. Across
713 candidates, 620 remain incomplete; their 20,846 unknown player-game cells
remain unknown. Missing rows or season rosters never prove DNP/nonmembership.
No entire club is complete for every candidate; league-wide completion is not claimed.

Active generation: `availability-season-inactive-2023-v1-20261115`, manifest
`8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8`.
Protected publication [43801111855](https://github.com/Bet-Zero/nbatools/actions/runs/43801111855)
completed its owner-approved write. Its original
[failed readiness receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-43801111855)
remains unchanged: operational readiness still fails solely because 2026-27 is
missing. No readiness exception, rollback or second publication was performed.
Previous generation `availability-participation-2025-durant-v1-20261114` is retained.

**Actual independent verification:**
[audit43807804521](https://github.com/Bet-Zero/nbatools/actions/runs/43807804521)
executed/passed one required test, zero skips/errors: all 1,213 object bodies /
415,007,162 bytes, all old cells/imports/source authority, 38 live registered
answers and three unknown/empty controls passed; the active pointer stayed fixed.
All seven new live summaries retain the correct teams and 2023-24 regular-season
scope. The 186-query preparation proof is reused against the identical published
manifest and runtime, not claimed as 186 new live requests. Separate checker
confirmed the executed results with zero findings. Exact details are in PR624.

**Actual backup and restore:**
[43809073200](https://github.com/Bet-Zero/nbatools/actions/runs/43809073200)
passed export, durable retention and a separate restore with no R2 credentials or
production writes. Both bind the same 1,213 files and approved manifest. The
[permanent backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-43809073200)
retains the 65,801,094-byte archive and both receipts; archive SHA256
`9a4dcc389a1b27c732be717b694bc30ed5f2002c0296c689ace38b2a7ce4e846`.
Independent review confirmed all seven retained assets. No source/test replay is
needed for this completed publication.

**Still separate:** Core-1 remains limited acceptance (K08: 16 PASS / 26 MISSING
DATA / 4 LIVE). Davis default-season/cross-team cases and current-season
freshness/readiness remain unresolved. K12, DQ-005, the 484-rate investigations
and historical membership/PDF research stay parked or closed. The existing
development-security advisory remains red; production/blocking CI passed.

**Next:** one bounded 2024-25 bulk participation pilot. Reuse retained data and the
same qualified season-inactive producer, measure newly answerable complete-season
cases, and preserve all unknowns. Additional production publication needs its own
explicit approval; no automatic refresh, new costs or substantial historical
backfill is authorized. Do not restart individual-player or membership research.

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
