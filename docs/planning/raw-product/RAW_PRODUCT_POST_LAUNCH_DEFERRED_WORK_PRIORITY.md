# Raw Product Post-Launch Deferred Work Priority

## 1. Purpose

This document preserves the current ranking of remaining Raw Product post-launch
and deferred notes after the post-review hardening closure refresh.

The goal is to keep the project from losing track of known non-blocking risks.
None of these items is currently classified as a launch blocker. The current
release status remains:

```text
RELEASE_CANDIDATE_WITH_NOTES
PREVIEW_READY_WITH_NOTES
FEEDBACK_READY_WITH_NOTES
PUBLIC_UI_READY_WITH_NOTES
```

Use this document when deciding what to address after launch/handoff, or before
starting major new feature expansion.

## 2. Priority ranking

| Rank | Item | Priority | Suggested timing |
|---|---|---|---|
| 1 | `natural_query.py` extraction / parser maintainability | Highest | Before major new query-family expansion |
| 2 | Visual QA corpus coverage follow-up | High | After fresh gap analysis when public UI risk shifts |
| 3 | Screenshot diffing / baseline / CI decision | Medium-high | After validated local artifact capture |
| 4 | `ReviewPage.tsx` exhaustive-deps lint warning | Medium | Small cleanup pass soon |
| 5 | Vite large-chunk warning / bundle analysis | Medium-low | After launch or when performance becomes a real concern |
| 6 | Return-package archive sweep | Low-medium | After launch/handoff, as repo hygiene |
| 7 | Admin dashboard / mutable feedback triage overlay | Low now; higher later if feedback volume grows | Only after export/spreadsheet workflow becomes painful |
| 8 | Branding / name change | Lowest | Later, once user base and product identity are clearer |

## 3. Detailed notes

### 3.1 `natural_query.py` extraction / parser maintainability

This is the highest-priority deferred item because the parser/routing layer is
the biggest long-term maintainability risk. The risk is not that the current
release is broken. The risk is that future feature growth can introduce
wrong-route behavior if parsing/routing rules keep accumulating in one large
module without controlled extraction and collision discipline.

Why it matters:

- Wrong-route bugs are worse than clean no-result responses because they can
  look like valid answers while answering a different question.
- Future feature additions may add overlapping phrase rules.
- The parser/routing growth guardrails now exist, but the large natural-query
  module still needs gradual structural cleanup over time.

Recommended next step:

```text
Run a natural_query.py extraction preflight.
```

The preflight should identify safe extraction targets, not begin a rewrite.
Likely first extraction candidates:

- stat aliases / constants
- date parsing helpers
- duplicated player/team aliases, if any
- unsupported-boundary definitions
- route-family helper functions
- note/caveat construction helpers

Do not do a one-pass parser rewrite. The correct approach is incremental,
well-tested extraction.

### 3.2 Visual QA corpus coverage follow-up

The first post-review corpus expansion is complete. The runtime corpus now has
20 cases, the expanded local manual baseline passed, and the canonical
non-diffing artifact run passed for that 20-case set.

Future coverage follow-up remains high priority when fresh gap analysis shows
that public-mode UI risk has shifted beyond the current corpus.

Why it matters:

- Public UI regressions are easy to miss without representative visual cases.
- Mobile layout is especially important after the answer-first and context-chip
  changes.
- Manual review and artifact capture are only useful if selected cases still
  represent the real UI risk surface.

The completed expansion added these coverage points:

- `jokic_season_summary`
- `jokic_triple_double_finder`
- `jokic_home_away_split`
- `curry_3_threes_streak`
- `jokic_best_5_rebounding_stretch`
- optional follow-up candidate: `lakers_playoff_history`

Recommended next step:

```text
Run fresh visual QA gap analysis before adding another corpus expansion wave.
```

### 3.3 Screenshot artifact follow-up

The first screenshot automation step is complete. Playwright-backed
non-diffing artifact capture is implemented and locally validated for the
expanded 20-case Visual QA corpus.

Canonical validation evidence:

- Run ID: `visual_qa_20_case_baseline`.
- Command:
  `make visual-qa-screenshots VISUAL_QA_BASE_URL=http://127.0.0.1:8000 VISUAL_QA_RUN_ID=visual_qa_20_case_baseline`.
- `desktop_1280` and `mobile_390` each captured 20/20 cases with request
  errors 0, statuses `ok: 15`, `no_result: 5`, `error: 0`, and document/body
  overflow `false`.
- The manifest lists 20 desktop card screenshots and 20 mobile card
  screenshots; expected PNG total is 42 including the two page captures.

The deferred question is whether artifact capture should grow into screenshot
diffing, committed PNG baselines, or a CI gate.

Why it matters:

