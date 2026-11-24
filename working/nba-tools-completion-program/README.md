# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex, November 24.** [PR637](https://github.com/Bet-Zero/nbatools/pull/637)
and [PR638](https://github.com/Bet-Zero/nbatools/pull/638) are merged; workflow
main `c90e4ee6`. Production runtime `997efe5d` is READY. Production data remains
**availability-season-inactive-2024-v1-20261116 (0abc)**; no candidate upload,
active-pointer change or backup operation occurred. Owner-approved preview-only
Vercel Authentication is now enabled; the Hobby plan is unchanged.
The limited Core-1 snapshot remains closed; full original acceptance and
league-wide participation remain unfinished.

**Qualified improvement:** all 82 Cleveland 2024-25 regular-season side lists
support complete TEAM WITH/WITHOUT for the 21 original pilot candidates. Without
LeVert 31–13, Hunter 44–11, Curry 64–18; WITH Curry is known-empty, not 0–0. Team
scope means appeared FOR Cleveland, including pre-join/post-leave games and
opponent appearances. Rostered missed games retain strict membership/DNP rules:
14/21 complete, with seven cases/318 cells unknown. BKN 0022400199, malformed originals,
disputed observations, zero-minute ambiguity and missing membership stay guarded.

**Exact upload-only approval packet — actually prepared and independently read:**
- Package `cleveland-team-appearances-2024-v1`; publisher `564f2e05`.
- Generation `availability-cleveland-2024-v3-20261124`.
- Manifest `d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
- Base `availability-season-inactive-2024-v1-20261116`, manifest
  `0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc`.
- 1,461 manifest-listed files/423,517,896 bytes. Bucket 3,615,096,504 bytes;
 conservative projection 4,048,614,400 bytes including 10 MB headroom, below 10 GB.
- Upload ceiling 1,462 candidate-object PUTs, **0 pointer PUTs**; candidate SDK
 one attempt, at most 100,000 reads / 100 LIST pages per inventory. Preview bound:
 two deployments/eight queries. No automatic publication retry or refresh.
- Reuses exact v2 ZIP `a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298`
 and appearance proof `fd637c6d36c4fd9ce30b9e3f769c9ba806f535b9a943dc4be3fc6314529df86a`.

**Verification:** independent checker `/root/coverage_checker`, zero open findings.
Required real-data run[45375696531](https://github.com/Bet-Zero/nbatools/actions/runs/45375696531)
actually selected/executed/passed one test with zero required skips: complete-source
preservation, 45 prior registered checks, 44 TEAM answer controls and seven rostered
unknown controls. Source/deployed evidence from PR633–635 is reused at its original
scope. All blocking pre/post CI passed for PR637/638 (including three main Python
jobs each); the existing development-security advisory remains informational red.
Protected[validate 45383154974](https://github.com/Bet-Zero/nbatools/actions/runs/45383154974)
passed on main c90; its literal `prepared_no_writes` JSON matches the exact tuple
above, and all writer/activation/backup jobs were skipped. Earlier failed tests,
their focused fixes and the initially unread 453787 receipt remain recorded in
the PRs; none is relabeled as a pass. Logging the existing nonsecret tuple resolved
artifact readback without new access or infrastructure. No broad audit was run.

**Owner authorization received November 24:** the owner replied “yes i approve”
to the exact upload-only packet above and bounded $0 private-preview access.
This authorization persists; do not request the same chat approval again.
Production activation remains UNAPPROVED.

**Upload is queued, not performed:** existing protected
[run45391469130](https://github.com/Bet-Zero/nbatools/actions/runs/45391469130)
is pinned to main `11ab5aad1db7897fec0b871e6d9dba77dd6929e3`, mode
`upload_candidate`. Fresh resolve/preparation passed and its actual receipt was
independently read: exact approved manifest/base/publisher/registry, 1,461 files,
423,517,896 bytes and unchanged 4,048,614,400-byte projection. The protected
writer is WAITING for `Bet-Zero` to use **Review deployments → r2-publication →
Approve**. A transparent delegated approval attempt through the existing owner
connection returned GitHub403 “Resource not accessible by integration”; no
approval was accepted, no R2 write occurred, and no broader credential or gate
change was attempted. Use the existing owner UI, not another upload run.

**Freeze main while this operation is pending/running.** The writer verifies
live main still equals its workflow revision. Do not merge this checkpoint or
any other PR until the upload/independent verification/receipt finishes (or an
explicitly approved cancellation). The handoff branch is
`codex/cleveland-upload-approved`; a draft docs PR preserves these facts without
invalidating the queued protected operation.

**Private-preview access:** fresh Vercel readback confirms project
`prj_luTVKSLCFRQP3BYwk93XETz9WwCy` has `ssoProtection.enabled=true`,
`deploymentType=preview`; password protection remains off and public production
protection is unchanged. Official Vercel pricing confirms Authentication is
included on Hobby. No candidate preview or temporary access link was created.
The workspace still enforces GitHub/package-manager hosts only. The authorized
request to add `*.vercel.app` was rejected by the managed environment because its
published configuration does not allow that access. The owner must add that
approved rule to the published network settings, preserve existing grants, and
apply it to this task. Chat approval alone did not edit the configuration.
No paid feature, broad credential or public development override is allowed.

After the existing owner environment gate is approved, let this same upload run
complete; do not repeat publication. The exact packet/base/budget are already
reconfirmed. Keep the active production pointer unchanged.
Independently verify every uploaded body and unchanged production pointer. Then
qualify an actual new protected preview's first query/loader miss within 20 seconds;
GitHub-runner/local timing cannot qualify it. Stop on failure. If it passes,
prepare a separately approved activation using **the same uploaded objects**,
with one pointer CAS and zero snapshot PUTs. Activation is not exposed before
that qualification. Original strict readiness and separate data/backup/restore
verification remain required after any future approved activation.

**Separate unfinished requirements:** original K08 remains 16 PASS / 26 MISSING
DATA / 4 LIVE; no original question, controlled positive, baseline or acceptance
outcome was changed. The new product meaning does not upgrade the 26 unsupported
cases. Live still includes current-season publication/membership, 24-hour
freshness, literal-current cases and K12 timing; 2026-27 readiness remains
503/new_season_not_loaded. Original failure receipts, verified backups, DQ-005
and 484 unavailable rates remain preserved. No new NBA collection, historical
research/backfill, spending, automatic refresh, wider season expansion or Live
implementation is authorized by this checkpoint.

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
