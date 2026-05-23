# Raw Product Hardening — Wave 4 Return Package

## 1. Executive summary

- Wave executed: Wave 4 — Docs/Return Package Taxonomy, per
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5.
- What was produced: a new "Return Packages" subsection inside the
  existing "Documentation Category Rules" section of `docs/index.md`,
  encoding the durable rules from
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md` §7. The
  subsection covers: return packages as evidence rather than source of
  truth; durable behavior changes belonging under `docs/`; the
  `return_packages/` home; the `outputs/` home for generated reports and
  machine/test artifacts; the regular archive cadence for completed wave
  packages; the requirement that prompts tell agents where return
  packages belong; and the rule that short copied summaries are
  appropriate for trivial changes.
- Files changed: `docs/index.md` only. `AGENTS.md` was inspected and
  does **not** reference return packages, so per the Wave 4 task
  constraint ("AGENTS.md only if it already references return packages")
  it was not modified.
- Scope: docs/policy only. No production code, parser, routing, backend,
  frontend, deployment, test, corpus, or behavior changes. No file
  moves, archives, renames, or deletions under `return_packages/`.
- Release status: unchanged. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`.
- Next wave: Wave 5 — README/Product Positioning Refresh (target file
  `README.md`, with `docs/index.md` "What NBA Tools Currently Supports"
  touched only if the README re-framing creates a contradiction).

## 2. Files changed

| File | Change type | Why |
| --- | --- | --- |
| `docs/index.md` | Updated docs index | Added a new "Return Packages" subsection inside the existing "Documentation Category Rules" section, between the existing "Working / Temporary Inventories" subsection and the "Audits — `audits/`" top-level section. No existing subsection or section was renamed, reordered, or rewritten. |
| `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_4_RETURN_PACKAGE.md` | Added return package | Records what changed, files changed, acceptance-criteria check, and validation result for Wave 4. |

No other files were created, modified, moved, or deleted. In
particular, no file under `return_packages/` was moved, renamed, or
archived; Wave 4 documents the rules, and the archive sweep is a
separate later pass per the plan §7 deferred list and Wave 4 stop
conditions.

## 3. What changed (substantive content)

### 3.1 docs/index.md — new "Return Packages" subsection

Location: inserted under the existing `## Documentation Category Rules`
section, immediately after the existing `### Working / Temporary
Inventories` subsection and immediately before the top-level
`## Audits — audits/` section. The other subsections of the
"Documentation Category Rules" section (Reference, Architecture,
Operations, Planning, Archive, Audits / Reviews / Verdicts, Working /
Temporary Inventories) were not edited.

Heading: `### Return Packages`.

The subsection opens with a one-paragraph framing that names return
packages as agent-to-reviewer handoff artifacts and asserts the
evidence-vs-source-of-truth distinction. It is followed by seven
bulleted rules, each of which leads with a short bolded rule name. The
seven rules:

1. **Evidence, not source of truth.** A return package is a
   point-in-time receipt for one execution wave; the authoritative
   description of current behavior lives under `docs/`.
2. **Durable behavior changes belong under `docs/`.** Long-term changes
   to behavior, policy, runbooks, contracts, interfaces, or
   release-readiness facts must land under `docs/` (in `reference/`,
   `architecture/`, `operations/`, `planning/`, `audits/`, or
   `archive/`), not only in the return package. The return package may
   quote or summarize the durable change, but the durable doc is what
   readers consult later.
3. **Return packages live under `return_packages/`.** Topic-scoped
   subdirectories such as `return_packages/raw-product/`,
   `return_packages/result_display/`, and `return_packages/review/` are
   the home for wave handoff artifacts. Durable product/operations/
   architecture/reference content does not live under
   `return_packages/`.
4. **Generated reports and machine/test artifacts live under
   `outputs/`.** Exported feedback runs, screenshot bundles, machine-
   generated QA reports, and similar regeneratable artifacts belong
   under `outputs/<workflow>/<run_id>/`, not under `return_packages/`
   or `docs/`. A return package may reference an `outputs/` run id; it
   should not copy the generated artifact into the return package.
5. **Archive completed wave packages on a regular cadence.** Once a
   workstream, release cycle, or wave series closes, completed return
   packages should be archived on a regular cleanup cadence so they
   stop competing visually with active planning docs. The archive sweep
   is a separate, explicitly scoped pass — not a side effect of an
   unrelated execution wave. No automatic deletion.
6. **Prompts must tell agents where return packages belong.** Execution
   prompts that produce a return package should state the exact target
   path (for example,
   `return_packages/raw-product/<WAVE_NAME>_RETURN_PACKAGE.md`), call
   out that durable behavior changes must also update `docs/`, and —
   when appropriate — say whether a short copied summary is acceptable
   in place of a committed return package file.
7. **Short copied summaries are appropriate for trivial changes.** For
   meaningful execution waves, release evidence, QA checkpoints, and
   any wave that changes a contract, runbook, policy, or release-
   readiness fact, write a committed return package under
   `return_packages/`. For trivial changes (typo fixes, single-link
   additions, cosmetic doc tweaks, one-line README clarifications) it
   is acceptable — and often preferred — to paste a short copied
   summary into the handoff prompt or PR description instead of
   committing a return package file. When in doubt, write the return
   package.

These rules are a direct encoding of
`RAW_PRODUCT_POST_REVIEW_NOTES.md` §7 (taxonomy block, rules block, and
the open-question / potential-answer block on trivial-change
summaries).

