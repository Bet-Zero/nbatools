# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 14, 2026 (Detroit). Lead: Codex.** Live main verified at
`f22f87ae` (merged PR619/620, retaining PR618). Existing branches, Tatum work,
source originals, published generations and all completed acceptance are preserved.
No background data worker is running; Agent 2/DQ-005 and K12 cold-start stay parked.

**Core-1 remains limited acceptance on held data, not league-wide completion.**
The earlier 126 checks, deployed proof and K08 view (16 PASS, 26 MISSING DATA,
4 LIVE) remain recorded, not rerun. Davis' default-season/cross-team gaps, wider
coverage, current-season freshness and known unavailable advanced values remain
open. Prior release evidence and defects stay in the unchanged
[checkpoint history](checkpoint-history-20261114.md).

Last recorded published snapshot:
`availability-participation-2025-durant-v1-20261114`, manifest
`cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366`,
1,186 objects. No new live-pointer/freshness claim or production data publication.
Readiness's known `new_season_not_loaded` blocker remains.

**Current unit: PR621, `codex/dated-membership-sample`.** The generalized engine
and PR619's game-grain recovery remain unchanged. PR619's 278 staged explicit
rows (173 played/105 nonparticipants) still are not published; its passing
focused R2 run43674107752 is reused only for that unchanged process.

The new offline bulk membership assessment automatically reads a frozen 2023
opening PDF and the complete retained NBA transaction feed. Whole-team sample:
2023-24 Lakers and Rockets, 82 observed games each, 21/22 candidate identities,
all 21/17 played identities explained, 13 changes plus conversion/draft controls.
It flags Hinton/Hudgins opening conflicts and Windler's disputed waiver date;
zero-appearance trade members, pre-anchor waivers and two-way status stay distinct.
**No accepted tenure or inferred DNPs.** The feed begins July 2015 and has no
explicit expiry event type; older rosters/guides have exact recorded access gaps.
[Sources, measured coverage, originals and reproduction](source-evidence/team-membership-20261114/README.md).

Focused controlled tests passed (14); retained-source local replay executed/passed
one test after correcting the source expectation that Samuels actually played
in Houston's opener. Source-stage independent reviews and three bounded successful
capture/custody runs are preserved. The checker found two conditional boundary gaps (unanchored conversion/departure);
both have narrow fixes and unfamiliar controls. Final exact-code delta review, blocking CI and
focused R2 membership replay are pending; PR621 must not merge without them.
No whole-project audit, routine full suite or broad replay was started manually.

**Next:** finish PR621's focused independent review/required gates, then qualify
one bounded frozen season-final team chronology/game-notes archive for this sample.
It must settle the opening corrections, effective dates and whole-team contract
history before continuous intervals can enter the existing membership contract.
No first/last or whole-season guesses. Missing participation stays unknown.
Substantial historical backfill, production publication, new costs and automatic
refresh remain separately gated; nothing is currently needed from B.

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
