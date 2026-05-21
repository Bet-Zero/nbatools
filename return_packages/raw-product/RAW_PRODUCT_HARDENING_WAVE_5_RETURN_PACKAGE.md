# Raw Product Hardening — Wave 5 Return Package

## 1. Executive summary

- Wave executed: Wave 5 — README/Product Positioning Refresh, per
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5.
- What was produced: a top-to-bottom rewrite of `README.md` that re-orders
  the repo entry point to lead with the public answer-first product
  framing instead of the historical CLI/dev-workbench framing, following
  the ordering recommended in
  `RAW_PRODUCT_POST_REVIEW_NOTES.md` §8.
- New ordering: product promise → what you can ask → what is
  intentionally unsupported → web UI quick start → developer surfaces
  (CLI ask / CLI structured query / HTTP API / exports / engine query
  classes / filters / entity resolution / stats) → QA & release status
  pointers → data & deployment notes → setup.
- Files changed: `README.md` only. `docs/index.md` was inspected for the
  "What NBA Tools Currently Supports" list; the README re-framing does
  not contradict it (the README's supported areas are a superset that
  adds **records** and **playoff history**, which the docs/index.md list
  did not previously enumerate). Per the Wave 5 task constraint
  ("Touch `docs/index.md` only if the README reframing creates a
  contradiction with it"), `docs/index.md` was not modified.
- Scope: docs/policy only. No production code, parser, routing, backend,
  frontend, deployment, test, corpus, or behavior changes. No file
  moves, archives, renames, or deletions. No product rebrand or rename
  (`NBA Tools` / `nbatools` retained per POST §10).
- Release status: unchanged. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`. The README quotes this status string
  verbatim and links the existing release-status docs as the source of
  truth.
- Next wave: Wave 6 — Lightweight Product Promise/Homepage Pass
  (frontend homepage/landing + public answer context duplication audit).

## 2. Files changed

| File | Change type | Why |
| --- | --- | --- |
| `README.md` | Rewritten | Re-ordered the top of the repo to lead with the product promise from `RAW_PRODUCT_POST_REVIEW_NOTES.md` §8, added a "What is intentionally unsupported" section, moved the web UI quick start ahead of the CLI/API/structured-query surfaces, and added a "QA and release status" section that links the release package, release-candidate handoff, release-readiness checklist, hardening plan, Wave 1 policy docs, query-feedback runbook, and docs index. All previously accurate example commands and engine-surface claims were preserved verbatim. |
| `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_5_RETURN_PACKAGE.md` | Added return package | Records what changed, files changed, acceptance-criteria check, and validation result for Wave 5. |

No other files were created, modified, moved, or deleted. In
particular:

- `docs/index.md` was not modified — see §3.3 below for the
  no-contradiction check.
- No file under `return_packages/`, `docs/`, `outputs/`, `archive/`, or
  the repo source tree was moved, renamed, archived, or deleted.

## 3. What changed (substantive content)

### 3.1 README.md — new top-down ordering

The README now opens with a product-first framing:

```text
NBA Tools is a natural-language NBA stats answer engine for stat-shaped
questions across players, teams, records, splits, streaks, leaderboards,
comparisons, and playoff history.
```

This is the framing recommended in
`RAW_PRODUCT_POST_REVIEW_NOTES.md` §8. The opening paragraph is followed
by a short answer-behavior paragraph ("Ask a stat-shaped NBA question
in plain English; get a direct, scoped answer backed by verified data.
When a question falls outside the current supported boundary, the
engine returns an explicit unsupported or no-result response instead of
inventing an answer.") and a surface-summary paragraph ("the same query
engine is exposed through three surfaces: a public answer-first web UI,
an HTTP API, and a CLI for development and power-user queries").

The new section ordering is exactly the structure recommended in POST
§8:

1. **Product promise** — opening paragraphs (above).
2. **What you can ask** — eight subsections of stat-shaped families,
   each named verbatim and each with the same accepted-phrasing
   examples the previous README carried (player summaries & recent
   form; team summaries, records & splits; leaderboards; comparisons &
   head-to-head; streaks; date-aware windows; game finders & boolean
   filters; count queries; playoff history). The subsection introduces
   each family using the answer-first phrasing the engine actually
   accepts (no `nbatools-cli ask` prefix in the examples here; those
   examples are presented as the natural-language questions a public UI
   user would type — the CLI form is shown later in the Developer
   surfaces section).
3. **What is intentionally unsupported** — new section. Names the
   product's explicit no-broad-fallback rule and enumerates the major
   guarded families (subjective/opinion/trend queries; inference beyond
   available data and invented metric definitions; query families in
   the promotion pipeline; specific guarded families: personal-foul
   leaderboards, single-team advanced-stat scalar summaries, rookie
   leaderboards, league-wide starter/bench leaderboards, team bench
   scoring, opponent-conference history outside trusted current-era
   coverage, single-team playoff round records, multi-player
   availability, lineup summaries/leaderboards without trusted
   coverage, on/off surfaces without trusted data, team rolling-stretch
   leaderboards, minutes leaderboards, team single-game threes). The
   section links the full table in
   `RAW_PRODUCT_RELEASE_PACKAGE.md` §4 and the
   `PARSER_ROUTING_GROWTH_GUARDRAILS.md` working principle ("Forgive
   phrasing. Do not invent meaning. No broad fallback answers for
   unsupported or low-confidence queries.").
4. **Web UI quick start** — moved ahead of the CLI/API surfaces.
   Names `nbatools-api` as the local command, names `/` as the public
   default with answer-first hero plus scoped context chips plus result
   table plus freshness plus history plus saved queries, and explicitly
   lists the preserved diagnostics surfaces (`/?debug=1`, `/review`,
   `/visual-qa`) so the reader knows debug chrome is **preserved, not
   removed** in the public default. Links
   `docs/operations/ui_guide.md` for frontend dev workflow.
5. **Developer surfaces** — new umbrella section covering, in order:
   CLI natural-language ask; CLI structured query (with the same five
   structured examples and the "26 structured routes" claim preserved
   verbatim); HTTP API (preserved `nbatools-api` + `GET /freshness` and
   linked `docs/architecture/api_layer.md`); exports (preserved
   `--txt`/`--csv`/`--json` examples); engine query classes
   (preserved verbatim); filters and windows (preserved verbatim);
   entity resolution (preserved verbatim, including the "90+ curated
   player aliases" claim); stats and metrics (preserved verbatim).
6. **QA and release status** — new section. Quotes the current release
   status string verbatim
   (`RELEASE_CANDIDATE_WITH_NOTES` /
   `PREVIEW_READY_WITH_NOTES` /
   `FEEDBACK_READY_WITH_NOTES` /
   `PUBLIC_UI_READY_WITH_NOTES`) and links the release package,
   release-candidate handoff, release-readiness checklist, post-review
   hardening plan, Wave 1 policy docs
   (`PARSER_ROUTING_GROWTH_GUARDRAILS.md`,
   `FEATURE_PROMOTION_RULES.md`), the query-feedback review runbook,
   and `docs/index.md`. Preserves the "~1,684 test functions across 42
   test files" tested-state claim verbatim and preserves the
   `make test` / `nbatools-cli test` commands. Preserves the
   `CHANGELOG.md` link.
7. **Data and deployment** — preserves the `nbatools-cli pipeline
   refresh` / `auto-refresh` commands, the pipeline stages list
   (`raw` / `processing` / `ops`), the `GET /freshness` endpoint, and
   the UI freshness panel summary. New "Deployment" subsection names
   the R2 + Vercel runtime, the `data/**` exclusion fact (which is the
   reason the Wave 2 data-backed feature promotion checklist exists),
   and links `docs/operations/deployment.md`. Adds a link to
   `docs/operations/pipeline_runbook.md`.
8. **Setup** — preserved verbatim from the previous README (editable
   install with dev dependencies, frontend install, production build,
   tests, two-terminal hot-reload). Reformatted from a fenced ```bash
   block to indented code to match the rest of the file's code-block
   style and clear the pre-existing `MD046/code-block-style` lint hint.

### 3.2 No production-claim drift

Per the Wave 5 task constraint ("Do not claim support outside the
current verified boundary"), the rewrite was performed by re-ordering
and re-framing existing accurate claims rather than by adding new
capability claims. The following items are quoted/preserved verbatim
from the previous README and remain accurate against the current
release package:

- Surfaces: public answer-first web UI, HTTP API, CLI.
- Engine query classes: finder / count / summary / comparison / split /
  leaderboard / streak / record / playoff (nine classes, verbatim).
- Filters/windows: season, season range, last N seasons, last N games,
  recent form, home/away, wins/losses, opponent/head-to-head, month,
  since month, last 30 days, since All-Star break, career, all-time,
  playoffs, threshold conditions with boolean chaining.
- Entity resolution: 90+ curated player aliases, accent normalization,
  team name/abbreviation/nickname resolution, ambiguity detection.
- Stats and metrics: pts, reb, ast, stl, blk, 3pm, tov, +/−, eFG%, TS%,
  USG%, AST%, REB%.
- "26 structured routes are available" — preserved verbatim.
- Web UI features — public default, `/?debug=1`, `/review`,
  `/visual-qa`, freshness panel, query history, saved queries.
- Pipeline stages — `raw` / `processing` / `ops`.
- Tested state — ~1,684 test functions across 42 test files.

The new "What is intentionally unsupported" section is constructed
entirely from the explicit unsupported-boundary table in
`RAW_PRODUCT_RELEASE_PACKAGE.md` §4; no new families were invented for
this section.

### 3.3 docs/index.md — no contradiction; not modified

The Wave 5 task says to touch `docs/index.md` only if the README
re-framing creates a contradiction with its "What NBA Tools Currently
Supports" list. The current `docs/index.md` list reads:

```text
natural-language NBA queries
structured CLI commands
player and team leaderboards
player and team summaries
player and team comparisons
split summaries
matchup / head-to-head phrasing
month / date-window queries
since All-Star break
player streaks
team streaks
CSV / TXT / JSON exports
```

The new README opens by naming the supported areas as: players, teams,
records, splits, streaks, leaderboards, comparisons, and playoff
history. Compared to the `docs/index.md` list:

- The README adds **records** and **playoff history**. These are not
  contradictions with the docs/index.md list — they are areas the
  docs/index.md list did not enumerate. Both are part of the current
  shipped boundary per `RAW_PRODUCT_RELEASE_PACKAGE.md` §3 (Team
  records / Playoff history / Playoff matchup history / Playoff round /
  appearance leaderboards) and are documented in
  `docs/reference/query_catalog.md` and
  `docs/reference/query_guide.md`.
- The README does not contradict any item in the docs/index.md list.
- The README does not claim any item outside the docs/index.md list
  beyond the two additions above, both of which are accurate against
  the release package.

A superset is not a contradiction, so `docs/index.md` was not modified
in this wave. A later, separately scoped pass may align the
`docs/index.md` list to add `records` and `playoff history` for
completeness; that is out of scope for Wave 5.

### 3.4 No rebrand / rename

The product name `NBA Tools` and the CLI/package name `nbatools` /
`nbatools-cli` / `nbatools-api` are preserved verbatim throughout. The
rewrite is positioning-only, not identity-changing. This matches POST
§10 (naming is explicitly deferred / non-goal) and the Wave 5 stop
condition.

### 3.5 No code/test/corpus/parser/backend/frontend/deployment/behavior changes

None. This wave is docs/policy only. No source file under
`src/nbatools/`, `frontend/`, `tools/`, `tests/`, `data/`, `outputs/`,
`Makefile`, `pyproject.toml`, deployment scripts, or any other
non-documentation surface was touched.

## 4. Acceptance-criteria check

From `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5 Wave 5 acceptance
criteria:

| Criterion | Status | Evidence |
| --- | --- | --- |
| README opens with the product-first framing from POST §8 | met | First paragraph quotes the POST §8 framing for a natural-language NBA stats answer engine across players, teams, records, splits, streaks, leaderboards, comparisons, and playoff history. |
| README preserves accurate links to existing dev surfaces and release docs | met | Developer surfaces section links `docs/architecture/api_layer.md`; QA section links the release package, release-candidate handoff, release-readiness checklist, hardening plan, parser/routing guardrails, feature promotion rules, query-feedback runbook, and docs index; Data and deployment section links the pipeline runbook and the deployment runbook. |
| No claim that the product supports anything outside the current verified boundary | met | All capability claims were re-ordered/re-framed from existing accurate claims; the "What is intentionally unsupported" section explicitly enumerates the guarded families from `RAW_PRODUCT_RELEASE_PACKAGE.md` §4 and links the full table. No new feature claims were added. |

From the user's explicit Wave 5 task list:

| Required item | Status | Where it appears |
| --- | --- | --- |
| Public answer-first NBA stats product framing | met | Opening paragraph + answer-behavior paragraph. |
| Natural-language NBA stats answer engine | met | First sentence verbatim. |
| Stat-shaped questions | met | First sentence + repeated in "What you can ask" framing. |
| Supported areas: players, teams, records, splits, streaks, leaderboards, comparisons, playoff history | met | First sentence enumerates all eight areas; "What you can ask" has a subsection for each family. |
| Intentionally unsupported boundaries | met | Dedicated "What is intentionally unsupported" section. |
| Web UI quick start before dev surfaces | met | "Web UI quick start" section comes immediately after "What is intentionally unsupported" and before "Developer surfaces". |
| Developer surfaces later: CLI / API / structured query | met | "Developer surfaces" section in order: CLI ask, CLI structured query, HTTP API, exports, engine query classes, filters, entity resolution, stats. |
| QA / release status pointers | met | "QA and release status" section with verbatim status string and links to release package, handoff, checklist, hardening plan, Wave 1 policy docs, feedback runbook, docs index. |
| Data / deployment notes | met | "Data and deployment" section with pipeline commands, stages, freshness, and R2/Vercel deployment summary linking the deployment runbook. |
| Do not rebrand or rename the product | met | `NBA Tools` / `nbatools` retained verbatim. |
| Do not claim support outside the current verified boundary | met | See acceptance row above; only re-ordering/re-framing of existing accurate claims. |
| Touch `docs/index.md` only if README reframing creates a contradiction | met (no-op) | No contradiction; `docs/index.md` not modified (see §3.3). |
| Wave 5 return package created | met | This file. |
| No code/test/corpus/parser/backend/frontend/deployment/behavior changes | met | docs/policy only. |
| `git diff --check` | met (clean — see §5.1) | |

Stop conditions (Wave 5, per plan §5):

- No rebrand / rename: confirmed. `NBA Tools` / `nbatools` retained.

## 5. Validation result

### 5.1 `git diff --check`

Run: `git diff --check`.

Result: clean (no whitespace errors flagged). See §6 for the exact
command.

### 5.2 Markdown lint

No repo-standard markdown linter is wired into the Makefile (per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §8). One IDE lint hint
surfaced during editing on the Setup section
(`MD046/code-block-style: Code block style [Expected: indented;
Actual: fenced]`). The previous README used a fenced ```bash block
only in the Setup section while the rest of the file used indented
code blocks; the Setup section was reformatted to indented code blocks
to clear the hint and unify the file's code-block style. No other lint
hints were flagged.

### 5.3 Code / test / corpus / parser / backend / frontend / deployment changes

None. This wave is docs/policy only.

## 6. Commands run for validation

```text
git diff --check
```

## 7. Scope discipline

What this wave intentionally did not do:

- Did not rebrand or rename the product. `NBA Tools`, `nbatools`,
  `nbatools-cli`, and `nbatools-api` are preserved verbatim.
- Did not claim any feature, query family, filter, or stat outside the
  current verified boundary. The "What is intentionally unsupported"
  section is sourced entirely from
  `RAW_PRODUCT_RELEASE_PACKAGE.md` §4.
- Did not modify `docs/index.md`. The README re-framing adds two
  supported areas (records, playoff history) that the docs/index.md
  list did not enumerate; a superset is not a contradiction, so the
  task constraint ("only if the README reframing creates a
  contradiction") was not triggered.
- Did not change `src/nbatools/`, `frontend/`, `tools/`, `tests/`,
  `data/`, `outputs/`, `Makefile`, `pyproject.toml`, deployment
  scripts, R2 sync, smoke harness, feedback endpoint, parser, routing,
  result contracts, raw QA corpus, frontend-copy QA, or visual QA
  expectations.
- Did not move, rename, archive, or delete any file under
  `return_packages/`, `docs/`, `outputs/`, `archive/`, or anywhere
  else in the repo.
- Did not redeclare release status. The README quotes the current
  release status string verbatim and links the existing release-status
  docs as the source of truth.
- Did not modify `CHANGELOG.md`.
- Did not modify `AGENTS.md`.
- Did not change Wave 4's new "Return Packages" subsection or any
  other section of `docs/index.md`.

## 8. Next wave

Wave 6 — Lightweight Product Promise/Homepage Pass, per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5:

- Target surfaces: frontend homepage / landing surface and the public
  result hero; relevant frontend-copy QA cases if copy changes.
- Goal: a small UX pass that makes the homepage feel search-first and
  answer-first without adding a required tutorial or category selector,
  and folds in the public answer context duplication audit from POST
  §4 (no duplicate scope between the answer sentence and chips).
- Stop conditions to carry forward: no required category selector, no
  required tutorial, no backend/parser behavior change.
- This is the first wave in the plan that touches frontend source
  files; the docs-only run of waves is complete after Wave 5.
