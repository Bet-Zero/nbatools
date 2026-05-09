# Result Display Lock-In — Preflight Prompt

> Mode: PREFLIGHT ONLY
>
> Goal: inspect the current result-display implementation and map exact code files/functions to `docs/planning/result-display-lock-in/result_display_lock_in_implementation_spec.md`.
>
> This prompt is intended for a repo-access agent. It must not implement code changes.

---

## Agent instructions

You are working in the `Bet-Zero/nbatools` repo.

This is a discovery-only preflight for the result display lock-in effort.

Read this source spec first:

```txt
docs/planning/result-display-lock-in/result_display_lock_in_implementation_spec.md
```

Also read these source decision logs if needed for detail:

```txt
docs/planning/result_display_family_review_lock_in.md
docs/planning/result_display_family_review_lock_in_batch_6_addendum.md
```

Do **not** change implementation code.

Do **not** refactor.

Do **not** attempt to fix UI.

Do **not** update snapshots/screenshots unless explicitly required for documentation evidence.

The only allowed repo changes are documentation outputs requested in this prompt.

---

## Required output files

Create this return package:

```txt
return_packages/result_display/RESULT_DISPLAY_PREFLIGHT_RETURN_PACKAGE.md
```

Create or update this planning doc:

```txt
docs/planning/result-display-lock-in/result_display_preflight_findings.md
```

Both files may contain the same core findings, but the return package should be formatted as the paste-back artifact.

---

## What to inspect

Map the current implementation for these areas:

### 1. Result renderer and pattern routing

Find and document:

- the main result renderer entry point
- route/pattern mapping files
- how routes map to display patterns
- whether all 19 reviewed families map to shared patterns or route-specific components
- any legacy route-specific components still in use

Expected likely areas, verify before relying on them:

```txt
frontend/src/components/results/ResultRenderer.tsx
frontend/src/components/results/config/routeToPattern.ts
frontend/src/components/results/patterns/
frontend/src/components/ResultSections.tsx
```

### 2. Hero sentence builders

Find and document where hero/sentence text is generated for:

- entity summaries
- player/team game logs
- leaderboards
- comparisons
- records
- playoff history
- no-result states
- streaks
- rolling stretches
- top performances

For each, note:

- file path
- function/component name
- whether copy is generic or route-specific
- whether it has access to query filters/context
- whether it can distinguish query intent, e.g. `against playoff teams` vs `in playoffs`, `which players` vs `best windows`

### 3. Context vs caveat rendering

Find and document:

- where caveats are rendered
- where query context/interpreted filters are rendered
- how the response data distinguishes caveats from context today
- whether normal context is currently being pushed into caveat display
- lowest-risk place to separate Context / Interpreted as / Caveat

### 4. Raw/detail toggles

Find and document:

- where raw/detail toggles are rendered
- how detail sections are detected
- whether the renderer can determine if a detail table duplicates the visible answer table
- how labels like `Show raw table`, `Game Detail`, `Player Game Detail`, `Season Breakdown Detail`, etc. are built
- lowest-risk place to suppress duplicate toggles or rename them to `Show additional columns`

### 5. Table primitives and column configuration

Find and document:

- shared table components/primitives
- column config/preset locations
- how widths/min-widths are controlled
- how horizontal scrolling is handled
- where metric highlighting is applied
- where footer rows are generated
- whether player/team game-log columns can be configured separately
- whether leaderboard-ish families share one table system or multiple systems

### 6. Row limits / show-all behavior

Find and document:

- whether answer tables currently support row caps
- where a `Show all {N}` affordance could be added
- whether parser review pages can intentionally show all rows while product UI caps rows
- how renderer knows whether it is in parser/debug review vs product UI

### 7. No-result behavior

Find and document:

- where Message No Result and Guided No Result are rendered
- how unsupported vs valid-empty states are detected
- where no-result copy is generated
- whether suggestion chips are static or generated from query context
- how to implement contextual suggestions without overreaching

### 8. Comparison logic

Find and document:

- where comparison panels/tables are rendered
- where metric rows are selected
- where edge/difference text is generated
- whether metric direction metadata exists
- where to add higher/lower/neutral metric direction metadata
- whether show-more metric groups exist today

