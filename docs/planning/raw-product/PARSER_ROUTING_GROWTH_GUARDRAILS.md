# Parser/Routing Growth Guardrails

## 1. Purpose

This is a durable policy document that governs how new natural-language query
support is added to NBA Tools. It exists so that parser/routing growth cannot
quietly become a wrong-route problem as new query families are introduced.

This doc is policy only. It does not change parser, routing, backend, or
frontend behavior. It does not change result contracts or QA corpus
expectations. It does not initiate any refactor. It defines the bar that any
new natural-language query support must clear before it ships.

Source review notes:

- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_REVIEW_NOTES.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md`

Companion policy:

- `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`

## 2. Working principles

Two principles govern every parser/routing change.

```text
Forgive phrasing.
Do not invent meaning.
```

```text
No broad fallback answers for unsupported or low-confidence queries.
```

What "forgive phrasing" means in practice:

- Accept reasonable rewordings of stat-shaped questions the product already
  supports.
- Accept common aliases (team nicknames, player short names, common stat
  shorthands) where they are already part of the supported surface.
- Tolerate ordering differences ("Lakers record on the road last season" vs
  "Lakers road record last season").

What "do not invent meaning" means in practice:

- Do not infer a metric the user did not name when the supported route
  requires an explicit metric.
- Do not turn a subjective phrase ("best defender", "cooled off lately") into
  a stat answer unless a defined metric and a supported route exist.
- Do not silently substitute a near-but-different route just because the
  intent looks close.

What "no broad fallback" means in practice:

- When parser confidence is below the supported boundary, return
  `no_result` / `filter_not_supported` / a guided unsupported response, not a
  broader related answer.
- Do not promote a partial match into a wider leaderboard, league-wide table,
  or alternate scope.
- Better to clearly say "this is not supported" than to answer a different
  question that looks credible.

## 3. Accepted phrase requirements

Every new supported query family must define an accepted phrase set as part of
its promotion. The set is a written contract, not an implementation detail.

Accepted phrase requirements:

- List the canonical phrasings the family must answer.
- Include reasonable alternate orderings and common shorthand for the same
  intent.
- Include the entity, scope, and filter combinations the family is required
  to handle.
- Each accepted phrase must map to a single expected route.
- Each accepted phrase must have at least one raw QA case in the natural
  query corpus.

Worked example (opponent-conference team record):

```text
Accepted:
- Celtics record against the East
- Celtics record vs Eastern Conference teams
- Lakers record against the West last season
- Lakers record vs Western Conference opponents in 2024-25
```

Each accepted phrase above must route to `team_record` with an
`opponent_conference` filter applied and must be covered by raw QA cases.

## 4. Rejected / guarded phrase requirements

Every new supported query family must also define a rejected / guarded phrase
set. This is the negative half of the contract and is what prevents wrong-route
growth.

Rejected / guarded phrase requirements:

- List phrasings that look adjacent to the accepted set but are explicitly
  not supported by this family.
- For each rejected phrase, state the expected unsupported behavior:
  `no_result`, `filter_not_supported`, a guided unsupported response, or a
  specific named alternative route when one applies.
- Rejected phrases must have raw QA cases that assert the unsupported
  behavior. Asserting only that the wrong route does not fire is not enough
  on its own — the corpus must pin the supported behavior shape.
- A new family must not loosen an existing family's rejected/guarded set in
  order to ship.

Worked example (opponent-conference team record):

```text
Rejected / guarded:
- east coast teams           -> geography phrase; unsupported
- conference finals          -> playoff round concept, not opponent filter
- vs Atlantic Division       -> division filter; unsupported in this family
- historical conference record outside trusted seasons -> conference_coverage
                                                          unsupported
