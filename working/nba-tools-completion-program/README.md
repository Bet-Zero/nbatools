# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 15, 2026 (Detroit). Lead: Codex.** Main is `b4c8b063` (PR623),
with all blocking post-merge checks passed. PR624, `codex/season-inactive-publication`,
prepares its exact qualified data for the existing protected publication process.
Prior work and originals remain preserved. No collection, source rebuilding,
production write or active-pointer change is authorized or performed.

**Core-1 remains limited acceptance, separate from league-wide completion.**
K08 remains 16 PASS / 26 MISSING DATA / 4 LIVE. Davis default-season/cross-team
cases and current-season freshness/readiness remain outstanding. K12, DQ-005,
the 484-rate source investigations and historical membership/PDF research stay
parked or closed. Older proof is in [checkpoint history](checkpoint-history-20261114.md).

**Qualified gain, still staged:** the unchanged PR623 ZIP qualifies 93 complete
2023-24 player/team/season cases, versus 18 published and 19 including prior PR619
staging. Every counted case covers all 82 games and both with/without queries.
Across 713 candidates, 620 remain incomplete: 134 include omissions in processed
reports; 486 have gaps outside those reports. Their 20,846 unknown player-game
cells retain unresolved membership and participation; missing rows never become
DNPs/nonmembers. No club is complete for every candidate.

Frozen preparation code `8168fbbc` passed independent review and targeted R2
[43788034248](https://github.com/Bet-Zero/nbatools/actions/runs/43788034248),
request `0dba4a1b`: 1 selected/executed/passed, zero skips/failures/errors.
All 186 complete-season API queries, the previous 18 cases, all 31 registered
published answers, every snapshot object and source/append preservation passed.
The transport copies the saved ZIP byte-for-byte; it invokes no source producer.
The deployed production record already contains PR623's reader, and runtime code
is unchanged by this preparation. Focused publication checks passed (44 tests).
Final registration review/CI and protected validate evidence belong in PR624;
reuse this frozen-code numerical pass when its covered bytes remain unchanged.

Proposed snapshot: `availability-season-inactive-2023-v1-20261115`, 1,213 objects /
415,007,162 bytes, manifest `8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8`.
The dry run projects 3,205,090,737 bytes against the unchanged 10 GB bucket ceiling.
[Preparation receipt](season-inactive-preparation.json) records exact source and
transport bindings. Existing live generation remains
`availability-participation-2025-durant-v1-20261114`, manifest
`cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366`.

**Activation blocker:** the authenticated public readiness check still returns
503 / `new_season_not_loaded` because 2026-27 is missing. The unchanged protected
post-publication verifier requires readiness 200. This historical overlay cannot
resolve that dependency; no operational acceptance, readiness exception or
activation approval is implied by successful preparation.

**Next:** finish registration and the existing protected **validate** run without
writes. Keep the active pointer unchanged while readiness blocks recommendation
of activation. Present an exact owner approval request only when publication can
pass its unchanged gates. After approved publication, expand the same bulk
participation approach to another season and measure newly complete season cases;
do not restart individual-player or historical membership research.

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
