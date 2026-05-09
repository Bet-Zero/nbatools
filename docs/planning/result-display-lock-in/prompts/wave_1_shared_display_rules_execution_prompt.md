# Result Display Lock-In — Wave 1 Shared Display Rules Execution Prompt

> Mode: EXECUTION
>
> Goal: implement the first shared-display wave from the result display lock-in project.
>
> Scope: cross-cutting frontend display rules only. Do not redesign individual family layouts yet.

---

## Agent instructions

You are working in the `Bet-Zero/nbatools` repo.

Read these docs first:

```txt
docs/planning/result-display-lock-in/result_display_lock_in_implementation_spec.md
docs/planning/result-display-lock-in/result_display_preflight_findings.md
return_packages/result_display/RESULT_DISPLAY_PREFLIGHT_RETURN_PACKAGE.md
```

The preflight found the project is ready to start implementation and recommended a shared-display wave first. This prompt executes that Wave 1.

---

## Wave 1 objective

Implement the shared result-display rules that affect multiple families:

1. Context vs Caveats separation
2. Raw/detail duplicate suppression + better raw/detail labels
3. Shared answer-table width/min-width polish
4. Metric highlight support consolidation where safe
5. Readable date/range formatting where applicable in visible UI
6. Important missing semantic values should not render as unexplained dashes
7. No-result primary copy should avoid developer/backend wording where safe

Do not attempt full family-specific rewrites in this wave.

Do not implement rolling-stretch dedupe in this wave.

Do not rebuild Comparison Panels in this wave.

Do not do the full game-log column expansion in this wave unless it is needed for a shared primitive API.

---

## Source-of-truth decisions for this wave

From the implementation spec:

- Context is normal query interpretation: date range, season range, opponent group, metric, qualified players, aggregation method, matchup pair, filter expansion.
- Caveats are actual limitations: missing data, approximation, unavailable columns, degraded/partial answer, unresolved ambiguity.
- Raw/detail toggles should be hidden if they duplicate the visible answer table.
- If a detail table exposes extra fields but uses the same row set, label it closer to `Show additional columns`, not `Show raw table`.
- Tables should scroll horizontally rather than crush values.
- Identity/date columns need readable minimum widths.
- Numeric columns need consistent minimum widths.
- Queried metric highlight behavior should remain intact.
- Important semantic columns should not show unexplained `—`; use readable fallback labels where the column has semantic importance.
- No-result primary copy should not expose backend column names where a human-readable version is possible.

---

## Preflight evidence anchors

Use the preflight return package for exact lines and symbols, especially:

- `frontend/src/components/ResultEnvelope.tsx`
  - current context chips and `Notes`/`Caveats` rendering
- `frontend/src/components/NoResultDisplay.tsx`
  - no-result profile/copy/suggestions/details
- `frontend/src/components/results/primitives/RawDetailToggle.tsx`
  - hardcoded `Show raw table` / `Hide raw table`
- `frontend/src/components/results/primitives/ResultTable.tsx`
  - shared answer-table primitive
- `frontend/src/components/results/primitives/ResultTable.module.css`
  - horizontal scroll and table cell styles
- Pattern components using raw/detail toggles:
  - `GameLogResult.tsx`
  - `StreakResult.tsx`
  - `ComparisonResult.tsx`
  - `RecordResult.tsx`
  - `PlayoffHistoryResult.tsx`
- No-result routing:
  - `ResultRenderer.tsx`
  - `resultShapes.ts`

---

## Required implementation tasks

### Task 1 — Context vs Caveats display separation

Implement a frontend-safe first pass.

Required behavior:

- Keep true `caveats` visible as caveats.
- Promote/render normal query interpretation separately as `Context` / `Interpreted as` where current metadata supports it.
- Use existing available metadata first, especially `metadata.applied_filters`, route metadata, season/date/range metadata, query metric, and any existing notes that are clearly context.
- Do not invent backend fields.
- Do not silently delete caveats.
- If a string cannot be safely classified as context, leave it as caveat.

Acceptance criteria:

- Applied filters such as opponent quality, thresholds, season/range, and matchup context appear as Context/Filter/Interpreted as rather than Caveats when data is available.
- Actual data limitations still appear as Caveats.
- Parser/review debug data remains allowed in review pages, but product UI should not be made more debuggy.

Recommended implementation approach:

- Prefer helper functions with names like `buildContextItems`, `buildCaveatItems`, or similar.
- Keep logic conservative and testable.

---

### Task 2 — Raw/detail toggle API and duplicate suppression

Update `RawDetailToggle` and pattern usages so duplicate raw/detail tables do not clutter outputs.

Required behavior:

- `RawDetailToggle` should accept custom collapsed/expanded labels.
- Default label can remain compatible, but answer-table-adjacent detail toggles should be able to say `Show additional columns` when appropriate.
- Add pattern-level duplicate suppression where clearly safe.

Minimum required suppressions:

