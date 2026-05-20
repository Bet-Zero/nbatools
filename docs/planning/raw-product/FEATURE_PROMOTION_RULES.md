# Feature Promotion Rules

## 1. Purpose

This is a durable policy document that governs how new product capabilities
are promoted in NBA Tools. It is the product-level companion to
`PARSER_ROUTING_GROWTH_GUARDRAILS.md`. Together they replace the implicit
"add a parser rule and ship" path with an explicit promotion path that any
new supported area must follow.

This doc is policy only. It does not change parser, routing, backend, or
frontend behavior. It does not change result contracts or QA corpus
expectations. It does not add features. It defines the bar that any new
supported area must clear before it is treated as shipped.

Source review notes:

- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_REVIEW_NOTES.md`

Companion policy:

- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`

## 2. Working principles

```text
Forgive phrasing.
Do not invent meaning.
```

```text
No broad fallback answers for unsupported or low-confidence queries.
```

```text
Do not casually promote new capabilities unless the data, route, UI, QA,
deployment, and docs are ready.
```

A capability is not "shipped" because the parser routes its phrasing. A
capability is shipped when its data, route, result contract, QA cases,
frontend rendering, deployment artifacts, and release docs all agree on the
same boundary.

## 3. The promotion path

Every new supported area must traverse the following path. Stages are
ordered. Earlier stages must be honest about scope before later stages
begin; later stages must not back-fill missing earlier work.

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

### 3.1 Unsupported boundary

Start from a clear statement of what is currently unsupported.

- Name the current unsupported behavior for the target phrasing. This is the
  reference point the promotion is moving.
- State why moving it is worth the cost (which user-visible questions become
  answerable, and which adjacent questions remain unsupported).
- If there is no current unsupported boundary because the phrasing already
  returns something, the promotion is a behavior change and must be treated
  with extra care: existing answers may be wrong-route answers that look
  credible.

### 3.2 Preflight

Produce a short preflight that resolves open product decisions before any
code is touched.

- Decide accepted phrasings, rejected phrasings, expected route, and
  expected unsupported behavior at the boundary.
- Decide whether new data is required and where it lives (raw / processed /
  R2 keys).
- Decide whether the existing result contract is sufficient or needs an
  extension. Extensions are themselves a promotion-scale event.
- Decide whether the frontend renderer needs new copy, new visual
  treatment, or only an additive section.
- Decide what raw QA, frontend-copy QA, and visual QA cases will pin the
  promotion's accepted and rejected behavior.
- Decide the deployment / R2 implications when data-backed (see §3.8 and
  the "Data-backed Feature Promotion Checklist" section of
  `docs/operations/deployment.md`).

The preflight is a written artifact. It can live in
`docs/planning/raw-product/` alongside the family it covers.

### 3.3 Data contract

If the promotion is data-backed, the data contract is the next gate.

- Specify the canonical data source(s) the family depends on (`raw/...`,
  `processed/...`, `data_contracts.md` entry).
- Specify the R2 object keys that will be required by deployed runtime.
- Specify behavior when data is missing: `no_data`, `unsupported`,
  `conference_coverage`, etc. Missing data must not degrade into a broader
  fallback.
- If no new data is required, state so explicitly. "No new data" is a valid
  data contract.

### 3.4 Route / result contract

Decide the route the family targets and the result contract it returns.

- Name the route (existing or new). New routes are higher-scope changes and
  may warrant their own promotion artifacts.
- Specify the result contract sections, fields, and conditional stacks the
  family produces. Reuse existing sections when possible.
- Specify the no-result / unsupported result shape at the boundary, in
  enough detail that the frontend renderer behavior is unambiguous.
- Cross-check the route choice against the route collision groups in
  `PARSER_ROUTING_GROWTH_GUARDRAILS.md` §5.

### 3.5 Parser support

Parser support is downstream of the data, route, and result contract — not
upstream of them.

- Apply the parser changes required to recognize the accepted phrasings.
- Apply the rejected / guarded phrasing guards required to prevent
  wrong-route growth.
- Honor the no-broad-fallback rule: low-confidence or out-of-boundary
  queries return the unsupported shape, not a wider answer.
- Parser changes must satisfy the accepted, rejected, collision, and
  unsupported-boundary checks in `PARSER_ROUTING_GROWTH_GUARDRAILS.md`
  §3–§8.