### 9. Playoff-specific renderers

Find and document:

- where playoff history, playoff round records, and playoff matchup history are rendered
- whether round/result labels are mapped centrally
- whether the renderer can derive `Winner` / `Series Result`
- whether the renderer can show both game record and series record when available
- how unavailable round data is represented today

### 10. Rolling stretch deduplication

Find and document:

- where rolling stretch leaderboard rows are produced or rendered
- whether deduplication should happen backend-side, frontend-side, or in response shaping
- whether response metadata can distinguish:
  - `which players`
  - `best stretches/windows`
  - named-player windows
- lowest-risk fallback if metadata is missing

### 11. Fixture/test/screenshot workflow

Find and document:

- where the 19 family fixtures/examples are defined
- how to run the query output fixture set
- how screenshots were generated, if scripts exist
- how to regenerate only targeted fixture outputs
- commands/tests relevant to result display validation
- any existing snapshot/visual-review harness

Minimum targeted fixture IDs from the spec:

```txt
1, 11, 14, 31, 36, 44, 45, 51, 71, 76, 201, 229, 234, 236, 237, 238, 239, 247
```

If any fixture IDs are missing or no longer match, document that clearly.

---

## Required evidence format

For every important claim, include evidence with:

```txt
file path
symbol/function/component name when available
line range when practical
brief explanation
```

Example:

```txt
frontend/src/components/results/patterns/LeaderboardResult.tsx
- `LeaderboardResult` renders the ranked table and currently receives `highlightMetric`.
- Evidence: lines 42–118.
```

Do not make unsupported claims. If evidence is missing, say so.

---

## Required return package structure

Write `return_packages/result_display/RESULT_DISPLAY_PREFLIGHT_RETURN_PACKAGE.md` with this structure:

```md
# Result Display Lock-In Preflight Return Package

## 1. Executive summary

- Overall readiness:
- Biggest implementation risk:
- Best first implementation wave:
- Any blockers:

## 2. Files inspected

| Area | Files inspected | Notes |
|---|---|---|

## 3. Current architecture map

Describe the current result rendering architecture.

## 4. Family-to-code map

| Family # | Family name | Current route/pattern | Current component(s) | Implementation notes | Risk |
|---:|---|---|---|---|---|

Include all 19 families.

## 5. Cross-cutting implementation map

### Context vs caveats
### Raw/detail toggles
### Shared table sizing
### Metric highlighting
### Row caps/show-all
### Footer rows
### No-result behavior
### Comparison edge metadata
### Playoff labels/results
### Rolling stretch dedupe

For each section include:

- current location(s)
- proposed implementation location(s)
- evidence
- risk

## 6. Fixture and validation map

| Fixture ID | Query/family | How to run/check | Notes |
|---:|---|---|---|

## 7. Recommended implementation waves

Update the wave plan from the spec using actual repo evidence.

## 8. Open questions / blockers

List only questions that genuinely block implementation or need user/product decision.

## 9. Suggested first execution prompt scope

Recommend the smallest high-leverage first implementation wave.
```

Also write `docs/planning/result-display-lock-in/result_display_preflight_findings.md` with the same findings or a planning-oriented version.

---

## Stop conditions

Stop and report clearly if:

- the implementation spec cannot be found
- the frontend result-display files cannot be found
- the fixture/test harness cannot be located after reasonable search
- the current branch has unresolved conflicts or missing required files
- evidence is too incomplete to write a safe execution prompt

Do not invent paths, components, or commands.

---

## Validation commands

Run only safe discovery/validation commands. Examples:

```bash
git status --short
find docs/planning/result-display-lock-in -maxdepth 2 -type f | sort
find frontend/src/components -maxdepth 4 -type f | sort | grep -E 'results|Result|Leaderboard|GameLog|Comparison|Record|NoResult|Playoff|Streak'
```

If package scripts are inspected, report relevant scripts but do not run expensive full suites unless they are clearly lightweight and necessary.

---

## Final instruction

This is preflight only. The correct output is a high-confidence implementation map, not code changes.
