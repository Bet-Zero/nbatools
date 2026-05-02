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

## Cloudflare R2 Setup

Use this process when recreating the storage setup for a future operator.

1. Sign in to Cloudflare or create a Cloudflare account.
2. Open **Storage & databases > R2** in the Cloudflare dashboard.
3. Create an R2 bucket named `nbatools-data`.
4. In the R2 account details area, create an R2 API token.
5. Choose `Object Read & Write`.
6. Scope the token to the specific `nbatools-data` bucket only.
7. Copy the generated Access Key ID and Secret Access Key immediately.
8. Store the credentials in the operator's password manager.
9. Add the variables listed above to the local `.env` file.
10. Add the same variables to Vercel project environment variables before
    enabling deployed `DATA_SOURCE=r2` reads.

The token should not have account-wide R2 admin permissions. It only needs to
read, write, and list objects in the one deployment bucket.

## Endpoint Construction

Build the S3-compatible endpoint from the account ID:

```text
https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com
```

Jurisdiction-specific buckets require jurisdiction-specific endpoints. The
current `nbatools-data` bucket uses the default endpoint pattern above.

## Verification

Phase N1 verifies the bucket through the real sync path:

```bash
nbatools-cli pipeline sync-r2 --dry-run
nbatools-cli pipeline sync-r2
```

The one-off manual upload/download test from the original setup checklist was
intentionally skipped. The `pipeline sync-r2` command is the production path
and is the meaningful verification.

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
- `POST /query` for the canonical N3 smoke queries

Each case captures status, latency, selected deployment headers, a short body
preview, and a compact payload summary so Phase N3 and the later custom-domain
wrap-up can compare like-for-like evidence.
