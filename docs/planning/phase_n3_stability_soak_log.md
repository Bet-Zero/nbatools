# Phase N3 Stability Soak Log

> **Status:** In progress. Started on 2026-05-02.

Deployment target for the current soak:
`https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app/`

This soak stays anchored on the active Vercel deployment URL until the custom
domain exists. If the domain is purchased mid-soak, Phase N4 can decide whether
to continue on the Vercel URL, restart on the custom domain, or run both.

---

## Success rule

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

## Daily procedure

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

The soak remains active. Keep appending one flat day entry per check until day
7 closes or an incident forces a reset.

---

## Deferred custom-domain work

The soak intentionally does not block on the missing custom domain. The
following still move to Phase N4 after domain purchase:

1. DNS/HTTPS verification on the custom domain
2. Custom-domain production smoke and deploy-on-main evidence
3. Comparison of custom-domain timings to the Vercel-URL soak baseline