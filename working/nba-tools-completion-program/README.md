# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Main `2c7d8cca` (PR626), all blocking post-merge CI passed.**
Production still uses `availability-season-inactive-2023-v1-20261115`, manifest
`8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8`.
It answers 93 complete 2023-24 cases (previously18); 620/713 candidates remain
incomplete. That publication is independently verified and backed up: see
[PR624](https://github.com/Bet-Zero/nbatools/pull/624),
[audit43807804521](https://github.com/Bet-Zero/nbatools/actions/runs/43807804521) and
[permanent secret-free restore/backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-43809073200).
Prior sources, old generations and saved branches remain. Do not repeat those
completed checks or call the preserved failed readiness receipt a data failure.

**Current task: exact 2024-25 protected-publication preparation, not activation.**
Branch `codex/season-inactive-2024-publication`; immutable publisher `a7816498`,
[PR627](https://github.com/Bet-Zero/nbatools/pull/627). Package
`season-inactive-2024-v1` targets `availability-season-inactive-2024-v1-20261116`.
The exact PR626 three-file ZIP is reused, SHA256
`a910703174d54873965f36f5f855e214fdb186a209565332922749f63de73e50`;
no collection, reconstruction, overwrite or append is permitted.

**Actual no-write full-snapshot proof:**
[43822127410](https://github.com/Bet-Zero/nbatools/actions/runs/43822127410)
executed/passed one required test, zero skips/errors. It binds reviewed6000c157 /
requesta1384804 to current base8ec. All 1,213 old entries/bodies remain identical;
only three paths are added: **1,216 files /419,488,508 bytes**, manifest
`0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc`.
All **69 complete cases versus11**, across23teams, passed138 API checks; all38prior
registered checks passed. All37,392 published2023 observations are unchanged,
reusing the93-case proof rather than claiming93 fresh live requests.
Seven disputed observations remain quarantined on14unknown game sides;
**638/707 cases and20,649 player-game cells stay unknown**. No club or new tenure
interval is complete. The existing engine and PR626 source qualification remain.

Deployment7817308443 /2c7d8cca supports the reader; source bytes were matched.
Actual readiness503 is solely2026-27 `new_season_not_loaded`, no exception applied.
Actual storage projection:3,624,837,557 /10,000,000,000 bytes. Pointer unchanged,
R2writes0. Separate checker confirmed actual results, zero findings. An initial
stale-generation test-helper failure is retained inPR627; it is not passed proof.
Registry preserves every old package/check and adds seven source-qualified live
examples. Protected **validate** on mergedmain is still required before approval;
its actual receipt and independent inspection belong inPR627. Do not activate
unless B explicitly approves the exact package/base/generation/manifest tuple.

**Next:** finish protected no-write validation and present that exact approval.
After approval, recheck the tuple/base, use the protected writer, independently
verify all published data/answers and complete the separate existing backup and
secret-free restore. Known readiness failure will likely skip automatic live
verification/backup: do not waive it or claim those steps passed until executed.
Stop for a genuine data/publication problem; no unapproved rollback.
After publication is verified/backed up, **reassess the coverage strategy before
more season batches**: roughly10% complete cases is not league-wide functionality.
No individual-player research, speculative absences, reopened membership/PDF hunt,
automatic refresh, new costs or substantial backfill is authorized.

**Still separate:** Core-1 limited acceptance (K08:16PASS/26MISSING DATA/4LIVE),
Davis default-season/cross-team cases and current-season freshness/readiness remain
open. K12, DQ-005 and484 investigations stay parked/closed. Preserve all blocking
gates; the existing development-security advisory remains red.

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
