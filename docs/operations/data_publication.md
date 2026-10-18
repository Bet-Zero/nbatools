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

A separate read-only job downloads and checks every published object's bytes,
checks the pointer and previous generation, and verifies deployed readiness and
the selected package's registered application answers (including opening and
qualified team/player S4 queries for the combined package). A separate job without
R2 secrets preserves the receipt in a `data-publication-<run-id>` GitHub release.
A receipt saying `publication_started_outcome_unknown` or
`published_verification_failed` is not acceptance. Investigate the actual pointer
and retained prior generation before any recovery; no automatic pruning or
rollback is authorized by this workflow.

## One-time account setup

The latest read-only audit in run39091103560 found `copilot`, `Preview`,
`Production` and `r2-validation`; `r2-publication` was absent and its API request
returned 404. Publication readiness is **false**. The API exposes
`can_admins_bypass`; the existing environments have no required-reviewer
protection and are unsuitable for publisher credentials. Only the missing
dedicated protected environment/account setup is needed. Reuse the accepted
workflow and existing bucket; do not create duplicate publication infrastructure
or repurpose an application or read-only validation environment.
The audit cannot retrieve existing secret values or establish whether the account
custodian already has a suitable publisher token. Reuse that token when available.

In [repository environments](https://github.com/Bet-Zero/nbatools/settings/environments),
create **r2-publication** unless a later audit identifies an existing dedicated
publisher environment. Restrict deployment
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
artifacts are not permanent data storage; reacquire/revalidate an expired package
before registering a replacement. A prior approval never approves a changed
artifact or a new generation.
