# Raw Product Hardening — Wave 1 Return Package

## 1. Executive summary

- Wave executed: Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion
  Rules, per
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5.
- What was produced: two durable policy docs and an updated docs index.
  - `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
  - `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`
  - `docs/index.md` planning section updated to list both new docs.
- Scope: docs/policy only. No production code, parser, routing, backend,
  frontend, test, or corpus changes.
- Release status: unchanged. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`.
- Next wave: Wave 2 — Data/R2 Promotion Checklist Hardening (target file
  `docs/operations/deployment.md`).

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md` | Added doc | New durable parser/routing policy doc; encodes working principles, accepted/rejected phrase contracts, route collision rule, unsupported-boundary regression rule, QA/corpus requirements, no-broad-fallback rule, deferred items. |
| `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md` | Added doc | New durable product-level promotion policy doc; encodes promotion path, per-feature contract format, opponent-conference worked example, stop conditions, non-goals. |
| `docs/index.md` | Updated doc index | Links both new policy docs from the planning section. |
| `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_1_RETURN_PACKAGE.md` | Added return package | Records what changed, files changed, acceptance-criteria check, and validation result for Wave 1. |

No other files were created, modified, moved, or deleted.

## 3. What changed (substantive content)

### 3.1 PARSER_ROUTING_GROWTH_GUARDRAILS.md

Sections in the new doc:

1. Purpose — policy-only framing; sources from `PARSER_ROUTING_GROWTH_REVIEW_NOTES.md` and `RAW_PRODUCT_POST_REVIEW_NOTES.md`; companion to `FEATURE_PROMOTION_RULES.md`.
2. Working principles — both governing rules:
   - "Forgive phrasing. Do not invent meaning."
   - "No broad fallback answers for unsupported or low-confidence queries."
3. Accepted phrase requirements — with opponent-conference worked example.
4. Rejected / guarded phrase requirements — with opponent-conference worked example (geography, conference finals, divisions, historical coverage).
5. Route collision check rule — names the high-risk collision groups from `PARSER_ROUTING_GROWTH_REVIEW_NOTES` §10C verbatim.
6. Unsupported-boundary regression requirement — unsupported behavior is a feature, not a gap.
7. QA / corpus requirement — at least one raw case per accepted, rejected, collision, and nearby-unsupported-boundary item.
8. No broad fallback rule — restated as a hard guardrail with concrete applications.
9. Working contract format — points to `FEATURE_PROMOTION_RULES.md` for the full per-feature contract.
10. Deferred items — (10.1) gradual `natural_query.py` extraction; (10.2) bucket-first intent classification preflight.
11. How this doc is used.

### 3.2 FEATURE_PROMOTION_RULES.md

Sections in the new doc:

1. Purpose — product-level companion to `PARSER_ROUTING_GROWTH_GUARDRAILS.md`.
2. Working principles — both governing rules, plus the "do not casually promote" framing from `RAW_PRODUCT_POST_REVIEW_NOTES.md` §9.
3. The promotion path — full ordered path:
   ```text
   unsupported boundary
     -> preflight
     -> data contract
     -> route / result contract
     -> parser support
     -> raw QA cases
     -> frontend-copy / visual QA when rendering changes
     -> preview / deployment smoke
     -> release docs
   ```
   Each stage has its own subsection (§3.1–§3.9).
4. Per-feature contract — every required field (accepted phrases, rejected/guarded phrases, expected route, expected unsupported behavior, required data contract, result contract expectations, frontend rendering expectations, raw QA cases, frontend-copy QA cases, visual QA cases, deployment/R2 checks, release-doc updates).
5. Worked example — opponent-conference team record, stage by stage (§5.1–§5.9).
6. Promotion stop conditions — the six explicit re-plan triggers.
7. Non-goals — category selector, parser rewrite, automatic corpus mutation, etc.
8. How this doc is used.

Cross-link to Wave 2 deployment runbook section is present: §3.8 and §5.8
explicitly state the data/R2 checklist will live in
`docs/operations/deployment.md` as part of Wave 2, and that the runbook
itself is the link target until that section lands.

### 3.3 docs/index.md

Two new bullets added to the planning section, immediately below the
existing `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` entry. No other entries
moved or removed.

## 4. Acceptance-criteria check

From `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5 Wave 1 acceptance criteria:

