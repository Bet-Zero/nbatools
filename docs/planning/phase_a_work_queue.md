# Phase A Work Queue

> **Role:** Sequenced, PR-sized work items for Phase A of [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) — _phrasing parity on shipped capabilities._
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

## 1. `[x]` Equivalence-group test infrastructure

**Why:** Phase A is primarily about making semantically equivalent queries produce identical parse states. The rest of Phase A needs a concise, reusable way to assert that. Building this first pays off on every subsequent item.

**Scope:**

- Create a pytest utility (fixture, helper function, or parametrize pattern) that takes a list of surface forms and asserts they all produce equivalent parse states
- "Equivalent" means: same `route`, same `route_kwargs` (modulo formatting), same key slot values (player, team, stat, thresholds, timeframe). Confidence and `normalized_query` obviously differ and are excluded from equivalence
- Add one working example using it — the simplest equivalence group from [`parser/examples.md §7.1`](../architecture/parser/examples.md#71-leaderboard--points-leaders-last-10-games)

**Files likely touched:**

- `tests/parser/` — new test module (e.g. `test_equivalence_groups.py`) or helper (`conftest.py`)
- Nothing in `src/nbatools/commands/` unless a minor API tweak is needed

**Acceptance criteria:**

- A reusable helper exists for equivalence-group assertions
- At least one equivalence group from [`parser/examples.md §7`](../architecture/parser/examples.md#7-equivalence-groups) is tested and passing
- The pattern is documented enough that subsequent items can copy-paste it

**Tests to run:**

- `make test-parser`
- `make test-impacted`

**Reference docs to consult:**

- [`parser/examples.md §7`](../architecture/parser/examples.md#7-equivalence-groups)
- [`parser/specification.md §19.2`](../architecture/parser/specification.md#192-equivalence-groups)

---

## 2. `[x]` Reconnaissance: catalog current phrasing gaps

**Why:** Phase A's work is scoped by _which pairs don't currently route identically_. Knowing which specific pairs diverge lets later items be targeted instead of speculative.

**Scope:**

- Run every paired example from [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form) through the parser (50 pairs)
- For each pair, compare `parse_query(question_form)` vs `parse_query(search_form)`
- Record every divergent pair with: inputs, diverging slots, likely cause
- Produce a gap inventory — can be a temporary markdown file in `docs/planning/phase_a_gap_inventory.md` or a new test file that has one failing case per divergent pair (XFail pattern is fine)

**Files likely touched:**

- `docs/planning/phase_a_gap_inventory.md` (new, or equivalent test file)
- Possibly new test module using the helper from item 1

**Acceptance criteria:**

- Every pair from [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form) is classified as passing or failing
- Every failing pair is recorded with the diverging slots identified
- The inventory is structured such that items 3–8 can consume it as a punchlist

**Tests to run:**

- `make test-parser`
- Just running `parse_query` on each pair is sufficient — no assertions required for this reconnaissance item

**Reference docs to consult:**

- [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form)

---

## 3. `[x]` Leaderboard phrasing parity

**Why:** Leaderboards are the highest-volume user intent and the most common first query. Parity here has the most user-visible impact.

**Scope:**

- Fix every divergent leaderboard pair from item 2's inventory (both player and team leaderboards)
- Add search-form and shorthand coverage for any leaderboard shape in [`query_catalog.md §3.6`](../reference/query_catalog.md) that currently fails parity
- Make sure the operator words in [`parser/specification.md §4.4`](../architecture/parser/specification.md#44-decision-signals) (`top`, `best`, `most`, `highest`, `leaders`, `hottest`) all route as strong signals

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — leaderboard route branches in `_finalize_route`
- `src/nbatools/commands/_leaderboard_utils.py` — `detect_player_leaderboard_stat`, `detect_team_leaderboard_stat`, `wants_ascending_leaderboard`
- `src/nbatools/commands/_parse_helpers.py` — `wants_leaderboard`, `wants_team_leaderboard`
- `tests/parser/` — equivalence tests added for each newly-covered leaderboard shape

**Acceptance criteria:**

- Every paired leaderboard example from [`parser/examples.md §3.1`](../architecture/parser/examples.md#31-leaders-and-rankings) and [§3.7](../architecture/parser/examples.md#37-whos-been-the-best-at--over-) routes identically in question and search forms
- At least one shorthand form (`points leaders last 10` pattern) also routes identically for each shape
- `query_catalog.md` updated if any new surface forms are now supported

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-impacted` during iteration

**Reference docs to consult:**

- [`parser/examples.md §3.1`](../architecture/parser/examples.md#31-leaders-and-rankings), [§3.7](../architecture/parser/examples.md#37-whos-been-the-best-at--over-)
- [`query_catalog.md §3.6`](../reference/query_catalog.md)

---

## 4. `[x]` Summary phrasing parity

**Why:** Summaries (`recent form`, `stats`, `averages`) are the second-most-common shape. "Player + timeframe" shorthand (`Jokic last 10`) relies on default-routing to summary, which needs consistent phrasing coverage.

**Scope:**

- Fix divergent summary pairs from item 2's inventory
- Ensure the default rule `<player> + <timeframe>` → `summary` fires for all reasonable phrasings
- Ensure `recent form` triggers don't over-fire on non-summary queries (e.g. don't force `last_n=10` when an explicit timeframe is given)

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — summary routing branches
- `src/nbatools/commands/_parse_helpers.py` — `wants_summary`, `wants_recent_form`, `default_season_for_context`

**Acceptance criteria:**

- Every paired summary example from [`parser/examples.md §3.3`](../architecture/parser/examples.md#33-last-n-games--since-date) routes identically
- Shorthand like `Jokic last 10`, `Jokic recent`, `Jokic last 10 games` all route to the same `player_game_summary` parse state
- No regressions in how `recent form` is detected vs. explicit-timeframe queries

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/examples.md §3.3`](../architecture/parser/examples.md#33-last-n-games--since-date)
- [`parser/specification.md §15.1`](../architecture/parser/specification.md#151-defaults-already-in-place)
- [`query_catalog.md §3.3`](../reference/query_catalog.md)

---

## 5. `[x]` Record phrasing parity

**Why:** Record queries are a natural sports intent and already have a dedicated router cluster. Phrasing parity unlocks that cluster for users who type search-form or shorthand.

**Scope:**

- Fix divergent record pairs from item 2's inventory
- Support the full range of `record when <condition>` phrasings — team threshold, player threshold (where shipped), home/away, wins/losses
- Ensure the default `<team> + <opponent-quality>` → `record` rule is set up for later Phase E completion (even though opponent-quality itself isn't shipped yet; the routing default should exist)

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — record routing branches
- `src/nbatools/commands/_playoff_record_route_utils.py` — `detect_record_intent`, `try_playoff_record_route`, `try_record_leaderboard_route`

**Acceptance criteria:**

- Every paired record example from [`parser/examples.md §3.9`](../architecture/parser/examples.md#39-record-when-___) routes identically
- Shorthand forms (`Lakers record vs Celtics`, `Bucks record Giannis out`) produce correct routes
- No regressions on currently-shipped record capability per [`query_catalog.md §3.8`](../reference/query_catalog.md)

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/examples.md §3.9`](../architecture/parser/examples.md#39-record-when-___)
- [`query_catalog.md §3.8`](../reference/query_catalog.md)

---

## 6. `[x]` Occurrence and frequency phrasing parity

**Why:** "How often" and "how many" are extremely natural user phrasings. Occurrence is already shipped (single, compound, distinct-count); parity here is about making all three phrasing styles reach the existing routes.

**Scope:**

- Fix divergent occurrence/frequency pairs from item 2's inventory
- Ensure `how often`, `how many`, `N+ <stat> games`, and shorthand (`Jokic td this season`, `Curry 5+ threes`) all route through `extract_occurrence_event` / `extract_compound_occurrence_event` correctly
- Cover compound cases (`how many games with 25+ pts and 10+ ast`)

**Files likely touched:**

- `src/nbatools/commands/natural_query.py` — occurrence routing
- `src/nbatools/commands/_occurrence_route_utils.py` — `extract_occurrence_event`, `extract_compound_occurrence_event`, `wants_occurrence_leaderboard`

**Acceptance criteria:**

- Every paired frequency example from [`parser/examples.md §3.8`](../architecture/parser/examples.md#38-frequency--how-often) routes identically
- Compound occurrence examples from [`parser/examples.md §4.2`](../architecture/parser/examples.md#42-occurrence-queries) parse correctly regardless of phrasing
- No regressions on occurrence support per [`query_catalog.md §3.10`](../reference/query_catalog.md)

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/examples.md §3.8`](../architecture/parser/examples.md#38-frequency--how-often), [§4.2](../architecture/parser/examples.md#42-occurrence-queries)
- [`parser/specification.md §12`](../architecture/parser/specification.md#12-occurrence-queries)

---

## 7. `[x]` Streak phrasing parity

**Why:** Streak queries are shipped and distinctive, but the surface-form coverage may be narrower than the question-form coverage. Parity here extends an already-solid capability.

**Scope:**

- Fix divergent streak pairs from item 2's inventory
- Cover search-form and shorthand variants (`Jokic longest 30-point streak`, `longest Jokic 30 point streak`, `Jokic consecutive 30 point games longest`)
- Both player and team streaks

**Files likely touched:**

- `src/nbatools/commands/_parse_helpers.py` — `extract_streak_request`, `extract_team_streak_request`, `STREAK_SPECIAL_PATTERNS`, `TEAM_STREAK_SPECIAL_PATTERNS`
- `src/nbatools/commands/natural_query.py` — streak routing

**Acceptance criteria:**

- Every streak shape in [`parser/examples.md §4.1`](../architecture/parser/examples.md#41-streak-queries) accepts all three phrasing styles
- The three-season default time scope for streaks (per [`parser/specification.md §13.3`](../architecture/parser/specification.md#133-default-time-scope)) is preserved

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/examples.md §4.1`](../architecture/parser/examples.md#41-streak-queries)
- [`parser/specification.md §13`](../architecture/parser/specification.md#13-streak-queries)

---

## 8. `[x]` Split and context phrasing parity

**Why:** Splits (home/away, wins/losses) are common and simple, but often the first thing users shorten to telegraphic phrasing (`Celtics home away`, `Jokic wins losses`). Parity here covers those.

**Scope:**

- Fix divergent split pairs from item 2's inventory
- Ensure all variations of home/away, road/away, wins/losses, win/loss detect cleanly
- Ensure split-comparison phrasings (`home vs away`, `in wins and losses`) route to `split_query` with the right `split_type`

**Files likely touched:**

- `src/nbatools/commands/_parse_helpers.py` — `detect_home_away`, `detect_wins_losses`, `detect_split_type`, `wants_split_summary`
- `src/nbatools/commands/natural_query.py` — split routing

**Acceptance criteria:**

- Every paired split example from [`parser/examples.md §3.10`](../architecture/parser/examples.md#310-splits--context--shorthand-search-style) routes identically
- `split_type` values are consistent for equivalent phrasings

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/examples.md §3.10`](../architecture/parser/examples.md#310-splits--context--shorthand-search-style)
- [`query_catalog.md §3.5`](../reference/query_catalog.md)

---

## 9. `[x]` Fuzzy time-word expansion

**Why:** `lately`, `recently`, `past month`, `last couple weeks` are common in natural phrasing but resolve inconsistently today. Getting these right unlocks a large swath of shorthand that currently routes unpredictably.

**Scope:**

- Formalize handling for: `lately`, `recently`, `past month`, `last month`, `past 2 weeks`, `last couple weeks`, `last night`, `yesterday`, `tonight`, `today`
- Use the glossary defaults from [`parser/specification.md §18.1`](../architecture/parser/specification.md#181-time-term-definitions-suggested-defaults--confirm-at-product-level) (note these are _suggested_ — confirm each with a brief product-policy decision before locking it in)
- Add test coverage for each new term

**Files likely touched:**

- `src/nbatools/commands/_date_utils.py` — `extract_date_range` expansion
- `src/nbatools/commands/_parse_helpers.py` — `wants_recent_form` and possibly a new `extract_fuzzy_time_window` helper
- `src/nbatools/commands/_constants.py` — alias mapping if needed
- `docs/architecture/parser/specification.md` — keep §18.1 in sync with what's actually implemented

**Acceptance criteria:**

- Each new fuzzy time word produces a deterministic, documented time window
- `Jokic lately`, `Jokic recently`, `Jokic past month`, `Jokic last night` all return sensible parse states
- Documentation in [`parser/specification.md §18.1`](../architecture/parser/specification.md#181-time-term-definitions-suggested-defaults--confirm-at-product-level) matches live behavior

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-preflight` (this touches shared infra)

**Reference docs to consult:**

- [`parser/specification.md §6.2`](../architecture/parser/specification.md#62-partial--needing-expansion)
- [`parser/specification.md §18.1`](../architecture/parser/specification.md#181-time-term-definitions-suggested-defaults--confirm-at-product-level)

---

## 10. `[x]` Absence phrasing expansion

**Why:** `detect_without_player` already exists and works well for `without X`. Users also naturally say `X out`, `X didn't play`, `no X`, `sans X`, `minus X` — all of which should reach the same logic.

**Scope:**

- Extend `detect_without_player` to recognize: `X out`, `X didn't play`, `X is out`, `X was out`, `no X`, `sans X`, `minus X`, `without X` (already), `w/o X` (already)
- Preserve the existing behavior where a detected `without_player` that matches the subject clears the subject so routing goes through the team path
- Carefully disambiguate `X out` from `X off` — the former is absence, the latter would be on/off (Phase E)

**Files likely touched:**

- `src/nbatools/commands/_matchup_utils.py` — `detect_without_player`
- Possibly `src/nbatools/commands/_constants.py` for alias expansion

**Acceptance criteria:**

- Every phrasing in scope routes to `without_player` set correctly
- The subject-clearing behavior is preserved (see `natural_query.py` lines around `if without_player and player and without_player.upper() == player.upper()`)
- `X off` is NOT misclassified as absence

**Tests to run:**

- `make test-parser`
- `make test-query`

**Reference docs to consult:**

- [`parser/specification.md §10`](../architecture/parser/specification.md#10-absence-and-with-without-logic)
- [`query_catalog.md §2.3`](../reference/query_catalog.md)

---

## 11. `[x]` Word-order equivalence test suite

**Why:** By this point, many phrasing differences are handled. Word-order variants (`best scorers last month` vs. `last month best scorers`) are a specific subcategory that's easy to miss. An explicit test suite locks it in and makes regressions visible.

**Scope:**

- Create a dedicated test file covering word-order permutations of common queries
- Cover at least: leaderboard phrasings, summary phrasings, record phrasings, occurrence phrasings
- 20–30 cases covering the patterns in [`parser/examples.md §5.4`](../architecture/parser/examples.md#54-word-order-swaps)

**Files likely touched:**

- `tests/parser/test_word_order_equivalence.py` (new)
- Possibly small fixes to `natural_query.py` or `_parse_helpers.py` if specific permutations fail (though earlier items likely caught the major ones)

**Acceptance criteria:**

- A dedicated test file exists with at least 20 word-order equivalence groups
- All tests pass
- Any failures found trigger small fixes in the appropriate detector rather than deferring them

**Tests to run:**

- `make test-parser`

**Reference docs to consult:**

- [`parser/examples.md §5.4`](../architecture/parser/examples.md#54-word-order-swaps)

---

## 12. `[x]` Sync `query_catalog.md` with Phase A additions

**Why:** Per AGENTS.md, `query_catalog.md` is the living inventory and must stay in sync with shipped capability. Phase A will have broadened the surface forms that various routes accept; that belongs in the catalog.

**Scope:**

- Review [`docs/reference/query_catalog.md`](../reference/query_catalog.md) against every Phase A item
- Add newly-supported surface forms to the relevant sections
- Add newly-supported fuzzy time words to §2.2
- Add newly-supported absence phrasings to §2.3
- Cross-check [`docs/reference/current_state_guide.md`](../reference/current_state_guide.md) — only update there if a claim has changed about _verified_ behavior (not just surface form)

**Files likely touched:**

- `docs/reference/query_catalog.md`
- Possibly `docs/reference/current_state_guide.md`
- Possibly `docs/index.md` if any new section was added

**Acceptance criteria:**

- `query_catalog.md` accurately reflects every surface form now supported
- No claim in the catalog lacks corresponding test coverage from Phase A
- Any linked docs (index, current-state-guide) are updated consistently

**Tests to run:**

- None (docs only), but spot-check that examples in the catalog actually work via `nbatools-cli ask "..."`

**Reference docs to consult:**

- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)
- [AGENTS.md](../../AGENTS.md) — doc maintenance rules

---

## 13. `[x]` Phase A retrospective and Phase B work queue draft

**Why:** This is the self-propagating task. With Phase A's scope substantially complete, Phase B should be drafted now so there's no dead time between phases, and any Phase A learnings should reshape Phase B's scope before it starts.

**Scope:**

- Review every checked item above. Note outcomes:
  - Were any items harder than expected? Easier?
  - Did any items reveal issues the plan didn't anticipate?
  - Are there shorthand or phrasing gaps that should have been in Phase A but weren't?
- Review the plan's Phase B scope ([`query_surface_expansion_plan.md §5.2`](./query_surface_expansion_plan.md)) against what Phase A actually accomplished. Note any scope adjustments needed
- If the plan needs changes, edit [`query_surface_expansion_plan.md`](./query_surface_expansion_plan.md) in the same session — don't let it drift silently
- Draft `phase_b_work_queue.md` following the same structure as this file:
  - Each item has: title, why, scope, files likely touched, acceptance criteria, test commands, reference docs, status checkbox
  - Items are ordered to minimize rework
  - The final item is the same self-propagating meta-task (draft Phase C queue)
- Aim for a similar size to this queue (10–15 items)

**Files likely touched:**

- `docs/planning/phase_b_work_queue.md` (new)
- `docs/planning/query_surface_expansion_plan.md` (if scope change)
- `docs/planning/phase_a_work_queue.md` (check this item as done)

**Acceptance criteria:**

- `phase_b_work_queue.md` exists and covers Phase B's scope
- Every item in the new queue is PR-sized, with clear acceptance criteria and test commands
- The final item of `phase_b_work_queue.md` is the meta-task "retrospective + draft Phase C work queue"
- If the plan changed, the diff is justified by Phase A learnings
- This item in `phase_a_work_queue.md` is checked off

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`query_surface_expansion_plan.md §9`](./query_surface_expansion_plan.md) — work queue convention
- [`query_surface_expansion_plan.md §5.2`](./query_surface_expansion_plan.md) — Phase B scope
- This file as a structural template

---

## Addendum — result-level bug fixes (added post-retrospective)

> **Why these exist:** Items 1–13 completed successfully at the parse-state level. Manual spot-checking after Phase A closed revealed three bugs where the parser correctly extracts slots but downstream routes don't respect them, producing confident-but-wrong results. Per the plan's §7.2 guardrail ("prefer honest unsupported responses over silently wrong answers"), these need to be fixed before Phase B starts. Scoped to stay narrow — broader ambiguity handling stays in Phase D.

---

## 14. `[x]` Audit slot-to-route contract for leaderboards

**Why:** Phase A proved the parser sets `last_n`, `home_only`/`away_only`, and `wins_only`/`losses_only` correctly for leaderboard queries. Manual testing showed `points leaders last 10` and `most points in wins` both return season-long leaders, meaning the routes silently ignore those slots. The phrasing-parity guarantee is empty if the routes don't honor the slots they're passed.

**Scope:**

- For each leaderboard route called by `_finalize_route` (`season_leaders`, `top_player_games`, `season_team_leaders`, `top_team_games`, and anything else in the leaderboard cluster), verify it reads and applies: `last_n`, `home_only`, `away_only`, `wins_only`, `losses_only`, `start_date`, `end_date`
- Fix any route that silently drops these slots
- Add tests that assert on **result content**, not just parse state — e.g., a `last_n=10` leaderboard's `pts_per_game` values should differ from the season-long leaderboard for the same players

**Files likely touched:**

- `src/nbatools/commands/_leaderboard_utils.py`
- Engine modules implementing `season_leaders`, `top_player_games`, `season_team_leaders`, `top_team_games` (follow imports from the utils module)
- `tests/parser/` or `tests/engine/` — new result-level tests

**Acceptance criteria:**

- Every leaderboard route respects the slots above when present
- `points leaders last 10` returns different `pts_per_game` values than `points leaders this season`
- `most points in wins` returns different values than `most points this season`
- At least 5 new result-level tests asserting filters actually change outputs

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-engine`

**Reference docs to consult:**

- [`parser/specification.md §5`](../architecture/parser/specification.md#5-slot-extraction) — slot contract
- [`query_catalog.md §3.6`](../reference/query_catalog.md) — currently-claimed leaderboard surface

---

## 15. `[x]` Audit slot-to-route contract for team_record

**Why:** Same pattern as item 14, for the record family. The `without_player` slot is correctly detected by the parser (Phase A item 10 added phrasings for it) but `team_record` doesn't filter the sample — manual testing returned a full-season record when `without_player` should have narrowed the sample significantly.

**Scope:**

- Verify `team_record` applies `without_player` when present
- Check related record routes for the same issue: `team_matchup_record`, record-leaderboard routes in `try_record_leaderboard_route`, playoff-record routes in `try_playoff_record_route`
- Add result-level tests: the sample size (games counted) must shrink when `without_player` filter is active

**Files likely touched:**

- `src/nbatools/commands/_playoff_record_route_utils.py`
- Engine modules implementing `team_record` and its variants
- `tests/parser/` or `tests/engine/` — new result-level tests

**Acceptance criteria:**

- `team_record` respects `without_player`
- A query like `Lakers record without LeBron` returns a smaller sample than `Lakers record this season`
- Same check for `home_only`, `away_only`, `wins_only`, `losses_only` if any of those are currently dropped
- At least 3 new result-level tests

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-engine`

**Reference docs to consult:**

- [`parser/specification.md §10`](../architecture/parser/specification.md#10-absence-and-with-without-logic)
- [`query_catalog.md §3.8`](../reference/query_catalog.md) — currently-claimed record surface

---

## 16. `[x]` Guard against zero-sample filter combinations

**Why:** Manual testing of `Celtics record when Giannis out` exposed a serious failure mode: the parser set `team=BOS, without_player=GIANNIS`, but Giannis has never played for Boston, so the filter is nonsensical. Instead of returning "no matching games," the engine silently fell through to an unfiltered full-season record — a confident wrong answer. Plan §7.2 explicitly calls this out as the #1 failure mode. A narrow guard is cheap and high-value; full proactive detection of nonsensical filters stays in Phase D.

**Scope:**

- In the routes touched by items 14 and 15, detect when applied filters reduce the sample to zero rows
- Return an explicit empty-sample result with a clear note (e.g., `"no games matched the specified filters"`), not a fallback to unfiltered data
- Align with the existing comparison `no_match` behavior per [`query_catalog.md §3.4`](../reference/query_catalog.md)
- Document this behavior in [`query_catalog.md`](../reference/query_catalog.md) so users know zero-sample → explicit no-match, not silent fallback

**Files likely touched:**

- Same engine routes as items 14 and 15
- Result envelope / `QueryResponse` handling if a new status is needed
- `docs/reference/query_catalog.md` — new note about zero-sample behavior
- `tests/engine/` — tests for zero-sample cases

**Acceptance criteria:**

- `Celtics record when Giannis out` returns an explicit no-match result, not a full-season record
- Other nonsensical filter combinations return no-match rather than fallback data
- The no-match result is structurally consistent with existing `no_match` results from the comparison family
- Catalog documents the behavior

**Explicitly out of scope:**

- Proactive detection of nonsensical filter combinations before execution (Phase D)
- Surfacing alternate interpretations when a filter is nonsensical (Phase D)
- Parse-level confidence scoring (Phase D)

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-engine`
- `make test-output` (if envelope shape changes)

**Reference docs to consult:**

- [`query_surface_expansion_plan.md §7.2`](./query_surface_expansion_plan.md) — guardrail: honest unsupported over silent wrong
- [`query_catalog.md §3.4`](../reference/query_catalog.md) — existing `no_match` behavior precedent

---

## 17. `[x]` Complete slot-to-route contract: wins_only and losses_only

**Why:** Item 14 addressed `last_n` and delivered equivalence-verified result differences, but manual re-testing after merge showed `wins_only` and `losses_only` are still being dropped downstream. `most points in wins` returns identical values to `points leaders this season`, meaning the kwarg reaches `season_leaders` (confirmed in natural_query.py) but the engine doesn't apply it. Item 14's acceptance criteria included this case but the result-level test was never written, so CI did not catch it. This item closes the gap narrowly and adds the specific test that should have existed.

**Scope:**

- Locate the engine-side implementation of `season_leaders` (and `season_team_leaders` if the same code path serves both) and fix the handling so `wins_only` and `losses_only` actually filter the underlying game sample before aggregation
- Verify the fix propagates correctly when combined with other active slots (e.g., `wins_only` + `last_n=10` should apply both filters)
- Add result-level tests that assert actual value differences — not just that the route was called with the right kwargs — for: `points leaders in wins` vs `points leaders this season`, and `points leaders in losses` vs `points leaders this season`
- Add parallel tests for team leaderboards if the same gap exists there

**Files likely touched:**

- Engine module implementing `season_leaders` / `season_team_leaders` (follow imports from `_leaderboard_utils.py` if unsure of location)
- `tests/parser/` or `tests/engine/` — new result-level tests, at least 2 new assertions covering `wins_only` and `losses_only`

**Acceptance criteria:**

- `nbatools-cli ask "most points in wins"` returns `pts_per_game` values that differ from `nbatools-cli ask "points leaders this season"`
- `nbatools-cli ask "most points in losses"` returns `pts_per_game` values that differ from `nbatools-cli ask "points leaders this season"`
- Same check passes for `team_leaderboard` equivalents if applicable
- New result-level tests exist and pass specifically for `wins_only` and `losses_only`, asserting value-level differences (not just parse state or kwarg presence)

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-engine`

**Reference docs to consult:**

- [`parser/specification.md §5`](../architecture/parser/specification.md#5-slot-extraction) — slot contract
- Phase A item 14 for the pattern the fix should follow
- [`query_catalog.md §3.6`](../reference/query_catalog.md) — leaderboard surface

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase A is complete. The draft of `phase_b_work_queue.md` from item 13 is the handoff artifact.

If any item is skipped (`[-]`), note the reason inline so the reason survives in git history.
