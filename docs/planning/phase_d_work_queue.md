# Phase D Work Queue

> **Role:** Sequenced, PR-sized work items for Phase D of [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — _Confidence, alternates, and canonical parse formalization._
>
> **How to work this file:** Find the first unchecked item below. Review the reference docs it cites. Execute per its acceptance criteria. Run the test commands. Check the item off, commit. Repeat. When every item above is checked, work the final meta-task.
>
> **Do not skip ahead** unless an earlier item is genuinely blocked. Items are ordered to minimize rework — later items assume earlier ones are done.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Phase C retrospective (context for Phase D)

Phase C formalized all implicit defaults in `_finalize_route`:

- Cataloged 20 default branches in `phase_c_defaults_inventory.md`
- Extracted 5 named default rules into `_default_rules.py` with `(should_fire, notes_message)` signatures
- Added `notes` entries when defaults fire so the UI can surface "showing X because..."
- Synced spec §15 with all implemented defaults (12 documented, 3 remaining unshipped)

Phase D can build on this foundation: default-rule firing signals feed directly into confidence scoring, and the named-rules module provides clean integration points.

---

## 1. `[x]` Define `QueryIntent` labels and map existing routes

**Why:** The parse state currently infers intent from ~15 boolean flags (`summary_intent`, `finder_intent`, `count_intent`, etc.) and route name strings. Phase D needs an explicit `intent` field. This item formalizes the shipped broad intent buckets and adds them to the parse state without changing any routing behavior.

**Scope:**

- Define a `QueryIntent` string-constant class covering the shipped broad intent buckets: `summary`, `comparison`, `split_summary`, `finder`, `count`, `leaderboard`, `streak`, `unsupported`
- Map existing routes into those broad buckets via `route_to_intent()`; multiple route families intentionally collapse into the same intent (for example, `team_record` and `playoff_history` both map to `summary`)
- Add an `intent` field to the parse state dict, populated at the end of `_finalize_route` based on the selected route
- Create a `route_to_intent()` mapping function so the mapping is explicit and testable
- The `intent` field is informational only — routing logic remains unchanged

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — `QueryIntent` label definition
- `src/nbatools/commands/natural_query.py` — populate `parsed["intent"]` in `_finalize_route`
- `tests/` — verify intent field is populated correctly for representative queries

**Acceptance criteria:**

- Every successful parse state includes an `intent` field with a valid broad `QueryIntent` value
- At least 15 test cases verify intent mapping across representative routes / route families
- Existing tests pass with no behavior change (intent is additive)

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §17.2`](../architecture/parser/specification.md#172-proposed-additions)
- `src/nbatools/commands/natural_query.py` — `_finalize_route` route assignments

---

## 2. `[x]` Design and implement heuristic confidence scoring

**Why:** The parse state needs a parse-wide `confidence` score (0–1) so downstream consumers (API, UI) can decide how to present results. This item implements the scoring function using heuristic signals — no ML.

**Scope:**

- Create a `compute_parse_confidence(parsed: dict) -> float` function in a new `_confidence.py` module
- Scoring signals (each contributes to or detracts from confidence):
  - **Entity resolution confidence**: `confident` → high, `ambiguous` → low, `none` → medium (may be valid for league-wide queries)
  - **Existing entity_ambiguity field**: `parsed["entity_ambiguity"]` is already populated by the parser when a player reference matches multiple candidates. When present, this is a strong low-confidence signal — use it directly rather than re-inventing entity-confidence detection.
  - **Explicit intent signal**: presence of explicit intent flags (`summary_intent`, `finder_intent`, etc.) → higher confidence than default-rule routing
  - **Default rule fired**: any `notes` entry starting with `"default:"` → moderate confidence penalty
  - **Stat specified**: explicit stat → higher confidence; stat fallback to `pts` → penalty
  - **Timeframe specified**: explicit season/date/last-N → higher; no time scope → penalty
  - **Threshold clarity**: explicit threshold with operator → high; fuzzy threshold → lower
- Populate `parsed["confidence"]` at the end of `_finalize_route`
- Confidence is informational — does not change routing behavior

**Files likely touched:**

- `src/nbatools/commands/_confidence.py` (new)
- `src/nbatools/commands/natural_query.py` — call `compute_parse_confidence` and set `parsed["confidence"]`
- `tests/test_parse_confidence.py` (new)

**Acceptance criteria:**

- Every parse state includes a `confidence` float between 0.0 and 1.0
- High-confidence queries (explicit intent + entity + timeframe) score > 0.85
- Medium-confidence queries (default-routed, partial entity) score 0.60–0.85
- Low-confidence queries (no entity, no intent, no timeframe) score < 0.60
- At least 20 test cases across the confidence tiers
- Existing tests pass with no behavior change

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §16.2`](../architecture/parser/specification.md#162-parse-level-confidence-proposed)
- `src/nbatools/commands/_default_rules.py` — default-rule signals

---

## 3. `[x]` Extend entity-level ambiguity to teams and stats

**Why:** `entity_resolution.py` currently handles player ambiguity (confidence: `confident` / `ambiguous` / `none`) but team and stat references have no equivalent. "OKC" is unambiguous, but "Washington" could be Wizards or Nationals context; stat aliases like "boards" are unambiguous but arbitrary abbreviations might not be.

**Scope:**

- Add a `resolve_team()` function (or extend existing team detection) that returns a `ResolutionResult`-style output with confidence
- Add a `resolve_stat()` function that validates stat aliases and flags unrecognized stat references as ambiguous rather than silently falling back to `pts`
- Wire the new resolution results into `_build_parse_state` so their confidence feeds into the parse-wide confidence score (item 2)
- When team/stat is ambiguous, set `entity_ambiguity` with appropriate type

**Files likely touched:**

- `src/nbatools/commands/entity_resolution.py` — new `resolve_team`, `resolve_stat` functions
- `src/nbatools/commands/natural_query.py` — `_build_parse_state` uses new resolution
- `src/nbatools/commands/_confidence.py` — consume team/stat confidence in scoring
- `tests/test_entity_resolution.py` — new test cases

**Acceptance criteria:**

- Team resolution returns confidence levels (at minimum: confident, none)
- Stat resolution returns confidence levels (confident for known aliases, none for unrecognized)
- `entity_ambiguity` is set for ambiguous team/stat references
- Parse-wide confidence score incorporates team/stat entity confidence
- At least 10 test cases for new entity resolution paths
- Existing tests pass with no behavior change

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-impacted`

**Reference docs to consult:**

- [`parser/specification.md §16.1`](../architecture/parser/specification.md#161-entity-level-ambiguity-already-shipped)
- `src/nbatools/commands/entity_resolution.py` — existing `ResolutionResult` pattern

---

## 4. `[x]` Implement alternates for medium-confidence parses

**Why:** When confidence is medium (0.60–0.85), the parser should surface the top alternate interpretation so the UI can offer "did you mean X?" This item adds the alternates mechanism.

**Scope:**

- Add an `alternates` field to the parse state (list of dicts, each with `intent`, `route`, `description`, `confidence`)
- Create a `generate_alternates(parsed: dict) -> list[dict]` function in `_confidence.py`
- For common ambiguous patterns (from spec §16.3), generate the alternate parse:
  - `Celtics recently` → primary: team summary; alternate: team record
  - `Tatum vs Knicks` → primary: head-to-head; alternate: player summary with opponent filter
  - `Jokic triple doubles` → primary: occurrence count; alternate: game finder
  - `best games Booker` → primary: top games; alternate: season-high finder
- Alternates are generated only when confidence < 0.85 and a known ambiguity pattern matches
- Limit to top 1–2 alternates

**Files likely touched:**

- `src/nbatools/commands/_confidence.py` — `generate_alternates` function
- `src/nbatools/commands/natural_query.py` — populate `parsed["alternates"]`
- `tests/test_parse_confidence.py` — alternates test cases

**Acceptance criteria:**

- `parsed["alternates"]` is populated for medium-confidence queries
- At least 5 known ambiguous patterns generate a meaningful alternate
- High-confidence queries have empty alternates lists
- Each alternate includes `intent`, `route`, `description`, `confidence`
- Existing tests pass with no behavior change

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §16.3`](../architecture/parser/specification.md#163-common-ambiguous-inputs)
- [`parser/specification.md §16.4`](../architecture/parser/specification.md#164-disambiguation-strategy)

---

## 5. `[x]` Add `confidence`, `intent`, and `alternates` to the API envelope

**Why:** The engine now produces confidence, intent, and alternates, but the API response doesn't expose them. This item threads the new fields through the `QueryResponse` envelope so the frontend can consume them.

**Scope:**

- Add `confidence: float | None`, `intent: str | None`, and `alternates: list[dict]` to the `QueryResponse` Pydantic model
- Populate them from the parse state in the query endpoint handler
- Add corresponding TypeScript interfaces in `frontend/src/api/types.ts`
- Fields are optional with sensible defaults (confidence=None, intent=None, alternates=[]) so existing clients don't break

**Files likely touched:**

- `src/nbatools/api.py` — `QueryResponse` model
- `src/nbatools/commands/_natural_query_execution.py` — thread fields through
- `frontend/src/api/types.ts` — TypeScript interface updates
- `tests/test_api.py` — verify new fields in API response
- `tests/test_result_contract.py` — verify envelope shape

**Acceptance criteria:**

- API response includes `confidence`, `intent`, and `alternates` fields
- Fields are optional — omitting them doesn't break existing clients
- At least 5 API test cases verify the new fields
- TypeScript types are updated and frontend builds cleanly (`npm run build`)

**Tests to run:**

- `make test-api`
- `make test-output`
- `cd frontend && npm run build`

**Reference docs to consult:**

- [`parser/specification.md §17.2`](../architecture/parser/specification.md#172-proposed-additions)
- `src/nbatools/api.py` — existing `QueryResponse` model
- `frontend/src/api/types.ts` — existing TypeScript interfaces

---

## 6. `[x]` Surface alternates in the React UI

**Why:** The API now exposes alternates, but the UI doesn't render them. This item adds a minimal "did you mean" display for medium-confidence parses.

**Scope:**

- Add a `DidYouMean` component (or extend `ResultEnvelope.tsx`) that renders alternates as clickable chips/links
- When clicked, re-query with the alternate's description text in this first pass; a future follow-up can carry a canonical query string or structured target
- Show confidence indicator (optional — could be as simple as showing/hiding the "did you mean" section based on confidence threshold)
- Keep it minimal — this is a functional first pass, not a design overhaul

**Files likely touched:**

- `frontend/src/components/ResultEnvelope.tsx` or new `DidYouMean.tsx`
- `frontend/src/App.tsx` — wire up alternate re-query
- `frontend/src/App.css` — minimal styling
- `frontend/src/test/` — component test for DidYouMean

**Acceptance criteria:**

- Medium-confidence queries show "Did you mean: [alternate description]?" below the result envelope
- Clicking an alternate triggers a new query via the alternate description text
- High-confidence queries do not show alternates
- Component renders correctly with 0, 1, and 2 alternates
- Frontend builds cleanly (`npm run build`)

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- [`parser/specification.md §16.4`](../architecture/parser/specification.md#164-disambiguation-strategy)
- `frontend/src/components/ResultEnvelope.tsx` — existing envelope rendering

---

## 7. `[x]` Sync spec §16 and §17 with implemented behavior

**Why:** After items 1–6, spec §16 (ambiguity/confidence) and §17 (canonical IR) should mirror the implementation exactly. This is the documentation-lockstep step.

**Scope:**

- Update spec §16.2 from "proposed" to "implemented" with the actual scoring formula
- Update spec §16.3 with any new ambiguous patterns discovered during implementation
- Update spec §17.1 to include `intent`, `confidence`, and `alternates` in the current parse state shape
- Move §17.2 additions to §17.1 (they're no longer proposed)
- Update §17.3 worked example to include the new fields
- Update `docs/reference/query_catalog.md` if any new query surface was added

**Files likely touched:**

- `docs/architecture/parser/specification.md` — §16 and §17
- `docs/reference/query_catalog.md` — if query surface changed

**Acceptance criteria:**

- §16.2 documents the implemented confidence scoring formula and tiers
- §17.1 includes `intent`, `confidence`, and `alternates` as current (not proposed) fields
- §17.3 worked example includes the new fields
- All examples in §16.3 and §15.3 are verified against actual `parse_query` output

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `src/nbatools/commands/_confidence.py` — actual scoring implementation
- `src/nbatools/commands/_constants.py` — `QueryIntent` labels

---

## 8. `[x]` Phase D retrospective and Phase E work queue draft

**Why:** Self-propagating final task. Ensures learnings are captured and the next phase is scoped before this one closes.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals
- Review the plan's Phase E scope ([`query_surface_expansion_plan.md §5.5`](./query_surface_expansion_plan.md)) against what Phase D actually accomplished
- If the plan needs changes, edit [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) in the same session
- Draft `phase_e_work_queue.md` following the same structure as this file
- Phase E is large (5 sub-phases in the plan); the work queue should sequence them and break each into PR-sized items

**Files likely touched:**

- `docs/planning/phase_e_work_queue.md` (new)
- `docs/planning/query_surface_expansion_plan.md` (if scope change)
- `docs/planning/phase_d_work_queue.md` (check this item as done)

**Acceptance criteria:**

- `phase_e_work_queue.md` exists and covers Phase E's scope
- Every item in the new queue is PR-sized with clear acceptance criteria
- The final item is the meta-task "retrospective + draft Phase F work queue"
- This item in `phase_d_work_queue.md` is checked off

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_surface_expansion_plan.md §9`](./query_surface_expansion_plan.md) — work queue convention
- [`query_surface_expansion_plan.md §5.5`](./query_surface_expansion_plan.md) — Phase E scope
- This file as a structural template

---

## Phase D retrospective

### What went well

- **Broad `QueryIntent` labels + `ROUTE_TO_INTENT` mapping** (item 1) were clean — a plain class with string constants was simpler than a Python Enum and equally effective. Multiple route families intentionally collapse into 8 coarse buckets, and `route_to_intent()` handles the count/finder duality with a single `count_intent` flag.
- **Heuristic confidence scoring** (item 2) landed with a straightforward additive model (base 0.70, signal adjustments, clamped to [0,1]). The scoring formula is transparent and easy to tune — no ML complexity needed for the current query surface.
- **Entity resolution extension** (item 3) for teams and stats was lightweight — `resolve_team()` and `resolve_stat()` return confidence signals that feed directly into `compute_parse_confidence` without restructuring the parse pipeline.
- **Alternates generation** (item 4) works well for the known ambiguity patterns. The pattern-matching approach (5 specific patterns in `generate_alternates`) is simple and maintainable — each pattern is ~10 lines with clear trigger conditions.
- **API envelope threading** (item 5) — adding optional fields with sensible defaults meant zero breaking changes for existing consumers. Pydantic's `Optional` fields with defaults made this trivial.
- **DidYouMean UI** (item 6) — clickable chips that re-query with the alternate description. Minimal implementation, functional first pass.
- **Spec sync** (item 7) — updating §16 and §17 was straightforward because items 1–6 had built the implementation incrementally. Also fixed a pre-existing import error in `test_entity_resolution.py`.

### What was harder than expected

- **Confidence calibration** — initial tier boundaries (0.85/0.60) produce reasonable results but some queries feel miscalibrated. For example, `most points this season` scores 0.82 (medium) even though it's unambiguous — the penalty comes from no entity being present, which is correct for a league-wide leaderboard but feels counterintuitive.
- **Alternates coverage** — only 5 patterns are coded in `generate_alternates`. Many medium-confidence queries (0.60–0.85) don't match any pattern and get no alternates even though the user might benefit from seeing one. Expanding pattern coverage is straightforward but labor-intensive.

### What Phase D didn't cover (residuals for later phases)

- **Alternate transport**: the UI currently re-queries alternates by submitting the alternate's human-readable description text. That's acceptable as a lightweight first pass, but a future pass should carry a canonical query string or structured target so alternates are not coupled to display wording.
- **Unsupported-query messaging**: queries that raise `ValueError` (like `"scoring"` alone) don't produce a parse state at all — they crash before confidence/alternates can run. Phase E or a dedicated error-handling pass should catch these and return a structured "unsupported" response with confidence=0 and helpful suggestions.
- **Session-context disambiguation** (§16.5): "prefer the parse consistent with recent query context" is spec'd but not implemented — would require stateful session tracking, which is out of scope for the current stateless parser.
- **ML-based confidence**: the heuristic model is adequate for the current surface but will plateau as query diversity grows. A future phase could train a lightweight classifier on (query, correct_route) pairs.
- **Entity-resolution anomalies**: wrong-subject detection in two-player queries and team resolution from player city remain unfixed from Phase A.

### Scope adjustments for Phase E

Phase E is large (5 sub-phases in the plan). The work queue should:

1. Start with **expanded context filters** (§5.5.4) — these extend existing routes and don't require new data sources, making them the lowest-risk entry point.
2. **Opponent-quality buckets** (§5.5.1) second — definitions are already reserved in the glossary, and the filter mechanism is similar to context filters.
3. **On/off queries** (§5.5.2) and **lineup queries** (§5.5.3) third — these require new data access layers and are higher-risk.
4. **Stretch / rolling-window queries** (§5.5.5) last — product definition of "hot" isn't settled.

Each sub-phase should be independently shippable.

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase D is complete. The draft of `phase_e_work_queue.md` from item 8 is the handoff artifact.