| Criterion | Status | Evidence |
|---|---|---|
| Both new docs exist under `docs/planning/raw-product/` | met | `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md` and `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md` created. |
| Both encode "Forgive phrasing. Do not invent meaning." | met | Stated verbatim in `PARSER_ROUTING_GROWTH_GUARDRAILS.md` §2 and `FEATURE_PROMOTION_RULES.md` §2. |
| Both encode "No broad fallback answers for unsupported or low-confidence queries." | met | Stated verbatim in `PARSER_ROUTING_GROWTH_GUARDRAILS.md` §2 and §8, and in `FEATURE_PROMOTION_RULES.md` §2. |
| `FEATURE_PROMOTION_RULES.md` explicitly references opponent-conference support as the worked example | met | `FEATURE_PROMOTION_RULES.md` §5 walks the entire promotion path using opponent-conference team record. |
| `docs/index.md` lists both docs | met | Two new bullets added to the planning section, both with one-line hooks. |

From the recommended first execution prompt in
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §6:

| Required content | Status |
|---|---|
| Working principles in `PARSER_ROUTING_GROWTH_GUARDRAILS.md` | met (§2) |
| Accepted phrase requirements | met (§3) |
| Rejected/guarded phrase requirements | met (§4) |
| Route collision check rule with the example collision groups from `PARSER_ROUTING_GROWTH_REVIEW_NOTES` §10C | met (§5; the five collision groups are quoted) |
| Unsupported-boundary regression requirement | met (§6) |
| QA/corpus requirement | met (§7) |
| Deferred items: gradual `natural_query.py` extraction, bucket-first intent classification preflight | met (§10.1 and §10.2) |
| Promotion path in `FEATURE_PROMOTION_RULES.md` | met (§3.1–§3.9) |
| Per-feature contract fields | met (§4; all 12 fields listed) |
| Worked example: opponent-conference support | met (§5.1–§5.9) |
| Cross-link to Wave 2 deployment-runbook section (link target may be the runbook itself for now) | met (§3.8 and §5.8 cite `docs/operations/deployment.md`) |
| `docs/index.md` planning section updated to list both new docs | met |

Stop conditions (Wave 1):

- No change to `src/nbatools/commands/natural_query.py` or any parser
  rules: confirmed.
- No category selector or new feature introduced: confirmed.
- No `natural_query.py` extraction begun: confirmed (deferred and named in
  §10.1 of the guardrails doc).

## 5. Validation result

### 5.1 `git diff --check`

Run: `git diff --check`.

Result: clean (no whitespace errors flagged). See §6 for the exact command.

### 5.2 Markdown lint

No repo-standard markdown linter is wired into the Makefile (per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §8). `git diff --check` is the
minimum bar, and it passed.

### 5.3 Code / test / corpus / parser / backend / frontend changes

None. This wave is docs/policy only.

## 6. Commands run for validation

```text
git diff --check
```

## 7. Scope discipline

What this wave intentionally did not do:

- Did not change `src/nbatools/commands/natural_query.py` or any parser
  surface.
- Did not change `src/nbatools/query_service.py` or any backend behavior.
- Did not change result contracts, raw QA corpus, frontend-copy QA, or
  visual QA expectations.
- Did not change `README.md`, the active release docs, or the public UI.
- Did not move, archive, rename, or delete any file.
- Did not begin the deferred `natural_query.py` extraction or any
  bucket-first preflight.
- Did not redeclare release status.

## 8. Next wave

Wave 2 — Data/R2 Promotion Checklist Hardening:

- Target file: `docs/operations/deployment.md`.
- Goal: turn `RAW_PRODUCT_POST_REVIEW_NOTES.md` §6 into a permanent,
  checkable promotion checklist (required runtime data key list rule, R2
  sync verification rule with `head_object` evidence, deployment smoke
  rule pointed at the feature, missing-data clean
  `no_data` / `unsupported` behavior rule with no broad fallback).
- Worked example: `raw/teams/team_conference_membership.csv`.
- Cross-link: `FEATURE_PROMOTION_RULES.md` §3.8 / §5.8 will be tightened to
  point at the new section in `docs/operations/deployment.md` once it
  lands.