### 3.6 Raw QA cases

Raw QA is the canonical proof that parser + route + data + result contract
agree.

- Add at least one raw QA case per accepted phrase canonical form.
- Add at least one raw QA case per rejected / guarded phrase.
- Add at least one raw QA case per adjacent-family collision group the
  family touches.
- Add at least one raw QA case per nearby unsupported boundary the family
  does not cross.
- Cases must assert the specific expected result shape, not "did not crash"
  and not "did not fall back".

### 3.7 Frontend-copy / visual QA when rendering changes

If the promotion changes user-visible copy or layout, the frontend-copy QA
and visual QA harnesses are required gates.

- Add frontend-copy QA cases for each new answer phrase or new copy
  variation.
- Add visual QA cases for each new layout, new section, or new state the
  homepage and result surfaces may show.
- If rendering does not change, state that explicitly and skip these gates.
  "Rendering unchanged" is a valid promotion record.

### 3.8 Preview / deployment smoke

If the promotion is data-backed or otherwise touches deployed runtime
behavior, deployment smoke is a required gate.

- Confirm required R2 object keys are listed.
- Confirm the data is synced to R2.
- Run deployment smoke against preview / production, targeting the new
  family.
- Confirm missing-data behavior returns the clean unsupported shape (no
  broad fallback).

The full data/R2 promotion checklist lives in
`docs/operations/deployment.md` under "Data-backed Feature Promotion
Checklist". Its rules 1–5 (required runtime data key list, R2 sync
verification with `head_object` evidence, deployment smoke pointed at the
feature, missing-data clean unsupported behavior, no broad fallback) are
the deployment-side gates for this stage.

### 3.9 Release docs

Release docs must agree with the new boundary. The promotion is not
complete until they do.

- Update `docs/reference/query_catalog.md` if the supported phrasing list
  changes.
- Update `docs/reference/query_guide.md` if the structured / natural query
  reference changes.
- Update `docs/reference/current_state_guide.md` if the verified shipped
  behavior changes.
- Update `docs/index.md` if a new durable doc is added under `docs/`.
- Update the active raw product release / handoff docs only if the
  release boundary itself moves.

## 4. Per-feature contract

Every promotion produces a single written contract. The contract is what a
reviewer reads to decide whether the promotion is ready.

Required fields:

- **accepted phrases** — canonical and reasonable alternate phrasings the
  family must answer
- **rejected / guarded phrases** — adjacent phrasings the family must not
  answer, with the expected unsupported behavior for each
- **expected route** — the route the family targets
- **expected unsupported behavior** — the specific shape returned at the
  boundary (`no_result`, `filter_not_supported`, `conference_coverage`,
  guided unsupported, etc.)
- **required data contract** — the canonical data sources and R2 keys, or
  "no new data" stated explicitly
- **result contract expectations** — the sections, fields, and conditional
  stacks the family produces
- **frontend rendering expectations** — the renderer behavior, or
  "rendering unchanged" stated explicitly
- **raw QA cases** — the case list pinning accepted, rejected, collision,
  and unsupported-boundary behavior
- **frontend-copy QA cases** — when copy changes; otherwise stated as
  "no copy change"
- **visual QA cases** — when UI/layout changes; otherwise stated as
  "no layout change"
- **deployment / R2 checks** — when data-backed; otherwise stated as
  "not data-backed"
- **release-doc updates** — the docs that must change for the new boundary
  to be honest

A promotion that cannot honestly fill every field is not ready.

## 5. Worked example — opponent-conference team record

The opponent-conference team record promotion is the worked example because
it is the most recent data-backed promotion in the Raw Product and it
exhibits every stage of the promotion path.

### 5.1 Unsupported boundary (before)

```text
"Celtics record against the East" -> no opponent-conference filter
                                     supported; either no_result or a
                                     broader team_record without the filter
                                     applied.
```

The promotion target: turn that phrasing into a clean opponent-conference
filtered `team_record` answer, with a clean unsupported shape when data is
unavailable for the requested season.

### 5.2 Preflight

The preflight resolved:

- accepted phrasings around "vs / against the East / West / Eastern / Western
  Conference"
- rejected phrasings: geography ("east coast teams"), playoff round
  ("conference finals"), division filters, historical conference coverage
  outside trusted seasons
