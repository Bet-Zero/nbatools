# NBA Tools Deployment Runbook

This runbook documents the deployment-side services used by NBA Tools.

Current deployment storage target:

- Provider: Cloudflare R2
- Bucket: `nbatools-data`
- S3 endpoint pattern: `https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com`
- S3 region: `auto`

## Environment Variables

Local credentials live in the repo-root `.env` file. That file is gitignored
and must never be committed or logged.

Production credentials will live in Vercel environment variables.

Required variables:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`

For the current deployment bucket, `R2_BUCKET_NAME` is `nbatools-data`.
The deployed runtime uses these credentials only for canonical-data reads, so
its token must be bucket-scoped read-only. Approved publication is an operator
workflow that uses separately controlled write authority; do not give the
deployed query runtime write access merely so an operator command can publish.

Optional query feedback variables:

- `QUERY_FEEDBACK_STORE`
- `QUERY_FEEDBACK_BUCKET_NAME`
- `QUERY_FEEDBACK_PREFIX`
- `QUERY_FEEDBACK_R2_ACCOUNT_ID`
- `QUERY_FEEDBACK_R2_ACCESS_KEY_ID`
- `QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY`
- `QUERY_FEEDBACK_PUBLIC_PERSISTENCE_ENABLED`
- `QUERY_FEEDBACK_LEGAL_BASIS_APPROVED`
- `QUERY_FEEDBACK_PUBLIC_NOTICE_APPROVED`
- `QUERY_FEEDBACK_DELETION_CONTACT`
- `QUERY_FEEDBACK_LIFECYCLE_VERIFIED`
- `NBATOOLS_ADMIN_FEEDBACK_ENABLED`
- `NBATOOLS_ADMIN_TOKEN`

`QUERY_FEEDBACK_STORE=r2` selects the store but does not by itself enable
deployed persistence. Deployed storage fails closed unless all five public
privacy gates above are also satisfied. They are currently unsatisfied: no
approved legal basis/notice or dedicated monitored public deletion channel
exists. Leave them unset and keep deployed feedback disabled. Disabled mode
returns JSON with `ok: true`, `stored: false`, and `disabled: true`; normal query
UX and `/query` responses continue unchanged. Automatic diagnostics are forced
off in all deployments and the public endpoint accepts only explicit
`user_submitted` feedback.

For deployed feedback storage, use `QUERY_FEEDBACK_BUCKET_NAME=nbatools-feedback`
or another dedicated bucket and keep `QUERY_FEEDBACK_PREFIX=query_feedback`.
Set the three `QUERY_FEEDBACK_R2_*` variables to a separate token scoped only to
that feedback bucket. The feedback store fails closed when those variables are
missing or when they alias the canonical-data access-key/secret pair; it never
falls back to `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`.

The May 18, 2026 preview inspection used the canonical data bucket under the
isolated `query_feedback/preview` prefix. That evidence is historical and does
not satisfy the current least-privilege contract. Keep deployed feedback
disabled until a dedicated feedback credential tuple is configured; no
canonical-data credential fallback is accepted.

Set `NBATOOLS_ADMIN_FEEDBACK_ENABLED=true` only when the backend admin feedback
review endpoints should be available. In deployed preview or production
environments, also set `NBATOOLS_ADMIN_TOKEN`; requests to
`/api/admin/feedback/*` must include that value in
`X-NBATools-Admin-Token`. If the endpoints are disabled, they return a disabled
`404` response. The token gates API access only; the frontend never receives R2
credentials.

`/visual-qa` is not a production surface. The dedicated FastAPI/Vercel route
serves it only for local development or an explicitly identified preview
environment and returns `404 internal_route_unavailable` in production or an
ambiguous deployed environment. Do not add a production rewrite to the general
review shell and do not use production for visual-corpus execution.

## Public admission and cost gate

Repository handlers enforce the approved application budgets:

- 4 KiB `/query`; 8 KiB `/structured-query`; 8 KiB `/query-feedback`
- JSON depth 4, 64 aggregate object members, 20 aggregate array elements
- the full 30-season supported range, with requests above 30 rejected
- three shared query execution slots, ten query/structured admissions per
  client/IP per rolling minute, and a 20-second response/platform duration
- 20 newly stored feedback submissions per client/IP per rolling 24 hours;
  idempotent replays do not consume another accepted slot

`429` responses are JSON and include `Retry-After`. The public query client does
not retry them automatically. Feedback retries are user-triggered and reuse one
UUID submission receipt.

The in-process counters above are not a global serverless quota. Before release,
configure equivalent request/rate/concurrency/cost controls at the Vercel edge
and verify them from outside the deployment. The approved project ceiling is the
current fixed plan cost with **$0 permitted metered overage**. If Vercel cannot
enforce that exact ceiling, leave this external gate unresolved and report the
closest enforceable alternatives to the owner; do not select one implicitly.

## Cloudflare R2 Setup

Use this process when recreating the storage setup for a future operator.

1. Sign in to Cloudflare or create a Cloudflare account.
2. Open **Storage & databases > R2** in the Cloudflare dashboard.
3. Create an R2 bucket named `nbatools-data`.
4. In the R2 account details area, create an R2 API token.
5. Choose bucket-scoped object-read permission for the deployed query runtime.
6. Scope the token to the specific `nbatools-data` bucket only.
7. Copy the generated Access Key ID and Secret Access Key immediately.
8. Store the credentials in the operator's password manager.
9. Add the variables listed above to the local `.env` file.
10. Add the same variables to Vercel project environment variables before
    enabling deployed `DATA_SOURCE=r2` reads.

The deployed runtime token should not have account-wide R2 admin or object-write
permissions. It needs only the canonical-data reads used by query execution.
Keep approved publication credentials operator-controlled and outside the
deployed runtime. For an approved publication, inject the operator's
write-scoped `R2_*` values only into that local command process; do not copy
them into Vercel runtime configuration.

For query feedback, create a separate bucket such as `nbatools-feedback` and a
separate R2 token scoped to that bucket when possible. Feedback writes need
object write permission; review/export workflows need list/read permission;
mutable triage overlay review needs list/read/write permission under the
feedback prefix. Do not expose these credentials to the frontend. The browser
submits feedback only through the backend-owned `POST /query-feedback`
endpoint.

Configure that token through `QUERY_FEEDBACK_R2_ACCOUNT_ID`,
`QUERY_FEEDBACK_R2_ACCESS_KEY_ID`, and
`QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY`. Do not copy the canonical-data access key
and secret into those variables.

Feedback records are minimized user reports. Common sensitive patterns are
redacted server-side; full results, accounts, client IP addresses, precise
device fingerprints, and session replay are not retained. Every raw record has
a fixed 90-day expiry and must be covered by a verified provider lifecycle rule
of 90 days or less. Conversion into a QA case, issue, or planning artifact does
not extend raw retention. See
[`query_feedback_privacy.md`](query_feedback_privacy.md). No real lifecycle or
deployed privacy configuration is currently verified.

## Endpoint Construction

Build the S3-compatible endpoint from the account ID:

```text
https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com
```

Jurisdiction-specific buckets require jurisdiction-specific endpoints. The
current `nbatools-data` bucket uses the default endpoint pattern above.

## Read-only legacy comparison

The legacy comparison command never writes:

```bash
nbatools-cli pipeline sync-r2 --dry-run
```

Direct non-dry `pipeline sync-r2` is disabled because sequential canonical-key
writes are not generation-atomic. Use the publication workflow below for any
approved data promotion.

## Generation Publication Before Preview Smoke

Vercel preview/runtime functions use `DATA_SOURCE=r2` and do not include
`data/**` in the function bundle. After adding or changing runtime data, first
complete local validation, choose a new unique generation ID, and obtain the
required approval for remote mutation. Then publish the immutable R2
generation:

```bash
.venv/bin/nbatools-cli pipeline sync-r2 --dry-run
.venv/bin/nbatools-cli pipeline publish-generation \
  --generation-id <unique-release-id> \
  --target r2
```

Publication stages and validates the full snapshot, uploads immutable
`generations/<id>/` objects, verifies size and `nbatools-sha256`, and only then
conditionally switches `metadata/active_generation.json`. A partial upload or
pointer conflict leaves the last-good generation active. Treat failed
publication or missing required generation objects as a deploy blocker.
[Cloudflare documents `If-Match` and `If-None-Match` as supported conditional
operations for S3-compatible `PutObject`](https://developers.cloudflare.com/r2/api/s3/api/);
the publisher uses those preconditions for immutable objects and pointer
compare-and-swap ownership.

For the first migration from legacy canonical R2 keys, publish the currently
trusted snapshot as a baseline generation before making further data changes.
Automated rollback to unmanifested legacy R2 keys is refused; after this
bootstrap, rollback always targets a verified immutable generation.

For opponent-conference support, the required object is:

```text
generations/<active-id>/raw/teams/team_conference_membership.csv
```

Verify it exists in R2 with a read-only head-object check before running
opponent-conference preview smoke:

```bash
.venv/bin/python - <<'PY'
import json

from nbatools.commands.pipeline.sync_r2 import create_r2_client, load_r2_config

config = load_r2_config()
client = create_r2_client(config)
pointer = json.loads(
    client.get_object(
        Bucket=config.bucket_name,
        Key="metadata/active_generation.json",
    )["Body"].read()
)
generation = pointer["generation_id"]
response = client.head_object(
    Bucket=config.bucket_name,
    Key=f"generations/{generation}/raw/teams/team_conference_membership.csv",
)
print(
    response["ContentLength"],
    response.get("LastModified"),
    response.get("Metadata", {}).get("nbatools-sha256"),
)
PY
```

Do not reuse legacy canonical-key evidence as generation proof. Capture the
current generation-prefixed length, modification time, and SHA-256 metadata
after an explicitly approved publication.

## Vercel Frontend Build

Phase N2 deploys the React UI by running the frontend build during Vercel's
project build:

```bash
npm --prefix frontend ci && npm --prefix frontend run build
```

The generated Vite bundle lands in `src/nbatools/ui/dist/`, which is also the
configured Vercel static output directory. The Python UI functions can serve
that same bundle for local production-like runs and fallback function paths.
The `frontend/` source directory remains excluded from runtime function
bundles; only the generated `ui/dist` output is needed at runtime. If the
bundle is unavailable locally, the root route intentionally falls back to the
API-only "UI bundle not built" shell.

## Deployment Smoke Monitoring

Phase N3 adds a reusable smoke-report tool for deployed URLs. It is designed to
work against either the current Vercel `*.vercel.app` deployment or the future
custom domain by changing only the supplied base URL.

Run it like this:

```bash
./.venv/bin/python tools/deployment_smoke.py \
    --base-url https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app \
    --output outputs/deployment_smoke/preview.json
```

The JSON report records:

- `GET /`
- `GET /health`
- `GET /freshness`
- `GET /readiness`, which must return HTTP `200`, `ready=true`, and
  `status=ready`
- `POST /query` for the canonical N3 smoke queries
- `POST /query` for `Celtics record against the East this season`, including
  the R2-backed `team_conference_membership.csv` data-path check that expects
  `team_record` / `ok` and 15 resolved East teams

Each case captures status, latency, selected deployment headers, a short body
preview, and a compact payload summary so Phase N3 and the later custom-domain
wrap-up can compare like-for-like evidence.

`/health` remains a cheap liveness check and `/freshness` remains descriptive.
Neither substitutes for `/readiness`. The default deployment smoke fails before
release acceptance when readiness returns `503`, reports any blocker, or cannot
prove an immutable active generation.

### Readiness exception record

Only the named release owner, **John Matthew, project owner**, may authorize a
temporary active-season lag exception. Set all three values together:

```text
NBATOOLS_READINESS_EXCEPTION_REASON=<specific reason>
NBATOOLS_READINESS_EXCEPTION_CREATED_AT=<ISO-8601 UTC timestamp>
NBATOOLS_READINESS_EXCEPTION_EXPIRES_AT=<ISO-8601 UTC timestamp>
```

The expiry must be no more than 24 hours after creation. The application ignores
partial, malformed, future-dated, expired, or overlong records. The exception
can remove only the `active_season_lag` blocker; it cannot make failed/unknown
coverage, an untrusted playoff slice, a failed refresh, or mutable/legacy data
ready. Remove the three variables after the next successful coherent refresh or
at expiry, whichever comes first.

If the opponent-conference smoke case returns `no_data`, lacks
`metadata.opponent_team_abbrs`, or resolves fewer than 15 East teams, stop the
deploy and verify the R2 object above before treating the preview as ready.

## Data-backed Feature Promotion Checklist

This is the deployment-side gate referenced by
[`docs/operations/feature_promotion_rules.md`](feature_promotion_rules.md)
§3.8. Any data-backed feature promotion must satisfy every rule below before
it is treated as shipped. The rules exist because the project is
data-dependent and the deployed runtime reads from R2: a feature can pass
locally while failing in preview or production if a required R2 object is
missing.

The companion product-level policy lives in
[`docs/operations/feature_promotion_rules.md`](feature_promotion_rules.md);
the parser/routing half lives in
[`docs/operations/parser_routing_growth_guardrails.md`](parser_routing_growth_guardrails.md).
This section is the deployment half of the same contract.

Promotion evidence belongs in the active task's tracked working materials and
handoff receipt while the task is open. Follow
[`docs/operations/working_and_archive_policy.md`](working_and_archive_policy.md):
use the active task workspace only while work is active, promote durable facts
back into `docs`, then move completed task materials to the ignored historical
archive. The top-level `return_packages` directory is legacy ignored migration
protection only; do not use it for new deployment or promotion work.

Working principle:

```text
No data-backed feature is promoted until:
  1. the local data contract exists
  2. required R2 object keys are documented
  3. a validated immutable generation is published to R2
  4. deployment smoke checks the feature against preview/prod data access
  5. missing data returns clean no_data/unsupported behavior, not broad fallback
```

### 1. Required runtime data key list rule

Every data-backed feature promotion must list every R2 object key the
deployed runtime needs for the feature to answer correctly.

- The list lives in the promotion's per-feature contract (see
  [`feature_promotion_rules.md`](feature_promotion_rules.md)
  §4) and is reproduced in the task-scoped active-work handoff receipt while the
  task is active.
- Keys are written as full generation-relative paths
  (`raw/teams/team_conference_membership.csv`) and evidence records the active
  generation prefix, not a legacy canonical key, glob pattern, or shorthand.
- "No new R2 objects required" is a valid list entry and must be stated
  explicitly when true. Implicit "nothing changed" is not acceptable.
- If the feature depends on existing keys, those keys are still listed so
  the smoke step has a complete set to assert against.

### 2. R2 generation verification rule (head_object evidence)

Every key listed under rule 1 must be confirmed present in R2 before the
feature's deployment smoke is run.

- Run `nbatools-cli pipeline sync-r2 --dry-run` only for legacy comparison.
  After explicit remote-publication approval, use
  `pipeline publish-generation --generation-id <unique-id> --target r2`.
- For each required key, capture `head_object` evidence and record it in
  the task-scoped active-work handoff receipt: `Bucket`, generation-prefixed
  `Key`, `ContentLength`, `LastModified`, and the `nbatools-sha256` metadata
  value. Also record the active pointer generation and generation-manifest
  checksum.
- A missing or unreachable key is a deploy blocker. Do not proceed to the
  deployment smoke step until every required key returns a clean
  `head_object` response.
- The `head_object` check is read-only and must use the same credentials
  the deployed runtime will use, not a more privileged account-wide token.

### 3. Deployment smoke rule (pointed at the feature)

Every data-backed feature promotion must add at least one deployment smoke
case that exercises the feature against the deployed runtime.

- The smoke case lives in `tools/deployment_smoke.py` (see
  [Deployment Smoke Monitoring](#deployment-smoke-monitoring) above) and
  runs against the preview or production base URL via `--base-url`.
- The smoke case must assert the expected route, the expected result shape,
  and any feature-specific evidence (e.g. resolved entity counts,
  metadata keys, scope filters present in the payload).
- The smoke report is captured in `outputs/deployment_smoke/` and
  referenced from the task-scoped active-work handoff receipt.
- The smoke step runs after R2 generation verification (rule 2) and before the
  feature is treated as shipped. A smoke pass without rule-2 evidence is
  not sufficient: a transient R2 cache hit can hide a missing object.

### 4. Missing-data clean no_data / unsupported behavior rule

When a required R2 object is absent, when the feature's scope is outside
the data's coverage, or when the data is otherwise unavailable, the
deployed runtime must return a clean unsupported shape — never a broader
answer.

- Acceptable shapes at the boundary: `no_data`, `filter_not_supported`,
  `conference_coverage`, or a route-specific guided unsupported response.
- The exact expected shape for the feature is fixed by the promotion's
  per-feature contract (see
  [`feature_promotion_rules.md`](feature_promotion_rules.md)
  §4 "expected unsupported behavior").
- A smoke case must explicitly pin the missing-data behavior whenever the
  feature has a realistic missing-data path. For
  `raw/teams/team_conference_membership.csv`, the existing smoke already
  checks that opponent-conference queries return `no_data` /
  `conference_coverage` when the file is unreachable.
- A passing smoke that only covers the happy path is not enough when the
  feature has a non-trivial missing-data boundary.

### 5. No broad fallback rule

This rule is restated here as a hard deployment-side guardrail because it
is the rule most likely to be quietly relaxed by an "answer something"
reflex.

```text
No broad fallback answers for unsupported or low-confidence queries.
```

Concrete deployment-side applications:

- If a required R2 object is missing, do not widen the answer to the
  nearest larger scope (e.g. unfiltered season record) and ship it. Return
  the clean unsupported shape and treat the deploy as blocked until rule 2
  passes.
- If the feature's scope is outside the data's coverage, do not silently
  collapse the scope filter and answer the broader question. Return
  `conference_coverage` (or the feature's documented unsupported shape).
- A broad-fallback answer that smoke-passes is a worse outcome than a
  clean unsupported response that smoke-fails, because it is harder to
  detect later. Prefer the visible failure.

### 6. Worked example — `raw/teams/team_conference_membership.csv`

The opponent-conference team-record promotion is the canonical worked
example for this checklist. It is also the worked example for the parser
and product-level halves of the contract (see
[`feature_promotion_rules.md`](feature_promotion_rules.md)
§5).

#### 6.1 Required runtime data key list

```text
raw/teams/team_conference_membership.csv
```

That is the only new R2 object the opponent-conference filter requires.
All other inputs (team metadata, season game logs) already shipped under
existing keys.

#### 6.2 R2 generation verification (head_object evidence)

Use the head-object snippet from
[Generation Publication Before Preview Smoke](#generation-publication-before-preview-smoke)
above. Capture evidence for the currently active immutable generation:

```text
Bucket=nbatools-data
ActiveGeneration=<generation-id>
GenerationManifestSha256=<sha256>
Key=generations/<generation-id>/raw/teams/team_conference_membership.csv
ContentLength=<bytes>
LastModified=<timestamp>
nbatools-sha256=<sha256>
```

Any new opponent-conference promotion (new season, new mapping) must
re-capture this evidence in its task-scoped active-work handoff receipt.

#### 6.3 Deployment smoke (pointed at the feature)

Run the deployment smoke tool against the target base URL:

```bash
./.venv/bin/python tools/deployment_smoke.py \
    --base-url https://<deployment-host> \
    --output outputs/deployment_smoke/<label>.json
```

The smoke report must show the opponent-conference case (e.g. `Celtics
record against the East this season`) returning `team_record` / `ok`,
including `metadata.opponent_team_abbrs` and 15 resolved East teams. See
[Deployment Smoke Monitoring](#deployment-smoke-monitoring) above for the
full case set.

#### 6.4 Missing-data clean unsupported behavior

If `raw/teams/team_conference_membership.csv` is missing or unreachable,
the deployed runtime must return `no_data` for the opponent-conference
case. If a season outside the trusted-coverage window is requested, the
runtime must return `conference_coverage`. Neither path may degrade into a
plain unfiltered `team_record` answer.

#### 6.5 No broad fallback

For the opponent-conference family specifically, a broad fallback would
look like a plain team-record answer without an `opponent_conference`
filter applied. That is the exact wrong-route shape this checklist exists
to prevent. The smoke case asserts the filter is present in the payload;
the missing-data path asserts the clean unsupported shape; neither is
allowed to silently widen the scope.

### How this checklist is used

- When a contributor proposes a data-backed feature promotion, this
  checklist is the deployment-side bar that proposal must clear.
- When a reviewer evaluates a promotion, rules 1–5 are the minimum
  deployment-side review surface.
- When the promotion's task-scoped active-work handoff receipt is written, it
  must include the required-key list (rule 1), `head_object` evidence (rule
  2), and a reference to the deployment smoke report (rule 3); when
  applicable, it must also include the missing-data smoke evidence (rule 4).
- When a future promotion changes which R2 objects the feature needs, the
  list is re-asserted and the `head_object` evidence is re-captured. A
  promotion that reuses old evidence is not adequately gated.

## Custom-Domain Closure Checklist

Use this durable checklist for the remaining production-domain work:

- choose or purchase the final domain
- attach the domain in Vercel and copy the exact DNS records Vercel requires
- verify DNS, HTTPS, and R2-backed production readiness
- capture the deploy-on-main evidence record
- run the post-cutover custom-domain smoke pass

Record task-local DNS values, provider screenshots, and smoke notes with the
active task materials. Promote any long-lived operational changes back into
this runbook after cutover.
