# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Main `b8d1e26d` (PR627); approved publication, independent data
verification and separate backup/restore are complete.** All prior work remains.

**Now answers:** 69 complete 2024-25 player/team/season cases, up from 11
(58 added), across 23 teams. Both with/without questions cover all 82 games,
including genuine empty samples. Previous 93 complete 2023-24 cases and their
sources remain intact. Across the 707 tested 2024-25 candidates, **638 remain
incomplete / 20,649 player-game cells unknown**; seven disputed observations
stay quarantined. No entire club or league-wide completion is claimed.

Active: `availability-season-inactive-2024-v1-20261116`, manifest
`0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc`.
Previous `availability-season-inactive-2023-v1-20261115` is retained.
The ONE [approved publication44040333371](https://github.com/Bet-Zero/nbatools/actions/runs/44040333371)
recorded actual owner approval and successful writer133896348108. Its original
[readiness-failure receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-44040333371)
is preserved unchanged. Current readiness is503 solely because 2026-27 is missing;
no exception, repeat publication or rollback was performed. Details: PR627.

**Actual independent verification:**
[audit44059932340](https://github.com/Bet-Zero/nbatools/actions/runs/44059932340)
executed/passed one required test, zero skips/errors: all 1,216 bodies /
419,488,508 bytes, all 1,213 prior entries/source authority, actual published
707-case census, seven quarantines on14unknown game sides, **45 registered live
answers and seven unknown/empty controls** passed. Pointer unchanged, R2writes0.
The 138-query preparation proof is reused against identical data/runtime, not
claimed as138 new live requests. Separate checker confirmed zero findings.
Data verification is complete; Core-1/operational acceptance is not expanded.

**Backup and separate restore:**
[44062070685](https://github.com/Bet-Zero/nbatools/actions/runs/44062070685)
passed export, durable retention, a separate runner restore without R2 credentials
and restore retention. The [permanent seven-asset backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-44062070685)
binds the same manifest, 1,216 files and419,488,508 bytes. Archive66,039,100 bytes,
SHA256 `dd3361b2f4fb64cbb5b15360d2efe594e9e6fff8c6df0647e5570d9cf76ec786`.
Export pointer unchanged / R2writes0; restore production_writes0. Independent
checker verified actual jobs, receipts and assets. Do not repeat these checks.

**Coverage strategy reassessed; no new collection started.** More season-inactive
files alone will not address omitted DNPs. Retained ten complete games contain
52 verified non-appearances absent from the season inactive file (35 coach's DNPs),
plus two appearances not proved by canonical positive minutes. All are already
imported: these are source-gap evidence, not newly accepted data or season cases.
Trades and players omitted from both sources still need dated membership proof.
Missing rows, season rosters and first/last appearances never fill that gap.

**Next:** one bounded **2024-25 Cleveland full-boxscore pilot**, using PR619's
existing game-level recovery and approved archives, all listed players across
all82games. Current source-derived baseline is5 complete /21 candidate cases;
no retained full Cleveland game body remains to recover. Measure complete-season
answers on both the fixed baseline and any expanded candidate set. Aim to close
a majority of the expanded cohort before wider collection; do not assume that
outcome or extrapolate one club to NBA history. Reuse all qualified inputs; if
the bulk source or meaningful case gains fail, stop rather than start another
source-hunt chain. No individual-player/PDF research or new infrastructure.
No additional seasons, substantial backfill, costs or automatic refresh are
started; any future data activation still requires exact protected approval.

**Still separate:** Core-1 limited acceptance (K08:16 PASS /26 MISSING DATA /4 LIVE),
Davis default-season/cross-team cases and 2026-27 freshness/readiness remain open.
K12, DQ-005 and484 investigations stay parked/closed. Existing development-security
advisory remains red; all blocking main/PR checks passed. Preserve the safeguards.

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
