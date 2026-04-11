# Data Freshness Plan

This document defines how `nbatools` data should be kept fresh as the repo evolves toward a UI-based NBA search app.

It is an engineering plan, not a product spec. The goal is a repeatable, trustworthy update story that fits the current local-first CSV + pandas architecture and can be tightened before a real UI ever exists.

Related docs:

- [docs/data_catalog.md](data_catalog.md) — what tables exist and where they live
- [docs/data_contracts.md](data_contracts.md) — what query code depends on
- [docs/pipeline_runbook.md](pipeline_runbook.md) — how the pipeline is currently operated
- [docs/roadmap.md](roadmap.md) — Phase 4 (data freshness) and Phase 6 (UI)

---

## 1. Scope and principles

### In scope

- where data comes from
- which datasets need refreshing
- what order raw and derived datasets should be rebuilt in
- how often updates should happen during the season
- how backfills and corrections should work
- what "current through" should mean for user trust
- what should be automated later vs. stay manual now

### Out of scope for this pass

- code changes
- new commands
- new orchestration frameworks
- database migration away from CSV

### Guiding principles

- **Local-first.** Everything runs on disk against CSVs under `data/`. No new infra in this pass.
- **Contracts first.** Refresh jobs must produce the columns required by [docs/data_contracts.md](data_contracts.md). If a pull regresses a required column, that is a freshness bug, not a cosmetic one.
- **Idempotent.** Re-running a refresh for the same season/type should be safe and should not corrupt state.
- **Explicit current-through.** Users should be able to trust a visible statement of how recent the loaded data is.
- **Manual now, automatable later.** Everything in this plan should be runnable by a human today and mechanizable later without a rewrite.

---

## 2. Where the data comes from

All raw data originates from the NBA data source via the existing `pull-*` commands documented in [docs/pipeline_runbook.md](pipeline_runbook.md).

The refresh story uses only commands that already exist:

- raw pulls: `pull-games`, `pull-schedule`, `pull-rosters`, `pull-team-game-stats`, `pull-player-game-stats`, `pull-standings-snapshots`, `pull-team-season-advanced`, `pull-player-season-advanced`
- validation: `validate-raw`
- processed builds: `build-team-game-features`, `build-game-features`, `build-player-game-features`, `build-league-season-stats`
- metadata: `update-manifest`
- orchestration: `backfill-season`, `backfill-range`
- verification: `inventory`, `show-manifest`

Anything not in that list is out of scope for this plan.

---

## 3. Core datasets that must stay fresh

Split by refresh priority, not by directory.

### Tier 1 — directly powers the query surface

These are the datasets query commands read. If any of these are stale, users get stale answers.

