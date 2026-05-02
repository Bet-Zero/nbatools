# Phase N3 Stability Soak Log

> **Status:** Closed as skipped on 2026-05-02 after the day-0 baseline.

Deployment target for the current soak:
`https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app/`

This soak was originally anchored on the active Vercel deployment URL until the
custom domain existed. On 2026-05-02, Track B closed the synthetic seven-day
loop as out of scope for a friends-tier release. The retained day-0 baseline
and the reusable smoke harness remain the fallback evidence path if deployed
behavior needs to be checked again before the custom-domain wrap-up.

---

## Skip decision

The seven-day synthetic soak is intentionally skipped.

Reason for the skip:

- Friends-tier scope means real ongoing usage is a better signal than waiting
  through a synthetic daily smoke loop.
- The day-0 baseline already captured a clean deployed reference point.
- `tools/deployment_smoke.py` remains available for targeted follow-up checks
  any time deployment behavior looks suspicious.

This file remains as the closed record of the baseline and the decision to stop
the longer soak procedure.

## Original success rule

The soak is successful when seven consecutive calendar days pass without manual
intervention on the deployed app and the daily smoke checks continue to return
usable results.

Manual intervention means any change made specifically to restore deployed
availability or correct deployed data freshness behavior after the soak starts.
Routine local development that does not repair a live incident does not reset
the soak by itself.

An incident means any of the following:

- Smoke harness failure for `GET /`, `GET /health`, `GET /freshness`, or a
  canonical `/query` case
- Wrong-route or `ok: false` query response for a canonical case
- Deployed freshness banner no longer matching `/freshness`
- Unplanned deployment outage, auth failure, asset failure, or function error

If an incident requires a code/config fix or manual Vercel action, the soak
resets after the repair lands and a new day-0 entry is recorded.

---

## Original daily procedure

Run once per day from the repo root:

```bash
./.venv/bin/python tools/deployment_smoke.py \
  --base-url https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app \
  --output outputs/deployment_smoke/soak-YYYY-MM-DD.json
```

Then update this log with:

1. Date and approximate check time
2. Result (`pass`, `watch`, or `incident`)
3. Any changed timings for the two watch-list queries
4. Freshness status/current-through date
5. Any incident notes or reset decision

---

## Watch list at soak start

Monitor these more closely during the seven-day run:

1. `POST /query` with `Jokic last 10` — baseline `8779.374 ms`
2. `POST /query` with `top 10 scorers 2025-26` — baseline `7499.919 ms`

These exceeded the 5-second first-observed watch threshold during the baseline
but still returned successful results.

---

## Day 0 Entry — 2026-05-02

- Check time: `2026-05-02T06:48:29Z`
- Result: `watch`
- Report: `outputs/deployment_smoke/phase_n3_preview_baseline_2026-05-02.json`
- Root/health/freshness: all passed
- Query smoke: all three canonical queries passed
- Freshness signal: `stale`, `current_through=2026-04-04`
- Freshness banner: matched the backend signal on the deployed first-run page
- Watch items: `Jokic last 10` and `top 10 scorers 2025-26` remained above the
  5-second watch threshold
- Incident: none
- Reset required: no

The synthetic soak does not continue past day 0. If a later targeted check is
needed, run the same smoke command and record the outcome in a new Phase N4
artifact or incident note instead of resuming this daily procedure.

---

## Deferred custom-domain work

The soak intentionally does not block on the missing custom domain. The
following still move to Phase N4 after domain purchase:

1. DNS/HTTPS verification on the custom domain
2. Custom-domain production smoke and deploy-on-main evidence
3. Comparison of custom-domain timings to the Vercel-URL soak baseline