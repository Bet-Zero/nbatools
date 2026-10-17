# Protected data publication

## Protected GitHub Actions process (implementation under review)

The owner superseded the terminal handoff on 2026-10-17. PR472 prepares a reusable
manual workflow; it is not yet accepted or permission to publish. The owner does
not need to run terminal commands. The original reviewed script remains the
snapshot validator behind the workflow, pinned by commit and checksums.

After acceptance, select the reviewed `opening-availability-v1` package in
[Protected R2 Data Publication](https://github.com/Bet-Zero/nbatools/actions/workflows/r2-data-publication.yml).
Use **main** and **validate**. This rebuilds the complete immutable snapshot with
existing read-only validation credentials, checks every source/code checksum,
authenticates the existing base manifest, and reports total storage cost bounds.
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
the Lakers-without-LeBron/Warriors-without-Moody answers. A separate job without
R2 secrets preserves the receipt in a `data-publication-<run-id>` GitHub release.
A receipt saying `publication_started_outcome_unknown` or
`published_verification_failed` is not acceptance. Investigate the actual pointer
and retained prior generation before any recovery; no automatic pruning or
rollback is authorized by this workflow.

## One-time account setup, only after workflow acceptance

The read-only audit in run39006702706 found `copilot`, `Preview`, `Production`
and `r2-validation`; no publisher environment exists. It confirmed the API exposes
`can_admins_bypass`. A new dedicated publisher environment is therefore necessary;
none of the existing application or validation environments should be repurposed.
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
