# Query Surface Expansion Plan

> **Role: Part 1 planning doc for parser/query-surface expansion.**
>
> **Status:** Part 1 complete. This doc no longer represents end-to-end capability completion on its own. The whole-plan completion authority is [`master_completion_plan.md`](./master_completion_plan.md). Part 1's execution/data continuation record is [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md).
>
> This plan drove the natural-query parser/query-surface expansion effort. It replaces the earlier attempt at this doc and is grounded in:
>
> - the actual state of `src/nbatools/commands/natural_query.py` and its helper modules
> - the living shipped inventory in [`docs/reference/query_catalog.md`](../reference/query_catalog.md)
> - the design references in [`docs/architecture/parser/`](../architecture/parser/)
> - the working style rules in [`AGENTS.md`](../../AGENTS.md)
>
> **Read before editing:** this file is a _plan_, not a capability catalog or a spec. Changes here should be directional, not fine-grained implementation detail.

---

## 1. Context

The current engine is mature. It ships ten query classes (finder, count, summary, comparison, split, leaderboard, streak, record, playoff, occurrence), has ~1,684 tests across 42 files, supports 90+ curated player aliases, handles compound boolean threshold logic with AND/OR/parentheses, and exposes itself through a CLI, FastAPI HTTP layer, and React UI.

Despite that, the natural-language surface still feels brittle outside curated examples. The gap is less about raw capability and more about:

