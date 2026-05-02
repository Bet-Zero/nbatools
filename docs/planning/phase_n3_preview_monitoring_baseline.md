# Phase N3 Preview Monitoring Baseline

> **Status:** Passed on 2026-05-02 against the active Vercel deployment URL.

Deployment target:
`https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app/`

Machine-readable report:
`outputs/deployment_smoke/phase_n3_preview_baseline_2026-05-02.json`

This baseline captures the first full Phase N3 smoke/monitoring run against the
domain-agnostic deployment target that exists before custom-domain purchase.

---

## Command Run

```bash
./.venv/bin/python tools/deployment_smoke.py \
  --base-url https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app \
  --output outputs/deployment_smoke/phase_n3_preview_baseline_2026-05-02.json
```

Result: report `ok: true`, `case_count: 6`, `failure_count: 0`.

---

## Baseline Matrix

| Case | Status | Timing | Cache/result notes |
| --- | --- | ---: | --- |
| `GET /` | `200` | `311.750 ms` | `x-vercel-cache: HIT`; built UI HTML served; fallback shell not detected |
| `GET /health` | `200` | `1307.790 ms` | `x-vercel-cache: MISS`; returned `{"status":"ok","version":"0.7.0"}` |
| `GET /freshness` | `200` | `437.671 ms` | `x-vercel-cache: MISS`; returned `status=stale`, `current_through=2026-04-04`, `season_count=1` |
| `POST /query` `Jokic last 10` | `200` | `8779.374 ms` | `x-vercel-cache: MISS`; returned `route=player_game_summary`, `result_status=ok`, `confidence=0.72` |
| `POST /query` `top 10 scorers 2025-26` | `200` | `7499.919 ms` | `x-vercel-cache: MISS`; returned `route=season_leaders`, `result_status=ok`, `confidence=0.82` |
| `POST /query` `Jokic summary (over 25 points and over 10 rebounds) 2025-26` | `200` | `1206.395 ms` | `x-vercel-cache: MISS`; returned `route=player_game_summary`, `result_status=ok`, `confidence=1.0` |

---

## Freshness Banner Verification

Integrated-browser verification on the first-run page matched the backend
freshness payload exactly:

- Banner region rendered `Data freshness`.
- Button label rendered `Data through 2026-04-04`.
- Status badge rendered `stale`.
- Guidance text rendered `Review data age before sharing results.`
- The live `/freshness` payload reported `status=stale` and
  `current_through=2026-04-04`.

No frontend/backend mismatch was observed in the deployed banner path.

---

## Watch List For The Soak

Two routes crossed the 5-second first-observed watch threshold and should be
tracked during the soak:

1. `POST /query` with `Jokic last 10` — `8779.374 ms`
2. `POST /query` with `top 10 scorers 2025-26` — `7499.919 ms`

These are not failures; they are the highest-latency cases from the baseline.
`GET /health`, `GET /freshness`, and the complex Jokic multi-filter query all
returned in `1.308s` or less on this pass.

---

## Deployment Observations

- Root HTML was a cached static hit while `/health`, `/freshness`, and
  `/query` remained dynamic function misses, which matches the expected Vercel
  deployment shape.
- All smoke cases returned HTTP `200`.
- Every query response reported `current_through=2026-04-04`.
- The deployed UI remains usable before the custom domain exists, so the soak
  can start now.

---

## Deferred Custom-Domain Checks

The following still wait for Phase N4:

1. Custom-domain DNS and HTTPS verification.
2. Deploy-on-main evidence on the custom-domain production deployment.
3. Re-running this same smoke baseline against the custom domain and comparing
   it to the Vercel-URL baseline.