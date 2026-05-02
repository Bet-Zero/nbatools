# Phase N4 Domain Cutover Checklist

> **Status:** Ready on 2026-05-02 for Phase N4 item 2.
>
> **Role:** Concrete operator worksheet for the remaining Track B custom-domain
> closure work.

This checklist is written so the domain-dependent N4 items can execute from a
single source of truth instead of reconstructing the cutover procedure after
the domain exists.

---

## Inputs To Fill Before Starting

Record these before item 3 begins:

- Final production domain:
- Registrar / DNS host:
- Hostname plan: apex only, or apex plus `www`
- Vercel project:
- Last successful `nbatools-cli pipeline sync-r2` time:
- Operator running the cutover:

---

## Evidence Artifacts To Populate

Phase N4 should leave behind these concrete artifacts:

1. `docs/planning/phase_n4_domain_cutover_results.md` - custom-domain setup,
   production readiness, and deploy-on-main evidence.
2. `docs/planning/phase_n4_production_smoke_results.md` - browser and API
   smoke results on the custom domain.
3. `outputs/deployment_smoke/phase_n4_<domain>_<YYYY-MM-DD>.json` -
   machine-readable smoke report from `tools/deployment_smoke.py`.

---

## Step-By-Step Operator Order

1. Choose and buy the final production domain.
2. Open the Vercel project and go to **Settings > Domains**.
3. Add the final hostname plan there:
   - add the apex domain if friends should use `https://example.com`
   - add `www` too if you want `https://www.example.com` to resolve or redirect
4. Copy the exact DNS records Vercel shows after adding the domain.
5. Record those values in the worksheet below before editing DNS.
6. Create the matching records at the registrar or DNS host.
7. Wait for Vercel to report the domain as verified and HTTPS as active.
8. Verify basic reachability in a browser:
   - `https://<custom-domain>/`
   - `https://<custom-domain>/health`
   - `https://<custom-domain>/freshness`
9. Confirm production readiness before cutover evidence:
   - Vercel production `DATA_SOURCE` is `r2`
   - R2 credentials are present in production environment variables
   - the latest `nbatools-cli pipeline sync-r2` completed successfully
10. Use the N4 item 3 PR merge as the deploy-on-main evidence event unless a
    later PR is explicitly chosen for that purpose.
11. After the item 3 merge, record the production deployment URL, commit, and
    deployment timestamp in `phase_n4_domain_cutover_results.md`.
12. Run the custom-domain smoke pass for item 4:

```bash
./.venv/bin/python tools/deployment_smoke.py \
  --base-url https://<custom-domain> \
  --output outputs/deployment_smoke/phase_n4_<domain>_<YYYY-MM-DD>.json
```

13. Run the browser checks on the custom domain:
   - first-run load
   - freshness banner
   - `Jokic last 10`
   - `top 10 scorers 2025-26`
   - `Jokic summary (over 25 points and over 10 rebounds) 2025-26`
14. Record smoke results, timings, deployment evidence, and any residual watch
    items in the two N4 result docs.

---

## DNS Worksheet

Fill this from the exact records Vercel shows for the chosen domain.

| Hostname | Record type | Record name | Record value / target | TTL | Verified? |
| --- | --- | --- | --- | --- | --- |
| apex | | | | | |
| www | | | | | |

Notes:

- Use the values Vercel shows for the final chosen domain; do not assume a
  generic A or CNAME target if Vercel provides something else.
- If the DNS host supports ALIAS/ANAME flattening for apex records, record that
  exact choice here as well.

---

## Production Readiness Worksheet

Fill this before item 3 is marked complete.

| Check | Expected state | Observed state | Evidence |
| --- | --- | --- | --- |
| Production `DATA_SOURCE` | `r2` | | |
| R2 credentials present | yes | | |
| Latest `sync-r2` run | successful | | |
| Root UI on custom domain | `200` | | |
| `/health` on custom domain | `200` | | |
| `/freshness` on custom domain | `200` | | |

---

## Deploy-On-Main Evidence Worksheet

Fill this during item 3.

| Field | Value |
| --- | --- |
| PR used for deploy-on-main evidence | |
| Merge commit | |
| Merge time (UTC) | |
| Vercel production deployment URL | |
| Deployment status | |
| Notes | |

---

## Post-Cutover Smoke Notes

Fill this during item 4.

| Check | Result | Timing / note |
| --- | --- | --- |
| `GET /` | | |
| `GET /health` | | |
| `GET /freshness` | | |
| `POST /query` - `Jokic last 10` | | |
| `POST /query` - `top 10 scorers 2025-26` | | |
| `POST /query` - complex Jokic multi-filter | | |

If the custom domain is not ready yet, leave this document in place and resume
from step 1 when the domain purchase and DNS work are complete.
