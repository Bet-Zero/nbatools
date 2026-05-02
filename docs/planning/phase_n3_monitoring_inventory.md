# Phase N3 Monitoring Inventory

> **Status:** Completed on 2026-05-02 for Phase N3 item 1.

This inventory defines the domain-agnostic monitoring and evidence workflow for
Track B Phase N3 while the product still runs on a Vercel `*.vercel.app` URL.
Custom-domain-only checks remain deferred to Phase N4 wrap-up.

---

## Deployment target rule

- Use the active deployed Vercel URL until the developer purchases or chooses
  the production domain from Phase N2 item 4.
- As of 2026-05-02, the verified deployed UI target is:
  `https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app/`
- The N3 harness must accept a supplied base URL so the same workflow can be
  re-run later against the custom domain without code changes.

---

## Current deployed surface

The active deployed URL is already sufficient for N3's domain-agnostic work:

- `GET /` returns the built React/Vite UI, not the fallback shell.
- `GET /health` returns `{"status":"ok","version":"0.7.0"}`.
- `GET /freshness` returns a structured freshness payload with
  `status=stale`, `current_through=2026-04-04`, and season-level detail.
- `POST /query` is live against the deployed R2-backed functions and returned
  `route=player_game_summary` for `Jokic last 10` during this audit.

Observed response headers from the 2026-05-02 live probe:

| Path | Status | Cache behavior | Useful headers/fields |
| --- | --- | --- | --- |
| `/` | `200` | `x-vercel-cache: HIT` | `server`, `cache-control`, `content-type`, `content-length`, `x-vercel-id` |
| `/health` | `200` | `x-vercel-cache: MISS` | `server`, `cache-control`, `content-type`, `content-length`, `x-vercel-id`, JSON `status`, `version` |
| `/freshness` | `200` | `x-vercel-cache: MISS` | `server`, `cache-control`, `content-type`, `content-length`, `x-vercel-id`, JSON `status`, `current_through`, `checked_at`, `seasons`, `last_refresh_*` |
| `/query` | `200` | `x-vercel-cache: MISS` | `server`, `cache-control`, `content-type`, `content-length`, `x-vercel-id`, JSON `ok`, `route`, `current_through`, `result_status` |

These fields are enough for Phase N3's monitoring baseline and the future
custom-domain rerun.

---

## Freshness-banner operating facts

The shipped frontend freshness surface is already in place; N3 only needs to
verify it against the deployed backend signal.

- `frontend/src/components/FreshnessStatus.tsx` calls `fetchFreshness()` on
  mount.
- The default deployed poll interval is `120_000` ms.
- Banner/panel states come directly from backend freshness values:
  `fresh`, `stale`, `unknown`, `failed`.
- The first-run banner shows `Data freshness`, the `Data through ...` label
  when `current_through` exists, and status-specific guidance text.

Phase N3 item 3 should compare the deployed banner state to the live
`/freshness` payload and record any mismatch explicitly.

---

## Canonical N3 smoke cases

N3 should monitor the same representative deployed cases already exercised in
Phases N1 and N2:

1. `GET /` — verify the deployed UI shell and static asset path.
2. `GET /health` — verify API reachability and version response.
3. `GET /freshness` — verify deployed data-age signal and refresh metadata.
4. `POST /query` with `Jokic last 10` — summary route baseline.
5. `POST /query` with `top 10 scorers 2025-26` — leaderboard route baseline.
6. `POST /query` with `Jokic summary (over 25 points and over 10 rebounds) 2025-26` — complex multi-filter summary baseline.

The smoke harness should record both pass/fail and timing for each case.

---

## Evidence artifacts for N3

N3 should produce and keep three artifacts:

1. A machine-readable smoke report from the new harness in item 2.
2. `phase_n3_preview_monitoring_baseline.md` with the first deployed baseline,
   watch-list routes, and freshness-banner verification.
3. `phase_n3_stability_soak_log.md` with day-0 evidence and the daily soak log.

The JSON report should be reusable for both the current Vercel URL and the
future custom-domain rerun in Phase N4.

---

## What N3 can finish without the custom domain

N3 can complete all of the following before the domain exists:

- Define the monitoring workflow and evidence schema.
- Add and test the reusable deployment smoke harness.
- Record a deployed baseline against the live Vercel URL.
- Verify the deployed freshness banner against `/freshness`.
- Start and maintain the 7-day stability soak log.

None of those require the final custom domain, because the deployed Vercel URL
already exercises the real React bundle, Vercel routing, and R2-backed API.

---

## Domain-gated work deferred to Phase N4

The following checks still require the future production domain and therefore
remain deferred:

1. Adding the custom domain to the Vercel project and configuring DNS.
2. Verifying HTTPS certificate provisioning and clean browser trust on the
   custom domain.
3. Confirming that the custom domain points at the intended production
   deployment.
4. Capturing deploy-on-main evidence specifically for the custom-domain
   production deployment.
5. Re-running the smoke baseline against the custom domain and comparing it to
   the N3 Vercel-URL baseline.

Those items should be made explicit again in `phase_n4_work_queue.md` once N3
reaches its final handoff step.