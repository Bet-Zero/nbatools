# NBA Tools completion program

## Resume checkpoint

**November 28, 2026. Integration lead Codex.** Start with the
[adopted plan and Section 6](execution-plan.md#6-completion-and-first-execution-assignment)
and [current frozen release evidence](stabilization-evidence-20261127.md).
[Prior checkpoint](https://github.com/Bet-Zero/nbatools/blob/f512933a02309c1a33ad4b68096e6878371699ea/working/nba-tools-completion-program/README.md)

**Cleveland is delivered and retained for recovery.** The last-good generation is
`availability-cleveland-2024-v3-20261124`, manifest
`d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
All 87 public controls passed. The original backup and independent full restore
verified 1,461 files. Cleveland was 31–13 without LeVert and 44–11 without
Hunter. TEAM participation covers 21/21 pilot players and rostered coverage is
14/21. [Activation](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-45763092143) ·
[Backup and restore](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-45763092143)

**Section 6 complete within the measured snapshot operating range.** All 1,907
numerical tests, 621 Raw QA cases and 521 filter comparisons executed with
zero snapshot-scope failures. The release preserves all original Live and
full-product requirements. The final deployment returned all seven checked
answers, including both concurrent cohorts. The exact native three-request
test and failure controls passed. The [W6A transition](w6a-transition.md)
uses independently accepted current evidence and retains the original
archive. [Release evidence](stabilization-evidence-20261127.md#corrected-release-acceptance)

The approved monitor passed scheduled execution after one timely retry, with
strict Live readiness still reporting `new_season_not_loaded`. All eight
production snapshot recovery cases passed and the isolated clock control kept
the clock running until the last case passed. The owner approved an eight-hour
recovery objective. [Monitoring and recovery evidence](stabilization-evidence-20261127.md#approved-monitoring-and-recovery) ·
[Scheduled run](https://github.com/Bet-Zero/nbatools/actions/runs/46097846832)

**The Lakers snapshot is active.** The owner approved the switch to
`availability-lal-team-2025-v1-20261127`, manifest
`2239be14825fed08e13da1cc118dd1082ea1f1edca86661ea39a7503ed5cce50`.
All six registered production answers and the exact original omitted-season
question passed. The owner-approved switch used one conditional pointer write
and retained Cleveland. A separate credential-free runner restored all 1,544
files from the 67,053,005-byte backup. The production monitor passed snapshot
health and scoring on the verified Lakers manifest. Strict Live readiness still
reports only `new_season_not_loaded`.
[Activation](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-46126604835) ·
[Backup and restore](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-46126604835) ·
[Production monitor](https://github.com/Bet-Zero/nbatools/actions/runs/46129690500) ·
[Original query proof](source-evidence/lakers-team-season-2025-26/original-33-production.json)

**Next action for W8.** Run protected read-only preparation for the
[Boston 82-game candidate](source-evidence/boston-team-season-2025-26/README.md).
The [acquisition](https://github.com/Bet-Zero/nbatools/pull/673),
[shared storage](https://github.com/Bet-Zero/nbatools/pull/674), and
[grouped preparation](https://github.com/Bet-Zero/nbatools/pull/676) changes
are integrated. The shared-object reader preserved exact 82-game Lakers
scoring in production and the [monitor passed](https://github.com/Bet-Zero/nbatools/actions/runs/46130934701).
Boston's exact local shared manifest plans 43 PUTs, reusing 1,541 files.
Confirm the live storage inventory, then seek the exact isolated upload
decision. Hosted candidate qualification and separate activation, backup,
restore, and monitoring still follow.

W8 still needs a second meaningful shared-object release and a grouped
expansion within the measured operating envelope. The 3,000-file limit
requires a source retention format qualification before league-wide
publication at the current per-game object count. W6B remains an archive
migration trigger. W9 still needs a selected current-data scope with timely
source arrival, positive deployed Live answers and a measured cadence.

**Original product ledger.** K08 is 17 PASS / 25 MISSING DATA / 4 LIVE.
Requirement #33, “Lakers record without Davis,” returns 53–29 across the 82
qualified selected-team games. Rostered and opponent eligibility cases still
require dated club evidence. [Current ledger](core1-acceptance-map.json) ·
[Original acceptance](acceptance-baseline-pr582.md) ·
[Coverage record](data-quality/DQ-006.json) ·
[Carry-forward](checkpoint-history-20261112.md)
