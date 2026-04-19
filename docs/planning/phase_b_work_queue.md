# Phase B Work Queue

> **Role:** Sequenced, PR-sized work items for Phase B of [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — _Consolidated normalization and codified glossary._
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

## Phase A retrospective

### What went well

- **Equivalence-group test infrastructure** (item 1) paid off immediately — every subsequent item used it, and failure messages point straight at the diverging keys.
- **Incremental catalog updates** during each item kept the documentation burden low for item 12.
- **Verb-phrase summary triggers** (item 4) and **verbal-form stat aliases** (item 3) were the two highest-leverage fixes: they unlocked the most equivalence groups with the fewest code changes.
- **Fuzzy time words** (item 9) were straightforward once `extract_date_range` and `extract_last_n` were the clear insertion points.

### What was harder than expected

- **Summary default routing** (item 4) required careful narrowing — the initial `<player> + <timeframe>` rule was too broad and broke 7 existing tests. The guard clause list grew to ~10 exclusions.
- **Absence expansion** (item 10) exposed an entity-resolution issue: when two players appear in a query (e.g., "Maxey when Embiid out"), `detect_player` picks the wrong one, and subject-clearing makes it worse. This is a pre-existing issue, not caused by Phase A, but now more visible.
- **Word-order "vs" detection** (item 11) — `"Jokic this season vs Embiid"` breaks comparison detection because "vs" is not adjacent to both player names. Not fixed; documented as residual.

### What Phase A didn't cover (residuals for later phases)

- **Entity-resolution anomalies**: #30 (`team='WAS'` for a Philly player), #45 (`player='Carmelo Anthony'` from "Anthony Davis"), two-player queries where `detect_player` picks the wrong subject. These need Phase E or a dedicated entity-resolution overhaul.
- **Undefined fuzzy-skill terms**: "all-around games" (#19), "catch-and-shoot" (#34), "transition scorer" (#35) — guardrail §7.2 says don't fake these; needs glossary definitions (Phase B can reserve the slots).
- **Context filters**: "4th quarter" (#49), "clutch" — Phase E territory.
- **Opponent-quality buckets**: "top-10 defenses" (#23), "contenders" — Phase E, but definitions should be reserved in Phase B glossary.
- **Multi-player AND**: "LeBron and AD both play" (#45) — plan §8 excludes multi-intent from all phases.

### Scope adjustments for Phase B

Phase A shipped fuzzy time-word handling (item 9), which the plan originally placed in Phase B as "formalize fuzzy-time definitions in glossary." Phase B should therefore focus on:

1. **Consolidating** the scattered alias tables (STAT_ALIASES, LEADERBOARD_STAT_ALIASES, verbal-form aliases) into one shared resource
2. **Creating** a glossary module that centralizes fuzzy-term definitions
3. **Reserving** undefined terms in the glossary with clear "not yet shipped" markers
4. **Reconciling** the two stat-pattern systems (STAT_PATTERN regex vs. STAT_ALIASES dict)

---

## 1. `[x]` Audit current alias fragmentation

**Why:** Before consolidating, we need a clear inventory of where aliases are defined and where they diverge. Multiple locations have overlapping but inconsistent alias tables.

**Scope:**

- Catalog every alias definition across the codebase: `STAT_ALIASES`, `LEADERBOARD_STAT_ALIASES`, `TEAM_LEADERBOARD_STAT_ALIASES`, `STAT_PATTERN`, stat detection in `_occurrence_route_utils.py`, etc.
- For each alias source, record: location, what it maps, which detectors consume it
- Identify aliases that exist in one table but not another (e.g., verbal forms added to STAT_ALIASES in Phase A but not to STAT_PATTERN)
- Produce a markdown inventory in `docs/planning/phase_b_alias_inventory.md`

**Files likely touched:**

- `docs/planning/phase_b_alias_inventory.md` (new)
- No code changes — reconnaissance only

**Acceptance criteria:**

- Every alias source is cataloged with its location and consumers
- Divergences between tables are identified and documented
- The inventory is structured for items 2–4 to consume as a punchlist

**Tests to run:**

- None (reconnaissance only)

**Reference docs to consult:**

- `src/nbatools/commands/_constants.py` — `STAT_ALIASES`, `STAT_PATTERN`
- `src/nbatools/commands/_leaderboard_utils.py` — `LEADERBOARD_STAT_ALIASES`
- [`parser/specification.md §2.2`](../architecture/parser/specification.md#22-alias-mapping)

---

## 2. `[x]` Unify stat aliases into a single source of truth

**Why:** `STAT_ALIASES`, `LEADERBOARD_STAT_ALIASES`, and `STAT_PATTERN` have overlapping but divergent content. A single canonical alias table eliminates drift and reduces the surface area for future phrasing work.

**Scope:**

- Merge `STAT_ALIASES` and `LEADERBOARD_STAT_ALIASES` into one dict (or have the leaderboard dict explicitly extend the base dict)
- Auto-generate `STAT_PATTERN` regex from the alias dict keys so it can never drift
- Ensure all detectors (`detect_stat`, `detect_player_leaderboard_stat`, `detect_team_leaderboard_stat`) consume the unified source
- Preserve the distinction between "this stat exists for leaderboard queries" and "this stat exists generally" if needed (via metadata in the alias entry, not separate dicts)

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — canonical alias dict
- `src/nbatools/commands/_leaderboard_utils.py` — consume from `_constants.py`
- `src/nbatools/commands/_parse_helpers.py` — `detect_stat` and `STAT_PATTERN`

**Acceptance criteria:**

- `STAT_PATTERN` is generated from the alias dict, not hand-maintained
- No alias exists in one table that should exist in both but doesn't
- All existing tests pass with no behavior change

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-preflight`

**Reference docs to consult:**

- [`parser/specification.md §2.2`](../architecture/parser/specification.md#22-alias-mapping)
- Item 1's alias inventory

---

## 3. `[x]` Create glossary module for fuzzy-term definitions

**Why:** Phase A hardcoded time-word defaults inline (`lately` → `last_n=10`, `past month` → 30 days). A glossary module centralizes these so the code documents its own product-policy decisions. Spec §18 becomes a mirror of this module, documented once and kept in sync.

**Scope:**

- Create `src/nbatools/commands/_glossary.py` with a data structure defining every fuzzy term and its expansion
- Include time terms (already shipped in Phase A), undefined skill terms (not shipped, marked as such), and opponent-quality terms (reserved for Phase E)
- Refactor `extract_last_n` and `extract_date_range` to read from the glossary rather than hardcoding values
- Mark unshipped terms clearly (e.g., `shipped=False`) so code that tries to use them gets a clear error
- Update spec §18 to be a complete mirror of the glossary module — every term present, each with its shipped/reserved/undefined status

**Files likely touched:**

- `src/nbatools/commands/_glossary.py` (new)
- `src/nbatools/commands/_parse_helpers.py` — `extract_last_n` refactor
- `src/nbatools/commands/_date_utils.py` — `extract_date_range` refactor
- `docs/architecture/parser/specification.md` — §18 full sync

**Acceptance criteria:**

- Every fuzzy time term from spec §18.1 is defined in the glossary module
- Undefined/reserved terms are in the glossary but marked as not shipped
- `extract_last_n` and `extract_date_range` read their defaults from the glossary
- Specification §18 is a complete mirror of the glossary module — every term present, each with its shipped/reserved/undefined status

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-preflight`

**Reference docs to consult:**

- [`parser/specification.md §18`](../architecture/parser/specification.md#18-glossary-and-vocabulary)
- Phase A item 9 implementation

---

## 4. `[x]` Reserve undefined skill and quality terms in glossary

**Why:** Terms like `hottest`, `best games`, `all-around`, `catch-and-shoot`, `contenders`, `good teams` appear in user queries but have no formal definition. Reserving them in the glossary makes the parser's coverage explicit and prevents silent guessing (guardrail §7.2). This item adds the reservation slots only — improved error messaging for reserved terms is deferred to Phase D where "I can't do this query" becomes a first-class response shape.

**Scope:**

- Add every identified undefined term from Phase A residuals and spec §18.2 to the glossary with `shipped=False`
- Categorize: skill terms, quality terms, opponent-quality terms
- Document the reservation in spec §18

**Files likely touched:**

- `src/nbatools/commands/_glossary.py` — add reserved entries
- `docs/architecture/parser/specification.md` — §18.2, §18.3

**Acceptance criteria:**

- Every undefined term from Phase A's gap inventory is in the glossary
- Spec §18 documents all reserved terms with their status

**Explicitly out of scope:**

- Improved error messages or "not supported" responses for reserved terms. Deferred to Phase D (ambiguity and confidence), where clear-failure messaging becomes a first-class response shape across the parser. Adding partial messaging in Phase B would either duplicate Phase D's work or constrain its design.

**Tests to run:**

- `make test-parser`

**Reference docs to consult:**

- [`parser/specification.md §18`](../architecture/parser/specification.md#18-glossary-and-vocabulary)
- `docs/planning/phase_a_gap_inventory.md` — undefined terms

---

## 5. `[x]` Normalize text earlier in the pipeline

**Why:** Currently, `normalize_text` is called independently in many detectors. Some detectors lowercase, some don't; some strip whitespace, some receive already-normalized text. A single normalization pass at pipeline entry eliminates inconsistencies.

**Scope:**

- Ensure `_build_parse_state` normalizes text once at entry and passes the normalized form to all detectors
- Audit each detector for redundant `normalize_text` calls and remove them
- Verify that case-sensitive operations (entity resolution) still receive original-case text where needed

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — `_build_parse_state` entry point
- `src/nbatools/commands/_parse_helpers.py` — remove per-detector normalization
- `src/nbatools/commands/_matchup_utils.py` — same

**Acceptance criteria:**

- Text normalization happens exactly once at pipeline entry
- No detector calls `normalize_text` internally (or explicitly documents why it needs to)
- All existing tests pass

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §2.1`](../architecture/parser/specification.md#21-pre-processing-pipeline)

---

## 6. `[x]` Reconcile STAT_PATTERN with alias dict

**Why:** `STAT_PATTERN` is a hand-maintained regex that must stay in sync with `STAT_ALIASES`. Phase A added verbal forms to `STAT_ALIASES` but not to `STAT_PATTERN`, relying on `detect_stat` (which uses the dict). If item 2 auto-generates the pattern, this item verifies correctness and handles edge cases.

**Scope:**

- Verify that auto-generated `STAT_PATTERN` correctly handles multi-word aliases (e.g., "three point percentage")
- Ensure the regex sorts longer aliases first to avoid partial matches (e.g., "three point %" before "three")
- Test with all stat aliases from the unified dict
- Remove any remaining hand-maintained `STAT_PATTERN` if fully generated

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — pattern generation logic
- Tests for edge cases

**Acceptance criteria:**

- `STAT_PATTERN` is provably correct for all entries in the alias dict
- Multi-word aliases match correctly
- No partial-match regressions

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- Item 2 implementation

---

## 7. `[x]` Document stat-alias table in query_catalog.md

**Why:** Users (and agents) need to know which stat phrasings are recognized. The unified alias table should have a human-readable rendering in the catalog.

**Scope:**

- Add a §2.6 (or equivalent) to `query_catalog.md` listing every recognized stat alias grouped by canonical stat
- Include both standard and verbal forms
- Note which aliases are leaderboard-only if that distinction persists

**Files likely touched:**

- `docs/reference/query_catalog.md` — new §2.6

**Acceptance criteria:**

- Every entry in the unified alias dict is represented in the catalog
- Every canonical stat has at least one alias example documented

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_catalog.md`](../reference/query_catalog.md)
- Unified alias dict from item 2

---

## 8. `[x]` Consolidate threshold operator handling

**Why:** Threshold extraction has multiple code paths (`extract_min_value`, `extract_threshold_conditions`, inline `N or more` / `N+` patterns added in Phase A). Consolidating into one threshold-extraction pipeline reduces future maintenance.

**Scope:**

- Identify all places where threshold values are extracted
- Consolidate into `extract_threshold_conditions` as the single entry point
- Ensure `extract_min_value` either delegates to the consolidated path or is removed
- Verify that all threshold patterns from Phase A (item 5, item 6) still work

**Files likely touched:**

- `src/nbatools/commands/_parse_helpers.py` — `extract_min_value`, `extract_threshold_conditions`
- `src/nbatools/commands/natural_query.py` — callers

**Acceptance criteria:**

- One code path for threshold extraction
- All Phase A equivalence tests still pass
- No duplicate threshold patterns

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §7`](../architecture/parser/specification.md#7-thresholds)

---

## 9. `[x]` Add leaderboard verbal-form aliases to unified dict

**Why:** Phase A added `scored`, `scoring`, `scores`, `rebounded`, `rebounding`, `assisted` to `STAT_ALIASES` and `scores` to `LEADERBOARD_STAT_ALIASES`. After item 2 unifies the dicts, ensure all verbal forms are consistently available across all contexts.

**Scope:**

- Review every verbal-form alias added in Phase A
- Ensure each is in the unified dict with appropriate metadata
- Add any missing verbal forms discovered during review (e.g., `blocked`, `stolen`)
- Update STAT_PATTERN (or its auto-generation) to include them

**Files likely touched:**

- `src/nbatools/commands/_constants.py`

**Acceptance criteria:**

- Every verbal-form stat alias is in the unified dict
- `detect_stat` and `detect_player_leaderboard_stat` both recognize them
- No regression in existing tests

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- Phase A items 3, 8 implementations

---

## 10. `[x]` Phase B retrospective and Phase C work queue draft

**Why:** Self-propagating final task. Ensures learnings are captured and the next phase is scoped before this one closes.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals
- Review the plan's Phase C scope ([`query_surface_expansion_plan.md §5.3`](./query_surface_expansion_plan.md)) against what Phase B actually accomplished
- If the plan needs changes, edit [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) in the same session
- Draft `phase_c_work_queue.md` following the same structure as this file

**Files likely touched:**

- `docs/planning/phase_c_work_queue.md` (new)
- `docs/planning/query_surface_expansion_plan.md` (if scope change)
- `docs/planning/phase_b_work_queue.md` (check this item as done)

**Acceptance criteria:**

- `phase_c_work_queue.md` exists and covers Phase C's scope
- Every item in the new queue is PR-sized with clear acceptance criteria
- The final item is the meta-task "retrospective + draft Phase D work queue"
- This item in `phase_b_work_queue.md` is checked off

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_surface_expansion_plan.md §9`](./query_surface_expansion_plan.md) — work queue convention
- [`query_surface_expansion_plan.md §5.3`](./query_surface_expansion_plan.md) — Phase C scope
- This file as a structural template

---

## Phase B retrospective

### What went well

- **Alias unification** (item 2) was the single highest-leverage change: `STAT_PATTERN` auto-generation from `STAT_ALIASES` eliminated a whole class of drift bugs, and `LEADERBOARD_STAT_ALIASES` extending the base dict means new aliases propagate everywhere automatically.
- **Glossary module** (item 3) centralized fuzzy-term definitions that had been hardcoded inline in `extract_last_n` and `extract_date_range`. The `shipped` flag makes the parser's coverage boundary explicit.
- **Early normalization** (item 5) — moving `normalize_text` to the top of `_build_parse_state` was straightforward and eliminated ~15 redundant per-detector calls.
- **STAT_PATTERN reconciliation** (item 6) was mostly free after item 2 auto-generated the pattern — verification confirmed multi-word aliases sort correctly (longest-first).

### What was harder than expected

- **Threshold consolidation** (item 8) — adding `N+ STAT` to `extract_threshold_conditions` triggered a false positive: "last 10 scoring leaders" matched "10 scoring" as a threshold. Required lookbehind guards (`(?<!last )`, `(?<!past )`, etc.) in `extract_min_value`'s bare-pattern fallback.
- **Glossary scope** (items 3–4) — deciding which undefined terms to reserve required reviewing Phase A's gap inventory exhaustively. The boundary between "reserved for later" and "never going to ship" is fuzzy.

### What Phase B didn't cover (residuals for later phases)

- **Occurrence-route threshold duplication**: `_occurrence_route_utils.py` has its own `_COMPOUND_STAT_MAP` and `_parse_single_threshold` that duplicate parts of `extract_threshold_conditions`. These weren't consolidated because occurrence routing depends on structural context (the `and` split logic) that doesn't map cleanly to the general threshold pipeline. A future unification could share the stat-map but keep the structural parsing separate.
- **Entity-resolution anomalies** from Phase A remain: wrong-subject detection in two-player queries, team resolution from player city. These are Phase D/E territory.
- **Improved error messaging for reserved terms**: deferred to Phase D where "I can't do this query" becomes a first-class response shape.

### Scope adjustments for Phase C

Phase B's glossary and alias work means Phase C can focus purely on default-rule formalization without worrying about term definitions. The `notes` field infrastructure (adding entries when a default fires) is the main new surface.

---

---

## Addendum — coverage gaps surfaced after retrospective

> **Why these exist:** Items 1–10 completed successfully and Phase B's consolidation work is structurally sound — no behavior regressions, clean alias unification, working glossary module. However, manual CLI spot-checking after merge revealed two coverage gaps where the spec and catalog claim capability that the consolidated code does not provide. Per guardrail §7.2 ("do not broaden claims without backing them up"), the docs are currently overclaiming. Fix is to bring code up to what the docs already promise. Scoped narrowly — not adding new capabilities, just closing the gap between documented and shipped.

---

## 11. `[x]` Add missing spec-documented stat-alias nicknames

**Why:** `docs/architecture/parser/specification.md` §18.4 lists `boards`, `dimes`, `swipes`, `swats` as canonical metric aliases, and `docs/reference/query_catalog.md` §2.6 claims to be the full inventory of `STAT_ALIASES`. But the consolidated `STAT_ALIASES` dict in `_constants.py` does not include those nicknames, so queries like "most boards this season" and "top dimes this season" fail with "Could not map this query to a supported pattern." This is a documentation-vs-reality gap introduced because Phase B item 2 reconciled the old tables against each other, not against the spec.

**Scope:**

- Add these entries to `STAT_ALIASES` in `src/nbatools/commands/_constants.py`:
  - `"boards": "reb"`
  - `"dimes": "ast"`
  - `"swipes": "stl"`
  - `"swats": "blk"`
- Verify the auto-generated `STAT_PATTERN` picks them up correctly (it should, since it's generated from the dict)
- Update `docs/reference/query_catalog.md` §2.6 to include these in the corresponding rows
- Add result-level tests: each nickname query should return a non-empty leaderboard equivalent to its canonical form

**Files likely touched:**

- `src/nbatools/commands/_constants.py` — add four alias entries
- `docs/reference/query_catalog.md` — update §2.6 table rows for `pts`, `reb`, `ast`, `stl`, `blk`
- `tests/parser/` — new tests asserting nickname forms route equivalently to canonical forms

**Acceptance criteria:**

- `nbatools-cli ask "most boards this season"` returns a non-empty rebounds leaderboard equivalent to `"most rebounds this season"`
- `nbatools-cli ask "most dimes this season"` returns a non-empty assists leaderboard equivalent to `"most assists this season"`
- `nbatools-cli ask "top swipes this season"` returns a non-empty steals leaderboard equivalent to `"most steals this season"`
- `nbatools-cli ask "most swats this season"` returns a non-empty blocks leaderboard equivalent to `"most blocks this season"`
- At least 4 new equivalence-group tests cover these nickname-to-canonical pairs
- `query_catalog.md` §2.6 table includes all four new aliases in the appropriate rows

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §18.4`](../architecture/parser/specification.md#184-metric-aliases) — canonical alias inventory
- [`query_catalog.md §2.6`](../reference/query_catalog.md) — living catalog
- Phase B item 2 implementation for the consolidated `STAT_ALIASES` structure

---

## 12. `[x]` Wire `last couple weeks` / `past 2 weeks` through date extraction

**Why:** `query_catalog.md` §2.2 documents `last couple weeks` and `past 2 weeks` as fuzzy-time forms that should resolve to a rolling 14-day window. The Phase B glossary module (`_glossary.py`) was supposed to centralize this. But manual testing shows `Jokic last couple weeks` returns "No matching games found" while equivalent queries like `Jokic past month` and `Jokic lately` work correctly. Either the glossary entry is missing, or the date-range extractor in `_date_utils.py` does not consult the glossary for these specific phrases.

**Scope:**

- Verify whether the glossary module contains entries for `last couple weeks` / `past 2 weeks` with a 14-day window definition; add them if missing
- Verify `extract_date_range` in `_date_utils.py` correctly matches both surface forms and produces a date range for "today minus 14 days" to "today"
- Do NOT add `last night` — that query correctly returns no-match given the current dataset's data end date; freshness-aware error messaging is Phase D territory and out of scope here
- Add result-level tests that assert `last couple weeks` and `past 2 weeks` produce a non-empty result when data within 14 days exists

**Files likely touched:**

- `src/nbatools/commands/_glossary.py` — add entries if missing
- `src/nbatools/commands/_date_utils.py` — `extract_date_range` expansion
- `tests/parser/` — new tests for these specific phrases

**Acceptance criteria:**

- `nbatools-cli ask "Jokic last couple weeks"` returns a non-empty result (assuming dataset has games within the last 14 days of its data end date)
- `nbatools-cli ask "Jokic past 2 weeks"` returns equivalent result to `"Jokic last couple weeks"`
- Both phrases resolve to the same date window per the glossary's 14-day default
- `lately`, `recently`, `past month` continue to work unchanged — no regressions
- New tests exist that assert the date window is applied correctly

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`query_catalog.md §2.2`](../reference/query_catalog.md) — documented fuzzy-time forms
- [`parser/specification.md §18.1`](../architecture/parser/specification.md#181-time-term-definitions-suggested-defaults--confirm-at-product-level) — time-term definitions
- Phase B item 3 (`_glossary.py` creation) and Phase A item 9 (`extract_date_range` expansion)

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase B is complete. The draft of `phase_c_work_queue.md` from item 10 is the handoff artifact.

If any item is skipped (`[-]`), note the reason inline so the reason survives in git history.