- Manual visual QA does not scale well.
- The current artifact command makes desktop/mobile evidence repeatable without
  turning live data into a pixel-diff gate.
- Screenshot diffs can catch layout regressions, mobile overflow, clipping, and
  hierarchy changes more consistently if baseline ownership and noise policy
  are defined first.
- This is especially useful for wide tables and mobile result surfaces.

Deferred follow-up sequence:

```text
1. Use the validated non-diffing artifact command for repeatable evidence.
2. Decide whether screenshot diffing or layout assertions are worth the noise.
3. Decide whether committed PNG baselines or a CI gate are justified.
```

Do not add screenshot diffing, committed PNG baselines, or a CI gate without a
baseline update and failure-triage policy.

### 3.4 `ReviewPage.tsx` exhaustive-deps lint warning

This is medium priority. It is currently an existing lint warning on an internal
review/debug surface, not a public product blocker. But warnings create noise,
and noise makes it easier to miss future real warnings.

Recommended approach:

- Fix in a tightly scoped task.
- Do not combine with larger UI or review-page work.
- Preserve existing `/review` behavior and abort-controller semantics.

Recommended timing:

```text
Small cleanup pass soon, after higher-risk planning work is stabilized.
```

### 3.5 Vite large-chunk warning / bundle analysis

This is medium-low priority. It may eventually matter for load performance, but
it is not currently a correctness issue and the production build succeeds.

Recommended approach:

- Start with bundle analysis, not blind code-splitting.
- Identify what is driving the large chunk.
- Decide whether lazy loading or chunk splitting is worth the complexity.

Recommended timing:

```text
After launch, or when real performance complaints/metrics justify it.
```

### 3.6 Return-package archive sweep

This is low-medium priority. It affects repo cleanliness and agent navigation,
not product behavior.

Why it matters:

- Return packages are evidence/handoff artifacts, not durable source-of-truth
  docs.
- Leaving every completed return package in active-looking locations creates
  visual noise.
- Wave 4 already documented the taxonomy and archive rule; the actual archive
  sweep remains a separate scoped pass.

Recommended approach:

- Do one explicit archive pass.
- Move completed packages according to the documented taxonomy.
- Do not edit package content during the sweep.
- Do not delete anything automatically.

Recommended timing:

```text
After launch/handoff, as repo hygiene.
```

### 3.7 Admin dashboard / mutable feedback triage overlay

This is low priority for now, but it may become high priority if feedback volume
grows.

Current state:

- Feedback collection exists.
- Feedback export/review workflow exists.
- Weekly beta review cadence exists.
- `triage_decisions_template.csv` is enough for early usage.

Why not now:

- An admin dashboard adds auth, UI, state mutation, and workflow complexity.
- A mutable triage overlay is only worth building once the export/spreadsheet
  workflow becomes painful.

Rule:

```text
Do not build an admin dashboard before the export/review workflow proves painful.
```

Recommended timing:

```text
Revisit only after real feedback volume justifies it.
```

### 3.8 Branding / name change

This is the lowest-priority deferred item.

`NBA Tools` / `nbatools` remains the working name. Naming matters eventually,
but it should not consume time during technical hardening or early launch unless
there is a specific external need.

Recommended timing:

```text
Later, once the product's user base and identity are clearer.
```

## 4. Recommended order of work

Recommended order:

```text
1. natural_query.py extraction preflight
2. visual QA corpus coverage gap analysis
3. screenshot diffing / baseline / CI decision
4. ReviewPage lint warning fix
5. Vite bundle/chunk analysis
6. return-package archive sweep
7. admin dashboard / mutable triage overlay
8. branding/name change
```

## 5. Recommended immediate next task

The recommended next task is a preflight, not a code refactor:

```text
Mode: PREFLIGHT — NATURAL_QUERY.PY EXTRACTION / PARSER MAINTAINABILITY
```

Purpose:

- inspect current `natural_query.py` structure
- identify safe extraction targets
- rank extraction candidates by risk/value
- define test coverage needed before each extraction
- preserve current parser/routing behavior
- avoid a broad rewrite

Expected output:

- a concrete extraction plan
- list of safe first extraction candidates
- stop conditions
- validation strategy
- recommendation for whether to execute a small first extraction wave

## 6. Non-goals

Do not treat this document as permission to start broad work.

Non-goals:

- no one-pass parser rewrite
- no unsupported feature promotion
- no automatic corpus mutation from feedback
- no required query category selector
- no admin dashboard until feedback volume proves need
- no branding/name sprint before product usage clarifies positioning
- no return-package moves outside an explicitly scoped archive sweep

## 7. Current launch implication

None of these items currently blocks launch/handoff.

They are ordered deferred notes. The release remains launch-ready with notes.
The recommended behavior is:

```text
launch/handoff with current notes
then address deferred work in priority order
```
