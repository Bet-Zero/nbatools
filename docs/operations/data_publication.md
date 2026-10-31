# Protected data publication

## Accepted protected GitHub Actions process

The owner superseded the terminal handoff on 2026-10-17. The reusable manual
workflow was independently reviewed, verified without writes, and merged in
[PR472](https://github.com/Bet-Zero/nbatools/pull/472). Its acceptance does not
authorize production publication. The owner does not need terminal commands.
The reviewed snapshot validator remains pinned by commit and checksums.

Select a merged, reviewed package in
[Protected R2 Data Publication](https://github.com/Bet-Zero/nbatools/actions/workflows/r2-data-publication.yml).
Use **main** and **validate**. This rebuilds the complete immutable snapshot with
existing read-only validation credentials, checks every source/code checksum,
authenticates the existing base manifest, and reports total storage cost bounds.
The original `opening-availability-v1` package remains available. The combined
`opening-s4-availability-v1` package in [PR482](https://github.com/Bet-Zero/nbatools/pull/482)
adds the opening game and four qualified BOS/LAL reports together; use it only
after that PR is merged and its post-merge CI passes. Its no-write snapshot
preserves all 684 existing objects and adds 18 source objects plus the derived
player-name index: 703 objects, 402,749,125 bytes. The full proposed manifest and
six consumer checks passed in
[run39091103560](https://github.com/Bet-Zero/nbatools/actions/runs/39091103560);
the PR records source bindings, checksums and remaining publication boundaries.
It never receives write credentials. A changed base requires a newly reviewed
package; changing an input cannot override it.

Production publication still requires a separate explicit owner authorization.
Only then may **publish** be selected. Review the preparation summary's package,
source artifact SHA256, publisher commit, base generation, proposed generation,
full manifest SHA256 and storage projection before approving the dedicated
`r2-publication` environment deployment. The publishing job rebuilds and compares
that exact snapshot before invoking the existing immutable publisher. There is no
arbitrary artifact, commit, shell-command or expected-base input.

### Retained K08 package — published and verified

[PR551](https://github.com/Bet-Zero/nbatools/pull/551) passed complete read-only
preparation in [run41178844607](https://github.com/Bet-Zero/nbatools/actions/runs/41178844607):
724objects,402,948,225bytes, manifest `de83522f…`, all13APIanswers and
byte-exact63,805,709byte backup/restore within the unchanged bounds. Compact
[acceptance receipt](https://github.com/Bet-Zero/nbatools/pull/551#issuecomment-6540420485)
retains the original preparation tuple and answers. The owner subsequently
published this exact package in run41184300649. Read-only recovery41189755604
verified all724published objects/readiness/13liveanswers; backup41190106961
completed durable retention and separate secret-free restore. See the recovery
section below; do not publish this generation again.

`retained-k08-availability-v1` prepares six already-qualified games: the retained
1997 Nets/Indiana, 2004 Detroit/Houston and 2014 New Orleans/Orlando structured
originals, plus the three authorized Lakers reports for October24/26/27,2025.
It performs no source acquisition. Original retrieval timestamps and archive
attribution remain; republication does not make the data fresh.

The fixed publisher binds the existing base manifest `5497832b…` and permits only
an append to the two registered 2025-26 availability CSV/import-lineage files.
Each prior CSV cell and import entry must remain equal; the exact three new PDF
game IDs and104new rows are bound to the reviewed artifact. Historical files and
source originals are additions. The existing opening-game PDF clock authority
cannot be replaced by the structured opener. All other existing snapshot objects,
transport/backup limits and protected publication gates remain unchanged.

Read-only acceptance must check the complete proposed snapshot, all thirteen
registered API answers (including exact missed-date population and player game
lists), and byte-exact bounded backup/restore. A successful preparation is still
`prepared_no_writes`: it does not authorize publication or resolve full-season
absence/membership coverage. Review the exact immutable publisher, source artifact,
base/proposed manifests and storage projection before any separate owner approval.

A separate read-only job downloads and checks every published object's bytes,
checks the pointer and previous generation, and verifies deployed readiness and
the selected package's registered application answers (including opening and
qualified team/player S4 queries for the combined package). A separate job without
R2 secrets preserves the receipt in a `data-publication-<run-id>` GitHub release.
A receipt saying `publication_started_outcome_unknown` or
`published_verification_failed` is not acceptance. Investigate the actual pointer
and retained prior generation before any recovery; no automatic pruning or
rollback is authorized by this workflow.

## Already-published generation: read-only recovery

**Completed:** [recovery41189755604](https://github.com/Bet-Zero/nbatools/actions/runs/41189755604)
passed all724published object bytes, production readiness and all13registered live
API answers. All requests returned HTTP200 on their first attempt with seven-second
spacing. [Backup41190106961](https://github.com/Bet-Zero/nbatools/actions/runs/41190106961)
then passed export, durable retention, separate secret-free restore and receipt
retention. The [permanent backup release](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-41190106961)
binds724files/402,948,225bytes and a63,805,709byte archive, SHA256
`1889fcc9aaf704930caee81ea856c05cd82b87f6608c8c9cd58a3e3ada23c0e8`.
The [PR553 recovery/backup receipts](https://github.com/Bet-Zero/nbatools/pull/553)
preserve all answers, manifests, workflow identities and original protected
approval. The historical failed receipt remains unchanged; recovered verification
is complete. Normal K08 development can resume. No publication/pointer change,
rollback, new credential or fresh NBA acquisition occurred during recovery.

Run41184300649 activated `availability-k08-retained-v1-20261031` successfully;
its historical receipt is `published_verification_failed`, after all724objects
and production readiness passed. This is **not** an instruction to publish again
or roll back. Preserve that receipt and the previous generation.

The focused13-query replay reproduced HTTP429 `rate_limited` at check11, the
LeBron missed-count query for October24and27,2025, after ten correct answers.
The public quota remains10queries/60seconds. Recovery41188880371 also retained
an edgeHTTP429 withoutRetry-After at the same check, so waiting only after an
application rejection was insufficient. The verifier spaces query starts7seconds
apart (at most9per rolling minute, leaving readiness headroom) and honors a strict integer
`Retry-After` of1..60 once per check, retaining every attempt and still requiring
all registered numeric/route/identity/population assertions. Other HTTP failures
and semantic contradictions remain failures. The original generic failure did
not retain its HTTP response; the reproduction is identified separately.

`tools.recover_k08_publication` is a fixed read-only recovery for that original
run, successful protected write job and reviewed publication-artifact digest.
It authenticates the original approval/package, preserves original identity,
and records a separate recovery workflow identity. It shares only the read-only
byte/pointer/readiness/API verifier; it cannot prepare, publish or roll back.
Use its explicit cloud recovery test through the existing reviewed R2 validation
request route. After verification passes, use the existing exact-generation
cloud-backup request/retention/secret-free restore route. Preserve a durable
recovery receipt alongside the original failed publication receipt. Success
requires all13answers and backup/restore evidence; a diagnostic failure is never
acceptance. No production writer credentials or new protected approval are needed.

## Publication startup failure before any jobs

[Run41181464506](https://github.com/Bet-Zero/nbatools/actions/runs/41181464506)
used the correct main/package/publish inputs but was rejected before creating any
jobs. GitHub's annotation identified a nested token-permission conflict: the
mixed validation workflow contains release-writing inventory/backup jobs, which
cannot be nested under a read-only caller even when their job conditions are false.
Preparation and verification therefore call the dedicated
`r2-publication-readonly.yml`; its single moved job keeps the same R2 validation
environment, named read-only secrets, immutable package checks, artifacts and
shared lock. The backup call keeps its existing explicit GitHub release permission.
The protected writer and owner approval remain separate and unchanged.

After a startup repair merges and post-merge CI passes, use **Run workflow** for a
fresh run on **main** with package **retained-k08-availability-v1**, mode **publish**.
Do not rerun the failed run: reruns retain its original workflow revision. Review
the newly prepared approval tuple, then approve the existing `r2-publication`
environment. A zero-job startup failure publishes nothing; success still requires
the protected write, live verification and durable publication receipt.

## First successful production publication — 2026-10-18

**SETUP PROVEN END-TO-END.** The owner explicitly authorized the reviewed package `opening-s4-availability-v1` and separately approved the protected `r2-publication` deployment. [Production run 39102232398](https://github.com/Bet-Zero/nbatools/actions/runs/39102232398) completed **SUCCESS** across preparation, write, read-only verification and durable receipt. The canonical [GitHub Release](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-39102232398) holds `receipt.json` with `publication_state=published_and_verified`.

- **Active R2 generation:** `availability-opening-s4-v1-20261017`, activated `2026-10-18T06:15:50Z`, manifest SHA256 `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`.
- **Verified scope:** 703 immutable objects, 402,749,125 bytes, source-qualified player participation data from five NBA games; old generation `queue-d-production-0574735-20260716` retained. The package is **not** season-wide absence coverage.
- **Live checks:** the deployed readiness response returned `ready`, the new active generation, no blockers; all six registered production-answer checks matched (LAL/GSW 2025 opener and Celtics/Tatum/Brown with/without qualified teammate across reviewed games).
- **Protected authority:** environment `r2-publication` ID `24614443886`, exactly one `main` branch rule, required reviewer `Bet-Zero`, disabled administrator bypass. The owner-approved write job and separate read-only verifier passed. Earlier missing-environment API HTTP404 is **resolved**.
- **Operational boundary:** the existing GitHub workflow can **manually** validate and publish future reviewed generations without a local laptop. This first success does **not** set up unattended scheduled data collection or automatically approve any future production update. Codex and unrelated feature development remain owner-paused.

The earlier read-only and environment-404 notes below are historical, from before this successful publication; they are not current blockers.

## Historical read-only execution (2026-10-18)

The owner-triggered first attempt [39095431450](https://github.com/Bet-Zero/nbatools/actions/runs/39095431450) failed because a reusable workflow call did not pass its three existing read-only `R2_VALIDATION_*` secret names. [PR #489](https://github.com/Bet-Zero/nbatools/pull/489) fixed only that mapping, retaining the environment's credential isolation, deployment review, and no-write `validate` mode. The new [run 39099028557](https://github.com/Bet-Zero/nbatools/actions/runs/39099028557) **succeeded on merged main**, with the full proposed `opening-s4-availability-v1` snapshot: 703 objects, 402,749,125 bytes, manifest SHA256 `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`. Receipt artifact `12126046663` has ZIP SHA256 `3587b20ea0675ee8f92c4864e9fbd0c5761fa05169d53f7bad804434af3a6957`. State `prepared_no_writes`; **no R2 write, active pointer switch, or production publish was performed**.

At the time of this **earlier read-only** run, the dedicated production environment had not yet been correctly configured and GitHub's audit returned HTTP 404. The owner subsequently created/configured the separate environment. The protections were verified in [audit 39101964895](https://github.com/Bet-Zero/nbatools/actions/runs/39101964895), and the first production publication then succeeded in [39102232398](https://github.com/Bet-Zero/nbatools/actions/runs/39102232398). This older 404 is no longer an action item.

## Existing production environment — keep configured

The dedicated `r2-publication` environment was created and verified successfully
with branch `main` only, required `Bet-Zero` reviewer, and disabled administrator
bypass. Its three publication environment secrets worked in the approved production
run. **Do not re-create the environment, re-enter the secrets, create another bucket,
or repeat the initial account setup for future publications.** The original read-only
`r2-validation` environment remains separate; preserve both.

In [repository environments](https://github.com/Bet-Zero/nbatools/settings/environments),
first verify **r2-publication** and the existing protections on the *exact* `Bet-Zero/nbatools`
repository; do not create a duplicate environment or token based on the current 404 alone. Restrict deployment
branches to **main** (branch, not tag), require **Bet-Zero** as reviewer, and disable
administrator bypass. Preserve stricter existing protections. If self-review is
prevented, an authorized different initiator must start the run; never weaken that
setting merely to let the sole owner dispatch and approve the same run.

Keep the existing R2 validation environment and runtime token read-only. Store
publisher values only as **environment secrets**, never repository secrets:
`R2_PUBLICATION_ACCOUNT_ID`, `R2_PUBLICATION_ACCESS_KEY_ID`, and
`R2_PUBLICATION_SECRET_ACCESS_KEY`. Reuse the existing bucket-scoped publishing
credential through its authorized account custodian when available; do not copy
it into chat, Codex Cloud, ordinary CI or a pull request.

Only if no suitable publisher credential is available, open the
[Cloudflare dashboard](https://dash.cloudflare.com/), choose the existing account,
then **R2 Object Storage > Overview > Manage R2 API Tokens**. Create an account API
token with **Object Read & Write**, restricted to the existing **nbatools-data**
bucket. Do not grant Admin Read & Write or all-bucket access. Save its Access Key
ID and Secret Access Key directly into the two environment secrets above, and
the existing account ID into the account secret. Do not change billing limits or
create another bucket. Follow the current
[Cloudflare R2 token instructions](https://developers.cloudflare.com/r2/api/tokens/)
if dashboard labels differ. GitHub cannot recover a stored secret value; use the
existing custodian rather than requesting its disclosure.

Future updates use this same process: agents acquire and qualify data, commit a
reviewed registry package with immutable code/source/base bindings, run read-only
preparation, and obtain required publication authorization. Temporary Actions
artifacts are not permanent data storage; rebuild/revalidate an expired package
from retained qualified originals where available before registering a replacement.
Fresh acquisition still needs its applicable authorization. A prior approval never approves a changed
artifact or a new generation.