- `GameLogResult`: do not show raw/detail toggle for the same rows already rendered as the main answer table unless extra fields exist.
- `StreakResult`: do not show `Full Streak Detail` if it duplicates the visible streak table without additional fields.
- `RecordResult`: hide duplicate `Record Detail`, `By Season Detail`, or `Matchup Summary Detail` when they duplicate the visible answer table.
- `PlayoffHistoryResult`: hide duplicate `Season Breakdown Detail`, `Series Detail`, or equivalent when visible answer table already covers the same rows/fields.
- `ComparisonResult`: keep detail toggles only when they expose useful additional fields not already shown in compact/metric sections.

Important:

- If it is not easy to prove duplication safely for a given component, do not hide it. Add a helper and document the limitation.
- Do not remove access to genuinely useful hidden sections such as top performers if they are not surfaced elsewhere.

Acceptance criteria:

- Visible result output should no longer show obvious duplicate raw toggles directly beneath equivalent answer tables.
- Raw/detail labels are less debuggy where the content is extra columns rather than raw data.

---

### Task 3 — Shared table width/min-width polish

Improve `ResultTable` and CSS so dense tables remain readable.

Required behavior:

- Add optional column sizing metadata if needed:
  - `minWidth`
  - `width`
  - `nowrap`
  - or a similar low-risk API
- Keep existing callers working.
- Ensure wide answer tables scroll horizontally instead of crushing values.
- Improve readability for identity, date, team/player, and numeric stat columns.

Acceptance criteria:

- Existing table layout does not regress.
- Team/player names and abbreviations should be less likely to truncate awkwardly.
- Numeric stat columns should remain compact but readable.
- No large card/table redesign in this wave.

---

### Task 4 — Important semantic fallback labels

Implement shared or pattern-local helpers for important semantic missing values.

Required behavior:

- For playoff round/result columns, do not render unexplained `—` when the value means unavailable/unknown.
- Use labels such as:
  - `Unavailable`
  - `Unknown`
  - `Not available`
  - `Round unavailable`
- Keep ordinary empty optional numeric fields simple.

Acceptance criteria:

- Playoff history and playoff matchup tables no longer show unexplained dashes in important round/result columns when the underlying meaning is unavailable/unknown.

---

### Task 5 — No-result copy cleanup

Improve no-result copy conservatively.

Required behavior:

- Primary no-result copy should avoid raw backend wording such as `Column 'def_rating' not available` when a human-readable metric label can be generated.
- Keep technical details available in details/debug section if useful.
- Do not overpromise unsupported alternatives.

Good user-facing copy example:

```txt
Defensive rating is not available in the current dataset.
```

Acceptance criteria:

- Existing unsupported/no-match states still render.
- Static fallback suggestions still render.
- Metadata-provided suggested queries still render.
- Hard unsupported and valid-empty distinctions are preserved.

---

## Tests and validation

Run targeted frontend tests if they exist, especially:

```bash
cd frontend && npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts
```

Also run:

```bash
cd frontend && npm run build
```

If those exact test names do not exist or the test runner syntax differs, inspect package scripts and run the closest safe targeted validation. Do not run expensive unrelated suites unless needed.

If possible, visually check or regenerate reviewed outputs for these fixture IDs after the change:

```txt
1, 11, 14, 31, 36, 44, 45, 51, 71, 76, 201, 229, 234, 236, 237, 238, 239, 247
```

If targeted screenshot regeneration is not supported, document the manual check path.

---

## Required documentation updates

Create this return package:

```txt
return_packages/result_display/RESULT_DISPLAY_WAVE_1_RETURN_PACKAGE.md
```

Update or create this planning note:

```txt
docs/planning/result-display-lock-in/result_display_wave_1_findings.md
```

The return package must include:

```md
# Result Display Lock-In Wave 1 Return Package

## 1. Executive summary

- Status:
- What changed:
- What did not change:
- Biggest remaining risk:

## 2. Changed files

| File | Purpose | Notes |
|---|---|---|

## 3. Implemented behaviors

### Context vs caveats
### Raw/detail toggles
### Table sizing
### Semantic missing labels
### No-result copy

For each section, include file evidence and notes.

## 4. Validation

| Command/check | Result | Notes |
|---|---|---|

## 5. Fixture review notes

| Fixture ID | Family | Checked? | Notes |
|---:|---|---|---|

## 6. Deferred work

List anything intentionally left for Waves 2–5.

## 7. Recommended next wave

Recommend whether Wave 2 should proceed as planned or whether Wave 1 needs follow-up.
```

---

## Stop conditions

Stop and report clearly if:

- the implementation spec or preflight return package cannot be found
- the result renderer files cannot be found
- the current branch has unresolved conflicts
- implementing duplicate suppression would require unsafe guessing that could hide useful data
- tests/build cannot run due to missing dependencies or environment issues

Do not make broad unrelated refactors.

Do not modify backend query behavior in this wave unless absolutely necessary for a small no-result copy mapping, and document it if you do.

---

## Definition of done for Wave 1

Wave 1 is complete when:

- shared result-display primitives support the required behavior
- the most obvious duplicate raw/detail toggles are suppressed or relabeled safely
- context vs caveat display is improved using existing metadata
- answer tables are more robust against width/truncation issues
- important semantic missing values have readable labels
- no-result primary copy is more human-readable where safe
- targeted validation/build is run or clearly documented as blocked
- the Wave 1 return package is written