- **phrasing coverage** for already-shipped capabilities (search-form and compressed shorthand don't consistently parse to the same place as full questions)
- **defaults and fuzzy-term definitions** that are applied inconsistently because they aren't documented in one place
- **parse-level confidence** and alternate interpretations, neither of which currently exist
- **new capability families** (opponent-quality buckets, on/off, lineups, expanded contexts) that users will ask for

The design references in [`docs/architecture/parser/`](../architecture/parser/) describe the target state. This plan is the bridge from where the parser is today to where those docs say it should be.

---

## 2. Scope and principles

### Guiding principles (abbreviated)

See [`docs/architecture/parser/overview.md`](../architecture/parser/overview.md) for full discussion. The short version:

1. **Question form, search form, and compressed shorthand are all first-class.** Already codified in AGENTS.md.
2. **Favor intent + slots over sentence grammar.** The repo's parse state already embodies this.
3. **Defaults are product policy, not implementation detail.** Document them; don't bury them in code.
4. **The biggest risk is confident-but-inconsistent interpretations**, not weird grammar.
5. **Prefer honest unsupported responses over silently wrong answers.**

### What this plan drives

- which phrasing coverage work to do next, in what order
- where new capability families should live
- which tests and docs need to move in lockstep

### What this plan does NOT drive

- the living inventory of shipped capabilities — that's [`query_catalog.md`](../reference/query_catalog.md)
- the spec of the parser's components — that's [`parser/specification.md`](../architecture/parser/specification.md)
- verified behavior boundaries — that's [`current_state_guide.md`](../reference/current_state_guide.md)
- implementation details inside any specific module

### Completion model used by this repo

For the overall product answer to "is the plan done?", use
[`master_completion_plan.md`](./master_completion_plan.md). The definitions
below describe this Part 1 plan's local completion model and roll up into that
master doc.

The repo now distinguishes three completion levels for user-facing capability work:

1. **Parser/query-surface complete**
   The parser recognizes the phrasing family, extracts the needed slots, routes correctly, and the docs/tests for the parser surface are updated. This level may still return placeholder or unfiltered results.
2. **Execution/data complete**
   The intended user-facing query family returns execution-backed results using the required data source or aggregation layer. If that cannot ship yet, the capability must be explicitly deferred or marked partial with a linked continuation plan, but that deferral remains an open master-plan state unless a product out-of-scope decision is recorded.
3. **Product/capability complete**
   The user-facing capability family is both parser/query-surface complete and execution/data complete, or it is explicitly out of scope by documented product decision. Current-state docs and catalogs may only imply full completion at this level.

**Planning rule:** a subplan, phase, or queue may not imply product completion from parser/query-surface completion alone. If a plan only reaches level 1, it must label itself as **Part 1** (or equivalent) and point to the continuation path for level 2. Whole-plan completion is answered only by [`master_completion_plan.md`](./master_completion_plan.md).

---

## 3. Current state snapshot

A short orientation, not a full inventory. For capabilities see [`query_catalog.md`](../reference/query_catalog.md); for components see [`parser/specification.md`](../architecture/parser/specification.md).

### 3.1 Architecture shape

- `src/nbatools/commands/natural_query.py` is the orchestration layer: `_build_parse_state(query)` extracts ~40 slots in parallel, `_finalize_route(parsed)` picks a route via an if/elif chain, `parse_query` and `run` are thin entry points.
- Specialized routers handle clusters: `try_playoff_record_route`, `try_occurrence_count_route`, `try_compound_occurrence_route`.
- OR queries split via `_split_or_clauses` and merge context via `_merge_inherited_context`, then combine with `_combine_or_results`.
- Helpers are organized by concern: `_parse_helpers`, `_matchup_utils`, `_occurrence_route_utils`, `_playoff_record_route_utils`, `_leaderboard_utils`, `_date_utils`, `_constants`, `entity_resolution`, `query_boolean_parser`.

### 3.2 What's shipped and solid

- entity resolution with ambiguity handling and candidate lists
- time parsing: explicit seasons, season ranges, since-season, last-N-seasons, career, last-N-games, date ranges, by-decade
- threshold parsing with AND, OR, and grouped boolean with parentheses
- core query classes: finder, count, summary, comparison, split, leaderboard, streak, record, playoff, occurrence
- filters: home/away, wins/losses, without-player, opponent team, opponent player, position, playoff round
- multi-surface consumption: CLI, API, UI all read the same envelope

### 3.3 What's partial

- fuzzy time words (`lately`, `past month`, `last night`) resolve inconsistently
- shorthand normalization is scattered across many `detect_*` helpers rather than centralized
- fuzzy-term product policy (`good teams`, `contenders`, `recently`, `best games`) is not documented in one place
- word-order flexibility isn't an explicit test category

### 3.4 What's not yet shipped

- data-backed on/off split execution beyond the current placeholder route
- data-backed lineup execution beyond the current placeholder routes
- opponent-quality buckets (`contenders`, `good teams`, `top-10 defenses`)
- expanded context filters (clutch, quarters, back-to-backs, starter/bench, overtime, one-possession)
- stretch / rolling-window queries (`hottest 3-game stretch`)
- parse-level confidence and alternate interpretations
- canonical parse state formalized as a versioned contract

---

## 4. Gap analysis

Dimension-by-dimension view of where the parser is vs. where [`parser/specification.md`](../architecture/parser/specification.md) says it should be.

| Dimension                         | Shipped state                                          | Target state                                                           | Gap    | Phase |
| --------------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------- | ------ | ----- |
| Surface normalization             | `normalize_text`; many detectors do their own variants | Single consolidated normalizer with published alias table              | Medium | B     |
| Alias mapping (stats, relations)  | Scattered across detectors; partial coverage           | One source of truth, documented in glossary                            | Medium | B     |
| Entity resolution                 | Mature: confidence, candidates, source                 | Extend pattern to teams, opponents, stats                              | Small  | D     |
| Time parsing — explicit           | Seasons, ranges, since, last-N, career, dates, decade  | No change needed                                                       | None   | —     |
| Time parsing — fuzzy              | `recent form` only; others partial                     | `lately`, `past month`, `last night`, `last couple weeks` normalized   | Medium | A/B   |
| Threshold operators               | Mature: AND, OR, grouped booleans with parens          | No change needed                                                       | None   | —     |
| Context filters                   | home/away, wins/losses, playoff rounds, position       | Add clutch, quarters, B2B, starter/bench, OT, one-possession           | Large  | E     |
| Opponent filters (team, player)   | Shipped                                                | No change needed                                                       | None   | —     |
| Opponent-quality buckets          | Not shipped                                            | `contenders`, `good teams`, `top-10 defenses` with product definitions | Large  | E     |
| Absence (`without X`)             | Shipped; clears player when it matches subject         | Broaden phrasing (`X out`, `X didn't play`, `no X`, `sans X`)          | Small  | A     |
| On/off queries                    | Single-player placeholder routing shipped              | New intent family with `lineup_members`, `presence_state` slots        | Medium | E     |
| Lineup queries                    | Placeholder routing shipped                            | New intent family with `unit_size`, `minute_minimum` slots             | Medium | E     |
| Streak queries                    | Shipped: player + team, with defaults                  | No change needed                                                       | None   | —     |
| Occurrence queries                | Shipped: single, compound, distinct-count              | No change needed                                                       | None   | —     |
| Playoff / historical              | Shipped: history, appearances, rounds, decades         | No change needed                                                       | None   | —     |
| Defaults for underspecified       | Some defaults applied in `_build_parse_state`          | Explicit, documented, applied consistently                             | Medium | C     |
| Word-order flexibility            | Works for some patterns, not systematically tested     | Explicit equivalence-group coverage                                    | Medium | A     |
| Search-form / shorthand coverage  | Many shipped capabilities accept only some phrasings   | All shipped capabilities accept question + search + shorthand          | Large  | A     |
| Parse-level confidence            | Not shipped (entity-level only)                        | Parse-wide confidence score                                            | Medium | D     |
| Alternate interpretations         | Not shipped                                            | Surface top-2 when confidence is medium                                | Medium | D     |
| Canonical parse state             | Implicit dict; route + route_kwargs appended           | Formalized schema with `intent` enum, `confidence`, `alternates`       | Medium | D     |
| Glossary / fuzzy-term definitions | Scattered across code; no doc source of truth          | One table, referenced from parser and stats engine                     | Medium | B     |
| Evaluation harness                | Marker-based (`parser`, `query`), testmon-backed       | Add explicit equivalence-group tests + failure-mode cases              | Medium | A     |

---

## 5. Phased roadmap

Five phases. Earlier phases unblock later ones. Each phase is self-contained enough to ship independently and leave the repo in a cleaner state.

Across every phase, real-query smoke coverage is part of the completion signal. When a phase adds or broadens parser/query behavior, it must add representative natural-language queries for that new capability or phrasing family to the active phase tuple in `tests/_query_smoke.py`, commit those queries to the repo, and run the matching smoke targets. New behavior is not considered phase-complete if the only proof lives in ad hoc terminal commands or chat history.

The letters map to v1's phases for continuity — A/B/C align with the v1 plan, D is new, and E bundles what v1 called "Phase D — new capability families."

### 5.1 Phase A — Phrasing parity on shipped capabilities

**Goal:** Every capability already listed in `query_catalog.md` should accept question form, search form, and compressed shorthand consistently.

**Scope (what changes):**

- Add search-form and shorthand variants for existing leaderboards, summaries, records, occurrences, streaks, and splits
- Strengthen fuzzy time-word handling where it already partially works (`lately`, `past month`, `recent`)
- Broaden absence phrasing (`X out`, `X didn't play`, `no X`, `sans X`) — `without_player` detection already exists, but not all surface forms route there
- Establish word-order equivalence as an explicit test category

**Where the work lives:**

- `src/nbatools/commands/natural_query.py` — routing predicates in `_finalize_route`
- `src/nbatools/commands/_parse_helpers.py` — intent flag detectors (`wants_*`, `detect_*`)
- `src/nbatools/commands/_matchup_utils.py` — `detect_without_player` phrasing expansion
- `src/nbatools/commands/_date_utils.py` — fuzzy time windows

**What's NOT in scope:**

- new capability families (on/off, lineups, opponent-quality) — those are Phase E
- adding new stat types, routes, or query classes
- centralizing the normalization layer — that's Phase B

**Definition of done:**

- equivalence groups from [`parser/examples.md §7`](../architecture/parser/examples.md) pass as parser tests
- at least 50 paired question/search/shorthand triples route identically
- `query_catalog.md` updated to reflect any surface-form additions

**Tests to run:**

- `make test-parser` (primary)
- `make test-query` (routing regressions)
- `make test-impacted` during iteration

**Reference doc sections to consult:**

- [`parser/specification.md §2`](../architecture/parser/specification.md#2-input-normalization) — aliases
- [`parser/specification.md §6`](../architecture/parser/specification.md#6-time-parsing) — fuzzy time
- [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form) — pairs
- [`parser/examples.md §5.4`](../architecture/parser/examples.md#54-word-order-swaps) — word-order

---

### 5.2 Phase B — Consolidated normalization and codified glossary

**Goal:** One source of truth for alias mapping, fuzzy-term definitions, and product-policy defaults. Pull scattered normalization into a coherent layer.

**Scope (what changes):**

- Consolidate alias mapping into `normalize_text` (or a companion module) so detectors consume a uniform input
- Create a glossary module (or data file) for fuzzy-term definitions: `recently`, `lately`, `past month`, `last couple weeks`, `best games`, `hottest`, `efficient`, `clutch`
- Document every term in [`parser/specification.md §18`](../architecture/parser/specification.md#18-glossary-and-vocabulary) with the current live definition
- Ensure stat-alias table is a shared resource (used by detectors, documented in [`query_catalog.md §2.6`](../reference/query_catalog.md))

**Where the work lives:**

- `src/nbatools/commands/_constants.py` — alias table expansion
- `src/nbatools/commands/_parse_helpers.py` — consume centralized aliases
- `src/nbatools/commands/_date_utils.py` — fuzzy-time resolution using glossary
- new module (e.g. `src/nbatools/commands/_glossary.py`) for fuzzy-term definitions
- [`parser/specification.md §18`](../architecture/parser/specification.md#18-glossary-and-vocabulary) — keep the documented glossary in sync

**What's NOT in scope:**

- opponent-quality buckets (`contenders`, `good teams`) — those ship in Phase E, but their _definitions_ get reserved in the glossary now so Phase E can populate them cleanly
- changing what's already shipped; this is a consolidation phase, not a behavior-change phase

**Definition of done:**

- all alias mapping flows through one resource
- glossary module documents every fuzzy term used anywhere in the parser
- specification's glossary section matches the code
- no detector hardcodes a time-window meaning inline

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-preflight` (because this touches shared infra)

**Reference doc sections to consult:**

- [`parser/specification.md §2.2`](../architecture/parser/specification.md#22-alias-mapping)
- [`parser/specification.md §18`](../architecture/parser/specification.md#18-glossary-and-vocabulary)

---

### 5.3 Phase C — Explicit defaults for underspecified queries

**Goal:** Every underspecified query pattern has a documented default behavior. Defaults are product policy, applied consistently, and changeable without rewriting parser code.

**Scope (what changes):**

- Audit `_build_parse_state` and `_finalize_route` for implicit defaults
- Promote implicit defaults to explicit, named rules
- Ensure each pattern in [`parser/specification.md §15`](../architecture/parser/specification.md#15-defaults-for-underspecified-queries) is either applied consistently or flagged as an open policy decision
- Add notes to the parse state output (`notes` list) when a default was applied, so UI can surface "showing X because..." when useful

**Default rules in scope:**

- `<player> + <timeframe>` → `summary`
- `<team> + <opponent-quality>` → `record` (even though opponent-quality isn't shipped until Phase E — the default rule ships here so Phase E can plug in)
- `<player> + <threshold>` → `occurrence` / `count`
- `"best games" + <subject>` → ranked game logs by Game Score
- `<team> + recently` → recent record + recent summary
- `<metric>` only, no subject → league-wide leaderboard

**Where the work lives:**

- `src/nbatools/commands/natural_query.py` — `_finalize_route` default branches
- `src/nbatools/commands/_parse_helpers.py` — `default_season_for_context` and related
- new helper (or consolidation in an existing one) for default-rule application

**What's NOT in scope:**

- parse-level confidence scoring — that's Phase D
- surfacing alternates — that's Phase D

**Definition of done:**

- every default rule named in [`parser/specification.md §15.2`](../architecture/parser/specification.md#152-defaults-to-formalize) is applied consistently or explicitly marked as unsupported
- the `notes` field on the parse state includes an entry when a default fired
- [`parser/specification.md §15`](../architecture/parser/specification.md#15-defaults-for-underspecified-queries) matches the code

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-impacted` during iteration

**Reference doc sections to consult:**

- [`parser/specification.md §15`](../architecture/parser/specification.md#15-defaults-for-underspecified-queries)
- [`parser/overview.md §5`](../architecture/parser/overview.md#5-product-policy-decisions-to-lock-down-early)

---

### 5.4 Phase D — Confidence, alternates, and canonical parse formalization

**Goal:** The parse state becomes an explicit, versioned contract with a confidence score and optional alternate interpretations.

**Scope (what changes):**

- Add a parse-wide `confidence` field to the parse state
- Add an `intent` enum to the parse state, replacing pure inference from intent-flag combinations
- Add an `alternates` list for medium-confidence parses (top 1–2 alternate parses)
- Extend entity-level ambiguity handling to teams and stats, not just players
- Update `_finalize_route` to populate these new fields
- Update the result envelope to carry confidence and alternate interpretations to the UI

**Where the work lives:**

- `src/nbatools/commands/natural_query.py` — `_build_parse_state` and `_finalize_route`
- `src/nbatools/commands/entity_resolution.py` — extend pattern to more entity types
- `src/nbatools/commands/_natural_query_execution.py` — carry confidence through render
- `src/nbatools/api.py` — QueryResponse envelope (if the shape changes)
- `frontend/src/api/types.ts` and `ResultEnvelope.tsx` — surface alternates in UI

**What's NOT in scope:**

- training a confidence model; heuristic scoring is fine for first pass
- broad UI redesign; the alternate-surface can be minimal

**Definition of done:**

- every parse state carries `intent` (enum), `confidence` (0–1), and `alternates` (list; usually empty)
- at least 10 known ambiguous-query cases surface a reasonable alternate
- the React UI renders "did you mean X" for medium-confidence parses (simple chip or link is enough)
- `QueryResponse` envelope documents the new fields

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-api` (envelope change)
- `make test` (maximum confidence, because envelope change touches multiple surfaces)

**Reference doc sections to consult:**

- [`parser/specification.md §16`](../architecture/parser/specification.md#16-ambiguity-and-confidence)
- [`parser/specification.md §17`](../architecture/parser/specification.md#17-canonical-intermediate-representation)

---

### 5.5 Phase E — New capability families

**Goal:** Add the major user-facing capability families that aren't shipped yet.

Phase E is large and naturally breaks into independent sub-phases that can ship in any order once A/B/C/D are stable.

#### 5.5.1 Opponent-quality buckets

- `against contenders`, `against good teams`, `against top-10 defenses`, `against playoff teams`
- new filter type: `opponent_quality` carrying surface term + resolved definition
- definitions live in the glossary (Phase B) and get populated with real values here
- routes: new or extended team/player routes accepting the filter

#### 5.5.2 On/off queries

- `Jokic on/off`, `Nuggets with Jokic on the floor`, `without Giannis`
- new slots: `lineup_members`, `presence_state`, `minute_minimum`
- new route family: `player_on_off`, `team_with_without_player`
- current shipped scope: single-player parser/routing support with an honest placeholder route
- data access layer: real execution still requires on/off splits or lineup-stint data

#### 5.5.3 Lineup queries

- `best 5-man lineups`, `3-man units with 200+ minutes`, `net rating with Tatum and Brown together`
- new slots: `unit_size`, minute thresholds
- new route family: `lineup_leaderboard`, `lineup_summary`
- current shipped scope: parser/routing support with honest placeholder summary and leaderboard routes
- data access: real execution still requires a lineup data source

#### 5.5.4 Expanded context filters

- clutch, quarter (1st/2nd/3rd/4th), half (1st/2nd), overtime, one-possession games, back-to-backs, rest advantage/disadvantage, nationally televised, starter/bench role
- extensions to existing filter slots; in most cases these slot into existing routes
- some (clutch, starter/bench) may require new data aggregations

#### 5.5.5 Stretch / rolling-window queries

- `hottest 3-game scoring stretch`, `best 5-game stretch by Game Score`
- new route family or an aggregation mode on existing leaderboard routes
- product decision: what metric defines "hot"?

**Cross-cutting guidance for Phase E:**

- each sub-phase should land its own capability catalog update in [`query_catalog.md`](../reference/query_catalog.md)
- each sub-phase should add its examples to [`parser/examples.md`](../architecture/parser/examples.md)
- each sub-phase should include equivalence-group tests for question/search/shorthand forms of its new capabilities
- sub-phases with new routes should touch API and UI envelope if the response shape changes

**Tests to run per sub-phase:**

- `make test-parser` + `make test-query` + `make test-engine` (new computation usually)
- `make test-api` if envelope changed
- `make test` before merging

**Reference doc sections to consult:**

- opponent-quality: [`parser/specification.md §9`](../architecture/parser/specification.md#9-opponent-quality-filters)
- on/off + lineups: [`parser/specification.md §11`](../architecture/parser/specification.md#11-onoff-and-lineup-support)
- expanded contexts: [`parser/specification.md §8`](../architecture/parser/specification.md#8-context-filters)
- stretch queries: [`parser/examples.md §8.4`](../architecture/parser/examples.md#84-stretch--rolling-window-queries-phase-e)

---

## 6. Testing strategy

Align with the existing repo conventions ([`AGENTS.md`](../../AGENTS.md) has the full testing policy).

### 6.1 Equivalence groups as the core parser test

Every phase should add or extend equivalence groups from [`parser/examples.md §7`](../architecture/parser/examples.md#7-equivalence-groups). A passing group means all phrasings in it produce identical parse states (modulo confidence).

### 6.2 Marker-based subset tests

Parser work uses pytest markers `parser` and `query`:

- Phase A: primarily `parser` marker (slot extraction + phrasing)
- Phase B: `parser` (normalization, aliases)
- Phase C: `parser` and `query` (defaults affect routing)
- Phase D: `parser`, `query`, and `api` (envelope change)
- Phase E sub-phases: vary by sub-phase; most touch `parser`, `query`, and `engine`

### 6.3 Failure-mode coverage

Each phase should add at least a handful of explicit failure-mode test cases (from [`parser/examples.md §5`](../architecture/parser/examples.md#5-stress-test-inputs) and [`parser/specification.md §20`](../architecture/parser/specification.md#20-failure-modes)). These should test that the parser fails cleanly rather than guesses wrong.

### 6.4 Real-query smoke is required per phase

Each phase must add or update representative real natural-language smoke cases in `tests/_query_smoke.py` for the capability families or phrasing families it just implemented. Those cases belong in the active phase tuple, are checked into the repo, and are part of the phase's done signal.

Use the smoke harness to protect behavior at the product surface, not just parser internals:

- phase smoke protects the active phase's new behavior and any honest temporary behavior that is part of the shipped user experience
- stable smoke protects durable shipped behavior across phases and catches regressions through the shared CLI/API natural-query paths
- for parser/query-surface work, the normal expectation is to run both `make test-phase-smoke` and `make test-smoke-queries`
- for engine/API/output work, run the smoke targets whenever the change materially affects real natural-query behavior

### 6.5 Logging-driven iteration

After each phase ships, monitor real-user query logs for:

- repeated reformulations (signals a bad first parse)
- low-confidence patterns at high volume
- unsupported shorthand that shows up frequently

Feed learnings back into the next phase's scope.

---

## 7. Guardrails

These apply across every phase.

### 7.1 Do not broaden claims without backing them up

Do not update [`query_catalog.md`](../reference/query_catalog.md) or [`README.md`](../../README.md) to advertise a capability until it is both shipped and tested. Docs describe verified behavior; they don't describe intent.

### 7.2 Do not fake undefined labels

Don't accept `good teams`, `contenders`, `hottest`, `best games`, `clutch`, or similar fuzzy terms as supported unless a definition exists in the glossary. Prefer returning a clear "not supported" than silently guessing.

### 7.3 Prefer small, targeted changes

Per [`AGENTS.md`](../../AGENTS.md), prefer tightening a route over adding a parallel one. Don't let new work create a third copy of existing logic.

### 7.4 Keep the parser UI-agnostic and transport-agnostic

Per [`AGENTS.md`](../../AGENTS.md), parser logic stays in `commands/`, not in CLI wrappers or frontend code. Envelope changes propagate through `api.py` and UI `types.ts` in lockstep.

### 7.5 Update `query_catalog.md` in the same pass

When a phase ships new capability, [`query_catalog.md`](../reference/query_catalog.md) gets updated in the same session, not later.

### 7.6 Keep parser and test coverage in sync

Per [`AGENTS.md`](../../AGENTS.md): a feature is not shipped if docs changed but tests didn't. Each phase adds test coverage commensurate with its scope.

### 7.7 Do not merge unrelated refactors into capability work

Refactors that aren't motivated by the phase's scope should land separately, so capability regressions can be bisected cleanly.

---

## 8. Out of scope for this plan

The following are deliberately excluded and should be addressed in separate planning docs if needed:

- **Storage-layer changes.** CSV + pandas stays the current model per AGENTS.md.
- **ML-based intent classification.** The parser remains heuristic; confidence scoring (Phase D) is heuristic, not model-backed.
- **Query personalization.** Per-user history-aware parsing is not planned here.
- **Multi-intent queries.** "Compare Jokic and Embiid and show Jokic's best games" — compound intents in one query are out of scope.
- **Conversational multi-turn.** "Now show me against Lakers" as a follow-up to a prior query is out of scope.

---

## 9. Work queue convention

This plan is directional. Sequenced, PR-sized work items for the active phase live in a companion work-queue file in the same directory: `phase_a_work_queue.md`, `phase_b_work_queue.md`, etc.

### 9.1 Why separate

The plan stays stable — its scope and phases rarely change. Work queues change often: tasks complete, learnings reshape priorities, new items get discovered. Keeping them separate means the plan doesn't churn when tactical work does.

### 9.2 Queue lifecycle

- **Drafted** when its phase activates — roughly when the prior phase is ~80% complete (so there's no dead time between phases, and learnings from the prior phase can inform the new queue's scope).
- **Worked** one item at a time. Each item has acceptance criteria and test commands; when done, the item is checked off in the queue file and committed.
- **Closed** when every item is checked and the queue's final meta-task has done one of the following:
  - drafted the next queue/phase toward end-to-end completion, or
  - written an explicit review-handoff instruction that names the files/artifacts to review, who should review them, and the immediate next action after review.

A queue must not close while leaving partial, placeholder, or unfiltered capability families without an explicit continuation path.

### 9.3 Required smoke content in queue items

Work-queue items that change real natural-query behavior must say so explicitly. This is part of the queue-writing convention, not an optional reminder.

For any item that adds or changes real parser/query behavior, the queue entry must:

- identify representative real natural-language queries for the new capability or phrasing family
- add or update those queries in the active phase tuple in `tests/_query_smoke.py`
- include `make test-phase-smoke` in **Tests to run**
- include `make test-smoke-queries` in **Tests to run** when the work touches parser/routing/shared natural-query execution or could regress durable shipped behavior

Research-only, docs-only, and internal refactor items that do not materially affect real natural-query behavior should not add meaningless smoke commands.

### 9.4 Self-propagation

The **final task in every work queue** must do one of two things:

1. draft the next queue/phase toward end-to-end completion, or
2. create an explicit review-handoff instruction for authoring that next queue, including the required files/artifacts and the immediate action after review.

The active queue for a plan is the queue that the plan explicitly names as the next active continuation step. Do not infer global product completion from the absence of unchecked items inside a subsystem-only queue.

### 9.5 Reusable agent prompt

Any agent — Claude Code, Cursor, a repo-level Claude, etc. — can work a phase with this prompt:

> Read the relevant plan doc and the active work queue that the plan explicitly identifies as next. Find the next unchecked item. Review the relevant reference docs it cites. Execute the item according to its acceptance criteria, including any required `tests/_query_smoke.py` updates. Run the specified test commands. When everything passes, check the item off in the work queue, update any docs the item requires.

No new prompt is needed for phase transitions — the final task of each queue handles it, either by drafting the next queue or by producing the explicit review-handoff that immediately precedes the next queue.

### 9.6 When the plan itself needs updating

If a phase's work uncovers a reason to change the plan's scope, priorities, or guardrails, update the plan in the same session that closes the relevant queue item. Don't let the plan drift silently from the actual direction.

---

## 10. Closure after Phase E

Phase E closes **Part 1 only**: parser/query-surface expansion.

This is not full product completion. The remaining gaps exposed by Phase E are not primarily about parser phrasing, slot extraction, or route selection anymore. They are about **execution/data completion**:

- true clutch filtering needs a play-by-play or equivalent clutch-capable split source
- real on/off results need on-court/off-court split data or locally derived stint data
- real lineup results need lineup-unit or rotation/stint data
- richer schedule-context execution still needs better metadata joins for some filters

The continuation path is now explicit:

- **Part 2 plan:** [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- **Next active queue:** [`phase_f_work_queue.md`](./phase_f_work_queue.md)

This repo must treat Phase A-E as subsystem completion, not final completion.

---

## 11. Document relationships

This plan sits alongside:

| Doc                                                                                          | Role                                               |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **This file**                                                                                | Part 1 plan for parser/query-surface expansion     |
| [`docs/planning/parser_execution_completion_plan.md`](./parser_execution_completion_plan.md) | Part 2 plan for execution/data completion          |
| [`docs/architecture/parser/overview.md`](../architecture/parser/overview.md)                 | Parser design principles                           |
| [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)       | Parser component spec                              |
| [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)                 | Parser example library + equivalence groups        |
| [`docs/reference/query_catalog.md`](../reference/query_catalog.md)                           | Living shipped inventory (update with every phase) |
| [`docs/reference/current_state_guide.md`](../reference/current_state_guide.md)               | Strict verified behavior                           |
| [`docs/reference/query_guide.md`](../reference/query_guide.md)                               | Broader narrative reference                        |
| [`AGENTS.md`](../../AGENTS.md)                                                               | Repo-wide conventions and testing policy           |
| [`docs/planning/roadmap.md`](./roadmap.md)                                                   | Broader repo roadmap (non-parser)                  |

### Update cadence

- **This plan** — Part 1 record. Keep it aligned with what Phase A-E actually accomplished and where it hands off next.
- **`parser_execution_completion_plan.md`** — Part 2 execution/data closure record after Part 1.
- **`query_catalog.md`** — updated in the same session as any shipped capability change.
- **Parser reference docs** — updated when component behavior changes or new capability families are designed.
- **Current state guide** — updated when verified-behavior claims change.