- `player_game_stats` — [docs/data_contracts.md](data_contracts.md#1-player_game_stats)
- `team_game_stats` — [docs/data_contracts.md](data_contracts.md#2-team_game_stats)
- `games` (canonical game identity)
- `player_season_advanced`
- `team_season_advanced`
- `rosters` (enrichment for leaderboards)

### Tier 2 — derived features consumed or planned to be consumed

Processed tables that depend on Tier 1 and must be rebuilt after Tier 1 changes.

- `team_game_features`
- `game_features`
- `player_game_features`
- `league_season_stats`

### Tier 3 — context and calendar

Lower refresh urgency, but still needs to track the active season.

- `schedule`
- `standings_snapshots` (regular season only)
- `teams` / `team_history_reference` (rarely changes)

### Metadata

- `backfill_manifest.csv` — must be updated at the end of every refresh so `inventory` and `show-manifest` stay honest.

---

## 4. Rebuild order

Refreshes must follow the same dependency order the pipeline already enforces. Breaking this order will produce derived tables that disagree with raw tables.

1. **Raw pulls**
   1. `pull-games`
   2. `pull-schedule`
   3. `pull-rosters`
   4. `pull-team-game-stats`
   5. `pull-player-game-stats`
   6. `pull-standings-snapshots` (regular season only)
   7. `pull-team-season-advanced`
   8. `pull-player-season-advanced`
2. **Validation** — `validate-raw`
3. **Processed builds**
   1. `build-team-game-features`
   2. `build-game-features`
   3. `build-player-game-features`
   4. `build-league-season-stats`
4. **Metadata** — `update-manifest`
5. **Verification** — `inventory` and `show-manifest`

This is the same order `backfill-season` already runs. For in-season refreshes, the simplest correct approach is to let `backfill-season` do all of this, not to hand-run individual pulls.

---

## 5. In-season refresh cadence

### Daily refresh — baseline

During the regular season, the current season should be refreshed once per day, after all games for the previous day are final.

- Command: `nbatools-cli backfill-season --season <current> --season-type "Regular Season"`
- Then: `nbatools-cli inventory` to confirm alignment
- Expected outcome: all Tier 1 and Tier 2 tables reflect the previous day's completed games.

### Post-game-night refresh

On heavy game nights (e.g. 10+ games), a second refresh should run after the last game of the night is final. This is the same command as the daily refresh.

The reason to run twice is not Tier 1 correctness — it is catching late stat corrections the NBA source sometimes posts hours after the final buzzer.

### Weekly sanity sweep

Once per week during the season:

- re-run the current season with `backfill-season` (no `--skip-existing`) to overwrite any silently drifted rows
- run `inventory` and `show-manifest`
- confirm `raw vs manifest aligned` and `processed vs manifest aligned` are both `True`

### Off-season / dead days

When there are no games scheduled, daily refresh is unnecessary. A weekly run is enough.

### Playoffs

Once `2025-26 Playoffs` data begins to appear, add a parallel refresh for `--season-type "Playoffs"` on the same cadence. Until then, playoff pulls cleanly skip per [docs/pipeline_runbook.md](pipeline_runbook.md#4-playoff-handling).

---

## 6. Full season rebuild

A full rebuild of a single season should be used when:

- a contract column is found to be missing or wrong for that season
- processed outputs are suspected of being stale relative to raw
- a pipeline change affects derivation logic

Procedure:

1. `nbatools-cli backfill-season --season <season> --season-type "Regular Season"` (no `--skip-existing`)
2. If the season has playoffs: repeat with `--season-type "Playoffs"`
3. `nbatools-cli inventory`
4. `nbatools-cli show-manifest`

Rebuilds are expensive on API calls. Do not rebuild a season speculatively — rebuild it because something is wrong or because a pipeline change forces it.

---

## 7. Historical backfill

Historical coverage today is `1996-97` through `2024-25` for both season types, plus `2025-26 Regular Season`. See [docs/data_catalog.md](data_catalog.md#6-coverage-status).

Backfill procedure for a range of seasons not yet on disk:

1. `nbatools-cli backfill-range --start-season <start> --end-season <end> --include-playoffs --skip-existing`
2. `nbatools-cli inventory`
3. Investigate any season that shows as incomplete in `show-manifest`
4. Re-run the specific failing season with `backfill-season` (no `--skip-existing`)

Rules:

- Always use `--skip-existing` for large ranges so completed seasons are not hammered again.
- Never rerun a whole range to fix one broken season — rerun that season directly.
- Transient NBA API timeouts are expected on long runs; the correct response is a targeted retry, not a blanket rerun.

---

## 8. Corrections and re-runs

Two kinds of corrections matter:

### Upstream stat corrections

The NBA source occasionally edits final box scores (fouls, assists, rebounds) after the fact. These typically land within 24–72 hours.

Handling:

- The daily refresh already overwrites Tier 1 rows, so normal corrections flow through without special action.
- The weekly sanity sweep catches slower corrections.
- No manual row editing. Corrections always come via re-pulling the raw source.

### Pipeline-introduced regressions

A local bug in a pull or build step can silently produce wrong data. This is harder to detect.

Handling:

1. Identify the affected season/type and dataset.
2. Rerun `backfill-season` for that season/type with no `--skip-existing`.
3. Run `validate-raw` (runs automatically as part of `backfill-season`).
4. If only a processed table is affected, the cheapest correct fix is still `backfill-season` — it reruns the raw pulls, but it guarantees derived tables match raw tables.

**Do not edit CSV files by hand.** Every row in `data/raw/` and `data/processed/` should be reproducible from `backfill-season`. If it is not, that is itself a bug worth fixing.

---

## 9. "Current through" — what users should be able to trust

For user trust (CLI now, UI later), the repo should be able to answer: *as of what point in time is the loaded data complete and correct?*

Working definition:

> **current through** = the latest `game_date` in `data/raw/games/<current_season>_regular_season.csv` where `is_final = 1`, assuming the most recent refresh succeeded and `backfill_manifest.csv` reports `raw_complete = 1` and `processed_complete = 1` for that season/type.

Properties this definition needs:

- It must be computable from files on disk, not from memory of when a human ran a refresh.
- It must move forward only when both raw and processed layers are complete for the active season/type.
- It must degrade gracefully when the current day has no final games yet (the value should be the last day that did).

For this pass: this stays a documented definition. No code change. A future small utility can surface it in the CLI and later in the UI. Until then, `inventory` + `show-manifest` + a glance at the latest `games` row is the manual approximation.

---

## 10. Minimum viable update workflow

The MVP is intentionally small and human-runnable.

### In-season daily refresh

```
nbatools-cli backfill-season --season <current> --season-type "Regular Season"
nbatools-cli inventory
```

Expected end state: `raw vs manifest aligned = True`, `processed vs manifest aligned = True`, latest `games.game_date` matches yesterday.

### Post-game refresh

Same command as the daily refresh, run after the last game of the night is final. Purpose: catch late stat corrections and complete the night's games.

### Full season rebuild

```
nbatools-cli backfill-season --season <season> --season-type "Regular Season"
nbatools-cli backfill-season --season <season> --season-type "Playoffs"   # if applicable
nbatools-cli inventory
nbatools-cli show-manifest
```

No `--skip-existing`. Used when a contract regression or pipeline change forces a clean rebuild.

### Historical backfill

```
nbatools-cli backfill-range --start-season <start> --end-season <end> --include-playoffs --skip-existing
nbatools-cli inventory
nbatools-cli show-manifest
```

Follow up any incomplete season with a targeted `backfill-season` rerun.

---

## 11. Automate later vs. manual now

### Stay manual in this pass

- Deciding *when* to run a refresh.
- Running daily and post-game refreshes.
- Deciding when a full season rebuild is warranted.
- Deciding when to start refreshing `--season-type "Playoffs"`.
- Investigating `validate-raw` failures.
- Investigating `inventory` misalignment.

Manual is fine because the current user surface is still a CLI used by the maintainer, and the cost of a missed refresh is bounded.

### Automate once the UI exists (or just before)

- Scheduled daily refresh of the current season (regular season, and playoffs when active).
- Scheduled weekly sanity sweep.
- Surfacing "current through" as a first-class field alongside query results.
- Automatic alert when `validate-raw` fails or when `inventory` reports misalignment.
- Automatic rerun of a single failed season on transient API errors, bounded by retry count.

### Never automate

- Hand-editing raw or processed CSVs.
- Blanket full-range rebuilds on a schedule. Backfill ranges should remain a deliberate human action.
- Bypassing `validate-raw` to "unblock" a refresh. A failing validation is the signal, not the obstacle.

---

## 12. How this evolves alongside the UI

This plan is deliberately aligned with the roadmap's Phase 4 (data freshness) and Phase 6 (first UI). See [docs/roadmap.md](roadmap.md).

Before the UI exists:

- The manual workflow in section 10 is enough.
- "current through" stays a documented definition and a manual check.
- Data contracts in [docs/data_contracts.md](data_contracts.md) remain the authority on what must be present after a refresh.

Once the UI is being built:

- "current through" becomes a structured field the engine returns on every query result, so the UI can render a freshness badge.
- The daily and post-game refreshes move behind a scheduler.
- `validate-raw` failures and manifest misalignment become visible in the UI instead of only in the CLI.
- Refresh history (when a refresh last succeeded and through what game date) becomes a first-class piece of state, not an implicit property of the filesystem.

The freshness story is what moves `nbatools` from "a strong local analytics CLI" to "a trustworthy NBA search product." Everything in this doc is sized to be doable now without blocking any of that later work.
