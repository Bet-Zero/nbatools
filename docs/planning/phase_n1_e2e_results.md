# Phase N1 E2E Results

> **Status:** Passed on 2026-05-02 against the main Vercel preview using
> `DATA_SOURCE=r2`.

Preview URL:
`https://nbatools-git-main-brents-projects-686e97fc.vercel.app/`

The root route returns the expected "UI bundle not built" fallback for Phase
N1. API verification used `/freshness` and `/query`.

---

## Verification Matrix

Local mode and deployed R2 mode were compared for the required item 6 cases.
All deployed requests returned HTTP `200`, all query envelopes returned
`ok: true`, and the selected result values matched local mode.

| Case | Endpoint | Request | First observed | Warm | Result |
| --- | --- | --- | ---: | ---: | --- |
| Freshness | `GET /freshness` | no body | `3.484s` | `0.387s` | matched local `status=stale`, `current_through=2026-04-04` |
| Simple query | `POST /query` | `{"query": "Jokic last 10"}` | `8.010s` | `0.946s` | matched local `player_game_summary` |
| Leaderboard query | `POST /query` | `{"query": "top 10 scorers 2025-26"}` | `8.678s` | `1.163s` | matched local `season_leaders` |
| Complex multi-filter query | `POST /query` | `{"query": "Jokic summary (over 25 points and over 10 rebounds) 2025-26"}` | `1.291s` | `1.534s` | matched local `player_game_summary` |

Warm timing is the immediate repeat after the first observed request. The
complex query's warm repeat was slightly slower than its first observed request,
which is normal network/runtime variance; both calls were successful and well
below the configured `60s` handler cap.

---

## Result Parity

| Query | Route | Local/deployed parity sample |
| --- | --- | --- |
| `Jokic last 10` | `player_game_summary` | Nikola Jokić, `10` games, `9-1`, `24.000` PPG, `13.600` RPG, `12.700` APG, `10` game-log rows |
| `top 10 scorers 2025-26` | `season_leaders` | Top 3: Luka Dončić `LAL` `33.484` PPG, Shai Gilgeous-Alexander `OKC` `31.569` PPG, Anthony Edwards `MIN` `28.917` PPG |
| `Jokic summary (over 25 points and over 10 rebounds) 2025-26` | `player_game_summary` | Nikola Jokić, `24` games, `15-9`, `34.333` PPG, `14.792` RPG, `10.667` APG, `24` game-log rows |

All three query responses reported `current_through=2026-04-04`.

---

## Timeout And Cold-Start Notes

Item 5 flagged the R2-backed `api/query.py` handler because an isolated local
R2 cold-style call took `13.471s`, above Vercel's default `10s` safety bar.
The deployed handler is configured with `maxDuration: 60`.

Observed deployed behavior confirms the mitigation:

- Final passing `/query` matrix completed with first-observed timings from
  `1.291s` to `8.678s`.
- During the post-protection diagnostic run before the final data-source fix,
  a deployed `/query` leaderboard request completed successfully with HTTP
  `200` in `20.986s`, demonstrating that the route was not capped at `10s`.
- No deployed request returned a timeout, auth failure, or handler error after
  Deployment Protection was disabled.

---

## Issues Found During Verification

1. Initial direct access was blocked by Vercel Deployment Protection and
   returned HTTP `401` before the nbatools API ran. The user disabled
   Deployment Protection for this preview.
2. After access was unblocked, player summary/comparison routes returned
   `no_data` in deployed mode while local mode and player finder routes worked.
   Root cause: `player_advanced_metrics.load_team_games_for_seasons()` still
   read `data/raw/team_game_stats/...` directly from the local filesystem. The
   Vercel bundle intentionally excludes `data/**`, so the team-context load
   failed in R2 mode. Fixed by routing that loader through `data_source`
   in PR #179.

The final passing run above was captured after PR #179 was merged and the main
Vercel deployment completed.
