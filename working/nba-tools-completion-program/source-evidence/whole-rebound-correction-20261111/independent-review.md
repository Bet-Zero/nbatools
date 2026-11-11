# Independent review — whole-game rebound correction v7

- Reviewer: separate Claude checker agent, run in an isolated context. It did not author the
  script or tests, and it wrote only to its own scratch directory. Backend model identity is
  not recorded; this is not a human review.
- Reviewed revision: `ea23447686b7ff45eea178e6efcb9976c8b9dda6` against base `cf39739`.
- Verdict: **APPROVE**, with no blocking findings.

## What the checker independently verified
- It extracted page 0 of the scorer PDF `5d11d197…` itself with pypdf. The heading is FINAL
  BOX, and Washington's line `… 4 6 10 3 2 0 1 1 0 21` matches all 16 counts on the v7 row.
- It diffed v6 and v7 file by file. The diff is exactly the raw CSV line 2668 (dreb 5→6,
  reb 9→10), the manifest, and 2 added metadata files. All 38 manifest hashes check out and
  the binding matches. v6 is untouched.
- Season reconciliation: v6 had 245 of 246 team-games matching (game 184 DAL: 31/49 vs
  32/50); v7 matches all 246. The quarter and half sums are 6/10.
- Stored derived values: only `player_game_features.reb_last_5` uses player REB, and it
  reads prior games only. Game 184's value of 7.4 is the mean of the 5 prior games, so it
  correctly does not change.
- It ran unfamiliar wordings against both versions and compared them with pandas over the
  raw rows. All matched:
  - double-double vs Spurs on Nov 4: no / yes
  - Mavericks players with 10+ boards on 2026-11-04: Flagg / Washington and Flagg
  - Dallas rebounding leaders: 7.875 / 8.0, with other players unchanged
  - games with 10+ REB: 2 / 3
  - 10+ REB streaks: game 184 added
  - season REB% from game logs: 12.363 / 12.559
  - box score on Nov 4: 9 / 10
  - games with 6+ DREB: 4 / 5
  - double-doubles: 1 / 2

## Non-blocking findings and disposition
1. Some interpretation gaps already exist on both v6 and v7, and this PR doesn't cause
   them. They stay as follow-ons in the interpretation queue:
   - "defensive rebounds 2026-27 total" returns a game finder instead of the total 47.
   - "most double doubles 2026-27 Mavericks" drops the team filter.
   - "Who led the Mavericks in double-doubles in 2026-27" returns no_result.
2. The README's list of dependent values left out the query-time REB% computed from game
   logs. It is now added to the README.
3. The validation report records absolute scratch paths and `generated_at`, so a re-run gives
   the same data bytes but a different manifest and archive hash. The pinned `binding.json`
   is authoritative. This is the same as the earlier v5/v6 reports.