- target route: `team_record` with an `opponent_conference` filter
- target unsupported shape at the boundary: `filter_not_supported` for
  rejected phrasings, `conference_coverage` for unsupported historical
  seasons
- data requirement: a conference membership mapping per supported season

### 5.3 Data contract

```text
raw/teams/team_conference_membership.csv
```

Required for opponent-conference support. Must exist in R2 for deployed
runtime behavior. Missing-data behavior is the clean `conference_coverage`
unsupported shape, not a broader team_record answer.

### 5.4 Route / result contract

- Route: `team_record` (existing).
- Result contract: existing `team_record` sections with an
  `opponent_conference` filter applied; no new sections introduced.
- Unsupported shape at the boundary: `filter_not_supported` /
  `conference_coverage`.
- Collision groups touched (from `PARSER_ROUTING_GROWTH_GUARDRAILS.md` §5):
  opponent conference vs conference finals vs geography phrases; team
  record vs team comparison vs team matchup.

### 5.5 Parser support

Parser changes recognized the accepted phrasings, guarded the rejected
phrasings, and honored the no-broad-fallback rule for low-confidence /
out-of-boundary cases.

### 5.6 Raw QA cases

Raw QA covered:

- accepted phrasings (Celtics / Lakers / East / West / current and prior
  seasons)
- rejected phrasings (geography, conference finals, divisions)
- nearby unsupported boundaries (historical conference coverage outside
  trusted seasons returns `conference_coverage`)
- adjacent existing families (plain team_record without an
  opponent_conference filter still routes correctly)

### 5.7 Frontend-copy / visual QA

The promotion preserved the existing `team_record` rendering, so visual QA
re-asserted existing baselines and frontend-copy QA added cases for the
opponent-conference scope phrase in the answer sentence.

### 5.8 Preview / deployment smoke

The opponent-conference promotion is also the worked example of the
data/R2 deployment guardrail in `RAW_PRODUCT_POST_REVIEW_NOTES.md` §6. The
`raw/teams/team_conference_membership.csv` object was required to exist in
R2 for deployed runtime behavior, and deployment smoke confirmed the
deployed runtime returned the clean answer rather than a fallback.

The detailed data/R2 promotion checklist lives in
`docs/operations/deployment.md` under "Data-backed Feature Promotion
Checklist", and its §6 reproduces this same opponent-conference example
from the deployment side (required-key list, `head_object` evidence,
deployment smoke case, missing-data unsupported shape).

### 5.9 Release docs

Release docs were updated to reflect the new supported boundary
(`query_catalog.md`, `query_guide.md`, `current_state_guide.md`, and the
active release / handoff docs as appropriate).

## 6. Promotion stop conditions

A promotion must stop and re-plan if any of the following are true:

- The promotion cannot honestly fill every per-feature contract field in
  §4.
- The promotion requires loosening a guarded phrasing in another existing
  family.
- The promotion requires the parser to invent a metric, scope, or filter
  the user did not name.
- The promotion would introduce a broad fallback for unsupported or
  low-confidence queries.
- The promotion is data-backed but no R2 path is identified.
- The promotion changes rendering but no frontend-copy or visual QA cases
  are added.

A stop is not a failure. It is a signal that the promotion needs a smaller,
better-bounded version, or a different preflight.

## 7. Non-goals

This policy doc does not:

- prescribe the size of a promotion (small additive families and larger new
  routes both use the same path; the contract scales with scope)
- replace the existing planning, preflight, or return-package conventions
- require a category selector before search (explicit non-goal of the Raw
  Product post-review)
- mandate a parser rewrite (explicit non-goal of the parser/routing growth
  review)
- automate corpus mutation from feedback (explicit non-goal)

## 8. How this doc is used

- When a contributor proposes a new supported area, this doc is the
  product-level bar that proposal must clear.
- When an agent is asked to "just add support for X", this doc is the
  reference that explains the path X must traverse.
- When a reviewer evaluates a promotion, §3 is the stage checklist and §4
  is the contract checklist.
- When a future promotion is data-backed, the "Data-backed Feature
  Promotion Checklist" section of `docs/operations/deployment.md` is the
  deployment gate.

This is a policy document. Updates to it are themselves a policy change and
should be treated with the same care as a feature promotion.
