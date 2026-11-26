# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 26, 2026. Lead and operations writer: Codex.** W0 landed in
[PR #645](https://github.com/Bet-Zero/nbatools/pull/645), main `bbacf58c`.
PR #644's accepted production deployment is `dpl_E4SfKHXdhXx2dnKbL2qnGeSMaXN9`.
The only unrelated open PR is blocked
[#462](https://github.com/Bet-Zero/nbatools/pull/462). No other writer or background
worker is active. [Execution plan](execution-plan.md)

**Cleveland is active and its historical answers and backup are verified.**
The owner approved [run 45763092143](https://github.com/Bet-Zero/nbatools/actions/runs/45763092143).
One conditional pointer write and zero snapshot uploads selected
`availability-cleveland-2024-v3-20261124`, manifest
`d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
The independent receipt records 1,461 verified objects, all 87 registered public
answers and the retained previous manifest. Cleveland's 2024-25 record without
Caris LeVert is 31–13 in 44 games. TEAM appearances cover all 21 pilot players;
rostered missed-game coverage remains 14/21. [Activation receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-45763092143)

**Recovery and proof.** The separate credential-free runner restored the 1,461
files byte-exact from the 66,763,469-byte candidate archive. The qualified restore
path checked every hash and reused source qualification. A credential-free
follow-up using the actual verified R2 reader over the restored filesystem
returned 31–13 in 44 games without LeVert. This exercised the loader with an
offline object transport, using the retained verified pointer and archive. The previous generation
`availability-season-inactive-2024-v1-20261116` retains its exact backup and
restore. No prospective candidate ZIP preflight or production rollback rehearsal
was found in the activation evidence. Reuse the accepted PR #643 cold proof
(5.8248 s and six follow-ups) and #644 independent review and post-merge CI.
[Candidate backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-45763092143)
· [Previous backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-44062070685)
· [PR #643](https://github.com/Bet-Zero/nbatools/pull/643)
· [PR #644](https://github.com/Bet-Zero/nbatools/pull/644)

**Live and stabilization remain open.** Public readiness reports 503 with sole
`new_season_not_loaded`, on the intended Cleveland generation. Scheduled
monitor run 45768634065 failed before its representative query. W5A logs for
the current deployment show Python 3.12 and uv 0.13.5, initial install from
`pyproject.toml` and subsequent build-step installs from an untracked build
`uv.lock`. The logs omit a complete installed inventory and say that Active CPU
billing ignores the configured memory value. Original K08 remains 16 PASS /
26 MISSING DATA / 4 LIVE. Full original acceptance, Live freshness, league-wide
participation, K12 timing, DQ-005 and the 484 labeled unavailable rates retain
their existing scope and authority.
[Monitor run](https://github.com/Bet-Zero/nbatools/actions/runs/45768634065)
· [Production build](https://vercel.com/zeros-projects-686e97fc/nbatools/E4SfKHXdhXx2dnKbL2qnGeSMaXN9)

**W4A.** The run-all implementation preserves the strict overall verdict and
reports snapshot status separately. The monitoring and retained historical
applicability checks passed locally. The next action after landing is to run
the existing production probe and confirm a scheduled run attempts all three
checks. W4A's changed alert and recovery policy remains reserved. Follow up on
W2's reusable readiness validation and guarded recovery using read-only proof.
Existing Cleveland activation and export do not need repeating.
No new collection, historical backfill, spending, automatic refresh or Live work is authorized for this assignment.
The checkout's existing `work` branch and the saved work below are preserved.

## Preserved scope

- **Acceptance contract:** [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md),
  byte-exact, SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`.
  Its status cells are historical; its requirements still apply, as revised only by
  the owner's recorded scope decisions, including [the November 14 decisions](https://github.com/Bet-Zero/nbatools/pull/611).
- **Bindings per group:** [K01](k01-binding.md), [K02](k02-binding.md),
  [K03](k03-binding.md), [K04](k04-binding.md), [K05](k05-binding.md),
  [K06](k06-binding.md), [K07](k07-binding.md), [K09](k09-binding.md),
  [K10](k10-binding.md), [K11](k11-binding.md), [K12](k12-binding.md). K08 uses the
  [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622).
- **Carry-forward scope:** section 8 of the baseline lists the work Core-1 does
  not complete (wider combinations, roles/context data, play-by-play/lineups,
  unattended freshness, guided tools). Use the execution plan for the current sequence.
- **Saved unreviewed work:** Tatum branch at
  `b835874e7c31dc29c38d62fcda263af404c881fe`. Don't treat it as accepted or
  overwrite it.
- **Agent 2 launch prompt**, if it's ever restarted:
  [data-quality/agent-2-prompt.md](data-quality/agent-2-prompt.md).
