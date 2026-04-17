# natural_query.py Cleanup Plan

> **Status: partially complete (last reviewed 2026-04-16).**
>
> Phase A (safe deduplication) and significant portions of Phase B
> (responsibility cleanup) have been completed in prior cleanup passes.
> Key progress:
>
> - duplicate routing branches in `_finalize_route` removed
> - duplicate `team_streak_finder` branch removed
> - intent detectors extracted for clearer parse → route separation
> - entity resolution consolidated in `entity_resolution.py`
> - structured result layer shipped (all routes return result objects)
> - structured-first execution path is now canonical
>
> Remaining value: Phase C (optional helper-module extraction) if the file
> continues to grow, and any Phase B items not yet addressed.
> See `docs/audits/architecture_hygiene_audit.md` items #3–5 for the next
> concrete extraction targets (leaderboard stat aliases, inline
> player/team aliases, date utilities).

This document lays out the cleanup plan for `src/nbatools/commands/natural_query.py`.

The goal is **not** to rewrite the natural query system from scratch.
The goal is to keep the existing shipped behavior while making the router easier to reason about, extend, and test.

---

## Why this file needs focused cleanup

`natural_query.py` is now one of the most important files in the repo.

It currently handles:

- alias resolution
- stat detection
- season/date extraction
- leaderboard detection
- matchup/head-to-head phrasing
- streak parsing
- threshold extraction
- route selection
- grouped boolean orchestration
- OR-query orchestration
- export-aware execution plumbing

That growth is natural, but it creates risk if structure does not catch up.

The current danger is not that the file exists. The danger is that new features keep landing in it without enough separation of concerns.

---

## Cleanup goals

The cleanup should improve:

- readability
- route determinism
- testability
- duplication control
- future UI/API readiness

It should **not** change behavior casually.

---

## Non-goals

This cleanup is **not** for:

- changing the user-facing query language on its own
- rewriting the entire parser into a new framework
- migrating storage
- rebuilding the command layer
- introducing UI-specific abstractions

The work should be incremental and behavior-preserving unless a bug fix is explicitly intended.

---

## Known cleanup targets

These are the highest-value issues currently visible.

### 1. Duplicate routing / post-processing branches

Known examples include:

- duplicated return logic in `_finalize_route`
- duplicated `team_streak_finder` routing branch
- split-route handling both inside `_finalize_route` and again in `parse_query()`

### 2. Parser helpers and orchestration mixed together

The file currently mixes:

- low-level detection helpers
- route-building logic
- grouped boolean execution
- export-aware execution helpers

These can be separated more cleanly without changing the public behavior.

### 3. `parse_query()` responsibilities are too broad

It is currently sitting on top of helper layers that are not yet cleanly separated into:

- parse state extraction
- route finalization
- special-case overrides

### 4. Grouped boolean and top-level OR execution are bolted into the same file

These are legitimate features, but they are complex enough to deserve clearer boundaries.

### 5. Date, leaderboard, streak, and matchup helpers are now substantial enough to become their own helper modules if growth continues

This does not need to happen immediately, but the file should be cleaned with that likely future split in mind.

---

## Target structure

The long-term shape should look more like this:

### Layer 1: normalization and detection helpers

Responsibilities:

- text normalization
- alias detection
- season/date extraction
- threshold extraction
- split detection
- leaderboard detection
- matchup detection
- streak detection

### Layer 2: parse-state assembly

Responsibilities:

- build the parse-state dictionary from the normalized query
- keep this step purely about interpreted state, not execution

### Layer 3: route finalization

Responsibilities:

- convert parse state into one explicit structured route
- build route kwargs
- avoid duplicate override logic after finalization

### Layer 4: special execution orchestration

Responsibilities:

- grouped boolean execution
- top-level OR execution
- export-aware run plumbing

This should remain downstream of routing, not blended into detection logic.

---

## Recommended cleanup phases

## Phase A — Safe deduplication

Low-risk cleanup with minimal behavior change.

### Tasks

1. remove duplicated return block in `_finalize_route`
2. remove duplicated `team_streak_finder` route branch
3. eliminate duplicate split-route overrides if `_finalize_route` already owns them
4. simplify any obviously dead or unreachable branches
5. tighten comments around non-obvious route behavior

### Goal

Make the file less noisy without changing surface behavior.

---

## Phase B — Responsibility cleanup inside the file

Still within one file, but with clearer boundaries.

### Tasks

1. group helper functions by responsibility
   - normalization / aliases
   - date/time parsing
   - threshold parsing
   - leaderboard detection
   - matchup/head-to-head detection
   - streak detection
2. separate parse-state assembly from route finalization more explicitly
3. make `parse_query()` a thinner wrapper over those layers
4. make grouped boolean and OR execution helpers visually distinct from parsing helpers

### Goal

A reader should be able to understand the file in passes instead of scrolling through a long blended flow.

---

## Phase C — Optional helper-module extraction

Do this only if the file remains too large or unstable after Phases A and B.

### Likely split candidates

- `natural_query_dates.py`
- `natural_query_leaderboards.py`
- `natural_query_streaks.py`
- `natural_query_matchups.py`
- `natural_query_execution.py`

### Rule

Do not split just for aesthetics. Split when it clearly improves maintainability or testability.

---

## Behavior safety rules for cleanup

Any cleanup work on this file should follow these rules:

- preserve current shipped behavior unless the task explicitly includes a bug fix
- add regression tests before removing suspicious branches if behavior is unclear
- do not broaden docs claims as part of cleanup
- do not silently change route precedence without tests
- do not mix cleanup and feature expansion unless the feature depends on it

---

## Test expectations during cleanup

At minimum, cleanup work should keep the following protected:

- parser route tests
- grouped boolean smoke tests
- leaderboard smoke tests
- summary/comparison/split smoke tests
- export tests

If route precedence or helper extraction changes, add explicit regression tests for:

- split route selection
- leaderboard route selection
- head-to-head phrasing
- date-aware parsing
- streak route selection
- grouped boolean routing

---

## Recommended immediate sequence

### Step 1

Do Phase A first.

That means:

- deduplicate obvious route branches
- remove repeated return logic
- make `parse_query()` and `_finalize_route()` ownership cleaner

### Step 2

Run the relevant parser/smoke tests.

### Step 3

Only then decide whether Phase B should remain in one file or start extracting helper modules.

---

## Definition of success

This cleanup is successful if:

- the current shipped behavior still works
- `natural_query.py` is easier to reason about
- route ownership is clearer
- duplication is reduced
- future agents are less likely to pile new logic into the wrong place
- the file is in a better position to support the long-term UI-based product goal

---

## Immediate next implementation target

The next code cleanup pass should focus on:

1. `_finalize_route`
2. `parse_query`
3. grouped boolean / OR execution boundaries

That gives the highest cleanup ROI without turning the task into a risky rewrite.
