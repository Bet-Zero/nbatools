# NBA Tools W3A host cutoff experiment

Read-only inspection confirmed production deployment
`dpl_9J2PKZ7bxgs8uqSEx2NtpY1b3bCN` at `b55cc24475da64d1797c87561e7a7f8e5cb925a4`
in `iad1`. Its build log says Active CPU billing ignores the declared 1,024
MiB. The connected deployment and project reads did not expose effective per-function
timeout or memory and this environment has neither Vercel CLI credentials nor a
configured Vercel API identity. The declared 20 s and 1,024 MiB are build inputs.

## Single reserved action

Create exactly one SSO-protected Vercel preview through the project's normal Git
integration. Create the currently absent Git branch `diagnostic/w3a-host-cutoff`
at the existing reviewed commit `f9aaf7a1658b432e1686ca522296f58feac168e6`, tree
`10495819c04866b3fcb0be764da623c6d92fcea2`. The review branch
`codex/w3a-cutoff-review-production-gate` points to that same exact commit and
is deployment-disabled. Creating the diagnostic ref supplies the actual provider
Git ref needed by the guard. The project is `prj_luTVKSLCFRQP3BYwk93XETz9WwCy`
in `zeros-projects-686e97fc`, with preview SSO enabled. Keep normal preview
read-only R2 credentials and the published Cleveland generation. There is no
configuration edit or system-variable override.

Record the ready immutable deployment ID and URL. Require provider-reported
preview target/environment, diagnostic Git ref, exact commit, preview protection,
and the actual built runtime/region. Require evidence that the preview uses the
existing read-only runtime connection and Cleveland generation
`availability-cleveland-2024-v3-20261124`, manifest
`d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
If any identity fails or the normal build is skipped, stop without another build.
If an existing authenticated inspection becomes available, bind and compare
`timeout`, `memorySize`, and `deployedTo` for both functions and production.
If it establishes the settings adequately before the probe, omit the hold and
avoid the reserved action. Without effective equivalence, results stay scoped to
the diagnostic deployment.

The source declares `api/query.py` and `api/structured_query.py` at 20 s each.
The diagnostic and production declarations and locks match exactly.

| Input | SHA-256 |
| --- | --- |
| `vercel.json` | `be68d6a90210a144711069bef4f0af844893a1a8d07b388a2a30c016daa71ae1` |
| `uv.lock` | `9e37abdc3e4c0cf95670157638ff9e8d936470cd9376c3ca26c3005899b223f3` |
| `frontend/package-lock.json` | `6ccf63e2790b36f9c70150f41b2c858fdf55aa0dd1f18e68b55daa914dd6510e` |

## Four sequential requests

Once the immutable preview is verified, create one deployment-scoped share
link with TTL 600 seconds. Keep the share secret and resulting cookie private.
Use one cookie session with no request retries and no redirects for the query
POSTs. Record only status, complete response, wall time, safe request and
provider IDs, and correlated server events.

1. POST `/query` with
   `{"query":"Cavaliers record without Caris LeVert in 2024-25"}`.
   Expect HTTP 200, 31 wins, 13 losses, 44 games.
2. POST `/structured-query` with
   `{"route":"team_record","kwargs":{"team":"CLE","season":"2024-25","without_player":"De'Andre Hunter"}}`.
   Expect HTTP 200, 44 wins, 11 losses, 55 games.
3. POST `/query` with `{}` and
   `X-NBATools-Deadline-Probe: provider-cutoff`.
4. Repeat the fixed witness body and header once on `/structured-query`.

Stop immediately on a failed positive control or unexpected authentication,
identity or provider response. Revoke the link immediately on every exit, with
regeneration disabled. If revocation is unavailable, record that fact and wait
for confirmed expiry. No additional links, POSTs, deployments, promotion,
R2 or pointer writes, paid resources, or changes to lasting settings. The
per-worker hold guard is not a deployment-wide quota. Private link access,
the four-request runner, and revocation enforce the operational bound.

## What the experiment can establish

The 24-second hold runs after body parsing and bypasses normal admission and the
query engine. A witnessed native cutoff requires a correlated
`w3a_host_cutoff_probe_started` event and provider timeout record for the same
invocation. A normal hold response establishes only that the host allowance
exceeded the completed hold. Inactive guards, uncorrelated 504s, SSO and
network failures are inconclusive. The branch predates production cache and
freshness changes. Timing the hold supplies neither current query response
headroom nor concurrency, disk, memory or overall release acceptance.

## November 27 execution receipt

The authorized diagnostic ref was created at the reviewed SHA. The Git push
produced no preview record. One Git-source build through the connected Vercel
project created `dpl_AZoXaPJtqCbEnePaqFsdnCC2KXgm`. It was READY on the exact
preview ref/SHA in iad1. An unauthenticated request redirected to protection.
The build used Python 3.12 and `uv.lock` and reported that Active CPU billing
ignored the declared memory. The scoped link reported a 600-second expiry
and was revoked without regeneration immediately after the fourth POST.

| POST | HTTP and elapsed | Result |
| --- | --- | --- |
| Natural control | 200, 7.830 s | 31–13 in 44, `req_18c3a4bdbca84539aca740fc40ed7904` |
| Structured control | 200, 6.711 s | 44–11 in 55, `req_9443590b4e8c40c8bf99cc20ed2ad202` |
| Natural hold | 504, 20.271 s | `jtm2d-1795816886282-73d1456e4ed5` |
| Structured hold | 504, 20.239 s | `kn6fb-1795816906498-33ecc432ffce` |

For each hold, Vercel correlated the matching probe-start event with
`Task timed out after 20 seconds` on the same invocation. The start-event
application IDs were `req_e772e0b44b5d4e478a67e334475414f8` and
`req_796741ed40e1418d96f519f13e0c2dae`. These results witness effective
native termination on this diagnostic build. Effective per-function memory
and the current application's hosted response margin are still open.
[Diagnostic deployment](https://vercel.com/zeros-projects-686e97fc/nbatools/AZoXaPJtqCbEnePaqFsdnCC2KXgm)
