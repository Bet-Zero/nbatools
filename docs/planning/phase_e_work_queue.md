# Phase E Work Queue

> **Role:** Sequenced, PR-sized work items for Phase E of [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — _New capability families._
>
> **How to work this file:** Find the first unchecked item below. Review the reference docs it cites. Execute per its acceptance criteria. Run the test commands. Check the item off, commit. Repeat. When every item above is checked, work the final meta-task.
>
> For any item here that changes real natural-query behavior, updating `PHASE_E_QUERY_SMOKE_CASES` in `tests/_query_smoke.py` and running the listed smoke targets is part of done.
>
> **Do not skip ahead** unless an earlier item is genuinely blocked. Items are ordered to minimize rework — later items assume earlier ones are done.
>
> **⚠️ Data-access caveat:** Items 5–10 (on/off, lineups, stretches) require new data sources or aggregation layers that may not exist yet. If the data layer is missing, scope the parser/routing work first and stub the engine call, then add a follow-up item to wire in the data. Do not block parser progress on data-layer decisions.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Phase D retrospective (context for Phase E)

Phase D formalized the parser's confidence, alternates, and canonical parse state:

- Defined a broad `QueryIntent` label set with 8 intent labels and `ROUTE_TO_INTENT` mapping
- Implemented heuristic confidence scoring in `_confidence.py` (base 0.70, signal adjustments)
- Extended entity resolution to teams (`resolve_team`) and stats (`resolve_stat`)
- Added alternates generation for 5 known ambiguity patterns
- Threaded `confidence`, `intent`, and `alternates` through the API envelope and React UI
- Synced spec §16 and §17 to match the implementation exactly

Phase E can now add new capability families knowing that each new route will automatically get intent classification, confidence scoring, and (where applicable) alternates.

---

## Sub-phase E1: Expanded context filters

Items 1–4 add context filters that extend existing routes. Items 2–4 are the lowest-risk additions because they mainly add filter slots that existing engine routes can consume. Item 1 (`clutch`) is only partially landed today: parser-side detection exists, but true clutch filtering still depends on play-by-play-backed data the current layer does not expose.

---

## 1. `[~]` Add `clutch` context filter

**Why:** Parser-side `clutch` recognition has landed, but true clutch filtering has not. Current behavior detects clutch phrasing, sets `clutch=True` in the parse state, and appends a note that results are unfiltered because play-by-play clutch splits are not available in the current data layer.

**Scope:**

- Keep the product-policy definition of `clutch` pinned in `_glossary.py`: last 5 minutes of 4th quarter or OT, score within 5 points (NBA's official definition)
- Keep the `clutch` boolean slot in the parse state, detected from surface forms: `clutch`, `in the clutch`, `clutch time`, `late-game`
- Surface a user-facing note when `clutch` is detected explaining that true clutch splits are not yet available and results are unfiltered
- Defer real route-level filtering / execution until a play-by-play-backed data source or aggregation layer exists
- Keep glossary / queue / spec wording honest: parser recognition shipped; true clutch filtering not yet shipped

**Files likely touched:**

- `src/nbatools/commands/_glossary.py` — update clutch entry
- `src/nbatools/commands/_parse_helpers.py` — `detect_clutch` helper
- `src/nbatools/commands/natural_query.py` — `_build_parse_state` + `_finalize_route`
- `tests/test_natural_query_parser.py` — clutch detection / note coverage

**Acceptance criteria:**

- `parse_query("Tatum clutch stats")` includes `clutch=True` in the parse state
- Surface forms `clutch`, `in the clutch`, `clutch time`, `late-game` all set the slot
- A user-facing note explains that results are currently unfiltered because true clutch splits are not available yet
- Glossary / queue wording does not claim true clutch filtering is fully shipped
- At least 5 parser tests cover clutch detection and the unfiltered-results note
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative clutch queries that assert the current honest temporary behavior through the real query path

**Remaining to reach `[x]`:**

- Thread `clutch` through `route_kwargs` as a real filter, not just parse-state metadata
- Execute true clutch filtering against play-by-play or another data source that can actually identify clutch possessions / splits
- Flip glossary / spec / queue shipped status only after filtered clutch results are real

**Tests to run:**

- `make test-parser`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §8.2`](../architecture/parser/specification.md#82-not-yet-shipped)
- `src/nbatools/commands/_glossary.py` — reserved clutch entry

---

## 2. `[x]` Add quarter and half context filters

**Why:** "4th quarter scoring", "first half stats", "3rd quarter collapse" — quarter/half filters are commonly requested and straightforward to detect.

**Scope:**

- Add a `quarter` slot (values: `1`, `2`, `3`, `4`, `OT`) and a `half` slot (values: `first`, `second`)
- Detect surface forms: `1st quarter`, `2nd quarter`, `3rd quarter`, `4th quarter`, `first half`, `second half`, `overtime`, `OT`
- Wire through to existing routes as filter parameters
- Document engine-layer requirements (quarter-level splits may need a different data aggregation than full-game logs)

**Files likely touched:**

- `src/nbatools/commands/_parse_helpers.py` — `detect_quarter`, `detect_half`
- `src/nbatools/commands/natural_query.py` — `_build_parse_state` + route kwargs
- Engine route files — accept quarter/half filters

**Acceptance criteria:**

- `parse_query("LeBron 4th quarter scoring")` includes `quarter="4"` in the parse state
- `parse_query("Celtics first half stats")` includes `half="first"`
- `overtime` / `OT` surface forms set `quarter="OT"`
- At least 6 parser tests covering quarter/half detection
- Engine accepts the filter (even if data layer needs follow-up)
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative quarter/half queries for the newly supported surface forms

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §8.2`](../architecture/parser/specification.md#82-not-yet-shipped)

---

## 3. `[x]` Add game-context filters (B2B, rest, one-possession, nationally televised)

**Why:** Schedule-context filters extend the existing home/away pattern. "Lakers on back-to-backs", "Jokic with rest advantage", "one-possession games".

**Scope:**

- Add slots: `back_to_back` (boolean), `rest_days` (e.g., `advantage`, `disadvantage`, or specific count), `one_possession` (boolean), `nationally_televised` (boolean)
- Detect surface forms: `back-to-back`, `b2b`, `second of a back-to-back`, `rest advantage`, `rest disadvantage`, `one-possession games`, `nationally televised`, `on national TV`
- Wire through to existing routes
- `b2b` is listed as "partial" in spec §8.1 — audit current state and complete if needed

**Files likely touched:**

- `src/nbatools/commands/_parse_helpers.py` — detection helpers
- `src/nbatools/commands/natural_query.py` — parse state + route kwargs

**Acceptance criteria:**

- `parse_query("Lakers on back-to-backs")` includes `back_to_back=True`
- `parse_query("Jokic with rest advantage")` includes relevant rest slot
- At least 6 parser tests
- No regressions in existing B2B handling
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative B2B, rest, one-possession, or national-TV queries for the new filters

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §8`](../architecture/parser/specification.md#8-context-filters)

---

## 4. `[ ]` Add starter/bench role filter

**Why:** "As a starter", "off the bench", "bench scoring" — role-based filters are a common request.

**Scope:**

- Add a `role` slot (values: `starter`, `bench`)
- Detect surface forms: `as starter`, `as a starter`, `starting`, `off the bench`, `bench`, `coming off the bench`, `reserve`
- Wire through to existing routes

**Files likely touched:**

- `src/nbatools/commands/_parse_helpers.py` — `detect_role`
- `src/nbatools/commands/natural_query.py` — parse state + route kwargs

**Acceptance criteria:**

- `parse_query("Brunson off the bench")` includes `role="bench"`
- `parse_query("LeBron as a starter stats")` includes `role="starter"`
- At least 4 parser tests
- No confusion with team-level "bench" references
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative starter/bench queries for the shipped role filter behavior

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §8.2`](../architecture/parser/specification.md#82-not-yet-shipped)

---

## Sub-phase E2: Opponent-quality buckets

---

## 5. `[ ]` Define opponent-quality product policy and wire filter

**Why:** "Against good teams", "vs contenders", "against top-10 defenses" — the most requested filter family not yet shipped. Definitions were reserved in the glossary during Phase B; now they need real values.

**Scope:**

- Define concrete product-policy definitions in `_glossary.py` for each opponent-quality term:
  - `contenders` / `good teams` / `top teams` → e.g., top 6 in conference by record
  - `playoff teams` → teams with playoff-qualifying record
  - `teams over .500` → literal win percentage > .500
  - `top-10 defenses` → top 10 by defensive rating
- Add an `opponent_quality` structured slot to the parse state (per spec §9.2: carries `surface_term` + `definition`)
- Detect surface forms: `against contenders`, `against good teams`, `vs top teams`, `against playoff teams`, `against teams over .500`, `against top-10 defenses`
- Wire the filter through to existing routes
- Engine: resolve opponent_quality to a list of team codes at query time using current standings/ratings data

**Files likely touched:**

- `src/nbatools/commands/_glossary.py` — populate opponent-quality definitions
- `src/nbatools/commands/_parse_helpers.py` — `detect_opponent_quality`
- `src/nbatools/commands/natural_query.py` — parse state + route kwargs
- Engine files — resolve quality bucket to team list

**Acceptance criteria:**

- `parse_query("Jokic against contenders")` includes an `opponent_quality` slot with `surface_term="contenders"` and a resolved definition
- All 6 surface forms from spec §9 are detected
- Glossary entries updated to `shipped=True` with concrete definitions
- At least 8 parser tests
- At least 2 end-to-end query tests showing filtered results
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative opponent-quality queries that cover the newly shipped filter family

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §9`](../architecture/parser/specification.md#9-opponent-quality-filters)
- `src/nbatools/commands/_glossary.py` — reserved opponent-quality entries

---

## 6. `[ ]` Update query catalog and examples for context + opponent-quality filters

**Why:** Documentation lockstep for items 1–5. Every new filter needs catalog and example entries.

**Scope:**

- Add context filters (clutch, quarter, half, B2B, rest, role) to `query_catalog.md` with example queries
- Add opponent-quality filters to `query_catalog.md`
- Add equivalence-group examples to `parser/examples.md` for each new filter
- Update spec §8.1 to move shipped filters from §8.2

**Files likely touched:**

- `docs/reference/query_catalog.md`
- `docs/architecture/parser/examples.md`
- `docs/architecture/parser/specification.md` — §8

**Acceptance criteria:**

- Every new filter is documented in the catalog with at least 2 example queries
- At least 3 new equivalence groups in `parser/examples.md`
- Spec §8.1/§8.2 accurately reflects shipped vs. unshipped

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_catalog.md`](../reference/query_catalog.md)
- [`parser/examples.md §7`](../architecture/parser/examples.md#7-equivalence-groups)

---

## Sub-phase E3: On/off and lineup queries

---

## 7. `[ ]` Reconnaissance: audit data layer for on/off and lineup support

**Why:** On/off and lineup queries require data that may not exist in the current dataset. Before building parser/routing, we need to know what data is available and what gaps exist.

**Scope:**

- Audit `data/` directory and data loading code for on/off split data
- Audit for lineup-level data (2-man, 3-man, 5-man unit stats)
- Document what's available, what format, and what's missing
- Produce an inventory in `docs/planning/phase_e_data_inventory.md`

**Files likely touched:**

- `docs/planning/phase_e_data_inventory.md` (new)
- No code changes — reconnaissance only

**Acceptance criteria:**

- Data availability for on/off splits is documented
- Data availability for lineup stats is documented
- Missing data sources are identified with suggested acquisition strategies
- Clear recommendation on which items can proceed with existing data

**Tests to run:**

- None (reconnaissance only)

**Reference docs to consult:**

- [`parser/specification.md §11`](../architecture/parser/specification.md#11-onoff-and-lineup-support)
- `src/nbatools/commands/` — existing data access patterns

---

## 8. `[ ]` Add on/off query intent and routing

**Why:** "Jokic on/off", "Nuggets with Jokic on the floor" — a new intent family. Parser work can proceed even if the data layer needs follow-up.

**Scope:**

- Add `QueryIntent.ON_OFF` to the intent enum
- Add new slots: `lineup_members` (list), `presence_state` (on/off/both)
- Detect surface forms: `on/off`, `with X on the floor`, `without X on the floor`, `X on court`, `X sitting`
- Add new route: `player_on_off` (or `team_with_without_player`)
- Stub engine implementation if data layer is incomplete

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — new intent, route mapping
- `src/nbatools/commands/_parse_helpers.py` — `detect_on_off`
- `src/nbatools/commands/natural_query.py` — routing
- New engine route file (or stub)

**Acceptance criteria:**

- `parse_query("Jokic on/off")` routes to `player_on_off` with correct slots
- `parse_query("Nuggets without Jokic on the floor")` sets `presence_state="off"`
- At least 8 parser tests
- Route exists (even if engine returns a placeholder)
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative on/off queries that assert the current shipped behavior or honest placeholder path

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §11`](../architecture/parser/specification.md#11-onoff-and-lineup-support)

---

## 9. `[ ]` Add lineup query intent and routing

**Why:** "Best 5-man lineups", "3-man units with 200+ minutes" — a new intent family.

**Scope:**

- Add `QueryIntent.LINEUP` to the intent enum
- Add new slots: `unit_size` (2/3/5), `minute_minimum`
- Detect surface forms: `lineups`, `5-man lineups`, `3-man units`, `2-man combos`, `lineup with X and Y`
- Add new routes: `lineup_leaderboard`, `lineup_summary`
- Stub engine implementation if data layer is incomplete

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — new intent, route mapping
- `src/nbatools/commands/_parse_helpers.py` — `detect_lineup_query`
- `src/nbatools/commands/natural_query.py` — routing
- New engine route file (or stub)

**Acceptance criteria:**

- `parse_query("best 5-man lineups this season")` routes to `lineup_leaderboard` with `unit_size=5`
- `parse_query("3-man units with 200+ minutes")` sets `unit_size=3` and `minute_minimum=200`
- At least 6 parser tests
- Route exists (even if engine returns a placeholder)
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative lineup queries that assert the current shipped behavior or honest placeholder path

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/specification.md §11`](../architecture/parser/specification.md#11-onoff-and-lineup-support)

---

## Sub-phase E4: Stretch / rolling-window queries

---

## 10. `[ ]` Add stretch / rolling-window query intent and routing

**Why:** "Hottest 3-game scoring stretch", "best 5-game stretch by Game Score" — a new aggregation mode.

**Scope:**

- Define product policy: what metric defines "hot" / "best" for a stretch? (Game Score is the leading candidate)
- Add `QueryIntent.STRETCH` to the intent enum (or use an aggregation mode on existing leaderboard)
- Add new slots: `window_size`, `stretch_metric`
- Detect surface forms: `X-game stretch`, `rolling X games`, `hottest stretch`, `best stretch`
- Add new route or aggregation mode

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — new intent or route
- `src/nbatools/commands/_parse_helpers.py` — `detect_stretch_query`
- `src/nbatools/commands/natural_query.py` — routing
- Engine files — rolling-window computation

**Acceptance criteria:**

- `parse_query("hottest 3-game scoring stretch")` routes correctly with `window_size=3`
- `parse_query("best 5-game stretch by Game Score")` sets `stretch_metric="game_score"`
- At least 4 parser tests
- Product-policy decision on "hot" metric is documented in glossary
- `PHASE_E_QUERY_SMOKE_CASES` adds or updates representative stretch queries that cover the new rolling-window behavior

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`parser/examples.md §8.4`](../architecture/parser/examples.md#84-stretch--rolling-window-queries-phase-e)

---

## Sub-phase E5: Documentation and wrap-up

---

## 11. `[ ]` Update query catalog, examples, and spec for all Phase E additions

**Why:** Final documentation lockstep for Phase E. Every new capability needs catalog, example, and spec entries.

**Scope:**

- Update `query_catalog.md` with all new query classes (on/off, lineup, stretch) and filters
- Update `parser/examples.md` with equivalence groups for new capabilities
- Update spec §8, §9, §11 to reflect shipped status
- Update spec §17.2 if new intents were added to `QueryIntent`

**Files likely touched:**

- `docs/reference/query_catalog.md`
- `docs/architecture/parser/examples.md`
- `docs/architecture/parser/specification.md`

**Acceptance criteria:**

- Every new capability is documented in the catalog
- Every new query class has equivalence-group examples
- Spec sections accurately reflect shipped vs. unshipped status

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- All Phase E items above

---

## 12. `[ ]` Phase E retrospective and Phase F work queue draft

**Why:** Self-propagating final task. Ensures learnings are captured and the next phase (if any) is scoped.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals
- Assess whether a Phase F is needed (the expansion plan doesn't define one — Phase E is the last planned phase)
- If further work is warranted, draft a `phase_f_work_queue.md` or update the expansion plan with a closing statement
- Check this item off

**Files likely touched:**

- `docs/planning/phase_e_work_queue.md` (check this item)
- `docs/planning/query_surface_expansion_plan.md` (closing statement or Phase F scope)
- `docs/planning/phase_f_work_queue.md` (if needed)

**Acceptance criteria:**

- Retrospective captures outcomes, surprises, and residuals
- Decision on Phase F is documented
- This item is checked off

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md)
- This file as the Phase E record

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase E is complete. Sub-phases (E1–E5) can be worked in order. Items within each sub-phase are sequential.

If any item is skipped (`[-]`), note the reason inline so the reason survives in git history.