### 3.2 AGENTS.md — not changed

The Wave 4 task constraint reads: "AGENTS.md only if it already
references return packages." `AGENTS.md` was searched (case-insensitive)
for `return package` and `return_package`; both searches returned no
matches. Therefore `AGENTS.md` was not modified in this wave. If a
future wave adds return-package guidance to `AGENTS.md`, that wave
should cross-link the new "Return Packages" subsection of
`docs/index.md`.

### 3.3 No files moved, archived, renamed, or deleted

Per the Wave 4 stop conditions and the user's explicit instruction
("Do not move, archive, rename, or delete any files in this wave"), no
file under `return_packages/` was moved, renamed, or deleted. The
archive cadence is documented as a rule; the archive sweep itself is a
separate later pass.

### 3.4 No code/test/corpus/parser/backend/frontend/deployment/behavior changes

None. This wave is docs/policy only.

## 4. Acceptance-criteria check

From `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5 Wave 4 acceptance
criteria:

| Criterion | Status | Evidence |
| --- | --- | --- |
| `docs/index.md` has a clearly labeled return-package taxonomy section | met | New `### Return Packages` subsection added under `## Documentation Category Rules`. |
| Rules cover: where return packages live | met | Rule 3 (`Return packages live under return_packages/`). |
| Rules cover: when to create them vs paste a short summary | met | Rule 7 (`Short copied summaries are appropriate for trivial changes`). |
| Rules cover: archive cadence | met | Rule 5 (`Archive completed wave packages on a regular cadence`). |

From the user's explicit Wave 4 task list (target rules):

| Required rule | Status | Where it appears |
| --- | --- | --- |
| Return packages are evidence, not source of truth | met | Rule 1 + intro paragraph. |
| Durable behavior changes belong under `docs/` | met | Rule 2. |
| Return packages live under `return_packages/` | met | Rule 3. |
| Outputs are generated reports/artifacts | met | Rule 4 (names `outputs/<workflow>/<run_id>/`). |
| Completed return packages should be archived on a regular cadence | met | Rule 5. |
| Prompts should tell agents where return packages belong | met | Rule 6. |
| Use short copied summaries instead of committed return packages for trivial changes when appropriate | met | Rule 7. |
| Target file: `docs/index.md` updated | met | New subsection added. |
| Target file: `AGENTS.md` updated **only if it already references return packages** | met (no-op) | `AGENTS.md` does not reference return packages, so not modified. |
| Wave 4 return package created | met | This file. |
| No file moves, archives, renames, or deletions in this wave | met | No `return_packages/` content was moved, renamed, archived, or deleted. |
| No code/test/corpus/parser/backend/frontend/deployment/behavior changes | met | This wave is docs/policy only. |
| `git diff --check` | met (clean — see §5.1) | |

Stop conditions (Wave 4, per plan §5):

- No move/delete of files in `return_packages/`: confirmed. Archive
  execution remains a separate later pass.

## 5. Validation result

### 5.1 `git diff --check`

Run: `git diff --check`.

Result: clean (no whitespace errors flagged). See §6 for the exact
command.

### 5.2 Markdown lint

No repo-standard markdown linter is wired into the Makefile (per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §8). The new "Return
Packages" subsection follows the existing heading hierarchy and bullet
style used in the rest of `docs/index.md`.

### 5.3 Code / test / corpus / parser / backend / frontend / deployment changes

None. This wave is docs/policy only.

## 6. Commands run for validation

```text
git diff --check
```

## 7. Scope discipline

What this wave intentionally did not do:

- Did not modify `AGENTS.md` (it does not currently reference return
  packages; the Wave 4 task constraint authorizes editing `AGENTS.md`
  only if it does).
- Did not move, rename, archive, or delete any file under
  `return_packages/`.
- Did not move, rename, archive, or delete any file under `docs/`,
  `outputs/`, `archive/`, or anywhere else in the repo.
- Did not change parser, routing, backend, frontend, deployment, R2
  sync, smoke harness, or feedback endpoint behavior.
- Did not change result contracts, raw QA corpus, frontend-copy QA, or
  visual QA expectations.
- Did not change `README.md`, the active release docs, or the public
  UI.
- Did not redeclare release status.
- Did not edit any other subsection of `docs/index.md`'s "Documentation
  Category Rules" section. The new "Return Packages" subsection was
  inserted between the existing "Working / Temporary Inventories"
  subsection and the next top-level section ("Audits — `audits/`"); no
  existing subsection text was rewritten.
- Did not edit the "Directory Layout" block at the top of
  `docs/index.md`. That block describes the `docs/` tree only; the
  return-package, outputs, and archive locations are repo-level
  siblings of `docs/` and are described in the new subsection rather
  than retro-fitted into the `docs/`-scoped layout diagram.

## 8. Next wave

Wave 5 — README/Product Positioning Refresh, per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5:

- Target file: `README.md`.
- Goal: re-order the README so the top of the repo describes the
  current product (public answer-first NBA stats product) rather than
  the historical CLI/dev workbench framing. New ordering: product
  promise → what questions it is good at → what is intentionally
  unsupported → web UI quick start → developer surfaces (CLI / API /
  structured query) → QA / release status pointers → data / deployment
  notes.
- Touch `docs/index.md`'s "What NBA Tools Currently Supports" list only
  if the README re-framing creates a contradiction with that list.
- No rebrand or rename (POST §10 deferred non-goal).
- No new feature claims outside the current verified boundary.