```

## 5. Route collision check rule

Wrong route is the dominant failure mode, not crashes. Every new supported
family must be reviewed against the route collision groups before it ships.

Required collision check:

- For each accepted phrase in the new family, name every existing family
  whose phrasing is adjacent in surface form.
- Provide a raw QA case for at least one phrasing in each adjacent family
  that asserts the existing family still routes correctly after the new
  family ships.
- For each rejected/guarded phrase in the new family, state which existing
  family it most resembles and assert the unsupported behavior with a raw QA
  case.
- If two families could legitimately match a phrase, document which one wins
  and why; the loser must have an explicit rejected phrase or guarded path.

Known high-risk collision groups (from PARSER_ROUTING_GROWTH_REVIEW_NOTES
§10C):

```text
opponent conference vs conference finals vs geography phrases
team record vs team comparison vs team matchup
player comparison vs player-vs-opponent summary
leaderboard vs top single-game performances
subjective/trend phrases vs supported stat metrics
```

Every new family promotion must explicitly say which of these collision
groups it touches, and document the routing decision for the touched group.

## 6. Unsupported-boundary regression requirement

A new family must not erode an existing unsupported boundary. Unsupported
behavior is a feature, not a gap.

Requirements:

- Identify every unsupported boundary the new family is near.
- Add or keep raw QA cases that pin the unsupported behavior at each near
  boundary.
- The expected unsupported shape (`no_result`, `filter_not_supported`,
  `conference_coverage`, or a guided unsupported response) must be the same
  shape that shipped before the new family.
- If a previously unsupported phrasing becomes supported, that change must
  be called out explicitly in the promotion record, not buried inside a
  parser rule.

The product rule:

```text
The unsupported boundary is part of the product.
Moving it requires a deliberate promotion, not an accidental side effect of
adding a new rule.
```

## 7. QA / corpus requirement

Every new supported family must ship with corpus coverage that pins both the
accepted and the rejected behavior.

Required coverage:

- At least one raw QA case per accepted phrase canonical form.
- At least one raw QA case per rejected/guarded phrase listed in the family
  contract.
- At least one collision-group case per adjacent existing family the new
  family is near, asserting the existing family still routes correctly.
- At least one unsupported-boundary case for each nearby boundary the new
  family does not cross.

Corpus discipline:

- Raw QA cases are the source of truth for parser/routing behavior.
- Frontend-copy QA and visual QA are required only when rendering changes
  result from the promotion. See `FEATURE_PROMOTION_RULES.md` for those
  gates.
- A new family cannot ship if its raw QA cases pass only because a broad
  fallback answered them. Each case must assert the specific expected
  shape.

## 8. No broad fallback rule

This rule is restated here as a hard guardrail because it is the rule most
likely to be quietly relaxed under pressure to "answer something".

```text
No broad fallback answers for unsupported or low-confidence queries.
```

Concrete applications:

- If a route requires a metric and the parser cannot pin one, return
  `filter_not_supported` or a guided unsupported response. Do not silently
  pick a default metric.
- If a route requires a scope and the parser cannot resolve it, return
  `no_result` for the requested scope. Do not widen the scope and return a
  broader answer.
- If the user's phrasing partially matches multiple families and confidence
  is split, prefer the clearer unsupported response over a confident-looking
  wrong route.

## 9. Working contract format

Every new supported family must record its contract in the format expected
by `FEATURE_PROMOTION_RULES.md`. At minimum, the contract names:

- accepted phrases
- rejected / guarded phrases
- expected route
- expected unsupported behavior
- required data contract
- result contract expectations
- frontend rendering expectations
- raw QA cases
- frontend-copy QA cases when copy changes
- visual QA cases when UI/layout changes
- deployment / R2 checks when data-backed
- release-doc updates

`FEATURE_PROMOTION_RULES.md` is the canonical home of the per-feature
contract format and its worked example. This doc covers the parser/routing
half of the contract; the feature promotion doc covers the full path.

## 10. Deferred items

The following work is intentionally deferred. It is named here so the
deferral is durable and is not reconsidered casually.

### 10.1 Gradual `natural_query.py` extraction

`src/nbatools/commands/natural_query.py` is the parser maintainability risk
identified by `PARSER_ROUTING_GROWTH_REVIEW_NOTES` §6. The current policy is:

```text
Do not panic-rewrite the parser.
Do not casually keep growing one giant parser file forever.
Add parser-growth guardrails now.
Refactor/extract gradually and safely.
```

Safe extraction candidates (execution deferred; document only in this
guardrail doc):

- stat aliases / constants
- player / team aliases if duplicated
- date parsing helpers
- unsupported-boundary definitions
- route-family-specific helpers
- note / caveat construction helpers

A single-pass rewrite is an explicit non-goal. Any future extraction wave
must follow the same accepted/rejected/collision/unsupported-boundary
guardrails as a new family promotion.

### 10.2 Bucket-first intent classification preflight

The bucket-first conceptual model from `PARSER_ROUTING_GROWTH_REVIEW_NOTES`
§7 (player_subject, team_subject, comparison, leaderboard, finder, record,
split, streak, playoff, unsupported_or_ambiguous) is a candidate
architectural direction but is not committed work.

Any bucket-first preflight, if undertaken later, must:

- not change observable routing behavior in its first wave
- not change result contracts
- not change QA corpus expectations
- be evaluated against the same accepted/rejected/collision/unsupported
  guardrails as a new family

This doc records the deferral. It does not commit to the design.

## 11. How this doc is used

- When a contributor proposes a new supported query family, this doc is the
  parser/routing half of the bar that proposal must clear.
- When an agent is asked to "just add a phrase rule", this doc is the
  reference that explains why a contract is required first.
- When a reviewer evaluates a parser change, the checks in sections 3–8 are
  the minimum review surface.
- When a future review revisits the deferred items in section 10, this doc
  is the prior decision record.

This is a policy document. Updates to it are themselves a policy change and
should be treated with the same care as a feature promotion.
