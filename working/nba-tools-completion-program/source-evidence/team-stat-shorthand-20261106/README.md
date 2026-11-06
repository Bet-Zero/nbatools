# Shared team noun threshold evidence

Agent1 repairs the recorded PR587 noun-threshold positive and P1/S3 condition
ownership. On baseline4bd2f799, missed questions are withheld and played-player
questions can bind the team number to the individual player's statistic. The
shared span/owner reader now carries team-owned noun bounds through the existing
player/team calculations; no player, phrase or season exception is introduced.

The bounded contract covers supported whole-game box-score counts with plus/bare
floors, strict/inclusive bounds, explicit exact zero, own-player/opponent clauses,
venue and existing sample/split consumers. Required controlled positives and
unread-name/unit guards live in `tests/test_team_stat_shorthand.py` and the
multi-team absence tests. Unsupported operation families remain unfinished;
refusal is containment, never positive acceptance.

`tests/cloud_team_stat_shorthand_real_data.py` replays PR587's retained qualified
originals and producers, validates identity/schema before consumption, and checks
five date-specific Spurs absence predicates plus Looney/Warriors consumers.
The author direct local replay passed; it is not an executed pytest/R2 gate.
`author-native-replay.json` retains exact IDs/counts/answers. Actual required hosted execution now passed in
[run42202957484](https://github.com/Bet-Zero/nbatools/actions/runs/42202957484):
4selected/4executed/4passed, zero skips/failures/errors/xfails. The request
`be1fde1b054c139c248092fad1d935924a079e5a` has sole parent/reviewed source
`3105fee4dabfe8826d10151cbe932699800b2af9`. Pinned immutable base
`availability-lebron-season-v1-20261031`, manifest
`3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`.
Actual R2 RawQA passed4cases/33checks with zero suspicious flags.
`required-summary.json` and `raw-qa-summary.json` preserve actual structured
job-log verdicts and the unchanged renderer output snapshots.

Broad preflight3e38cbe2 ended10201passed/1863unavailable-data skips/2failed.
The stale inventory600vs603 was regenerated, and the old ranked-opponent refusal
was deliberately replaced with raw exact-ID positive support after independent
verification (including a different entity/threshold). Affected60tests and
2corrected named-owner assertions pass;19initial independent controls and the
2ranked-opponent promotion controls pass. Review explicitly bounds applicability
of unaffected broad results across the narrow named-owner runtime delta.
`software-validation.json` retains original failures/resolutions; no failing or
incomplete broad execution is relabeled an exact-head pass. Final exact-head CI
and landing receipts remain in PR589. No new source was acquired or data published.

Three new canonical Raw QA cases check the strict versus inclusive110teamPTS
boundary: Warriors under110=14games/3wins/11losses; Looney14games/113REB;
Looney through110=17games/143REB. These are independently selected from the
original JSON regular-season22022 rows, not copied from engine output. Existing
qualified inputs and numerical/RawQA backstops remain required.

Native full-season Poeltl acceptance remains pending DQ-004 original tenure
sources; no proposed total is accepted. DQ-005 reported margins remain unqualified
and unused. The existing exceptions and all46positive obligations are preserved.
Production publication, freshness acceptance, K12 and Agent2 are outside this
checkpoint. Final review, hosted and landing receipts belong in the task PR.
