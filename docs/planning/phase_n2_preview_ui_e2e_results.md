# Phase N2 Preview UI E2E Results

> **Status:** Passed on 2026-05-02 against the Phase N2 item 2 Vercel preview.

Preview URL:
`https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app/`

Deployment id observed in the served root HTML:
`dpl_FnyPq5mX5zcRDe3G6PnP3eXqLYyB`

The preview served the generated React/Vite bundle at `/`, not the API-only
fallback shell, and all tested UI workflows used same-origin API calls against
the deployed R2-backed functions.

---

## Workflow Matrix

| Area | Verification | Result |
| --- | --- | --- |
| First-run load | Loaded `/` at `1280x900`; confirmed app shell, starter queries, saved-query empty state, and absence of the "UI bundle not built" fallback | Pass |
| Health indicator | Confirmed header status rendered `API online` with version `v0.7.0` | Pass |
| Freshness display | Confirmed first-run banner rendered `Data through 2026-04-04` with `stale` status | Pass |
| Natural query execution | Ran the three representative N1 queries through the query bar | Pass |
| Summary rendering | `Jokic last 10` and the complex Jokic threshold query rendered `player_game_summary`, player hero stats, game log, full summary, and by-season tables | Pass |
| Leaderboard rendering | `top 10 scorers 2025-26` rendered `season_leaders`, leaderboard cards, and the full leaderboard table | Pass |
| Raw JSON | Opened "Show Raw JSON" and confirmed the response contained `ok: true` and the expected route | Pass |
| Copy link | Clicked "Copy Link" in a browser context with clipboard permission and confirmed copied feedback | Pass |
| Saved queries | Saved `Jokic last 10` as `Jokic recent smoke` with tags and confirmed the saved-query card/actions rendered | Pass |
| Query history | Confirmed the three executed natural queries appeared in session history with route/query-class labels and action buttons | Pass |
| Phone layout | Loaded `/?q=Jokic last 10` at `390x844`; confirmed result rendering and asserted document/body scroll width stayed within viewport width | Pass |

---

## Representative Query Results

| Query | Route | Browser-observed timing | Rendered evidence |
| --- | --- | ---: | --- |
| `Jokic last 10` | `player_game_summary` | `1.222s` | Nikola Jokic player summary, game log, full summary, by-season table |
| `top 10 scorers 2025-26` | `season_leaders` | `1.818s` | Leaderboard headed by Luka Doncic, full leaderboard table |
| `Jokic summary (over 25 points and over 10 rebounds) 2025-26` | `player_game_summary` | `1.506s` | Nikola Jokic filtered summary, game log, full summary, by-season table |

Timings are measured from query submit to the deployed `/query` response in a
single browser session after the item 2 preview was already warm.

---

## Viewport Evidence

- Desktop workflow screenshot:
  `/tmp/nbatools-phase-n2-item3-desktop.png`
- Phone workflow screenshot:
  `/tmp/nbatools-phase-n2-item3-phone.png`

The phone pass used a `390x844` viewport and programmatically asserted:

- `document.documentElement.scrollWidth <= window.innerWidth + 1`
- `document.body.scrollWidth <= window.innerWidth + 1`

No broken layout, overlapping text, or page widening was observed in the
verified phone result path.

---

## Commands Run

```bash
npm run test
```

Result: `13` test files passed, `237` tests passed.

```bash
node .codex_tmp_phase_n2_preview.cjs
```

Result: browser workflow verification passed against the deployed preview.

The browser script was a temporary local verification harness and is not part of
the product codebase.

---

## Issues Found

No item 3 blockers or UI defects were found during this pass.
