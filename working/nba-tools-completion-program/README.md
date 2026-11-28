# NBA Tools completion program

## Resume checkpoint

**November 28, 2026. Integration lead Codex.** Start with the
[adopted plan and Section 6](execution-plan.md#6-completion-and-first-execution-assignment)
and [current frozen release evidence](stabilization-evidence-20261127.md).
[Prior checkpoint](https://github.com/Bet-Zero/nbatools/blob/cc14b1d329dcf6842833706096fd7ea908a663e6/working/nba-tools-completion-program/README.md)

**Cleveland is delivered.** The active generation is
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

**Current queue.** W7 and W8 prepared and qualified the 2025–26 Lakers candidate
`availability-lal-team-2025-v1-20261127`, manifest
`2239be14825fed08e13da1cc118dd1082ea1f1edca86661ea39a7503ed5cce50`.
It certifies all 82 Lakers sides. Independent upload verification checked all
1,544 data files and confirmed zero active-pointer writes. The protected preview
passed the 6.11-second cold query and all six follow-ups. The updated production
monitor passed against the immutable Cleveland base while strict Live readiness
remained failed. Main `99d63aec` is deployed and full CI passed.
Read-only activation preparation verified the unchanged Cleveland base and
measured a 67,053,005-byte backup for all 1,544 files. The next action is the
owner's decision on one conditional pointer PUT and zero snapshot PUTs in run
46126604835. After approval, verify deployed answers, backup, clean restore and
the new generation in production monitoring.
[Upload](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-46121655390) ·
[Hosted proof](source-evidence/lakers-team-season-2025-26/hosted-qualification.json) ·
[Monitor](https://github.com/Bet-Zero/nbatools/actions/runs/46125995235) ·
[Owner gate](https://github.com/Bet-Zero/nbatools/actions/runs/46126604835)

**W8 and W9.** The independently reviewed acquisition, storage and grouped
preparation candidates are in
[PR 673](https://github.com/Bet-Zero/nbatools/pull/673),
[PR 674](https://github.com/Bet-Zero/nbatools/pull/674) and
[PR 676](https://github.com/Bet-Zero/nbatools/pull/676). An exact offline Lakers
comparison projected 86 PUTs and 3,115,859 bytes with reuse. The complete
1,544-file archive and clean restore passed locally. Targeted R2 verification
passed the independent Cleveland answer and full backup. Main stays frozen
during activation. The offline league survey covered 1,230 games. Boston is the
next scope, with 69 of 82 complete team sides and 13 archive-indexed gaps.
The first draft binds four originals to the reviewed capture and native stage.
Run that bounded two-game acquisition after Lakers delivery. Broader shared
publication still needs a real released scope and clean recovery evidence.
W6B remains an archive migration trigger. W9 needs fresh source evidence,
positive Live answers and a measured publication and recovery cadence.

**Original product ledger.** K08 remains 16 PASS / 26 MISSING DATA / 4 LIVE.
The 2025–26 Lakers team-season slice uses all 82 final games. Requirement #33,
“Lakers record without Davis,” is one acceptance case for the slice. Verify
complete selected-side appearance coverage, contextual identity and independent
game records. Measure preparation, serving, publication and recovery effort
before proposing a wider cadence. Rostered cases require dated club membership
and qualified nonparticipation. [Original acceptance](acceptance-baseline-pr582.md) ·
[Coverage record](data-quality/DQ-006.json) ·
[Carry-forward](checkpoint-history-20261112.md)
